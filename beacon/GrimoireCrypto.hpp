#ifndef GRIMOIRE_CRYPTO_HPP
#define GRIMOIRE_CRYPTO_HPP

#include <string>
#include <vector>
#include <sodium.h> // 需要 libsodium 的常量

// 定义公钥/私钥的长度，直接使用 libsodium 的标准常量
#define CRYPTO_KEY_BYTES crypto_box_PUBLICKEYBYTES
#define CRYPTO_SHARED_KEY_BYTES crypto_box_BEFORENMBYTES
#define CRYPTO_NONCE_BYTES crypto_aead_aes256gcm_NPUBBYTES
#define CRYPTO_TAG_BYTES crypto_aead_aes256gcm_ABYTES

namespace Grimoire::Crypto {

    /**
     * @brief 负责所有加密和密钥管理任务。
     * 实现 X25519 ECDH 和 AES-GCM 加密，对接服务器端协议。
     */
    class GrimoireCrypto {
        public:
            // 构造函数和析构函数
            GrimoireCrypto();
            ~GrimoireCrypto();

            /**
             * @brief 加密 Payload：使用共享会话密钥对数据进行 AES-GCM 加密。
             * @param plaintext_payload 要加密的数据（原始字节）。
             * @return 密文 (IV + Ciphertext + Tag + SF)，Base64编码。
             */
            std::string EncryptPayload(const std::vector<unsigned char>& plaintext_payload);

            /**
             * @brief 解密 Payload：解密服务器返回的密文。
             * @param ciphertext_b64 服务器返回的密文 (Nonce + Ciphertext + Tag)，Base64编码。
             * @return 解密后的原始数据（JSON Body 字节）。
             */
            std::vector<unsigned char> DecryptPayload(const std::string& ciphertext_b64);


            /**
             * @brief 用于 InitialKeyExchange 阶段的临时私钥
             * @return 临时密钥字符串
             */
            std::string GenerateClientKey();


            /**
             * @brief 协商密钥
             * @param server_public_key_b64 服务器发来的公钥
             * @return 解密后的原始数据（JSON Body 字节）。
             */
            bool CompleteKeyDerivation(const std::string& server_public_key_b64);

            /**
             * @brief 获取 Beacon 的永久会话指纹/身份 (Base64编码的永久公钥)。
             * [[nodiscard]]保证变量会被使用
             */
            [[nodiscard]] std::string GetBeaconSessionFingerprint() const;

        private:
            // 协商后的共享会话密钥 (用于 AES-GCM 加密)
            std::vector<unsigned char> session_key_;
            std::vector<unsigned char> temp_secret_key_;
            // Beacon ID (永久公钥，作为 Session Fingerprint)
            std::string beacon_id_;
    };

} // namespace Grimoire::Crypto

#endif // GRIMOIRE_CRYPTO_HPP