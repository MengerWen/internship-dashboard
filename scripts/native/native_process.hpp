#pragma once

#include <string>
#include <vector>

namespace dashboard {
using Strings = std::vector<std::string>;
std::string run_process(const std::string& program, const Strings& args);
}
