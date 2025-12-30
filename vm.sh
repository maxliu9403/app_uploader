#!/system/bin/sh
# Multi-App VM Manager V8.0 (Vinted/Carousell + Multi-Region)

if [ "$(id -u)" -ne 0 ]; then echo "❌ 错误：需 Root 权限"; exit 1; fi

# ================= 配置区 =================

BACKUP_ROOT="/sdcard/MultiApp_Farm"
PROFILE_ROOT="/sdcard/MultiApp_Farm/Profiles"
CONF_FILE="/data/local/tmp/multiapp_conf.txt"
GEN_SCRIPT="/data/local/tmp/gen.sh"

API_URL="http://127.0.0.1:9090"
SECRET=""

mkdir -p "$BACKUP_ROOT"
mkdir -p "$PROFILE_ROOT"

# App-specific package mapping
get_package_name() {
    case "$1" in
        Vinted) echo "fr.vinted" ;;
        Carousell) echo "com.thecarousell.Carousell" ;;
        *) echo "fr.vinted" ;;
    esac
}

# Region-to-ProxyGroup mapping
get_proxy_group() {
    case "$1" in
        GB) echo "Select-UK-Exit" ;;
        SG) echo "Select-SG-Exit" ;;
        MY) echo "Select-MY-Exit" ;;
        PH) echo "Select-PH-Exit" ;;
        *) echo "Select-UK-Exit" ;;
    esac
}

# ================= 核心工具函数 =================

clean_network_stack() {
    settings delete global http_proxy
    settings delete global global_http_proxy_host
    settings delete global global_http_proxy_port
    cmd connectivity flush-dns >/dev/null 2>&1
}

switch_proxy() { 
    TARGET_NODE="$1"
    PROXY_GROUP="$2"  # Dynamic proxy group based on region
    [ -z "$TARGET_NODE" ] && return
    [ -z "$PROXY_GROUP" ] && PROXY_GROUP="Select-UK-Exit"
    
    curl -s -X PUT "$API_URL/proxies/$PROXY_GROUP" \
         -H "Content-Type: application/json" \
         -H "Authorization: Bearer $SECRET" \
         -d "{\"name\": \"$TARGET_NODE\"}" > /dev/null 2>&1

    if [ -f "$CONF_FILE" ]; then
        sed -i '/CurrentNode=/d' "$CONF_FILE"
        echo "CurrentNode=$TARGET_NODE" >> "$CONF_FILE"
        chmod 666 "$CONF_FILE"
    fi
}

sync_gps_from_ip() {
    JSON=$(curl -s --connect-timeout 3 "http://ip-api.com/json")
    LAT=$(echo "$JSON" | grep -o '"lat":[^,]*' | cut -d':' -f2)
    LON=$(echo "$JSON" | grep -o '"lon":[^,]*' | cut -d':' -f2)
    if [ ! -z "$LAT" ] && [ -f "$CONF_FILE" ]; then
        sed -i '/GPS_/d' "$CONF_FILE"
        echo "GPS_LAT=$LAT" >> "$CONF_FILE"
        echo "GPS_LON=$LON" >> "$CONF_FILE"
        chmod 666 "$CONF_FILE"
    fi
}

# [外科手术式清理 GMS]
# 既切断关联，又保留大部分缓存以维持三绿
spoof_system_gms_ids() {
    if [ -f "$CONF_FILE" ]; then
        NEW_ID=$(grep "AdsId=" "$CONF_FILE" | cut -d= -f2 | tr -d '\r\n ')
        
        if [ ! -z "$NEW_ID" ]; then
            echo "⚡ [GMS] 执行外科手术式清理..."
            
            GMS_PKG="com.google.android.gms"
            GMS_DATA="/data/data/$GMS_PKG"
            S_PREFS="$GMS_DATA/shared_prefs"
            
            # 1. 强杀 GMS
            killall com.google.android.gms 2>/dev/null
            am force-stop "$GMS_PKG"
            sleep 0.5
            
            # --- 手术 A: 替换 Advertising ID (保持不变) ---
            XML_ADID="$S_PREFS/adid_settings.xml"
            if [ -f "$XML_ADID" ]; then chattr -i "$XML_ADID" 2>/dev/null; fi
            rm -f "$XML_ADID"
            
            # --- 手术 B: 删除 App Set ID (ASID) ---
            # Vinted 会读取这个ID，如果不删，光换广告ID没用
            rm -f "$S_PREFS/app_set_id_storage.xml"
            
            # --- 手术 C: 删除 GMS Checkin/Instance ID ---
            # 这是谷歌识别设备的身份证，删除它会强制 GMS 重新注册，切断与上一个谷歌账号的关联
            rm -f "$S_PREFS/Checkin.xml"
            rm -f "$S_PREFS/device_id.xml"
            
            # --- 重建目录结构 ---
            if [ ! -d "$S_PREFS" ]; then
                mkdir -p "$S_PREFS"
                chmod 771 "$S_PREFS"
                chown $(stat -c '%u:%g' "$GMS_DATA") "$S_PREFS"
            fi
            
            # 写入新的广告 ID
            echo "<?xml version='1.0' encoding='utf-8' standalone='yes' ?><map><string name=\"adid_key\">$NEW_ID</string><boolean name=\"enable_limit_ad_tracking\" value=\"false\" /></map>" > "$XML_ADID"
            
            # 修复权限
            chmod 660 "$XML_ADID"
            chown $(stat -c '%u:%g' "$GMS_DATA") "$XML_ADID"
            restorecon "$XML_ADID" >/dev/null 2>&1
            
            # 再次强杀
            am force-stop "$GMS_PKG"
            echo "✅ GMS 身份重置完成 (ASID/GAID/Checkin)"
        fi
    fi
}

