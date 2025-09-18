from cryptography.fernet import Fernet
from django.conf import settings

cipher = Fernet(settings.ENCRYPTION_KEY)

def encrypt_text(plain_text: str) -> str:
    """Encrypt a plain text string."""
    return cipher.encrypt(plain_text.encode()).decode()
    
def decrypt_text(encrypted_text: str) -> str:
    """Decrypt an encrypted string."""
    return cipher.decrypt(encrypted_text.encode()).decode()