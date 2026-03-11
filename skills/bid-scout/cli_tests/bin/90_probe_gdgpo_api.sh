#!/usr/bin/env bash
# 广东省政府采购网 API 端点探测测试
# 执行 probe 脚本，输出探测报告到 /tmp/gdgpo_probe.json
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
OUTPUT="/tmp/gdgpo_probe.json"

echo "===== 广东省政府采购网 API 端点探测 ====="
echo "技能目录: $SKILL_DIR"
echo "输出文件: $OUTPUT"
echo ""

python3 "$SKILL_DIR/tools/gdgpo_probe_api.py" \
  --config "$SKILL_DIR/config/gdgpo_api.json" \
  --output "$OUTPUT" \
  --verbose

echo ""
echo "===== 探测结果 ====="
if [ -f "$OUTPUT" ]; then
  python3 -c "
import json, sys
with open('$OUTPUT', 'r', encoding='utf-8') as f:
    d = json.load(f)
print(f'页面可访问: {d.get(\"page_accessible\", False)}')
print(f'JS bundle 数: {len(d.get(\"js_bundles_found\", []))}')
print(f'候选 API 数: {len(d.get(\"suspected_apis\", []))}')
best = d.get('best_endpoint')
if best:
    print(f'最佳端点: {best.get(\"url\", \"N/A\")}')
    print(f'已确认: {best.get(\"confirmed\", False)}')
else:
    print('最佳端点: 未发现')
print(f'需要运行时确认: {d.get(\"needs_runtime_confirmation\", True)}')
"
else
  echo "错误: 输出文件未生成"
  exit 1
fi
