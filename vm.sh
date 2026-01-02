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

# ================= 映射函数 =================

get_package_name() {
    case "$1" in
        Vinted) echo "fr.vinted" ;;
        Carousell) echo "com.thecarousell.Carousell" ;;
        *) echo "fr.vinted" ;;
    esac
}

get_proxy_group() {
    case "$1" in
        HK) echo "Select-HK-IP" ;; 
        GB) echo "Select-UK-Exit" ;;
        SG) echo "Select-SG-Exit" ;;
        MY) echo "Select-MY-Exit" ;;
        PH) echo "Select-PH-Exit" ;;
        *) echo "Select-HK-IP" ;; 
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
    REGION_CODE="$2"
    
    # Strict validation
    if [ -z "$TARGET_NODE" ] || [ ${#TARGET_NODE} -le 2 ]; then
        echo "❌ [FATAL] Invalid node name: '$TARGET_NODE'"
        exit 1
    fi
    
    if [ -z "$REGION_CODE" ]; then
        echo "❌ [FATAL] Region code is empty"
        exit 1
    fi

    PROXY_GROUP=$(get_proxy_group "$REGION_CODE")
    
    echo "🌐 [Clash] Switching to node: $TARGET_NODE (Group: $PROXY_GROUP)"
    
    # Build API commands
    if [ -z "$SECRET" ]; then
        CMD_GROUP="curl -s -X PUT $API_URL/proxies/$PROXY_GROUP -H 'Content-Type: application/json' -d '{\"name\": \"$TARGET_NODE\"}'"
        CMD_GLOBAL="curl -s -X PUT $API_URL/proxies/GLOBAL -H 'Content-Type: application/json' -d '{\"name\": \"$TARGET_NODE\"}'"
    else
        CMD_GROUP="curl -s -X PUT $API_URL/proxies/$PROXY_GROUP -H 'Content-Type: application/json' -H 'Authorization: Bearer $SECRET' -d '{\"name\": \"$TARGET_NODE\"}'"
        CMD_GLOBAL="curl -s -X PUT $API_URL/proxies/GLOBAL -H 'Content-Type: application/json' -H 'Authorization: Bearer $SECRET' -d '{\"name\": \"$TARGET_NODE\"}'"
    fi
    
    # Execute switch
    RESPONSE=$(eval "$CMD_GROUP")
    eval "$CMD_GLOBAL" >/dev/null 2>&1

    # CRITICAL: Check for API errors
    if echo "$RESPONSE" | grep -qi "error\|not found\|invalid\|failed"; then
        echo "❌ [FATAL] Clash API error: $RESPONSE"
        echo "❌ Cannot proceed with unsafe network. Exiting."
        exit 1
    fi

    # Verify switch with retry
    sleep 1
    NOW=$(curl -s "$API_URL/proxies/$PROXY_GROUP" | grep -o '"now":"[^"]*"' | cut -d'"' -f4)
    if [ "$NOW" != "$TARGET_NODE" ]; then
        sleep 2
        NOW=$(curl -s "$API_URL/proxies/$PROXY_GROUP" | grep -o '"now":"[^"]*"' | cut -d'"' -f4)
    fi
    
    # CRITICAL: Final verification
    if [ "$NOW" != "$TARGET_NODE" ]; then
        echo "❌ [FATAL] Proxy switch verification failed!"
        echo "   Expected: $TARGET_NODE"
        echo "   Got: $NOW"
        echo "❌ Unsafe to launch app. Exiting."
        exit 1
    fi
    
    echo "✅ Proxy verified: $NOW (GLOBAL synced)"

    # Update config file
    if [ -f "$CONF_FILE" ]; then
        sed -i '/CurrentNode=/d' "$CONF_FILE"
        echo "CurrentNode=$TARGET_NODE" >> "$CONF_FILE"
        chmod 666 "$CONF_FILE"
    fi
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
    SAVE_APP_TYPE=$(grep "AppType=" "$CONF_FILE" | cut -d= -f2 | tr -d '\r\n ')
    [ -z "$SAVE_APP_TYPE" ] && SAVE_APP_TYPE="Vinted"
    SAVE_PKG=$(get_package_name "$SAVE_APP_TYPE")
    
    echo "💾 正在备份账号: [$SAVE_NAME] (App: $SAVE_APP_TYPE)..."
    
    freeze_app "$SAVE_PKG"
    safe_remove_google_account
    
    # 确保当前节点信息被写入 Profile
    if [ -f "$CONF_FILE" ]; then
         CUR_NODE=$(grep "CurrentNode=" "$CONF_FILE" | cut -d= -f2 | tr -d '\r\n ')
         SAVE_PROFILE="$PROFILE_ROOT/${SAVE_NAME}.conf"
         if [ ! -z "$CUR_NODE" ] && [ -f "$SAVE_PROFILE" ]; then
            sed -i '/CurrentNode=/d' "$SAVE_PROFILE"
            echo "CurrentNode=$CUR_NODE" >> "$SAVE_PROFILE"
         fi
         # 如果 Profile 不存在，从 Conf 复制
         if [ ! -f "$SAVE_PROFILE" ]; then cp "$CONF_FILE" "$SAVE_PROFILE"; fi
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
    APP_TYPE="$3"      
    RAW_ARG4="$4"
    RAW_ARG5="$5"
    
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
                *) REGION="HK" ;; 
            esac
            echo "🎯 [Smart Parse] Node: $NODE -> Region: $REGION"
        fi
    else
        REGION="$RAW_ARG4"
        NODE="$RAW_ARG5"
    fi
    
    [ -z "$APP_TYPE" ] && APP_TYPE="Vinted"
    [ -z "$REGION" ] && REGION="HK"
    [ -z "$NODE" ] && NODE="HK_061"

    PKG=$(get_package_name "$APP_TYPE")
    DATA_INT="/data/data/$PKG"
    DATA_EXT="/sdcard/Android/data/$PKG"
    
    echo "🆕 初始化 [$APP_TYPE | Region:$REGION | Node:$NODE]..."
    freeze_app "$PKG"
    pm clear "$PKG" >/dev/null 2>&1
    rm -rf "$DATA_EXT"
    safe_remove_google_account
    
    clean_network_stack
    switch_proxy "$NODE" "$REGION"
    
    # 🔨 Generate fingerprint with CORRECT region (fixes SIM mismatch)
    echo "🔨 [Fingerprint] Generating for $APP_TYPE | Region: $REGION"
    sh "$GEN_SCRIPT" "$APP_TYPE" "$REGION"
    
    if [ ! -f "$CONF_FILE" ]; then
        echo "❌ [FATAL] gen.sh failed to create config file"
        exit 1
    fi
    
    echo "AccountName=$NAME" >> "$CONF_FILE"
    echo "CurrentNode=$NODE" >> "$CONF_FILE"
    cp "$CONF_FILE" "$PROFILE_ROOT/$NAME.conf"
    chmod 666 "$CONF_FILE" "$PROFILE_ROOT/$NAME.conf"
    
    force_inject_gms_ads_id
    spoof_ssaid
    sync_gps_from_ip 
    
    APP_UID=$(cmd package list packages -U | grep "$PKG" | awk -F: '{print $3}' | tr -d ' ')
    if [ ! -z "$APP_UID" ]; then fix_strict "$DATA_INT" "$APP_UID"; fi

    echo "✈️ 网络重置..."
    cmd connectivity airplane-mode enable; sleep 1; cmd connectivity airplane-mode disable; sleep 3
    
    kill_interfering_apps
    unfreeze_app "$PKG"
    
    echo "✅ 新环境就绪 (New模式不自动拉起APP)"
fi

# === LOAD (加载) ===
if [ "$ACTION" = "load" ]; then
    [ -z "$NAME" ] && exit 1
    ARCHIVE="$BACKUP_ROOT/${NAME}.tar.gz"
    PROFILE="$PROFILE_ROOT/${NAME}.conf"
    
    if [ ! -f "$ARCHIVE" ]; then echo "❌ 无备份文件"; exit 1; fi

    # --- 🛡️ 自动防丢检查 (Auto-Save Guard) ---
    if [ -f "$CONF_FILE" ]; then
        CURRENT_NAME=$(grep "AccountName=" "$CONF_FILE" | cut -d= -f2 | tr -d '\r\n ')
        if [ ! -z "$CURRENT_NAME" ] && [ "$CURRENT_NAME" != "$NAME" ]; then
            echo "⚠️ 检测到当前活跃环境: [$CURRENT_NAME]"
            execute_save_logic "$CURRENT_NAME"
        fi
    fi
    # ----------------------------------------
    
    if [ -f "$PROFILE" ]; then
        APP_TYPE=$(grep "AppType=" "$PROFILE" | cut -d= -f2 | tr -d '\r\n ')
        REGION=$(grep "Region=" "$PROFILE" | cut -d= -f2 | tr -d '\r\n ')
        SAVED_NODE=$(grep "CurrentNode=" "$PROFILE" | cut -d= -f2 | tr -d '\r\n ')
    fi
    [ -z "$APP_TYPE" ] && APP_TYPE="Vinted"
    [ -z "$REGION" ] && REGION="HK"
    [ -z "$SAVED_NODE" ] && SAVED_NODE="HK_061"
    
    PKG=$(get_package_name "$APP_TYPE")
    DATA_INT="/data/data/$PKG"
    DATA_DE="/data/user_de/0/$PKG"
    DATA_EXT="/sdcard/Android/data/$PKG"
    APP_UID=$(cmd package list packages -U | grep "$PKG" | awk -F: '{print $3}' | tr -d ' ')
    
    echo "♻️ 还原 [$NAME] -> 节点: $SAVED_NODE..."
    
    freeze_app "$PKG"
    find "$DATA_INT" -mindepth 1 -maxdepth 1 ! -name 'lib' -exec rm -rf {} +
    rm -rf "$DATA_DE" "$DATA_EXT"
    safe_remove_google_account
    
    # Extract backup
    echo "📦 [Restore] Extracting backup..."
    tar -xzf "$ARCHIVE" -C /
    
    if [ $? -ne 0 ]; then
        echo "❌ [FATAL] Backup extraction failed"
        exit 1
    fi
    
    # Restore profile config
    if [ -f "$PROFILE" ]; then 
        cp "$PROFILE" "$CONF_FILE"
        chmod 666 "$CONF_FILE"
        restorecon "$CONF_FILE"
    fi
    
    # Network setup
    clean_network_stack
    switch_proxy "$SAVED_NODE" "$REGION"
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
    
    kill_interfering_apps
    unfreeze_app "$PKG"
    
    # 仅 Load 模式自动拉起
    launch_app "$PKG"
fi

# === SAVE (保存) ===
if [ "$ACTION" = "save" ]; then
    [ -z "$NAME" ] && exit 1
    
    # 直接调用封装好的保存逻辑
    execute_save_logic "$NAME"
    
    # 如果是手动保存，解冻 APP 方便继续使用
    APP_TYPE=$(grep "AppType=" "$CONF_FILE" | cut -d= -f2 | tr -d '\r\n ')
    [ -z "$APP_TYPE" ] && APP_TYPE="Vinted"
    PKG=$(get_package_name "$APP_TYPE")
    unfreeze_app "$PKG"
fi