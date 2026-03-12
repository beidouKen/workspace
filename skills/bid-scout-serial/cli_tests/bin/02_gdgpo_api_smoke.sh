#!/usr/bin/env bash
# 广东省政府采购网 API 单页冒烟测试
# 关键词"体育"，1 页，验证输出 JSON 结构
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
OUTPUT="/tmp/bss_gdgpo_smoke.json"

echo "===== 广东站 API 冒烟测试（体育，1 页）====="
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
echo "===== 结果检查 ====="
if [ ! -f "$OUTPUT" ]; then
  echo "[FAIL] 输出文件未生成"
  exit 1
fi

python3 -c "
import json, sys
with open('$OUTPUT', 'r', encoding='utf-8') as f:
    d = json.load(f)

status = d.get('status', 'unknown')
items = d.get('items', [])
errors = d.get('errors', [])

print(f'状态: {status}')
print(f'条目数: {len(items)}')
print(f'错误数: {len(errors)}')

if items:
    for i, item in enumerate(items[:5], 1):
        title = item.get('title', 'N/A')[:60]
        score = item.get('match_score', 0)
        print(f'  [{i}] {title} (score={score:.2f})')

if status in ('completed', 'partial') and len(items) > 0:
    print('')
    print('[PASS] API 冒烟测试通过')
else:
    print('')
    print(f'[FAIL] API 冒烟测试失败 (status={status}, items={len(items)})')
    sys.exit(1)
"
