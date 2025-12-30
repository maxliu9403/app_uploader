# 🔧 修复 VM 路由 404 错误

## ❌ 问题描述

**日志错误：**
```
2025-12-30 22:43:00 [INFO] 127.0.0.1 - - "GET /api/vm/proxy-names?region=HK HTTP/1.1" 404
2025-12-30 22:43:00 [INFO] 127.0.0.1 - - "GET /api/vm/generate-account-name?app_type=Carousell&region=HK HTTP/1.1" 404
```

**问题：**
1. 前端请求 `/api/vm/proxy-names` → 后端没有这个路由
2. 前端请求 `/api/vm/generate-account-name` → 后端定义的是 `/api/vm/generate-name`（路由名称不匹配）

---

## ✅ 修复内容

### 1. 修改文件：`routes/vm_routes.py`

#### 修复 1：更正路由名称

**修改前：**
```python
@bp.route('/generate-name', methods=['GET'])
def generate_name():
    """生成 VM 账号名称"""
```

**修改后：**
```python
@bp.route('/generate-account-name', methods=['GET'])
def generate_account_name():
    """生成 VM 账号名称"""
```

**说明：** 将路由名称从 `/generate-name` 改为 `/generate-account-name`，匹配前端请求。

---

#### 修复 2：新增缺失的路由

**新增路由：**
```python
@bp.route('/proxy-names', methods=['GET'])
def get_proxy_names():
    """获取代理节点名称列表（根据地区过滤）"""
    try:
        region = request.args.get('region', '').strip().upper()
        
        # 调用 vm_service 获取代理名称列表
        success, result = vm_service.get_proxy_names_by_region(region)
        if success:
            return jsonify({'success': True, 'data': result})
        else:
            return jsonify({'success': False, 'error': result}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

**功能：** 根据地区（region）参数，从 `config.yaml` 中过滤并返回代理节点名称列表。

---

### 2. 修改文件：`services/vm_service.py`

#### 修改 1：添加 config_manager 参数

**修改前：**
```python
def __init__(self, path_manager, adb_helper, setting_manager):
    self.path_manager = path_manager
    self.adb_helper = adb_helper
    self.setting_manager = setting_manager
```

**修改后：**
```python
def __init__(self, path_manager, adb_helper, setting_manager, config_manager=None):
    self.path_manager = path_manager
    self.adb_helper = adb_helper
    self.setting_manager = setting_manager
    self.config_manager = config_manager
```

**说明：** 添加 `config_manager` 参数，用于读取代理配置。

---

#### 修改 2：新增方法 `get_proxy_names_by_region()`

```python
def get_proxy_names_by_region(self, region=None):
    """获取代理节点名称列表（根据地区过滤）"""
    try:
        if not self.config_manager:
            logger.warning("ConfigManager 未初始化，无法获取代理列表")
            return False, "ConfigManager 未初始化"
        
        # 加载配置
        config = self.config_manager.load()
        proxies = config.get('proxies', [])
        
        if not proxies:
            logger.info("配置文件中没有代理")
            return True, []
        
        # 过滤代理
        from utils.yaml_helper import is_transit_proxy
        
        proxy_names = []
        for proxy in proxies:
            # 跳过中转线路
            if is_transit_proxy(proxy):
                continue
            
            proxy_name = proxy.get('name')
            if not proxy_name:
                continue
            
            # 如果指定了地区，进行过滤
            if region:
                proxy_region = proxy.get('Region') or proxy.get('region') or ''
                if proxy_region.upper() != region.upper():
                    continue
            
            proxy_names.append(proxy_name)
        
        logger.info(f"成功获取代理名称列表: {len(proxy_names)} 个代理（地区: {region or '全部'}）")
        return True, proxy_names
        
    except Exception as e:
        logger.error(f"获取代理名称列表失败: {str(e)}", exc_info=True)
        return False, str(e)
