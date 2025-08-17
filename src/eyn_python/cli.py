from __future__ import annotations

from pathlib import Path
from typing import Optional, cast
import json as json_module
import json
from datetime import datetime

import typer

from eyn_python.logging import get_logger, console
from dataclasses import asdict
from typing import Any, Dict, cast
from eyn_python.display import (
    print_data,
    build_specs_render,
    build_netinfo_render,
    build_uptime_render,
    build_disks_render,
    build_top_render,
    build_battery_render,
    build_temps_render,
    build_ports_render,
    build_pubip_render,
    build_latency_render,
)
from rich.panel import Panel
from eyn_python.config import GlobalSettings, DownloadSettings, ConvertSettings
from eyn_python.download.youtube import DownloadJob, download
from eyn_python.download.instagram import download_instagram_video
from eyn_python.download.tiktok import download_tiktok_video
from eyn_python.convert.core import plan_conversions, convert_all
from eyn_python.media import (
    ffprobe_json,
    extract_audio,
    trim_media,
    AudioExtractOptions,
    # Image processing
    ThumbnailOptions,
    resize_image,
    crop_image,
    convert_image_format,
    generate_thumbnails,
    extract_exif,
    set_exif,
    # PDF tools
    pdf_merge,
    pdf_split,
    pdf_extract_text,
    pdf_extract_images,
    pdf_get_info,
    # OCR
    OCRResult,
    ocr_image,
    ocr_image_detailed,
    get_tesseract_languages,
    preprocess_image_for_ocr,
)
from eyn_python.paths import user_downloads_dir, ensure_dir
from eyn_python.scrape import (
    HttpClient,
    AsyncHttpClient,
    parse_html,
    extract_all,
    extract_links,
    crawl,
    crawl_async,
    fetch_sitemap_urls,
    search_async,
    extract_metadata,
    extract_forms,
    extract_assets,
    download_asset,
    save_page,
    fetch_robots_txt,
    can_fetch,
)
from eyn_python.scrape.screenshot import take_screenshot
from eyn_python.scrape.pdf import save_as_pdf
from eyn_python.archive import ArchiveSettings, ArchiveFormat, create_archive, extract_archive
from eyn_python.clean import CleanSettings, clean as clean_run
from eyn_python.system import (
    close_browsers,
    get_common_browser_app_names,
    detect_specs,
    network_info,
    uptime_info,
    partitions_info,
    top_processes,
    battery_info,
    temperatures_info,
    listening_ports,
    public_ip,
    http_latency,
    TempCleanSettings,
    default_temp_dir,
    clean_temp,
)
from eyn_python.system.uuid import generate_uuid
from eyn_python.system.password import generate_password
from eyn_python.system.hash import hash_file
from eyn_python.system.base64 import encode_base64, decode_base64
from eyn_python.system.url import encode_url, decode_url
from eyn_python.system.time import to_timestamp, from_timestamp
from eyn_python.system.qrcode import generate_qr_code
from eyn_python.system.text import word_count
from eyn_python.system.color import random_hex_color
from eyn_python.api import (
    APIClient,
    APIResponse,
    BearerAuth,
    BasicAuth,
    APIKeyAuth,
    APITestSuite,
    run_api_tests,
    benchmark_endpoint,
    load_test_suite_from_json,
)
from eyn_python.webhook import (
    WebhookServer,
    WebhookClient,
    send_webhook,
    simulate_webhook,
    start_webhook_server,
    stop_webhook_server,
    capture_webhooks,
    test_webhook_endpoint,
)
from eyn_python.random import (
    # Secure random
    secure_random_bytes,
    secure_random_string,
    secure_random_int,
    secure_random_float,
    generate_token,
    generate_password_secure,
    # Mock data
    MockDataGenerator,
    MockDataOptions,
    generate_name,
    generate_email,
    generate_phone,
    generate_address,
    generate_company,
    generate_user_profile,
    generate_credit_card,
    # Lorem ipsum
    LoremGenerator,
    LoremOptions,
    generate_lorem_words,
    generate_lorem_sentences,
    generate_lorem_paragraphs,
    generate_lorem_text,
    # Seeded random
    SeededRandom,
    seeded_choice,
    seeded_shuffle,
    seeded_int,
    seeded_float,
    # Dice
    Dice,
    DiceRoll,
    roll_dice,
    roll_custom_dice,
    roll_advantage,
    roll_disadvantage,
    calculate_dice_stats,
    compare_dice_sets,
    parse_dice_notation,
)

app = typer.Typer(
    name="eyn",
    add_completion=True,
    no_args_is_help=True,
    help="EYN Python: a modular toolkit (YouTube downloader, converter, and more).",
)

log = get_logger("eyn")

@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logs."),
) -> None:
    if verbose:
        import logging
        get_logger("eyn").setLevel(logging.DEBUG)  # bump global level

# ---- Download: YouTube ------------------------------------------------------

dl_app = typer.Typer(help="YouTube downloader (yt-dlp powered).")
app.add_typer(dl_app, name="dl")

@dl_app.command("yt")
def dl_yt(
    url: str = typer.Argument(..., help="YouTube video/playlist URL."),
    out: Path = typer.Option(Path.cwd() / "out", "--out", "-o", help="Output directory."),
    format: str = typer.Option(
        DownloadSettings().format,
        "--format", "-f",
        help="yt-dlp format selector.",
    ),
    playlist: bool = typer.Option(False, "--playlist", help="Treat URL as playlist."),
    metadata: bool = typer.Option(True, "--metadata/--no-metadata", help="Embed metadata."),
    thumbnail: bool = typer.Option(True, "--thumbnail/--no-thumbnail", help="Embed thumbnail."),
    fragments: int = typer.Option(8, "--fragments", help="Concurrent fragment downloads."),
) -> None:
    """
    Download a video or playlist from YouTube.
    """
    settings = DownloadSettings(
        format=format,
        playlist=playlist,
        metadata=metadata,
        embed_thumbnail=thumbnail,
        concurrent_fragments=fragments,
    )
    job = DownloadJob(url=url, output_dir=out, settings=settings)
    download(job)

@dl_app.command("ig")
def dl_ig(
    url: str = typer.Argument(..., help="Instagram video URL."),
    out: Path = typer.Option(Path.cwd() / "out.mp4", "--out", "-o", help="Output file."),
) -> None:
    """
    Download a video from Instagram.
    """
    import asyncio
    console().print(f"[blue]Downloading Instagram video...[/blue]")
    asyncio.run(download_instagram_video(url, out))
    console().print(f"[green]✓ Video saved to {out}[/green]")

@dl_app.command("tt")
def dl_tt(
    url: str = typer.Argument(..., help="TikTok video URL."),
    out: Path = typer.Option(Path.cwd() / "out.mp4", "--out", "-o", help="Output file."),
) -> None:
    """
    Download a video from TikTok.
    """
    import asyncio
    console().print(f"[blue]Downloading TikTok video...[/blue]")
    asyncio.run(download_tiktok_video(url, out))
    console().print(f"[green]✓ Video saved to {out}[/green]")

# Convenience alias: `eyn dl URL`
@dl_app.callback(invoke_without_command=True)
def dl_default(
    ctx: typer.Context,
    url: Optional[str] = typer.Argument(None, help="YouTube video/playlist URL."),
    out: Path = typer.Option(Path.cwd() / "out", "--out", "-o", help="Output directory."),
    format: str = typer.Option(
        DownloadSettings().format,
        "--format",
        "-f",
        help="yt-dlp format selector.",
    ),
    playlist: bool = typer.Option(False, "--playlist", help="Treat URL as playlist."),
    metadata: bool = typer.Option(True, "--metadata/--no-metadata", help="Embed metadata."),
    thumbnail: bool = typer.Option(True, "--thumbnail/--no-thumbnail", help="Embed thumbnail."),
    fragments: int = typer.Option(8, "--fragments", help="Concurrent fragment downloads."),
) -> None:
    if ctx.invoked_subcommand is None:
        if not url:
            typer.echo(ctx.get_help())
            raise typer.Exit(0)
        dl_yt(url, out, format, playlist, metadata, thumbnail, fragments)

# ---- Convert ----------------------------------------------------------------

