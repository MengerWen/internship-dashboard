#include "workspace_inventory.hpp"
#include <chrono>
#include <fstream>
#include <iostream>
#include <stdexcept>

namespace fs = std::filesystem;
void check(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
int main() {
    auto stamp = std::chrono::steady_clock::now().time_since_epoch().count();
    auto root = fs::current_path()/("audit-fixture-"+std::to_string(stamp));
    try {
        check(fs::create_directory(root), "fixture already exists");
        auto runs = root/".local"/"runs";
        auto empty = scan_runs(runs);
        check(empty.files==0 && empty.bytes==0 && empty.links.empty() && empty.errors.empty(), "absent runs");
        std::string name=u8"待保存 正文.md";
        auto draft = root/fs::u8path(name);
        std::ofstream(draft,std::ios::binary) << "draft";
        fs::create_directories(runs/"task");
        auto log = runs/"task"/"result.json";
        std::ofstream(log,std::ios::binary) << "{}";
        Strings errors;
        auto groups = group_paths(root,{name},errors);
        check(errors.empty() && groups.at(name).bytes==5 && groups.at(name).entries==1,"UTF-8 untracked file");
        std::error_code error;
        fs::create_directory_symlink(root,runs/"linked",error);
        auto result = scan_runs(runs);
        check(result.files==1 && result.bytes==2 && result.errors.empty(), "run contents");
        if (!error) {
            check(result.links==Strings{"linked"}, "directory link");
            fs::remove(runs/"linked");
        } else std::cout << "directory symlink unavailable: " << error.message() << '\n';
        check(fs::file_size(draft)==5 && fs::file_size(log)==2, "inventory changed fixture");
        for (const auto& path : {log,runs/"task",runs,root/".local",draft,root}) fs::remove(path);
        return 0;
    } catch (const std::exception& e) {
        std::cerr << root << ": " << e.what() << '\n';
        return 1;
    }
}
