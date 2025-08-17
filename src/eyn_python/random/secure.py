from __future__ import annotations

import secrets
import string
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class CryptoRandom:
    """Cryptographically secure random data generator."""
    
    @staticmethod
    def bytes(length: int) -> bytes:
        """Generate cryptographically secure random bytes."""
        return secrets.token_bytes(length)
    
    @staticmethod
    def hex(length: int) -> str:
        """Generate cryptographically secure random hex string."""
        return secrets.token_hex(length)
    
    @staticmethod
    def urlsafe(length: int) -> str:
        """Generate cryptographically secure URL-safe string."""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def string(length: int, alphabet: str = string.ascii_letters + string.digits) -> str:
        """Generate cryptographically secure random string from alphabet."""
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def int(min_val: int = 0, max_val: int = 2**32 - 1) -> int:
        """Generate cryptographically secure random integer in range."""
        return secrets.randbelow(max_val - min_val + 1) + min_val
    
    @staticmethod
    def float(min_val: float = 0.0, max_val: float = 1.0) -> float:
        """Generate cryptographically secure random float in range."""
        random_int = secrets.randbelow(2**32)
        normalized = random_int / (2**32 - 1)
        return min_val + (max_val - min_val) * normalized
    
    @staticmethod
    def choice(sequence: List) -> any:
        """Cryptographically secure choice from sequence."""
        if not sequence:
            raise ValueError("Cannot choose from empty sequence")
        return sequence[secrets.randbelow(len(sequence))]
    
    @staticmethod
    def shuffle(sequence: List) -> List:
        """Cryptographically secure shuffle of sequence."""
        result = sequence.copy()
        for i in range(len(result) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            result[i], result[j] = result[j], result[i]
        return result


def secure_random_bytes(length: int) -> bytes:
    """Generate cryptographically secure random bytes."""
    return CryptoRandom.bytes(length)


def secure_random_string(
    length: int,
    include_uppercase: bool = True,
    include_lowercase: bool = True,
    include_digits: bool = True,
    include_symbols: bool = False,
    custom_alphabet: Optional[str] = None,
) -> str:
    """Generate cryptographically secure random string."""
    if custom_alphabet:
        return CryptoRandom.string(length, custom_alphabet)
    
    alphabet = ""
    if include_uppercase:
        alphabet += string.ascii_uppercase
    if include_lowercase:
        alphabet += string.ascii_lowercase
    if include_digits:
        alphabet += string.digits
    if include_symbols:
        alphabet += "!@#$%^&*()-_=+[]{}|;:,.<>?"
    
    if not alphabet:
        raise ValueError("At least one character type must be included")
    
    return CryptoRandom.string(length, alphabet)


def secure_random_int(min_val: int = 0, max_val: int = 2**32 - 1) -> int:
    """Generate cryptographically secure random integer."""
    return CryptoRandom.int(min_val, max_val)


def secure_random_float(min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Generate cryptographically secure random float."""
    return CryptoRandom.float(min_val, max_val)


def generate_token(length: int = 32, format: str = "hex") -> str:
    """Generate cryptographically secure token.
    
    Args:
        length: Token length (in bytes for hex/urlsafe, characters for base64)
        format: Token format - 'hex', 'urlsafe', or 'base64'
    """
    if format == "hex":
        return secrets.token_hex(length)
    elif format == "urlsafe":
        return secrets.token_urlsafe(length)
    elif format == "base64":
        import base64
        return base64.b64encode(secrets.token_bytes(length)).decode('ascii')
    else:
        raise ValueError("Format must be 'hex', 'urlsafe', or 'base64'")


def generate_password_secure(
    length: int = 16,
    min_uppercase: int = 1,
    min_lowercase: int = 1,
    min_digits: int = 1,
    min_symbols: int = 1,
    exclude_ambiguous: bool = True,
) -> str:
    """Generate cryptographically secure password with requirements."""
    
    # Define character sets
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    symbols = "!@#$%^&*()-_=+[]{}|;:,.<>?"
    
    # Remove ambiguous characters if requested
    if exclude_ambiguous:
        ambiguous = "0O1lI"
        uppercase = ''.join(c for c in uppercase if c not in ambiguous)
        lowercase = ''.join(c for c in lowercase if c not in ambiguous)
        digits = ''.join(c for c in digits if c not in ambiguous)
    
    # Check if requirements are feasible
    min_total = min_uppercase + min_lowercase + min_digits + min_symbols
    if min_total > length:
        raise ValueError(f"Minimum requirements ({min_total}) exceed password length ({length})")
    
    # Generate required characters
    password_chars = []
    password_chars.extend(CryptoRandom.choice(uppercase) for _ in range(min_uppercase))
    password_chars.extend(CryptoRandom.choice(lowercase) for _ in range(min_lowercase))
    password_chars.extend(CryptoRandom.choice(digits) for _ in range(min_digits))
    password_chars.extend(CryptoRandom.choice(symbols) for _ in range(min_symbols))
    
    # Fill remaining length with random characters from all sets
    all_chars = uppercase + lowercase + digits + symbols
    remaining = length - len(password_chars)
    password_chars.extend(CryptoRandom.choice(all_chars) for _ in range(remaining))
    
    # Shuffle the password
    return ''.join(CryptoRandom.shuffle(password_chars))


def generate_api_key(
    length: int = 32,
    prefix: Optional[str] = None,
    separator: str = "_",
) -> str:
    """Generate API key with optional prefix."""
    key = secrets.token_urlsafe(length)
    if prefix:
        return f"{prefix}{separator}{key}"
    return key


def generate_session_id(length: int = 24) -> str:
    """Generate session ID."""
    return secrets.token_urlsafe(length)


def generate_uuid_like() -> str:
    """Generate UUID-like string using secure random."""
    # Generate 16 random bytes
    random_bytes = secrets.token_bytes(16)
    
    # Format as UUID
    hex_string = random_bytes.hex()
    return f"{hex_string[:8]}-{hex_string[8:12]}-{hex_string[12:16]}-{hex_string[16:20]}-{hex_string[20:32]}"


def generate_csrf_token(length: int = 32) -> str:
    """Generate CSRF token."""
    return secrets.token_urlsafe(length)


def generate_nonce(length: int = 16) -> str:
    """Generate cryptographic nonce."""
    return secrets.token_hex(length)
