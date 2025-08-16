from __future__ import annotations

from pathlib import Path
from typing import Optional, cast
import json as json_module
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
from eyn_python.media import ffprobe_json, extract_audio, trim_media, AudioExtractOptions
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
    asyncio.run(download_instagram_video(url, out))
    console().print(f"Video saved to {out}")

@dl_app.command("tt")
def dl_tt(
    url: str = typer.Argument(..., help="TikTok video URL."),
    out: Path = typer.Option(Path.cwd() / "out.mp4", "--out", "-o", help="Output file."),
) -> None:
    """
    Download a video from TikTok.
    """
    import asyncio
    asyncio.run(download_tiktok_video(url, out))
    console().print(f"Video saved to {out}")

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
    dst = download_asset(url, out)
    data = {"path": str(dst)}
    from eyn_python.display import build_saved_panel, print_data
    print_data(data, build_saved_panel("Downloaded", str(dst)), json)


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


