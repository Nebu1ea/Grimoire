//
// Created by Nebu1ea on 2025/11/25.
//

#ifndef GRIMOIREBEACON_UTILS_HPP
#define GRIMOIREBEACON_UTILS_HPP


#include <string>
#include <vector>


namespace Grimoire::Utils {

    /**
     * @brief 对字节数据进行 Base64 编码
     * @param input_bytes 原始字节数据
     * @return Base64 编码后的字符串
     */
    std::string Base64Encode(const std::vector<unsigned char>& input_bytes);

    /**
     * @brief 对 Base64 字符串进行解码
     * @param input_b64 Base64 字符串
     * @return 解码后的原始字节数据
     */
    std::vector<unsigned char> Base64Decode(const std::string& input_b64);


    /**
     * @brief 对字节数据进行 Hex (十六进制) 编码
     */
    std::string HexEncode(const std::vector<unsigned char>& input_bytes);


    /**
     * @brief 对 Hex 字符串进行解码
     */
    std::vector<unsigned char> HexDecode(const std::string& input_hex);
} // namespace Grimoire::Utils


#endif //GRIMOIREBEACON_UTILS_HPP