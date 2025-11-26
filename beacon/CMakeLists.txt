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


# 目标和源文件
set(SOURCE_FILES
        main.cpp
        GrimoireAgent.cpp
        GrimoireComms.cpp
        GrimoireCrypto.cpp
        Utils.cpp
)

add_executable(GrimoireBeacon ${SOURCE_FILES})



# 链接目标库
target_link_libraries(GrimoireBeacon
        PUBLIC
        ${LIBSODIUM_LIBRARIES}  # 链接 libsodium
        ${CURL_LIBRARIES}       # 链接 libcurl
)

# 告诉编译器去哪里找头文件 (如果 find_package 没有自动完成)
target_include_directories(GrimoireBeacon PUBLIC
        ${LIBSODIUM_INCLUDE_DIRS}
        ${CURL_INCLUDE_DIRS}
)