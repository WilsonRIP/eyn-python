import secrets
import string

def generate_password(length: int = 16, use_symbols: bool = True) -> str:
    alphabet = string.ascii_letters + string.digits
    if use_symbols:
        alphabet += string.punctuation
    
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password
