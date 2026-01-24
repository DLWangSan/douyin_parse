"""
Douyin Video Downloader - Qt6 GUI Application (Slim Version)
Slim version without auto cookie acquisition, requires manual cookie import
"""
import os

os.environ["DISABLE_LOGIN"] = "1"

from qt_app import main


if __name__ == "__main__":
    main()



