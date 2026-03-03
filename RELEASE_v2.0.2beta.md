# v2.0.2beta: Album/Image Download with Live Image Support

## 🎉 New Features

### ✨ Album/Image Download Support
- **Image album parsing**: Support downloading image albums (图集)
- **Live image support**: Live images (Live Photo) are downloaded as MP4 videos
- **Content type detection**: Automatically detect video or image content
- **Multiple formats**: Support jpg, webp, png, gif, and mp4 formats
- **Smart deduplication**: Automatic removal of duplicate images
- **Note format support**: Support `/note/` URL format for albums

### 🔧 Technical Improvements
- Enhanced image data extraction with live image detection
- Improved URL extraction for live images (extract video URLs from `video` field)
- Better file type detection based on Content-Type and URL
- Optimized download logic for both static images and live videos

## 📦 Downloads

**Note**: Due to file size limits, executables need to be uploaded manually:
- `douyin_app_full_v2.0.2beta.exe` (~343 MB) - Full version with Playwright
- `douyin_app_slim_v2.0.2beta.exe` (~66 MB) - Slim version without Playwright

Please download from the Assets section below after manual upload.

## 🚀 Usage

### Downloading Image Albums

1. **Parse album link**: Paste album/share link in single video tab or user homepage tab
2. **Content type detection**: The app automatically detects if it's a video or image album
3. **Download**:
   - **Static albums**: Images are saved as jpg/webp/png files in a folder
   - **Live albums**: Live images are downloaded as MP4 video files
4. **File naming**: Files are numbered sequentially (001.jpg, 002.webp, etc.)

### Features

- **Automatic format detection**: File extension is determined by actual content type
- **Folder organization**: Each album is saved in its own folder
- **Batch download**: Support batch downloading multiple albums from user homepage
- **Type indicator**: Table shows content type (视频/图集) with image count

## 🔍 Technical Details

### Live Image Detection
- Detects `live_photo_type: 1` or `clip_type: 5` in API response
- Extracts video URL from `video.play_addr.url_list` (watermark-free)
- Downloads as MP4 format for proper playback

### Image Deduplication
- Removes duplicate URLs based on clean URL (without query parameters)
- Each image object only extracts one URL (prioritizes video for live images)
- Prevents downloading the same image multiple times

## ⚠️ Beta Notice

This is a beta release. Please report any issues you encounter.

## 📝 Changelog

### Added
- Image album download functionality
- Live image (Live Photo) support - downloads as MP4
- Content type detection (video/image)
- Support for `/note/` URL format
- Image format auto-detection (jpg/webp/png/gif/mp4)
- Image deduplication logic

### Fixed
- Fixed duplicate image downloads
- Fixed MP4 playback issues for live images
- Improved URL extraction for live images

### Changed
- Enhanced image data extraction to prioritize live image videos
- Updated download logic to handle both static and live images
- Improved file type detection