spoof_ssaid() {
    NEW=$(grep "AndroidID=" "$CONF_FILE" | cut -d= -f2 | tr -d '\r\n ')
    if [ ! -z "$NEW" ]; then settings put secure android_id "$NEW"; fi
}

freeze_app() { 
    PKG="$1"
    am force-stop "$PKG"
}

unfreeze_app() { 
    PKG="$1"
    cmd package compile -m speed "$PKG" > /dev/null 2>&1
}

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
    am force-stop com.android.launcher3 2>/dev/null
    am force-stop com.google.android.gsf.login 2>/dev/null
}

# 安全移除 Google 账号
safe_remove_google_account() {
    echo "🧹 [Login&Drop] 移除 Google 账号..."
    pm clear com.google.android.gsf.login >/dev/null 2>&1
    pm clear com.android.vending >/dev/null 2>&1
}

# ================= 主逻辑 =================

ACTION="$1"
NAME="$2"

if [ -z "$ACTION" ]; then echo "用法: $0 [new|load|save] [NAME]"; exit 1; fi

# === NEW (新号) ===
if [ "$ACTION" = "new" ]; then
    APP_TYPE="$3"      # Vinted or Carousell
    REGION="$4"        # GB, SG, MY, PH
    NODE="$5"          # Proxy node name
    
    [ -z "$APP_TYPE" ] && APP_TYPE="Vinted"
    [ -z "$REGION" ] && REGION="GB"
    [ -z "$NODE" ] && NODE="UK-01"
    
    PKG=$(get_package_name "$APP_TYPE")
    PROXY_GROUP=$(get_proxy_group "$REGION")
    
    DATA_INT="/data/data/$PKG"
    DATA_DE="/data/user_de/0/$PKG"
    DATA_EXT="/sdcard/Android/data/$PKG"
    DATA_MED="/sdcard/Android/media/$PKG"
    
    echo "🆕 初始化 [$APP_TYPE | $REGION]..."
    freeze_app "$PKG"
    pm clear "$PKG" >/dev/null 2>&1
    rm -rf "$DATA_EXT" "$DATA_MED"
    pm clear com.google.android.webview >/dev/null 2>&1
    
    safe_remove_google_account
    
    clean_network_stack
    switch_proxy "$NODE" "$PROXY_GROUP"
    
    echo "🔨 指纹生成..."
    sh "$GEN_SCRIPT" "$APP_TYPE" "$REGION" "$NAME"
    chmod 666 "$CONF_FILE"
    
    # Save profile config (gen.sh already wrote AccountName)
    PROFILE="$PROFILE_ROOT/$NAME.conf"
    cp "$CONF_FILE" "$PROFILE"
    
    # Add metadata to both active config and profile
    echo "AppType=$APP_TYPE" >> "$CONF_FILE"
    echo "Region=$REGION" >> "$CONF_FILE"
    
    echo "AppType=$APP_TYPE" >> "$PROFILE"
    echo "Region=$REGION" >> "$PROFILE"
    
    chmod 666 "$CONF_FILE"
    chmod 666 "$PROFILE"
    
    # 执行深度清理
    spoof_system_gms_ids
    spoof_ssaid
    sync_gps_from_ip 
    
    APP_UID=$(cmd package list packages -U | grep "$PKG" | awk -F: '{print $3}' | tr -d ' ')
    if [ ! -z "$APP_UID" ]; then fix_strict "$DATA_INT" "$APP_UID"; fi

    echo "✈️ 网络重置..."
    cmd connectivity airplane-mode enable; sleep 1; cmd connectivity airplane-mode disable; sleep 3
    
    kill_interfering_apps
    unfreeze_app "$PKG"
	
	echo "⏳ 等待 GMS 预热 (5s)..."
    sleep 5
    
    echo "🚀 启动 $APP_TYPE (请手动登录 Google)..."
    am start -n "$PKG/.MainActivity" >/dev/null 2>&1
fi

