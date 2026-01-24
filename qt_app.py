import json
import os
import re
import sys
from datetime import datetime

import requests
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QPlainTextEdit,
    QProgressBar,
    QHeaderView,
    QFileDialog,
)

from douyin_video_parser import DouyinVideoParser

DISABLE_LOGIN = os.environ.get("DISABLE_LOGIN", "0") == "1"

if getattr(sys, "frozen", False):
    os.environ.setdefault(
        "PLAYWRIGHT_BROWSERS_PATH",
        os.path.join(sys._MEIPASS, "playwright-browsers"),
    )
    os.environ.setdefault("PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD", "1")

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
DEFAULT_SAVE_DIR = os.path.join(BASE_DIR, "downloads")


def safe_filename(text: str, fallback: str) -> str:
    text = text or ""
    text = re.sub(r"[\\/:*?\"<>|]", "_", text).strip()
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return fallback
    return text[:60]


def format_time(ts: int | None) -> str:
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def load_config() -> dict:
    data = {
        "cookie": "",
        "save_dir": DEFAULT_SAVE_DIR,
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data.update(json.load(f))
        except Exception:
            pass
    cookie_path = os.path.join(BASE_DIR, "douyin_cookie.txt")
    if os.path.exists(cookie_path):
        try:
            with open(cookie_path, "r", encoding="utf-8") as f:
                data["cookie"] = f.read().lstrip("\ufeff").strip()
        except Exception:
            pass
    return data


def save_config(cookie: str, save_dir: str):
    data = {"cookie": cookie, "save_dir": save_dir}
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(os.path.join(BASE_DIR, "douyin_cookie.txt"), "w", encoding="utf-8") as f:
        f.write(cookie or "")


def cookies_to_header(cookies: list[dict]) -> str:
    parts = []
    for c in cookies:
        name = c.get("name")
        value = c.get("value")
        if name and value is not None:
            parts.append(f"{name}={value}")
    return "; ".join(parts)


def download_file(url: str, path: str, progress_cb=None) -> bool:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/90.0.4430.212 Safari/537.36"
        ),
        "Referer": "https://www.douyin.com/",
        "Origin": "https://www.douyin.com",
        "Accept": "*/*",
        "Range": "bytes=0-",
    }
    try:
        resp = requests.get(url, headers=headers, stream=True, timeout=30)
        if resp.status_code not in (200, 206):
            return False
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb and total > 0:
                        progress_cb(int(downloaded * 100 / total))
        if progress_cb:
            progress_cb(100)
        return True
    except Exception:
        return False


class ParseSingleWorker(QThread):
    result = Signal(dict)
    error = Signal(str)

    def __init__(self, parser: DouyinVideoParser, url: str):
        super().__init__()
        self.parser = parser
        self.url = url

    def run(self):
        info = self.parser.parse_video(self.url)
        if not info:
            self.error.emit("解析失败")
            return
        self.result.emit(info)


class ParseListWorker(QThread):
    result = Signal(dict)
    done = Signal()
    error = Signal(str)

    def __init__(self, parser: DouyinVideoParser, urls: list[str]):
        super().__init__()
        self.parser = parser
        self.urls = urls

    def run(self):
        if not self.urls:
            self.error.emit("列表为空")
            return
        for url in self.urls:
            meta = self.parser.parse_video_meta(url)
            if not meta:
                continue
            payload = {"url": url, **meta}
            self.result.emit(payload)
        self.done.emit()


class ParseUserWorker(QThread):
    result = Signal(list, str)
    error = Signal(str)

    def __init__(self, parser: DouyinVideoParser, url: str, max_pages: int):
        super().__init__()
        self.parser = parser
        self.url = url
        self.max_pages = max_pages

    def run(self):
        url = self.url
        if "douyin.com/video/" in url or "v.douyin.com/" in url:
            user_home = self.parser.get_user_home_from_video_url(url)
            if not user_home:
                self.error.emit("无法从视频解析主页")
                return
            urls = self.parser.get_user_aweme_urls(user_home, max_pages=self.max_pages)
            self.result.emit(urls, user_home)
            return

        urls = self.parser.get_user_aweme_urls(url, max_pages=self.max_pages)
        if not urls:
            self.error.emit("解析主页列表失败")
            return
        self.result.emit(urls, url)


