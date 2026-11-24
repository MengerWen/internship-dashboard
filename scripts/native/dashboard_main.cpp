#include "dashboard_build.hpp"

#include <iostream>
#include <regex>
#include <stdexcept>

#ifdef _WIN32
#define NOMINMAX
#include <fcntl.h>
#include <io.h>
#include <windows.h>
#endif

namespace {
using dashboard::fs::path;

int run(const dashboard::Strings& args) {
    using namespace dashboard;
    BuildOptions options;
    options.root = fs::canonical(fs::current_path());
    options.output = options.root / "dist";

    auto absolute = [&](const std::string& name) { return (options.root / fs::u8path(name)).lexically_normal(); };
    try {
        if (args.size() == 2 && args.front() == "--render-markdown") {
#ifdef _WIN32
            _setmode(_fileno(stdout), _O_BINARY);
#endif
            std::cout << render_markdown(load_document(absolute(args.back())).body);
            return std::cout ? 0 : 1;
        }
        for (std::size_t i = 0; i < args.size(); ++i) {
            const auto& flag = args[i];
            if (flag == "--help" || flag == "-h") {
                std::cout << "dashboard_builder [--release] [--output PATH] [--asset-copy-manifest PATH]\n"
                             "                  [--daily-cache PATH] [--tags-snapshot PATH] [--pagefind EXE]\n"
                             "                  [--build-time ISO_DATE] [--asset-version YYYYMMDDHHMMSS]\n"
                             "dashboard_builder --render-markdown PATH\n"
                             "Run from the repository root. Default output: dist.\n";
                return 0;
            }
            if (flag == "--release") continue;
            if (i + 1 == args.size()) throw std::invalid_argument("missing argument for " + flag);
            const auto& value = args[++i];
            if (flag == "--output") options.output = absolute(value);
            else if (flag == "--asset-copy-manifest") options.asset_manifest = absolute(value);
            else if (flag == "--daily-cache") options.daily_cache = absolute(value);
            else if (flag == "--tags-snapshot") options.tags = absolute(value);
            else if (flag == "--pagefind") options.pagefind = absolute(value);
            else if (flag == "--build-time") {
                options.build_time = china_time(value);
                if (options.build_time != value) throw std::invalid_argument("--build-time requires a +08:00 ISO timestamp");
            } else if (flag == "--asset-version") {
                if (!std::regex_match(value, std::regex(R"(\d{14})")))
                    throw std::invalid_argument("--asset-version requires 14 digits");
                options.asset_version = value;
            } else throw std::invalid_argument("unknown argument " + flag);
        }
        if (!fs::is_regular_file(options.root / "config.json") || !fs::is_directory(options.root / "site"))
            throw std::runtime_error("run dashboard_builder from the dashboard repository root");
        build_dashboard(options);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "dashboard_builder: " << error.what() << '\n';
        return 1;
    }
}
}

#ifdef _WIN32
int wmain(int argc, wchar_t** argv) {
    SetConsoleOutputCP(CP_UTF8);
    dashboard::Strings args;
    for (int i = 1; i < argc; ++i) args.push_back(dashboard::fs::path(argv[i]).u8string());
    return run(args);
}
#else
int main(int argc, char** argv) {
    return run({argv + 1, argv + argc});
}
#endif
