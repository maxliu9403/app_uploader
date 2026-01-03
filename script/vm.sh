#!/system/bin/sh
# Multi-App VM Manager V9.0 (Production Grade)
# Features: GMS Force Injection | Smart Region Parsing | Robust Proxy Safety | Auto-Save Guard

if [ "$(id -u)" -ne 0 ]; then echo "❌ 错误：需 Root 权限"; exit 1; fi

# ================= 配置区 =================

BACKUP_ROOT="/sdcard/MultiApp_Farm"
PROFILE_ROOT="/sdcard/MultiApp_Farm/Profiles"
CONF_FILE="/data/local/tmp/multiapp_conf.txt"
GEN_SCRIPT="/data/local/tmp/gen.sh"

# Clash API 地址
API_URL="http://127.0.0.1:9090"
SECRET="" 

mkdir -p "$BACKUP_ROOT"
mkdir -p "$PROFILE_ROOT"

# 后端 API 地址 (通过 ADB Reverse 端口转发)
BACKEND_API_URL="http://127.0.0.1:5000"

# 设备ID (用于后端API调用，需要与电脑端配置一致)
# 可通过 getprop ro.serialno 获取，或手动指定
DEVICE_ID=""
if [ -z "$DEVICE_ID" ]; then
    DEVICE_ID=$(getprop ro.serialno 2>/dev/null | tr -d '\r\n ')
fi

# ================= 备用线路 API 函数 =================

# ================= 错误码定义 =================
# 服务端可根据这些退出码判断具体错误类型
#
# 0   = 成功
# 1   = 通用错误 / 参数错误
# 10  = 网络验证失败（所有线路）
# 11  = 代理切换失败
# 12  = 配置文件生成失败
# 20  = 备份文件不存在
# 21  = 备份解压失败
# 22  = 数据恢复失败
# 30  = APP 类型未知
# 31  = APP 未安装
# 40  = 权限/SELinux 错误

EXIT_SUCCESS=0
EXIT_PARAM_ERROR=1
EXIT_NETWORK_FAIL=10
EXIT_PROXY_SWITCH_FAIL=11
EXIT_CONFIG_GEN_FAIL=12
EXIT_BACKUP_NOT_FOUND=20
EXIT_BACKUP_EXTRACT_FAIL=21
EXIT_RESTORE_FAIL=22
EXIT_UNKNOWN_APP=30
EXIT_APP_NOT_INSTALLED=31
EXIT_PERMISSION_ERROR=40

# ================= 日志辅助函数 =================

log_step() {
    echo "📋 [步骤] $1"
}

log_info() {
    echo "ℹ️  [信息] $1"
}

log_success() {
    echo "✅ [成功] $1"
}

log_warning() {
    echo "⚠️  [警告] $1"
}

log_error() {
    echo "❌ [错误] $1"
}

log_fatal() {
    echo "🚨 [致命] $1"
}

# 输出结构化结果 (供服务端解析)
# 格式: ##RESULT##|status|code|message
output_result() {
    local status="$1"   # success / error
    local code="$2"     # 错误码
    local message="$3"  # 消息
    echo "##RESULT##|${status}|${code}|${message}"
}


# 从服务端获取可用的备用线路
# 参数: $1 = REGION (地区代码)
# 返回: 成功时设置 BACKUP_LINE_NAME 变量，失败返回 1
get_backup_line() {
    local region="$1"
    
    if [ -z "$DEVICE_ID" ] || [ -z "$region" ]; then
        echo "❌ [Backup Line] 参数缺失: device_id=$DEVICE_ID, region=$region"
        return 1
    fi
    
    echo "🔄 [Backup Line] 正在获取备用线路... (设备: $DEVICE_ID, 地区: $region)"
    
    # 调用后端API获取可用备用线路
    local response
    response=$(curl -s --connect-timeout 10 -m 15 \
        "${BACKEND_API_URL}/api/proxies/backup-lines/get-available?device_id=${DEVICE_ID}&region=${region}")
    
    if [ -z "$response" ]; then
        echo "❌ [Backup Line] API 请求失败或超时"
        return 1
    fi
    
    # 解析响应
    local success
    success=$(echo "$response" | grep -o '"success"[[:space:]]*:[[:space:]]*true' | head -1)
    
    if [ -z "$success" ]; then
        local error
        error=$(echo "$response" | grep -o '"error"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)
        echo "❌ [Backup Line] 获取失败: ${error:-未知错误}"
        return 1
    fi
    
    # 提取线路名称
    BACKUP_LINE_NAME=$(echo "$response" | grep -o '"line_name"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$BACKUP_LINE_NAME" ]; then
        echo "❌ [Backup Line] 无法解析线路名称"
        return 1
    fi
    
    echo "✅ [Backup Line] 获取成功: $BACKUP_LINE_NAME"
    return 0
}

# 更新线路占用状态
# 参数: $1 = LINE_NAME (线路名称)
#       $2 = STATUS (true=占用, false=释放)
#       $3 = REGION (地区代码)
# 返回: 成功返回 0，失败返回 1
update_line_occupancy() {
    local line_name="$1"
    local status="$2"
    local region="$3"
    
    if [ -z "$DEVICE_ID" ] || [ -z "$line_name" ] || [ -z "$status" ] || [ -z "$region" ]; then
        echo "❌ [Occupancy] 参数缺失"
        return 1
    fi
    
    local action="占用"
    [ "$status" = "false" ] && action="释放"
    
    echo "🔄 [Occupancy] 更新线路状态: $line_name -> $action"
    
    # 调用后端API更新占用状态
    local response
    response=$(curl -s --connect-timeout 10 -m 15 \
        -X POST \
        -H "Content-Type: application/json" \
        -d "{\"device_id\":\"${DEVICE_ID}\",\"line_name\":\"${line_name}\",\"status\":${status},\"region\":\"${region}\"}" \
        "${BACKEND_API_URL}/api/proxies/backup-lines/occupancy")
    
    if [ -z "$response" ]; then
        echo "❌ [Occupancy] API 请求失败或超时"
        return 1
    fi
    
    # 解析响应
    local success
    success=$(echo "$response" | grep -o '"success"[[:space:]]*:[[:space:]]*true' | head -1)
    
    if [ -z "$success" ]; then
        local error
        error=$(echo "$response" | grep -o '"error"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)
        echo "❌ [Occupancy] 更新失败: ${error:-未知错误}"
        return 1
    fi
    
    echo "✅ [Occupancy] 线路 $line_name ${action}成功"
    return 0
}

# ================= 映射函数 =================

get_package_name() {
    case "$1" in
        Vinted) echo "fr.vinted" ;;
        Carousell) echo "com.thecarousell.Carousell" ;;
        *) echo "fr.vinted" ;;
    esac
}

