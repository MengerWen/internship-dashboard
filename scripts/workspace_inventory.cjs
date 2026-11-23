const { spawnSync } = require("node:child_process");
const { existsSync } = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const local = path.join(root, ".local", "native");
const windows = process.platform === "win32";
const nav = process.argv[2] === "--nav";
const journalRegister = process.argv[2] === "--journal-register";
const journal = process.argv[2] === "--journal" || journalRegister;
const tool = journal ? "journal_sources" : nav ? "nav_scrollspy" : "workspace_inventory";
const exe = path.join(local, "bin", tool + (windows ? ".exe" : ""));
function run(program, args) {
  const child = spawnSync(program, args, { cwd: root, stdio: "inherit", windowsHide: true });
  if (child.error) throw child.error;
  if (child.status !== 0) process.exit(child.status ?? 1);
}
if (process.argv[2] === "--build") {
  let cmake = "cmake";
  if (windows && spawnSync(cmake, ["--version"], { windowsHide: true }).error?.code === "ENOENT") {
    const locator = path.join(process.env["ProgramFiles(x86)"], "Microsoft Visual Studio", "Installer", "vswhere.exe");
    const install = spawnSync(locator, ["-latest", "-products", "*", "-requires",
      "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
      { encoding: "utf8", windowsHide: true });
    if (install.status !== 0 || !install.stdout.trim()) throw Error("CMake or Visual Studio C++ Build Tools required");
    cmake = path.join(install.stdout.trim(), "Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe");
  }
  const build = path.join(local, "build");
  run(cmake, ["-S", path.join(__dirname, "native"), "-B", build, ...(!windows ? ["-DCMAKE_BUILD_TYPE=Release"] : [])]);
  run(cmake, ["--build", build, "--config", "Release"]);
  const ctest = path.join(path.dirname(cmake), windows ? "ctest.exe" : "ctest");
  run(cmake, ["-E", "chdir", build, ctest, "-C", "Release", "--output-on-failure"]);
  run(cmake, ["--install", build, "--config", "Release", "--prefix", local]);
} else {
  if (!existsSync(exe)) {
    console.error(journal ? "请在研究仓库与 dashboard 同级时运行 npm run workspace:build。" :
      "请先运行 npm run workspace:build 安装 C++ 工具。");
    process.exit(2);
  }
  const options = process.argv.slice(nav || journal ? 3 : 2);
  run(exe, journal ? ["--root", root, ...(journalRegister ? ["--register"] : []), ...options] : options);
}
