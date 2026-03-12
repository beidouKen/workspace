---
name: bid-scout-serial
description: 招投标信息串行采集工具（保底版）。当用户需要查询、采集政府招投标公告时使用此技能。单 Agent 串行执行，不依赖子 Agent / session / 多标签页，优先保证稳定可用。支持 API-first 采集、browser 兜底、关键词筛选打分、CSV/HTML 报告输出。
metadata: { "openclaw": { "emoji": "📋", "variant": "serial" } }
---

# 招投标信息串行采集 (BidScout Serial)

> **这是串行保底版**。不使用子 Agent、不使用 session、不使用多标签页。
> 主 Agent 自己按站点顺序逐个采集，优先稳定可用。

## 能力范围

**支持**：
- 单 Agent 串行采集多个站点（逐站点顺序执行）
- API-first 采集（广东省政府采购网通过 HTTP API 直接抓取，无需浏览器）
- Browser 兜底采集（API 不可用时，用 browser navigate + screenshot + snapshot）
- 智能关键词筛选打分（体育 + 服务运营关键词交叉评分）
- CSV 报告（18 列标准结构，utf-8-sig 编码，Excel 兼容）
- HTML 情报报告（摘要统计 + 主表格 + 折叠详情 + 异常区）
- 人工接管（验证码/登录时阻塞式等待用户处理）

**不支持**：
- 多站点并发采集
- 子 Agent 编排
- Session 恢复 / 会话追踪
- 多标签页同时操作
- 增量 / 定时采集

## 核心原则

### 禁止

1. **禁止创建子 Agent** — 不使用 `sessions_spawn` / `sessions_send` / `sessions_history`
2. **禁止使用 `browser type`** — 会报 "request required" 错误
3. **禁止使用 `browser open`** — 不创建新标签页，所有操作在当前标签页
4. **禁止放弃整体任务** — 单站点失败只跳过该站点，继续采集下一个
5. **禁止引入并发逻辑** — 不使用 targetId 分发、不使用 thread、不使用 worker

### 必须

1. **单标签页操作**：所有 browser 命令在当前标签页执行，不带 `targetId` 参数
2. **串行顺序执行**：站点 A 完全采集完毕后，才开始站点 B
3. **API 优先**：凡有 API 的站点，先用 `exec` 调用 Python 脚本；API 失败才退回 browser
4. **image 工具是你的眼睛**：页面内容通过 `image` 工具读取截图获取
5. **每次操作后间隔**：页面操作后 `exec command:"sleep 2"` 等待加载

## 目标站点

| 站点 | 入口 URL | 采集方式 | 备注 |
|------|----------|----------|------|
| 广东省政府采购网 | `https://gdgpo.czt.gd.gov.cn/maincms-web/fullSearchingGd` | **API-first**，browser 兜底 | 优先用 `gdgpo_api_fetch.py` 直接调接口 |
| 广州市体育局 | `https://tyj.gz.gov.cn/tzgg/cgzb/` | **browser only** | 天然体育相关，直接采集列表 |

> 站点执行顺序：先广东站（API 模式快且稳定），再广州站（需要浏览器）。

## 工具路径

本技能附带 Python 工具，相对于 SKILL.md 所在目录：
- **广东站 API 抓取**：`tools/gdgpo_api_fetch.py`（API-first 核心脚本，输出统一 JSON Schema）
- **广东站接口探测**：`tools/gdgpo_probe_api.py`（发现/验证搜索 API 端点）
- **广东站接口配置**：`config/gdgpo_api.json`（接口参数、字段映射、选择器）
- **关键词筛选**：`tools/keyword_filter.py`
- **CSV 生成**：`tools/generate_csv.py`（18 列标准结构）
- **HTML 报告**：`tools/generate_html.py`（情报报告，含摘要/表格/折叠详情/异常区）

调用时必须使用绝对路径，基于技能目录解析。例如：
```
exec command:"python3 {skill_dir}/tools/gdgpo_api_fetch.py --keyword 体育 --pages 3 --config {skill_dir}/config/gdgpo_api.json --output /tmp/gdgpo_raw.json --verbose"
exec command:"python3 {skill_dir}/tools/keyword_filter.py --input /tmp/bid_raw.json --output /tmp/bid_filtered.json"
exec command:"python3 {skill_dir}/tools/generate_csv.py --input /tmp/bid_filtered.json --output /tmp/bid_report.csv"
exec command:"python3 {skill_dir}/tools/generate_html.py --input /tmp/bid_raw.json --output /tmp/bid_report.html"
```

## 操作流程

### 第一步：理解需求

分析用户想采集什么：
- 是否指定了站点？未指定则默认查**全部站点**
- 是否指定了关键词？未指定则使用内置体育+服务运营关键词
- 采集数量？默认每站点 **5 条**

如果需求模糊，简短确认后开始。

### 第二步：检查浏览器连接

**仅在需要浏览器采集时执行此步骤**。如果用户只需要广东站且 API 可用，可跳过此步。

```
browser status
```

如果未连接，告知用户：

