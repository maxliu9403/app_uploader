#!/system/bin/sh
# Multi-Region Config Generator V22.0 (Security-Enhanced Single Config)
# Features: Region-based MCC/MNC | AppType-based Model Fingerprints | Kill Switch Compatible

APP_TYPE="$1"  # Vinted or Carousell
REGION="$2"    # GB, SG, MY, PH, HK

[ -z "$APP_TYPE" ] && APP_TYPE="Vinted"
[ -z "$REGION" ] && REGION="GB"

# Single config file for all apps
CONF_FILE="/data/local/tmp/multiapp_conf.txt"

# --- 工具函数 ---
gen_hex() { cat /dev/urandom | tr -dc 'a-f0-9' | head -c "$1" | tr -d '\n\r'; }
gen_num() { cat /dev/urandom | tr -dc '0-9' | head -c "$1" | tr -d '\n\r'; }
gen_uuid() { 
    local u="$(gen_hex 8)-$(gen_hex 4)-$(gen_hex 4)-$(gen_hex 4)-$(gen_hex 12)"
    echo -n "$u"
}

# --- 生成参数 ---
ANDROID_ID=$(gen_hex 16)
ADS_ID=$(gen_uuid)
IMEI="86516605$(gen_num 7)"
SERIAL=$(gen_hex 8 | tr 'a-f' 'A-F')
# 🐛 关键修复: GSF ID 必须是16位纯数字 (十进制格式)，不是十六进制！
# Device ID 软件期望格式如: "4570628172512369"
GSF_ID=$(gen_num 16)
MIUI_ID=$(gen_num 13)
OAID=$(gen_uuid)
MAC="D4:D2:D6:$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F')"
BT_MAC="18:F0:E4:$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F')"

# --- [IP 模拟移动网络] ---
IP="10.$(( $(date +%s) % 255 )).$(( $(date +%s) % 255 )).$(( $(date +%s) % 250 + 2 ))"
GPS_ALT=$(awk -v min=5 -v max=100 'BEGIN{srand(); print min+rand()*(max-min)}')


# --- [Time Simulation] ---
NOW_TS=$(date +%s)
# 30-120 days ago (Loyal user simulation)
DAYS=$(( $(gen_num 2) % 90 + 30 ))
INSTALL_TS=$(( NOW_TS - DAYS * 86400 ))

