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
    
    # Build API commands
    if [ -z "$SECRET" ]; then
        CMD_GLOBAL="curl -s -X PUT $API_URL/proxies/GLOBAL -H 'Content-Type: application/json' -d '{\"name\": \"$TARGET_NODE\"}'"
    else
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
    NOW=$(curl -s "$API_URL/proxies/GLOBAL" | grep -o '"now":"[^"]*"' | cut -d'"' -f4)
    if [ "$NOW" != "$TARGET_NODE" ]; then
        sleep 2
        NOW=$(curl -s "$API_URL/proxies/GLOBAL" | grep -o '"now":"[^"]*"' | cut -d'"' -f4)
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
    
    # 切换代理
    switch_proxy "$NODE" "$REGION"
    
    # 🔨 Generate fingerprint with CORRECT region (fixes SIM mismatch)
    echo "🔨 [Fingerprint] Generating for $APP_TYPE | Region: $REGION"
    sh "$GEN_SCRIPT" "$APP_TYPE" "$REGION"
    
    if [ ! -f "$CONF_FILE" ]; then
        echo "❌ [FATAL] gen.sh failed to create config file"
        exit 1
    fi
    
    # 写入配置
    echo "AccountName=$NAME" >> "$CONF_FILE"
    echo "CurrentNode=$NODE" >> "$CONF_FILE"
    echo "AppType=$APP_TYPE" >> "$CONF_FILE"
    
    # 保存配置副本
    cp "$CONF_FILE" "$PROFILE_ROOT/$NAME.conf"
    chmod 666 "$CONF_FILE" "$PROFILE_ROOT/$NAME.conf"
    
    # 注入 GMS IDs
    force_inject_gms_ads_id
    spoof_ssaid
    
    # GPS 同步
    sync_gps_from_ip 
    
    # 修复权限
    APP_UID=$(cmd package list packages -U | grep "$PKG" | awk -F: '{print $3}' | tr -d ' ')
    if [ ! -z "$APP_UID" ]; then 
        fix_strict "$DATA_INT" "$APP_UID"
    fi

    # 网络重置
    echo "✈️ 网络重置..."
    cmd connectivity airplane-mode enable
    sleep 1
    cmd connectivity airplane-mode disable
    sleep 3
    
    # 清理干扰应用
    kill_interfering_apps
    
    # 解冻应用
    unfreeze_app "$PKG"
    
    echo "✅ 新环境就绪: $NAME (New模式不自动拉起APP)"
    echo "📋 账号信息: APP=$APP_TYPE, Region=$REGION, Node=$NODE"
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
        BACKUP_VERSION=$(grep "AppVersion=" "$PROFILE" | cut -d= -f2 | tr -d '\r\n ')
    fi
    [ -z "$APP_TYPE" ] && APP_TYPE="Vinted"
    [ -z "$REGION" ] && REGION="HK"
    [ -z "$SAVED_NODE" ] && SAVED_NODE="HK_061"
    
    PKG=$(get_package_name "$APP_TYPE")
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
    
    echo "♻️ 还原 [$NAME] -> 节点: $SAVED_NODE..."
    
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
    echo "📦 [Restore] Extracting backup..."
    tar -xzf "$ARCHIVE" -C /
    
    if [ $? -ne 0 ]; then
        echo "❌ [FATAL] Backup extraction failed"
        exit 1
    fi
    
    # 🔒 关键：修复所有权限和SELinux上下文
    echo "🔧 [Restore] 修复权限和SELinux上下文..."
    fix_strict "$DATA_INT" "$APP_UID"
    fix_strict "$DATA_DE" "$APP_UID"
    
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