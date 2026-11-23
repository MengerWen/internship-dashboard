#pragma once
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace dashboard {
using Metadata = std::vector<std::pair<std::string,std::string>>;
std::string page(bool daily, const std::string& title, const std::string& body,
                 const std::string& redirect, const Metadata& metadata);
enum class DailySourceStatus { valid, invalid_relative_path, outside_daily_directory, unreadable_path };
DailySourceStatus validate_daily_source(std::string_view directory, std::string_view source) noexcept;
}
