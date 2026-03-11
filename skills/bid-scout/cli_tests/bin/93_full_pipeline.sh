#!/usr/bin/env bash
# 完整 pipeline 集成测试：API 抓取 → 关键词筛选 → CSV → HTML
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
RAW_OUTPUT="/tmp/bid_raw.json"
ITEMS_OUTPUT="/tmp/bid_raw_items.json"
FILTERED_OUTPUT="/tmp/bid_filtered.json"
CSV_OUTPUT="/tmp/bid_report.csv"
HTML_OUTPUT="/tmp/bid_report.html"

echo "===== 完整 Pipeline 集成测试 ====="
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
echo "--- 步骤 2: 关键词筛选 ---"
if [ -f "$ITEMS_OUTPUT" ]; then
  python3 "$SKILL_DIR/tools/keyword_filter.py" \
    --input "$ITEMS_OUTPUT" \
    --output "$FILTERED_OUTPUT"
  echo "筛选完成: $FILTERED_OUTPUT"
else
  echo "items 文件不存在，从完整输出中提取..."
  if [ -f "$RAW_OUTPUT" ]; then
    python3 -c "
import json
with open('$RAW_OUTPUT', 'r', encoding='utf-8') as f:
    d = json.load(f)
items = d.get('items', [])
with open('$ITEMS_OUTPUT', 'w', encoding='utf-8') as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
print(f'提取了 {len(items)} 条 items')
"
    python3 "$SKILL_DIR/tools/keyword_filter.py" \
      --input "$ITEMS_OUTPUT" \
      --output "$FILTERED_OUTPUT"
    echo "筛选完成: $FILTERED_OUTPUT"
  fi
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
  echo "警告: 筛选结果不存在，跳过 CSV 生成"
fi

echo ""

# 步骤 4：生成 HTML 报告（从原始 JSON 生成，包含完整元信息）
echo "--- 步骤 4: 生成 HTML 报告 ---"
if [ -f "$RAW_OUTPUT" ]; then
  python3 "$SKILL_DIR/tools/generate_html.py" \
    --input "$RAW_OUTPUT" \
    --output "$HTML_OUTPUT"
  echo "HTML 生成完成: $HTML_OUTPUT"
else
  echo "警告: 原始 JSON 不存在，跳过 HTML 生成"
fi

echo ""
echo "===== Pipeline 结果 ====="
echo "原始 JSON:  $RAW_OUTPUT"
echo "Items JSON: $ITEMS_OUTPUT"
echo "筛选 JSON:  $FILTERED_OUTPUT"
echo "CSV 报告:   $CSV_OUTPUT"
echo "HTML 报告:  $HTML_OUTPUT"

if [ -f "$RAW_OUTPUT" ]; then
  python3 -c "
import json
with open('$RAW_OUTPUT', 'r', encoding='utf-8') as f:
    d = json.load(f)
items = d.get('items', [])
print(f'状态: {d.get(\"status\", \"unknown\")}')
print(f'请求页数: {d.get(\"pages_requested\", 0)}, 成功页数: {d.get(\"pages_succeeded\", 0)}')
print(f'总条目数: {len(items)}')
high = sum(1 for i in items if i.get('match_level') == 'high')
print(f'高匹配条目: {high}')
quality = {}
for i in items:
    q = i.get('data_quality', 'unknown')
    quality[q] = quality.get(q, 0) + 1
print(f'数据质量分布: {quality}')
print(f'错误数: {len(d.get(\"errors\", []))}')
"
fi

echo ""
for f in "$CSV_OUTPUT" "$HTML_OUTPUT"; do
  if [ -f "$f" ]; then
    SIZE=$(wc -c < "$f" | tr -d ' ')
    echo "✓ $f ($SIZE bytes)"
  else
    echo "✗ $f (未生成)"
  fi
done
