#include "page_renderer.hpp"
#include <iostream>
#include <iterator>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#include <windows.h>
#endif

int run(const std::vector<std::string>& args) {
    if (args.size() == 3 && args[0] == "validate-daily-source")
        return static_cast<int>(dashboard::validate_daily_source(args[1], args[2]));
    if (args.size() == 1 && args[0] == "daily-scenes") {
        std::string body{std::istreambuf_iterator<char>(std::cin),{}};
        std::cout << dashboard::daily_scenes(body);
        return std::cin.bad() || !std::cout ? 1 : 0;
    }
    if (args.size() == 2 && args[0] == "markdown-title") {
        std::string body{std::istreambuf_iterator<char>(std::cin),{}};
        std::cout << dashboard::markdown_title(body, args[1]);
        return std::cin.bad() || !std::cout ? 1 : 0;
    }
    const bool daily = args.size() == 2 && args[0] == "daily";
    if (!daily && (args.size() < 3 || args[0] != "index" || (args.size()-3)%2)) {
        std::cerr << "page_renderer daily TITLE | index TITLE REDIRECT [KEY VALUE ...] < body.html\n"
                     "page_renderer daily-scenes < body.html\n"
                     "page_renderer markdown-title FALLBACK < body.md\n"
                     "page_renderer validate-daily-source DIRECTORY RELATIVE_HTML\n";
        return 2;
    }
    dashboard::Metadata meta;
    for (std::size_t i=3; i<args.size(); i+=2) meta.emplace_back(args[i],args[i+1]);
    std::string body{std::istreambuf_iterator<char>(std::cin),{}};
    std::cout << dashboard::page(daily,args[1],body,daily ? "" : args[2],meta);
    return std::cin.bad() || !std::cout ? 1 : 0;
}
#ifdef _WIN32
int wmain(int argc,wchar_t** argv) {
    _setmode(_fileno(stdin), _O_BINARY);
    _setmode(_fileno(stdout), _O_BINARY);
    std::vector<std::string> args;
    for (int i=1; i<argc; ++i) {
        int count = WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,argv[i],-1,nullptr,0,nullptr,nullptr);
        if (!count) return 2;
        std::string value(static_cast<std::size_t>(count),'\0');
        if (!WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,argv[i],-1,value.data(),count,nullptr,nullptr)) return 2;
        value.pop_back(); args.push_back(std::move(value));
    }
    return run(args);
}
#else
int main(int argc,char** argv) { return run({argv+1,argv+argc}); }
#endif
