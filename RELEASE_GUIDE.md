# GitHub Release 创建指南

由于exe文件过大（完整版342MB），无法直接提交到Git仓库，需要通过GitHub Release手动上传。

## 📦 创建Release步骤

### 1. 访问GitHub仓库
打开 https://github.com/DLWangSan/douyin_parse

### 2. 创建Release
- 点击右侧 **"Releases"** → **"Draft a new release"**
- 或者直接访问：https://github.com/DLWangSan/douyin_parse/releases/new

### 3. 填写Release信息

**Tag**: 选择 `v2.0.0`（已创建tag）

**Release title**: `v2.0.0 - Complete Rewrite`

**Description**:
```markdown
## 🎉 v2.0.0 - Complete Rewrite

### ✨ New Features
- Complete rewrite with latest reverse engineering algorithms (a_bogus & X-Bogus)
- Modern Qt6 GUI interface
- Batch download support
- User homepage parsing
- Auto cookie management (full version)

### 📦 Downloads
- **Full Version** (`douyin_app_full.exe`): Includes Playwright for auto cookie acquisition (342 MB)
- **Slim Version** (`douyin_app_slim.exe`): Manual cookie import only (66 MB)

### ⚠️ Important
Old code from years ago has become obsolete due to Douyin's anti-scraping mechanism upgrades. Please use this latest version!

### 🔧 Technical Details
- Pure Python implementation
- No browser automation required for core functionality
- Supports latest Douyin API
```

### 4. 上传文件
将以下文件拖拽到 **"Attach binaries"** 区域：
- `dist/douyin_app_full.exe` (342 MB)
- `dist/douyin_app_slim.exe` (66 MB)

**文件位置**: `E:\funny\dy_cursor\dist\`

### 5. 发布
- 勾选 **"Set as the latest release"**
- 点击 **"Publish release"** 按钮

## 📝 注意事项

- exe文件太大无法提交到Git仓库，只能通过Release上传
- 完整版包含Playwright浏览器，体积较大
- 精简版体积较小，但需要手动导入Cookie
