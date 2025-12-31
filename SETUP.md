# 🚀 Proxy Manager 配置指南

## 📋 目录
- [快速开始](#快速开始)
- [配置文件说明](#配置文件说明)
- [安全注意事项](#安全注意事项)
- [常见问题](#常见问题)

## 快速开始

### 1. 克隆项目后的首次配置

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 复制配置文件示例
copy config.yaml.example config.yaml
copy config\setting.yaml.example config\setting.yaml

# Windows PowerShell
# Copy-Item config.yaml.example config.yaml
# Copy-Item config\setting.yaml.example config\setting.yaml

# Linux/Mac
# cp config.yaml.example config.yaml
# cp config/setting.yaml.example config/setting.yaml
```

### 2. 修改配置文件

编辑 `config.yaml` 和 `config/setting.yaml`，填入你自己的配置信息。

### 3. 启动应用

```bash
python app.py
```

## 配置文件说明

### 📄 config.yaml

这是 Clash 代理配置文件，包含以下主要部分：

#### 1. 基础设置
```yaml
socks-port: 7891          # SOCKS5 代理端口
mixed-port: 7890          # HTTP(S) + SOCKS5 混合端口
allow-lan: true           # 允许局域网连接
mode: rule                # 代理模式：rule（规则）/global（全局）/direct（直连）
```

#### 2. 节点列表
```yaml
proxies:
  # 中转节点
  - name: "中转线路示例"
    type: trojan
    server: "your-server.example.com"
    port: 443
    password: "your-password"
    
  # 代理节点
  - name: "HK_001"
    type: socks5
    server: "proxy.example.com"
    port: 1080
    region: "HK"
    username: "your-username"
    password: "your-password"
```

#### 3. 策略组
```yaml
proxy-groups:
  - name: "Select-HK-IP"
    type: select
    proxies:
      - "HK_001"
      - "HK_002"
```

#### 4. 规则
```yaml
rules:
  - DOMAIN-SUFFIX,google.com,PROXY
  - GEOIP,CN,DIRECT
  - MATCH,PROXY
```

### ⚙️ config/setting.yaml

这是应用程序配置文件，包含路径和设备信息：

```yaml
# 主配置文件路径
config_file_path: "D:/app_uploader/config.yaml"

# ADB 工具路径
adb_path: "D:/platform-tools/adb.exe"

# VM 相关路径（设备上的路径）
vm_script_path: "/data/local/tmp/vm.sh"
vm_accounts_file_path: "/sdcard/vm_accounts.txt"
vm_model_config_path: "/data/data/bin.mt.plus/model.conf"

# 设备列表
devices:
  - device_id: "emulator-5554"
    remark: "测试设备1"

# 地区列表
regions:
  - code: "US"
    name: "美国"
  - code: "HK"
    name: "香港"
```

## 🔒 安全注意事项

### ⚠️ 重要：保护敏感信息

1. **永远不要提交配置文件到 Git**
   - `config.yaml` 包含代理服务器的账号和密码
   - `config/setting.yaml` 可能包含设备信息
   - 这些文件已在 `.gitignore` 中被忽略

2. **使用示例文件**
   - `config.yaml.example` - 配置文件模板（可以提交）
   - `config/setting.yaml.example` - 设置文件模板（可以提交）
   - 其他开发者可以复制这些文件并填入自己的信息

3. **检查 Git 状态**
   ```bash
   # 确保敏感文件不会被提交
   git status
   
   # 应该看不到 config.yaml 和 setting.yaml
   ```

4. **如果不小心提交了敏感信息**
   ```bash
   # 从 Git 历史中移除（谨慎操作！）
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch config.yaml" \
     --prune-empty --tag-name-filter cat -- --all
   
   # 强制推送（警告：会覆盖远程历史）
   git push origin --force --all
   
   # 建议：立即更改所有泄露的密码
   ```

## 📝 配置文件结构

```
app_uploader/
├── config.yaml              # ❌ 真实配置（不提交）
├── config.yaml.example      # ✅ 配置模板（可提交）
├── config/
│   ├── setting.yaml         # ❌ 真实设置（不提交）
│   └── setting.yaml.example # ✅ 设置模板（可提交）
├── .gitignore               # Git 忽略规则
└── ...
```

## 🔧 常见问题

### Q1: 首次运行时提示找不到配置文件？
**A:** 复制示例配置文件：
```bash
copy config.yaml.example config.yaml
copy config\setting.yaml.example config\setting.yaml
```

### Q2: ADB 连接不上设备？
**A:** 检查以下几点：
1. `config/setting.yaml` 中的 `adb_path` 是否正确
2. 设备是否已通过 USB 连接或网络连接
3. 运行 `adb devices` 检查设备连接状态
4. 确保已开启 USB 调试模式

### Q3: 如何添加新的代理节点？
**A:** 编辑 `config.yaml`，在 `proxies` 部分添加：
```yaml
proxies:
  - name: "新节点名称"
    type: socks5
    server: "服务器地址"
    port: 端口号
    username: "用户名"
    password: "密码"
    region: "地区代码"
```

### Q4: 如何切换不同的配置文件？
**A:** 在 Web 界面中通过"配置管理"页面修改 `config_file_path`，或直接编辑 `config/setting.yaml`。

### Q5: 配置文件格式错误怎么办？
**A:** 
1. 检查 YAML 语法（注意缩进必须使用空格）
2. 使用在线 YAML 验证器检查格式
3. 参考 `config.yaml.example` 的正确格式
4. 查看应用日志文件 `logs/proxy_manager.log`

## 📚 更多帮助

- API 文档：`http://localhost:5000/api/docs`
- 完整 API 说明：参见 `API_DOCS.md`
- 问题反馈：通过项目的 Issue 系统

## 🎯 下一步

配置完成后，你可以：
1. 启动应用：`python app.py`
2. 访问主界面：`http://localhost:5000`
3. 查看 API 文档：`http://localhost:5000/api/docs`
4. 开始管理代理和设备

