//
// Created by Nebu1ea on 2025/11/25.
//

#include "Utils.hpp"
#include <sodium.h> //引入 libsodium 核心库
#include <stdexcept>
#include <iostream>

namespace Grimoire::Utils
{

    // --- Base64 编码 ---
    std::string Base64Encode(const std::vector<unsigned char>& input_bytes) {
        if (input_bytes.empty()) {
            return "";
        }

        // 计算需要的 Base64 字符串长度，后续创建vector用的
        // sodium_base64_ENCODED_LEN 会自动计算并包含 NULL 终止符的空间
        size_t encoded_len = sodium_base64_encoded_len(
            input_bytes.size(),
            sodium_base64_VARIANT_ORIGINAL // 使用标准 Base64 格式
        );

        // 创建缓冲区
        // std::string 构造函数可以接收 char*，所以我们用 char* 数组，最后好转换为string
        std::vector<char> output_buffer(encoded_len);

        // 执行编码
        // sodium_bin2base64 返回 output_buffer 的指针
        if (sodium_bin2base64(
            output_buffer.data(),
            output_buffer.size(),
            input_bytes.data(),
            input_bytes.size(),
            sodium_base64_VARIANT_ORIGINAL
        ) == nullptr) {
            // 理论上不会失败，除非缓冲区太小
            throw std::runtime_error("Base64Encode: Failed to encode data.");
        }

        // 返回 std::string (从 char* 转换，encoded_len 已经包含了 NULL 终止符)
        // 我们需要减去 NULL 终止符的长度
        return std::string(output_buffer.data());
    }


    // --- Base64 解码 ---
    std::vector<unsigned char> Base64Decode(const std::string& input_b64) {
        if (input_b64.empty()) {
            return {};
        }

        // 声明存储实际解码字节数的变量
        size_t decoded_len = 0;

        // 确定最大的解码缓冲区大小（Base64 长度最多为原始长度的 4/3）
        // 简单安全的做法是使用字符串长度作为上限
        size_t max_decoded_len = input_b64.length();

        // 创建输出缓冲区（使用字符串长度作为安全上限）
        std::vector<unsigned char> decoded_buffer(max_decoded_len);

        // 执行解码
        // sodium_base642bin 返回 NULL 表示失败
        if (sodium_base642bin(
            decoded_buffer.data(),
            max_decoded_len,
            input_b64.c_str(),
            input_b64.length(),
            nullptr, // 忽略分隔符
            &decoded_len, //实际解码的字节数会被写入这里
            nullptr, // 忽略状态指针
            sodium_base64_VARIANT_ORIGINAL
        ) != 0) {
            throw std::runtime_error("Base64Decode: Invalid Base64 string or decoding failed.");
        }

        // 调整 vector 大小并返回
        // 必须将 vector 调整为实际解码的长度 decoded_len
        decoded_buffer.resize(decoded_len);
        return decoded_buffer;
    }

    // --- Hex 编码 ---
    std::string HexEncode(const std::vector<unsigned char>& input_bytes) {
        if (input_bytes.empty()) {
            return "";
        }

        // Hex 编码长度 = 字节数 * 2 + 1 (NULL 终止符)
        size_t encoded_len = input_bytes.size() * 2 + 1;
        std::vector<char> output_buffer(encoded_len);

        // 使用 libsodium 的 sodium_bin2hex
        if (sodium_bin2hex(
            output_buffer.data(),
            output_buffer.size(),
            input_bytes.data(),
            input_bytes.size()
        ) == nullptr) {
            throw std::runtime_error("HexEncode: Failed to encode data.");
        }

        // 返回 std::string (不包含 NULL 终止符)
        return std::string(output_buffer.data());
    }


    // --- Hex 解码 ---
    std::vector<unsigned char> HexDecode(const std::string& input_hex) {
        if (input_hex.empty()) {
            return {};
        }

        size_t decoded_len = 0;
        // 原始字节数 = Hex 字符串长度 / 2
        size_t max_decoded_len = input_hex.length() / 2;
        std::vector<unsigned char> decoded_buffer(max_decoded_len);

        // 使用 libsodium 的 sodium_hex2bin
        if (sodium_hex2bin(
            decoded_buffer.data(),
            max_decoded_len,
            input_hex.c_str(),
            input_hex.length(),
            nullptr, // 忽略分隔符
            &decoded_len, // 实际解码的字节数
            nullptr // 忽略状态指针
        ) != 0) {
            throw std::runtime_error("HexDecode: Invalid Hex string or decoding failed.");
        }

        // 调整 vector 大小并返回
        decoded_buffer.resize(decoded_len);
        return decoded_buffer;
    }
}
