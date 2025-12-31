# 设备ID绑定功能实现方案

## 实现概述

本文档详细说明设备ID绑定功能的完整实现方案，包括后端Service层、API路由层和前端的所有修改。

## 已完成的修改

### 1. ConfigManager ✅
**文件**: `core/config.py`

**修改内容**:
- `get_config_file(device_id=None)`: 支持device_id参数
- `load(device_id=None)`: 支持加载设备特定配置
- `save(config, device_id=None)`: 支持保存到设备特定路径

**路径逻辑**:
- 如果提供device_id: `./network_config/{device_id}/config.yaml`
- 否则使用默认路径: `./config.yaml`

### 2. DeviceService ✅
**文件**: `services/device_service.py`

**新增功能**:
- `_ensure_device_config_dir(device_id)`: 自动创建设备配置目录
- 在`get_devices()`中自动为每个设备创建配置文件夹
- 在`save_device_config()`中确保设备配置目录存在

**自动创建逻辑**:
1. 检查`./network_config/{device_id}/`目录是否存在
2. 不存在则创建目录
3. 从`config_temp.yaml`复制配置文件
4. 如果模板不存在，创建基本的空配置

### 3. ProxyService（部分完成）✅
**文件**: `services/proxy_service.py`

**已修改的方法**:
- `get_all_proxies(device_id=None)`
- `add_proxy(data, device_id=None)`
- `update_proxy_by_name(proxy_name, data, device_id=None)`

**注意**: 由于编辑冲突，部分方法可能需要手动验证

## 待完成的修改

### 4. TransitService（进行中）
**文件**: `services/transit_service.py`

**需要修改的方法**:
```python
# 修改前
def get_all_transits(self):
    config = self.config_manager.load()

# 修改后
def get_all_transits(self, device_id=None):
    config = self.config_manager.load(device_id)

# 同样的模式应用到:
- add_transit(data, device_id=None)
- update_transit(index, data, device_id=None)
- delete_transit(index, device_id=None)
```

**保存配置时**:
```python
# 修改前
self.config_manager.save(config)

# 修改后
self.config_manager.save(config, device_id)
```

### 5. API路由层
**文件**: `routes/proxy_routes.py` 和 `routes/transit_routes.py`

**实现策略**: 从请求中获取device_id参数

#### 方案A: 查询参数（推荐）
```python
@bp.route('/proxies', methods=['GET'])
def get_proxies():
    device_id = request.args.get('device_id')
    success, data = proxy_service.get_all_proxies(device_id)
    # ...
```

#### 方案B: 请求头
```python
device_id = request.headers.get('X-Device-ID')
```

#### 方案C: 请求体（POST/PUT）
```python
data = request.json
device_id = data.get('device_id')
```

**推荐使用方案A（查询参数）**，因为:
- GET请求友好
- 前端实现简单
- 调试方便

### 6. 前端实现

#### 6.1 设备选择器UI
**文件**: `templates/proxy_manager.html`

**添加位置**: 页面头部

```html
<div class="device-selector">
    <label>📱 当前设备:</label>
    <select id="deviceSelector" onchange="switchDevice()">
        <option value="">加载中...</option>
    </select>
</div>
```

**CSS样式**:
```css
.device-selector {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 6px;
}

.device-selector select {
    padding: 6px 12px;
    border-radius: 4px;
    min-width: 200px;
}
```

#### 6.2 JavaScript实现

**加载设备列表**:
```javascript
async function loadDeviceList() {
    try {
        const response = await fetch('/api/devices');
        const result = await response.json();
        
        if (result.success) {
            const selector = document.getElementById('deviceSelector');
            selector.innerHTML = '';
            
            result.data.forEach(device => {
                const option = document.createElement('option');
                option.value = device.device_id;
                option.textContent = device.remark ? 
                    `${device.device_id} (${device.remark})` : 
                    device.device_id;
                selector.appendChild(option);
            });
            
            // 从localStorage恢复上次选择的设备
            const lastDevice = localStorage.getItem('currentDeviceId');
            if (lastDevice) {
                selector.value = lastDevice;
            }
        }
    } catch (error) {
        console.error('加载设备列表失败:', error);
    }
}
```

