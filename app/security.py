"""
Symmetric encryption for OAuth tokens at rest. Set ENCRYPTION_KEY in your
environment (generate once with Fernet.generate_key() and store in a secrets
manager, not in source control).
"""
import os
from cryptography.fernet import Fernet

_key = os.environ.get("ENCRYPTION_KEY")
if not _key:
    # Only for local dev — never rely on this in production.
    _key = Fernet.generate_key().decode()
    print("WARNING: ENCRYPTION_KEY not set, using an ephemeral dev key.")

_fernet = Fernet(_key.encode() if isinstance(_key, str) else _key)


def encrypt_token(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    return _fernet.decrypt(ciphertext.encode()).decode()
