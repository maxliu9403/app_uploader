# 设备ID绑定功能 - 实现状态

## ✅ 已完成的工作

### 1. 核心配置层 ✅
**文件**: `core/config.py`

**ConfigManager改造完成**:
```python
# 支持device_id参数的方法
- get_config_file(device_id=None)  # 获取设备特定配置文件路径
- load(device_id=None)              # 加载设备特定配置
- save(config, device_id=None)      # 保存到设备特定路径
```

**路径逻辑**:
- 提供device_id: `./network_config/{device_id}/config.yaml`
- 不提供device_id: `./config.yaml` (向后兼容)

### 2. 设备服务层 ✅
**文件**: `services/device_service.py`

**新增功能**:
- `_ensure_device_config_dir(device_id)`: 自动创建设备配置目录和文件
- 在`get_devices()`中为每个连接的设备自动创建配置文件夹
- 在`save_device_config()`中确保设备配置目录存在

**自动创建逻辑**:
1. 检查`./network_config/{device_id}/`目录
2. 不存在则创建目录
3. 从`config_temp.yaml`复制配置文件
4. 如果模板不存在，创建基本空配置

### 3. 代理服务层 ✅
**文件**: `services/proxy_service.py`

**已修改的方法**（支持device_id参数）:
```python
- get_all_proxies(device_id=None)
- add_proxy(data, device_id=None)
- update_proxy_by_name(proxy_name, data, device_id=None)
- delete_proxy_by_name(proxy_name, device_id=None)
- delete_proxy_by_index(index, device_id=None)
```

**所有方法都已更新**:
- 调用`config_manager.load(device_id)`加载配置
- 调用`config_manager.save(config, device_id)`保存配置

### 4. 中转线路服务层 ✅
**文件**: `services/transit_service.py`

**已修改的方法**（支持device_id参数）:
```python
- get_all_transits(device_id=None)
- add_transit(data, device_id=None)
- update_transit(index, data, device_id=None)
- delete_transit(index, device_id=None)
```

**所有方法都已更新**:
- 调用`config_manager.load(device_id)`加载配置
- 调用`config_manager.save(config, device_id)`保存配置

---

## 📋 待实现的工作

### 5. API路由层改造 ⏳
**文件**: `routes/proxy_routes.py` 和 `routes/transit_routes.py`

**需要修改的内容**:

#### 5.1 代理管理API
**文件**: `routes/proxy_routes.py`

在每个路由函数中添加device_id参数获取：

```python
@bp.route('/proxies', methods=['GET'])
def get_proxies():
    """获取所有代理"""
    # 添加这一行获取device_id
    device_id = request.args.get('device_id')
    
    # 传递device_id给service
    success, data = proxy_service.get_all_proxies(device_id)
    
    if success:
        return jsonify({'success': True, 'data': data})
    else:
        return jsonify({'success': False, 'error': data}), 500

@bp.route('/proxies', methods=['POST'])
def add_proxy():
    """添加代理"""
    data = request.json
    
    # 添加这一行获取device_id
    device_id = request.args.get('device_id')
    
    # 传递device_id给service
    success, result = proxy_service.add_proxy(data, device_id)
    
    if success:
        return jsonify({'success': True, 'data': result})
    else:
        return jsonify({'success': False, 'error': result}), 400

# 同样的模式应用到:
# - PUT /proxies/<proxy_name> (update_proxy_by_name)
# - DELETE /proxies/<proxy_name> (delete_proxy_by_name)
# - DELETE /proxies/by-index/<int:index> (delete_proxy_by_index)
# - POST /proxies/batch (batch_add_proxies)
```

#### 5.2 中转线路API
**文件**: `routes/transit_routes.py`

```python
@bp.route('/transit', methods=['GET'])
def get_transit():
    """获取所有中转线路"""
    # 添加device_id参数获取
    device_id = request.args.get('device_id')
    
    success, data = transit_service.get_all_transits(device_id)
    
    if success:
        return jsonify({'success': True, 'data': data})
    else:
        return jsonify({'success': False, 'error': data}), 500

@bp.route('/transit', methods=['POST'])
def add_transit():
    """添加中转线路"""
    data = request.json
    device_id = request.args.get('device_id')
    
    success, result = transit_service.add_transit(data, device_id)
    
    if success:
        return jsonify({'success': True, 'data': result})
    else:
        return jsonify({'success': False, 'error': result}), 400

# 同样的模式应用到:
# - PUT /transit/<int:index> (update_transit)
# - DELETE /transit/<int:index> (delete_transit)
# - GET /transit/names (get_transit_names)
```

