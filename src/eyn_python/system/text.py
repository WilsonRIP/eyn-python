from typing import Dict

def word_count(text: str) -> Dict[str, int]:
    lines = text.splitlines()
    words = text.split()
    chars = len(text)
    return {
        "lines": len(lines),
        "words": len(words),
        "chars": chars,
    }