class DownloadWorker(QThread):
    progress = Signal(int)
    status = Signal(str)
    done = Signal(int, int)

    def __init__(self, parser: DouyinVideoParser, urls: list[str], save_dir: str):
        super().__init__()
        self.parser = parser
        self.urls = urls
        self.save_dir = save_dir

    def run(self):
        os.makedirs(self.save_dir, exist_ok=True)
        success = 0
        total = len(self.urls)
        for idx, url in enumerate(self.urls, start=1):
            self.status.emit(f"下载中 {idx}/{total}")
            info = self.parser.parse_video(url)
            if not info or not info.get("nwm_url"):
                continue
            desc = info.get("desc") or ""
            aweme_id = info.get("aweme_id") or "douyin"
            name = safe_filename(desc, aweme_id) + ".mp4"
            path = os.path.join(self.save_dir, name)

            def _cb(p):
                self.progress.emit(p)

            ok = download_file(info["nwm_url"], path, progress_cb=_cb)
            if ok:
                success += 1
        self.done.emit(success, total)


class CookieWorker(QThread):
    qr = Signal(bytes)
    status = Signal(str)
    done = Signal(str)
    error = Signal(str)

    def run(self):
        try:
            from playwright.sync_api import sync_playwright
        except Exception:
            self.error.emit("缺少 playwright，请先安装：pip install playwright && playwright install chromium")
            return

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    locale="zh-CN",
                    timezone_id="Asia/Shanghai",
                )
                page = context.new_page()
                self.status.emit("打开登录页...")
                page.goto("https://www.douyin.com", wait_until="domcontentloaded", timeout=30000)
                content = ""
                try:
                    content = page.content()
                except Exception:
                    content = ""

                if "error_code" in content or "缺少参数" in content:
                    self.status.emit("登录页受限，切换备用入口...")
                    page.goto(
                        "https://www.douyin.com/passport/web/auth/?aid=6383&next=https%3A%2F%2Fwww.douyin.com",
                        wait_until="domcontentloaded",
                        timeout=30000,
                    )

                self.status.emit("等待二维码出现...")
                element = None
                # 优先查找二维码图片（更精确，避免截到整块区域）
                selectors = [
                    "img[aria-label*='二维码']",
                    "img.RhjdbXj8",
                    "img[src^='data:image/png;base64']",
                    "img[src*='qrcode']",
                    "img[src*='qr']",
                    "img[alt*='二维码']",
                    "[class*=qrcode] img",
                ]
                # 若是手机号登录界面，尝试切换到扫码登录
                try:
                    for text in ["扫码登录", "二维码登录", "二维码", "扫码"]:
                        btn = page.query_selector(f"text={text}")
                        if btn:
                            btn.click()
                            break
                except Exception:
                    pass

                for _ in range(40):
                    for sel in selectors:
                        try:
                            el = page.query_selector(sel)
                            if el:
                                box = el.bounding_box()
                                if box and box["width"] >= 120 and box["height"] >= 120:
                                    element = el
                                    break
                        except Exception:
                            continue
                    if element:
                        break
                    page.wait_for_timeout(500)

                # 处理 iframe 场景
                if not element:
                    try:
                        for frame in page.frames:
                            for sel in selectors:
                                el = frame.query_selector(sel)
                                if el:
                                    box = el.bounding_box()
                                    if box and box["width"] >= 120 and box["height"] >= 120:
                                        element = el
                                        break
                            if element:
                                break
                    except Exception:
                        element = None

                if not element:
                    self.error.emit("未找到二维码，请确认页面可访问并未被拦截")
                    browser.close()
                    return

                try:
                    img_bytes = element.screenshot()
                    self.qr.emit(img_bytes)
                except Exception:
                    self.error.emit("二维码截图失败")
                    browser.close()
                    return

                self.status.emit("等待扫码登录...")

                def has_login_cookies(cookies: list[dict]) -> bool:
                    """检测是否有完整的登录cookie（必须包含关键登录标识）"""
                    names = {c.get("name") for c in cookies}
                    # 必须同时有sessionid和sid_tt或uid_tt（这是登录成功的核心标识）
                    has_sessionid = "sessionid" in names
                    has_sid_tt = "sid_tt" in names
                    has_uid_tt = "uid_tt" in names
                    
                    # 主要检测：sessionid + sid_tt 或 uid_tt（必须同时存在）
                    if has_sessionid and (has_sid_tt or has_uid_tt):
                        return True
                    
                    # 次要检测：passport_auth_status且值为"1"（表示已认证）
                    for c in cookies:
                        if c.get("name") == "passport_auth_status" and c.get("value") == "1":
                            return True
                    
                    return False

                # 监听页面导航事件（登录成功通常会跳转）
                navigation_occurred = False
                def on_navigation(frame):
                    nonlocal navigation_occurred
                    if frame == page.main_frame:
                        navigation_occurred = True
                
                page.on("framenavigated", on_navigation)

                # 监听网络请求（登录成功会触发新的API请求）
                login_request_detected = False
                def on_request(request):
                    nonlocal login_request_detected
                    url = request.url
                    # 登录成功后会请求用户信息或主页数据
                    if any(keyword in url for keyword in ["/aweme/v1/web/user/", "/aweme/v1/web/im/user/info/", "/aweme/v1/web/im/user/info/"]):
                        login_request_detected = True
                
                page.on("request", on_request)

                original_url = page.url
                last_cookie_count = 0

                for i in range(300):  # 增加到300次（5分钟）
                    cookies = context.cookies()
                    cookie_count = len(cookies)
                    
                    # 检测cookie数量变化（登录成功会新增多个cookie）
                    cookie_increased = cookie_count > last_cookie_count
                    last_cookie_count = cookie_count
                    
                    login_by_cookie = has_login_cookies(cookies)

                    # 检测二维码是否消失（多种方式检测）
                    qr_gone = False
                    try:
                        if element:
                            # 方式1：检查元素是否可见
                            qr_gone = not element.is_visible()
                            # 方式2：检查元素是否还在DOM中
                            if not qr_gone:
                                try:
                                    element.bounding_box()  # 如果元素不存在会抛异常
                                except Exception:
                                    qr_gone = True
                    except Exception:
                        qr_gone = True
                    
                    # 方式3：检查页面中是否还有二维码相关元素
                    if not qr_gone:
                        try:
                            qr_selectors = [
                                "img[aria-label*='二维码']",
                                "img[src*='qrcode']",
                                "img[src*='qr']",
                            ]
                            found_qr = False
                            for sel in qr_selectors:
                                if page.query_selector(sel):
                                    found_qr = True
                                    break
                            if not found_qr:
                                qr_gone = True
                        except Exception:
                            pass

                    # 检测页面文本变化（增加更多关键词）
                    login_text = False
                    try:
                        page_text = page.content()
                        # 增加更多登录成功的标识
                        login_keywords = [
                            "扫码成功", "已登录", "登录成功", "登录完成", "确认登录",
                            "登录验证成功", "验证通过", "授权成功"
                        ]
                        for t in login_keywords:
                            if t in page_text:
                                login_text = True
                                break
                    except Exception:
                        login_text = False

                    # 检测URL变化（登录成功会跳转）
                    current_url = page.url
                    url_changed = (
                        current_url != original_url and 
                        "login" not in current_url.lower() and 
                        "passport" not in current_url.lower() and
                        "auth" not in current_url.lower()
                    )
                    
                    # 检测是否跳转到主页（douyin.com且不是登录页）
                    is_homepage = (
                        "douyin.com" in current_url and 
                        current_url != original_url and
                        "passport" not in current_url.lower() and
                        "login" not in current_url.lower()
                    )

                    # 综合判断：必须确认登录成功才保存，优先级从高到低
                    # 1. 如果有完整的登录cookie（sessionid + sid_tt/uid_tt），立即保存（最高优先级）
                    if login_by_cookie:
                        self.status.emit("检测到登录Cookie，正在保存...")
                        page.wait_for_timeout(2000)  # 等待cookie完整
                        cookies = context.cookies()
                        # 再次确认有登录cookie
                        if has_login_cookies(cookies):
                            cookie_str = cookies_to_header(cookies)
                            self.done.emit(cookie_str)
                            browser.close()
                            return
                    
                    # 2. 如果跳转到主页（最可靠的登录成功标志）
                    if is_homepage:
                        self.status.emit("检测到跳转主页，等待Cookie...")
                        page.wait_for_timeout(4000)  # 等待cookie完整设置
                        cookies = context.cookies()
                        # 必须确认有登录cookie才保存
                        if has_login_cookies(cookies):
                            cookie_str = cookies_to_header(cookies)
                            self.done.emit(cookie_str)
                            browser.close()
                            return
                    
                    # 3. 如果二维码消失 + URL变化（跳转），说明登录成功
                    if qr_gone and url_changed:
                        self.status.emit("检测到登录跳转，等待Cookie...")
                        page.wait_for_timeout(4000)  # 等待cookie完整设置
                        cookies = context.cookies()
                        # 必须确认有登录cookie才保存
                        if has_login_cookies(cookies):
                            cookie_str = cookies_to_header(cookies)
                            self.done.emit(cookie_str)
                            browser.close()
                            return
                    
                    # 4. 如果页面文本显示登录成功
                    if login_text:
                        self.status.emit("检测到登录成功提示，验证Cookie...")
                        page.wait_for_timeout(4000)
                        cookies = context.cookies()
                        # 必须确认有登录cookie才保存
                        if has_login_cookies(cookies):
                            cookie_str = cookies_to_header(cookies)
                            self.done.emit(cookie_str)
                            browser.close()
                            return
                    
                    # 5. 如果检测到登录相关的API请求
                    if login_request_detected:
                        self.status.emit("检测到登录请求，验证Cookie...")
                        page.wait_for_timeout(3000)
                        cookies = context.cookies()
                        # 必须确认有登录cookie才保存
                        if has_login_cookies(cookies):
                            cookie_str = cookies_to_header(cookies)
                            self.done.emit(cookie_str)
                            browser.close()
                            return
                    
                    # 6. 如果二维码消失 + cookie数量显著增加，等待后验证
                    if qr_gone and cookie_increased and cookie_count >= 10:
                        self.status.emit("检测到扫码成功，等待Cookie设置...")
                        page.wait_for_timeout(5000)  # 等待更长时间确保cookie完整
                        cookies = context.cookies()
                        # 必须确认有登录cookie才保存
                        if has_login_cookies(cookies):
                            cookie_str = cookies_to_header(cookies)
                            self.done.emit(cookie_str)
                            browser.close()
                            return
                    
                    # 7. 如果二维码消失 + 导航发生 + cookie增加
                    if qr_gone and navigation_occurred and cookie_increased:
                        self.status.emit("检测到页面变化，等待Cookie...")
                        page.wait_for_timeout(4000)
                        cookies = context.cookies()
                        if has_login_cookies(cookies):
                            cookie_str = cookies_to_header(cookies)
                            self.done.emit(cookie_str)
                            browser.close()
                            return

                    if i % 10 == 0:
                        self.status.emit(f"等待扫码登录... ({i//10 + 1}/30)")
                    page.wait_for_timeout(1000)

                self.error.emit("登录超时，请重试")
                browser.close()
        except Exception as e:
            self.error.emit(f"获取失败: {e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.parser = DouyinVideoParser()
        self.config = load_config()
        self.parser.set_cookie(self.config.get("cookie"))
        self.save_dir = self.config.get("save_dir", DEFAULT_SAVE_DIR)

        self.setWindowTitle("抖音无水印解析器")
        self.setMinimumSize(1200, 760)

        tabs = QTabWidget()
        tabs.addTab(self._build_single_tab(), "单视频下载")
        tabs.addTab(self._build_user_tab(), "主页/视频解析")
        tabs.addTab(self._build_config_tab(), "配置")
        self.setCentralWidget(tabs)
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(
            """
            QWidget { background: #0f1115; color: #e6e6e6; font-size: 14px; }
            QLineEdit, QSpinBox, QPlainTextEdit { background: #1b1f2a; border: 1px solid #2b3142; padding: 8px; border-radius: 6px; }
            QPushButton { background: #3b82f6; border: none; padding: 8px 14px; border-radius: 6px; }
            QPushButton:hover { background: #2563eb; }
            QPushButton:disabled { background: #394256; }
            QTabBar::tab { padding: 10px 16px; background: #1b1f2a; margin: 2px; border-radius: 6px; }
            QTabBar::tab:selected { background: #2b3142; }
            QTableWidget { background: #121520; border: 1px solid #2b3142; }
            QHeaderView::section { background: #1b1f2a; padding: 6px; border: none; }
            """
        )

    def _build_single_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        row = QHBoxLayout()
        self.single_input = QLineEdit()
        self.single_input.setPlaceholderText("输入单个视频分享链接")
        self.single_parse_btn = QPushButton("解析")
        self.single_download_btn = QPushButton("下载到默认目录")
        self.single_download_btn.setEnabled(False)
        row.addWidget(self.single_input)
        row.addWidget(self.single_parse_btn)
        row.addWidget(self.single_download_btn)

        self.single_cover = QLabel("封面预览")
        self.single_cover.setFixedSize(520, 300)
        self.single_cover.setAlignment(Qt.AlignCenter)
        self.single_cover.setStyleSheet("background: #1b1f2a; border-radius: 8px;")

        self.single_info = QLabel()
        self.single_info.setWordWrap(True)

        info_row = QHBoxLayout()
        info_row.addWidget(self.single_cover, 2)
        info_row.addWidget(self.single_info, 3)

        self.single_loading = QProgressBar()
        self.single_loading.setRange(0, 0)
        self.single_loading.setVisible(False)

        self.single_progress = QProgressBar()
        self.single_progress.setRange(0, 100)
        self.single_progress.setVisible(False)

        layout.addLayout(row)
        layout.addLayout(info_row)
        layout.addWidget(self.single_loading)
        layout.addWidget(self.single_progress)
        layout.addStretch(1)

        self.single_parse_btn.clicked.connect(self._on_single_parse)
        self.single_download_btn.clicked.connect(self._on_single_download)
        return widget

    def _build_user_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        row = QHBoxLayout()
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("输入用户主页或视频链接")
        self.user_max_pages = QSpinBox()
        self.user_max_pages.setRange(1, 50)
        self.user_max_pages.setValue(1)
        self.user_parse_btn = QPushButton("解析")
        self.user_select_all_btn = QPushButton("全选")
        self.user_clear_all_btn = QPushButton("全不选")
        self.user_download_btn = QPushButton("下载勾选(默认目录)")
        self.user_download_btn.setEnabled(False)

        row.addWidget(self.user_input)
        row.addWidget(QLabel("max_pages"))
        row.addWidget(self.user_max_pages)
        row.addWidget(self.user_parse_btn)
        row.addWidget(self.user_select_all_btn)
        row.addWidget(self.user_clear_all_btn)
        row.addWidget(self.user_download_btn)

        self.user_table = self._build_table()
        self.user_loading = QProgressBar()
        self.user_loading.setRange(0, 0)
        self.user_loading.setVisible(False)
        self.user_progress = QProgressBar()
        self.user_progress.setRange(0, 100)
        self.user_progress.setVisible(False)

        layout.addLayout(row)
        layout.addWidget(self.user_table)
        layout.addWidget(self.user_loading)
        layout.addWidget(self.user_progress)

        self.user_parse_btn.clicked.connect(self._on_user_parse)
        self.user_download_btn.clicked.connect(self._on_user_download)
        self.user_select_all_btn.clicked.connect(lambda: self._toggle_all(self.user_table, True))
        self.user_clear_all_btn.clicked.connect(lambda: self._toggle_all(self.user_table, False))
        return widget

    def _build_config_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        action_row = QHBoxLayout()
        self.cookie_status = QLabel("状态：未获取")
        get_cookie_btn = QPushButton("获取Cookie")
        action_row.addWidget(get_cookie_btn)
        action_row.addWidget(self.cookie_status)
        action_row.addStretch(1)

        self.cookie_editor = QPlainTextEdit()
        self.cookie_editor.setPlaceholderText("粘贴抖音 Cookie")
        self.cookie_editor.setPlainText(self.config.get("cookie", ""))

        self.cookie_qr = QLabel("二维码预览")
        self.cookie_qr.setFixedSize(260, 260)
        self.cookie_qr.setAlignment(Qt.AlignCenter)
        self.cookie_qr.setStyleSheet("background: #1b1f2a; border-radius: 8px;")

        path_row = QHBoxLayout()
        self.save_path_input = QLineEdit()
        self.save_path_input.setText(self.save_dir)
        browse_btn = QPushButton("选择目录")
        save_btn = QPushButton("保存配置")
        path_row.addWidget(self.save_path_input)
        path_row.addWidget(browse_btn)
        path_row.addWidget(save_btn)

        layout.addLayout(action_row)
        layout.addWidget(self.cookie_qr)
        layout.addWidget(QLabel("Cookie"))
        layout.addWidget(self.cookie_editor)
        layout.addWidget(QLabel("保存路径"))
        layout.addLayout(path_row)
        layout.addStretch(1)

        if DISABLE_LOGIN:
            get_cookie_btn.setEnabled(False)
            self.cookie_qr.setText("精简版不支持自动登录")
            self.cookie_status.setText("状态：已禁用")
        else:
            get_cookie_btn.clicked.connect(self._on_get_cookie)
        browse_btn.clicked.connect(self._on_browse_dir)
        save_btn.clicked.connect(self._on_save_config)
        return widget

    def _build_table(self):
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["选择", "封面", "文案", "视频ID", "时间"])
        table.setColumnWidth(0, 60)
        table.setColumnWidth(1, 200)
        table.setColumnWidth(2, 420)
        table.setColumnWidth(3, 180)
        table.setColumnWidth(4, 180)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        return table

    def _on_single_parse(self):
        url = self.single_input.text().strip()
        if not url:
            return
        self.single_parse_btn.setEnabled(False)
        self.single_download_btn.setEnabled(False)
        self.single_loading.setVisible(True)
        self.single_info.setText("解析中...")

        self.single_worker = ParseSingleWorker(self.parser, url)
        self.single_worker.result.connect(self._single_result)
        self.single_worker.error.connect(self._single_error)
        self.single_worker.finished.connect(self._single_parse_done)
        self.single_worker.start()

    def _single_parse_done(self):
        self.single_loading.setVisible(False)
        self.single_parse_btn.setEnabled(True)

    def _single_result(self, info: dict):
        self.single_info.setText(
            f"ID: {info.get('aweme_id')}\n"
            f"时间: {format_time(info.get('create_time'))}\n"
            f"作者: {info.get('author_nickname')}\n"
            f"文案: {info.get('desc')}\n"
            f"封面: {info.get('cover_url')}\n"
            f"无水印: {info.get('nwm_url')}"
        )
        self.single_download_btn.setEnabled(bool(info.get("nwm_url")))
        self.single_download_btn.setProperty("nwm_url", info.get("nwm_url"))
        self.single_download_btn.setProperty("desc", info.get("desc"))
        self.single_download_btn.setProperty("aweme_id", info.get("aweme_id"))
        cover_url = info.get("cover_url")
        if cover_url:
            self._set_cover(self.single_cover, cover_url, 520, 300)

    def _single_error(self, msg: str):
        self.single_info.setText(msg)

    def _on_single_download(self):
        url = self.single_download_btn.property("nwm_url")
        if not url:
            return
        os.makedirs(self.save_dir, exist_ok=True)
        desc = self.single_download_btn.property("desc") or ""
        aweme_id = self.single_download_btn.property("aweme_id") or "douyin"
        name = safe_filename(desc, aweme_id) + ".mp4"
        path = os.path.join(self.save_dir, name)

        self.single_progress.setVisible(True)
        self.single_progress.setValue(0)

        def _cb(p):
            self.single_progress.setValue(p)

        ok = download_file(url, path, progress_cb=_cb)
        QMessageBox.information(self, "下载", "完成" if ok else "失败")
        self.single_progress.setVisible(False)

    def _on_user_parse(self):
        url = self.user_input.text().strip()
        if not url:
            return
        self.user_parse_btn.setEnabled(False)
        self.user_download_btn.setEnabled(False)
        self.user_table.setRowCount(0)
        self.user_loading.setVisible(True)

        self.user_worker = ParseUserWorker(
            self.parser, url, self.user_max_pages.value()
        )
        self.user_worker.result.connect(self._user_list_result)
        self.user_worker.error.connect(self._user_error)
        self.user_worker.finished.connect(self._user_parse_done)
        self.user_worker.start()

    def _user_parse_done(self):
        self.user_parse_btn.setEnabled(True)

    def _user_list_result(self, urls: list, user_home: str):
        self.user_table.setRowCount(0)
        self.user_download_btn.setEnabled(True)

        self.list_worker = ParseListWorker(self.parser, urls)
        self.list_worker.result.connect(lambda info: self._append_row(self.user_table, info))
        self.list_worker.error.connect(self._user_error)
        self.list_worker.done.connect(lambda: self.user_loading.setVisible(False))
        self.user_loading.setVisible(True)
        self.list_worker.start()

    def _user_error(self, msg: str):
        self.user_loading.setVisible(False)
        QMessageBox.warning(self, "解析失败", msg)

    def _on_user_download(self):
        urls = self._get_checked_urls(self.user_table)
        if not urls:
            return
        self.user_progress.setVisible(True)
        self.user_progress.setValue(0)
        self.user_download_btn.setEnabled(False)

        self.download_worker = DownloadWorker(self.parser, urls, self.save_dir)
        self.download_worker.progress.connect(self.user_progress.setValue)
        self.download_worker.status.connect(lambda _: None)
        self.download_worker.done.connect(self._download_done)
        self.download_worker.start()

    def _download_done(self, success: int, total: int):
        self.user_progress.setVisible(False)
        self.user_download_btn.setEnabled(True)
        QMessageBox.information(self, "下载完成", f"成功 {success} / {total}")

    def _toggle_all(self, table: QTableWidget, checked: bool):
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item:
                item.setCheckState(Qt.Checked if checked else Qt.Unchecked)

    def _get_checked_urls(self, table: QTableWidget) -> list[str]:
        urls = []
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                url = item.data(Qt.UserRole)
                if url:
                    urls.append(url)
        return urls

    def _append_row(self, table: QTableWidget, info: dict):
        row = table.rowCount()
        table.insertRow(row)
        table.setRowHeight(row, 110)

        check_item = QTableWidgetItem()
        check_item.setCheckState(Qt.Unchecked)
        check_item.setData(Qt.UserRole, info.get("url"))
        table.setItem(row, 0, check_item)

        cover_label = QLabel()
        cover_label.setFixedSize(180, 100)
        cover_label.setAlignment(Qt.AlignCenter)
        cover_label.setStyleSheet("background: #1b1f2a; border-radius: 6px;")
        if info.get("cover_url"):
            self._set_cover(cover_label, info["cover_url"], 180, 100)
        table.setCellWidget(row, 1, cover_label)

        table.setItem(row, 2, QTableWidgetItem(info.get("desc") or ""))
        table.setItem(row, 3, QTableWidgetItem(info.get("aweme_id") or ""))
        table.setItem(row, 4, QTableWidgetItem(format_time(info.get("create_time"))))

    def _set_cover(self, label: QLabel, url: str, w: int, h: int):
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                pix = QPixmap()
                if pix.loadFromData(resp.content):
                    label.setPixmap(pix.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        except Exception:
            pass

    def _on_browse_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择保存目录", self.save_dir)
        if path:
            self.save_path_input.setText(path)

    def _on_save_config(self):
        cookie = self.cookie_editor.toPlainText().strip()
        save_dir = self.save_path_input.text().strip() or DEFAULT_SAVE_DIR
        save_config(cookie, save_dir)
        self.parser.set_cookie(cookie)
        self.save_dir = save_dir
        QMessageBox.information(self, "保存", "配置已保存")

    def _on_get_cookie(self):
        if DISABLE_LOGIN:
            QMessageBox.information(self, "提示", "精简版不支持自动获取Cookie")
            return
        self.cookie_status.setText("状态：获取中...")
        self.cookie_qr.setText("加载二维码中...")
        self.cookie_worker = CookieWorker()
        self.cookie_worker.qr.connect(self._on_cookie_qr)
        self.cookie_worker.status.connect(self._on_cookie_status)
        self.cookie_worker.done.connect(self._on_cookie_done)
        self.cookie_worker.error.connect(self._on_cookie_error)
        self.cookie_worker.start()

    def _on_cookie_qr(self, img_bytes: bytes):
        pix = QPixmap()
        if pix.loadFromData(img_bytes):
            self.cookie_qr.setPixmap(pix.scaled(260, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _on_cookie_status(self, text: str):
        self.cookie_status.setText(f"状态：{text}")

    def _on_cookie_done(self, cookie: str):
        self.cookie_status.setText("状态：获取成功")
        self.cookie_editor.setPlainText(cookie)
        self.parser.set_cookie(cookie)
        save_dir = self.save_path_input.text().strip() or DEFAULT_SAVE_DIR
        save_config(cookie, save_dir)
        QMessageBox.information(self, "Cookie", "已保存到文件")

    def _on_cookie_error(self, msg: str):
        self.cookie_status.setText("状态：失败")
        QMessageBox.warning(self, "Cookie", msg)


def main():
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()

