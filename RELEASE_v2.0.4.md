# v2.0.4: Fix QR Code Login (Full Edition)

## What's New

### Login Fix
- Fixed an issue where Cookie was not extracted automatically after scanning the QR code
- Improved login panel opening and QR code detection
- After a successful scan, the app now redirects to the homepage and saves Cookie automatically

## Downloads

- `douyin_app_full_v2.0.4.exe` - Full edition (Playwright QR login included)
- `douyin_app_slim_v2.0.4.exe` - Slim edition (manual Cookie import required)

## Changelog

### Fixed
- Full edition failed to extract Cookie after QR code login
- Login detection was too strict, preventing Cookie from being saved
- QR code loading could appear stuck on "Loading QR code..."
