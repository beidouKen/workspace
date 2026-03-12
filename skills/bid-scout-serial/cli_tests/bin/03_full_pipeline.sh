#!/usr/bin/env bash
# 完整 pipeline 测试：API 抓取 → 关键词筛选 → CSV → HTML
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
RAW_OUTPUT="/tmp/bss_raw.json"
ITEMS_OUTPUT="/tmp/bss_items.json"
FILTERED_OUTPUT="/tmp/bss_filtered.json"
CSV_OUTPUT="/tmp/bss_report.csv"
HTML_OUTPUT="/tmp/bss_report.html"

echo "===== bid-scout-serial 完整 Pipeline 测试 ====="
echo "技能目录: $SKILL_DIR"
echo ""

# 步骤 1：API 抓取
echo "--- 步骤 1: API 抓取（体育，3 页）---"
python3 "$SKILL_DIR/tools/gdgpo_api_fetch.py" \
  --keyword 体育 \
  --pages 3 \
  --page-size 10 \
  --config "$SKILL_DIR/config/gdgpo_api.json" \
  --output "$RAW_OUTPUT" \
  --verbose

echo ""

# 步骤 2：提取 items 并执行关键词筛选
echo "--- 步骤 2: 提取 items + 关键词筛选 ---"
if [ -f "$RAW_OUTPUT" ]; then
  python3 -c "
import json, pathlib
d = json.load(open('$RAW_OUTPUT', 'r', encoding='utf-8'))
items = d.get('items', [])
pathlib.Path('$ITEMS_OUTPUT').write_text(
    json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'提取了 {len(items)} 条 items')
"
  python3 "$SKILL_DIR/tools/keyword_filter.py" \
    --input "$ITEMS_OUTPUT" \
    --output "$FILTERED_OUTPUT"
  echo "筛选完成: $FILTERED_OUTPUT"
else
  echo "[FAIL] 原始 JSON 不存在，无法继续"
  exit 1
fi

echo ""

# 步骤 3：生成 CSV
echo "--- 步骤 3: 生成 CSV ---"
if [ -f "$FILTERED_OUTPUT" ]; then
  python3 "$SKILL_DIR/tools/generate_csv.py" \
    --input "$FILTERED_OUTPUT" \
    --output "$CSV_OUTPUT"
  echo "CSV 生成完成: $CSV_OUTPUT"
else
  echo "[WARN] 筛选结果不存在，跳过 CSV"
fi

echo ""

# 步骤 4：生成 HTML 报告
echo "--- 步骤 4: 生成 HTML 报告 ---"
if [ -f "$RAW_OUTPUT" ]; then
  python3 "$SKILL_DIR/tools/generate_html.py" \
    --input "$RAW_OUTPUT" \
    --output "$HTML_OUTPUT"
  echo "HTML 生成完成: $HTML_OUTPUT"
else
  echo "[WARN] 原始 JSON 不存在，跳过 HTML"
fi

echo ""
echo "===== Pipeline 结果 ====="

PASS=0
FAIL=0

for f in "$RAW_OUTPUT" "$ITEMS_OUTPUT" "$FILTERED_OUTPUT" "$CSV_OUTPUT" "$HTML_OUTPUT"; do
  if [ -f "$f" ]; then
    SIZE=$(wc -c < "$f" | tr -d ' ')
    echo "[PASS] $f ($SIZE bytes)"
    ((PASS++))
  else
    echo "[FAIL] $f (未生成)"
    ((FAIL++))
  fi
done

echo ""

if [ -f "$RAW_OUTPUT" ]; then
  python3 -c "
import json
d = json.load(open('$RAW_OUTPUT', 'r', encoding='utf-8'))
items = d.get('items', [])
print(f'状态: {d.get(\"status\", \"unknown\")}')
print(f'请求页数: {d.get(\"pages_requested\", 0)}, 成功页数: {d.get(\"pages_succeeded\", 0)}')
print(f'总条目数: {len(items)}')
high = sum(1 for i in items if i.get('match_level') == 'high')
print(f'高匹配条目: {high}')
print(f'错误数: {len(d.get(\"errors\", []))}')
"
fi

echo ""
echo "===== 结果: $PASS 通过, $FAIL 失败 ====="
[ "$FAIL" -eq 0 ] || exit 1
