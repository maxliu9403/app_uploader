#!/system/bin/sh
# Sing-Box / Clash 自动切线脚本 (通用版)

# ⚠️ 必须和 config.yaml 里的策略组名称一模一样！
PROXY_GROUP="Select-HK-IP"

API_URL="http://127.0.0.1:9090"
SECRET=""  # 如果 config.yaml 中 secret 不为空，请在这里填写

TARGET_NODE="$1"

if [ -z "$TARGET_NODE" ]; then
    echo "❌ 错误: 未指定节点名称"
    echo "用法: $0 <节点名称>"
    echo "可用节点: HK_061, HK_091, HK_092, HK_093, HK_094, HK_095, HK_096, HK_097, HK_098, HK_099, HK_100"
    exit 1
fi

echo "🌐 正在切换网络至: [$TARGET_NODE] ..."

# 发送切换指令（Clash Meta / Sing-Box 兼容格式）
if [ -z "$SECRET" ]; then
    RESPONSE=$(curl -s -X PUT "$API_URL/proxies/$PROXY_GROUP" \
         -H "Content-Type: application/json" \
         -d "{\"name\": \"$TARGET_NODE\"}")
else
    RESPONSE=$(curl -s -X PUT "$API_URL/proxies/$PROXY_GROUP" \
         -H "Content-Type: application/json" \
         -H "Authorization: Bearer $SECRET" \
         -d "{\"name\": \"$TARGET_NODE\"}")
fi

# 检查返回结果
if echo "$RESPONSE" | grep -qi "error\|not found\|invalid"; then
    echo "❌ 切换失败！"
    echo "错误信息: $RESPONSE"
    echo ""
    echo "💡 调试建议:"
    echo "1. 检查策略组名称是否正确: $PROXY_GROUP"
    echo "2. 检查节点名称是否正确: $TARGET_NODE"
    echo "3. 当前可用节点列表:"
    curl -s "$API_URL/proxies/$PROXY_GROUP" | grep -o '"all":\["[^]]*"\]' | sed 's/"all":\[//;s/\]//;s/","/\n/g;s/"//g' | sed 's/^/   - /'
    exit 1
fi

# 验证切换结果
CURRENT=$(curl -s "$API_URL/proxies/$PROXY_GROUP" | grep -o '"now":"[^"]*"' | cut -d'"' -f4)

if [ "$CURRENT" = "$TARGET_NODE" ]; then
    echo "✅ 切换成功: $TARGET_NODE"
    echo "📍 当前使用: $CURRENT"
else
    echo "⚠️ 切换可能失败"
    echo "目标节点: $TARGET_NODE"
    echo "当前节点: $CURRENT"
    exit 1
fi