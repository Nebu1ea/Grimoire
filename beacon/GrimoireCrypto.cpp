//
// Created by Nebu1ea on 2025/11/25.
//

#include "GrimoireCrypto.hpp"
#include "Utils.hpp"
#include <sodium.h>
#include <stdexcept>
#include <fstream>
#include <iostream>


namespace Grimoire::Crypto {

    GrimoireCrypto::GrimoireCrypto() {
        if (sodium_init() == -1) {
            throw std::runtime_error("libsodium initialization failed!");
        }

        std::cout << "[Crypto] Libsodium initialized. Beacon is stateless." << std::endl;
    }

    GrimoireCrypto::~GrimoireCrypto() {
        // 销毁时清除内存中的敏感数据
        if (!session_key_.empty()) {
            sodium_memzero(session_key_.data(), session_key_.size());
        }
    }


    // --- 获取 Beacon ID  ---
    std::string GrimoireCrypto::GetBeaconSessionFingerprint() const {
        return beacon_id_;
    }

    // --- 实现 InitialKeyExchange ---
    std::string GrimoireCrypto::InitialKeyExchange(const std::string& server_public_key_b64) {
        // 解码服务器永久公钥
        std::vector<unsigned char> server_public_key = Utils::Base64Decode(server_public_key_b64);

        // 校验密钥长度
        if (server_public_key.size() != crypto_box_PUBLICKEYBYTES) {
            throw std::runtime_error("InitialKeyExchange: Invalid server public key size.");
        }

        // 生成临时密钥对
        std::vector<unsigned char> temp_public_key(crypto_box_PUBLICKEYBYTES);
        std::vector<unsigned char> temp_secret_key(crypto_box_SECRETKEYBYTES);

        // libsodium 提供了这个函数来生成用于密钥协商的临时密钥对
        crypto_box_keypair(temp_public_key.data(), temp_secret_key.data());

        // 协商共享会话密钥 (Derive Shared Session Key)
        // X25519 ECDH 的核心步骤
        session_key_.resize(crypto_box_BEFORENMBYTES);

        // 共享密钥存储位置，服务器公钥，客户端临时私钥
        if (crypto_box_beforenm(
            session_key_.data(),             // 共享密钥 (K)
            server_public_key.data(),        // 接收方公钥 (服务器永久公钥)
            temp_secret_key.data()           // 发送方私钥 (客户端临时私钥)
        ) != 0) {
            throw std::runtime_error("InitialKeyExchange: Shared key derivation failed.");
        }


        std::vector<unsigned char> session_key_hash(crypto_hash_sha256_BYTES);

        if (crypto_hash_sha256(
        session_key_hash.data(),
        session_key_.data(),
        session_key_.size()
        ) != 0) {
            throw std::runtime_error("InitialKeyExchange: SHA256 hash failed.");
        }

        beacon_id_ = Utils::HexEncode(session_key_hash);
        // 清理内存中的临时私钥
        sodium_memzero(temp_secret_key.data(), temp_secret_key.size());

        std::cout << "[Crypto] Shared Session Key derived successfully (Forward Secrecy enabled)." << std::endl;

        // 返回临时公钥给服务器（Base64 编码）
        return Utils::Base64Encode(temp_public_key);
    }

