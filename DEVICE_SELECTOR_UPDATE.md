# 设备选择器功能更新说明

## 📋 更新内容

### 1. 设备管理表格新增"当前设备"列

在设备管理标签页的设备列表中添加了一个单选按钮列，用户可以通过勾选来设置当前使用的设备。

**表格结构**：
```
| 当前设备 | 备注 | 设备ID | 状态 | 操作 |
|   (○)   | ... |  ...  | ... | ... |
```

### 2. 页面头部设备选择器改为只读展示

原来的下拉选择器改为只读的文本展示，显示当前选中的设备ID和备注。

**修改前**：
```html
<select id="deviceSelector" onchange="switchDevice()">
    <option value="">加载中...</option>
</select>
```

**修改后**：
```html
<span id="currentDeviceDisplay" style="color: #10b981; font-weight: 600; font-size: 14px;">
    加载中...
</span>
```

### 3. 新增JavaScript函数

#### `setCurrentDevice(deviceId)`
- 当用户在设备列表中勾选某个设备时调用
- 保存选择到localStorage
- 更新页面头部的设备显示
- 如果在代理或中转线路标签页，自动重新加载数据

#### `updateDeviceSelectorDisplay()`
- 更新页面头部的当前设备显示
- 从`/api/device-configs`获取设备列表
- 从localStorage读取当前设备ID
- 显示设备ID和备注

### 4. 修改现有函数

#### `refreshDeviceList()`
- 获取当前设备ID
- 为每个设备渲染单选按钮
- 当前设备的单选按钮默认选中

---

## 🎯 使用流程

1. **页面加载**：
   - 调用`updateDeviceSelectorDisplay()`更新头部显示
   - 显示当前选中的设备（从localStorage读取）

2. **切换设备**：
   - 用户在设备管理标签页勾选某个设备
   - 触发`setCurrentDevice(deviceId)`
   - 保存到localStorage
   - 更新头部显示
   - 重新加载当前标签页的数据

3. **数据隔离**：
   - 所有API调用通过`getCurrentDeviceId()`获取当前设备ID
   - 使用`buildUrlWithDeviceId()`构建带device_id参数的URL
   - 确保操作只影响当前选中的设备

---

## 📝 代码示例

### 设备列表渲染（带单选按钮）

```javascript
devices.forEach(device => {
    const isCurrentDevice = device.device_id === currentDeviceId;
    const row = document.createElement('tr');
    row.innerHTML = `
        <td style="text-align: center;">
            <input type="radio" 
                   name="currentDevice" 
                   value="${device.device_id}" 
                   ${isCurrentDevice ? 'checked' : ''}
                   onchange="setCurrentDevice('${device.device_id}')"
                   style="cursor: pointer; width: 18px; height: 18px;">
        </td>
        <td>${device.remark || '-'}</td>
        <td><code>${device.device_id}</code></td>
        <td><span class="status-badge status-${device.status}">${device.status}</span></td>
        <td>
            <button class="btn-icon" onclick="saveDeviceConfig('${device.device_id}')" title="保存配置">
                💾
            </button>
        </td>
    `;
    tbody.appendChild(row);
});
```

### 设置当前设备

```javascript
async function setCurrentDevice(deviceId) {
    try {
        console.log(`🔄 切换当前设备为: ${deviceId}`);
        
        // 保存到localStorage
        localStorage.setItem('currentDeviceId', deviceId);
        
        // 更新设备选择器显示
        await updateDeviceSelectorDisplay();
        
        // 显示成功提示
        showDeviceAlert('success', `已切换到设备: ${deviceId}`);
        
        // 如果当前在代理或中转线路标签页，重新加载数据
        const currentTab = document.querySelector('.tab-btn.active');
        if (currentTab) {
            const tabText = currentTab.textContent.trim();
            if (tabText.includes('代理列表')) {
                loadProxies();
            } else if (tabText.includes('中转线路')) {
                loadTransitProxies();
            }
        }
    } catch (error) {
        console.error('❌ 切换设备失败:', error);
        showDeviceAlert('error', '切换设备失败: ' + error.message);
    }
}
```

### 更新头部显示

```javascript
async function updateDeviceSelectorDisplay() {
    try {
        // 获取设备配置列表
        const configsResponse = await fetch('/api/device-configs');
        const configsResult = await configsResponse.json();
        
        const display = document.getElementById('currentDeviceDisplay');
        
        if (configsResult.success) {
            const devices = configsResult.data || [];
            
            // 从localStorage获取当前设备
            const currentDeviceId = localStorage.getItem('currentDeviceId');
            const currentDevice = devices.find(d => d.device_id === currentDeviceId);
            
            if (currentDevice) {
                display.textContent = currentDevice.remark ? 
                    `${currentDevice.device_id} (${currentDevice.remark})` : 
                    currentDevice.device_id;
                display.style.color = '#10b981';
            } else if (devices.length > 0) {
                // 默认选择第一个设备
                const firstDevice = devices[0];
                localStorage.setItem('currentDeviceId', firstDevice.device_id);
                display.textContent = firstDevice.remark ? 
                    `${firstDevice.device_id} (${firstDevice.remark})` : 
                    firstDevice.device_id;
                display.style.color = '#10b981';
            }
        }
    } catch (error) {
        console.error('❌ 更新设备选择器显示异常:', error);
    }
}
```

---

## ✅ 优势

1. **用户体验更好**：
   - 在设备列表中直接勾选，更直观
   - 头部显示当前设备，一目了然
   - 切换设备后自动刷新数据

2. **数据一致性**：
   - 所有操作都基于当前选中的设备
   - localStorage保证刷新页面后设备选择不丢失

3. **代码简洁**：
   - 单一数据源（localStorage）
   - 统一的设备ID获取方式（getCurrentDeviceId）
   - 统一的URL构建方式（buildUrlWithDeviceId）

---

**更新时间**: 2025-12-31  
**状态**: ✅ 已完成
