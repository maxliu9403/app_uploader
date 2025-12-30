# 🔧 YAML 格式保留修复说明

## 📋 用户需求

**核心要求：**
对 `config.yaml` 的修改操作**只允许修改 `proxies` 和 `proxy-groups` 两个区域**，其他所有区域（包括注释、格式、空行）必须完全保持不变。

---

## 🎯 修改内容

### 文件：`utils/yaml_helper.py`

#### 修改的方法：`save_yaml_file()`

**修改策略：**
1. 读取原文件内容
2. 使用正则表达式精确匹配 `proxies` 和 `proxy-groups` 区域
3. 只替换这两个区域的内容，保留所有其他内容
4. 写回文件

**关键代码：**

```python
@staticmethod
def save_yaml_file(file_path, config):
    """
    保存配置到 YAML 文件
    
    ⚠️ 重要：只修改 proxies 和 proxy-groups 两个区域，其他所有内容保持不变
    """
    try:
        # 读取原文件
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # 生成新的 proxies 内容
        new_proxies_content = YAMLHelper._generate_proxies_section(config)
        
        # 生成新的 proxy-groups 内容
        new_proxy_groups_content = YAMLHelper._generate_proxy_groups_section(config)
        
        # 使用正则表达式替换 proxies 部分
        # 匹配从 "proxies:" 后的换行符开始，到下一个 "# ====" 注释行之前
        proxies_pattern = r'(proxies:\n)((?:.*\n)*?)(?=# ====)'
        original_content = re.sub(
            proxies_pattern,
            f'\\1{new_proxies_content}\n',
            original_content,
            count=1,
            flags=re.MULTILINE
        )
        
        # 使用正则表达式替换 proxy-groups 部分
        proxy_groups_pattern = r'(proxy-groups:\n)((?:.*\n)*?)(?=# ====)'
        original_content = re.sub(
            proxy_groups_pattern,
            f'\\1{new_proxy_groups_content}\n',
            original_content,
            count=1,
            flags=re.MULTILINE
        )
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        
        logger.info(f"✅ 配置文件保存成功（只修改了 proxies 和 proxy-groups）: {file_path}")
```

---

### 新增方法：`_generate_proxies_section()`

**功能：** 生成 `proxies` 部分的内容（保持行内 JSON 格式）

```python
@staticmethod
def _generate_proxies_section(config):
    """生成 proxies 部分的内容"""
    lines = []
    proxies = config.get('proxies', [])
    
    # 分类代理
    transit_proxies = [p for p in proxies if is_transit_proxy(p)]
    normal_proxies = [p for p in proxies if not is_transit_proxy(p)]
    
    # 写入中转线路
    if transit_proxies:
        lines.append('  # 1. 中转基座 (Trojan)')
        for proxy in transit_proxies:
            proxy_copy = {k: v for k, v in proxy.items() if k != '_index'}
            proxy_json = json.dumps(proxy_copy, ensure_ascii=False, separators=(',', ':'))
            lines.append(f'  - {proxy_json}')
        lines.append('')
    
    # 写入普通代理
    if normal_proxies:
        region = normal_proxies[0].get('Region') or normal_proxies[0].get('region') or 'HK'
        region_name = {'HK': '香港', 'GB': '英国', 'SG': '新加坡', 'MY': '马来西亚', 
                       'PH': '菲律宾', 'FR': '法国'}.get(region, region)
        
        lines.append(f'  # 2. {region_name}出口 (绑定中转)')
        for proxy in normal_proxies:
            proxy_copy = {k: v for k, v in proxy.items() if k != '_index'}
            proxy_json = json.dumps(proxy_copy, ensure_ascii=False, separators=(',', ':'))
            lines.append(f'  - {proxy_json}')
        lines.append(' ')
    
    return '\n'.join(lines)
```

---

### 新增方法：`_generate_proxy_groups_section()`

**功能：** 生成 `proxy-groups` 部分的内容（保持 YAML 格式）

```python
@staticmethod
def _generate_proxy_groups_section(config):
    """生成 proxy-groups 部分的内容"""
    lines = []
    proxy_groups = config.get('proxy-groups', [])
    
    for group in proxy_groups:
        lines.append(f'  - name: "{group["name"]}"')
        lines.append(f'    type: {group["type"]}')
        if 'proxies' in group:
            lines.append('    proxies:')
            for proxy_name in group['proxies']:
                lines.append(f'      - "{proxy_name}"')
        lines.append('       ')  # 空行分隔
    
    return '\n'.join(lines)
```

---

## ✅ 保证不被修改的内容

以下内容**完全不会被修改**：