> **需要连接浏览器**
>
> 请在 Chrome 浏览器中：
> 1. 打开任意网页
> 2. 点击工具栏上的 **OpenClaw Browser Relay** 扩展图标
> 3. 确保图标徽章显示为 **ON**
> 4. 回复「**好了**」
>
> 连接成功后我会自动开始采集。

**等待用户回复后才继续。**

### 第三步：采集站点 A — 广东省政府采购网（API-first）

**阶段 1：API 采集（优先执行）**

直接通过 Python 脚本调用站点数据接口，无需浏览器：

```
exec command:"python3 {skill_dir}/tools/gdgpo_api_fetch.py --keyword 体育 --pages 3 --page-size 10 --config {skill_dir}/config/gdgpo_api.json --output /tmp/gdgpo_raw.json --verbose"
```

检查结果：
```
exec command:"python3 -c \"import json; d=json.load(open('/tmp/gdgpo_raw.json','r',encoding='utf-8')); print(f'status={d.get(\\\"status\\\")}, items={len(d.get(\\\"items\\\",[]))}, errors={len(d.get(\\\"errors\\\",[]))}')\""
```

判断：
- `status` 为 `completed` 或 `partial` 且 `items` 非空 → API 采集成功，跳到第四步
- `status` 为 `failed` 或 `items` 为空 → 进入阶段 2（browser 兜底）

**阶段 2：browser 兜底（仅在 API 失败时执行）**

1. 确认浏览器已连接（若未连接，执行第二步）
2. 导航到搜索页：
   ```
   browser navigate url:"https://gdgpo.czt.gd.gov.cn/maincms-web/fullSearchingGd"
   exec command:"sleep 3"
   ```
3. 截图确认页面状态：
   ```
   browser screenshot
   ```
   用 image 工具判断：搜索页正常 / tipsPage 重定向 / 403 / 验证码
4. 获取可访问性树找搜索框：
   ```
   browser snapshot
   ```
5. 点击搜索框并尝试输入：
   ```
   browser click ref:"{搜索框ref}"
   exec command:"sleep 1"
   browser act kind:fill ref:"{搜索框ref}" text:"体育"
   exec command:"sleep 1"
   ```
6. 截图确认输入成功：
   ```
   browser screenshot
   ```
   如果输入失败 → 进入人工接管（见人工接管章节）
7. 点击搜索按钮：
   ```
   browser click ref:"{搜索按钮ref}"
   exec command:"sleep 5"
   ```
8. 提取结果：screenshot + snapshot + image 读取列表
9. 对前 5 条逐个进入详情页提取摘要

browser 兜底只做基本提取，将结果写入 `/tmp/gdgpo_raw.json`。

### 第四步：采集站点 B — 广州市体育局（browser）

```
exec command:"sleep 3"
```

1. 导航到列表页：
   ```
   browser navigate url:"https://tyj.gz.gov.cn/tzgg/cgzb/"
   exec command:"sleep 3"
   ```
2. 截图 + 可访问性树：
   ```
   browser screenshot
   browser snapshot
   ```
   用 image 工具判断页面状态，从 snapshot 提取公告列表（标题、日期、链接）
3. 对前 5 条公告，逐个进入详情页：
   ```
   browser navigate url:"{详情URL}"
   exec command:"sleep 2"
   browser screenshot
   ```
   用 image 工具提取正文摘要（前 500 字）
4. 采集完成后，将结果写入 `/tmp/bid_site_gz.json`：
   ```
   exec command:"cat > /tmp/bid_site_gz.json << 'JSONEOF'
   [站点 B 的 items JSON 数组]
   JSONEOF"
   ```

### 第五步：汇总结果与生成报告

1. **提取广东站 items**（如果 API 模式成功）：
   ```
   exec command:"python3 -c \"import json,pathlib; d=json.load(open('/tmp/gdgpo_raw.json','r',encoding='utf-8')); pathlib.Path('/tmp/gdgpo_items.json').write_text(json.dumps(d.get('items',[]),ensure_ascii=False,indent=2),encoding='utf-8'); print(f'提取 {len(d.get(\"items\",[]))} 条')\""
   ```

2. **合并两站数据**：
   ```
   exec command:"python3 -c \"import json,pathlib; a=json.loads(pathlib.Path('/tmp/bid_site_gz.json').read_text(encoding='utf-8')) if pathlib.Path('/tmp/bid_site_gz.json').exists() else []; b=json.loads(pathlib.Path('/tmp/gdgpo_items.json').read_text(encoding='utf-8')) if pathlib.Path('/tmp/gdgpo_items.json').exists() else []; pathlib.Path('/tmp/bid_raw.json').write_text(json.dumps(a+b,ensure_ascii=False,indent=2),encoding='utf-8'); print(f'合并: 广州站 {len(a)} 条 + 广东站 {len(b)} 条 = {len(a)+len(b)} 条')\""
   ```

3. **关键词筛选**：
   ```
   exec command:"python3 {skill_dir}/tools/keyword_filter.py --input /tmp/bid_raw.json --output /tmp/bid_filtered.json"
   ```