# === LOAD (加载) ===
if [ "$ACTION" = "load" ]; then
    [ -z "$NAME" ] && exit 1
    ARCHIVE="$BACKUP_ROOT/${NAME}.tar.gz"
    PROFILE="$PROFILE_ROOT/${NAME}.conf"
    if [ ! -f "$ARCHIVE" ]; then echo "❌ 无备份"; exit 1; fi
    
    # Read AppType from profile to determine package
    if [ -f "$PROFILE" ]; then
        APP_TYPE=$(grep "AppType=" "$PROFILE" | cut -d= -f2 | tr -d '\r\n ')
        REGION=$(grep "Region=" "$PROFILE" | cut -d= -f2 | tr -d '\r\n ')
    fi
    [ -z "$APP_TYPE" ] && APP_TYPE="Vinted"
    [ -z "$REGION" ] && REGION="GB"
    
    PKG=$(get_package_name "$APP_TYPE")
    PROXY_GROUP=$(get_proxy_group "$REGION")
    
    DATA_INT="/data/data/$PKG"
    DATA_DE="/data/user_de/0/$PKG"
    DATA_EXT="/sdcard/Android/data/$PKG"
    DATA_MED="/sdcard/Android/media/$PKG"
    
    APP_UID=$(cmd package list packages -U | grep "$PKG" | awk -F: '{print $3}' | tr -d ' ')
    
    echo "♻️ 还原 [$NAME | $APP_TYPE | $REGION]..."
    freeze_app "$PKG"
    find "$DATA_INT" -mindepth 1 -maxdepth 1 ! -name 'lib' -exec rm -rf {} +
    rm -rf "$DATA_DE" "$DATA_EXT" "$DATA_MED"
    
    safe_remove_google_account
    
    tar -xzf "$ARCHIVE" -C /
    
    if [ -f "$PROFILE" ]; then 
        cp "$PROFILE" "$CONF_FILE"
        chmod 666 "$CONF_FILE"
        restorecon "$CONF_FILE"
        # Ensure metadata is in active config
        if ! grep -q "AccountName=" "$CONF_FILE"; then
            echo "AccountName=$NAME" >> "$CONF_FILE"
        fi
        if ! grep -q "AppType=" "$CONF_FILE"; then
            echo "AppType=$APP_TYPE" >> "$CONF_FILE"
        fi
        if ! grep -q "Region=" "$CONF_FILE"; then
            echo "Region=$REGION" >> "$CONF_FILE"
        fi
    else 
        if [ ! -f "$CONF_FILE" ]; then 
            echo "❌ 指纹丢失"
            exit 1
        fi
    fi
    
    if [ -f "$CONF_FILE" ]; then SAVED_NODE=$(grep "CurrentNode=" "$CONF_FILE" | cut -d= -f2 | tr -d '\r\n '); fi
    [ -z "$SAVED_NODE" ] && SAVED_NODE="UK-01"
    
    clean_network_stack
    switch_proxy "$SAVED_NODE" "$PROXY_GROUP"
    sync_gps_from_ip
    
    echo "🔧 修复权限..."
    fix_strict "$DATA_INT" "$APP_UID"
    fix_strict "$DATA_DE" "$APP_UID"
    if [ -d "$DATA_EXT" ]; then chown -R media_rw:media_rw "$DATA_EXT"; fi
    
    # 恢复时也要确保 GMS ID 是匹配的
    spoof_system_gms_ids
    spoof_ssaid
    
    echo "✈️ 刷新..."
    sync
    cmd connectivity airplane-mode enable; sleep 1; cmd connectivity airplane-mode disable; sleep 4
    
    kill_interfering_apps
    unfreeze_app "$PKG"
    echo "🚀 加载完成 ($SAVED_NODE)"
    am start -n "$PKG/.MainActivity" >/dev/null 2>&1
fi

# === SAVE (保存) ===
if [ "$ACTION" = "save" ]; then
    [ -z "$NAME" ] && exit 1
    
    # Determine package from profile
    PROFILE="$PROFILE_ROOT/${NAME}.conf"
    if [ -f "$PROFILE" ]; then
        APP_TYPE=$(grep "AppType=" "$PROFILE" | cut -d= -f2 | tr -d '\r\n ')
    fi
    [ -z "$APP_TYPE" ] && APP_TYPE="Vinted"
    PKG=$(get_package_name "$APP_TYPE")
    
    echo "💾 打包 [$NAME]..."
    freeze_app "$PKG"
    sleep 1
    
    # 保存前移除账号
    safe_remove_google_account
    
    chmod 644 "$CONF_FILE" 2>/dev/null
    
    if [ ! -f "$PROFILE_ROOT/${NAME}.conf" ] && [ -f "$CONF_FILE" ]; then
        cp "$CONF_FILE" "$PROFILE_ROOT/${NAME}.conf"
    fi
    
    cd /
    tar --exclude='cache' --exclude='code_cache' --exclude='lib' \
        -czf "$BACKUP_ROOT/${NAME}.tar.gz" \
        "data/data/$PKG" \
        "data/user_de/0/$PKG" \
        "sdcard/Android/data/$PKG" \
        "sdcard/Android/media/$PKG" \
        "data/local/tmp/multiapp_conf.txt" 2>/dev/null
    unfreeze_app "$PKG"
    echo "✅ 保存成功"
fi