1. ✅ **基础设置** - `socks-port`, `mixed-port`, `allow-lan` 等
2. ✅ **性能优化** - `tcp-concurrent`, `global-client-fingerprint` 等
3. ✅ **DNS 设置** - 完整的 `dns:` 配置块，包括所有注释
4. ✅ **Tun 设置** - 完整的 `tun:` 配置块，包括所有注释
5. ✅ **Rules 规则** - 完整的 `rules:` 配置块，包括所有注释
6. ✅ **其他配置** - `redir-port` 等
7. ✅ **所有注释** - 包括分隔注释行（`# ====================`）
8. ✅ **所有空行** - 保持原有的空行格式
9. ✅ **原有格式** - 缩进、引号等格式完全保持

---

## 🔍 只会被修改的内容

以下内容**会被修改**（仅这两个区域）：

### 1. `proxies:` 区域

**从：**
```yaml
proxies:
  # 1. 中转基座 (Trojan)
  - {"name":"中转线路HK03",...}

  # 2. 香港出口 (绑定中转)
  - {"name":"HK_061",...}
  - {"name":"HK_062",...}
 
```

**到：**
```yaml
# ==================== 策略组 ====================
```

**说明：** 从 "proxies:" 的下一行开始，到 "# ==================== 策略组 ====================" 注释行之前的所有内容。

---

### 2. `proxy-groups:` 区域

**从：**
```yaml
proxy-groups:
  - name: "Select-HK-IP"
    type: select
    proxies:
      - "HK_061"
      - "HK_062"
       
  - name: "PROXY"
    type: select
    proxies:
      - "Select-HK-IP"
       
```

**到：**
```yaml
# ==================== 规则 ====================
```

**说明：** 从 "proxy-groups:" 的下一行开始，到 "# ==================== 规则 ====================" 注释行之前的所有内容。

---

## 📝 正则表达式说明

### Proxies 匹配模式

```python
proxies_pattern = r'(proxies:\n)((?:.*\n)*?)(?=# ====)'
```

**解释：**
- `(proxies:\n)` - 捕获 "proxies:" 和紧跟的换行符（保留）
- `((?:.*\n)*?)` - 非贪婪匹配任意内容和换行符（会被替换）
- `(?=# ====)` - 前瞻断言，匹配到 "# ====" 开头的行就停止（不包括该行）

---

### Proxy-Groups 匹配模式

```python
proxy_groups_pattern = r'(proxy-groups:\n)((?:.*\n)*?)(?=# ====)'
```

**解释：** 同上，只是匹配 "proxy-groups:" 区域

---

## 🧪 测试验证

### 测试脚本：`test_yaml_preserve.py`

```bash
cd D:\app_uploader
python test_yaml_preserve.py
```

**预期结果：**
- ✅ DNS/Tun 配置未改变
- ✅ Rules 规则未改变
- ✅ 所有注释行保持不变
- ✅ 只有 proxies 和 proxy-groups 内容被更新

---

## 📋 修改调用的所有位置

以下位置调用了 `YAMLHelper.save_yaml_file()`：

1. **`services/proxy_service.py`**
   - `add_proxy()` - 添加代理
   - `update_proxy()` - 更新代理
   - `update_proxy_by_name()` - 通过名称更新代理
   - `delete_proxy()` - 删除代理
   - `delete_proxy_by_name()` - 通过名称删除代理
   - `batch_add_proxies()` - 批量添加代理

2. **`services/transit_service.py`**
   - `add_transit()` - 添加中转线路
   - `update_transit()` - 更新中转线路
   - `delete_transit()` - 删除中转线路

**所有这些方法现在都只会修改 `proxies` 和 `proxy-groups` 区域！**

---

## ⚠️ 注意事项

1. **文件必须存在** - 如果文件不存在，会创建新文件（使用 `_write_new_config_file` 方法）
2. **分隔注释必须存在** - 正则表达式依赖 "# ====" 格式的分隔注释行
3. **行内 JSON 格式** - proxies 保持行内 JSON 格式（`- {...}`）
4. **YAML 格式** - proxy-groups 保持 YAML 格式（多行，带缩进）

---

## ✅ 总结

### 修改前

❌ **问题：** `save_yaml_file()` 会重写整个文件，丢失所有注释和格式

### 修改后

✅ **解决：** 只修改 `proxies` 和 `proxy-groups` 两个区域，其他所有内容完全保持不变

### 关键改进

1. ✅ 使用正则表达式精确匹配需要修改的区域
2. ✅ 保留所有注释（包括分隔注释）
3. ✅ 保留所有空行和格式
4. ✅ 保留所有其他配置区域（DNS, Tun, Rules, 等）
5. ✅ 只在必要时修改，不做任何额外的格式调整

---

**修复版本：** v2.3.0  
**完成时间：** 2025-12-30  
**状态：** ✅ 已修复

**祝您使用愉快！** 🎊

