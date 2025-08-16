from pathlib import Path
from playwright.async_api import async_playwright

async def take_screenshot(url: str, out: Path, full_page: bool = True) -> None:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        await page.screenshot(path=out, full_page=full_page)
        await browser.close()
