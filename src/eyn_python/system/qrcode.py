from pathlib import Path
import qrcode

def generate_qr_code(text: str, path: Path) -> None:
    img = qrcode.make(text)
    img.save(path)
