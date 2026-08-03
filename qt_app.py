"""
Douyin Video Downloader - Qt6 GUI Application
Full version with auto cookie acquisition support
"""
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
    QDialog,
    QDialogButtonBox,
    QRadioButton,
    QButtonGroup,
    QGroupBox,
    QScrollArea,
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


DOUYIN_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)

QR_SELECTORS = [
    ".qrcode-img img",
    "img[aria-label*='二维码']",
    "img.RhjdbXj8",
    "img[src^='data:image/png;base64']",
    "img[src*='qrcode']",
    "img[src*='qr']",
    "img[alt*='二维码']",
    "[class*=qrcode] img",
]


def clear_proxy_env():
    for key in (
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "SOCKS_PROXY",
        "http_proxy", "https_proxy", "all_proxy", "socks_proxy",
    ):
        os.environ.pop(key, None)


def has_valid_login_cookie(cookies: list[dict]) -> bool:
    for c in cookies:
        if c.get("name") == "sessionid" and c.get("value"):
            return True
    return False


def is_logged_in_url(url: str) -> bool:
    lower = (url or "").lower()
    if "douyin.com" not in lower:
        return False
    return not any(x in lower for x in ("passport", "/login", "/auth"))


def open_login_panel(page) -> None:
    """打开登录弹窗并切到扫码（只用短超时选择器，避免全页扫描卡顿）"""
    clicked = False
    for fn in (
        lambda: page.click("#login-panel-new", timeout=3000),
        lambda: page.locator("[id*='login-panel'], [id*='login-pannel']").first.click(timeout=2000),
        lambda: page.get_by_role("button", name="登录").first.click(timeout=2000),
    ):
        try:
            fn()
            clicked = True
            break
        except Exception:
            continue
    if clicked:
        page.wait_for_timeout(1500)

    for text in ("扫码登录", "二维码登录", "二维码"):
        try:
            page.get_by_text(text, exact=False).first.click(timeout=1500)
            page.wait_for_timeout(800)
            return
        except Exception:
            continue


def find_qr_element(page):
    scopes = [page, *page.frames]
    for scope in scopes:
        for sel in QR_SELECTORS:
            try:
                el = scope.query_selector(sel)
                if not el:
                    continue
                box = el.bounding_box()
                if box and box.get("width", 0) >= 100 and box.get("height", 0) >= 100:
                    return el
            except Exception:
                continue
    return None


def wait_for_qr_element(page, status_cb=None, timeout_sec: int = 35):
    """轮询等待二维码出现，必要时重试打开登录弹窗。"""
    import time

    deadline = time.time() + timeout_sec
    opened = False
    last_open_retry = 0.0
    last_status_emit = 0.0
    while time.time() < deadline:
        element = find_qr_element(page)
        if element:
            return element

        now = time.time()
        if not opened:
            open_login_panel(page)
            opened = True
            last_open_retry = now
        elif now - last_open_retry >= 8:
            open_login_panel(page)
            last_open_retry = now

        if status_cb and now - last_status_emit >= 2:
            remain = max(0, int(deadline - now))
            status_cb(f"等待二维码出现...（剩余约 {remain}s）")
            last_status_emit = now

        page.wait_for_timeout(500)
    return None


def extract_login_cookies(context, page, status_cb=None) -> str | None:
    """登录成功后提取 Cookie"""
    cookies = context.cookies()
    if has_valid_login_cookie(cookies):
        return cookies_to_header(cookies)

    if status_cb:
        status_cb("登录成功，正在提取 Cookie...")
    try:
        page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(2000)
    except Exception:
        pass

    cookies = context.cookies()
    if has_valid_login_cookie(cookies):
        return cookies_to_header(cookies)
    return None


