#!/usr/bin/env bash
# 广东省政府采购网 API 抓取测试 — 关键词"体育"，单页
# 抓取第 1 页，输出到 /tmp/gdgpo_raw.json
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
OUTPUT="/tmp/gdgpo_raw.json"

echo "===== 广东省政府采购网 API 抓取（体育，1 页） ====="
echo "技能目录: $SKILL_DIR"
echo "输出文件: $OUTPUT"
echo ""

python3 "$SKILL_DIR/tools/gdgpo_api_fetch.py" \
  --keyword 体育 \
  --pages 1 \
  --page-size 10 \
  --config "$SKILL_DIR/config/gdgpo_api.json" \
  --output "$OUTPUT" \
  --verbose

echo ""
echo "===== 抓取结果摘要 ====="
if [ -f "$OUTPUT" ]; then
  python3 -c "
import json
with open('$OUTPUT', 'r', encoding='utf-8') as f:
    d = json.load(f)
print(f'状态: {d.get(\"status\", \"unknown\")}')
print(f'条目数: {len(d.get(\"items\", []))}')
print(f'错误数: {len(d.get(\"errors\", []))}')
for i, item in enumerate(d.get('items', [])[:5], 1):
    print(f'  [{i}] {item.get(\"title\", \"N/A\")[:60]} (score={item.get(\"score\", 0):.2f})')
"
else
  echo "错误: 输出文件未生成"
  exit 1
fi
