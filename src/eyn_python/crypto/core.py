from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from pathlib import Path
from typing import Union, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from eyn_python.logging import get_logger

log = get_logger(__name__)


def generate_key() -> bytes:
    """Generate a new encryption key."""
    return Fernet.generate_key()


def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
    """Derive a key from a password using PBKDF2."""
    if salt is None:
        salt = secrets.token_bytes(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt


def encrypt_text(text: str, key: Union[str, bytes]) -> str:
    """Encrypt text using Fernet."""
    if isinstance(key, str):
        key = key.encode()
    
    f = Fernet(key)
    encrypted = f.encrypt(text.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_text(encrypted_text: str, key: Union[str, bytes]) -> str:
    """Decrypt text using Fernet."""
    if isinstance(key, str):
        key = key.encode()
    
    f = Fernet(key)
    encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode())
    decrypted = f.decrypt(encrypted_bytes)
    return decrypted.decode()


def encrypt_file(input_path: Union[str, Path], output_path: Union[str, Path], 
                key: Union[str, bytes]) -> None:
    """Encrypt a file."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    if isinstance(key, str):
        key = key.encode()
    
    f = Fernet(key)
    
    with open(input_path, 'rb') as infile:
        data = infile.read()
    
    encrypted_data = f.encrypt(data)
    
    with open(output_path, 'wb') as outfile:
        outfile.write(encrypted_data)


def decrypt_file(input_path: Union[str, Path], output_path: Union[str, Path], 
                key: Union[str, bytes]) -> None:
    """Decrypt a file."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    if isinstance(key, str):
        key = key.encode()
    
    f = Fernet(key)
    
    with open(input_path, 'rb') as infile:
        encrypted_data = infile.read()
    
    decrypted_data = f.decrypt(encrypted_data)
    
    with open(output_path, 'wb') as outfile:
        outfile.write(decrypted_data)


def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[str, bytes]:
    """Hash a password using PBKDF2."""
    if salt is None:
        salt = secrets.token_bytes(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    
    hash_bytes = kdf.derive(password.encode())
    hash_hex = hash_bytes.hex()
    
    return hash_hex, salt


def verify_password(password: str, hash_hex: str, salt: bytes) -> bool:
    """Verify a password against its hash."""
    try:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        hash_bytes = kdf.derive(password.encode())
        return hash_bytes.hex() == hash_hex
    except Exception:
        return False


def create_secure_token(data: str, secret_key: str, expires_in: int = 3600) -> str:
    """Create a secure token with expiration."""
    timestamp = str(int(time.time()) + expires_in)
    message = f"{data}:{timestamp}"
    
    # Create HMAC signature
    signature = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Combine data, timestamp, and signature
    token_data = f"{message}:{signature}"
    return base64.urlsafe_b64encode(token_data.encode()).decode()


def verify_secure_token(token: str, secret_key: str) -> Optional[str]:
    """Verify a secure token and return the data if valid."""
    try:
        # Decode token
        token_data = base64.urlsafe_b64decode(token.encode()).decode()
        parts = token_data.split(':')
        
        if len(parts) != 3:
            return None
        
        data, timestamp, signature = parts
        
        # Check expiration
        if int(time.time()) > int(timestamp):
            return None
        
        # Verify signature
        message = f"{data}:{timestamp}"
        expected_signature = hmac.new(
            secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if signature == expected_signature:
            return data
        else:
            return None
            
    except Exception:
        return None
