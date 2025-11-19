import hashlib
import os
from base64 import b64encode, b64decode
from typing import Tuple
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization
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


    # 返回公钥字节
    def get_publickey(self) -> bytes:
        public_bytes = self.public.public_bytes(
            encoding=serialization.Encoding.Raw,  # 使用原始格式
            format=serialization.PublicFormat.Raw  # 使用原始公共格式
        )

        return  public_bytes

    # 用对方公钥 + 自己私钥算共享秘钥 → HKDF 派生 AES 密钥
    def derive_session_key(self, my_private: x25519.X25519PrivateKey, beacon_public_key: bytes) -> str:
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
        beacon_id_bytes = hashlib.sha256(aes_key).digest()
        beacon_id = beacon_id_bytes.hex()
        self.sessions[beacon_id] = AESGCM(aes_key)

        return  beacon_id

    # 下面就是熟悉的 AES-GCM 了
    # 加密方法
    def grimoire_encrypt(self, beacon_id: str, data: bytes) -> str:
        """
        输出结构: Base64( IV || Ciphertext || GCM Tag || SF )
        """
        aesgcm = self.sessions.get(beacon_id)
        if not aesgcm:
            raise ValueError(f"No session found: {beacon_id[:8]}")

        iv = os.urandom(Config.IV_LENGTH)

        # ct_and_tag 包含了 Ciphertext 和 GCM Tag,为了证明
        ct_and_tag = aesgcm.encrypt(iv, data, None)

        # 获取 SF 原始字节
        session_fingerprint_bytes = bytes.fromhex(beacon_id)

        # 组合最终负载: IV || CT || Tag || SF
        full_payload = iv + ct_and_tag + session_fingerprint_bytes

        return b64encode(full_payload).decode('utf-8')

    # 解密方法
    def grimoire_decrypt(self, payload: str) -> Tuple[bytes, str]:
        """
        Base64 解码，剥离 SF，查找密钥，解密并验证负载。
        """
        try:
            raw_payload = b64decode(payload)
        except Exception:
            raise ValueError("Invalid Base64 payload received.")

        # 剥离 SF
        if len(raw_payload) < Config.IV_LENGTH + Config.SF_LENGTH:
            raise ValueError("Payload too short")

        session_fingerprint_bytes = raw_payload[-Config.SF_LENGTH:]

        # 这里现在只剩 IV + CT||Tag
        encrypted_data = raw_payload[:-Config.SF_LENGTH]

        # 查找密钥
        beacon_id = session_fingerprint_bytes.hex()
        aesgcm = self.sessions.get(beacon_id)

        if not aesgcm:
            raise ValueError(f"No active session found: {beacon_id[:8]}")

        # 剥离 IV
        iv = encrypted_data[:Config.IV_LENGTH]

        # 剩余部分正是 CT || Tag
        ciphertext_and_tag = encrypted_data[Config.IV_LENGTH:]

        # 解密
        try:
            plaintext = aesgcm.decrypt(iv, ciphertext_and_tag, None)
            return plaintext, beacon_id
        except InvalidTag:
            # 重新抛出，让上层捕获
            raise InvalidTag(f"GCM authentication failed: {beacon_id[:8]}.")