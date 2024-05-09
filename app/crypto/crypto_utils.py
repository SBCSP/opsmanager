import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Function to generate a key based on a passphrase
def key_from_passphrase(passphrase, salt=None):
    if salt is None:
        salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000,
        backend=default_backend()
    )
    key = kdf.derive(passphrase.encode())
    return Fernet(base64.urlsafe_b64encode(key)), salt

# Function to encrypt content
def encrypt_content(content, passphrase):
    fernet, salt = key_from_passphrase(passphrase)
    encrypted = fernet.encrypt(content.encode())
    return encrypted, salt  # You need to store the salt along with the encrypted data

# Function to decrypt content
def decrypt_content(encrypted_content, passphrase, salt):
    try:
        fernet, _ = key_from_passphrase(passphrase, salt)
        return fernet.decrypt(encrypted_content).decode()
    except Exception as e:
        print(f"Decryption error: {str(e)}")  # For debugging, consider logging this properly
        raise e