class QualitySelectionDialog(QDialog):
    """Modern quality selection dialog"""
    def __init__(self, qualities: list[dict], parent=None):
        super().__init__(parent)
        # Deduplicate qualities by ratio and bit_rate
        self.qualities = self._deduplicate_qualities(qualities)
        self.selected_quality = None
        self.setWindowTitle("选择视频质量")
        self.setMinimumWidth(500)
        self.setMaximumHeight(600)  # Limit maximum height
        self.setup_ui()
        self._apply_style()
    
    def _deduplicate_qualities(self, qualities: list[dict]) -> list[dict]:
        """Remove duplicate qualities based on ratio and bit_rate"""
        seen = set()
        unique_qualities = []
        for quality in qualities:
            ratio = quality.get("ratio", "")
            bit_rate = quality.get("bit_rate", 0)
            # Create a unique key
            key = (ratio, bit_rate)
            if key not in seen:
                seen.add(key)
                unique_qualities.append(quality)
        return unique_qualities
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        title = QLabel("请选择要下载的视频质量：")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)
        
        # Create scroll area for quality options
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(200)
        scroll_area.setMaximumHeight(400)  # Limit scroll area height
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #2b3142;
                border-radius: 8px;
                background: #1b1f2a;
            }
            QScrollBar:vertical {
                background: #1b1f2a;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #3b82f6;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #2563eb;
            }
        """)
        
        group = QGroupBox()
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(8)
        self.button_group = QButtonGroup(self)
        
        if not self.qualities:
            no_quality = QLabel("未找到可用的视频质量选项")
            no_quality.setStyleSheet("color: #999; padding: 20px;")
            group_layout.addWidget(no_quality)
        else:
            for idx, quality in enumerate(self.qualities):
                ratio = quality.get("ratio", "未知")
                bit_rate = quality.get("bit_rate", 0)
                quality_label = quality.get("quality_label", ratio)
                
                # Create quality description
                desc = f"{quality_label}"
                if bit_rate > 0 and f"{bit_rate // 1000}Kbps" not in quality_label:
                    desc += f" - {bit_rate // 1000}Kbps"
                
                radio = QRadioButton(desc)
                radio.setProperty("quality", quality)
                if idx == 0:  # Select highest quality by default
                    radio.setChecked(True)
                    self.selected_quality = quality
                self.button_group.addButton(radio, idx)
                group_layout.addWidget(radio)
                
                # Connect signal to update selection
                radio.toggled.connect(lambda checked, q=quality: self._on_quality_selected(checked, q))
        
        group_layout.addStretch()  # Add stretch at the end
        scroll_area.setWidget(group)
        layout.addWidget(scroll_area)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _on_quality_selected(self, checked: bool, quality: dict):
        if checked:
            self.selected_quality = quality
    
    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background: #0f1115; color: #e6e6e6; }
            QGroupBox { 
                border: 2px solid #2b3142; 
                border-radius: 8px; 
                margin-top: 10px; 
                padding-top: 15px;
                background: #1b1f2a;
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px;
            }
            QRadioButton {
                padding: 12px;
                font-size: 14px;
                border-radius: 6px;
                margin: 4px;
            }
            QRadioButton:hover {
                background: #2b3142;
            }
            QRadioButton::indicator {
                width: 20px;
                height: 20px;
                border-radius: 10px;
                border: 2px solid #3b82f6;
            }
            QRadioButton::indicator:checked {
                background: #3b82f6;
            }
            QDialogButtonBox QPushButton {
                min-width: 80px;
                padding: 8px 16px;
            }
        """)
    
    def get_selected_quality(self) -> dict | None:
        return self.selected_quality


