#pragma once
#include <string>
#include <utility>
#include <vector>

namespace dashboard {
using Metadata = std::vector<std::pair<std::string,std::string>>;
std::string page(bool daily, const std::string& title, const std::string& body,
                 const std::string& redirect, const Metadata& metadata);
}
