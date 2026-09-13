# Nahimic Linux

让笔记本扬声器在 Linux 上用上 Nahimic 音效。提供音乐、电影、游戏、通话四种模式，低音、人声、高音、环绕、动态压缩和十段均衡器。支持一键开关对比，音量与系统同步，设置自动保存，关闭面板后音效继续运行。

## 安装

Arch Linux 及衍生发行版：

```sh
yay -S nahimic-linux
```

也可以使用 `paru -S nahimic-linux`。安装会自动下载所需运行组件、匹配扬声器并启动音效。安装完成后，从应用菜单打开 **Nahimic 音效**，或运行 `nahimic`。首次准备运行环境需要稍等片刻。

目前已验证机械革命无界 14X Pro（Senary 声卡，子系统 ID `1D05E022`）的内置扬声器。需要 x86_64、PipeWire、PipeWire Pulse 和 systemd 用户会话。界面使用 Qt，支持 KDE、GNOME 及其他提供上述组件的桌面环境。耳机、蓝牙和其他输出设备继续使用系统原有音频路径。

## 让 AI 帮你安装或适配

可以直接把下面这段话发给 Claude Code、Codex 等 AI 编程助手：

> 阅读 https://github.com/wearzdk/nahimic-linux ，按照 AGENTS.md 检查我的系统和声卡，安装并验证 Nahimic Linux。若型号不一致，请检查现有设备配置，完成本机测试后提交 PR，帮助更多人使用。

下方说明主要供 AI 助手、维护者和需要排查问题的用户参考。

## 使用与排查

面板顶部的开关可即时切换音效与原声。开机启动可在面板里调整。

```sh
nahimic --status
systemctl --user status nahimic.service
journalctl --user -u nahimic.service -b
```

切回内置扬声器后，可用 `systemctl --user restart nahimic.service` 重新连接。设置保存在 `${XDG_DATA_HOME:-~/.local/share}/nahimic-linux/`。

## 构建与安装

AUR 的 `PKGBUILD` 位于 `packaging/`。构建依赖 MinGW-w64 GCC、C 编译器、pkg-config、libpulse、Python 和 cabextract。运行依赖 Wine、PySide6、PipeWire、PipeWire Pulse、libpulse、systemd。

```sh
git clone https://aur.archlinux.org/nahimic-linux.git
cd nahimic-linux
makepkg -si
```

构建会从 Microsoft Update 和 Nahimic 官方支持站点获取固定版本组件，并验证归档及实际使用文件的 SHA-256。界面与宿主程序通过 `make` 构建，`make DESTDIR=/tmp/nahimic-stage install` 可检查系统包目录布局。完整安装以 PKGBUILD 为准。

## 贡献设备适配

请先阅读 [AGENTS.md](AGENTS.md)。提交机器型号、声卡硬件 ID、PipeWire 输出信息，以及音效开关、参数保存、服务重启和连续播放的测试结果。每个型号使用与硬件匹配的配置，新增支持以本机验证为依据。

本项目为社区维护项目，未与 Nahimic、SteelSeries 或电脑厂商建立隶属关系。项目代码使用 MIT 许可证；下载的运行组件适用其原有许可。Nahimic 名称及相关商标归其权利人所有。