4. **生成 CSV**：
   ```
   exec command:"python3 {skill_dir}/tools/generate_csv.py --input /tmp/bid_filtered.json --output /tmp/bid_report.csv"
   ```

5. **生成 HTML 报告**：
   ```
   exec command:"python3 {skill_dir}/tools/generate_html.py --input /tmp/bid_raw.json --output /tmp/bid_report.html"
   ```

### 第六步：输出报告

使用 Markdown 表格展示精简结果：

```
## 招投标采集报告

| # | 来源 | 标题 | 日期 | 匹配度 |
|---|------|------|------|--------|
| 1 | 广东政府采购网 | xxx | 2026-03-10 | 高 |
| 2 | 广州体育局 | xxx | 2026-03-09 | 中 |

CSV 报告：`/tmp/bid_report.csv`
HTML 报告：`/tmp/bid_report.html`（可直接浏览器打开）
```

匹配度星级：
- 高 (score >= 0.8)
- 中 (score >= 0.5)
- 低-中 (score >= 0.2)
- 低 (score < 0.2)

## 人工接管

串行版的人工接管非常简单：主 Agent 直接在对话中通知用户，等待用户回复后继续。

**触发场景**：
- 验证码 / 滑块验证
- 需要登录
- 自动输入失败（`browser act kind:fill` 报错）

**处理流程**：

1. Agent 告知用户具体问题：
   > **{站点名称}** 遇到 {问题描述}，请在浏览器中处理，完成后回复「**好了**」，或回复「**跳过**」跳过该站点。

2. 等待用户回复：
   - 用户回复「好了」→ 重新截图确认页面状态，继续采集
   - 用户回复「跳过」→ 记录该站点为跳过，继续下一站点

3. 无需 `sessions_send`，无需 session 恢复，直接在主对话中完成。

## browser 工具用法

串行版只使用以下命令，**不带 `targetId` 参数**（单标签页模式）：

| 命令 | 用途 |
|------|------|
| `browser status` | 检查浏览器连接状态 |
| `browser navigate url:"..."` | 导航到指定 URL |
| `browser screenshot` | 截取当前页面 |
| `browser snapshot` | 获取可访问性树 |
| `browser scroll direction:down amount:800` | 向下滚动 |
| `browser click ref:"N"` | 点击元素 |

### 谨慎使用
- `browser act kind:fill ref:"{ref}" text:"..."` — 可能报错，失败后切换为人工协助输入

### 禁止使用
- `browser type` — 报 "request required"
- `browser open` — 不创建新标签页

等待页面加载用 exec：
```
exec command:"sleep 3"
```

## 容错策略

| 情况 | 处理 |
|------|------|
| 广东站 API 成功 | 直接使用 `/tmp/gdgpo_raw.json`，不启动 browser |
| 广东站 API 返回 403/429 | 脚本内部自动重试；最终失败退回 browser 兜底 |
| 广东站 API 接口变化 | 输出 `status=failed`，退回 browser 兜底 |
| 广东站 API + browser 均失败 | 记录错误，跳过继续下一站点 |
| 页面打不开 / 超时 | `sleep 5` 后重试一次，仍失败则记录错误跳过 |
| 验证码 / 滑块 | 通知用户人工处理，等待回复 |
| 需要登录 | 通知用户人工处理，等待回复 |
| 自动输入失败 | 通知用户手动输入关键词，等待回复 |
| 403 / 访问被拒 | `sleep 10` 后重试一次，仍失败记录错误跳过 |
| tipsPage 重定向 | snapshot 找关闭按钮 → click → 重新导航 |
| 搜索无结果 | 记录"搜索关键词无相关公告"，继续 |
| 浏览器未连接 | 提示用户连接，等待回复 |
| 单站点彻底失败 | 跳过，继续下一站点，**绝不终止整体任务** |

## 输出 Schema

所有站点输出统一 JSON Schema：

```json
{
  "source_site": "站点名称",
  "title": "公告标题",
  "publish_date": "YYYY-MM-DD",
  "url": "列表页 URL",
  "detail_url": "详情页 URL",
  "detail_url_status": "ok | unresolved_js_detail | failed",
  "summary": "摘要",
  "detail_text": "详情正文前 500 字",
  "purchaser": "采购人",
  "budget": "预算金额",
  "region": "地区",
  "notice_type": "公告类型",
  "match_score": 0.0,
  "match_level": "high | medium | low-medium | low",
  "match_reason": "匹配原因",
  "crawl_method": "api | browser",
  "data_quality": "high | medium | low",
  "crawl_time": "ISO 8601 时间戳"
}
```

## 当前限制

- **不支持并发**：所有站点串行执行，采集速度较慢
- **不支持子 Agent**：主 Agent 自己完成所有工作
- **不支持 session 恢复**：如果中途中断，需要从头开始
- **广州市体育局无 API 模式**：只能通过 browser 采集
- **单标签页**：每次只能操作一个页面
- **人工接管为阻塞式**：用户不回复则流程停滞
- **暂不支持增量采集**：每次运行都是全量采集
- **暂不支持自定义站点**：站点列表固定在 SKILL.md 中