**修改清单**:
- [ ] `routes/proxy_routes.py` - 所有代理相关路由
- [ ] `routes/transit_routes.py` - 所有中转线路相关路由

### 6. 前端实现 ⏳
**文件**: `templates/proxy_manager.html`

#### 6.1 添加设备选择器UI

在页面头部添加（大约在第680行，header部分）:

```html
<div class="header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1>🔧 Proxy Manager</h1>
            <p>管理 config.yaml 中的代理配置</p>
            <!-- 新增：设备选择器 -->
            <div class="device-selector">
                <label>📱 当前设备:</label>
                <select id="deviceSelector" onchange="switchDevice()">
                    <option value="">加载中...</option>
                </select>
            </div>
        </div>
        <button class="btn btn-secondary" onclick="showPathSettingsModal()">
            ⚙️ 路径设置
        </button>
    </div>
</div>
```

#### 6.2 添加CSS样式

在`<style>`标签中添加（大约在第50行）:

```css
.device-selector {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 10px;
    padding: 8px 12px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 6px;
}

.device-selector label {
    font-size: 14px;
    font-weight: 500;
    opacity: 0.9;
}

.device-selector select {
    padding: 6px 12px;
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.9);
    color: #374151;
    font-size: 14px;
    cursor: pointer;
    min-width: 200px;
}

.device-selector select:focus {
    outline: none;
    border-color: white;
    box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.3);
}
```

#### 6.3 添加JavaScript函数

在`<script>`标签中添加（大约在第3350行之后）:

```javascript
// ==================== 设备管理功能 ====================

// 加载设备列表
async function loadDeviceList() {
    try {
        const response = await fetch('/api/devices');
        const result = await response.json();
        
        if (result.success) {
            const selector = document.getElementById('deviceSelector');
            const devices = result.data || [];
            
            if (devices.length === 0) {
                selector.innerHTML = '<option value="">无可用设备</option>';
                return;
            }
            
            selector.innerHTML = '';
            devices.forEach(device => {
                const option = document.createElement('option');
                option.value = device.device_id;
                option.textContent = device.remark ? 
                    `${device.device_id} (${device.remark})` : 
                    device.device_id;
                selector.appendChild(option);
            });
            
            // 从localStorage恢复上次选择
            const lastDevice = localStorage.getItem('currentDeviceId');
            if (lastDevice && devices.some(d => d.device_id === lastDevice)) {
                selector.value = lastDevice;
            } else if (devices.length > 0) {
                selector.value = devices[0].device_id;
                localStorage.setItem('currentDeviceId', devices[0].device_id);
            }
        }
    } catch (error) {
        console.error('加载设备列表失败:', error);
    }
}

// 切换设备
function switchDevice() {
    const selector = document.getElementById('deviceSelector');
    const deviceId = selector.value;
    
    if (deviceId) {
        localStorage.setItem('currentDeviceId', deviceId);
        // 重新加载数据
        loadProxies();
        loadTransit();
        showNotification(`已切换到设备: ${deviceId}`, 'success');
    }
}

// 获取当前设备ID
function getCurrentDeviceId() {
    const selector = document.getElementById('deviceSelector');
    return selector ? selector.value : null;
}
```

#### 6.4 修改现有加载函数

修改`loadProxies()`函数:

```javascript
async function loadProxies() {
    try {
        // 获取当前设备ID
        const deviceId = getCurrentDeviceId();
        const url = deviceId ? 
            `/api/proxies?device_id=${encodeURIComponent(deviceId)}` : 
            '/api/proxies';
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.success) {
            paginationState.proxies.allData = result.data || [];
            paginationState.proxies.currentPage = 1;
            renderProxiesPage();
        } else {
            showNotification('加载代理列表失败: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('加载代理列表失败:', error);
        showNotification('加载代理列表失败: ' + error.message, 'error');
    }
}
```

修改`loadTransit()`函数:

