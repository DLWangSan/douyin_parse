"""
抖音 X-Bogus 签名算法 (纯 Python 实现)

基于 Evil0ctal/Douyin_TikTok_Download_API 项目 (Apache 2.0)
https://github.com/Evil0ctal/Douyin_TikTok_Download_API
"""

import time
import base64
import hashlib


class XBogus:
    """生成抖音 API 请求所需的 X-Bogus 签名参数"""

    def __init__(self, user_agent: str = None) -> None:
        # 字符映射表: '0'-'9' (48-57) → 0-9, 'a'-'f' (97-102) → 10-15
        self._char_map = [None] * 128
        for i in range(10):
            self._char_map[48 + i] = i  # '0'-'9' → 0-9
        for i in range(6):
            self._char_map[97 + i] = 10 + i  # 'a'-'f' → 10-15
        self._charset = "Dkdpgh4ZKsQB80/Mfvw36XI1R25-WUAlEi7NLboqYTOPuzmFjJnryx9HVGcaStCe="
        self._ua_key = b"\x00\x01\x0c"
        self.user_agent = (
            user_agent
            if user_agent
            else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
        )

    def _md5_str_to_array(self, md5_str: str) -> list:
        """将 MD5 字符串转换为字节数组"""
        if len(md5_str) > 32:
            return [ord(c) for c in md5_str]

        arr = []
        for i in range(0, len(md5_str), 2):
            high = self._char_map[ord(md5_str[i])]
            low = self._char_map[ord(md5_str[i + 1])]
            arr.append((high << 4) | low)
        return arr

    def _md5(self, data) -> str:
        """计算 MD5 哈希"""
        if isinstance(data, str):
            # 字符串 → 用 ord() 转为字节数组 (兼容任意长度)
            arr = [ord(c) for c in data]
        elif isinstance(data, list):
            arr = data
        else:
            raise ValueError("Invalid input type")
        return hashlib.md5(bytes(arr)).hexdigest()

    def _md5_encrypt(self, url_path: str) -> list:
        """对 URL 路径进行双重 MD5 加密"""
        first_md5 = self._md5(url_path)
        second_md5 = self._md5(self._md5_str_to_array(first_md5))
        return self._md5_str_to_array(second_md5)

    def _encoding_conversion(self, a, b, c, e, d, t, f, r, n, o, i, _, x, u, s, l, v, h, p):
        """编码转换 - 将字节列表转为 ISO-8859-1 字符串

        注意: 参数顺序是原算法的关键，必须严格匹配。
        浮点数 0.00390625 会落在参数 i 上，被 int(i) 处理。
        """
        y = [a]
        y.append(int(i))
        y.extend([b, _, c, x, e, u, d, s, t, l, f, v, r, h, n, p, o])
        return bytes(y).decode("ISO-8859-1")

    @staticmethod
    def _encoding_conversion2(a: int, b: int, c: str) -> str:
        """编码转换辅助"""
        return chr(a) + chr(b) + c

    @staticmethod
    def _rc4_encrypt(key: bytes, data: bytes) -> bytearray:
        """RC4 加密"""
        S = list(range(256))
        j = 0
        for i in range(256):
            j = (j + S[i] + key[i % len(key)]) % 256
            S[i], S[j] = S[j], S[i]

        i = j = 0
        encrypted = bytearray()
        for byte in data:
            i = (i + 1) % 256
            j = (j + S[i]) % 256
            S[i], S[j] = S[j], S[i]
            encrypted.append(byte ^ S[(S[i] + S[j]) % 256])
        return encrypted

    def _calc(self, a1: int, a2: int, a3: int) -> str:
        """生成最终编码的 4 字符块"""
        x = ((a1 & 255) << 16) | ((a2 & 255) << 8) | a3
        return (self._charset[(x >> 18) & 63] +
                self._charset[(x >> 12) & 63] +
                self._charset[(x >> 6) & 63] +
                self._charset[x & 63])

    def get_xbogus(self, url_path: str) -> tuple:
        """
        生成 X-Bogus 签名

        Args:
            url_path: 完整的请求 URL 或 URL 参数字符串

        Returns:
            (带 X-Bogus 的完整参数字符串, X-Bogus 值, User-Agent)
        """
        # 生成三个密钥数组
        rc4_encrypted = self._rc4_encrypt(
            self._ua_key,
            self.user_agent.encode("ISO-8859-1")
        )
        array1 = self._md5_str_to_array(
            self._md5(base64.b64encode(rc4_encrypted).decode("ISO-8859-1"))
        )

        array2 = self._md5_str_to_array(
            self._md5(self._md5_str_to_array("d41d8cd98f00b204e9800998ecf8427e"))
        )

        url_path_array = self._md5_encrypt(url_path)

        # 时间戳和常量
        timer = int(time.time())
        ct = 536919696

        # 构建新数组
        new_array = [
            64, 0.00390625, 1, 12,
            url_path_array[14], url_path_array[15],
            array2[14], array2[15],
            array1[14], array1[15],
            (timer >> 24) & 255, (timer >> 16) & 255,
            (timer >> 8) & 255, timer & 255,
            (ct >> 24) & 255, (ct >> 16) & 255,
            (ct >> 8) & 255, ct & 255,
        ]

        # 异或校验
        xor_result = new_array[0]
        for i in range(1, len(new_array)):
            b = new_array[i]
            if isinstance(b, float):
                b = int(b)
            xor_result ^= b
        new_array.append(xor_result)

        # 拆分奇偶位
        array3 = [new_array[i] for i in range(0, len(new_array), 2)]
        array4 = [new_array[i] for i in range(1, len(new_array), 2)]
        merge_array = array3 + array4

        # RC4 加密 + 编码
        garbled = self._encoding_conversion2(
            2, 255,
            self._rc4_encrypt(
                b"\xff",
                self._encoding_conversion(*merge_array).encode("ISO-8859-1"),
            ).decode("ISO-8859-1"),
        )

        # 最终编码
        xb = ""
        for i in range(0, len(garbled), 3):
            xb += self._calc(
                ord(garbled[i]),
                ord(garbled[i + 1]),
                ord(garbled[i + 2]),
            )

        result = f"{url_path}&X-Bogus={xb}"
        return result, xb, self.user_agent

    # 兼容旧调用名
    getXBogus = get_xbogus


if __name__ == "__main__":
    # 测试
    test_url = (
        "https://www.douyin.com/aweme/v1/web/aweme/post/"
        "?device_platform=webapp&aid=6383&channel=channel_pc_web"
        "&sec_user_id=MS4wLjABAAAAW9FWcqS7RdQAWPd2AA5fL_ilmqsIFUCQ_Iym6Yh9_cU"
        "&max_cursor=0&count=18"
    )
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    xb = XBogus(user_agent=ua)
    result = xb.get_xbogus(test_url)
    print(f"X-Bogus: {result[1]}")
    print(f"完整URL: {result[0][:100]}...")
