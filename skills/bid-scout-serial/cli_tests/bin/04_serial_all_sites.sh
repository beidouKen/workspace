#!/usr/bin/env bash
# 多站点串行集成测试
# 模拟串行流程：广东站 API → 广州站 mock → 合并 → 筛选 → CSV → HTML
# 广州站因需要浏览器，此测试使用 mock 数据模拟
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
GDGPO_RAW="/tmp/bss_serial_gdgpo.json"
GDGPO_ITEMS="/tmp/bss_serial_gdgpo_items.json"
GZ_MOCK="/tmp/bss_serial_gz_mock.json"
MERGED="/tmp/bss_serial_merged.json"
FILTERED="/tmp/bss_serial_filtered.json"
CSV_OUTPUT="/tmp/bss_serial_report.csv"
HTML_OUTPUT="/tmp/bss_serial_report.html"

echo "===== bid-scout-serial 多站点串行集成测试 ====="
echo "技能目录: $SKILL_DIR"
echo ""

# 步骤 1：广东站 API 采集
echo "--- 步骤 1: 广东省政府采购网 API 采集 ---"
python3 "$SKILL_DIR/tools/gdgpo_api_fetch.py" \
  --keyword 体育 \
  --pages 2 \
  --page-size 10 \
  --config "$SKILL_DIR/config/gdgpo_api.json" \
  --output "$GDGPO_RAW" \
  --verbose

python3 -c "
import json, pathlib
d = json.load(open('$GDGPO_RAW', 'r', encoding='utf-8'))
items = d.get('items', [])
pathlib.Path('$GDGPO_ITEMS').write_text(
    json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'广东站: status={d.get(\"status\")}, items={len(items)}')
"

echo ""
echo "--- 步骤 2: 广州市体育局 (mock 数据) ---"

cat > "$GZ_MOCK" << 'MOCKEOF'
[
  {
    "source_site": "广州市体育局",
    "title": "[mock] 广州市体育局2026年体育场馆运营服务采购项目公告",
    "publish_date": "2026-03-10",
    "url": "https://tyj.gz.gov.cn/tzgg/cgzb/",
    "detail_url": "https://tyj.gz.gov.cn/tzgg/cgzb/content/post_12345.html",
    "detail_url_status": "ok",
    "summary": "广州市体育局拟采购体育场馆运营管理服务",
    "detail_text": "[mock] 这是模拟的详情正文，用于测试串行 pipeline 的数据合并能力。",
    "purchaser": "广州市体育局",
    "budget": "500万元",
    "region": "广州",
    "notice_type": "招标公告",
    "match_score": 0,
    "match_level": "",
    "match_reason": "",
    "crawl_method": "browser",
    "data_quality": "medium",
    "crawl_time": "2026-03-12T00:00:00+00:00"
  },
  {
    "source_site": "广州市体育局",
    "title": "[mock] 广州市全民健身活动执行服务项目招标",
    "publish_date": "2026-03-08",
    "url": "https://tyj.gz.gov.cn/tzgg/cgzb/",
    "detail_url": "https://tyj.gz.gov.cn/tzgg/cgzb/content/post_12346.html",
    "detail_url_status": "ok",
    "summary": "为推动全民健身事业发展，拟采购活动执行服务",
    "detail_text": "[mock] 模拟正文：全民健身运动会执行服务采购，含赛事组织、场地保障等。",
    "purchaser": "广州市体育局",
    "budget": "200万元",
    "region": "广州",
    "notice_type": "招标公告",
    "match_score": 0,
    "match_level": "",
    "match_reason": "",
    "crawl_method": "browser",
    "data_quality": "medium",
    "crawl_time": "2026-03-12T00:00:00+00:00"
  }
]
MOCKEOF
echo "写入 mock 数据: $GZ_MOCK (2 条)"

echo ""
echo "--- 步骤 3: 合并两站数据 ---"
python3 -c "
import json, pathlib
gz = json.loads(pathlib.Path('$GZ_MOCK').read_text(encoding='utf-8'))
gdgpo = json.loads(pathlib.Path('$GDGPO_ITEMS').read_text(encoding='utf-8')) if pathlib.Path('$GDGPO_ITEMS').exists() else []
merged = gz + gdgpo
pathlib.Path('$MERGED').write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'合并: 广州站 {len(gz)} 条 + 广东站 {len(gdgpo)} 条 = {len(merged)} 条')
"

echo ""
echo "--- 步骤 4: 关键词筛选 ---"
python3 "$SKILL_DIR/tools/keyword_filter.py" \
  --input "$MERGED" \
  --output "$FILTERED"

echo ""
echo "--- 步骤 5: 生成 CSV ---"
python3 "$SKILL_DIR/tools/generate_csv.py" \
  --input "$FILTERED" \
  --output "$CSV_OUTPUT"
echo "CSV: $CSV_OUTPUT"

echo ""
echo "--- 步骤 6: 生成 HTML ---"
python3 "$SKILL_DIR/tools/generate_html.py" \
  --input "$MERGED" \
  --output "$HTML_OUTPUT"
echo "HTML: $HTML_OUTPUT"

echo ""
echo "===== 串行集成测试结果 ====="
PASS=0
FAIL=0

for f in "$GDGPO_RAW" "$GZ_MOCK" "$MERGED" "$FILTERED" "$CSV_OUTPUT" "$HTML_OUTPUT"; do
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
python3 -c "
import json
items = json.loads(open('$FILTERED', 'r', encoding='utf-8').read())
sites = {}
for item in items:
    s = item.get('source_site', 'unknown')
    sites[s] = sites.get(s, 0) + 1
print('按站点统计:')
for site, count in sites.items():
    print(f'  {site}: {count} 条')
high = sum(1 for i in items if i.get('match_level') == 'high')
med = sum(1 for i in items if i.get('match_level') == 'medium')
print(f'匹配度: high={high}, medium={med}, other={len(items)-high-med}')
"

echo ""
echo "===== 结果: $PASS 通过, $FAIL 失败 ====="
[ "$FAIL" -eq 0 ] || exit 1
