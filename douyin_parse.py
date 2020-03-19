import os
import sys
import time

import requests
from PyQt5 import QtCore
from lxml import etree
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import *

from qianfeng.shizhan.parse_douyin.ui import Ui_MainWindow

ua_phone = 'Mozilla/5.0 (Linux; Android 6.0; ' \
         'Nexus 5 Build/MRA58N) AppleWebKit/537.36 (' \
         'KHTML, like Gecko) Chrome/80.0.3987.116 Mobile Safari/537.36'
ua_win = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' \
         'AppleWebKit/537.36 (KHTML, like Gecko) ' \
         'Chrome/80.0.3987.116 Safari/537.36'


# 以指定ua发起get请求
def get_resp(url, ua):
    headers = {
        'User-Agent': ua
    }
    resp = requests.get(url, headers=headers)
    if resp:
        return resp
    else:
        log_tab.insertPlainText(
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ':\n' + '链接错误！' + '\n\n')
        link_text.clear()


# 下载视频用
def get_resp_video(url):
    headers = {
        'User-Agent': ua_phone
    }
    resp = requests.get(url, headers=headers, stream=True)
    return resp


# 从script中获取真实视频地址
def findUrlInScript(script):
    test = script.split('playAddr: "', 1)
    test = test[1].split('",', 1)
    like_link = test[0]
    link = like_link.replace('playwm', 'play').strip()
    return link


# 链接处理，包含重定向
def parse_shareLink(link):
    resp = get_resp(link, ua_win)
    # 获取重定向之后的地址
    re_link = resp.url
    re_resp = get_resp(re_link, ua_win)
    et = etree.HTML(re_resp.text)
    # 获取链接
    script = et.xpath("/html/body/div/script[3]/text()")[0]
    script = (str(script))
    # 获取id及content组成文件名
    id = et.xpath("//*[@id='pageletReflowVideo']/div/div[2]/div[2]/div/div[2]/p/text()")[0].split('@')[1]
    content = et.xpath("//*[@id='pageletReflowVideo']/div/div[2]/div[2]/p/text()")[0]
    content = content.split('#')[0].split(',')[0].split('。')[0].split('?')[0].split('？')[0].split('，')[0].split('!')[0].split('！')[0]
    name = id + '：' + content + '.mp4'
    return name, findUrlInScript(script)


# 下载
def download(path, video_url, file_name):
    if not os.path.exists(path):
        os.mkdir(os.getcwd() + '\\douyin_download')
        log_tab.insertPlainText(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ':\n' + '正在创建下载文件夹：douyin_download' + '\n\n')
    os.chdir(path)
    log_tab.insertPlainText(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ':\n' + file_name + '开始下载...' + '\n\n')
    r = get_resp_video(video_url)
    link_text.clear()
    with open(file_name, 'wb') as mp4:
        print(file_name)
        for trunk in r.iter_content(chunk_size=1024 * 1024):
            if trunk:
                mp4.write(trunk)
    os.system('explorer.exe /n, %s' % os.getcwd())
    log_tab.insertPlainText(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ':\n' + file_name + '下载完成！' + '\n\n')


def download_click():
    log_tab.insertPlainText(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ':\n' +
                            link_text.toPlainText() + '\n')
    share_link = link_text.toPlainText()
    name, _url = parse_shareLink(share_link)
    resp = get_resp(_url, ua_phone)
    # 获取最终下载地址
    last_url = resp.url
    download('./douyin_download', last_url, name)
    os.chdir('..')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    MainWindow = QMainWindow()
    MainWindow.setFixedSize(438, 303)
    MainWindow.show()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    log_tab = ui.plainTextEdit
    link_text = ui.textEdit
    download_button = ui.pushButton_2
    download_button.clicked.connect(lambda: download_click())





    # print(MainWindow.width(),MainWindow.height())
    sys.exit(app.exec_())




