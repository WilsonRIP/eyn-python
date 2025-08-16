from urllib.parse import quote, unquote

def encode_url(text: str) -> str:
    return quote(text)

def decode_url(encoded_text: str) -> str:
    return unquote(encoded_text)
