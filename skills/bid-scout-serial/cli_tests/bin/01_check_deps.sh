#!/usr/bin/env bash
# 依赖检查：Python3 + 必要包 + 配置文件
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PASS=0
FAIL=0

check() {
  local label="$1"; shift
  if "$@" > /dev/null 2>&1; then
    echo "[PASS] $label"
    ((PASS++))
  else
    echo "[FAIL] $label"
    ((FAIL++))
  fi
}

echo "===== bid-scout-serial 依赖检查 ====="
echo "技能目录: $SKILL_DIR"
echo ""

check "Python3 可用" python3 --version
check "requests 已安装" python3 -c "import requests"
check "beautifulsoup4 已安装" python3 -c "from bs4 import BeautifulSoup"
check "lxml 已安装" python3 -c "import lxml"
check "jinja2 已安装" python3 -c "import jinja2"

check "config/gdgpo_api.json 存在" test -f "$SKILL_DIR/config/gdgpo_api.json"
check "tools/gdgpo_api_fetch.py 存在" test -f "$SKILL_DIR/tools/gdgpo_api_fetch.py"
check "tools/gdgpo_probe_api.py 存在" test -f "$SKILL_DIR/tools/gdgpo_probe_api.py"
check "tools/keyword_filter.py 存在" test -f "$SKILL_DIR/tools/keyword_filter.py"
check "tools/generate_csv.py 存在" test -f "$SKILL_DIR/tools/generate_csv.py"
check "tools/generate_html.py 存在" test -f "$SKILL_DIR/tools/generate_html.py"

echo ""
echo "===== 结果: $PASS 通过, $FAIL 失败 ====="
[ "$FAIL" -eq 0 ] || exit 1
