# EYN Python

A typed, modular toolkit with:

- `eyn dl` — fast, flexible YouTube downloader (yt-dlp)
- `eyn convert` — batch-capable media/file converter (FFmpeg required)
 - `eyn probe` — show media metadata (ffprobe JSON)
 - `eyn audio` — quick audio extraction (mp3/aac/flac/m4a/wav/ogg)
 - `eyn trim` — cut clips by timestamps

## Install

```bash
pip install -e .
```

## Usage

- Download a single video quickly (alias):

```bash
eyn dl "https://www.youtube.com/watch?v=VIDEO_ID"
```

- Full YouTube downloader command with options:

```bash
eyn dl yt "https://www.youtube.com/watch?v=VIDEO_ID" \
  --out ./out \
  --format "bestvideo*[ext=mp4]+bestaudio/best" \
  --playlist \
  --no-thumbnail \
  --fragments 8
```

- Convert media (FFmpeg required):

```bash
eyn convert ./input.mp4 --to mp3 -o ./out
```

- Batch convert recursively:

```bash
eyn convert ./media --to mp4 -o ./out --recursive
```

- Probe media metadata (JSON):

```bash
eyn probe ./input.mp4
```

- Extract audio quickly:

```bash
eyn audio ./input.mp4 --to mp3 -o ./out --bitrate 192k
```

- Trim a clip by timestamps:

```bash
eyn trim ./input.mp4 --start 00:00:05 --end 00:00:12 -o ./out --to mp4
```