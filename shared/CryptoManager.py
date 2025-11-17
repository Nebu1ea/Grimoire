import os
from base64 import b64encode, b64decode
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from config import Config

# 这里为了安全掩蔽，我采用 ECDH（X25519） 一次性密钥交换策略
class GrimoireCryptoManager:
    def __init__(self):
        # 存储所有的AESGCM {beacon_id: AESGCM实例}
        self.sessions = {}

        # 生成自己的临时密钥对
        self.private = x25519.X25519PrivateKey.generate()
        self.public = self.private.public_key()

    # 用对方公钥 + 自己私钥算共享秘钥 → HKDF 派生 AES 密钥
    def derive_session_key(self, beacon_id: str, my_private: x25519.X25519PrivateKey, beacon_public_key: bytes):
        beacon_public = x25519.X25519PublicKey.from_public_bytes(beacon_public_key)
        shared = my_private.exchange(beacon_public)

        # 计算 AES 密钥
        derived = HKDF(
            algorithm=hashes.SHA256(),
            length=Config.AES_KEY_LENGTH,
            salt=None,
            info=Config.HKDF_INFO,
        ).derive(shared)

        aes_key = derived
        self.sessions[beacon_id] = AESGCM(aes_key)

    # 下面就是熟悉的 AES-GCM 了
    def encrypt(self, beacon_id: str, data: bytes) -> str:
        aesgcm = self.sessions.get(beacon_id)

        iv = os.urandom(12)
        ct = aesgcm.encrypt(iv, data, None)
        return b64encode(iv + ct).decode()

    def decrypt(self, beacon_id: str, payload: str) -> bytes:
        aesgcm = self.sessions.get(beacon_id)

        raw = b64decode(payload)
        iv, output = raw[:12], raw[12:]
        return aesgcm.decrypt(iv, output, None)