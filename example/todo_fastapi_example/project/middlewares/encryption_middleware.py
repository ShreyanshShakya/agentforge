from pycryptodome.Cipher import AES
import base64

class EncryptionMiddleware:
    def __init__(self, key):
        self.key = key.encode('utf-8')
        self.block_size = AES.block_size

    def pad(self, data):
        padding_len = self.block_size - len(data) % self.block_size
        return data + (chr(padding_len) * padding_len).encode('utf-8')

    def unpad(self, data):
        padding_len = int(data[-1])
        return data[:-padding_len]

    def encrypt(self, data):
        iv = AES.new(self.key, AES.MODE_CBC)
        encrypted_data = iv.encrypt(self.pad(data.encode('utf-8')))
        return base64.b64encode(iv.iv + encrypted_data).decode('utf-8')

    def decrypt(self, encrypted_data):
        encrypted_data = base64.b64decode(encrypted_data)
        iv = encrypted_data[:self.block_size]
        encrypted_data = encrypted_data[self.block_size:]
        decrypted_data = self.unpad(AES.new(self.key, AES.MODE_CBC, iv).decrypt(encrypted_data))
        return decrypted_data.decode('utf-8')