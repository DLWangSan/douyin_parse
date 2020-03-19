# douyin_parse
抖音短视频解析
在网上看过一些论坛帖，有一些解析抖音无水印视频的教程。说是教程，其实大部分都是提供接口，或引流或卖接口。我想看看究竟是怎么实现的去水印。立帖记录全过程。

## 1.浏览器分析
从抖音短视频中分享一段视频。可以得到：

> \#在抖音，记录美好生活#再见，武汉！战“疫”英雄要回家了。一路平安~https://v.douyin.com/WuRMPV/ 复制此链接，打开【抖音短视频】，直接观看视频！

我将这段文字中的链接部分复制下来，在浏览器打开。并使用开发者工具调试。

![浏览器打开初始链接](https://upload-images.jianshu.io/upload_images/13604849-07dfb8fb61b824bd.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

可以看到在video标签中存在一个链接。
```
https://aweme.snssdk.com/aweme/v1/playwm/?video_id=v0200fba0000bpo4s1b82vu9dp4ehlog&line=0
```
复制该链接在浏览器打开：
![直接打开src链接](https://upload-images.jianshu.io/upload_images/13604849-f36ff52b59fbd569.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

发现仍然是带水印的视频，而且页面重定向成了新地址：
```
http://v6-dy-y.ixigua.com
/8d090338ca04948b648bb7e4ba0b215f/5e72da81/video/tos/hxsy/tos-hxsy-ve-0015/832e6e52408d4c1e931b763b152e5d21
/?a=1128&br=0&bt=2405&cr=0&cs=0&dr=0&ds=3&er=&l=202003190935350101940982142734B1FC&lr=aweme&qs=0&rc=am9oc
zx5OzQ3czMzZGkzM0ApODVpNzk8OWRmNzVnM2g1N2dsZTFhci9fcGxfLS1fLS9zczM0Yl8vMzVfYGBhNmItYTE6Yw%3D%3D&vl=&vr=
```

分析之前的地址：

###  **https**://aweme**.snssdk.com**/aweme/v1/**playwm**/?video_id=v0200fba0000bpo4s1b82vu9dp4ehlog&line=0

包含**playwm** 后面的wm是什么意思？将**playwm**改成**play**，并将请求的User-Agent修改为手机。便得到了无水印版本的视频。手动操作部分结束！

![无水印视频](https://upload-images.jianshu.io/upload_images/13604849-b7a9a1bd21f8c49c.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)


## 2. 代码实现

先测试一下下载流媒体。
```python
def download(video_url, file_name):
    r = get_resp(video_url)
    with open(file_name, 'wb') as mp4:
        for trunk in r.iter_content(1024 * 1024):
            if trunk:
                mp4.write(trunk)
```
调用之后可以正常下载视频。所以可以放心写爬虫获取到这个真实地址了。剩下的按照第一步的手动操作即可。

遇到了一个大问题，即在初始页面上没有视频地址，必须点击一下按钮，才会跳出。故直接用XPATH会找不到要的链接。怎么办呢？首先想到模拟点击，但是这样我就需要使用**selenium**（或许有更好的办法我想不到），这样就会让程序庞大不少。非我所愿。
仔细观察页面，发现页面下方的js有这样一段：
```javascript
$(function(){
            require('web:component/reflow_video/index').create({
                hasData: 1,
                videoWidth: 720,
                videoHeight: 1280,
                playAddr: "https://aweme.snssdk.com/aweme/v1/playwm/?s_vid=93f1b41336a8b7a442dbf1c29c6bbc561699c13ffb2ce3cacb960e9bcb7c0b8f9f0ec410108d165bd0bfd2b83c1070676ccafc940fd5dc933ea73704a90e4faf&line=0",
                cover: "https://p3.pstatp.com/large/tos-cn-p-0015/584d6a06932940998a1decc057ab2978_1584418313.jpg"

            });
        });
```

这不就把地址封面直接给我了吗。实在有种“得来全不费功夫”的感觉！
写一个函数来解析js：
```python
# 从script中获取真实视频地址
def findUrlInScript(script):
    test = script.split('playAddr: "', 1)
    test = test[1].split('",', 1)
    like_link = test[0]
    link = like_link.replace('playwm', 'play').strip()
    return link
```
给文件命名：
```
    id = et.xpath("//*[@id='pageletReflowVideo']/div/div[2]/div[2]/div/div[2]/p/text()")[0].split('@')[1]
    content = et.xpath("//*[@id='pageletReflowVideo']/div/div[2]/div[2]/p/text()")[0]
    content = content.split('#')[0].split(',')[0].split('。')[0].split('?')[0].split('？')[0].split('，')[0].split('!')[0].split('！')[0]
    name = id + '：' + content + '.mp4'
```

随便测试一个，已经可以下载到根目录了。为了工整，还是创建一个文件夹用于保存吧~
```python
    if not os.path.exists(path):
        os.mkdir(os.getcwd() + '\\douyin_download')
    os.chdir(path)
```
调用download的时，加一个路径的参数即可。测试成功！
![下载成功图](https://upload-images.jianshu.io/upload_images/13604849-f3c86610d7ceeb6e.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)


![无水印](https://upload-images.jianshu.io/upload_images/13604849-2ff6e764d30e6b1e.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

测试确实把水印去了，至此，核心功能已经全部实现，编写总代码~~~

## 3. 最后一步 封装
从来没有用过python的用户界面，但是这次想发到论坛，所以还是简单做一个用户界面方便使用吧。
口碑比较好的似乎是PyQt，试一下吧~

工具还是比较好的，但是我第一次用，所以界面比较丑，也存在一些小bug，比如说错误的链接会闪退~下个版本再更新吧

![打包后效果](https://upload-images.jianshu.io/upload_images/13604849-5d6e99b4997b55f7.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

最终代码已经上传到github上，看到的帮我点个star吧~
[源码及成果](https://github.com/DLWangSan/douyin_parse)