```javascript
async function loadTransit() {
    try {
        // 获取当前设备ID
        const deviceId = getCurrentDeviceId();
        const url = deviceId ? 
            `/api/transit?device_id=${encodeURIComponent(deviceId)}` : 
            '/api/transit';
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.success) {
            paginationState.transit.allData = result.data || [];
            paginationState.transit.currentPage = 1;
            renderTransitPage();
        } else {
            showNotification('加载中转线路失败: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('加载中转线路失败:', error);
        showNotification('加载中转线路失败: ' + error.message, 'error');
    }
}
```

修改所有添加/编辑/删除函数，在URL中添加device_id参数:

```javascript
// 示例：添加代理
async function submitProxy() {
    const deviceId = getCurrentDeviceId();
    const url = deviceId ? 
        `/api/proxies?device_id=${encodeURIComponent(deviceId)}` : 
        '/api/proxies';
    
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(proxyData)
    });
    // ...
}
```

#### 6.5 页面初始化

修改页面加载事件:

```javascript
document.addEventListener('DOMContentLoaded', function() {
    // 先加载设备列表
    loadDeviceList();
    
    // 延迟加载数据，等待设备列表加载完成
    setTimeout(() => {
        loadProxies();
        loadTransit();
    }, 500);
});
```

---

## 🧪 测试步骤

### 测试1: 设备文件夹自动创建
```bash
1. 启动应用
2. 连接新设备（通过ADB）
3. 刷新设备列表（访问 /api/devices）
4. 验证创建了 ./network_config/{device_id}/ 目录
5. 验证 config.yaml 文件存在
```

### 测试2: 设备切换
```bash
1. 在设备A添加代理 "proxy-a-1"
2. 在前端切换到设备B
3. 验证代理列表为空
4. 在设备B添加代理 "proxy-b-1"
5. 切换回设备A
6. 验证仍然显示 "proxy-a-1"
```

### 测试3: 配置文件隔离
```bash
1. 查看 ./network_config/device-a/config.yaml
   - 应该只包含 proxy-a-1
2. 查看 ./network_config/device-b/config.yaml
   - 应该只包含 proxy-b-1
```

---

## 📝 实现检查清单

### 后端 ✅
- [x] ConfigManager支持device_id参数
- [x] DeviceService自动创建设备文件夹
- [x] ProxyService所有方法支持device_id
- [x] TransitService所有方法支持device_id

### API路由层 ⏳
- [ ] proxy_routes.py - 添加device_id参数获取
- [ ] transit_routes.py - 添加device_id参数获取

### 前端 ⏳
- [ ] 添加设备选择器UI
- [ ] 添加CSS样式
- [ ] 实现loadDeviceList()函数
- [ ] 实现switchDevice()函数
- [ ] 修改loadProxies()添加device_id参数
- [ ] 修改loadTransit()添加device_id参数
- [ ] 修改所有添加/编辑/删除函数
- [ ] 修改页面初始化逻辑

### 文档 ✅
- [x] DEVICE_ID_IMPLEMENTATION.md - 完整实现方案
- [x] IMPLEMENTATION_STATUS.md - 当前状态（本文档）

---

## 🎯 下一步操作

1. **修改API路由层**（约30分钟）
   - 打开`routes/proxy_routes.py`
   - 在每个路由函数开头添加`device_id = request.args.get('device_id')`
   - 将device_id传递给service方法
   - 对`routes/transit_routes.py`重复相同操作

2. **实现前端**（约1小时）
   - 添加设备选择器HTML和CSS
   - 实现JavaScript设备管理函数
   - 修改现有的加载和操作函数

3. **测试验证**（约30分钟）
   - 运行测试用例
   - 验证设备切换功能
   - 验证配置隔离

---

## 💡 关键要点

1. **向后兼容**: 不提供device_id时使用默认config.yaml
2. **自动创建**: 连接设备时自动创建配置文件夹
3. **数据隔离**: 不同设备的配置完全独立
4. **用户体验**: 使用localStorage记住用户选择的设备

---

## 🔗 相关文档

- `DEVICE_ID_IMPLEMENTATION.md` - 详细实现方案
- `config_temp.yaml` - 配置模板文件
- `core/config.py` - ConfigManager实现
- `services/device_service.py` - DeviceService实现
- `services/proxy_service.py` - ProxyService实现
- `services/transit_service.py` - TransitService实现
