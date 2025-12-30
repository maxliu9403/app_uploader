#!/system/bin/sh
# Multi-Region Config Generator V20.0 (Vinted/Carousell + GB/SG/MY/PH)

APP_TYPE="$1"  # Vinted or Carousell
REGION="$2"    # GB, SG, MY, PH
ACCOUNT_NAME="$3"  # Account name for stable random seed

[ -z "$APP_TYPE" ] && APP_TYPE="Vinted"
[ -z "$REGION" ] && REGION="GB"
[ -z "$ACCOUNT_NAME" ] && ACCOUNT_NAME="Unknown"

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
GSF_ID=$(gen_num 16)
MIUI_ID=$(gen_num 13)
OAID=$(gen_uuid)
MAC="D4:D2:D6:$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F')"
BT_MAC="18:F0:E4:$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F'):$(gen_hex 2 | tr 'a-f' 'A-F')"

# --- [IP 模拟移动网络] ---
IP="10.$(( $(date +%s) % 255 )).$(( $(date +%s) % 255 )).$(( $(date +%s) % 250 + 2 ))"

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
        ;;
esac

# --- 机型随机化 (K40S 亲戚系列 - Adreno 650) ---
CASE=$(( $(date +%s) % 4 ))
case $CASE in
0) # Poco F3
    MOD="M2012K11AG"; MAN="Xiaomi"; BRA="POCO"; DEV="alioth"; PRO="alioth_global"
    FIN="POCO/alioth_global/alioth:13/RKQ1.211001.001/V14.0.7.0.TKHMIXM:user/release-keys"
    GPU_VEN="Qualcomm"; GPU_REN="Adreno (TM) 650"
    ;;
1) # Xiaomi 10T
    MOD="M2007J3SG"; MAN="Xiaomi"; BRA="Xiaomi"; DEV="apollo"; PRO="apollo_global"
    FIN="Xiaomi/apollo_global/apollo:12/RKQ1.211001.001/V14.0.1.0.SJDMIXM:user/release-keys"
    GPU_VEN="Qualcomm"; GPU_REN="Adreno (TM) 650"
    ;;
2) # OnePlus 9R
    MOD="LE2101"; MAN="OnePlus"; BRA="OnePlus"; DEV="lemonades"; PRO="LE2101"
    FIN="OnePlus/LE2101/lemonades:13/RKQ1.211119.001/R.1161099-1-2:user/release-keys"
    GPU_VEN="Qualcomm"; GPU_REN="Adreno (TM) 650"
    ;;
*) # Xiaomi 12X
    MOD="2112123AG"; MAN="Xiaomi"; BRA="Xiaomi"; DEV="psyche"; PRO="psyche_global"
    FIN="Xiaomi/psyche_global/psyche:13/RKQ1.211001.001/V14.0.5.0.TLDMIXM:user/release-keys"
    GPU_VEN="Qualcomm"; GPU_REN="Adreno (TM) 650"
    ;;
esac

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
AccountName=$ACCOUNT_NAME
EOF

echo "✅ [$APP_TYPE | $REGION | $ACCOUNT_NAME] 配置生成: IP=$IP | SSAID=$ANDROID_ID | GPS=$GPS_LAT,$GPS_LON"