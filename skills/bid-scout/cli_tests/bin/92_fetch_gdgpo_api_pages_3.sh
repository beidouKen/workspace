#!/usr/bin/env bash
# 广东省政府采购网 API 抓取测试 — 关键词"体育"，3 页
# 抓取 3 页，生成原始 JSON、过滤后 JSON 和 CSV
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
RAW_OUTPUT="/tmp/gdgpo_raw.json"
ITEMS_OUTPUT="/tmp/gdgpo_raw_items.json"
FILTERED_OUTPUT="/tmp/gdgpo_filtered.json"
CSV_OUTPUT="/tmp/gdgpo_report.csv"

echo "===== 广东省政府采购网 API 抓取（体育，3 页） ====="
echo "技能目录: $SKILL_DIR"
echo ""

# 步骤 1：API 抓取 3 页
echo "--- 步骤 1: API 抓取 ---"
python3 "$SKILL_DIR/tools/gdgpo_api_fetch.py" \
  --keyword 体育 \
  --pages 3 \
  --page-size 10 \
  --config "$SKILL_DIR/config/gdgpo_api.json" \
  --output "$RAW_OUTPUT" \
  --verbose

echo ""

# 步骤 2：关键词筛选
echo "--- 步骤 2: 关键词筛选 ---"
if [ -f "$ITEMS_OUTPUT" ]; then
  python3 "$SKILL_DIR/tools/keyword_filter.py" \
    --input "$ITEMS_OUTPUT" \
    --output "$FILTERED_OUTPUT"
  echo "筛选完成: $FILTERED_OUTPUT"
else
  echo "警告: items 文件不存在 ($ITEMS_OUTPUT)，跳过筛选"
  # 尝试从完整输出中提取 items
  if [ -f "$RAW_OUTPUT" ]; then
    python3 -c "
import json
with open('$RAW_OUTPUT', 'r', encoding='utf-8') as f:
    d = json.load(f)
items = d.get('items', [])
with open('$ITEMS_OUTPUT', 'w', encoding='utf-8') as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
print(f'从完整输出中提取了 {len(items)} 条 items')
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
echo "===== 最终结果 ====="
echo "原始 JSON: $RAW_OUTPUT"
echo "Items JSON: $ITEMS_OUTPUT"
echo "筛选 JSON: $FILTERED_OUTPUT"
echo "CSV 报告: $CSV_OUTPUT"

if [ -f "$RAW_OUTPUT" ]; then
  python3 -c "
import json
with open('$RAW_OUTPUT', 'r', encoding='utf-8') as f:
    d = json.load(f)
print(f'状态: {d.get(\"status\", \"unknown\")}')
print(f'请求页数: {d.get(\"pages_requested\", 0)}, 成功页数: {d.get(\"pages_succeeded\", 0)}')
print(f'总条目数: {len(d.get(\"items\", []))}')
print(f'错误数: {len(d.get(\"errors\", []))}')
high = sum(1 for i in d.get('items', []) if i.get('score', 0) >= 0.7)
print(f'高相关性条目 (score>=0.7): {high}')
"
fi