def download_file(url: str, path: str, progress_cb=None) -> bool:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36"
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
        try:
            info = self.parser.parse_video(self.url)
            if not info:
                # Try to get more debug info
                try:
                    video_id = self.parser.get_video_id(self.url)
                    if video_id:
                        data = self.parser.get_aweme_detail(video_id)
                        if data:
                            aweme = data.get("aweme_detail") or {}
                            aweme_type = aweme.get("aweme_type", "unknown")
                            has_images = bool(aweme.get("images"))
                            self.error.emit(f"解析失败：aweme_type={aweme_type}, 是否有images={has_images}")
                        else:
                            self.error.emit("解析失败：无法获取API数据，请检查Cookie是否有效")
                    else:
                        # Try to get the redirected URL for debugging
                        try:
                            import requests
                            session = requests.Session()
                            session.headers.update({
                                "User-Agent": self.parser.user_agent,
                                "Referer": "https://www.douyin.com/"
                            })
                            resp = session.get(self.url, allow_redirects=True, timeout=10)
                            real_url = resp.url
                            self.error.emit(f"解析失败：无法提取视频ID\n访问URL: {real_url}\n请确认链接是否为有效的抖音视频/图集链接")
                        except Exception:
                            self.error.emit("解析失败：无法提取视频ID，请确认链接格式正确")
                except Exception as e:
                    self.error.emit(f"解析失败：{str(e)}")
                return
            self.result.emit(info)
        except Exception as e:
            self.error.emit(f"解析失败：{str(e)}")


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
            # Parse full video info including qualities
            info = self.parser.parse_video(url)
            if not info:
                continue
            payload = {"url": url, **info}
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

    def __init__(self, parser: DouyinVideoParser, video_infos: list[dict], save_dir: str, selected_ratio: str = None):
        super().__init__()
        self.parser = parser
        self.video_infos = video_infos  # List of dicts with url, qualities, etc.
        self.save_dir = save_dir
        self.selected_ratio = selected_ratio  # Optional: filter by ratio

    def run(self):
        os.makedirs(self.save_dir, exist_ok=True)
        success = 0
        total = len(self.video_infos)
        for idx, info in enumerate(self.video_infos, start=1):
            content_type = info.get("content_type", "video")
            
            if content_type == "video":
                ok = self._download_video(info, idx, total)
            elif content_type == "image":
                ok = self._download_album(info, idx, total)
            else:
                continue
            
            if ok:
                success += 1
        self.done.emit(success, total)
    
    def _download_video(self, info: dict, idx: int, total: int) -> bool:
        """Download a single video"""
        self.status.emit(f"下载视频 {idx}/{total}")
        
        # Get video URL
        url = info.get("url")
        if not url:
            return False
        
        # Get download URL from qualities or fallback to nwm_url
        download_url = None
        qualities = info.get("qualities", [])
        
        if qualities:
            if self.selected_ratio:
                # Find quality matching selected ratio
                for q in qualities:
                    if q.get("ratio") == self.selected_ratio:
                        download_url = q.get("url")
                        break
            # If no match or no ratio specified, use highest quality
            if not download_url and qualities:
                download_url = qualities[0].get("url")
        
        # Fallback to nwm_url
        if not download_url:
            download_url = info.get("nwm_url")
        
        if not download_url:
            return False
        
        desc = info.get("desc") or ""
        aweme_id = info.get("aweme_id") or "douyin"
        
        # Add quality suffix to filename
        quality_suffix = ""
        if self.selected_ratio:
            quality_suffix = f"_{self.selected_ratio}"
        elif qualities:
            quality_suffix = f"_{qualities[0].get('ratio', '')}"
        
        name = safe_filename(desc, aweme_id) + quality_suffix + ".mp4"
        path = os.path.join(self.save_dir, name)

        def _cb(p):
            self.progress.emit(p)

        return download_file(download_url, path, progress_cb=_cb)
    
    def _download_album(self, info: dict, idx: int, total: int) -> bool:
        """Download an album (multiple images)"""
        self.status.emit(f"下载图集 {idx}/{total}")
        
        image_data = info.get("image_data", {})
        image_urls = image_data.get("image_urls", [])
        
        if not image_urls:
            return False
        
        desc = info.get("desc") or ""
        aweme_id = info.get("aweme_id") or "douyin"
        
        # Create folder for album
        folder_name = safe_filename(desc, aweme_id)
        album_dir = os.path.join(self.save_dir, folder_name)
        os.makedirs(album_dir, exist_ok=True)
        
        # Check if these are live images
        is_live = image_data.get("is_live", False)
        
        success_count = 0
        for img_idx, img_url in enumerate(image_urls, start=1):
            try:
                # Determine file extension first
                url_lower = img_url.lower()
                if is_live:
                    # Live images are videos, save as mp4
                    ext = ".mp4"
                elif ("gif" in url_lower or url_lower.endswith(".gif") or ".gif?" in url_lower):
                    ext = ".gif"
                elif ("webp" in url_lower or url_lower.endswith(".webp") or ".webp?" in url_lower):
                    ext = ".webp"
                elif ("png" in url_lower or url_lower.endswith(".png") or ".png?" in url_lower):
                    ext = ".png"
                else:
                    ext = ".jpg"  # Default to jpg
                
                img_name = f"{img_idx:03d}{ext}"
                img_path = os.path.join(album_dir, img_name)
                
                # For live images (MP4 videos), use download_file function for better support
                if is_live:
                    def _cb(p):
                        # Progress callback for live images
                        pass
                    ok = download_file(img_url, img_path, progress_cb=_cb)
                    if ok:
                        success_count += 1
                else:
                    # For static images, use simple download
                    resp = requests.get(img_url, timeout=30, stream=True, headers={"User-Agent": self.parser.user_agent})
                    if resp.status_code == 200:
                        with open(img_path, "wb") as f:
                            for chunk in resp.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        success_count += 1
            except Exception:
                pass
        
        # Consider successful if at least one image downloaded
        return success_count > 0


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

        clear_proxy_env()
        browser = None
        try:
            self.status.emit("启动浏览器...")
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                    ],
                )
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=DOUYIN_UA,
                    locale="zh-CN",
                    timezone_id="Asia/Shanghai",
                )
                context.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
                )
                page = context.new_page()

                self.status.emit("打开抖音...")
                page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1500)

                cookies = context.cookies()
                if has_valid_login_cookie(cookies):
                    cookie_str = extract_login_cookies(context, page, self.status.emit)
                    if cookie_str:
                        self.done.emit(cookie_str)
                        browser.close()
                        return

                self.status.emit("获取二维码...")
                element = wait_for_qr_element(page, self.status.emit, timeout_sec=35)

                if not element:
                    self.error.emit("未找到二维码，请确认网络正常且页面未被拦截")
                    browser.close()
                    return

                try:
                    self.qr.emit(element.screenshot())
                except Exception:
                    self.error.emit("二维码截图失败")
                    browser.close()
                    return

                self.status.emit("等待扫码，请在手机上确认登录...")
                start_url = page.url

                for i in range(120):
                    cookies = context.cookies()
                    current_url = page.url

                    if has_valid_login_cookie(cookies):
                        cookie_str = extract_login_cookies(context, page, self.status.emit)
                        if cookie_str:
                            self.done.emit(cookie_str)
                            browser.close()
                            return

                    if is_logged_in_url(current_url) and current_url != start_url:
                        cookie_str = extract_login_cookies(context, page, self.status.emit)
                        if cookie_str:
                            self.done.emit(cookie_str)
                            browser.close()
                            return

                    try:
                        text = page.inner_text("body")
                        if "扫码成功" in text:
                            self.status.emit("扫码成功，请在手机上点击确认...")
                        elif any(k in text for k in ("登录成功", "已登录", "登录完成")):
                            cookie_str = extract_login_cookies(context, page, self.status.emit)
                            if cookie_str:
                                self.done.emit(cookie_str)
                                browser.close()
                                return
                    except Exception:
                        pass

                    if i % 5 == 0:
                        self.status.emit(f"等待扫码登录... ({i // 5 + 1}/24)")
                    page.wait_for_timeout(1000)

                self.error.emit("登录超时，请重试（扫码后需在手机上确认）")
                browser.close()
        except Exception as e:
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass
            self.error.emit(f"获取失败: {e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.parser = DouyinVideoParser()
        self.config = load_config()
        self.parser.set_cookie(self.config.get("cookie"))
        self.save_dir = self.config.get("save_dir", DEFAULT_SAVE_DIR)

        self.setWindowTitle("抖音无水印解析器 v2.0.4")
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
        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(["选择", "封面", "类型", "文案", "视频ID", "时间"])
        table.setColumnWidth(0, 60)
        table.setColumnWidth(1, 200)
        table.setColumnWidth(2, 100)
        table.setColumnWidth(3, 320)
        table.setColumnWidth(4, 180)
        table.setColumnWidth(5, 180)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
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
        content_type = info.get("content_type", "video")
        
        info_text = (
            f"ID: {info.get('aweme_id')}\n"
            f"类型: {'图集' if content_type == 'image' else '视频'}\n"
            f"时间: {format_time(info.get('create_time'))}\n"
            f"作者: {info.get('author_nickname')}\n"
            f"文案: {info.get('desc')}\n"
            f"封面: {info.get('cover_url')}\n"
        )
        
        if content_type == "video":
            qualities = info.get("qualities", [])
            qualities_text = ""
            if qualities:
                qualities_text = "\n可用质量: " + ", ".join([q.get("quality_label", q.get("ratio", "未知")) for q in qualities[:3]])
            info_text += f"无水印: {info.get('nwm_url')}" + qualities_text
            self.single_download_btn.setEnabled(bool(info.get("nwm_url") or qualities))
            self.single_download_btn.setProperty("nwm_url", info.get("nwm_url"))
            self.single_download_btn.setProperty("qualities", qualities)
        elif content_type == "image":
            image_count = info.get("image_count", 0)
            image_data = info.get("image_data", {})
            image_urls = image_data.get("image_urls", []) if image_data else []
            info_text += f"图片数量: {image_count}张"
            self.single_download_btn.setEnabled(bool(image_urls))
            self.single_download_btn.setProperty("image_data", image_data)
        
        self.single_info.setText(info_text)
        self.single_download_btn.setProperty("content_type", content_type)
        self.single_download_btn.setProperty("desc", info.get("desc"))
        self.single_download_btn.setProperty("aweme_id", info.get("aweme_id"))
        cover_url = info.get("cover_url")
        if cover_url:
            self._set_cover(self.single_cover, cover_url, 520, 300)

    def _single_error(self, msg: str):
        self.single_info.setText(msg)

    def _on_single_download(self):
        content_type = self.single_download_btn.property("content_type") or "video"
        
        if content_type == "video":
            # Video download
            qualities = self.single_download_btn.property("qualities") or []
            url = self.single_download_btn.property("nwm_url")
            
            # Show quality selection dialog if multiple qualities available
            selected_quality = None
            if qualities and len(qualities) > 1:
                dialog = QualitySelectionDialog(qualities, self)
                if dialog.exec() != QDialog.Accepted:
                    return
                selected_quality = dialog.get_selected_quality()
                if selected_quality:
                    url = selected_quality.get("url")
            elif not url and qualities:
                # Fallback to first quality if no default URL
                url = qualities[0].get("url")
            
            if not url:
                QMessageBox.warning(self, "错误", "未找到可用的视频地址")
                return
            
            os.makedirs(self.save_dir, exist_ok=True)
            desc = self.single_download_btn.property("desc") or ""
            aweme_id = self.single_download_btn.property("aweme_id") or "douyin"
            
            # Add quality suffix to filename if selected
            quality_suffix = ""
            if selected_quality:
                ratio = selected_quality.get("ratio", "")
                if ratio:
                    quality_suffix = f"_{ratio}"
            
            name = safe_filename(desc, aweme_id) + quality_suffix + ".mp4"
            path = os.path.join(self.save_dir, name)

            self.single_progress.setVisible(True)
            self.single_progress.setValue(0)

            def _cb(p):
                self.single_progress.setValue(p)

            ok = download_file(url, path, progress_cb=_cb)
            QMessageBox.information(self, "下载", "完成" if ok else "失败")
            self.single_progress.setVisible(False)
        
        elif content_type == "image":
            # Album download
            image_data = self.single_download_btn.property("image_data") or {}
            image_urls = image_data.get("image_urls", [])
            
            if not image_urls:
                QMessageBox.warning(self, "错误", "未找到可用的图片地址")
                return
            
            os.makedirs(self.save_dir, exist_ok=True)
            desc = self.single_download_btn.property("desc") or ""
            aweme_id = self.single_download_btn.property("aweme_id") or "douyin"
            
            # Create folder for album
            folder_name = safe_filename(desc, aweme_id)
            album_dir = os.path.join(self.save_dir, folder_name)
            os.makedirs(album_dir, exist_ok=True)
            
            self.single_progress.setVisible(True)
            self.single_progress.setRange(0, len(image_urls))
            self.single_progress.setValue(0)
            
            # Check if these are live images
            is_live = image_data.get("is_live", False)
            
            success = 0
            for idx, img_url in enumerate(image_urls, start=1):
                try:
                    # Determine file extension first
                    url_lower = img_url.lower()
                    if is_live:
                        # Live images are videos, save as mp4
                        ext = ".mp4"
                    elif ("gif" in url_lower or url_lower.endswith(".gif") or ".gif?" in url_lower):
                        ext = ".gif"
                    elif ("webp" in url_lower or url_lower.endswith(".webp") or ".webp?" in url_lower):
                        ext = ".webp"
                    elif ("png" in url_lower or url_lower.endswith(".png") or ".png?" in url_lower):
                        ext = ".png"
                    else:
                        ext = ".jpg"  # Default to jpg
                    
                    img_name = f"{idx:03d}{ext}"
                    img_path = os.path.join(album_dir, img_name)
                    
                    # For live images (MP4 videos), use download_file function for better support
                    if is_live:
                        def _cb(p):
                            self.single_progress.setValue(int((idx - 1) * 100 / len(image_urls) + p / len(image_urls)))
                        ok = download_file(img_url, img_path, progress_cb=_cb)
                        if ok:
                            success += 1
                    else:
                        # For static images, use simple download
                        resp = requests.get(img_url, timeout=30, stream=True, headers={"User-Agent": self.parser.user_agent})
                        if resp.status_code == 200:
                            with open(img_path, "wb") as f:
                                for chunk in resp.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                            success += 1
                except Exception:
                    pass
                
                self.single_progress.setValue(idx)
            
            QMessageBox.information(self, "下载", f"完成 {success}/{len(image_urls)}")
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
        video_infos = self._get_checked_video_infos(self.user_table)
        if not video_infos:
            QMessageBox.warning(self, "提示", "请先勾选要下载的内容")
            return
        
        # Filter videos only for quality selection
        video_only_infos = [info for info in video_infos if info.get("content_type", "video") == "video"]
        selected_ratio = None
        
        # Show quality selection dialog only if there are videos with multiple ratios
        if video_only_infos:
            available_ratios = self._get_all_available_ratios(video_only_infos)
            
            if available_ratios and len(available_ratios) > 1:
                # Create a simplified quality list for selection
                quality_list = []
                for ratio in available_ratios:
                    # Find a representative quality for this ratio
                    for info in video_only_infos:
                        qualities = info.get("qualities", [])
                        for q in qualities:
                            if q.get("ratio") == ratio:
                                quality_list.append(q)
                                break
                        if any(q.get("ratio") == ratio for q in qualities):
                            break
                
                if quality_list:
                    dialog = QualitySelectionDialog(quality_list, self)
                    dialog.setWindowTitle("选择批量下载的视频质量")
                    if dialog.exec() == QDialog.Accepted:
                        selected_quality = dialog.get_selected_quality()
                        if selected_quality:
                            selected_ratio = selected_quality.get("ratio")
                    else:
                        return
        
        self.user_progress.setVisible(True)
        self.user_progress.setValue(0)
        self.user_download_btn.setEnabled(False)

        self.download_worker = DownloadWorker(self.parser, video_infos, self.save_dir, selected_ratio)
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

    def _get_checked_video_infos(self, table: QTableWidget) -> list[dict]:
        """Get checked video info dicts instead of just URLs"""
        infos = []
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                info = item.data(Qt.UserRole)
                if info and isinstance(info, dict):
                    infos.append(info)
        return infos
    
    def _get_all_available_ratios(self, video_infos: list[dict]) -> set[str]:
        """Extract all available ratios from video infos"""
        ratios = set()
        for info in video_infos:
            qualities = info.get("qualities", [])
            for q in qualities:
                ratio = q.get("ratio")
                if ratio:
                    ratios.add(ratio)
        return sorted(ratios, key=lambda x: {"1080p": 5, "720p": 4, "540p": 3, "480p": 2, "360p": 1}.get(x, 0), reverse=True)

    def _append_row(self, table: QTableWidget, info: dict):
        row = table.rowCount()
        table.insertRow(row)
        table.setRowHeight(row, 110)

        check_item = QTableWidgetItem()
        check_item.setCheckState(Qt.Unchecked)
        # Store full info dict instead of just URL
        check_item.setData(Qt.UserRole, info)
        table.setItem(row, 0, check_item)

        cover_label = QLabel()
        cover_label.setFixedSize(180, 100)
        cover_label.setAlignment(Qt.AlignCenter)
        cover_label.setStyleSheet("background: #1b1f2a; border-radius: 6px;")
        if info.get("cover_url"):
            self._set_cover(cover_label, info["cover_url"], 180, 100)
        table.setCellWidget(row, 1, cover_label)

        # Content type column
        content_type = info.get("content_type", "video")
        type_text = "视频"
        if content_type == "image":
            image_count = info.get("image_count", 0)
            type_text = f"图集({image_count}张)"
        
        type_item = QTableWidgetItem(type_text)
        if content_type == "image":
            # Green background for albums
            type_item.setBackground(Qt.GlobalColor.darkGreen)
            type_item.setForeground(Qt.GlobalColor.white)
        table.setItem(row, 2, type_item)

        table.setItem(row, 3, QTableWidgetItem(info.get("desc") or ""))
        table.setItem(row, 4, QTableWidgetItem(info.get("aweme_id") or ""))
        table.setItem(row, 5, QTableWidgetItem(format_time(info.get("create_time"))))

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
        self.cookie_qr.clear()
        self.cookie_qr.setText("启动浏览器...")
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
        if not self.cookie_qr.pixmap():
            self.cookie_qr.setText(text)

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

