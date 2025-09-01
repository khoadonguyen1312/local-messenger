from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64
import hashlib

KEY = hashlib.sha256(b"super_secret_key").digest()

def encrypt(data: bytes) -> bytes:
    cipher = AES.new(KEY, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(data)
    return base64.b64encode(cipher.nonce + tag + ciphertext)

def decrypt(token: bytes) -> bytes:
    raw = base64.b64decode(token)
    nonce, tag, ciphertext = raw[:16], raw[16:32], raw[32:]
    cipher = AES.new(KEY, AES.MODE_EAX, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag)
