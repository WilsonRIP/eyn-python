import base64

def encode_base64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()

def decode_base64(encoded_text: str) -> str:
    return base64.b64decode(encoded_text.encode()).decode()
