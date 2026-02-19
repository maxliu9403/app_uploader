# Proxy Manager & App Uploader

这是一个集成了 Android 设备代理管理、环境模拟 (VM) 和 Carousell 自动化操作的综合工具平台。

## 📋 项目概览

本项目主要包含两个核心模块：

1.  **Proxy Manager (Web 管理端)**
    *   基于 Flask 的 Web 界面。
    *   管理 Clash 代理配置。
    *   管理连接的 Android 设备。
    *   执行 VM 脚本操作（创建、保存、加载环境）。
    *   提供 RESTful API 和 Swagger 文档。

2.  **Carousell Automation (`main.py`)**
    *   自动化 Carousell 商品上架与编辑脚本。
    *   基于 ADB 和 OpenCV 进行图像识别与自动化控制。
    *   集成 OCR (EasyOCR) 用于文本识别。
    *   支持智能混合输入 (Smart Hybrid Input) 模拟人工操作。

## 🛠️ 环境要求

*   **操作系统**: Windows / Linux / macOS
*   **Python**: 3.8+
*   **依赖工具**:
    *   [ADB (Android Debug Bridge)](https://developer.android.com/studio/releases/platform-tools) (需配置到环境变量或在配置中指定路径)
    *   即插即用的 Android 设备或模拟器 (需 Root 权限以支持 VM 脚本功能)

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

**注意**: `main.py` 自动化脚本需要额外的依赖（如 `opencv-python`, `easyocr` 等），请确保已安装：

```bash
pip install opencv-python pandas openpyxl easyocr adbutils
```

### 2. 配置文件

项目包含敏感配置，**请勿直接提交配置文件**。请复制示例文件创建本地配置：

```bash
# 复制主配置文件 (Clash 代理配置)
copy config.yaml.example config.yaml

# 复制设置文件 (应用路径与设备配置)
copy config\setting.yaml.example config\setting.yaml
```

编辑 `config/setting.yaml`，填入正确的 ADB 路径和设备信息：

```yaml
adb_path: "D:/platform-tools/adb.exe"  # 你的 ADB 路径
vm_script_path: "/data/local/tmp/vm.sh" # 设备端脚本路径
...
```

### 3. 运行 Web 管理端

启动 Flask 应用：

```bash
python app.py
```

*   访问 Web 界面: `http://localhost:5000`
*   API 文档 (Swagger): `http://localhost:5000/api/docs`

### 4. 运行自动化脚本

确保设备已连接并授权 USB 调试：

```bash
python main.py
```

## 📂 项目结构

```
app_uploader/
├── app.py                  # Web 应用入口 (Flask)
├── main.py                 # 自动化脚本入口 (Carousell)
├── config.yaml             # [配置] 代理节点配置 (不提交)
├── config/                 # 配置目录
│   ├── setting.yaml        # [配置] 环境与设备设置 (不提交)
│   └── ...
├── core/                   # 核心逻辑 (PathManager, ConfigManager)
├── services/               # 业务逻辑层 (Proxy, Device, VM, Region)
├── routes/                 # API 路由定义
├── script/                 # 设备端 Shell 脚本
│   ├── vm.sh               # VM 环境切换核心脚本
│   └── gen.sh              # 配置生成脚本
├── utils/                  # 工具函数 (ADB, YAML)
└── docs/                   # 文档目录
```

## 🧩 主要功能说明

### Web 管理端 (`app.py`)
*   **代理管理**: 查看和切换 Clash 代理节点与策略组。
*   **VM 操作**:
    *   **New**: 创建全新应用环境（随机化设备 ID 等）。
    *   **Save**: 保存当前环境状态到本地。
    *   **Load**: 加载已保存的环境。
*   **设备管理**: 实时查看设备连接状态。

### 自动化脚本 (`main.py`)
*   **智能输入**: 模拟人类打字行为。
*   **图像识别**: 自动识别屏幕元素（按钮、输入框）。
*   **区域检测**: 自动检测网络环境区域 (HK/my/sg) 并调整策略。
*   **OCR 集成**: 识别屏幕文本信息。

## ⚠️ 注意事项

1.  **安全性**: `config.yaml` 包含代理服务器密码，`setting.yaml` 包含设备路径，**切勿提交到 Git 仓库**。
2.  **ADB 连接**: 确保 `adb` 命令可用，且设备已开启 USB 调试。
3.  **VM 脚本**: `vm.sh` 需推送至设备 (`/data/local/tmp/`) 并给予执行权限 (`chmod +x`) 才能正常工作。

## 📝 许可证

Private / Internal Use Only