    // --- 实现 EncryptPayload ---
    std::string GrimoireCrypto::EncryptPayload(const std::vector<unsigned char>& plaintext_payload) {
        if (beacon_id_.empty() || session_key_.empty()) {
            throw std::runtime_error("EncryptPayload: Session not established.");
        }

        // 准备 Nonce (IV) 和 Tag
        std::vector<unsigned char> nonce(CRYPTO_NONCE_BYTES);
        // 使用 libsodium 生成一个密码学安全的随机 Nonce
        randombytes_buf(nonce.data(), nonce.size());

        // 准备密文缓冲区
        // 密文大小 = 明文大小 + 认证标签大小
        size_t ciphertext_len = plaintext_payload.size() + CRYPTO_TAG_BYTES;
        std::vector<unsigned char> ciphertext(ciphertext_len);

        // 实际标签的字节数
        unsigned long long actual_tag_len = 0;

        // 执行 AES-GCM 加密 (使用 libsodium 的高级 AEAD 接口)
        // 这里使用了 libsodium 的 AES-GCM 实现，它是 AEAD 族中的一个
        if (crypto_aead_aes256gcm_encrypt(
            ciphertext.data(),                 // 输出：密文 (包含 Tag)
            &actual_tag_len,                   // 输出：实际生成的标签长度
            plaintext_payload.data(),          // 输入：明文
            plaintext_payload.size(),          // 输入：明文长度
            nullptr,                           // 附加认证数据 (AAD)，这里不用
            0,                                 // AAD 长度
            nullptr,                           // 秘密 nonce (IV)
            nonce.data(),                      // 输入：随机 Nonce
            session_key_.data()                // 输入：共享会话密钥
        ) != 0) {
            throw std::runtime_error("EncryptPayload: AES-GCM encryption failed.");
        }

        // 拼接最终的负载：Nonce + Ciphertext + Tag
        // Nonce 已经在 ciphertext 的实际内容之外，我们需要手动拼接

        std::vector<unsigned char> sf_raw = Utils::HexDecode(beacon_id_);
        if (sf_raw.size() != crypto_hash_sha256_BYTES) {
            throw std::runtime_error("EncryptPayload: SF hash size mismatch (Expected 32 bytes).");
        }

        size_t final_raw_size = CRYPTO_NONCE_BYTES + ciphertext_len + sf_raw.size();
        std::vector<unsigned char> final_payload;
        final_payload.reserve(final_raw_size);

        // 拼接 Nonce (IV)
        final_payload.insert(final_payload.end(), nonce.begin(), nonce.end());
        // 拼接 Ciphertext + Tag
        final_payload.insert(final_payload.end(), ciphertext.begin(), ciphertext.end());
        // 拼接 SF (Beacon ID)
        final_payload.insert(final_payload.end(), sf_raw.begin(), sf_raw.end());

        std::cout << "[Crypto] Payload encrypted successfully. Final size: " << final_payload.size() << " bytes." << std::endl;

        // Base64 编码并返回
        return Utils::Base64Encode(final_payload);
    }

    // --- 解密流程 ---
    std::vector<unsigned char> GrimoireCrypto::DecryptPayload(const std::string& ciphertext_b64) {
        if (session_key_.empty()) {
            throw std::runtime_error("DecryptPayload: Session key not established.");
        }

        // Base64 解码
        std::vector<unsigned char> raw_payload = Utils::Base64Decode(ciphertext_b64);

        // 检查最小长度
        // 最小长度 = Nonce (IV) 长度 + Tag 长度
        size_t min_encrypted_size = CRYPTO_NONCE_BYTES + CRYPTO_TAG_BYTES;

        if (raw_payload.size() < min_encrypted_size) {
            throw std::runtime_error("DecryptPayload: Payload size too short (Expected IV|CT|TAG).");
        }

        // 剥离 IV (Nonce)
        // IV 位于原始负载的前 CRYPTO_NONCE_BYTES 字节
        std::vector<unsigned char> iv(
            raw_payload.begin(),
            raw_payload.begin() + CRYPTO_NONCE_BYTES
        );

        // 剩余部分是密文和 Tag (CT || Tag)
        std::vector<unsigned char> ciphertext_and_tag(
            raw_payload.begin() + CRYPTO_NONCE_BYTES,
            raw_payload.end()
        );

        // 准备解密缓冲区
        // 明文大小 = (CT||Tag) 大小 - Tag 大小
        size_t plaintext_size = ciphertext_and_tag.size() - CRYPTO_TAG_BYTES;
        std::vector<unsigned char> plaintext(plaintext_size);
        unsigned long long decrypted_len = 0;

        // 执行 AES-GCM 解密
        if (crypto_aead_aes256gcm_decrypt(
            plaintext.data(),               // 输出：明文
            &decrypted_len,                 // 输出：实际解密长度
            nullptr,
            ciphertext_and_tag.data(),      // 输入：密文 (包含 Tag)
            ciphertext_and_tag.size(),      // 输入：密文总长度
            nullptr,                        // 附加认证数据 (AAD)，这里不用
            0,                              // AAD 长度
            iv.data(),                      // 输入：Nonce
            session_key_.data()             // 输入：共享会话密钥
        ) != 0) {
            // 如果认证标签无效 (InvalidTag)，libsodium 会返回非零值
            throw std::runtime_error("DecryptPayload: GCM authentication failed or decryption error.");
        }

        // 调整 vector 大小并返回
        plaintext.resize(decrypted_len);
        std::cout << "[Crypto] Payload decrypted successfully. Plaintext size: " << plaintext.size() << " bytes." << std::endl;

        return plaintext;
    }

} // namespace Grimoire::Crypto