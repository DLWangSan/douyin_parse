"""
Douyin watermark-free video parser (requests + a_bogus + X-Bogus)
Input: share URL, Output: watermark-free video URL
"""

import re
import requests
from urllib.parse import quote

try:
    from abogus import ABogus
except Exception:
    ABogus = None

try:
    from xbogus import XBogus
except Exception:
    XBogus = None


class DouyinVideoParser:
    def __init__(self):
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/90.0.4430.212 Safari/537.36"
        )
        self.cookie = self._load_cookie()

    @staticmethod
    def _load_cookie():
        try:
            with open("douyin_cookie.txt", "r", encoding="utf-8") as f:
                return f.read().lstrip("\ufeff").strip()
        except FileNotFoundError:
            return ""

    def set_cookie(self, cookie: str):
        self.cookie = (cookie or "").lstrip("\ufeff").strip()

    def get_video_id(self, share_url: str) -> str | None:
        """从分享链接中提取视频ID，支持多种格式"""
        # 先尝试从文本中提取URL（处理复制时可能包含的文本、换行等）
        url_patterns = [
            r'https?://[^\s]+',  # 标准URL
            r'v\.douyin\.com/[^\s]+',  # 短链接
            r'douyin\.com/video/\d+',  # 直接视频链接
        ]
        
        extracted_url = None
        for pattern in url_patterns:
            match = re.search(pattern, share_url)
            if match:
                extracted_url = match.group(0)
                if not extracted_url.startswith('http'):
                    extracted_url = 'https://' + extracted_url
                break
        
        if not extracted_url:
            # 如果没有匹配到，尝试直接使用原字符串
            extracted_url = share_url.strip()
        
        # 如果已经是完整URL格式，直接提取ID
        direct_match = re.search(r'/video/(\d+)', extracted_url)
        if direct_match:
            return direct_match.group(1)
        
        # 否则尝试访问并获取重定向后的URL
        session = requests.Session()
        session.headers.update({
            "User-Agent": self.user_agent,
            "Referer": "https://www.douyin.com/"
        })
        try:
            resp = session.get(extracted_url, allow_redirects=True, timeout=10)
            real_url = resp.url
            match = re.search(r'/video/(\d+)', real_url)
            if match:
                return match.group(1)
            return None
        except Exception:
            return None

    def get_aweme_detail(self, video_id: str) -> dict | None:
        if ABogus is None:
            return None

        params = {
            "device_platform": "webapp",
            "aid": "6383",
            "channel": "channel_pc_web",
            "aweme_id": video_id,
            "pc_client_type": "1",
            "version_code": "290100",
            "version_name": "29.1.0",
            "cookie_enabled": "true",
            "browser_language": "zh-CN",
            "browser_platform": "Win32",
            "browser_name": "Chrome",
            "browser_version": "130.0.0.0",
            "browser_online": "true",
            "engine_name": "Blink",
            "engine_version": "130.0.0.0",
            "os_name": "Windows",
            "os_version": "10",
            "platform": "PC",
            "msToken": "",
        }

        try:
            a_bogus = ABogus().get_value(params)
            params["a_bogus"] = quote(a_bogus, safe="")
        except Exception:
            return None

        headers = {
            "User-Agent": self.user_agent,
            "Referer": f"https://www.douyin.com/video/{video_id}",
            "Accept": "application/json, text/plain, */*",
        }
        if self.cookie:
            headers["Cookie"] = self.cookie

        api_url = "https://www.douyin.com/aweme/v1/web/aweme/detail/"
        return self._request_json(api_url, params, headers)

    def _request_json(self, api_url: str, params: dict, headers: dict) -> dict | None:
        # 先试 a_bogus
        try:
            resp = requests.get(api_url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200 and resp.content:
                return resp.json()
        except Exception:
            pass

        # 再试 X-Bogus
        if XBogus is None:
            return None
        try:
            param_str = "&".join([f"{k}={v}" for k, v in params.items()])
            xb_value = XBogus(self.user_agent).getXBogus(param_str)
            xb_url = f"{api_url}?{param_str}&X-Bogus={xb_value[1]}"
            resp = requests.get(xb_url, headers=headers, timeout=10)
            if resp.status_code == 200 and resp.content:
                return resp.json()
        except Exception:
            return None

        return None

    @staticmethod
    def extract_nwm_url(data: dict) -> str | None:
        """Extract single watermark-free URL (backward compatibility)"""
        qualities = DouyinVideoParser.extract_video_qualities(data)
        if not qualities:
            return None
        # Return the highest quality URL by default
        return qualities[0]["url"]
    
    @staticmethod
    def extract_video_qualities(data: dict) -> list[dict]:
        """
        Extract all available video quality options
        Returns: List of dicts with keys: url, ratio, bit_rate, quality_label
        """
        aweme = data.get("aweme_detail") or {}
        video = aweme.get("video") or {}
        play_addr = video.get("play_addr") or {}
        bit_rate_list = video.get("bit_rate") or []
        uri = play_addr.get("uri")
        url_list = play_addr.get("url_list") or []
        
        qualities = []
        
        # Method 1: Extract from bit_rate list (most comprehensive)
        if bit_rate_list:
            for bit_rate_info in bit_rate_list:
                # Handle case where bit_rate_info might not be a dict
                if not isinstance(bit_rate_info, dict):
                    continue
                
                play_addr_br = bit_rate_info.get("play_addr") or {}
                url_list_br = play_addr_br.get("url_list") or []
                bit_rate = bit_rate_info.get("bit_rate", 0)
                gear_name = bit_rate_info.get("gear_name", "")
                
                # Extract ratio from quality_type (handle both dict and int cases)
                ratio = ""
                quality_type = bit_rate_info.get("quality_type")
                if isinstance(quality_type, dict):
                    ratio = quality_type.get("name", "")
                elif isinstance(quality_type, (int, str)):
                    # If quality_type is a number or string, try to parse it
                    quality_str = str(quality_type)
                    ratio_match = re.search(r'(\d+p)', quality_str.lower())
                    if ratio_match:
                        ratio = ratio_match.group(1)
                
                # Parse ratio from gear_name if not found
                if not ratio and gear_name:
                    ratio_match = re.search(r'(\d+p)', gear_name.lower())
                    if ratio_match:
                        ratio = ratio_match.group(1)
                
                # If no ratio found, try to infer from bit_rate
                if not ratio:
                    if bit_rate >= 2000000:  # ~2Mbps or higher
                        ratio = "1080p"
                    elif bit_rate >= 1000000:  # ~1Mbps or higher
                        ratio = "720p"
                    elif bit_rate >= 500000:  # ~500kbps or higher
                        ratio = "540p"
                    else:
                        ratio = "480p"
                
                if url_list_br:
                    for url in url_list_br:
                        nwm_url = url.replace("playwm", "play")
                        quality_label = f"{ratio} ({bit_rate // 1000}Kbps)" if bit_rate else ratio
                        qualities.append({
                            "url": nwm_url,
                            "ratio": ratio,
                            "bit_rate": bit_rate,
                            "quality_label": quality_label,
                            "gear_name": gear_name,
                        })
        
        # Method 2: Extract from play_addr url_list (fallback)
        if not qualities and url_list:
            for url in url_list:
                nwm_url = url.replace("playwm", "play")
                # Try to extract ratio from URL
                ratio_match = re.search(r'ratio=(\d+p)', url.lower())
                ratio = ratio_match.group(1) if ratio_match else "1080p"
                qualities.append({
                    "url": nwm_url,
                    "ratio": ratio,
                    "bit_rate": 0,
                    "quality_label": ratio,
                    "gear_name": "",
                })
        
        # Method 3: Construct from uri with different ratios (last resort)
        if not qualities and uri:
            # Try common ratios
            for ratio in ["1080p", "720p", "540p", "480p", "360p"]:
                nwm_url = f"https://aweme.snssdk.com/aweme/v1/play/?video_id={uri}&ratio={ratio}&line=0"
                qualities.append({
                    "url": nwm_url,
                    "ratio": ratio,
                    "bit_rate": 0,
                    "quality_label": ratio,
                    "gear_name": "",
                })
        
        # Remove duplicates and sort by quality (highest first)
        seen_urls = set()
        unique_qualities = []
        for q in qualities:
            if q["url"] not in seen_urls:
                seen_urls.add(q["url"])
                unique_qualities.append(q)
        
        # Sort by bit_rate descending, then by ratio (1080p > 720p > ...)
        def sort_key(q):
            ratio_order = {"1080p": 5, "720p": 4, "540p": 3, "480p": 2, "360p": 1}
            return (q["bit_rate"], ratio_order.get(q["ratio"], 0))
        
        unique_qualities.sort(key=sort_key, reverse=True)
        
        return unique_qualities

    @staticmethod
    def extract_video_meta(data: dict) -> dict:
        aweme = data.get("aweme_detail") or {}
        author = aweme.get("author") or {}
        video = aweme.get("video") or {}
        cover = video.get("cover") or {}
        cover_list = cover.get("url_list") or []
        return {
            "aweme_id": aweme.get("aweme_id"),
            "desc": aweme.get("desc"),
            "create_time": aweme.get("create_time"),
            "author_nickname": author.get("nickname"),
            "author_sec_uid": author.get("sec_uid"),
            "cover_url": cover_list[0] if cover_list else None,
        }

    def parse_to_nwm_url(self, share_url: str) -> str | None:
        video_id = self.get_video_id(share_url)
        if not video_id:
            return None
        data = self.get_aweme_detail(video_id)
        if not data:
            return None
        return self.extract_nwm_url(data)

    def parse_video(self, share_url: str) -> dict | None:
        """返回完整解析结果（无水印地址 + 基本信息 + 所有质量选项）"""
        video_id = self.get_video_id(share_url)
        if not video_id:
            return None
        data = self.get_aweme_detail(video_id)
        if not data:
            return None
        nwm_url = self.extract_nwm_url(data)
        qualities = self.extract_video_qualities(data)
        meta = self.extract_video_meta(data)
        return {
            "nwm_url": nwm_url,
            "qualities": qualities,
            **meta,
        }

    def parse_video_meta(self, share_url: str) -> dict | None:
        """仅解析视频基础信息（不计算无水印地址）"""
        video_id = self.get_video_id(share_url)
        if not video_id:
            return None
        data = self.get_aweme_detail(video_id)
        if not data:
            return None
        return self.extract_video_meta(data)

    def get_user_home_from_video_url(self, share_url: str) -> str | None:
        video_id = self.get_video_id(share_url)
        if not video_id:
            return None
        data = self.get_aweme_detail(video_id)
        if not data:
            return None
        aweme = data.get("aweme_detail") or {}
        author = aweme.get("author") or {}
        sec_uid = author.get("sec_uid")
        if not sec_uid:
            return None
        return f"https://www.douyin.com/user/{sec_uid}"

    def get_user_aweme_urls_from_video_url(
        self,
        share_url: str,
        max_pages: int = 10,
        count: int = 20
    ) -> list[str]:
        user_home = self.get_user_home_from_video_url(share_url)
        if not user_home:
            return []
        return self.get_user_aweme_urls(user_home, max_pages=max_pages, count=count)

    @staticmethod
    def get_sec_uid(user_url: str) -> str | None:
        """从用户链接中提取sec_uid，支持多种格式"""
        # 先尝试从文本中提取URL
        url_patterns = [
            r'https?://[^\s]+',  # 标准URL
            r'douyin\.com/user/[^\s]+',  # 用户主页链接
        ]
        
        extracted_url = None
        for pattern in url_patterns:
            match = re.search(pattern, user_url)
            if match:
                extracted_url = match.group(0)
                if not extracted_url.startswith('http'):
                    extracted_url = 'https://' + extracted_url
                break
        
        if not extracted_url:
            extracted_url = user_url.strip()
        
        # 尝试多种匹配模式
        patterns = [
            r"/user/([^/?\s]+)",  # /user/MS4wLjAB...
            r"sec_uid=([^&\s]+)",  # sec_uid=MS4wLjAB...
            r"user/([^/?\s]+)",   # user/MS4wLjAB... (无前导斜杠)
        ]
        
        for pattern in patterns:
            m = re.search(pattern, extracted_url)
            if m:
                return m.group(1)
        
        return None

    def get_user_aweme_urls(
        self,
        user_url: str,
        max_pages: int = 10,
        count: int = 20
    ) -> list[str]:
        sec_uid = self.get_sec_uid(user_url)
        if not sec_uid:
            return []

        headers = {
            "User-Agent": self.user_agent,
            "Referer": "https://www.douyin.com/",
            "Accept": "application/json, text/plain, */*",
        }
        if self.cookie:
            headers["Cookie"] = self.cookie

        api_url = "https://www.douyin.com/aweme/v1/web/aweme/post/"
        max_cursor = 0
        urls = []
        seen = set()

        for _ in range(max_pages):
            params = {
                "device_platform": "webapp",
                "aid": "6383",
                "channel": "channel_pc_web",
                "sec_user_id": sec_uid,
                "max_cursor": str(max_cursor),
                "count": str(count),
                "locate_query": "false",
                "show_live_replay_strategy": "1",
                "need_time_list": "1",
                "time_list_query": "0",
                "whale_cut_token": "",
                "cut_version": "1",
                "publish_video_strategy_type": "2",
                "pc_client_type": "1",
                "version_code": "290100",
                "version_name": "29.1.0",
                "cookie_enabled": "true",
                "screen_width": "1920",
                "screen_height": "1080",
                "browser_language": "zh-CN",
                "browser_platform": "Win32",
                "browser_name": "Chrome",
                "browser_version": "130.0.0.0",
                "browser_online": "true",
                "engine_name": "Blink",
                "engine_version": "130.0.0.0",
                "os_name": "Windows",
                "os_version": "10",
                "cpu_core_num": "12",
                "device_memory": "8",
                "platform": "PC",
                "downlink": "10",
                "effective_type": "4g",
                "round_trip_time": "50",
                "msToken": "",
            }
            if ABogus is not None:
                try:
                    a_bogus = ABogus().get_value(params)
                    params["a_bogus"] = quote(a_bogus, safe="")
                except Exception:
                    pass

            data = self._request_json(api_url, params, headers)
            if not data:
                break

            aweme_list = data.get("aweme_list") or []
            for aweme in aweme_list:
                aweme_id = aweme.get("aweme_id")
                if aweme_id:
                    url = f"https://www.douyin.com/video/{aweme_id}"
                    if url not in seen:
                        seen.add(url)
                        urls.append(url)

            if not data.get("has_more"):
                break
            max_cursor = data.get("max_cursor") or 0

        return urls


def get_nwm_url(share_url: str) -> str | None:
    """简化调用：输入分享链接，输出无水印真实地址"""
    return DouyinVideoParser().parse_to_nwm_url(share_url)

