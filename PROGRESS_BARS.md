# Progress Bars for Downloads

This document describes the progress bar features that have been added to all download operations in the EYN Python toolkit.

## Overview

All download operations now feature beautiful, real-time progress bars powered by Rich. The progress bars show:

- **Download progress** with percentage completion
- **Transfer speed** in human-readable format (B/s, KB/s, MB/s, etc.)
- **Time remaining** estimate
- **File size** information
- **Visual progress bar** with spinner animation

## Supported Download Operations

### 1. YouTube Downloads (`eyn dl yt`)

YouTube downloads now use Rich progress bars that integrate with yt-dlp's progress hooks:

```bash
eyn dl yt "https://www.youtube.com/watch?v=VIDEO_ID"
```

**Features:**
- Real-time progress for video and audio streams
- Progress tracking for multiple files in playlists
- Post-processing progress indicators
- Error status display

### 2. Instagram Downloads (`eyn dl ig`)

Instagram video downloads now show progress:

```bash
eyn dl ig "https://www.instagram.com/p/POST_ID/" --out video.mp4
```

**Features:**
- Progress bar for video file download
- Automatic file size detection
- Transfer speed display

### 3. TikTok Downloads (`eyn dl tt`)

TikTok video downloads now show progress:

```bash
eyn dl tt "https://www.tiktok.com/@user/video/VIDEO_ID" --out video.mp4
```

**Features:**
- Progress bar for video file download
- Automatic file size detection
- Transfer speed display

### 4. Asset Downloads (`eyn scrape download-asset`)

Web asset downloads now show progress:

```bash
eyn scrape download-asset "https://example.com/image.jpg" --out ./assets
```

**Features:**
- Progress bar for any downloadable asset
- Automatic filename extraction
- Transfer speed display

## Progress Bar Components

### Visual Elements

1. **Spinner**: Animated spinner showing activity
2. **Description**: File name being downloaded
3. **Progress Bar**: Visual representation of completion
4. **Percentage**: Exact completion percentage
5. **Transfer Speed**: Current download speed
6. **Time Remaining**: Estimated time to completion

### Color Coding

- **Blue**: Active downloads
- **Green**: Completed downloads (✓)
- **Red**: Failed downloads (✗)

## Technical Implementation

### Progress Bar Classes

#### `DownloadProgress`
A context manager for simple file downloads:

```python
from eyn_python.download.progress import DownloadProgress

with DownloadProgress("filename.mp4", total_size=1024000) as progress:
    # Update progress as chunks are downloaded
    progress.update(chunk_size)
```

#### `YouTubeProgressHook`
A progress hook for YouTube downloads:

```python
from eyn_python.download.progress import create_youtube_progress_hook

hook = create_youtube_progress_hook()
# Pass to yt-dlp options
ydl_opts = {"progress_hooks": [hook]}
```

### Utility Functions

#### `download_with_progress()`
A high-level function for downloading files with progress:

```python
from eyn_python.download.progress import download_with_progress

download_with_progress(
    url="https://example.com/file.mp4",
    output_path=Path("file.mp4"),
    filename="file.mp4"
)
```

## Configuration

### Customization Options

Progress bars can be customized by modifying the `DownloadProgress` class:

- **Bar width**: Change `bar_width` parameter
- **Colors**: Modify Rich color schemes
- **Columns**: Add/remove progress columns
- **Update frequency**: Control refresh rate

### Performance Considerations

- Progress bars use minimal CPU overhead
- Updates are throttled to prevent excessive redraws
- Memory usage is constant regardless of file size
- Network performance is unaffected

## Error Handling

Progress bars gracefully handle various error conditions:

- **Network errors**: Display error status in red
- **File size unknown**: Show indeterminate progress
- **Interrupted downloads**: Clear progress display
- **Invalid URLs**: Show appropriate error messages

## Examples

### Basic Download with Progress

```python
from eyn_python.download.progress import download_with_progress
from pathlib import Path

# Download a file with automatic progress bar
download_with_progress(
    url="https://example.com/large_file.zip",
    output_path=Path("large_file.zip"),
    filename="large_file.zip"
)
```

### Custom Progress Bar

```python
from eyn_python.download.progress import DownloadProgress

with DownloadProgress("custom_file.mp4") as progress:
    # Custom download logic
    for chunk in download_chunks():
        progress.update(len(chunk))
```

## Troubleshooting

### Common Issues

1. **Progress bar not showing**: Ensure terminal supports Rich output
2. **Incorrect file sizes**: Check if server provides Content-Length header
3. **Slow updates**: Large chunk sizes may cause infrequent updates

### Debug Mode

Enable verbose logging to see detailed progress information:

```bash
eyn dl yt "URL" --verbose
```

## Future Enhancements

Potential improvements for future versions:

- **Resume capability**: Resume interrupted downloads
- **Multiple downloads**: Concurrent download progress
- **Custom themes**: User-defined progress bar styles
- **Progress persistence**: Save progress across sessions
- **Bandwidth limiting**: Throttle download speeds

## Contributing

To add progress bars to new download operations:

1. Import the progress utilities
2. Use `DownloadProgress` for simple downloads
3. Use `download_with_progress()` for HTTP downloads
4. Create custom progress hooks for complex operations
5. Test with various file sizes and network conditions
