# 🎬 抖音无水印视频下载工具

> 纯Python实现，逆向算法突破反爬，无需浏览器自动化，高效稳定！

## 📢 重要更新

**本项目已全面重构更新！**

原项目代码（多年前的版本）由于抖音反爬机制升级已经失效。本项目已完全重写，采用最新的逆向算法（`a_bogus` 和 `X-Bogus`），支持：
- ✅ 最新的抖音API调用方式
- ✅ 完整的登录Cookie管理
- ✅ 现代化Qt6图形界面
- ✅ 批量下载功能
- ✅ 用户主页解析


[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Qt6](https://img.shields.io/badge/GUI-Qt6-purple.svg)](https://www.qt.io/)

## ✨ 核心特性

### 🚀 技术亮点
- **纯Python实现**：完全逆向 `a_bogus` 和 `X-Bogus` 算法，无需依赖浏览器自动化
- **高效稳定**：直接调用API，速度快、资源占用低
- **突破反爬**：完美绕过抖音的反爬虫机制，稳定获取无水印视频

### 🎯 功能特色
- ✅ **单个视频下载**：输入分享链接，一键获取无水印视频
- ✅ **批量下载**：支持用户主页批量解析，最多可解析20页视频
- ✅ **智能识别**：输入单个视频链接，自动找到用户主页并解析所有作品
- ✅ **可视化界面**：现代化Qt6界面，支持封面预览、文案展示
- ✅ **灵活选择**：批量下载时支持多选，想下哪个选哪个
- ✅ **自动登录**：完整版支持扫码登录自动获取Cookie（可选）
- ✅ **配置管理**：Cookie和保存路径持久化存储
- ✅ **视频质量选择**：支持选择视频分辨率和码率（v2.0.1+）
- ✅ **图集下载**：支持下载图片图集和Live图（Live Photo）（v2.0.2+）

## 📦 版本说明

### 完整版 (`douyin_app_full.exe`)
- ✅ 自动获取Cookie功能（扫码登录）
- ✅ 所有核心功能
- 📦 体积较大（包含Playwright浏览器）

### 精简版 (`douyin_app_slim.exe`)
- ✅ 所有核心功能
- ❌ 需手动导入Cookie
- 📦 体积小巧

## 🎨 界面预览

### 功能标签页
1. **单个视频下载**：快速下载单个无水印视频
2. **主页/视频解析**：批量解析用户作品，支持封面预览和批量下载
3. **配置管理**：Cookie管理、保存路径设置

## 🚀 快速开始

### 方法一：使用可执行文件（推荐）

1. **下载对应版本**
   - 需要自动登录：下载 `douyin_app_full.exe`
   - 只需手动Cookie：下载 `douyin_app_slim.exe`

2. **首次使用**
   - **完整版**：打开软件 → 配置标签 → 点击"获取Cookie" → 扫码登录 → 自动保存
   - **精简版**：打开软件 → 配置标签 → 手动粘贴Cookie到文本框 → 保存

3. **开始使用**
   - **单个视频**：复制抖音分享链接 → 粘贴到"单个视频下载"标签 → 点击下载
   - **批量下载**：输入用户主页链接或任意视频链接 → 设置最大页数 → 解析 → 勾选要下载的视频 → 下载

### 方法二：源码运行

```bash
# 1. 克隆或下载项目
git clone <repository-url>
cd dy_cursor

# 2. 安装依赖
pip install requests PySide6 playwright

# 3. 安装Playwright浏览器（仅完整版需要）
playwright install chromium

# 4. 配置Cookie
# 方式1：在配置界面扫码登录（完整版）
# 方式2：手动创建 douyin_cookie.txt 文件，粘贴Cookie内容

# 5. 运行程序
python qt_app.py          # 完整版
python qt_app_slim.py     # 精简版
```

## 📖 使用说明

### 获取Cookie（完整版）

1. 打开软件，切换到"配置"标签
2. 点击"获取Cookie"按钮
3. 等待二维码出现（无头浏览器自动打开）
4. 使用抖音APP扫码登录
5. 登录成功后，Cookie自动保存

### 手动导入Cookie（精简版）

1. 打开浏览器，访问 [抖音官网](https://www.douyin.com)
2. 登录账号
3. 打开开发者工具（F12）→ Network标签
4. 刷新页面，找到任意请求
5. 复制请求头中的 `Cookie` 值
6. 粘贴到软件的Cookie配置框中，保存

### 单个视频下载

1. 在抖音APP中，点击视频右下角"分享"按钮
2. 复制链接
3. 粘贴到"单个视频下载"标签的输入框
4. 点击"下载"按钮
5. 视频将保存到配置的下载目录

### 批量下载用户作品

1. 切换到"主页/视频解析"标签
2. 输入以下任一链接：
   - 用户主页链接：`https://www.douyin.com/user/xxx`
   - 任意视频链接：`https://www.douyin.com/video/xxx`
   - 图集链接：`https://v.douyin.com/xxx` 或 `https://www.douyin.com/note/xxx`
3. 设置最大页数（默认1页，最多20页）
4. 点击"解析"按钮
5. 等待解析完成，界面会显示所有内容的封面和文案
6. 表格中会显示内容类型（视频/图集）
7. 勾选要下载的内容（支持多选）
8. 如果下载视频，会弹出质量选择对话框（v2.0.1+）
9. 点击"下载选中"按钮

### 下载图集（v2.0.2+）

1. 解析图集链接后，表格中会显示"图集(x张)"
2. 勾选要下载的图集
3. 点击"下载选中"按钮
4. 图集会保存到独立文件夹中：
   - **静态图集**：保存为jpg/webp/png格式
   - **Live图集**：保存为MP4视频格式
5. 文件按序号命名（001.jpg, 002.webp, 003.mp4等）

## 🔧 技术原理

### 算法逆向
- **a_bogus算法**：SM3哈希 + RC4加密 + 浏览器指纹
- **X-Bogus算法**：MD5哈希 + RC4加密
- 纯Python实现，无需JavaScript引擎

> **核心算法参考**：本项目的 `a_bogus` 和 `X-Bogus` 算法实现参考自开源项目 [Douyin_TikTok_Download_API](https://github.com/Evil0ctal/Douyin_TikTok_Download_API)，感谢原作者的开源贡献！

### 无水印提取
- 识别 `play_addr` 中的 `uri` 参数
- 构造无水印播放地址：`aweme.snssdk.com/aweme/v1/play/?video_id={uri}`
- 或直接替换 `playwm` 为 `play`

### API调用
- 使用 `requests` 库直接调用抖音API
- 自动生成签名参数，绕过反爬检测
- 支持Cookie认证，获取完整视频信息

## 📁 文件结构

```
dy_cursor/
├── qt_app.py              # 完整版GUI主程序
├── qt_app_slim.py         # 精简版GUI主程序
├── douyin_video_parser.py # 核心解析逻辑
├── abogus.py              # a_bogus算法实现
├── xbogus.py              # X-Bogus算法实现
├── douyin_cookie.txt      # Cookie存储文件
├── config.json            # 配置文件
└── downloads/             # 默认下载目录
```

## ⚙️ 配置说明

### config.json
```json
{
  "cookie": "你的Cookie字符串",
  "save_dir": "下载保存路径"
}
```

### douyin_cookie.txt
纯文本文件，存储Cookie字符串（优先读取此文件）

## 🐛 常见问题

### Q: 提示"未找到视频"或"解析失败"
**A:** 
- 检查Cookie是否有效（可能已过期）
- 尝试重新获取Cookie
- 确认分享链接格式正确

### Q: 下载的视频有 watermark
**A:** 
- 确保使用的是最新版本
- 检查Cookie是否完整（需包含 `sessionid` 等关键字段）

### Q: 完整版无法获取Cookie
**A:** 
- 确保网络连接正常
- 检查防火墙是否阻止浏览器启动
- 尝试使用精简版手动导入Cookie

### Q: 批量下载时提示"解析失败"
**A:** 
- 检查输入的链接是否正确
- 确认用户主页是公开的
- 尝试减少最大页数

## 📝 更新日志

### v2.0.2beta (2026-03-03) - 图集下载功能 🖼️
- ✨ **图集下载支持**：新增图片图集下载功能
- ✨ **Live图支持**：Live图（Live Photo）自动下载为MP4视频格式
- ✨ **内容类型检测**：自动识别视频和图集内容
- ✨ **多格式支持**：支持jpg、webp、png、gif、mp4等多种格式
- ✨ **Note格式支持**：支持 `/note/` 格式的链接
- 🔧 **智能去重**：自动去除重复图片，每个图集只下载一次
- 🔧 **文件夹组织**：每个图集自动创建独立文件夹
- 🔧 **格式自动识别**：根据实际内容自动识别文件格式

### v2.0.1-beta (2026-02-XX) - 视频质量选择功能 🎬
- ✨ **视频质量选择**：支持选择视频分辨率和码率
- ✨ **质量选择对话框**：现代化UI，支持滚动浏览所有可用质量
- ✨ **批量质量选择**：批量下载时统一选择视频质量
- ✨ **文件名增强**：下载的文件名包含质量后缀（如 `video_1080p.mp4`）
- 🔧 **智能去重**：自动去除重复的质量选项
- 🔧 **质量提取优化**：增强视频质量信息提取逻辑

### v2.0.0 (2026-01-24) - 全面重构更新 🎉
- 🔄 **完全重写**：旧代码已失效，采用最新的逆向算法
- ✅ 实现单个视频无水印下载
- ✅ 实现用户主页批量解析
- ✅ 实现自动Cookie获取（完整版）
- ✅ 现代化Qt6界面
- ✅ 支持封面预览和批量选择下载
- ✅ 采用最新的 `a_bogus` 和 `X-Bogus` 算法
- ✅ 支持最新抖音API调用方式

### v1.0.0 (旧版本 - 已失效)
- ⚠️ 旧版本代码由于抖音反爬机制升级已失效
- 仅保留作为历史记录

## 🙏 致谢

- 核心算法参考：[Douyin_TikTok_Download_API](https://github.com/Evil0ctal/Douyin_TikTok_Download_API) - 感谢原作者 Evil0ctal 的开源贡献！

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## ⚠️ 免责声明

本工具仅供学习交流使用，请勿用于商业用途。下载的视频请遵守相关法律法规和平台规定。

---

**⭐ 如果这个工具对你有帮助，欢迎给个Star！**

## 📈 Star History[![Star History Chart](https://api.star-history.com/svg?repos=DLWangSan/douyin_parse&type=Date)](https://star-history.com/#DLWangSan/douyin_parse&Date)