# --- 区域配置 (MCC/MNC/Phone/Operator) ---
case "$REGION" in
    GB)
        MCC="234"; MNC="15"  # Vodafone UK
        IMSI="23415$(gen_num 10)"
        ICCID="894415$(gen_num 13)"
        PHONE="+447$(gen_num 9)"
        OPERATOR="Vodafone UK"
        SSID="Vodafone-WiFi-$(gen_num 3)"
        BSSID="50:C7:BF:$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F')"
        GPS_LAT="51.5072"; GPS_LON="-0.1276"  # London
        TIMEZONE="Europe/London"; LOCALE="en_GB"; ISO_CODE="gb"
        ;;
    HK)
        MCC="454"; MNC="00"  # CSL
        IMSI="45400$(gen_num 10)"
        ICCID="8985200$(gen_num 13)"
        PHONE="+852$(gen_num 8)"
        OPERATOR="CSL"
        SSID="CSL-WiFi-$(gen_num 3)"
        BSSID="00:1E:58:$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F')"
        GPS_LAT="22.3193"; GPS_LON="114.1694"  # Hong Kong
        TIMEZONE="Asia/Hong_Kong"; LOCALE="en_HK"; ISO_CODE="hk"
        ;;

    SG)
        MCC="525"; MNC="01"  # SingTel
        IMSI="52501$(gen_num 10)"
        ICCID="895201$(gen_num 13)"
        PHONE="+658$(gen_num 7)"
        OPERATOR="SingTel"
        SSID="SingTel-WiFi-$(gen_num 3)"
        BSSID="54:A0:50:$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F')"
        GPS_LAT="1.3521"; GPS_LON="103.8198"  # Singapore
        TIMEZONE="Asia/Singapore"; LOCALE="en_SG"; ISO_CODE="sg"
        ;;
    MY)
        MCC="502"; MNC="12"  # Maxis
        IMSI="50212$(gen_num 10)"
        ICCID="895012$(gen_num 13)"
        PHONE="+6012$(gen_num 7)"
        OPERATOR="Maxis"
        SSID="Maxis-WiFi-$(gen_num 3)"
        BSSID="00:1F:3F:$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F')"
        GPS_LAT="3.1390"; GPS_LON="101.6869"  # Kuala Lumpur
        TIMEZONE="Asia/Kuala_Lumpur"; LOCALE="en_MY"; ISO_CODE="my"
        ;;
    PH)
        MCC="515"; MNC="02"  # Globe
        IMSI="51502$(gen_num 10)"
        ICCID="895102$(gen_num 13)"
        PHONE="+639$(gen_num 9)"
        OPERATOR="Globe Telecom"
        SSID="Globe-WiFi-$(gen_num 3)"
        BSSID="78:44:76:$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F')"
        GPS_LAT="14.5995"; GPS_LON="120.9842"  # Manila
        TIMEZONE="Asia/Manila"; LOCALE="en_PH"; ISO_CODE="ph"
        ;;
    *)
        # Default to GB
        MCC="234"; MNC="15"
        IMSI="23415$(gen_num 10)"
        ICCID="894415$(gen_num 13)"
        PHONE="+447$(gen_num 9)"
        OPERATOR="Vodafone UK"
        SSID="Vodafone-WiFi-$(gen_num 3)"
        BSSID="50:C7:BF:$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F')"
        GPS_LAT="51.5072"; GPS_LON="-0.1276"
        TIMEZONE="Europe/London"; LOCALE="en_GB"; ISO_CODE="gb"
        ;;
esac

# --- 机型配置 (AppType-based: EU vs SEA) ---
if [ "$APP_TYPE" = "Vinted" ]; then
    # 🇪🇺 EU Models for Vinted (Pixel/Samsung preferred for EU market)
    CASE=$(( $(date +%s) % 4 ))
    case $CASE in
    0) # Google Pixel 6 Pro
        MOD="GF5KQ"; MAN="Google"; BRA="google"; DEV="raven"; PRO="raven"
        FIN="google/raven/raven:13/TP1A.221005.002/9012097:user/release-keys"
        GPU_VEN="ARM"; GPU_REN="Mali-G78"
        ;;
    1) # Samsung Galaxy S21 5G
        MOD="SM-G991B"; MAN="samsung"; BRA="samsung"; DEV="o1s"; PRO="o1sxxx"
        FIN="samsung/o1sxxx/o1s:13/TP1A.220624.014/G991BXXU5DVKB:user/release-keys"
        GPU_VEN="ARM"; GPU_REN="Mali-G78"
        ;;
    2) # Google Pixel 7
        MOD="GVU6C"; MAN="Google"; BRA="google"; DEV="panther"; PRO="panther"
        FIN="google/panther/panther:13/TQ3A.230805.001/10316531:user/release-keys"
        GPU_VEN="ARM"; GPU_REN="Mali-G710"
        ;;
    *) # Samsung Galaxy S22
        MOD="SM-S901B"; MAN="samsung"; BRA="samsung"; DEV="r0s"; PRO="r0sxxx"
        FIN="samsung/r0sxxx/r0s:13/TP1A.220624.014/S901BXXU2AVKC:user/release-keys"
        GPU_VEN="Xclipse"; GPU_REN="Xclipse 920"
        ;;
    esac
