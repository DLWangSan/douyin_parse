# v2.0.4: 修复完整版扫码登录

## 🎉 更新内容

### 🔧 登录修复
- 修复扫码后不会自动提取 Cookie 的问题
- 优化登录页打开与二维码识别逻辑
- 扫码成功后自动跳转首页并保存 Cookie

## 📦 Downloads

- `douyin_app_full_v2.0.4.exe` - 完整版（含 Playwright 扫码登录）
- `douyin_app_slim_v2.0.4.exe` - 精简版（需手动导入 Cookie）

## 📝 Changelog

### Fixed
- 完整版扫码登录后无法自动提取 Cookie
- 登录检测条件过严导致无法完成保存
