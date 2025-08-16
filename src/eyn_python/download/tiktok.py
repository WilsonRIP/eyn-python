import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import httpx

async def download_tiktok_video(url: str, out: Path) -> None:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        
        video_url = await page.get_attribute('video', 'src')
        if not video_url:
            raise ValueError("Could not find video URL on the page.")

        async with httpx.AsyncClient() as client:
            response = await client.get(video_url)
            response.raise_for_status()
            
            with open(out, 'wb') as f:
                f.write(response.content)
        
        await browser.close()
