"""
抖音 A-Bogus 签名算法 (纯 Python 实现)

用于抖音新版 Web API 的签名参数生成。
基于 Evil0ctal/Douyin_TikTok_Download_API 项目中的实现修改。
原始实现来自 JoeanAmier/TikTokDownloader (GPL v3)。

需要 gmssl 库提供 SM3 哈希支持。
"""

from random import choice, randint, random
from re import compile as re_compile
from time import time
from urllib.parse import urlencode, quote
from gmssl import sm3, func

__all__ = ["ABogus"]


class ABogus:
    """生成抖音 API 请求所需的 A-Bogus 签名参数"""

    _url_encode_filter = re_compile(r"%([0-9A-F]{2})")
    _arguments = [0, 1, 14]
    _ua_key = "\x00\x01\x0e"
    _end_string = "cus"
    _version = [1, 0, 1, 5]
    _browser = "1536|742|1536|864|0|0|0|0|1536|864|1536|864|1536|742|24|24|MacIntel"
    _reg_init = [
        1937774191, 1226093241, 388252375, 3666478592,
        2842636476, 372324522, 3817729613, 2969243214,
    ]
    _charsets = {
        "s0": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=",
        "s1": "Dkdpgh4ZKsQB80/Mfvw36XI1R25+WUAlEi7NLboqYTOPuzmFjJnryx9HVGcaStCe=",
        "s2": "Dkdpgh4ZKsQB80/Mfvw36XI1R25-WUAlEi7NLboqYTOPuzmFjJnryx9HVGcaStCe=",
        "s3": "ckdp1h4ZKsUB80/Mfvw36XIgR25+WQAlEi7NLboqYTOPuzmFjJnryx9HVGDaStCe",
        "s4": "Dkdpgh2ZmsQB80/MfvV36XI1R45-WUAlEixNLwoqYTOPuzKFjJnry79HbGcaStCe",
    }

    def __init__(self, platform: str = None):
        self.chunk = []
        self.size = 0
        self.reg = self._reg_init[:]

        # UA 特征码 (需要根据实际使用的 User-Agent 调整)
        self.ua_code = [
            76, 98, 15, 131, 97, 245, 224, 133, 122, 199,
            241, 166, 79, 34, 90, 191, 128, 126, 122, 98,
            66, 11, 14, 40, 49, 110, 110, 173, 67, 96, 138, 252,
        ]

        self.browser = self._generate_browser_info(platform) if platform else self._browser
        self.browser_len = len(self.browser)
        self.browser_code = self._char_code_at(self.browser)

    # ---- 随机数生成 ----

    @classmethod
    def _list_1(cls, random_num=None, a=170, b=85, c=45):
        return cls._random_list(random_num, a, b, 1, 2, 5, c & a)

    @classmethod
    def _list_2(cls, random_num=None, a=170, b=85):
        return cls._random_list(random_num, a, b, 1, 0, 0, 0)

    @classmethod
    def _list_3(cls, random_num=None, a=170, b=85):
        return cls._random_list(random_num, a, b, 1, 0, 5, 0)

    @staticmethod
    def _random_list(a=None, b=170, c=85, d=0, e=0, f=0, g=0):
        r = a if a is not None else (random() * 10000)
        v = [r, int(r) & 255, int(r) >> 8]
        return [
            v[1] & b | d,
            v[1] & c | e,
            v[2] & b | f,
            v[2] & c | g,
        ]

    @staticmethod
    def _from_char_code(*args):
        return "".join(chr(code) for code in args)

    def _generate_string_1(self, r1=None, r2=None, r3=None):
        return (self._from_char_code(*self._list_1(r1)) +
                self._from_char_code(*self._list_2(r2)) +
                self._from_char_code(*self._list_3(r3)))

    # ---- 字符串 2 生成 ----

    def _generate_string_2(self, url_params: str, method="GET",
                           start_time=0, end_time=0) -> str:
        a = self._list_4_list(url_params, method, start_time, end_time)
        e = self._end_check_num(a)
        a.extend(self.browser_code)
        a.append(e)
        return self._rc4_encrypt(self._from_char_code(*a), "y")

    def _list_4_list(self, url_params: str, method="GET",
                     start_time=0, end_time=0) -> list:
        start_time = start_time or int(time() * 1000)
        end_time = end_time or (start_time + randint(4, 8))
        params_arr = self._generate_params_code(url_params)
        method_arr = self._generate_method_code(method)
        return self._list_4(
            (end_time >> 24) & 255, params_arr[21], self.ua_code[23],
            (end_time >> 16) & 255, params_arr[22], self.ua_code[24],
            (end_time >> 8) & 255, (end_time >> 0) & 255,
            (start_time >> 24) & 255, (start_time >> 16) & 255,
            (start_time >> 8) & 255, (start_time >> 0) & 255,
            method_arr[21], method_arr[22],
            (end_time // 256 // 256 // 256 // 256) & 0xFF,
            (start_time // 256 // 256 // 256 // 256) & 0xFF,
            self.browser_len,
        )

    @staticmethod
    def _list_4(a, b, c, d, e, f, g, h, i, j, k, m, n, o, p, q, r):
        return [
            44, a, 0, 0, 0, 0, 24, b, n, 0, c, d, 0, 0, 0, 1, 0, 239,
            e, o, f, g, 0, 0, 0, 0, h, 0, 0, 14, i, j, 0, k, m, 3, p, 1,
            q, 1, r, 0, 0, 0,
        ]

    # ---- SM3 哈希相关 ----

    @classmethod
    def _generate_method_code(cls, method: str) -> list:
        return cls._sm3_to_array(cls._sm3_to_array(method + cls._end_string))

    def _generate_params_code(self, params: str) -> list:
        return self._sm3_to_array(self._sm3_to_array(params + self._end_string))

    @classmethod
    def _sm3_to_array(cls, data) -> list:
        if isinstance(data, str):
            b = data.encode("utf-8")
        else:
            b = bytes(data)
        h = sm3.sm3_hash(func.bytes_to_list(b))
        return [int(h[i:i + 2], 16) for i in range(0, len(h), 2)]

    # ---- 工具方法 ----

    @staticmethod
    def _end_check_num(arr: list) -> int:
        r = 0
        for i in arr:
            r ^= i
        return r

    @staticmethod
    def _char_code_at(s: str) -> list:
        return [ord(c) for c in s]

    @staticmethod
    def _rc4_encrypt(plaintext: str, key: str) -> str:
        s = list(range(256))
        j = 0
        for i in range(256):
            j = (j + s[i] + ord(key[i % len(key)])) % 256
            s[i], s[j] = s[j], s[i]
        i = j = 0
        result = []
        for ch in plaintext:
            i = (i + 1) % 256
            j = (j + s[i]) % 256
            s[i], s[j] = s[j], s[i]
            t = (s[i] + s[j]) % 256
            result.append(chr(s[t] ^ ord(ch)))
        return "".join(result)

    @staticmethod
    def _generate_browser_info(platform: str) -> str:
        inner_w = randint(1280, 1920)
        inner_h = randint(720, 1080)
        outer_w = randint(inner_w, 1920)
        outer_h = randint(inner_h, 1080)
        values = [
            inner_w, inner_h, outer_w, outer_h,
            0, choice((0, 30)), 0, 0,
            outer_w, outer_h, outer_w, outer_h,
            inner_w, inner_h, 24, 24,
            platform,
        ]
        return "|".join(str(v) for v in values)

    # ---- 结果编码 ----

    @classmethod
    def _generate_result(cls, s: str, charset="s4") -> str:
        cs = cls._charsets[charset]
        result = []
        for i in range(0, len(s), 3):
            remaining = len(s) - i
            if remaining >= 3:
                n = (ord(s[i]) << 16) | (ord(s[i + 1]) << 8) | ord(s[i + 2])
                result.append(cs[(n >> 18) & 63])
                result.append(cs[(n >> 12) & 63])
                result.append(cs[(n >> 6) & 63])
                result.append(cs[n & 63])
            elif remaining == 2:
                n = (ord(s[i]) << 16) | (ord(s[i + 1]) << 8)
                result.append(cs[(n >> 18) & 63])
                result.append(cs[(n >> 12) & 63])
                result.append(cs[(n >> 6) & 63])
            else:
                n = ord(s[i]) << 16
                result.append(cs[(n >> 18) & 63])
                result.append(cs[(n >> 12) & 63])
        # 补等号
        padding = (4 - len(result) % 4) % 4
        result.append("=" * padding)
        return "".join(result)

    # ---- 主接口 ----

    def get_value(self, url_params, method="GET",
                  start_time=0, end_time=0,
                  random_num_1=None, random_num_2=None, random_num_3=None) -> str:
        """
        生成 A-Bogus 签名

        Args:
            url_params: dict 或 str 类型的 URL 参数
            method: HTTP 方法 (GET/POST)
            start_time: 起始时间戳 (毫秒)
            end_time: 结束时间戳 (毫秒)

        Returns:
            A-Bogus 签名字符串 (需 URL 编码后使用)
        """
        if isinstance(url_params, dict):
            url_params = urlencode(url_params)

        string_1 = self._generate_string_1(random_num_1, random_num_2, random_num_3)
        string_2 = self._generate_string_2(url_params, method, start_time, end_time)
        combined = string_1 + string_2
        return self._generate_result(combined, "s4")


if __name__ == "__main__":
    # 测试
    import json

    bogus = ABogus()
    test_params = {
        "device_platform": "webapp",
        "aid": "6383",
        "channel": "channel_pc_web",
        "pc_client_type": "1",
        "version_code": "190500",
        "version_name": "19.5.0",
        "cookie_enabled": "true",
        "browser_language": "zh-CN",
        "browser_platform": "Win32",
        "browser_name": "Firefox",
        "browser_online": "true",
        "engine_name": "Gecko",
        "os_name": "Windows",
        "os_version": "10",
        "platform": "PC",
        "screen_width": "1920",
        "screen_height": "1080",
        "cpu_core_num": "12",
        "aweme_id": "7345492945006595379",
    }
    a_bogus = bogus.get_value(test_params)
    print(f"A-Bogus: {quote(a_bogus, safe='')}")
