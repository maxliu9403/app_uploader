# VM 脚本优化文档

## 概述

本次优化对 `vm.sh` 脚本进行了全面改造，增加了详细的中文日志输出和结构化的错误状态返回，便于服务端解析和其他服务判断执行结果。

---

## 错误码定义

脚本新增了标准化的退出码，服务端可根据退出码准确判断错误类型：

| 退出码 | 常量名 | 含义 |
|--------|--------|------|
| `0` | `EXIT_SUCCESS` | 执行成功 |
| `1` | `EXIT_PARAM_ERROR` | 通用错误 / 参数错误 |
| `10` | `EXIT_NETWORK_FAIL` | 网络验证失败（所有线路） |
| `11` | `EXIT_PROXY_SWITCH_FAIL` | 代理切换失败 |
| `12` | `EXIT_CONFIG_GEN_FAIL` | 配置文件生成失败 |
| `20` | `EXIT_BACKUP_NOT_FOUND` | 备份文件不存在 |
| `21` | `EXIT_BACKUP_EXTRACT_FAIL` | 备份解压失败 |
| `22` | `EXIT_RESTORE_FAIL` | 数据恢复失败 |
| `30` | `EXIT_UNKNOWN_APP` | APP 类型未知 |
| `31` | `EXIT_APP_NOT_INSTALLED` | APP 未安装 |
| `40` | `EXIT_PERMISSION_ERROR` | 权限/SELinux 错误 |

---

## 日志辅助函数

新增 6 个日志辅助函数，统一日志格式：

```bash
log_step()    # 📋 [步骤] 描述当前执行步骤
log_info()    # ℹ️  [信息] 输出信息性日志
log_success() # ✅ [成功] 操作成功
log_warning() # ⚠️  [警告] 警告信息
log_error()   # ❌ [错误] 错误信息
log_fatal()   # 🚨 [致命] 致命错误，通常导致脚本退出
```

### 使用示例

```bash
log_step "开始加载账号: $NAME"
log_info "备份文件: $ARCHIVE"
log_success "账号加载成功"
log_warning "检测到版本变化"
log_error "参数不能为空"
log_fatal "备份文件不存在"
```

---

## 结构化结果输出

### 格式定义

脚本执行结束时输出结构化结果，格式如下：

```
##RESULT##|<status>|<code>|<message>
```

| 字段 | 说明 | 示例 |
|------|------|------|
| `status` | 状态 (`success` / `error`) | `success` |
| `code` | 退出码 | `0` |
| `message` | 消息描述 | `账号 Vinted_HK_001 创建成功` |

### 输出示例

**成功：**
```
##RESULT##|success|0|账号 Vinted_HK_001 创建成功
```

**失败：**
```
##RESULT##|error|20|备份文件不存在
```

### 函数定义

```bash
output_result() {
    local status="$1"   # success / error
    local code="$2"     # 错误码
    local message="$3"  # 消息
    echo "##RESULT##|${status}|${code}|${message}"
}
```

---

## 服务端解析

`app.py` 中的 SSE 端点已更新，可解析结构化结果：

### 解析逻辑

```python
# 解析结构化结果: ##RESULT##|status|code|message
if line_stripped.startswith('##RESULT##|'):
    parts = line_stripped.split('|', 3)
    if len(parts) >= 4:
        script_result = {
            'status': parts[1],
            'code': parts[2],
            'message': parts[3]
        }
```

### SSE 响应格式

**成功响应：**
```json
{
    "type": "success",
    "message": "账号 Vinted_HK_001 创建成功",
    "exit_code": "0"
}
```

**错误响应：**
```json
{
    "type": "error",
    "message": "备份文件不存在",
    "exit_code": "20"
}
```

---

## 日志输出示例

### NEW 操作

```
═══════════════════════════════════════════════════════════════
📋 [步骤] 开始创建新账号
═══════════════════════════════════════════════════════════════

📋 [步骤] 切换网络代理: HK_001 (地区: HK)
📋 [步骤] 生成设备指纹: Vinted | 地区: HK
ℹ️  [信息] 配置写入完成: 账号=Vinted_HK_001, 节点=HK_001, 类型=Vinted
📋 [步骤] 保存配置副本到 Profile 目录
📋 [步骤] 注入 GMS Ads ID 和 SSAID
📋 [步骤] 同步 GPS 位置信息
📋 [步骤] 修复应用权限和 SELinux 上下文
📋 [步骤] 重置网络连接 (飞行模式刷新)
📋 [步骤] 清理干扰应用进程
📋 [步骤] 解冻目标应用: com.vinted.app

═══════════════════════════════════════════════════════════════
✅ [成功] 新账号创建成功: Vinted_HK_001
═══════════════════════════════════════════════════════════════
ℹ️  [信息] 账号名称: Vinted_HK_001
ℹ️  [信息] 应用类型: Vinted
ℹ️  [信息] 目标地区: HK
ℹ️  [信息] 代理节点: HK_001
ℹ️  [信息] 包名: com.vinted.app
═══════════════════════════════════════════════════════════════

##RESULT##|success|0|账号 Vinted_HK_001 创建成功
```

