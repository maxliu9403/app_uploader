# Proxy Manager API 文档

## 📖 简介

这是 Proxy Manager 系统的完整 API 文档。本系统使用 Swagger/OpenAPI 规范来提供交互式的 API 文档界面。

## 🚀 快速开始

### 安装依赖

首先，确保安装所有必需的依赖：

```bash
pip install -r requirements.txt
```

### 启动应用

```bash
python app.py
```

应用将在 `http://localhost:5000` 上启动。

### 访问 Swagger 文档

启动应用后，在浏览器中访问：

```
http://localhost:5000/api/docs
```

你将看到完整的交互式 API 文档界面，可以直接在页面上测试所有 API 接口。

## 📋 API 分类

### 1. 代理管理 (Proxy Management)
管理普通代理服务器的增删改查操作。

**主要接口：**
- `GET /api/proxies` - 获取所有代理
- `POST /api/proxies` - 添加新代理
- `POST /api/proxies/batch` - 批量添加代理
- `PUT /api/proxies/{index}` - 更新代理（通过索引）
- `PUT /api/proxies/by-name/{proxy_name}` - 更新代理（通过名称，推荐）
- `DELETE /api/proxies/{index}` - 删除代理（通过索引）
- `DELETE /api/proxies/by-name/{proxy_name}` - 删除代理（通过名称，推荐）

### 2. 中转线路 (Transit Proxy)
管理中转线路的配置和操作。

**主要接口：**
- `GET /api/transit-proxies` - 获取所有中转线路
- `GET /api/transit-proxies/names` - 获取中转线路名称列表
- `POST /api/transit-proxies` - 添加中转线路
- `PUT /api/transit-proxies/{index}` - 更新中转线路
- `DELETE /api/transit-proxies/{index}` - 删除中转线路

### 3. VM账号管理 (VM Account Management)
管理虚拟机账号的创建、加载和保存操作。

**主要接口：**
- `GET /api/vm/generate-account-name` - 生成VM账号名称
- `GET /api/vm/proxy-names` - 获取代理节点名称列表
- `GET /api/vm/get-config-value` - 获取设备配置值
- `GET /api/vm/account-list` - 获取VM账号列表
- `POST /api/vm/new` - 创建新的VM账号（SSE流式响应）
- `POST /api/vm/save` - 保存VM账号（SSE流式响应）
- `POST /api/vm/load` - 加载VM账号（SSE流式响应）

### 4. 设备管理 (Device Management)
管理 Android 设备的连接和配置。

**主要接口：**
- `GET /api/devices` - 获取已连接的设备列表
- `GET /api/device-configs` - 获取已保存的设备配置
- `POST /api/device-configs` - 添加或更新设备配置
- `DELETE /api/device-configs/{device_id}` - 删除设备配置

### 5. 地区管理 (Region Management)
管理地区代码和名称。

**主要接口：**
- `GET /api/regions` - 获取所有地区
- `POST /api/regions` - 添加新地区
- `DELETE /api/regions/{code}` - 删除地区

### 6. 配置管理 (Settings Management)
管理系统路径和配置。

**主要接口：**
- `GET /api/path-settings` - 获取所有路径配置
- `POST /api/path-settings` - 更新路径配置

## 🔧 响应格式

所有 API 接口统一使用以下 JSON 响应格式：

### 成功响应
```json
{
  "success": true,
  "data": { /* 返回的数据 */ },
  "message": "操作成功信息（可选）"
}
```

### 失败响应
```json
{
  "success": false,
  "error": "错误信息描述"
}
```

### SSE 流式响应（VM操作）
VM 创建、保存、加载操作使用 Server-Sent Events (SSE) 流式响应：

```
data: {"type": "log", "message": "日志信息"}

data: {"type": "success", "message": "操作成功"}

data: {"type": "error", "message": "错误信息"}
```

## 📝 使用示例

### 1. 添加代理

```bash
curl -X POST http://localhost:5000/api/proxies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "proxy_us_01",
    "server": "192.168.1.100",
    "port": 1080,
    "username": "user123",
    "password": "pass123",
    "region": "US"
  }'
```

### 2. 获取所有代理

```bash
curl http://localhost:5000/api/proxies
```

### 3. 生成VM账号名称

```bash
curl "http://localhost:5000/api/vm/generate-account-name?app_type=TT&region=US"
```

### 4. 获取设备列表

```bash
curl http://localhost:5000/api/devices
```

## 🎯 注意事项

1. **SSE 流式响应：** VM 操作（创建、保存、加载）使用 SSE 流式响应，需要使用支持 EventSource 的客户端。

2. **设备ID：** 某些接口支持可选的 `device_id` 参数，用于指定特定的 Android 设备。

3. **地区代码：** 地区代码统一使用大写字母（如 US、JP、UK）。

4. **代理操作：** 推荐使用按名称操作的接口（`/by-name/{proxy_name}`），而不是按索引操作。

5. **错误处理：** 所有接口都包含完整的错误处理，返回详细的错误信息。

## 🔒 安全建议

1. 在生产环境中，建议配置适当的身份验证和授权机制。
2. 敏感信息（如密码）在日志中会被自动脱敏。
3. 建议使用 HTTPS 协议传输数据。

## 📚 更多信息

- Swagger UI: `http://localhost:5000/api/docs`
- OpenAPI JSON: `http://localhost:5000/apispec.json`
- 主页面: `http://localhost:5000/`

## 🐛 问题反馈

如果遇到问题或有建议，请通过项目的问题追踪系统反馈。

