from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from eyn_python.logging import get_logger, console
from eyn_python.config import GlobalSettings, DownloadSettings, ConvertSettings
from eyn_python.download.youtube import DownloadJob, download
from eyn_python.convert.core import plan_conversions, convert_all
from eyn_python.media import ffprobe_json, extract_audio, trim_media, AudioExtractOptions
from eyn_python.scrape import HttpClient, AsyncHttpClient, parse_html, extract_all, extract_links, crawl, crawl_async, fetch_sitemap_urls, search_async
from eyn_python.archive import ArchiveSettings, create_archive, extract_archive
from eyn_python.clean import CleanSettings, clean as clean_run
from eyn_python.system import close_browsers, get_common_browser_app_names

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
    convert_all(jobs)

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
) -> None:
    client = HttpClient()
    html = client.get(url)
    console().print(f"Fetched {len(html)} bytes")


@scrape_app.command("select")
def scrape_select(
    url: str = typer.Argument(..., help="URL to fetch."),
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector to extract."),
    attr: Optional[str] = typer.Option(None, "--attr", help="Attribute to extract (optional)."),
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
    console().print_json(data={"count": len(items), "items": items})


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
) -> None:
    urls = fetch_sitemap_urls(base)
    console().print_json(data={"count": len(urls), "urls": urls})


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
    settings = ArchiveSettings(format=format, level=level, recursive=recursive, exclude=exclude)
    dst = create_archive(src, out, settings)
    console().print(f"Saved -> {dst}")


@archive_app.command("extract")
def archive_extract(
    archive: Path = typer.Argument(..., exists=True, readable=True, help="Archive to extract."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Output directory."),
) -> None:
    dst = extract_archive(archive, out)
    console().print(f"Extracted -> {dst}")

if __name__ == "__main__":
    app()


