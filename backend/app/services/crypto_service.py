from cryptography.fernet import Fernet
from app.config import settings

# Initialize symmetric Fernet cipher from environment secret
fernet = Fernet(settings.FERNET_SECRET_KEY.encode())


def encrypt_secret(value: str) -> str:
    """Encrypts sensitive values (such as BOT_TOKEN) using Fernet at rest."""
    if not value:
        return ""
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(encrypted_value: str) -> str:
    """Decrypts a Fernet ciphertext back to plaintext for container runtime injection."""
    if not encrypted_value:
        return ""
    return fernet.decrypt(encrypted_value.encode("utf-8")).decode("utf-8")


def mask_secret(value: str) -> str:
    """
    Returns masked value formatted as '••••1234'.
    Never returns full secret value after initial save.
    """
    if not value:
        return ""
    if len(value) <= 4:
        return "••••"
    return "••••" + value[-4:]
