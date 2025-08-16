from pathlib import Path
from playwright.async_api import async_playwright

async def save_as_pdf(url: str, out: Path) -> None:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        await page.pdf(path=out)
        await browser.close()