### LOAD 操作

```
═══════════════════════════════════════════════════════════════
📋 [步骤] 开始加载账号: Vinted_HK_001
═══════════════════════════════════════════════════════════════

ℹ️  [信息] 备份文件: /sdcard/MultiApp_Farm/Vinted_HK_001.tar.gz
ℹ️  [信息] 配置文件: /sdcard/MultiApp_Farm/Profiles/Vinted_HK_001.conf
ℹ️  [信息] APP类型: Vinted, 地区: HK
ℹ️  [信息] 目标应用包名: com.vinted.app
📋 [步骤] 开始还原账号: Vinted_HK_001 (节点: HK_001)
📋 [步骤] 冻结目标应用: com.vinted.app
📋 [步骤] 解压备份文件...
✅ [成功] 备份解压完成
📋 [步骤] 修复权限和 SELinux 上下文...
📋 [步骤] 清理网络状态
📋 [步骤] 切换代理节点: HK_001 (地区: HK)
📋 [步骤] 清理干扰应用进程
📋 [步骤] 解冻应用: com.vinted.app
📋 [步骤] 启动应用

═══════════════════════════════════════════════════════════════
✅ [成功] 账号加载成功: Vinted_HK_001
═══════════════════════════════════════════════════════════════
ℹ️  [信息] 账号名称: Vinted_HK_001
ℹ️  [信息] 应用类型: Vinted
ℹ️  [信息] 目标地区: HK
ℹ️  [信息] 代理节点: HK_001
ℹ️  [信息] 包名: com.vinted.app
═══════════════════════════════════════════════════════════════

##RESULT##|success|0|账号 Vinted_HK_001 加载成功
```

### SAVE 操作

```
═══════════════════════════════════════════════════════════════
📋 [步骤] 开始保存账号: Vinted_HK_001
═══════════════════════════════════════════════════════════════

ℹ️  [信息] 账号名称: Vinted_HK_001
📋 [步骤] 解冻应用: com.vinted.app

═══════════════════════════════════════════════════════════════
✅ [成功] 账号保存成功: Vinted_HK_001
═══════════════════════════════════════════════════════════════
ℹ️  [信息] 账号名称: Vinted_HK_001
ℹ️  [信息] 应用类型: Vinted
ℹ️  [信息] 备份文件: /sdcard/MultiApp_Farm/Profiles/Vinted_HK_001.tar.gz
═══════════════════════════════════════════════════════════════

##RESULT##|success|0|账号 Vinted_HK_001 保存成功
```

---

## 错误处理示例

### 备份文件不存在

```
═══════════════════════════════════════════════════════════════
📋 [步骤] 开始加载账号: NonExistent_001
═══════════════════════════════════════════════════════════════

ℹ️  [信息] 备份文件: /sdcard/MultiApp_Farm/NonExistent_001.tar.gz
ℹ️  [信息] 配置文件: /sdcard/MultiApp_Farm/Profiles/NonExistent_001.conf
🚨 [致命] 备份文件不存在: /sdcard/MultiApp_Farm/NonExistent_001.tar.gz
##RESULT##|error|20|备份文件不存在
```

### 未知 APP 类型

```
🚨 [致命] 未知的APP类型: UnknownApp
##RESULT##|error|30|未知的APP类型: UnknownApp
```

---

## 兼容性

服务端实现了向后兼容：
- 如果脚本输出了 `##RESULT##` 格式的结果，优先使用该结果
- 如果没有输出结构化结果（旧版脚本），则回退到仅依赖 `process.returncode` 判断

---

## 文件变更

| 文件 | 变更内容 |
|------|----------|
| `script/vm.sh` | 添加错误码定义、日志函数、结构化输出、详细中文日志 |
| `app.py` | 更新 `/api/vm/new`, `/api/vm/save`, `/api/vm/load` 端点解析结构化结果 |
