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

## Image Processing

- Resize images with aspect ratio preservation:

```bash
eyn img resize ./image.jpg --width 800 --height 600 -o ./resized.jpg
```

- Crop images to specific coordinates:

```bash
eyn img crop ./image.jpg --x 100 --y 100 --width 400 --height 300
```

- Convert image formats:

```bash
eyn img convert ./image.png --to jpg --quality 95
```

- Generate thumbnails (batch processing):

```bash
eyn img thumbs ./photos --out ./thumbs --width 256 --height 256 --mode cover
```

- Extract EXIF metadata:

```bash
eyn img exif ./photo.jpg
```

## PDF Processing

- Merge multiple PDFs:

```bash
eyn pdf merge file1.pdf file2.pdf file3.pdf --out merged.pdf
```

- Split PDF into individual pages:

```bash
eyn pdf split document.pdf --out ./pages
```

- Extract text from PDF:

```bash
eyn pdf text document.pdf --out extracted.txt
```

- Extract images from PDF:

```bash
eyn pdf images document.pdf --out ./pdf_images
```

## OCR (Optical Character Recognition)

- Extract text from images:

```bash
eyn ocr image.png --lang eng
```

- Advanced OCR with preprocessing and confidence scores:

```bash
eyn ocr scan.jpg --detailed --preprocess --psm 6 --out extracted.txt
```

- List available OCR languages:

```bash
eyn ocr-langs
```

## Other Tools

- Generate random hex color(s):

```bash
eyn color --luminosity light --count 3
# ["#E6F299", "#D4E8B9", "#B3E7E3"]

eyn color --alpha 0.5
# #A1C2FF80

eyn color --no-hash --seed 42
# A4B93C
```

## API Testing

- Make HTTP requests with authentication:

```bash
eyn api get https://api.example.com/users --bearer YOUR_TOKEN
eyn api post https://api.example.com/users --data '{"name": "John", "email": "john@example.com"}'
eyn api get https://api.example.com/data --basic user:password
```

- Benchmark API endpoints:

```bash
eyn api benchmark https://api.example.com/health --requests 1000 --concurrency 50
```

- Run test suites from JSON files:

```bash
eyn api test api_tests.json --base-url https://staging.api.example.com
```

Example test suite (`api_tests.json`):
```json
{
  "name": "User API Tests",
  "base_url": "https://api.example.com",
  "tests": [
    {
      "name": "Get user list",
      "method": "GET",
      "url": "/users",
      "expected_status": 200
    },
    {
      "name": "Create user",
      "method": "POST", 
      "url": "/users",
      "json_data": {"name": "Test User", "email": "test@example.com"},
      "expected_status": 201
    }
  ]
}
```

## Webhook Testing

- Send webhooks with predefined templates:

```bash
eyn webhook send https://your-app.com/webhook --template github_push
eyn webhook send https://your-app.com/webhook --template stripe_payment
```

- Send custom webhook data:

```bash
eyn webhook send https://your-app.com/webhook --data '{"event": "user.created", "user_id": 123}'
```

- Start a webhook receiver server for testing:

```bash
eyn webhook server --port 8080 --save --file webhooks.json
```

- Capture webhooks for development:

```bash
eyn webhook capture --port 8080 --count 5 --timeout 60 --save captured.json
```

- Test webhook endpoints:

```bash
eyn webhook test https://your-app.com/webhook --template webhook_test --status 200
```

Available webhook templates:
- `github_push` - GitHub push event
- `stripe_payment` - Stripe payment success
- `slack_message` - Slash command
- `webhook_test` - Generic test webhook

## Random Data Generation

- Generate cryptographically secure random data:

```bash
eyn random secure string --length 32 --symbols
eyn random secure token --length 16 --format urlsafe
eyn random secure password --length 20
eyn random secure int --min 1 --max 1000 --count 5
```

- Generate mock data for testing:

```bash
eyn random mock name --count 10 --gender female
eyn random mock email --count 5 --seed 42
eyn random mock address --count 3
eyn random mock profile --gender male
```

- Generate lorem ipsum text with variations:

```bash
eyn random lorem words --count 20 --word-set tech
eyn random lorem sentences --count 5 --word-set business
eyn random lorem paragraphs --count 3 --start-lorem
eyn random lorem text --count 2 --word-set lorem
```

- Generate seeded random data for reproducible results:

```bash
eyn random seed 42 --type int --count 10 --min 1 --max 100
eyn random seed 123 --type choice --choice red --choice blue --choice green --count 5
eyn random seed 456 --type string --length 8 --alphabet "ABC123"
eyn random seed 789 --type color --count 3
```

- Roll dice with advanced configurations:

```bash
eyn random dice 2d6+3
eyn random dice 4d6dl1 --count 6 --verbose  # Drop lowest, roll 6 times
eyn random dice 1d20 --advantage --count 3
eyn random dice 3d8 --stats  # Show statistics
eyn random dice 2d6 --compare 1d12  # Compare dice sets
```

Available dice notation:
- `XdY` - Roll X dice with Y sides
- `XdY+Z` - Add modifier Z
- `XdYdlN` - Drop N lowest dice
- `XdYdhN` - Drop N highest dice
- `XdY!` - Exploding dice (reroll max values)
- `--advantage/--disadvantage` - Roll twice, take higher/lower