@app.command("convert")
def convert(
    src: Path = typer.Argument(..., exists=True, readable=True, help="Source file or directory."),
    to: str = typer.Option(..., "--to", help="Target extension/format, e.g., mp4, mp3, mkv, wav."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Output directory (optional)."),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Recurse folders."),
    crf: int = typer.Option(23, "--crf", help="Video CRF (lower = better quality)."),
    preset: str = typer.Option("medium", "--preset", help="Video preset (x264/x265)."),
    tune: Optional[str] = typer.Option(None, "--tune", help="Video tune (film, animation, etc.)."),
    audio_bitrate: Optional[str] = typer.Option("192k", "--audio-bitrate", help="Audio bitrate."),
    video_codec: str = typer.Option("libx264", "--vcodec", help="Video codec (libx264, libx265...)."),
    audio_codec: str = typer.Option("aac", "--acodec", help="Audio codec (aac, libmp3lame...)."),
    # New core options
    workers: Optional[int] = typer.Option(None, "--workers", "-j", help="Max concurrent ffmpeg processes (default: ~half your CPU cores)."),
    smart_copy: bool = typer.Option(True, "--smart-copy/--no-smart-copy", help="Try stream copy when container/codec already compatible (faster, lossless)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print planned ffmpeg commands without running."),
    skip_up_to_date: bool = typer.Option(True, "--skip-up-to-date/--no-skip-up-to-date", help="Skip when destination exists, non-empty, and not older than source."),
) -> None:
    """
    Convert media using FFmpeg (installed separately). Works on files or directories.
    """
    settings = ConvertSettings(
        to=to,
        recursive=recursive,
        output_dir=out,
    )
    # override nested video settings
    settings.video.crf = crf
    settings.video.preset = preset
    settings.video.tune = tune
    settings.video.audio_bitrate = audio_bitrate
    settings.video.video_codec = video_codec
    settings.video.audio_codec = audio_codec

    jobs = plan_conversions(src, settings)
    convert_all(
        jobs,
        workers=workers,
        smart_copy=smart_copy,
        dry_run=dry_run,
        skip_if_up_to_date=skip_up_to_date,
    )

# ---- Media tools -------------------------------------------------------------

@app.command("probe")
def probe(
    src: Path = typer.Argument(..., exists=True, readable=True, help="Source media file."),
) -> None:
    """
    Show media metadata via ffprobe (JSON).
    """
    data = ffprobe_json(src)
    console().print_json(data=data)


