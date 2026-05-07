# APLUSE ENGINE v3.4

基于 [apate](https://github.com/rippod/apate) 思路，用 Python 重新实现的文件伪装/还原工具。通过替换文件头部字节并追加加密元数据，将任意文件伪装为另一种格式（如将 `.rar` 伪装为 `.mp4`），同时支持一键还原，现在支持windows系统和安卓系统的还原。

## 功能特性

**核心能力**
- 一键伪装/还原：自动识别文件当前状态，原始文件执行伪装，伪装文件执行还原
- 批量处理：支持同时操作多个文件或整个文件夹
- 多版本兼容：支持 v1 / v2 / v3 / v4 四种元数据格式的解析与还原
- 自定义魔术字：支持 HEX 和文本两种输入，可随机生成，用于标记伪装文件

**恢复工具生成**
- Windows 恢复程序：打包为独立 `.exe`，无需 Python 环境即可在任意电脑上批量还原
- Android 恢复包：生成 Android 项目，编译为 `.apk` 安装到手机端还原伪装文件
- 恢复程序支持手动输入魔术字，同一工具可适配不同密钥

**界面与体验**
- 7 套主题：暗色极客、亮色极简、渐变幽蓝、暗金奢华、猛男猛粉、辐射废土、低调暗紫
- 拖拽添加：支持将文件/文件夹直接拖入列表
- 文件大小显示：列表项和状态栏实时显示文件数量与总大小
- 键盘快捷键：`Ctrl+O` 添加文件、`Delete` 删除选中、`Ctrl+D` 扫描、`Ctrl+Enter` 启动
- 操作日志持久化：所有操作记录同步写入 `apluse.log`

**安全与健壮**
- 配置文件自动迁移：从旧版 `mask_config.json` 无缝升级到新版配置
- 跨分区兼容：文件移动使用 `shutil.move`，支持不同盘符
- 文件占用检测：被其他程序锁定时给出明确提示
- 批量操作确认：执行前弹出二次确认，防止误操作

## 截图

### v3.1

![v3.1](README.assets/image-20260409010208641.png)

### v3.3

![v3.3-1](README.assets/image-20260409010324267.png)

![v3.3-2](README.assets/image-20260409010347858.png)

### v3.4

![image-20260507173405311](README.assets/image-20260507173405311.png)

#### 手机恢复：

![Screenshot_20260507_174010](README.assets/mobile.jpg)

## 使用方式

### 基本操作

1. 启动程序后，在「核心密钥」区域确认或修改魔术字
2. 将目标文件拖入「目标执行队列」，或点击按钮选择
3. 将伪装用的媒体文件拖入「面具文件库」
4. 点击「引擎启动」即可自动完成伪装或还原

### 生成恢复工具

伪装完成后，点击「生成恢复程序」按钮，选择：
- **Windows (.exe)**：生成 `{魔术字}_restore.exe`，放到伪装文件所在目录双击运行即可批量还原
- **Android (.apk)**：生成 Android 项目，用 Android Studio 编译后安装到手机

### 键盘快捷键

| 快捷键 | 功能 |
|---|---|
| `Ctrl+O` | 添加目标文件 |
| `Ctrl+Shift+O` | 添加面具文件 |
| `Delete` | 删除选中项 |
| `Ctrl+D` | 扫描分析队列 |
| `Ctrl+Enter` | 启动引擎 |

## 环境要求

- Python 3.8+
- PyQt5

```bash
pip install pyqt5
```

## 构建

### PyInstaller（推荐）

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=icon.ico -n apluse --add-data "icon.ico;." --clean main.py
```

### Nuitka

```bash
nuitka --standalone --onefile --windows-console-mode=disable --enable-plugin=pyqt5 --windows-icon-from-ico=icon.ico --output-filename=apluse --include-data-files=icon.ico=icon.ico --clean-cache=all main.py
```

### 生成恢复工具的额外依赖

生成 Windows 恢复程序需要系统中安装 Python 和 PyInstaller（程序会自动检测并安装）。

生成 Android 恢复包需要 [Android Studio](https://developer.android.com/studio)，程序会自动创建完整项目，用 Android Studio 打开后一键编译即可。如需自动转换图标，需安装 `pip install Pillow`。

## 项目结构

```
apluse/
├── main.py              # 程序入口
├── core.py              # 核心引擎：伪装/还原逻辑、配置管理、恢复工具生成
├── ui.py                # PyQt5 界面
├── themes.py            # 主题配色方案
├── android_templates.py # Android 项目模板
├── icon.ico             # 应用图标
└── apluse_config.json   # 配置文件（自动生成）
```

## 致谢

思路来源：[apate](https://github.com/rippod/apate)