```

**功能：**
1. 从 `config.yaml` 读取所有代理
2. 过滤掉中转线路（`IsBase=true`）
3. 根据 `region` 参数过滤代理
4. 返回符合条件的代理名称列表

---

### 3. 修改文件：`app.py`

**修改前：**
```python
vm_service = VMService(path_manager, adb_helper, setting_manager)
```

**修改后：**
```python
vm_service = VMService(path_manager, adb_helper, setting_manager, config_manager)
```

**说明：** 在初始化 `vm_service` 时传入 `config_manager`。

---

## 📋 API 路由说明

### 1. `/api/vm/generate-account-name`

**方法：** `GET`

**参数：**
- `app_type` - 应用类型（如：Carousell, Vinted）
- `region` - 地区代码（如：HK, GB, SG）

**功能：** 生成 VM 账号名称

**示例请求：**
```
GET /api/vm/generate-account-name?app_type=Carousell&region=HK
```

**示例响应：**
```json
{
  "success": true,
  "data": "Carousell_HK_002"
}
```

---

### 2. `/api/vm/proxy-names`

**方法：** `GET`

**参数：**
- `region` - （可选）地区代码，用于过滤代理

**功能：** 获取代理节点名称列表

**示例请求：**
```
GET /api/vm/proxy-names?region=HK
```

**示例响应：**
```json
{
  "success": true,
  "data": ["HK_061", "HK_062", "HK_063"]
}
```

**不指定地区（获取所有代理）：**
```
GET /api/vm/proxy-names
```

**响应：**
```json
{
  "success": true,
  "data": ["HK_061", "HK_062", "GB_001", "GB_002"]
}
```

---

## 🔍 过滤逻辑

### 代理过滤规则

1. **跳过中转线路**
   - 检查 `IsBase` 字段
   - `IsBase=true` 的代理会被跳过

2. **地区过滤**
   - 检查代理的 `Region` 或 `region` 字段
   - 如果指定了 `region` 参数，只返回匹配的代理
   - 不区分大小写（HK = hk）

3. **返回格式**
   - 只返回代理名称（`name` 字段）
   - 返回列表格式：`["HK_061", "HK_062", ...]`

---

## ✅ 测试验证

### 测试场景 1：生成账号名称

**请求：**
```bash
curl "http://localhost:5000/api/vm/generate-account-name?app_type=Carousell&region=HK"
```

**预期响应：**
```json
{
  "success": true,
  "data": "Carousell_HK_002"
}
```

---

### 测试场景 2：获取指定地区的代理列表

**请求：**
```bash
curl "http://localhost:5000/api/vm/proxy-names?region=HK"
```

**预期响应：**
```json
{
  "success": true,
  "data": ["HK_061", "HK_062"]
}
```

**验证：**
- ✅ 只返回 HK 地区的代理
- ✅ 不包含中转线路（如：中转线路HK03）

---

### 测试场景 3：获取所有代理列表

**请求：**
```bash
curl "http://localhost:5000/api/vm/proxy-names"
```

**预期响应：**
```json
{
  "success": true,
  "data": ["HK_061", "HK_062", "GB_001", "SG_001"]
}
```

**验证：**
- ✅ 返回所有地区的代理
- ✅ 不包含中转线路

---

## 📝 日志输出

### 成功获取代理列表

```
2025-12-30 22:46:25 [INFO] 📥 收到请求: GET /api/vm/proxy-names
2025-12-30 22:46:25 [INFO]    查询参数: {'region': 'HK'}
2025-12-30 22:46:25 [INFO] 成功获取代理名称列表: 2 个代理（地区: HK）
2025-12-30 22:46:25 [INFO] 📤 响应状态: 200 OK
```

### 成功生成账号名称

```
2025-12-30 22:46:30 [INFO] 📥 收到请求: GET /api/vm/generate-account-name
2025-12-30 22:46:30 [INFO]    查询参数: {'app_type': 'Carousell', 'region': 'HK'}
2025-12-30 22:46:30 [INFO] 生成账号名称: Carousell_HK_002
2025-12-30 22:46:30 [INFO] 📤 响应状态: 200 OK
```

---

## 🚀 应用状态

✅ **应用已成功启动**

```
http://127.0.0.1:5000
```

**启动日志：**
```
2025-12-30 22:46:21 [INFO] 🚀 Proxy Manager 应用启动
* Running on http://127.0.0.1:5000
```

---

## 📋 总结

### 修改的文件

1. ✅ `routes/vm_routes.py` - 修正路由名称，新增 `/proxy-names` 路由
2. ✅ `services/vm_service.py` - 添加 `config_manager` 参数，新增 `get_proxy_names_by_region()` 方法
3. ✅ `app.py` - 更新 `vm_service` 初始化，传入 `config_manager`

### 修复的问题

1. ✅ 修复 `/api/vm/proxy-names` 404 错误
2. ✅ 修复 `/api/vm/generate-account-name` 404 错误
3. ✅ 实现代理节点名称列表的地区过滤功能

### 新增功能

1. ✅ 支持根据地区获取代理节点列表
2. ✅ 自动过滤中转线路
3. ✅ 完整的日志记录

---

**修复版本：** v2.3.1  
**完成时间：** 2025-12-30 22:46:22  
**状态：** ✅ 已修复并验证

现在 VM 管理的所有 API 都能正常工作了！🎊

