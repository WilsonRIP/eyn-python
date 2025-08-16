import hashlib
from pathlib import Path

def hash_file(path: Path, algorithm: str = 'sha256') -> str:
    h = hashlib.new(algorithm)
    with open(path, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()