**切换设备**:
```javascript
function switchDevice() {
    const selector = document.getElementById('deviceSelector');
    const deviceId = selector.value;
    
    // 保存到localStorage
    localStorage.setItem('currentDeviceId', deviceId);
    
    // 重新加载数据
    loadProxies();
    loadTransit();
}
```

**修改现有的加载函数**:
```javascript
async function loadProxies() {
    const deviceId = document.getElementById('deviceSelector').value;
    const url = deviceId ? 
        `/api/proxies?device_id=${encodeURIComponent(deviceId)}` : 
        '/api/proxies';
    
    const response = await fetch(url);
    // ... 处理响应
}

async function loadTransit() {
    const deviceId = document.getElementById('deviceSelector').value;
    const url = deviceId ? 
        `/api/transit?device_id=${encodeURIComponent(deviceId)}` : 
        '/api/transit';
    
    const response = await fetch(url);
    // ... 处理响应
}
```

**修改添加/编辑/删除函数**:
```javascript
async function addProxy(data) {
    const deviceId = document.getElementById('deviceSelector').value;
    const url = deviceId ? 
        `/api/proxies?device_id=${encodeURIComponent(deviceId)}` : 
        '/api/proxies';
    
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    // ...
}
```

#### 6.3 页面初始化
```javascript
document.addEventListener('DOMContentLoaded', function() {
    loadDeviceList();
    // 等待设备列表加载后再加载数据
    setTimeout(() => {
        loadProxies();
        loadTransit();
    }, 500);
});
```

### 7. Swagger文档更新

**需要更新的API端点**:

#### 代理管理API
```yaml
/api/proxies:
  get:
    parameters:
      - name: device_id
        in: query
        required: false
        type: string
        description: 设备ID，不提供则使用默认配置
  post:
    parameters:
      - name: device_id
        in: query
        required: false
        type: string
```

#### 中转线路API
```yaml
/api/transit:
  get:
    parameters:
      - name: device_id
        in: query
        required: false
        type: string
```

## 实现步骤

### Step 1: 完成TransitService修改
修改所有方法支持device_id参数

### Step 2: 更新API路由
在所有代理和中转线路API中添加device_id参数获取逻辑

### Step 3: 实现前端
添加设备选择器UI和JavaScript逻辑

### Step 4: 测试
- 测试设备文件夹自动创建
- 测试设备切换
- 测试数据隔离

## 测试用例

### 测试1: 设备文件夹自动创建
```bash
# 1. 连接新设备
# 2. 刷新设备列表
# 3. 验证 ./network_config/{device_id}/ 目录被创建
# 4. 验证 config.yaml 文件存在
```

### 测试2: 设备切换
```bash
# 1. 在设备A添加代理
# 2. 切换到设备B
# 3. 验证代理列表为空或显示设备B的代理
# 4. 在设备B添加代理
# 5. 切换回设备A
# 6. 验证设备A的代理仍然存在
```

### 测试3: 数据隔离
```bash
# 1. 设备A: 添加代理 proxy-a-1
# 2. 设备B: 添加代理 proxy-b-1
# 3. 验证 ./network_config/device-a/config.yaml 只包含 proxy-a-1
# 4. 验证 ./network_config/device-b/config.yaml 只包含 proxy-b-1
```

## 注意事项

1. **向后兼容**: 如果不提供device_id，系统使用默认的config.yaml
2. **错误处理**: 如果设备配置文件不存在，自动创建
3. **用户体验**: 设备选择器应该记住用户的选择（localStorage）
4. **性能**: 避免频繁读写配置文件，考虑缓存
5. **安全**: 验证device_id参数，防止路径遍历攻击

## 完成标准

- [ ] 所有Service方法支持device_id参数
- [ ] 所有API路由支持device_id参数
- [ ] 前端设备选择器正常工作
- [ ] 设备切换后数据正确加载
- [ ] 不同设备的配置完全隔离
- [ ] Swagger文档已更新
- [ ] 通过所有测试用例
