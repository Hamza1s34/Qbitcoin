# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
import base64

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from pyqrllib.pyqrllib import getRandomSeed

from qbitcoin.crypto.misc import sha256


class AESHelper(object):
    def __init__(self, key_str: str):
        self.key = key_str.encode()
        self.key_hash = sha256(self.key)

    def encrypt(self, message: bytes, iv=None) -> dict:
        """
        Encrypt message and return components separately for modern wallet format
        """
        if iv is None:
            iv = bytes(getRandomSeed(16, ''))

        cipher = Cipher(AES(self.key_hash), modes.CTR(iv), default_backend())
        enc = cipher.encryptor()
        ciphertext = enc.update(message) + enc.finalize()

        # Return components separately for modern wallet format
        return {
            'ciphertext': base64.standard_b64encode(ciphertext).decode(),
            'nonce': base64.standard_b64encode(iv).decode(),
            'salt': base64.standard_b64encode(self.key_hash[:16]).decode()
        }

    def encrypt_legacy(self, message: bytes, iv=None) -> str:
        """
        Legacy encrypt method that returns combined base64 string
        """
        if iv is None:
            iv = bytes(getRandomSeed(16, ''))

        cipher = Cipher(AES(self.key_hash), modes.CTR(iv), default_backend())
        enc = cipher.encryptor()
        ciphertext = enc.update(message) + enc.finalize()

        output_message = base64.standard_b64encode(iv + ciphertext)
        return output_message.decode()

    def decrypt(self, data: str) -> bytes:
        secret_message = base64.standard_b64decode(data.encode())
        secret_iv = secret_message[:16]

        secret_ciphertext = secret_message[16:]

        cipher = Cipher(AES(self.key_hash), modes.CTR(secret_iv), default_backend())
        dec = cipher.decryptor()

        return dec.update(secret_ciphertext) + dec.finalize()

    def decrypt_with_components(self, ciphertext_b64: str, nonce_b64: str, salt_b64: str) -> bytes:
        """
        Decrypt using separate components for modern wallet format
        """
        ciphertext = base64.standard_b64decode(ciphertext_b64.encode())
        iv = base64.standard_b64decode(nonce_b64.encode())

        cipher = Cipher(AES(self.key_hash), modes.CTR(iv), default_backend())
        dec = cipher.decryptor()

        return dec.update(ciphertext) + dec.finalize()