# get_proxy_group() {
#     case "$1" in
#         HK) echo "Select-HK-IP" ;; 
#         GB) echo "Select-UK-Exit" ;;
#         SG) echo "Select-SG-Exit" ;;
#         MY) echo "Select-MY-Exit" ;;
#         PH) echo "Select-PH-Exit" ;;
#         *) echo "Select-HK-IP" ;; 
#     esac
# }

# ================= 核心工具函数 =================

clean_network_stack() {
    settings delete global http_proxy
    settings delete global global_http_proxy_host
    settings delete global global_http_proxy_port
    cmd connectivity flush-dns >/dev/null 2>&1
}

deep_clean_system_traces() {
    log_step "执行深度环境清洗 (Deep Clean)"
    
    # 1. 缩略图阻断 (删除并占位)
    rm -rf /sdcard/DCIM/.thumbnails
    rm -rf /sdcard/Pictures/.thumbnails
    touch /sdcard/DCIM/.thumbnails
    touch /sdcard/Pictures/.thumbnails
    chmod 000 /sdcard/DCIM/.thumbnails
    chmod 000 /sdcard/Pictures/.thumbnails
    
    # 2. WebView & Cache 清洗
    PKGS=$(pm list packages -3 | cut -d: -f2)
    for P in $PKGS; do
        if [ -d "/data/data/$P/app_webview" ]; then rm -rf "/data/data/$P/app_webview"; fi
        if [ -d "/data/data/$P/cache" ]; then rm -rf "/data/data/$P/cache"; fi
        if [ -d "/data/data/$P/code_cache" ]; then rm -rf "/data/data/$P/code_cache"; fi
    done
    
    # 3. 剪贴板重置
    service call clipboard 2 s16 "" >/dev/null 2>&1
    
    # 4. 相册清空 & 媒体库刷新
    rm -f /sdcard/DCIM/Camera/*
    am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d "file:///sdcard/DCIM/Camera" >/dev/null 2>&1
    
    echo "✅ [Deep Clean] 环境痕迹已清除"
}

verify_network_environment() {
    EXPECTED_REGION="$1"
    # Ensure expected region is uppercase
    EXPECTED_REGION=$(echo "$EXPECTED_REGION" | tr '[:lower:]' '[:upper:]')
    
    echo "🔍 [Network] Verifying connectivity and region match... (Expect: $EXPECTED_REGION)"
    
    FOUND_REGION=""

    # 1. ipinfo.io (HTTPS)
    echo "   👉 Check 1: ipinfo.io"
    RESP=$(curl -s --connect-timeout 8 -m 12 "https://ipinfo.io/json")
    if [ ! -z "$RESP" ]; then
        CODE=$(echo "$RESP" | grep -o '"country"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)
        if [ -z "$CODE" ]; then CODE=$(echo "$RESP" | grep -o '"country":"[^"]*"' | cut -d'"' -f4); fi
        
        if [ "$CODE" = "$EXPECTED_REGION" ]; then
            echo "   ✅ Verified (ipinfo.io): $CODE"
            return 0
        elif [ ! -z "$CODE" ]; then
             echo "   ⚠️ Region Mismatch (ipinfo.io): Got $CODE, Want $EXPECTED_REGION"
        fi
    fi
    
    # 2. ipapi.co (HTTPS)
    echo "   👉 Check 2: ipapi.co"
    RESP=$(curl -s --connect-timeout 8 -m 12 "https://ipapi.co/json/")
    if [ ! -z "$RESP" ]; then
        CODE=$(echo "$RESP" | grep -o '"country_code"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)
        # Fallback regex if spacing varies
        if [ -z "$CODE" ]; then CODE=$(echo "$RESP" | grep -o '"country_code":"[^"]*"' | cut -d'"' -f4); fi
        
        if [ "$CODE" = "$EXPECTED_REGION" ]; then
            echo "   ✅ Verified (ipapi.co): $CODE"
            return 0
        elif [ ! -z "$CODE" ]; then
            echo "   ⚠️ Region Mismatch (ipapi.co): Got $CODE, Want $EXPECTED_REGION"
        fi
    fi

    # 3. ip-api.com (HTTP)
    echo "   👉 Check 3: ip-api.com"
    RESP=$(curl -s --connect-timeout 8 -m 12 "http://ip-api.com/json/")
    if [ ! -z "$RESP" ]; then
        CODE=$(echo "$RESP" | grep -o '"countryCode"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)
        if [ -z "$CODE" ]; then CODE=$(echo "$RESP" | grep -o '"countryCode":"[^"]*"' | cut -d'"' -f4); fi
        
        if [ "$CODE" = "$EXPECTED_REGION" ]; then
            echo "   ✅ Verified (ip-api.com): $CODE"
            return 0
        elif [ ! -z "$CODE" ]; then
             echo "   ⚠️ Region Mismatch (ip-api.com): Got $CODE, Want $EXPECTED_REGION"
        fi
    fi

 
    
    echo "❌ [Network] 网络验证失败!"
    echo "   可能原因: 代理下线, 地区不匹配, 或 API 被屏蔽。"
    return 1
}

# 内部函数：执行实际的代理切换（不含网络验证）
_do_switch_proxy() {
    local target_node="$1"
    local proxy_group="Proxy-IP"
    
    # Build API commands
    local cmd_group cmd_global
    if [ -z "$SECRET" ]; then
        cmd_group="curl -s -X PUT $API_URL/proxies/$proxy_group -H 'Content-Type: application/json' -d '{\"name\": \"$target_node\"}'"
        cmd_global="curl -s -X PUT $API_URL/proxies/GLOBAL -H 'Content-Type: application/json' -d '{\"name\": \"$target_node\"}'"
    else
        cmd_group="curl -s -X PUT $API_URL/proxies/$proxy_group -H 'Content-Type: application/json' -H 'Authorization: Bearer $SECRET' -d '{\"name\": \"$target_node\"}'"
        cmd_global="curl -s -X PUT $API_URL/proxies/GLOBAL -H 'Content-Type: application/json' -H 'Authorization: Bearer $SECRET' -d '{\"name\": \"$target_node\"}'"
    fi
    
    # Execute switch
    local response
    response=$(eval "$cmd_group")
    eval "$cmd_global" >/dev/null 2>&1
    
    # Check for API errors
    if echo "$response" | grep -qi "error\|not found\|invalid\|failed"; then
        echo "❌ [Clash API] 切换失败: $response"
        return 1
    fi
    
    # Verify switch
    sleep 1
    local now
    now=$(curl -s "$API_URL/proxies/$proxy_group" | grep -o '"now":"[^"]*"' | cut -d'"' -f4)
    if [ "$now" != "$target_node" ]; then
        sleep 2
        now=$(curl -s "$API_URL/proxies/$proxy_group" | grep -o '"now":"[^"]*"' | cut -d'"' -f4)
    fi
    
    if [ "$now" != "$target_node" ]; then
        echo "❌ [Clash] 代理切换验证失败! 期望: $target_node, 实际: $now"
        return 1
    fi
    
    echo "✅ [Clash] 代理已切换: $now"
    return 0
}

switch_proxy() { 
    TARGET_NODE="$1"
    REGION_CODE="$2"
    
    echo "🎯 [Switch] Target Node: $TARGET_NODE | Region: $REGION_CODE"
    
    # Strict validation
    if [ -z "$TARGET_NODE" ] || [ ${#TARGET_NODE} -le 2 ]; then
        echo "❌ [FATAL] Invalid node name: '$TARGET_NODE'"
        exit 1
    fi
    
    if [ -z "$REGION_CODE" ]; then
        echo "❌ [FATAL] Region code is empty"
        exit 1
    fi
    
    # 第一次尝试：使用原始节点
    echo "📡 [第1次尝试] 使用主线路: $TARGET_NODE"
    
    if ! _do_switch_proxy "$TARGET_NODE"; then
        echo "❌ [FATAL] Clash 代理切换失败，无法继续"
        exit 1
    fi
    
    # 网络环境验证
    if verify_network_environment "$REGION_CODE"; then
        echo "✅ [Network] 主线路验证通过"
        
        # 设置全局变量供调用者使用
        FINAL_NODE="$TARGET_NODE"
        
        # 更新配置文件
        if [ -f "$CONF_FILE" ]; then
            sed -i '/CurrentNode=/d' "$CONF_FILE"
            echo "CurrentNode=$TARGET_NODE" >> "$CONF_FILE"
            chmod 666 "$CONF_FILE"
            chcon u:object_r:app_data_file:s0 "$CONF_FILE"
        fi
        return 0
    fi
    
    # ========== 备用线路重试逻辑 ==========
    echo "⚠️ [Fallback] 主线路验证失败，尝试获取备用线路..."
    
    # 🔓 释放失败的主线路（让其他设备可以使用）
    echo "🔓 [Release] 释放失败的主线路: $TARGET_NODE"
    update_line_occupancy "$TARGET_NODE" "false" "$REGION_CODE"
    
    local max_retries=3
    local retry_count=0
    local used_backup_line=""
    
    while [ $retry_count -lt $max_retries ]; do
        retry_count=$((retry_count + 1))
        echo ""
        echo "🔄 [备用线路重试 $retry_count/$max_retries]"
        
        # 1. 获取备用线路
        if ! get_backup_line "$REGION_CODE"; then
            echo "❌ [重试 $retry_count] 无法获取备用线路"
            continue
        fi
        
        local backup_node="$BACKUP_LINE_NAME"
        echo "📡 [重试 $retry_count] 切换到备用线路: $backup_node"
        
        # 2. 切换到备用线路
        if ! _do_switch_proxy "$backup_node"; then
            echo "❌ [重试 $retry_count] 备用线路切换失败: $backup_node"
            continue
        fi
        
        # 3. 验证备用线路网络环境
        if verify_network_environment "$REGION_CODE"; then
            echo "✅ [重试 $retry_count] 备用线路验证通过: $backup_node"
            
            # 4. 更新占用状态（标记为占用）
            update_line_occupancy "$backup_node" "true" "$REGION_CODE"
            
            # 5. 设置全局变量供调用者使用（关键！）
            FINAL_NODE="$backup_node"
            
            if [ -f "$CONF_FILE" ]; then
                sed -i '/CurrentNode=/d' "$CONF_FILE"
                echo "CurrentNode=$backup_node" >> "$CONF_FILE"
                chmod 666 "$CONF_FILE"
                chcon u:object_r:app_data_file:s0 "$CONF_FILE"
            fi
            
            echo "✅ [Fallback] 已成功切换到备用线路: $backup_node"
            echo "📌 [FINAL_NODE] 全局变量已设置为: $FINAL_NODE"
            return 0
        else
            echo "❌ [重试 $retry_count] 备用线路验证失败: $backup_node"
            # 备用线路本就没有被占用，不需要释放
        fi
    done
    
    # 所有重试都失败
    echo ""
    echo "❌ [FATAL] 所有线路验证均失败 (已尝试 $max_retries 条备用线路)"
    echo "   主线路: $1"
    echo "   地区: $REGION_CODE"
    echo "   可能原因: 所有代理均下线或被封锁"
    echo "❌ Unsafe environment. Exiting."
    exit 1
}

sync_gps_from_ip() {
    echo "📍 同步 IP 地理位置..."
    JSON=$(curl -s --connect-timeout 5 "http://ip-api.com/json")
    LAT=$(echo "$JSON" | grep -o '"lat":[^,]*' | cut -d':' -f2)
    LON=$(echo "$JSON" | grep -o '"lon":[^,]*' | cut -d':' -f2)
    if [ ! -z "$LAT" ] && [ -f "$CONF_FILE" ]; then
        sed -i '/GPS_LAT/d' "$CONF_FILE"
        sed -i '/GPS_LON/d' "$CONF_FILE"
        echo "GPS_LAT=$LAT" >> "$CONF_FILE"
        echo "GPS_LON=$LON" >> "$CONF_FILE"
        chmod 666 "$CONF_FILE"
        chcon u:object_r:app_data_file:s0 "$CONF_FILE"
        echo "✅ GPS 已更新: $LAT, $LON"
    fi
}

# 🔥 CRITICAL: GMS Advertising ID Force Injection
# This function MUST be called after tar extraction in load()
force_inject_gms_ads_id() {
    if [ ! -f "$CONF_FILE" ]; then
        echo "⚠️ [GMS] Config file not found, skipping injection"
        return 1
    fi
    
    NEW_ADS_ID=$(grep "AdsId=" "$CONF_FILE" | cut -d= -f2 | tr -d '\r\n ')
    
    if [ -z "$NEW_ADS_ID" ]; then
        echo "⚠️ [GMS] AdsId not found in config"
        return 1
    fi
    
    echo "💉 [GMS] Force-injecting Ads ID: $NEW_ADS_ID"
    
    GMS_PKG="com.google.android.gms"
    GMS_DATA="/data/data/$GMS_PKG"
    S_PREFS="$GMS_DATA/shared_prefs"
    
    # Kill GMS completely
    killall com.google.android.gms 2>/dev/null
    am force-stop "$GMS_PKG" 2>/dev/null
    sleep 1
    
    # Remove all existing GMS ID files
    rm -f "$S_PREFS/adid_settings.xml"
    rm -f "$S_PREFS/app_set_id_storage.xml"
    rm -f "$S_PREFS/Checkin.xml"
    rm -f "$S_PREFS/device_id.xml"
    
    # Ensure directory exists with correct permissions
    if [ ! -d "$S_PREFS" ]; then 
        mkdir -p "$S_PREFS"
        chmod 771 "$S_PREFS"
        chown $(stat -c '%u:%g' "$GMS_DATA") "$S_PREFS"
    fi
    
    # Force-write the Ads ID XML
    XML_ADID="$S_PREFS/adid_settings.xml"
    echo "<?xml version='1.0' encoding='utf-8' standalone='yes' ?><map><string name=\"adid_key\">$NEW_ADS_ID</string><boolean name=\"enable_limit_ad_tracking\" value=\"false\" /></map>" > "$XML_ADID"
    
    # CRITICAL: Fix permissions for persistence
    chmod 660 "$XML_ADID"
    chown $(stat -c '%u:%g' "$GMS_DATA") "$XML_ADID"
    restorecon "$XML_ADID" >/dev/null 2>&1
    
    # Force-stop again to ensure reload
    am force-stop "$GMS_PKG" 2>/dev/null
    
    echo "✅ [GMS] Ads ID injection complete"
    return 0
}

spoof_ssaid() {
    if [ ! -f "$CONF_FILE" ]; then return 1; fi
    NEW=$(grep "AndroidID=" "$CONF_FILE" | cut -d= -f2 | tr -d '\r\n ')
    if [ ! -z "$NEW" ]; then 
        settings put secure android_id "$NEW"
        echo "✅ [SSAID] Android ID set: $NEW"
    fi
}

freeze_app() { PKG="$1"; am force-stop "$PKG"; }
unfreeze_app() { PKG="$1"; cmd package compile -m speed "$PKG" > /dev/null 2>&1; }

fix_strict() { 
    TARGET="$1"; T_UID="$2"
    if [ -d "$TARGET" ] && [ ! -z "$T_UID" ]; then 
        chown -R "$T_UID:$T_UID" "$TARGET"
        find "$TARGET" -type d -exec chmod 700 {} \;
        find "$TARGET" -type f -exec chmod 600 {} \;
        restorecon -R -F "$TARGET"
    fi 
}

kill_interfering_apps() {
    am force-stop com.android.settings
    am force-stop com.box.app 2>/dev/null
    am force-stop com.android.chrome 2>/dev/null
    am force-stop com.google.android.gsf.login 2>/dev/null
}

safe_remove_google_account() {
    pm clear com.google.android.gsf.login >/dev/null 2>&1
    pm clear com.android.vending >/dev/null 2>&1
}

launch_app() {
    PKG_NAME="$1"
    echo "🚀 [Load完成] 正在拉起应用: $PKG_NAME"
    monkey -p "$PKG_NAME" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        if [ "$PKG_NAME" = "com.thecarousell.Carousell" ]; then
            am start -n "com.thecarousell.Carousell/com.thecarousell.Carousell.activities.EntryActivity" >/dev/null 2>&1
        else
            am start -n "$PKG_NAME/.MainActivity" >/dev/null 2>&1
        fi
    fi
}

# --- 封装保存逻辑 (供 save 命令和 load 自动备份调用) ---
execute_save_logic() {
    SAVE_NAME="$1"
    # 从NAME解析APP_TYPE作为后备: AppType_Region_deviceId(remark)_number
    SAVE_NAME_PARSED_APP_TYPE=$(echo "$SAVE_NAME" | cut -d'_' -f1)
    SAVE_APP_TYPE=$(grep "AppType=" "$CONF_FILE" | head -1 | cut -d= -f2 | tr -d '\r\n ')
    [ -z "$SAVE_APP_TYPE" ] && SAVE_APP_TYPE="$SAVE_NAME_PARSED_APP_TYPE"
    
    if [ -z "$SAVE_APP_TYPE" ]; then
        echo "❌ 无法确定 APP_TYPE（Conf文件缺失且无法从名称解析）"
        return 1
    fi
    SAVE_PKG=$(get_package_name "$SAVE_APP_TYPE")
    
    echo "💾 正在备份账号: [$SAVE_NAME] (App: $SAVE_APP_TYPE)..."
    
    freeze_app "$SAVE_PKG"
    safe_remove_google_account
    
    # 确保当前节点信息被写入 Profile
    if [ -f "$CONF_FILE" ]; then
         CUR_NODE=$(grep "CurrentNode=" "$CONF_FILE" | head -1 | cut -d= -f2 | tr -d '\r\n ')
         SAVE_PROFILE="$PROFILE_ROOT/${SAVE_NAME}.conf"
         if [ ! -z "$CUR_NODE" ] && [ -f "$SAVE_PROFILE" ]; then
            sed -i '/CurrentNode=/d' "$SAVE_PROFILE"
            echo "CurrentNode=$CUR_NODE" >> "$SAVE_PROFILE"
         fi
         # 如果 Profile 不存在，从 Conf 复制
         if [ ! -f "$SAVE_PROFILE" ]; then cp "$CONF_FILE" "$SAVE_PROFILE"; fi
         
         # 📌 记录APP版本（用于Load时兼容性检测）
         APP_VERSION=$(dumpsys package $SAVE_PKG 2>/dev/null | grep "versionName=" | head -1 | sed 's/.*versionName=//' | tr -d ' ')
         if [ ! -z "$APP_VERSION" ]; then
             sed -i '/AppVersion=/d' "$SAVE_PROFILE"
             echo "AppVersion=$APP_VERSION" >> "$SAVE_PROFILE"
             echo "📌 [Save] APP版本: $APP_VERSION"
         fi
    fi
    
    cd /
    tar --exclude='cache' --exclude='code_cache' --exclude='lib' \
        -czf "$BACKUP_ROOT/${SAVE_NAME}.tar.gz" \
        "data/data/$SAVE_PKG" "data/user_de/0/$SAVE_PKG" "sdcard/Android/data/$SAVE_PKG" \
        "data/local/tmp/multiapp_conf.txt" 2>/dev/null
    
    echo "✅ 备份完成: $SAVE_NAME"
}


# ================= 主逻辑 =================

ACTION="$1"
NAME="$2"

if [ -z "$ACTION" ]; then echo "用法: $0 [new|load|save] [NAME]"; exit 1; fi

# === NEW (新号) ===
if [ "$ACTION" = "new" ]; then
    NAME="$2"
    APP_TYPE="$3"      
    RAW_ARG4="$4"
    RAW_ARG5="$5"
    
    # ✅ Validation: No hardcoded defaults - all params required
    if [ -z "$NAME" ]; then
        echo "❌ [ERROR] 账号名称不能为空"
        exit 1
    fi
    
    if [ -z "$APP_TYPE" ]; then
        echo "❌ [ERROR] APP类型不能为空 (例如: Vinted, Carousell, TT, IG)"
        exit 1
    fi
    
    # 🎯 Smart Region Parsing from Node Name
    # Fixes "UK SIM in HK" bug by auto-detecting region from node prefix
    if echo "$RAW_ARG4" | grep -qE "^[A-Z]{2}[_-][0-9a-zA-Z]+"; then
        NODE="$RAW_ARG4"
        # Extract region from node name (e.g., HK_01 -> HK, UK_London -> GB)
        if [ ${#RAW_ARG5} -eq 2 ]; then 
            REGION="$RAW_ARG5"
        else
            # Auto-detect from node prefix
            case "$NODE" in 
                HK*|HongKong*) REGION="HK" ;; 
                UK*|GB*|London*) REGION="GB" ;; 
                SG*|Singapore*) REGION="SG" ;; 
                MY*|Malaysia*) REGION="MY" ;;
                PH*|Manila*) REGION="PH" ;;
                US*|America*) REGION="US" ;;
                JP*|Japan*) REGION="JP" ;;
                TH*|Thailand*) REGION="TH" ;;
                VN*|Vietnam*) REGION="VN" ;;
                *) 
                    echo "⚠️ [WARNING] 无法从节点名称自动识别地区: $NODE"
                    echo "❌ [ERROR] 请明确指定地区代码 (例如: HK, GB, SG, MY, PH)"
                    exit 1
                    ;;
            esac
            echo "🎯 [Smart Parse] Node: $NODE -> Region: $REGION"
        fi
    else
        REGION="$RAW_ARG4"
        NODE="$RAW_ARG5"
    fi
    
    # ✅ Validation: Node and Region are required
    if [ -z "$REGION" ]; then
        echo "❌ [ERROR] 地区代码不能为空 (例如: HK, GB, SG, MY, PH)"
        exit 1
    fi
    
    if [ -z "$NODE" ]; then
        echo "❌ [ERROR] 代理节点不能为空 (例如: HK_061, UK_London)"
        exit 1
    fi

    PKG=$(get_package_name "$APP_TYPE")
    if [ -z "$PKG" ]; then
        echo "❌ [ERROR] 未知的APP类型: $APP_TYPE"
        exit 1
    fi
    
    DATA_INT="/data/data/$PKG"
    DATA_EXT="/sdcard/Android/data/$PKG"
    
    echo "🆕 初始化新账号 [$NAME] [$APP_TYPE | Region:$REGION | Node:$NODE]..."
    
    # 🔄 NEW FEATURE: Save current account before creating new one
    if [ -f "$CONF_FILE" ]; then
        CURRENT_ACCOUNT=$(cat "$CONF_FILE" 2>/dev/null | grep '^AccountName=' | head -n 1 | cut -d= -f2- | tr -d '\r\n ')
        
        if [ ! -z "$CURRENT_ACCOUNT" ]; then
            echo "💾 [Auto-Save] 检测到当前账号: $CURRENT_ACCOUNT"
            echo "💾 [Auto-Save] 开始保存当前账号缓存..."
            
            # Get APP_TYPE from current config
            CURRENT_APP_TYPE=$(cat "$CONF_FILE" 2>/dev/null | grep '^AppType=' | head -n 1 | cut -d= -f2- | tr -d '\r\n ')
            if [ -z "$CURRENT_APP_TYPE" ]; then
                CURRENT_APP_TYPE="$APP_TYPE"
            fi
            
            CURRENT_PKG=$(get_package_name "$CURRENT_APP_TYPE")
            
            if [ ! -z "$CURRENT_PKG" ]; then
                freeze_app "$CURRENT_PKG"
                
                BACKUP_PATH="$PROFILE_ROOT/${CURRENT_ACCOUNT}.tar.gz"
                echo "📦 [Auto-Save] 创建备份: $BACKUP_PATH"
                
                rm -f "$BACKUP_PATH"
                tar -czf "$BACKUP_PATH" \
                    -C /data/data "$CURRENT_PKG" \
                    -C /sdcard/Android/data "$CURRENT_PKG" \
                    2>/dev/null || echo "⚠️ [Auto-Save] 部分数据无法备份（可能正常）"
                
                if [ -f "$BACKUP_PATH" ]; then
                    chmod 666 "$BACKUP_PATH"
                    echo "✅ [Auto-Save] 当前账号已保存"
                else
                    echo "⚠️ [Auto-Save] 备份创建失败，继续执行..."
                fi
                
                unfreeze_app "$CURRENT_PKG"
            fi
        fi
    fi
    
    # 🧹 Clean target app cache and storage
    echo "🧹 [Clean] 清理目标APP环境: $PKG"
    freeze_app "$PKG"
    
    # ✅ pm clear 是安卓官方API，会清空数据但保留目录结构和SELinux上下文
    # ❌ 不要使用 rm -rf "$DATA_INT"，会破坏Inode和SELinux绑定导致闪退
    pm clear "$PKG" >/dev/null 2>&1
    
    # ✅ 外部存储可以删除
    rm -rf "$DATA_EXT"
    
    # Google账号清理
    safe_remove_google_account
    
    # 网络栈清理
    clean_network_stack
    deep_clean_system_traces
    
    # 切换代理
    log_step "切换网络代理: $NODE (地区: $REGION)"
    switch_proxy "$NODE" "$REGION"
    
    # 🔨 Generate fingerprint with CORRECT region (fixes SIM mismatch)
    log_step "生成设备指纹: $APP_TYPE | 地区: $REGION"
    sh "$GEN_SCRIPT" "$APP_TYPE" "$REGION"
    
    if [ ! -f "$CONF_FILE" ]; then
        log_fatal "指纹配置文件生成失败 (gen.sh 执行异常)"
        output_result "error" "$EXIT_CONFIG_GEN_FAIL" "指纹配置文件生成失败"
        exit $EXIT_CONFIG_GEN_FAIL
    fi
    
    # 写入配置
    # 使用 FINAL_NODE（switch_proxy 设置的全局变量，可能是备用线路）
    echo "AccountName=$NAME" >> "$CONF_FILE"
    echo "CurrentNode=$FINAL_NODE" >> "$CONF_FILE"
    echo "AppType=$APP_TYPE" >> "$CONF_FILE"
    
    log_info "配置写入完成: 账号=$NAME, 节点=$FINAL_NODE, 类型=$APP_TYPE"
    
    # 保存配置副本
    log_step "保存配置副本到 Profile 目录"
    cp "$CONF_FILE" "$PROFILE_ROOT/$NAME.conf"
    chmod 666 "$CONF_FILE" "$PROFILE_ROOT/$NAME.conf"
    chcon u:object_r:app_data_file:s0 "$CONF_FILE"
    
    # 注入 GMS IDs
    log_step "注入 GMS Ads ID 和 SSAID"
    force_inject_gms_ads_id
    spoof_ssaid
    
    # GPS 同步
    log_step "同步 GPS 位置信息"
    sync_gps_from_ip 
    
    # 修复权限
    log_step "修复应用权限和 SELinux 上下文"
    APP_UID=$(cmd package list packages -U | grep "$PKG" | awk -F: '{print $3}' | tr -d ' ')
    if [ ! -z "$APP_UID" ]; then 
        fix_strict "$DATA_INT" "$APP_UID"
    fi

    # 网络重置
    log_step "重置网络连接 (飞行模式刷新)"
    cmd connectivity airplane-mode enable
    sleep 1
    cmd connectivity airplane-mode disable
    sleep 3
    
    # 清理干扰应用
    log_step "清理干扰应用进程"
    kill_interfering_apps
    
    # 🌍 设置系统时区和语言 (Regional Consistency)
    if [ -f "$CONF_FILE" ]; then
        TZ=$(grep "Timezone=" "$CONF_FILE" | cut -d= -f2 | tr -d '\r\n ')
        LOC=$(grep "Locale=" "$CONF_FILE" | cut -d= -f2 | tr -d '\r\n ')
        
        if [ ! -z "$TZ" ]; then 
            setprop persist.sys.timezone "$TZ"
            log_step "设置时区: $TZ"
        fi
        
        if [ ! -z "$LOC" ]; then
            setprop persist.sys.locale "$LOC"
            setprop persist.sys.language "en"
            # Extract country from locale (e.g., en_GB -> GB)
            CTY=$(echo "$LOC" | cut -d_ -f2)
            setprop persist.sys.country "$CTY"
            log_step "设置语言区域: $LOC (Country: $CTY)"
        fi
    fi
    
    # 解冻应用
    log_step "解冻目标应用: $PKG"
    unfreeze_app "$PKG"
    
    # 输出成功结果
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    log_success "新账号创建成功: $NAME"
    echo "═══════════════════════════════════════════════════════════════"
    log_info "账号名称: $NAME"
    log_info "应用类型: $APP_TYPE"
    log_info "目标地区: $REGION"
    log_info "代理节点: $FINAL_NODE"
    log_info "包名: $PKG"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    
    output_result "success" "$EXIT_SUCCESS" "账号 $NAME 创建成功"
    exit $EXIT_SUCCESS
fi


# === LOAD (加载) ===
if [ "$ACTION" = "load" ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    log_step "开始加载账号: $NAME"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    
    if [ -z "$NAME" ]; then
        log_error "账号名称不能为空"
        output_result "error" "$EXIT_PARAM_ERROR" "账号名称不能为空"
        exit $EXIT_PARAM_ERROR
    fi
    
    ARCHIVE="$BACKUP_ROOT/${NAME}.tar.gz"
    PROFILE="$PROFILE_ROOT/${NAME}.conf"
    
    log_info "备份文件: $ARCHIVE"
    log_info "配置文件: $PROFILE"
    
    if [ ! -f "$ARCHIVE" ]; then
        log_fatal "备份文件不存在: $ARCHIVE"
        output_result "error" "$EXIT_BACKUP_NOT_FOUND" "备份文件不存在"
        exit $EXIT_BACKUP_NOT_FOUND
    fi

    # --- 🛡️ 自动防丢检查 (Auto-Save Guard) ---
    if [ -f "$CONF_FILE" ]; then
        CURRENT_NAME=$(grep "AccountName=" "$CONF_FILE" | cut -d= -f2 | tr -d '\r\n ')
        if [ ! -z "$CURRENT_NAME" ] && [ "$CURRENT_NAME" != "$NAME" ]; then
            log_warning "检测到当前活跃环境: [$CURRENT_NAME]"
            log_step "自动保存当前账号以防止数据丢失..."
            execute_save_logic "$CURRENT_NAME"
        fi
    fi
    # ----------------------------------------
    
    # 从NAME解析APP_TYPE和REGION作为后备方案
    # Name格式: AppType_Region_deviceId(remark)_number, 例如: Vinted_GB_72e8932c(HK2)_001
    NAME_PARSED_APP_TYPE=$(echo "$NAME" | cut -d'_' -f1)
    NAME_PARSED_REGION=$(echo "$NAME" | cut -d'_' -f2)
    
    if [ -f "$PROFILE" ]; then
        APP_TYPE=$(grep "AppType=" "$PROFILE" | head -1 | cut -d= -f2 | tr -d '\r\n ')
        REGION=$(grep "Region=" "$PROFILE" | head -1 | cut -d= -f2 | tr -d '\r\n ')
        SAVED_NODE=$(grep "CurrentNode=" "$PROFILE" | head -1 | cut -d= -f2 | tr -d '\r\n ')
        BACKUP_VERSION=$(grep "AppVersion=" "$PROFILE" | head -1 | cut -d= -f2 | tr -d '\r\n ')
    fi
    
    # 如果profile中没有APP_TYPE，则从NAME解析
    [ -z "$APP_TYPE" ] && APP_TYPE="$NAME_PARSED_APP_TYPE"
    [ -z "$REGION" ] && REGION="$NAME_PARSED_REGION"
    
    # 验证必要参数
    if [ -z "$APP_TYPE" ]; then
        echo "❌ 无法确定 APP_TYPE（profile缺失且无法从账号名称解析）"
        exit 1
    fi
    if [ -z "$SAVED_NODE" ]; then
        echo "⚠️ 未找到保存的代理节点，将使用默认代理"
    fi
    
    log_info "APP类型: $APP_TYPE, 地区: $REGION"
    PKG=$(get_package_name "$APP_TYPE")
    if [ -z "$PKG" ]; then
        log_fatal "未知的APP类型: $APP_TYPE"
        output_result "error" "$EXIT_UNKNOWN_APP" "未知的APP类型: $APP_TYPE"
        exit $EXIT_UNKNOWN_APP
    fi
    log_info "目标应用包名: $PKG"
    DATA_INT="/data/data/$PKG"
    DATA_DE="/data/user_de/0/$PKG"
    DATA_EXT="/sdcard/Android/data/$PKG"
    APP_UID=$(cmd package list packages -U | grep "$PKG" | awk -F: '{print $3}' | tr -d ' ')
    
    # 📌 版本兼容性检测
    CURRENT_VERSION=$(dumpsys package $PKG 2>/dev/null | grep "versionName=" | head -1 | sed 's/.*versionName=//' | tr -d ' ')
    if [ ! -z "$BACKUP_VERSION" ] && [ ! -z "$CURRENT_VERSION" ]; then
        if [ "$BACKUP_VERSION" != "$CURRENT_VERSION" ]; then
            echo "⚠️ [VERSION] 检测到APP版本变化！"
            echo "   备份版本: $BACKUP_VERSION"
            echo "   当前版本: $CURRENT_VERSION"
            echo "   ⚠️ 可能存在数据兼容性问题，继续执行..."
        else
            echo "✅ [VERSION] 版本一致: $CURRENT_VERSION"
        fi
    fi
    
    log_step "开始还原账号: $NAME (节点: $SAVED_NODE)"
    
    log_step "冻结目标应用: $PKG"
    freeze_app "$PKG"
    
    # 🔒 安全清理（修正版方案A）
    # ✅ 保留 lib 目录（因为备份中排除了lib，删除会导致闪退）
    # ✅ 清空其他所有数据（避免账号污染）
    if [ -d "$DATA_INT" ]; then
        find "$DATA_INT" -mindepth 1 -maxdepth 1 ! -name 'lib' -exec rm -rf {} + 2>/dev/null
    fi
    
    # ✅ 完全删除 DATA_DE（tar会重建，restorecon会修复SELinux）
    rm -rf "$DATA_DE"
    
    # ✅ 完全删除外部存储
    rm -rf "$DATA_EXT"
    
    safe_remove_google_account
    
    # Extract backup
    log_step "解压备份文件..."
    tar -xzf "$ARCHIVE" -C /
    
    if [ $? -ne 0 ]; then
        log_fatal "备份文件解压失败"
        output_result "error" "$EXIT_BACKUP_EXTRACT_FAIL" "备份文件解压失败"
        exit $EXIT_BACKUP_EXTRACT_FAIL
    fi
    log_success "备份解压完成"
    
    # 🔒 关键：修复所有权限和SELinux上下文
    log_step "修复权限和 SELinux 上下文..."
    fix_strict "$DATA_INT" "$APP_UID"
    fix_strict "$DATA_DE" "$APP_UID"
    
    # Restore profile config
    if [ -f "$PROFILE" ]; then 
        cp "$PROFILE" "$CONF_FILE"
        chmod 666 "$CONF_FILE"
        chcon u:object_r:app_data_file:s0 "$CONF_FILE"
    fi
    
    # Network setup
    log_step "清理网络状态"
    clean_network_stack
    deep_clean_system_traces
    log_step "切换代理节点: $SAVED_NODE (地区: $REGION)"
    switch_proxy "$SAVED_NODE" "$REGION"
    
    # 如果使用了备用线路，更新配置中的 CurrentNode
    if [ ! -z "$FINAL_NODE" ] && [ "$FINAL_NODE" != "$SAVED_NODE" ]; then
        echo "📌 [Load] 使用了备用线路: $FINAL_NODE (原始: $SAVED_NODE)"
        sed -i '/CurrentNode=/d' "$CONF_FILE"
        echo "CurrentNode=$FINAL_NODE" >> "$CONF_FILE"
        # 同步更新 Profile
        if [ -f "$PROFILE" ]; then
            sed -i '/CurrentNode=/d' "$PROFILE"
            echo "CurrentNode=$FINAL_NODE" >> "$PROFILE"
        fi
    fi
    
    sync_gps_from_ip
    
    # Fix permissions
    fix_strict "$DATA_INT" "$APP_UID"
    fix_strict "$DATA_DE" "$APP_UID"
    if [ -d "$DATA_EXT" ]; then 
        chown -R media_rw:media_rw "$DATA_EXT"
        restorecon -R "$DATA_EXT" 2>/dev/null
    fi
    
    # 🔥 CRITICAL: Force-inject GMS Ads ID after restore
    # This ensures the Ads ID from config overwrites any restored GMS data
    force_inject_gms_ads_id
    spoof_ssaid
    
    echo "✈️ 刷新网络..."
    sync
    cmd connectivity airplane-mode enable; sleep 1; cmd connectivity airplane-mode disable; sleep 4
    
    log_step "清理干扰应用进程"
    kill_interfering_apps
    
    # 🌍 设置系统时区和语言 (Regional Consistency)
    if [ -f "$CONF_FILE" ]; then
        TZ=$(grep "Timezone=" "$CONF_FILE" | cut -d= -f2 | tr -d '\r\n ')
        LOC=$(grep "Locale=" "$CONF_FILE" | cut -d= -f2 | tr -d '\r\n ')
        
        if [ ! -z "$TZ" ]; then 
            setprop persist.sys.timezone "$TZ"
            log_step "设置时区: $TZ"
        fi
        
        if [ ! -z "$LOC" ]; then
            setprop persist.sys.locale "$LOC"
            setprop persist.sys.language "en"
            # Extract country from locale (e.g., en_GB -> GB)
            CTY=$(echo "$LOC" | cut -d_ -f2)
            setprop persist.sys.country "$CTY"
            log_step "设置语言区域: $LOC (Country: $CTY)"
        fi
    fi
    
    log_step "解冻应用: $PKG"
    unfreeze_app "$PKG"
    
    # 仅 Load 模式自动拉起
    log_step "启动应用"
    launch_app "$PKG"
    
    # 输出成功结果
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    log_success "账号加载成功: $NAME"
    echo "═══════════════════════════════════════════════════════════════"
    log_info "账号名称: $NAME"
    log_info "应用类型: $APP_TYPE"
    log_info "目标地区: $REGION"
    log_info "代理节点: ${FINAL_NODE:-$SAVED_NODE}"
    log_info "包名: $PKG"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    
    output_result "success" "$EXIT_SUCCESS" "账号 $NAME 加载成功"
    exit $EXIT_SUCCESS
fi

# === SAVE (保存) ===
if [ "$ACTION" = "save" ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    log_step "开始保存账号: $NAME"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    
    if [ -z "$NAME" ]; then
        log_error "账号名称不能为空"
        output_result "error" "$EXIT_PARAM_ERROR" "账号名称不能为空"
        exit $EXIT_PARAM_ERROR
    fi
    
    log_info "账号名称: $NAME"
    
    # 直接调用封装好的保存逻辑
    execute_save_logic "$NAME"
    SAVE_RESULT=$?
    
    # 如果是手动保存，解冻 APP 方便继续使用
    APP_TYPE=$(grep "AppType=" "$CONF_FILE" | cut -d= -f2 | tr -d '\r\n ')
    [ -z "$APP_TYPE" ] && APP_TYPE="Vinted"
    PKG=$(get_package_name "$APP_TYPE")
    
    log_step "解冻应用: $PKG"
    unfreeze_app "$PKG"
    
    # 输出保存结果
    if [ $SAVE_RESULT -eq 0 ]; then
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        log_success "账号保存成功: $NAME"
        echo "═══════════════════════════════════════════════════════════════"
        log_info "账号名称: $NAME"
        log_info "应用类型: $APP_TYPE"
        log_info "备份文件: $PROFILE_ROOT/${NAME}.tar.gz"
        echo "═══════════════════════════════════════════════════════════════"
        echo ""
        
        output_result "success" "$EXIT_SUCCESS" "账号 $NAME 保存成功"
        exit $EXIT_SUCCESS
    else
        log_fatal "账号保存失败"
        output_result "error" "$EXIT_RESTORE_FAIL" "账号保存失败"
        exit $EXIT_RESTORE_FAIL
    fi
fi