import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import httpx

from eyn_python.download.progress import download_with_progress

async def download_instagram_video(url: str, out: Path) -> None:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        
        video_url = await page.get_attribute('meta[property="og:video"]', 'content')
        if not video_url:
            raise ValueError("Could not find video URL on the page.")

        await browser.close()
        
        # Download with progress bar
        filename = out.name
        download_with_progress(video_url, out, filename)
