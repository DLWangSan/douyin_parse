# v2.0.3: 修复抖音解析算法

## 🎉 更新内容

### 🔧 算法修复
- 同步最新 `a_bogus` / `X-Bogus` 签名实现
- 修复 `a_bogus` 二次 URL 编码导致签名失效的问题
- 对齐最新抖音 Web API 请求参数与请求头

## 📦 Downloads

- `douyin_app_full_v2.0.3.exe` - 完整版（含 Playwright 扫码登录）
- `douyin_app_slim_v2.0.3.exe` - 精简版（需手动导入 Cookie）

## 📝 Changelog

### Fixed
- 抖音 Web API 签名失效导致无法解析/下载
- A-Bogus 签名二次编码问题