else
    # 🌏 SEA Models for Carousell (Xiaomi/Oppo popular in SEA)
    CASE=$(( $(date +%s) % 4 ))
    case $CASE in
    0) # Xiaomi 11T Pro (Popular in SG/MY)
        MOD="2107113SG"; MAN="Xiaomi"; BRA="Xiaomi"; DEV="vili"; PRO="vili_global"
        FIN="Xiaomi/vili_global/vili:13/RKQ1.211001.001/V14.0.3.0.TKDMIXM:user/release-keys"
        GPU_VEN="Qualcomm"; GPU_REN="Adreno (TM) 660"
        ;;
    1) # OPPO Find X3 Pro
        MOD="CPH2173"; MAN="OPPO"; BRA="OPPO"; DEV="OP4F2F"; PRO="OP4F2F"
        FIN="OPPO/CPH2173/OP4F2F:13/TP1A.220905.001/R.202303201900:user/release-keys"
        GPU_VEN="Qualcomm"; GPU_REN="Adreno (TM) 660"
        ;;
    2) # Xiaomi 12 (SEA version)
        MOD="2201123G"; MAN="Xiaomi"; BRA="Xiaomi"; DEV="cupid"; PRO="cupid_global"
        FIN="Xiaomi/cupid_global/cupid:13/RKQ1.211001.001/V14.0.6.0.TLCMIXM:user/release-keys"
        GPU_VEN="Qualcomm"; GPU_REN="Adreno (TM) 730"
        ;;
    3) # Redmi K40 / POCO F3 (Global/Alioth) - Matches User Device Series
        MOD="M2012K11AG"; MAN="Xiaomi"; BRA="POCO"; DEV="alioth"; PRO="alioth_global"
        FIN="POCO/alioth_global/alioth:13/TKQ1.221114.001/V14.0.7.0.TKHMIXM:user/release-keys"
        GPU_VEN="Qualcomm"; GPU_REN="Adreno (TM) 650"
        ;;
    *) # OPPO Reno8 Pro

        MOD="CPH2357"; MAN="OPPO"; BRA="OPPO"; DEV="OP557BL1"; PRO="OP557BL1"
        FIN="OPPO/CPH2357/OP557BL1:13/TP1A.220905.001/R.202304251430:user/release-keys"
        GPU_VEN="Qualcomm"; GPU_REN="Adreno (TM) 650"
        ;;
    esac
fi

# --- 写入文件 ---
rm -f "$CONF_FILE"
touch "$CONF_FILE"
chmod 666 "$CONF_FILE"

cat <<EOF > "$CONF_FILE"
AndroidID=$ANDROID_ID
AdsId=$ADS_ID
GsfId=$GSF_ID
IMEI=$IMEI
Serial=$SERIAL
MacAddress=$MAC
BluetoothMAC=$BT_MAC
WifiBSSID=$BSSID
SubscriberID=$IMSI
SimSerial=$ICCID
PhoneNumber=$PHONE
InternalIP=$IP
WifiSSID=$SSID
MCC=$MCC
MNC=$MNC
NetworkOperator=$OPERATOR
SimOperator=$OPERATOR
MANUFACTURER=$MAN
BRAND=$BRA
MODEL=$MOD
DEVICE=$DEV
PRODUCT=$PRO
FINGERPRINT=$FIN
MiuiID=$MIUI_ID
OAID=$OAID
GPUVendor=$GPU_VEN
GPURenderer=$GPU_REN
SELinuxStatus=Enforcing
GPS_LAT=$GPS_LAT
GPS_LON=$GPS_LON
GPS_ALT=$GPS_ALT
FirstInstallTime=$INSTALL_TS
GPS_ALT=$GPS_ALT
AppType=$APP_TYPE
Region=$REGION
Timezone=$TIMEZONE
Locale=$LOCALE
ISO_CODE=$ISO_CODE
EOF

chmod 666 "$CONF_FILE"
echo "✅ [$APP_TYPE | $REGION] 配置已生成 -> $CONF_FILE"
echo "📱 Model: $MOD ($MAN)"
echo "🌐 IP=$IP | SSAID=$ANDROID_ID"
echo "📍 GPS: $GPS_LAT,$GPS_LON ($OPERATOR)"