@app.command("audio")
def audio(
    src: Path = typer.Argument(..., exists=True, readable=True, help="Source media file."),
    to: str = typer.Option("mp3", "--to", help="Audio format: mp3, aac, flac, m4a, wav, ogg."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Output directory (optional)."),
    codec: Optional[str] = typer.Option(None, "--codec", help="Audio codec override."),
    bitrate: Optional[str] = typer.Option("192k", "--bitrate", help="Audio bitrate."),
) -> None:
    """
    Extract audio from a media file.
    """
    dst = extract_audio(src, out, to, AudioExtractOptions(codec=codec, bitrate=bitrate))
    console().print(f"Saved -> {dst}")


@app.command("trim")
def trim(
    src: Path = typer.Argument(..., exists=True, readable=True, help="Source media file."),
    start: str = typer.Option(..., "--start", help="Start timestamp (e.g., 00:00:05)."),
    end: Optional[str] = typer.Option(None, "--end", help="End timestamp (e.g., 00:00:10)."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Output directory (optional)."),
    to: Optional[str] = typer.Option(None, "--to", help="Target extension, default keep source."),
    reencode: bool = typer.Option(False, "--reencode", help="Re-encode instead of stream copy."),
) -> None:
    """
    Trim/cut a clip by timestamps.
    """
    dst = trim_media(src, out, to, start, end, copy=not reencode)
    console().print(f"Saved -> {dst}")


# ---- Image Processing -------------------------------------------------------

img_app = typer.Typer(help="Image processing tools (Pillow).")
app.add_typer(img_app, name="img")


@img_app.command("resize")
def image_resize_cmd(
    src: Path = typer.Argument(..., exists=True, readable=True, help="Source image."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Output file."),
    width: Optional[int] = typer.Option(None, "--width", help="Target width."),
    height: Optional[int] = typer.Option(None, "--height", help="Target height."),
    keep_aspect: bool = typer.Option(True, "--keep-aspect/--no-keep-aspect", help="Preserve aspect ratio."),
    quality: int = typer.Option(90, "--quality", help="JPEG quality (if applicable)."),
) -> None:
    """Resize an image with optional aspect ratio preservation."""
    try:
        dst = resize_image(src, out, width, height, keep_aspect, quality)
        console().print(f"Saved -> {dst}")
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@img_app.command("crop")
def image_crop_cmd(
    src: Path = typer.Argument(..., exists=True, readable=True, help="Source image."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Output file."),
    x: int = typer.Option(..., "--x", help="Left coordinate."),
    y: int = typer.Option(..., "--y", help="Top coordinate."),
    width: int = typer.Option(..., "--width", help="Crop width."),
    height: int = typer.Option(..., "--height", help="Crop height."),
    quality: int = typer.Option(90, "--quality", help="JPEG quality (if applicable)."),
) -> None:
    """Crop an image to specified coordinates and dimensions."""
    try:
        dst = crop_image(src, out, x, y, width, height, quality)
        console().print(f"Saved -> {dst}")
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@img_app.command("convert")
def image_convert_cmd(
    src: Path = typer.Argument(..., exists=True, readable=True, help="Source image."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Output file."),
    to: str = typer.Option("png", "--to", help="Target format: png|jpg|jpeg|webp|bmp|tiff"),
    quality: int = typer.Option(90, "--quality", help="JPEG quality (if applicable)."),
) -> None:
    """Convert image to different format."""
    try:
        dst = convert_image_format(src, out, to, quality)
        console().print(f"Saved -> {dst}")
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@img_app.command("thumbs")
def image_thumbs_cmd(
    src: Path = typer.Argument(..., exists=True, readable=True, help="Source file or directory."),
    out: Path = typer.Option(Path.cwd() / "thumbs", "--out", "-o", help="Output directory."),
    width: int = typer.Option(256, "--width", help="Thumbnail width."),
    height: int = typer.Option(256, "--height", help="Thumbnail height."),
    mode: str = typer.Option("fit", "--mode", help="fit|cover"),
    quality: int = typer.Option(90, "--quality", help="JPEG quality."),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", help="Recurse directories."),
    pattern: str = typer.Option("*", "--pattern", help="Glob pattern when src is directory."),
) -> None:
    """Generate thumbnails for images."""
    try:
        options = ThumbnailOptions(
            size=(width, height),
            mode=mode,
            quality=quality,
            recursive=recursive,
            pattern=pattern,
        )
        n = generate_thumbnails(src, out, options)
        console().print(f"Generated {n} thumbnail(s) -> {out}")
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@img_app.command("exif")
def image_exif_cmd(
    src: Path = typer.Argument(..., exists=True, readable=True, help="Source image."),
    json: bool = typer.Option(False, "--json", help="Raw JSON output."),
) -> None:
    """Extract EXIF metadata from an image."""
    try:
        data = extract_exif(src)
        if json:
            console().print_json(data=data)
        else:
            from eyn_python.display import print_data
            print_data(data, Panel(f"EXIF Data for {src.name}", title="Image Metadata"), json)
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@img_app.command("set-exif")
def image_set_exif_cmd(
    src: Path = typer.Argument(..., exists=True, readable=True, help="Source image."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Output image (defaults overwrite)."),
    kv: list[str] = typer.Option([], "--set", help="Key=Value updates (repeat)."),
) -> None:
    """Set EXIF metadata on an image."""
    try:
        updates: dict[str, str] = {}
        for item in kv:
            if "=" in item:
                k, v = item.split("=", 1)
                updates[k] = v
        dst = set_exif(src, out, updates)
        console().print(f"Saved -> {dst}")
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# ---- PDF Tools ---------------------------------------------------------------

pdf_app = typer.Typer(help="PDF manipulation (merge, split, extract text/images).")
app.add_typer(pdf_app, name="pdf")


@pdf_app.command("merge")
def pdf_merge_cmd(
    files: list[Path] = typer.Argument(..., exists=True, readable=True, help="Input PDFs in order."),
    out: Path = typer.Option(Path.cwd() / "merged.pdf", "--out", "-o", help="Output file."),
) -> None:
    """Merge multiple PDF files into one."""
    try:
        dst = pdf_merge(files, out)
        console().print(f"Merged {len(files)} files -> {dst}")
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@pdf_app.command("split")
def pdf_split_cmd(
    src: Path = typer.Argument(..., exists=True, readable=True, help="Source PDF."),
    out: Path = typer.Option(Path.cwd() / "pages", "--out", "-o", help="Output directory."),
) -> None:
    """Split a PDF into individual pages."""
    try:
        n = pdf_split(src, out)
        console().print(f"Split into {n} page(s) -> {out}")
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@pdf_app.command("text")
def pdf_text_cmd(
    src: Path = typer.Argument(..., exists=True, readable=True, help="Source PDF."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Save to text file."),
) -> None:
    """Extract text from a PDF."""
    try:
        text = pdf_extract_text(src)
        if out:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            console().print(f"Text saved -> {out}")
        else:
            console().print(text)
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@pdf_app.command("images")
def pdf_images_cmd(
    src: Path = typer.Argument(..., exists=True, readable=True, help="Source PDF."),
    out: Path = typer.Option(Path.cwd() / "images", "--out", "-o", help="Output directory."),
) -> None:
    """Extract images from a PDF."""
    try:
        n = pdf_extract_images(src, out)
        console().print(f"Extracted {n} image(s) -> {out}")
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@pdf_app.command("info")
def pdf_info_cmd(
    src: Path = typer.Argument(..., exists=True, readable=True, help="Source PDF."),
    json: bool = typer.Option(False, "--json", help="Raw JSON output."),
) -> None:
    """Show PDF information and metadata."""
    try:
        data = pdf_get_info(src)
        if json:
            console().print_json(data=data)
        else:
            from eyn_python.display import print_data
            print_data(data, Panel(f"PDF Info for {src.name}", title="PDF Metadata"), json)
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# ---- OCR ---------------------------------------------------------------------

@app.command("ocr")
def ocr_cmd(
    src: Path = typer.Argument(..., exists=True, readable=True, help="Image to OCR."),
    lang: str = typer.Option("eng", "--lang", "-l", help="Language (Tesseract installed)."),
    psm: Optional[int] = typer.Option(None, "--psm", help="Tesseract page segmentation mode."),
    oem: Optional[int] = typer.Option(None, "--oem", help="OCR Engine mode."),
    config: Optional[str] = typer.Option(None, "--config", help="Additional Tesseract config."),
    detailed: bool = typer.Option(False, "--detailed", help="Include confidence and word positions."),
    preprocess: bool = typer.Option(False, "--preprocess", help="Preprocess image for better OCR."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Save text to file."),
) -> None:
    """Extract text from images using Tesseract OCR."""
    try:
        img_path = src
        
        # Preprocess if requested
        if preprocess:
            preprocessed_path = src.parent / f"{src.stem}_preprocessed.png"
            img_path = preprocess_image_for_ocr(src, preprocessed_path)
            console().print(f"Preprocessed image -> {img_path}")
        
        if detailed:
            result = ocr_image_detailed(img_path, lang, psm, oem, config)
            if out:
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(result.text, encoding="utf-8")
                console().print(f"Text saved -> {out}")
                console().print(f"Average confidence: {result.confidence:.1f}%")
            else:
                console().print(f"[green]Confidence: {result.confidence:.1f}%[/green]")
                console().print(result.text)
        else:
            text = ocr_image(img_path, lang, psm, oem, config)
            if out:
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(text, encoding="utf-8")
                console().print(f"Text saved -> {out}")
            else:
                console().print(text)
                
        # Clean up preprocessed file if created
        if preprocess and img_path != src:
            img_path.unlink(missing_ok=True)
            
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("ocr-langs")
def ocr_langs_cmd() -> None:
    """List available OCR languages."""
    try:
        langs = get_tesseract_languages()
        console().print("Available Tesseract languages:")
        for lang in sorted(langs):
            console().print(f"  {lang}")
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# ---- API Testing -------------------------------------------------------------

api_app = typer.Typer(help="REST API testing and interaction.")
app.add_typer(api_app, name="api")


@api_app.command("get")
def api_get_cmd(
    url: str = typer.Argument(..., help="URL to request."),
    headers: list[str] = typer.Option([], "--header", "-H", help="Headers in 'Key: Value' format."),
    auth_bearer: Optional[str] = typer.Option(None, "--bearer", help="Bearer token."),
    auth_basic: Optional[str] = typer.Option(None, "--basic", help="Basic auth 'user:pass'."),
    auth_key: Optional[str] = typer.Option(None, "--api-key", help="API key."),
    auth_key_header: str = typer.Option("X-API-Key", "--api-key-header", help="API key header name."),
    timeout: float = typer.Option(30.0, "--timeout", help="Request timeout in seconds."),
    json_output: bool = typer.Option(False, "--json", help="Raw JSON output."),
    save: Optional[Path] = typer.Option(None, "--save", help="Save response to file."),
) -> None:
    """Make a GET request to an API endpoint."""
    try:
        # Parse headers
        header_dict = {}
        for header in headers:
            if ':' in header:
                key, value = header.split(':', 1)
                header_dict[key.strip()] = value.strip()
        
        # Setup auth
        auth = None
        if auth_bearer:
            auth = BearerAuth(auth_bearer)
        elif auth_basic:
            if ':' not in auth_basic:
                raise ValueError("Basic auth must be in 'user:pass' format")
            username, password = auth_basic.split(':', 1)
            auth = BasicAuth(username, password)
        elif auth_key:
            auth = APIKeyAuth(auth_key, auth_key_header)
        
        # Make request
        client = APIClient(default_headers=header_dict, auth=auth, timeout=timeout)
        response = client.get(url)
        
        # Save response
        if save:
            save.parent.mkdir(parents=True, exist_ok=True)
            save.write_text(response.text, encoding='utf-8')
            console().print(f"Response saved to {save}")
        
        # Display response
        if json_output:
            response_data = {
                'status_code': response.status_code,
                'headers': response.headers,
                'body': response.text,
                'elapsed_ms': response.elapsed_ms,
            }
            console().print_json(data=response_data)
        else:
            console().print(f"[green]Status:[/green] {response.status_code}")
            console().print(f"[green]Time:[/green] {response.elapsed_ms:.1f}ms")
            console().print(f"[green]Content-Type:[/green] {response.content_type}")
            console().print()
            
            if response.content_type.startswith('application/json'):
                try:
                    console().print_json(data=response.json)
                except:
                    console().print(response.text)
            else:
                console().print(response.text)
        
        client.close()
        
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@api_app.command("post")
def api_post_cmd(
    url: str = typer.Argument(..., help="URL to request."),
    data: Optional[str] = typer.Option(None, "--data", "-d", help="JSON data to send."),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File containing JSON data."),
    headers: list[str] = typer.Option([], "--header", "-H", help="Headers in 'Key: Value' format."),
    auth_bearer: Optional[str] = typer.Option(None, "--bearer", help="Bearer token."),
    auth_basic: Optional[str] = typer.Option(None, "--basic", help="Basic auth 'user:pass'."),
    auth_key: Optional[str] = typer.Option(None, "--api-key", help="API key."),
    auth_key_header: str = typer.Option("X-API-Key", "--api-key-header", help="API key header name."),
    timeout: float = typer.Option(30.0, "--timeout", help="Request timeout in seconds."),
    json_output: bool = typer.Option(False, "--json", help="Raw JSON output."),
) -> None:
    """Make a POST request to an API endpoint."""
    try:
        # Parse headers
        header_dict = {}
        for header in headers:
            if ':' in header:
                key, value = header.split(':', 1)
                header_dict[key.strip()] = value.strip()
        
        # Parse data
        json_data = None
        if data:
            json_data = json.loads(data)
        elif file:
            json_data = json.loads(file.read_text())
        
        # Setup auth
        auth = None
        if auth_bearer:
            auth = BearerAuth(auth_bearer)
        elif auth_basic:
            if ':' not in auth_basic:
                raise ValueError("Basic auth must be in 'user:pass' format")
            username, password = auth_basic.split(':', 1)
            auth = BasicAuth(username, password)
        elif auth_key:
            auth = APIKeyAuth(auth_key, auth_key_header)
        
        # Make request
        client = APIClient(default_headers=header_dict, auth=auth, timeout=timeout)
        response = client.post(url, json_data=json_data)
        
        # Display response
        if json_output:
            response_data = {
                'status_code': response.status_code,
                'headers': response.headers,
                'body': response.text,
                'elapsed_ms': response.elapsed_ms,
            }
            console().print_json(data=response_data)
        else:
            console().print(f"[green]Status:[/green] {response.status_code}")
            console().print(f"[green]Time:[/green] {response.elapsed_ms:.1f}ms")
            console().print()
            
            if response.content_type.startswith('application/json'):
                try:
                    console().print_json(data=response.json)
                except:
                    console().print(response.text)
            else:
                console().print(response.text)
        
        client.close()
        
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@api_app.command("test")
def api_test_cmd(
    suite_file: Path = typer.Argument(..., exists=True, help="JSON file containing test suite."),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Override base URL."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output."),
) -> None:
    """Run API test suite from JSON file."""
    try:
        suite = load_test_suite_from_json(suite_file)
        
        if base_url:
            suite.base_url = base_url
        
        console().print(f"Running test suite: [blue]{suite.name}[/blue]")
        console().print(f"Base URL: {suite.base_url}")
        console().print()
        
        results = run_api_tests(suite)
        
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        
        for result in results:
            status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
            console().print(f"{status} {result.name} ({result.execution_time_ms:.1f}ms)")
            
            if not result.passed or verbose:
                console().print(f"  {result.message}")
                if result.response and verbose:
                    console().print(f"  Status: {result.response.status_code}")
                    console().print(f"  URL: {result.response.url}")
            console().print()
        
        console().print(f"Results: {passed} passed, {failed} failed")
        
        if failed > 0:
            raise typer.Exit(1)
            
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@api_app.command("benchmark")
def api_benchmark_cmd(
    url: str = typer.Argument(..., help="URL to benchmark."),
    method: str = typer.Option("GET", "--method", "-m", help="HTTP method."),
    requests: int = typer.Option(100, "--requests", "-n", help="Number of requests."),
    concurrency: int = typer.Option(10, "--concurrency", "-c", help="Concurrent requests."),
    data: Optional[str] = typer.Option(None, "--data", "-d", help="JSON data for POST/PUT."),
    headers: list[str] = typer.Option([], "--header", "-H", help="Headers in 'Key: Value' format."),
    timeout: float = typer.Option(30.0, "--timeout", help="Request timeout in seconds."),
) -> None:
    """Benchmark an API endpoint."""
    try:
        # Parse headers
        header_dict = {}
        for header in headers:
            if ':' in header:
                key, value = header.split(':', 1)
                header_dict[key.strip()] = value.strip()
        
        # Parse data
        json_data = None
        if data:
            json_data = json.loads(data)
        
        # Run benchmark
        client = APIClient(default_headers=header_dict, timeout=timeout)
        
        console().print(f"Benchmarking {url}")
        console().print(f"Method: {method}, Requests: {requests}, Concurrency: {concurrency}")
        console().print()
        
        result = benchmark_endpoint(
            client, method, url, requests, concurrency, json_data=json_data
        )
        
        # Display results
        console().print(f"[green]Benchmark Results[/green]")
        console().print(f"Total requests: {result.total_requests}")
        console().print(f"Successful: {result.successful_requests}")
        console().print(f"Failed: {result.failed_requests}")
        console().print(f"Total time: {result.total_time_seconds:.2f}s")
        console().print(f"Requests/sec: {result.requests_per_second:.2f}")
        console().print()
        console().print(f"Response times (ms):")
        console().print(f"  Average: {result.avg_response_time_ms:.1f}")
        console().print(f"  Min: {result.min_response_time_ms:.1f}")
        console().print(f"  Max: {result.max_response_time_ms:.1f}")
        console().print(f"  Median: {result.median_response_time_ms:.1f}")
        
        if result.status_codes:
            console().print()
            console().print("Status codes:")
            for code, count in sorted(result.status_codes.items()):
                console().print(f"  {code}: {count}")
        
        if result.errors:
            console().print()
            console().print("Errors:")
            for error in result.errors[:5]:  # Show first 5 errors
                console().print(f"  {error}")
            if len(result.errors) > 5:
                console().print(f"  ... and {len(result.errors) - 5} more")
        
        client.close()
        
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# ---- Webhook Testing ---------------------------------------------------------

webhook_app = typer.Typer(help="Webhook testing and simulation.")
app.add_typer(webhook_app, name="webhook")


@webhook_app.command("send")
def webhook_send_cmd(
    url: str = typer.Argument(..., help="Webhook URL."),
    data: Optional[str] = typer.Option(None, "--data", "-d", help="JSON data to send."),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File containing JSON data."),
    template: Optional[str] = typer.Option(None, "--template", "-t", help="Webhook template (github_push, stripe_payment, etc)."),
    headers: list[str] = typer.Option([], "--header", "-H", help="Headers in 'Key: Value' format."),
    signature_header: Optional[str] = typer.Option(None, "--signature-header", help="Header name for signature."),
    signature_secret: Optional[str] = typer.Option(None, "--signature-secret", help="Secret for signature."),
    retries: int = typer.Option(3, "--retries", help="Number of retries."),
    timeout: float = typer.Option(30.0, "--timeout", help="Request timeout in seconds."),
) -> None:
    """Send a webhook to a URL."""
    try:
        # Parse headers
        header_dict = {}
        for header in headers:
            if ':' in header:
                key, value = header.split(':', 1)
                header_dict[key.strip()] = value.strip()
        
        # Parse data
        webhook_data = {}
        if data:
            webhook_data = json.loads(data)
        elif file:
            webhook_data = json.loads(file.read_text())
        elif template:
            webhook_data = simulate_webhook(template)
        else:
            webhook_data = simulate_webhook('webhook_test')
        
        # Send webhook
        client = WebhookClient(
            default_headers=header_dict,
            timeout=timeout,
            retries=retries,
        )
        
        response = client.send(
            url=url,
            data=webhook_data,
            signature_header=signature_header,
            signature_secret=signature_secret,
        )
        
        console().print(f"[green]Webhook sent successfully[/green]")
        console().print(f"Status: {response.status_code}")
        console().print(f"Time: {response.elapsed_ms:.1f}ms")
        console().print(f"Response: {response.text[:200]}{'...' if len(response.text) > 200 else ''}")
        
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@webhook_app.command("server")
def webhook_server_cmd(
    port: int = typer.Option(8080, "--port", "-p", help="Port to listen on."),
    host: str = typer.Option("localhost", "--host", help="Host to bind to."),
    save_requests: bool = typer.Option(False, "--save", help="Save requests to file."),
    requests_file: Optional[Path] = typer.Option(None, "--file", help="File to save requests to."),
) -> None:
    """Start a webhook receiver server."""
    try:
        server = WebhookServer(
            host=host,
            port=port,
            save_requests=save_requests,
            requests_file=requests_file,
        )
        
        console().print(f"Starting webhook server on http://{host}:{port}")
        console().print("Press Ctrl+C to stop")
        console().print()
        console().print("Admin endpoints:")
        console().print(f"  GET  http://{host}:{port}/_admin/requests - View captured requests")
        console().print(f"  POST http://{host}:{port}/_admin/clear - Clear captured requests")
        console().print()
        
        server.start(threaded=False)  # Block until stopped
        
    except KeyboardInterrupt:
        console().print("\nStopping webhook server...")
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@webhook_app.command("capture")
def webhook_capture_cmd(
    port: int = typer.Option(8080, "--port", "-p", help="Port to listen on."),
    count: int = typer.Option(1, "--count", "-n", help="Number of webhooks to capture."),
    timeout: float = typer.Option(30.0, "--timeout", "-t", help="Timeout in seconds."),
    save: Optional[Path] = typer.Option(None, "--save", help="Save captured webhooks to file."),
) -> None:
    """Capture incoming webhooks for testing."""
    try:
        console().print(f"Capturing {count} webhook(s) on port {port} (timeout: {timeout}s)")
        
        webhooks = capture_webhooks(port=port, count=count, timeout=timeout)
        
        if webhooks:
            console().print(f"\n[green]Captured {len(webhooks)} webhook(s):[/green]")
            for i, webhook in enumerate(webhooks, 1):
                console().print(f"\n[blue]Webhook {i}:[/blue]")
                console().print(f"  Method: {webhook.method}")
                console().print(f"  Path: {webhook.path}")
                console().print(f"  Headers: {len(webhook.headers)} headers")
                console().print(f"  Body size: {len(webhook.body)} bytes")
                if webhook.json_data:
                    console().print(f"  JSON: {json.dumps(webhook.json_data, indent=2)[:200]}...")
            
            if save:
                webhook_data = [{
                    'id': w.id,
                    'timestamp': w.timestamp.isoformat(),
                    'method': w.method,
                    'url': w.url,
                    'path': w.path,
                    'headers': w.headers,
                    'query_params': w.query_params,
                    'body': w.body,
                    'json_data': w.json_data,
                    'content_type': w.content_type,
                    'remote_addr': w.remote_addr,
                } for w in webhooks]
                
                save.parent.mkdir(parents=True, exist_ok=True)
                save.write_text(json.dumps(webhook_data, indent=2))
                console().print(f"\nSaved to {save}")
        else:
            console().print("[yellow]No webhooks captured[/yellow]")
        
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@webhook_app.command("test")
def webhook_test_cmd(
    url: str = typer.Argument(..., help="Webhook URL to test."),
    template: str = typer.Option("webhook_test", "--template", "-t", help="Webhook template."),
    expected_status: int = typer.Option(200, "--status", help="Expected status code."),
    timeout: float = typer.Option(10.0, "--timeout", help="Request timeout."),
) -> None:
    """Test a webhook endpoint."""
    try:
        payload = simulate_webhook(template)
        result = test_webhook_endpoint(url, payload, expected_status, timeout)
        
        if result.success:
            console().print(f"[green]✓ Test passed[/green] ({result.response_time_ms:.1f}ms)")
            console().print(f"Message: {result.message}")
        else:
            console().print(f"[red]✗ Test failed[/red] ({result.response_time_ms:.1f}ms)")
            console().print(f"Message: {result.message}")
            if result.error:
                console().print(f"Error: {result.error}")
            raise typer.Exit(1)
        
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# ---- Random Data Generation --------------------------------------------------

random_app = typer.Typer(help="Random data generation tools.")
app.add_typer(random_app, name="random")


@random_app.command("secure")
def random_secure_cmd(
    type: str = typer.Argument(..., help="Type: bytes|string|int|float|token|password"),
    length: int = typer.Option(16, "--length", "-l", help="Length/size of output."),
    min_val: Optional[int] = typer.Option(None, "--min", help="Minimum value (for int/float)."),
    max_val: Optional[int] = typer.Option(None, "--max", help="Maximum value (for int/float)."),
    format: str = typer.Option("hex", "--format", help="Token format: hex|urlsafe|base64."),
    uppercase: bool = typer.Option(True, "--uppercase/--no-uppercase", help="Include uppercase letters."),
    lowercase: bool = typer.Option(True, "--lowercase/--no-lowercase", help="Include lowercase letters."),
    digits: bool = typer.Option(True, "--digits/--no-digits", help="Include digits."),
    symbols: bool = typer.Option(False, "--symbols", help="Include symbols."),
    count: int = typer.Option(1, "--count", "-n", help="Number of values to generate."),
) -> None:
    """Generate cryptographically secure random data."""
    try:
        results = []
        
        for _ in range(count):
            if type == "bytes":
                result = secure_random_bytes(length).hex()
            elif type == "string":
                result = secure_random_string(
                    length, uppercase, lowercase, digits, symbols
                )
            elif type == "int":
                min_v = min_val if min_val is not None else 0
                max_v = max_val if max_val is not None else 2**31 - 1
                result = secure_random_int(min_v, max_v)
            elif type == "float":
                min_v = float(min_val) if min_val is not None else 0.0
                max_v = float(max_val) if max_val is not None else 1.0
                result = secure_random_float(min_v, max_v)
            elif type == "token":
                result = generate_token(length, format)
            elif type == "password":
                result = generate_password_secure(length)
            else:
                console().print(f"[red]Error:[/red] Unknown type '{type}'")
                console().print("Available types: bytes, string, int, float, token, password")
                raise typer.Exit(1)
            
            results.append(result)
        
        if count == 1:
            console().print(str(results[0]))
        else:
            console().print_json(data=results)
            
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@random_app.command("mock")
def random_mock_cmd(
    type: str = typer.Argument(..., help="Type: name|email|phone|address|company|profile|card"),
    count: int = typer.Option(1, "--count", "-n", help="Number of items to generate."),
    seed: Optional[int] = typer.Option(None, "--seed", help="Random seed for reproducible results."),
    gender: str = typer.Option("any", "--gender", help="Gender: male|female|any."),
    format: str = typer.Option("###-###-####", "--format", help="Phone number format."),
    locale: str = typer.Option("en_US", "--locale", help="Locale for data generation."),
    null_chance: float = typer.Option(0.0, "--null-chance", help="Chance of null values (0.0-1.0)."),
) -> None:
    """Generate mock data (names, emails, addresses, etc.)."""
    try:
        from eyn_python.random.mock import MockDataOptions, Gender, Locale
        
        # Parse gender
        gender_map = {"male": Gender.MALE, "female": Gender.FEMALE, "any": Gender.ANY}
        gender_enum = gender_map.get(gender.lower(), Gender.ANY)
        
        # Parse locale
        locale_map = {
            "en_us": Locale.EN_US, "en_gb": Locale.EN_GB, "es_es": Locale.ES_ES,
            "fr_fr": Locale.FR_FR, "de_de": Locale.DE_DE, "it_it": Locale.IT_IT
        }
        locale_enum = locale_map.get(locale.lower(), Locale.EN_US)
        
        options = MockDataOptions(
            locale=locale_enum,
            seed=seed,
            include_null_chance=null_chance
        )
        
        generator = MockDataGenerator(options)
        results = []
        
        for _ in range(count):
            if type == "name":
                result = generator.full_name(gender_enum)
            elif type == "email":
                result = generator.email()
            elif type == "phone":
                result = generator.phone(format)
            elif type == "address":
                result = generator.address()
            elif type == "company":
                result = generator.company()
            elif type == "profile":
                result = generator.user_profile(gender_enum)
            elif type == "card":
                result = generator.credit_card()
            else:
                console().print(f"[red]Error:[/red] Unknown type '{type}'")
                console().print("Available types: name, email, phone, address, company, profile, card")
                raise typer.Exit(1)
            
            results.append(result)
        
        if count == 1:
            if isinstance(results[0], dict):
                console().print_json(data=results[0])
            else:
                console().print(str(results[0]))
        else:
            console().print_json(data=results)
            
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@random_app.command("lorem")
def random_lorem_cmd(
    type: str = typer.Argument(..., help="Type: words|sentences|paragraphs|text"),
    count: int = typer.Option(5, "--count", "-n", help="Number of items to generate."),
    word_set: str = typer.Option("lorem", "--word-set", help="Word set: lorem|business|tech."),
    min_words: int = typer.Option(5, "--min-words", help="Minimum words per sentence."),
    max_words: int = typer.Option(15, "--max-words", help="Maximum words per sentence."),
    min_sentences: int = typer.Option(3, "--min-sentences", help="Minimum sentences per paragraph."),
    max_sentences: int = typer.Option(8, "--max-sentences", help="Maximum sentences per paragraph."),
    start_with_lorem: bool = typer.Option(True, "--start-lorem/--no-start-lorem", help="Start with 'Lorem ipsum'."),
    seed: Optional[int] = typer.Option(None, "--seed", help="Random seed for reproducible results."),
    separator: str = typer.Option("\n\n", "--separator", help="Separator for multiple items."),
) -> None:
    """Generate lorem ipsum text with variations."""
    try:
        options = LoremOptions(
            seed=seed,
            start_with_lorem=start_with_lorem,
            include_punctuation=True,
            sentence_variance=True,
            paragraph_variance=True
        )
        
        generator = LoremGenerator(options)
        
        if type == "words":
            result = generator.words(count, word_set)
            console().print(" ".join(result))
        elif type == "sentences":
            result = generator.sentences(count, min_words, max_words, word_set)
            console().print(separator.join(result))
        elif type == "paragraphs":
            result = generator.paragraphs(count, min_sentences, max_sentences, 
                                        min_words, max_words, word_set)
            console().print(separator.join(result))
        elif type == "text":
            result = generator.text(count, (min_sentences, max_sentences),
                                  (min_words, max_words), word_set, separator)
            console().print(result)
        else:
            console().print(f"[red]Error:[/red] Unknown type '{type}'")
            console().print("Available types: words, sentences, paragraphs, text")
            raise typer.Exit(1)
            
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@random_app.command("seed")
def random_seed_cmd(
    seed: int = typer.Argument(..., help="Random seed value."),
    type: str = typer.Option("int", "--type", help="Type: int|float|choice|shuffle|string."),
    count: int = typer.Option(1, "--count", "-n", help="Number of values to generate."),
    min_val: int = typer.Option(0, "--min", help="Minimum value (for int/float)."),
    max_val: int = typer.Option(100, "--max", help="Maximum value (for int/float)."),
    choices: list[str] = typer.Option(["A", "B", "C"], "--choice", help="Choices for selection."),
    length: int = typer.Option(10, "--length", help="String length."),
    alphabet: str = typer.Option("abcdefghijklmnopqrstuvwxyz", "--alphabet", help="String alphabet."),
) -> None:
    """Generate seeded random data for reproducible results."""
    try:
        generator = SeededRandom(seed)
        results = []
        
        for _ in range(count):
            if type == "int":
                result = generator.int(min_val, max_val)
            elif type == "float":
                result = generator.float(float(min_val), float(max_val))
            elif type == "choice":
                result = generator.choice(choices)
            elif type == "string":
                result = generator.string(length, alphabet)
            elif type == "hex":
                result = generator.hex_string(length)
            elif type == "boolean":
                result = generator.boolean()
            elif type == "color":
                result = generator.color_hex()
            else:
                console().print(f"[red]Error:[/red] Unknown type '{type}'")
                console().print("Available types: int, float, choice, string, hex, boolean, color")
                raise typer.Exit(1)
            
            results.append(result)
        
        if type == "shuffle":
            shuffled = generator.shuffle(choices)
            console().print_json(data=shuffled)
        elif count == 1:
            console().print(str(results[0]))
        else:
            console().print_json(data=results)
            
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@random_app.command("dice")
def random_dice_cmd(
    notation: str = typer.Argument("1d6", help="Dice notation (e.g., 2d6+3, 1d20, 4d6dl1)."),
    count: int = typer.Option(1, "--count", "-n", help="Number of rolls."),
    seed: Optional[int] = typer.Option(None, "--seed", help="Random seed for reproducible results."),
    advantage: bool = typer.Option(False, "--advantage", help="Roll with advantage."),
    disadvantage: bool = typer.Option(False, "--disadvantage", help="Roll with disadvantage."),
    stats: bool = typer.Option(False, "--stats", help="Show dice statistics."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show individual rolls."),
    compare: Optional[str] = typer.Option(None, "--compare", help="Compare with another dice set."),
) -> None:
    """Roll dice with various configurations and modifiers."""
    try:
        if advantage:
            dice = parse_dice_notation(notation)
            dice.advantage = True
        elif disadvantage:
            dice = parse_dice_notation(notation)
            dice.disadvantage = True
        else:
            dice = parse_dice_notation(notation)
        
        if stats:
            dice_stats = dice.statistics()
            console().print(f"[blue]Dice Statistics for {notation}:[/blue]")
            console().print(f"Range: {dice_stats.min_possible} - {dice_stats.max_possible}")
            console().print(f"Average: {dice_stats.average:.2f}")
            console().print(f"Most likely: {dice_stats.most_likely}")
            
            # Show top probabilities
            sorted_probs = sorted(dice_stats.probability_distribution.items(), 
                                key=lambda x: x[1], reverse=True)[:5]
            console().print("\nTop probabilities:")
            for value, prob in sorted_probs:
                console().print(f"  {value}: {prob:.2%}")
            return
        
        if compare:
            comparison = compare_dice_sets(notation, compare, 1000)
            console().print(f"[blue]Comparison: {notation} vs {compare}[/blue]")
            for key, value in comparison.items():
                if "percentage" in key:
                    console().print(f"{key}: {value:.1f}%")
                else:
                    console().print(f"{key}: {value:.3f}")
            return
        
        results = []
        total_sum = 0
        
        for i in range(count):
            roll = dice.roll(seed)
            results.append(roll)
            total_sum += roll.final_total
            
            if verbose or count == 1:
                individual = f"[{', '.join(map(str, roll.individual_rolls))}]"
                modifier_str = f" + {roll.modifier}" if roll.modifier > 0 else f" - {abs(roll.modifier)}" if roll.modifier < 0 else ""
                
                if count > 1:
                    console().print(f"Roll {i+1}: {individual} = {roll.total}{modifier_str} = {roll.final_total}")
                else:
                    console().print(f"{roll.dice_notation}: {individual} = {roll.total}{modifier_str} = {roll.final_total}")
        
        if count > 1 and not verbose:
            console().print(f"\n[green]Summary:[/green]")
            console().print(f"Rolls: {count}")
            console().print(f"Total: {total_sum}")
            console().print(f"Average: {total_sum / count:.2f}")
            console().print(f"Range: {min(r.final_total for r in results)} - {max(r.final_total for r in results)}")
            
    except Exception as e:
        console().print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# ---- Future: plugin discovery (auto-register) -------------------------------
# from eyn_python.plugins import load_plugins
# for p in load_plugins():
#     p.register()

# ---- Scrape ------------------------------------------------------------------

scrape_app = typer.Typer(help="Advanced web scraping tools (httpx + selectolax).")
app.add_typer(scrape_app, name="scrape")


@scrape_app.command("get")
def scrape_get(
    url: str = typer.Argument(..., help="URL to fetch."),
    json: bool = typer.Option(False, "--json", help="Raw JSON output."),
) -> None:
    client = HttpClient()
    html = client.get(url)
    data = {"url": url, "bytes": len(html)}
    from eyn_python.display import build_get_render, print_data
    print_data(data, build_get_render(url, len(html)), json)


@scrape_app.command("select")
def scrape_select(
    url: str = typer.Argument(..., help="URL to fetch."),
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector to extract."),
    attr: Optional[str] = typer.Option(None, "--attr", help="Attribute to extract (optional)."),
    json: bool = typer.Option(False, "--json", help="Raw JSON output."),
) -> None:
    client = HttpClient()
    html = client.get(url)
    tree = parse_html(html)
    items = []
    for n in tree.css(selector):
        if attr:
            val = n.attributes.get(attr)
            if val:
                items.append(val)
        else:
            items.append(n.text(strip=True))
    data = {"count": len(items), "items": items}
    from eyn_python.display import build_select_render, print_data
    print_data(data, build_select_render(selector, len(items)), json)


@scrape_app.command("crawl")
def scrape_crawl(
    url: str = typer.Argument(..., help="Start URL."),
    max_pages: int = typer.Option(10, "--max-pages", help="Max pages to visit."),
    same_domain: bool = typer.Option(True, "--same-domain/--any-domain", help="Restrict to domain."),
) -> None:
    pages = 0
    for u, html in crawl(url, max_pages=max_pages, same_domain=same_domain):
        console().print(f"Visited: {u} ({len(html)} bytes)")
        pages += 1
    console().print(f"Done. {pages} pages visited.")


@scrape_app.command("crawl-async")
def scrape_crawl_async(
    url: str = typer.Argument(..., help="Start URL."),
    max_pages: int = typer.Option(20, "--max-pages", help="Max pages to visit."),
    concurrency: int = typer.Option(5, "--concurrency", "-c", help="Concurrent requests."),
    delay: float = typer.Option(0.5, "--delay", help="Per-origin delay seconds."),
    same_domain: bool = typer.Option(True, "--same-domain/--any-domain", help="Restrict to domain."),
    obey_robots: bool = typer.Option(True, "--robots/--no-robots", help="Respect robots.txt."),
    user_agent: Optional[str] = typer.Option(None, "--user-agent", help="Custom User-Agent."),
) -> None:
    """Concurrent crawler with rate limiting and robots.txt compliance."""
    import asyncio as _asyncio

    results = _asyncio.run(
        crawl_async(
            url,
            max_pages=max_pages,
            concurrency=concurrency,
            delay=delay,
            same_domain=same_domain,
            obey_robots=obey_robots,
            user_agent=user_agent,
        )
    )
    for u, html in results:
        console().print(f"Visited: {u} ({len(html)} bytes)")
    console().print(f"Done. {len(results)} pages visited.")


@scrape_app.command("links")
def scrape_links(
    url: str = typer.Argument(..., help="URL to fetch and list links."),
) -> None:
    client = HttpClient()
    html = client.get(url)
    links = extract_links(html, url)
    console().print_json(data={"count": len(links), "links": links})


@scrape_app.command("sitemap")
def scrape_sitemap(
    base: str = typer.Argument(..., help="Base URL, e.g. https://example.com"),
    json: bool = typer.Option(False, "--json", help="Raw JSON output."),
) -> None:
    urls = fetch_sitemap_urls(base)
    data = {"count": len(urls), "urls": urls}
    from eyn_python.display import build_list_render, print_data
    print_data(data, build_list_render("Sitemap URLs", "URL", urls[:50]), json)


@scrape_app.command("meta")
def scrape_meta(
    url: str = typer.Argument(..., help="URL to fetch and extract metadata."),
    json: bool = typer.Option(False, "--json", help="Raw JSON output."),
) -> None:
    client = HttpClient()
    html = client.get(url)
    data = extract_metadata(html, url)
    from eyn_python.display import build_meta_render, print_data
    print_data(data, build_meta_render(data), json)


@scrape_app.command("forms")
def scrape_forms_cmd(
    url: str = typer.Argument(..., help="URL to fetch and list forms."),
    json: bool = typer.Option(False, "--json", help="Raw JSON output."),
) -> None:
    client = HttpClient()
    html = client.get(url)
    data = extract_forms(html, url)
    from eyn_python.display import build_forms_render, print_data
    print_data(data, build_forms_render(data), json)


@scrape_app.command("assets")
def scrape_assets_cmd(
    url: str = typer.Argument(..., help="URL to fetch and list assets (img/js/css/media)."),
    json: bool = typer.Option(False, "--json", help="Raw JSON output."),
) -> None:
    client = HttpClient()
    html = client.get(url)
    data = extract_assets(html, url)
    from eyn_python.display import build_assets_summary_render, print_data
    print_data(data, build_assets_summary_render(data), json)


@scrape_app.command("download-asset")
def scrape_download_asset(
    url: str = typer.Argument(..., help="Asset URL to download."),
    out: Path = typer.Option(Path.cwd() / "out", "--out", "-o", help="Output directory."),
    json: bool = typer.Option(False, "--json", help="Raw JSON output."),
) -> None:
    console().print(f"[blue]Downloading asset from {url}...[/blue]")
    dst = download_asset(url, out)
    data = {"path": str(dst)}
    from eyn_python.display import build_saved_panel, print_data
    print_data(data, build_saved_panel("Downloaded", str(dst)), json)
    console().print(f"[green]✓ Asset saved to {dst}[/green]")


@scrape_app.command("save")
def scrape_save_page(
    url: str = typer.Argument(..., help="Page URL to fetch and save HTML."),
    out: Path = typer.Option(Path.cwd() / "out", "--out", "-o", help="Output directory."),
    json: bool = typer.Option(False, "--json", help="Raw JSON output."),
) -> None:
    result = save_page(url, out)
    from eyn_python.display import build_saved_panel, print_data
    print_data(result, build_saved_panel("Saved Page", result.get("path", "")), json)


@scrape_app.command("robots")
def scrape_robots(
    base: str = typer.Argument(..., help="Base site URL, e.g. https://example.com"),
    json: bool = typer.Option(False, "--json", help="Raw JSON output."),
) -> None:
    info = fetch_robots_txt(base)
    from eyn_python.display import build_robots_render, print_data
    print_data(info, build_robots_render(info), json)


@scrape_app.command("can-fetch")
def scrape_can_fetch(
    base: str = typer.Argument(..., help="Base site URL, e.g. https://example.com"),
    url: str = typer.Argument(..., help="Target URL to check."),
    agent: str = typer.Option("Mozilla/5.0", "--agent", help="User-Agent."),
    json: bool = typer.Option(False, "--json", help="Raw JSON output."),
) -> None:
    r = fetch_robots_txt(base)
    text = r.get("text")
    text_str = text if isinstance(text, str) else None
    ok = can_fetch(base, agent, url, text_str)
    data = {"allowed": ok}
    from eyn_python.display import print_data
    print_data(data, Panel("Allowed" if ok else "Blocked", title="Robots"), json)


@scrape_app.command("search")
def scrape_search(
    url: str = typer.Argument(..., help="Start URL to crawl."),
    keywords: list[str] = typer.Option(..., "--kw", help="Keyword(s) to search, repeatable."),
    max_pages: int = typer.Option(50, "--max-pages", help="Max pages to visit."),
    concurrency: int = typer.Option(6, "--concurrency", "-c", help="Concurrent requests."),
    delay: float = typer.Option(0.4, "--delay", help="Per-origin delay seconds."),
    same_domain: bool = typer.Option(True, "--same-domain/--any-domain", help="Restrict to domain."),
    obey_robots: bool = typer.Option(True, "--robots/--no-robots", help="Respect robots.txt."),
    user_agent: Optional[str] = typer.Option(None, "--user-agent", help="Custom User-Agent."),
    ignore_case: bool = typer.Option(True, "--ignore-case/--case", help="Case-insensitive matches."),
    regex: bool = typer.Option(False, "--regex", help="Treat keywords as regex patterns."),
    whole_word: bool = typer.Option(False, "--word", help="Whole word matches only."),
) -> None:
    import asyncio as _asyncio
    hits = _asyncio.run(
        search_async(
            url,
            keywords,
            max_pages=max_pages,
            concurrency=concurrency,
            delay=delay,
            same_domain=same_domain,
            obey_robots=obey_robots,
            user_agent=user_agent,
            ignore_case=ignore_case,
            regex=regex,
            whole_word=whole_word,
        )
    )
    # Sort by total matches desc
    hits_sorted = sorted(hits, key=lambda x: sum(x[1].values()), reverse=True)
    console().print_json(data=[{"url": u, "matches": m} for u, m in hits_sorted])


@scrape_app.command("screenshot")
def scrape_screenshot(
    url: str = typer.Argument(..., help="URL to screenshot."),
    out: Path = typer.Option(Path.cwd() / "screenshot.png", "--out", "-o", help="Output file."),
    no_full_page: bool = typer.Option(False, "--no-full-page", help="Screenshot the viewport only."),
) -> None:
    """Take a screenshot of a webpage."""
    import asyncio
    asyncio.run(take_screenshot(url, out, full_page=not no_full_page))
    console().print(f"Screenshot saved to {out}")


@scrape_app.command("pdf")
def scrape_pdf(
    url: str = typer.Argument(..., help="URL to save as PDF."),
    out: Path = typer.Option(Path.cwd() / "page.pdf", "--out", "-o", help="Output file."),
) -> None:
    """Save a webpage as a PDF."""
    import asyncio
    asyncio.run(save_as_pdf(url, out))
    console().print(f"PDF saved to {out}")


# ---- Clean (unnecessary files) ----------------------------------------------

@app.command("clean")
def clean_cmd(
    src: Path = typer.Argument(Path.cwd(), exists=True, readable=True, help="Root directory to scan."),
    apply: bool = typer.Option(False, "--apply", help="Apply deletions (otherwise dry-run)."),
    remove_empty_dirs: bool = typer.Option(False, "--remove-empty", help="Remove empty directories after deletion."),
    include_hidden: bool = typer.Option(False, "--hidden", help="Include hidden files/dirs in matching."),
    pattern: list[str] = typer.Option([], "--pattern", help="Extra glob patterns to remove (repeatable)."),
    exclude: list[str] = typer.Option([], "--exclude", help="Exclude glob patterns (repeatable)."),
) -> None:
    settings = CleanSettings()
    if pattern:
        settings.patterns.extend(pattern)
    if exclude:
        settings.exclude.extend(exclude)
    settings.apply = apply
    settings.remove_empty_dirs = remove_empty_dirs
    settings.include_hidden = include_hidden

    result = clean_run(src, settings)
    console().print_json(data=result)


# ---- System: close all browsers --------------------------------------------

@app.command("close-browsers")
def close_browsers_cmd(
    app: list[str] = typer.Option([], "--app", help="Specific browser app names to close (repeatable)."),
    force: bool = typer.Option(False, "--force", help="Force kill if graceful quit fails."),
    timeout: float = typer.Option(5.0, "--timeout", help="Seconds to wait for graceful quit."),
) -> None:
    apps = app or get_common_browser_app_names()
    res = close_browsers(apps, timeout_seconds=timeout, force=force)
    console().print_json(data={
        "attempted": res.attempted,
        "closed": res.closed,
        "forced": res.forced,
    })

# ---- Archive (compress/extract) ---------------------------------------------

archive_app = typer.Typer(help="Create and extract archives (zip, tar, tar.gz, tar.bz2, tar.xz).")
app.add_typer(archive_app, name="archive")


@archive_app.command("compress")
def archive_compress(
    src: Path = typer.Argument(..., exists=True, readable=True, help="Source file or directory."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Output file or directory."),
    format: str = typer.Option("zip", "--format", "-f", help="zip|tar|tar.gz|tar.bz2|tar.xz"),
    level: int = typer.Option(6, "--level", help="Compression level (0-9)."),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", help="Recurse directories."),
    exclude: list[str] = typer.Option([], "--exclude", help="Glob patterns to exclude (repeatable)."),
) -> None:
    allowed_formats = {"zip", "tar", "tar.gz", "tar.bz2", "tar.xz"}
    if format not in allowed_formats:
        raise typer.BadParameter(f"Invalid format: {format}. Choose one of: {', '.join(sorted(allowed_formats))}")
    fmt: ArchiveFormat = cast(ArchiveFormat, format)
    settings = ArchiveSettings(format=fmt, level=level, recursive=recursive, exclude=exclude)
    dst = create_archive(src, out, settings)
    console().print(f"Saved -> {dst}")


@archive_app.command("extract")
def archive_extract(
    archive: Path = typer.Argument(..., exists=True, readable=True, help="Archive to extract."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Output directory."),
) -> None:
    dst = extract_archive(archive, out)
    console().print(f"Extracted -> {dst}")

# ---- System info --------------------------------------------------------------

@app.command("specs")
def specs_cmd(
    json: bool = typer.Option(False, "--json", help="Raw JSON output."),
    save: bool = typer.Option(False, "--save", help="Save JSON to Downloads folder."),
) -> None:
    """Show basic system specs (CPU, memory, disk)."""
    data = detect_specs()
    data_dict = data if isinstance(data, dict) else asdict(data)
    data_typed: Dict[str, Any] = cast(Dict[str, Any], data_dict)
    print_data(data_typed, build_specs_render(data_typed), json)
    if save:
        downloads = user_downloads_dir()
        ensure_dir(downloads)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        dest = downloads / f"eyn_specs_{ts}.json"
        dest.write_text(json_module.dumps(data_typed, indent=2), encoding="utf-8")
        console().print(f"Saved -> {dest}")


@app.command("netinfo")
def netinfo_cmd(json: bool = typer.Option(False, "--json", help="Raw JSON output.")) -> None:
    """Show network interfaces and traffic counters."""
    data = network_info()
    print_data(data, build_netinfo_render(data), json)


@app.command("uptime")
def uptime_cmd(json: bool = typer.Option(False, "--json", help="Raw JSON output.")) -> None:
    """Show system uptime and load averages (if available)."""
    data = uptime_info()
    print_data(data, build_uptime_render(data), json)


@app.command("disks")
def disks_cmd(json: bool = typer.Option(False, "--json", help="Raw JSON output.")) -> None:
    """List mounted disk partitions and usage."""
    data = partitions_info()
    print_data(data, build_disks_render(data), json)


@app.command("top")
def top_cmd(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of processes."),
    json: bool = typer.Option(False, "--json", help="Raw JSON output."),
) -> None:
    """Show top processes by CPU and memory."""
    data = top_processes(limit=limit)
    print_data(data, build_top_render(data), json)


@app.command("battery")
def battery_cmd(json: bool = typer.Option(False, "--json", help="Raw JSON output.")) -> None:
    """Show battery status (if present)."""
    data = battery_info()
    print_data(data, build_battery_render(data), json)


@app.command("temps")
def temps_cmd(json: bool = typer.Option(False, "--json", help="Raw JSON output.")) -> None:
    """Show temperature sensors (if available)."""
    data = temperatures_info()
    print_data(data, build_temps_render(data), json)


@app.command("ports")
def ports_cmd(json: bool = typer.Option(False, "--json", help="Raw JSON output.")) -> None:
    """List listening TCP/UDP ports."""
    data = listening_ports()
    print_data(data, build_ports_render(data), json)


@app.command("pubip")
def pubip_cmd(json: bool = typer.Option(False, "--json", help="Raw JSON output.")) -> None:
    """Show your public IP (best-effort)."""
    data = public_ip()
    print_data(data, build_pubip_render(data), json)


@app.command("latency")
def latency_cmd(
    url: str = typer.Option("https://www.google.com", "--url", help="URL to check."),
    attempts: int = typer.Option(3, "--attempts", "-a", help="Number of attempts."),
    timeout: float = typer.Option(5.0, "--timeout", "-t", help="Per-request timeout seconds."),
    json: bool = typer.Option(False, "--json", help="Raw JSON output."),
) -> None:
    """HTTP latency check to a URL (ms)."""
    data = http_latency(url=url, attempts=attempts, timeout=timeout)
    print_data(data, build_latency_render(data), json)


@app.command("uuid")
def uuid_cmd() -> None:
    """Generate a version 4 UUID."""
    new_uuid = generate_uuid()
    console().print(new_uuid)


@app.command("password")
def password_cmd(
    length: int = typer.Option(16, "--length", "-l", help="Password length."),
    no_symbols: bool = typer.Option(False, "--no-symbols", help="Exclude symbols."),
) -> None:
    """Generate a secure, random password."""
    password = generate_password(length=length, use_symbols=not no_symbols)
    console().print(password)


@app.command("hash")
def hash_cmd(
    file: Path = typer.Argument(..., exists=True, readable=True, help="File to hash."),
    algorithm: str = typer.Option("sha256", "--algorithm", "-a", help="Hash algorithm."),
) -> None:
    """Generate a hash for a file."""
    digest = hash_file(file, algorithm)
    console().print(f"{algorithm}: {digest}")


base64_app = typer.Typer(help="Base64 encoder/decoder.")
app.add_typer(base64_app, name="base64")


@base64_app.command("encode")
def base64_encode_cmd(text: str) -> None:
    """Encode a string to Base64."""
    encoded = encode_base64(text)
    console().print(encoded)


@base64_app.command("decode")
def base64_decode_cmd(text: str) -> None:
    """Decode a Base64 string."""
    decoded = decode_base64(text)
    console().print(decoded)


url_app = typer.Typer(help="URL encoder/decoder.")
app.add_typer(url_app, name="url")


@url_app.command("encode")
def url_encode_cmd(text: str) -> None:
    """Encode a string to be URL-safe."""
    encoded = encode_url(text)
    console().print(encoded)


@url_app.command("decode")
def url_decode_cmd(text: str) -> None:
    """Decode a URL-safe string."""
    decoded = decode_url(text)
    console().print(decoded)


timestamp_app = typer.Typer(help="Timestamp converter.")
app.add_typer(timestamp_app, name="timestamp")


@timestamp_app.command("to")
def timestamp_to_cmd(
    date_str: str = typer.Argument(..., help="Date string (YYYY-MM-DD HH:MM:SS)"),
) -> None:
    """Convert a date string to a Unix timestamp."""
    dt = datetime.fromisoformat(date_str)
    ts = to_timestamp(dt)
    console().print(ts)


@timestamp_app.command("from")
def timestamp_from_cmd(
    ts: int = typer.Argument(..., help="Unix timestamp"),
) -> None:
    """Convert a Unix timestamp to a date string."""
    dt = from_timestamp(ts)
    console().print(dt.isoformat())


@app.command("qr")
def qr_cmd(
    text: str = typer.Argument(..., help="Text or URL to encode."),
    out: Path = typer.Option("qrcode.png", "--out", "-o", help="Output file."),
) -> None:
    """Generate a QR code."""
    generate_qr_code(text, out)
    console().print(f"QR code saved to {out}")


@app.command("wc")
def wc_cmd(
    text: str = typer.Argument("", help="Text to count."),
    file: Optional[Path] = typer.Option(None, "--file", "-f", exists=True, readable=True, help="File to count."),
) -> None:
    """Count lines, words, and characters."""
    if file:
        text = file.read_text()
    
    counts = word_count(text)
    console().print(f"Lines: {counts['lines']}")
    console().print(f"Words: {counts['words']}")
    console().print(f"Characters: {counts['chars']}")


@app.command("color")
def color_cmd(
    luminosity: str = typer.Option("any", "--luminosity", "-l", help="any|light|dark|pastel"),
    alpha: float = typer.Option(-1.0, "--alpha", "-a", help="Optional alpha 0..1. Omit or negative to skip."),
    count: int = typer.Option(1, "--count", "-n", help="How many colors to generate."),
    no_hash: bool = typer.Option(False, "--no-hash", help="Exclude leading # in output."),
    seed: Optional[int] = typer.Option(None, "--seed", help="Deterministic seed (applied per color index)."),
) -> None:
    """Generate random hex color(s)."""
    include_hash = not no_hash
    use_alpha = None if alpha < 0 else alpha
    if count <= 1:
        color = random_hex_color(luminosity=luminosity, alpha=use_alpha, include_hash=include_hash, seed=seed)
        console().print(color)
        return
    colors: list[str] = []
    for i in range(count):
        per_seed = None if seed is None else (seed + i)
        colors.append(
            random_hex_color(luminosity=luminosity, alpha=use_alpha, include_hash=include_hash, seed=per_seed)
        )
    console().print_json(data=colors)


@app.command("headers")
def headers_cmd(
    url: str = typer.Argument(..., help="URL to fetch headers from."),
) -> None:
    """Fetch and display HTTP headers from a URL."""
    client = HttpClient()
    headers = client.get_headers(url)
    console().print_json(data=headers)


# ---- Temp files cleaner -------------------------------------------------------

@app.command("clean-temp")
def clean_temp_cmd(
    root: Optional[Path] = typer.Option(None, "--root", help="Temp directory to clean (defaults to system temp)."),
    hours: float = typer.Option(24.0, "--hours", help="Delete files older than N hours."),
    apply: bool = typer.Option(False, "--apply", help="Apply deletions (otherwise dry-run)."),
    no_remove_empty: bool = typer.Option(False, "--no-remove-empty", help="Do not remove empty directories."),
    include_hidden: bool = typer.Option(True, "--include-hidden/--no-include-hidden", help="Include hidden files."),
    json: bool = typer.Option(False, "--json", help="Raw JSON output."),
) -> None:
    settings = TempCleanSettings(
        older_than_hours=hours,
        include_hidden=include_hidden,
        apply=apply,
        remove_empty_dirs=not no_remove_empty,
    )
    result = clean_temp(root, settings)
    from eyn_python.display import build_clean_render, print_data
    print_data(result, build_clean_render(result), json)

if __name__ == "__main__":
    app()


