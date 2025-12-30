# Proxy Manager - 代理配置管理工具

一个基于 Web 的图形化工具，用于管理 `config.yaml` 文件中的代理配置。

## 功能特性

- ✅ **可视化界面**: 美观的 Web 界面展示所有代理配置
- ✅ **增删改查**: 完整的 CRUD 操作支持
- ✅ **智能默认值**: type 默认为 `socks5`，skip-cert-verify 默认为 `true`
- ✅ **灵活配置**: 支持所有代理参数的自定义输入
- ✅ **实时保存**: 修改后立即保存到配置文件

## 快速开始

### 方法一：一键启动（推荐）

**Windows 用户：**
- 双击运行 `start_proxy_manager.bat`
- 脚本会自动检查环境、安装依赖并启动服务
- 浏览器会自动打开管理界面

**PowerShell 用户：**
```powershell
.\start_proxy_manager.ps1
```

### 方法二：手动启动

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **启动服务**
   ```bash
   python proxy_manager.py
   ```

3. **访问界面**
   打开浏览器访问: http://localhost:5000

## 使用说明

### 添加代理

1. 点击 "➕ 添加代理" 按钮
2. 填写必填项：
   - **名称**: 代理名称（必填）
   - **类型**: 代理类型，默认为 `socks5`
   - **服务器**: 服务器地址（必填）
   - **端口**: 服务器端口（必填）
3. 填写可选参数：
   - **用户名**: SOCKS5/HTTP 代理的用户名
   - **密码**: 代理密码
   - **SNI**: TLS SNI 域名
   - **跳过证书验证**: 默认为 `true`
   - **UDP**: 是否支持 UDP
   - **Dialer Proxy**: 上游代理名称
   - **其他参数**: JSON 格式的自定义参数
4. 点击 "保存" 完成添加

### 编辑代理

1. 在代理列表中点击 "编辑" 按钮
2. 修改需要更改的字段
3. 点击 "保存" 完成更新

### 删除代理

1. 在代理列表中点击 "删除" 按钮
2. 确认删除操作

## 支持的代理类型

- `socks5` (默认)
- `trojan`
- `http`
- `https`
- `ss` (Shadowsocks)
- `vmess`

## 配置文件格式

工具会自动读取和保存 `config.yaml` 文件。配置文件格式示例：

```yaml
proxies:
  - name: "HK-Res-01"
    type: "socks5"
    server: "us.arxlabs.io"
    port: 3010
    username: "user123"
    password: "pass123"
    skip-cert-verify: true
    udp: true
```

## 注意事项

- ⚠️ 修改配置前建议备份 `config.yaml` 文件
- ⚠️ 确保配置文件格式正确，否则可能导致解析失败
- ⚠️ 服务运行在 `0.0.0.0:5000`，局域网内其他设备也可以访问

## 故障排除

### 端口被占用

如果 5000 端口被占用，可以修改 `proxy_manager.py` 中的端口号：

```python
app.run(host='0.0.0.0', port=5000)  # 修改为其他端口
```

### 依赖安装失败

如果使用国内网络，脚本会自动使用清华镜像源。也可以手动安装：

```bash
pip install flask flask-cors pyyaml -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 配置文件不存在

如果 `config.yaml` 不存在，程序会自动创建一个空的配置文件。

## 技术栈

- **后端**: Flask (Python)
- **前端**: HTML + CSS + JavaScript
- **配置**: YAML

## 许可证

MIT License

