# v2.0.5: Fix Douyin API 403 (UIFID / Argus Gateway)

## What's New

### Parse Fix
- Fixed `403 Blocked by ArgusSecurityPlugin Uifid Not Found` on video/user list API calls
- Automatically reads `UIFID` / `UIFID_TEMP` and `s_v_web_id` from your Cookie and sends them with signed requests
- `a_bogus` signing is unchanged; this release adds the gateway fields Douyin now requires

### Full Edition Login (Visible Browser)
- Replaced headless QR automation with a **visible Chromium window**
- You log in on Douyin normally (QR, password, captcha, etc.); the app captures Cookie in the background
- More reliable visitor fields (`UIFID`, `s_v_web_id`) for parsing

## Downloads

- `douyin_app_full_v2.0.5.exe` - Full edition (Playwright QR login included)
- `douyin_app_slim_v2.0.5.exe` - Slim edition (manual Cookie import required)

## Changelog

### Fixed
- Parsing failed even with a valid Cookie (Argus gateway / UIFID mismatch)
- User profile video list API missing the same gateway context

## Notes

- You still need a **valid Cookie** (scan login in full edition, or import from browser).
- Cookie should include visitor fields such as `UIFID` or `UIFID_TEMP` and `s_v_web_id`. If parsing still fails, re-login to refresh Cookie.
