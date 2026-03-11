---
name: bid-scout
description: 招投标信息智能采集工具。当用户需要查询、采集、监控政府招投标公告（如广州体育局、广东政府采购网等）时使用此技能。支持多站点并发子 Agent 采集、关键词筛选打分、人工接管验证码/登录，输出 CSV 报告。
metadata: { "openclaw": { "emoji": "📋" } }
---

# 招投标信息智能采集 (BidScout)

## 能力范围

- **多站点并发采集**：通过 `sessions_spawn` 创建子 Agent，每个子 Agent 负责一个站点
- **标签页隔离**：主 Agent 预创建标签页并分配 `targetId`，子 Agent 在各自标签页中操作
- **智能页面解析**：browser 导航 + screenshot + image 视觉识别 + snapshot 可访问性树
- **关键词筛选打分**：体育关键词 + 服务运营关键词交叉打分
- **人工接管**：遇到验证码/登录/403 时通过 `sessions_send` 双向通信，通知用户处理
- **CSV 报告输出**：生成 Excel 兼容的 CSV 文件

## 核心原则（必须严格遵守）

⛔ **禁止事项**：
1. **禁止使用 `browser type`** — 报 "request required" 错误
2. **子 Agent 禁止使用 `browser open`** — 标签页由主 Agent 预创建并分配
3. **禁止放弃** — 单个站点失败绝不终止整个任务，跳过继续下一个

⚠️ **谨慎使用**：
- **`browser act kind:fill`** — 参数容易出错，不保证成功。仅在需要文字输入时作为**首选尝试**，失败后立即切换为人工协助输入（通知用户手动输入）

✅ **必须事项**：
- **宿主机浏览器**：通过 Chrome 扩展控制用户 Chrome，有登录态和 cookie
- **image 工具是你的眼睛**：页面内容通过 `image` 工具读取截图获取
- **标签页隔离**：子 Agent 的每一条 browser 命令都必须携带 `targetId` 参数
- **子 Agent 使用 `mode: "session"`**：以支持人工接管时的双向通信

## 目标站点

| 站点 | 入口 URL | 备用 URL | 备注 |
|------|----------|----------|------|
| 广州市体育局 | `https://tyj.gz.gov.cn/tzgg/cgzb/` | — | 天然体育相关，直接采集列表 |
| 广东省政府采购网 | `https://gdgpo.czt.gd.gov.cn/maincms-web/fullSearchingGd` | `https://gdgpo.czt.gd.gov.cn/` | 直接进入全文搜索页，搜索体育关键词；搜索页无弹窗/tipsPage 问题 |

## 工具路径

本技能附带 Python 工具，相对于 SKILL.md 所在目录：
- **关键词筛选**：`tools/keyword_filter.py`
- **CSV 生成**：`tools/generate_csv.py`
- **广东站 API 抓取**：`tools/gdgpo_api_fetch.py`（API-first 核心脚本）
- **广东站接口探测**：`tools/gdgpo_probe_api.py`（发现/验证搜索 API 端点）
- **广东站接口配置**：`config/gdgpo_api.json`（接口参数、字段映射、选择器）

调用时必须使用绝对路径，基于技能目录解析。例如：
```
exec command:"python3 {skill_dir}/tools/keyword_filter.py --input /tmp/bid_raw.json --output /tmp/bid_filtered.json"
exec command:"python3 {skill_dir}/tools/generate_csv.py --input /tmp/bid_filtered.json --output /home/node/.openclaw/workspace/bid_report.csv"
exec command:"python3 {skill_dir}/tools/gdgpo_api_fetch.py --keyword 体育 --pages 5 --config {skill_dir}/config/gdgpo_api.json --output /tmp/gdgpo_raw.json --verbose"
exec command:"python3 {skill_dir}/tools/gdgpo_probe_api.py --config {skill_dir}/config/gdgpo_api.json --output /tmp/gdgpo_probe.json --verbose"
```

> **广东省政府采购网采集策略**：优先使用 API-first 模式（通过 `gdgpo_api_fetch.py` 直接调用站点数据接口），browser 仅作为兜底方案。API 模式更稳定、精度更高、不依赖浏览器渲染状态。

## 操作流程

### 第一步：理解需求

分析用户想采集什么：
- 是否指定了站点？未指定则默认查**全部站点**
- 是否指定了关键词？未指定则使用内置体育+服务运营关键词
- 采集数量？默认每站点 **5 条**

如果需求模糊，简短确认后开始。

### 第二步：检查浏览器连接（必须！）

**Chrome relay 模式需要用户手动附加标签页。在做任何浏览器操作之前，必须先确认连接。**

首先尝试检查浏览器状态：
```
browser status
```

如果返回错误或显示未连接，**立即告知用户**：

> 📌 **需要连接浏览器**
>
> 请在 Chrome 浏览器中：
> 1. 打开任意网页
> 2. 点击工具栏上的 **OpenClaw Browser Relay** 扩展图标
> 3. 确保图标徽章显示为 **ON**
> 4. 回复「**好了**」
>
> 连接成功后我会自动开始采集。

**等待用户回复「好了」后才继续下一步。不要在浏览器未连接时创建子 Agent！**

### 第三步：预创建标签页并获取 targetId（主 Agent 执行）

浏览器已连接后，**在创建子 Agent 之前**，主 Agent 先为每个站点打开独立标签页。

**第一个标签页**（广州市体育局）：
```
browser navigate url:"https://tyj.gz.gov.cn/tzgg/cgzb/"
```
→ 从返回结果中提取 `targetId` 字段（如 `"AAA111..."`），记为 **targetId_A**

```
exec command:"sleep 2"
```

**第二个标签页**（广东省政府采购网 — 全文搜索页）：
```
browser open url:"https://gdgpo.czt.gd.gov.cn/maincms-web/fullSearchingGd"
```
→ 从返回结果中提取 `targetId` 字段（如 `"BBB222..."`），记为 **targetId_B**

```
exec command:"sleep 3"
```

**搜索页状态验证**：
```
browser screenshot targetId:"{targetId_B}"
```
用 image 工具确认页面是全文搜索页（应显示搜索框、筛选条件等，无弹窗覆盖）。

> **与首页的区别**：搜索页 `fullSearchingGd` 不存在首页的 tipsPage 重定向和「服务指引」弹窗问题，页面直接加载为搜索界面。

**⚠️ 异常处理**（低概率）：
- 如果 URL 被重定向到了 tipsPage → snapshot 找关闭按钮 → click → 重新 navigate 到搜索页 URL
- 如果页面显示 403/空白 → exec command:"sleep 10" → 重试导航

**⚠️ 如果 `browser open` 失败**（报 "tab not found" 等错误）：
放弃多标签页方案，直接跳转到「降级策略：顺序执行模式」章节。在单标签页中先采集站点 A，完成后再采集站点 B。

**验证两个 targetId 都获取成功后**，才继续创建子 Agent。

### 第四步：创建子 Agent（使用 `mode: "session"`）

使用 `sessions_spawn` 为每个站点创建独立的子 Agent。**必须使用 `mode: "session"`**，以支持人工接管时主 Agent 向子 Agent 发送后续指令。

**创建子 Agent A（广州市体育局）**：

```
sessions_spawn task:"你是招投标信息采集子 Agent。你的任务是从广州市体育局网站采集最新的招投标公告。

【标签页绑定】
你的专属标签页 targetId 为：{targetId_A}
⚠️ 你的每一条 browser 命令都必须携带 targetId:\"{targetId_A}\" 参数！
例如：
  browser navigate url:\"...\" targetId:\"{targetId_A}\"
  browser screenshot targetId:\"{targetId_A}\"
  browser snapshot targetId:\"{targetId_A}\"
  browser scroll direction:down amount:800 targetId:\"{targetId_A}\"
  browser click ref:\"N\" targetId:\"{targetId_A}\"

如果不带 targetId，操作可能会跑到其他标签页上！

【目标站点】
- 名称：广州市体育局
- 入口 URL：https://tyj.gz.gov.cn/tzgg/cgzb/

【采集步骤】
1. 页面已由主 Agent 预加载，直接开始：
   browser screenshot targetId:\"{targetId_A}\"
   用 image 工具判断页面状态
2. 如果页面正常：
   a. browser snapshot targetId:\"{targetId_A}\" 获取可访问性树
   b. 用 image 工具读取截图，提取列表中的公告标题、发布日期、链接
   c. 对前 5 条公告，逐个 browser navigate url:\"详情URL\" targetId:\"{targetId_A}\" 进入详情页
   d. 每个详情页：browser screenshot targetId:\"{targetId_A}\" → image 提取正文摘要（前 500 字）
   e. 每次操作后 exec command:\"sleep 2\"
3. 如果遇到验证码/滑块：
   在你的回复中说明「⚠️ 广州市体育局: 检测到验证码，需要人工处理」
   然后 exec command:\"sleep 30\" 等待 30 秒
   之后重新 browser screenshot targetId:\"{targetId_A}\" 检查页面状态
   如果仍然有验证码，再等 30 秒重试一次（最多重试 2 次）
   如果主 Agent 向你发送了「继续」消息，立即重新检查页面并继续采集
4. 如果遇到登录页：同验证码处理，说明「需要登录」
5. 如果遇到 403/访问被拒：exec command:\"sleep 10\"，然后重试一次

【数据格式】
采集完成后，将结果以如下 JSON 格式在你的最终回复中输出：
```json
{
  \"status\": \"completed\",
  \"site\": \"广州市体育局\",
  \"items\": [
    {
      \"source_site\": \"广州市体育局\",
      \"title\": \"公告标题\",
      \"publish_date\": \"YYYY-MM-DD\",
      \"url\": \"完整 URL\",
      \"summary\": \"正文摘要前 500 字\",
      \"detail_text\": \"详情正文前 500 字\"
    }
  ],
  \"errors\": []
}
```

【注意事项】
- 每条 browser 命令必须带 targetId:\"{targetId_A}\"
- 最多采集 5 条
- 单条失败不影响其他条目
- browser 工具只用 navigate/screenshot/snapshot/scroll/click
- 禁止使用 browser open（标签页已分配给你）" label:"bid-scout-gz-tyj" mode:"session"
```

**创建子 Agent B（广东省政府采购网 — API-first 模式）**：

```
sessions_spawn task:"你是招投标信息采集子 Agent。你的任务是从广东省政府采购网采集与**体育**相关的招投标公告。

**广东省政府采购网优先使用 API-first 模式，browser 仅为兜底方案。**

【标签页绑定】
你的专属标签页 targetId 为：{targetId_B}
⚠️ 仅在 browser 兜底时使用。每条 browser 命令必须携带 targetId:\"{targetId_B}\" 参数。

【目标站点】
- 名称：广东省政府采购网
- 入口 URL：https://gdgpo.czt.gd.gov.cn/maincms-web/fullSearchingGd（全文搜索页）

【采集步骤 — 阶段 1：API-first（优先执行）】

直接通过 Python 脚本调用站点数据接口，无需浏览器交互：

1. 执行 API 抓取：
   exec command:\"python3 {skill_dir}/tools/gdgpo_api_fetch.py --keyword 体育 --pages 5 --page-size 10 --config {skill_dir}/config/gdgpo_api.json --output /tmp/gdgpo_raw.json --verbose\"

2. 检查执行结果：
   exec command:\"cat /tmp/gdgpo_raw.json | head -c 500\"
   在输出中查看 status 和 items 数量。

3. 判断结果：
   - 输出中 status 为 \"completed\" 或 \"partial\" 且 items 非空数组 → API 采集成功，跳到【输出数据】
   - status 为 \"failed\" 或 items 为空数组 → 进入阶段 2（browser 兜底）

【采集步骤 — 阶段 2：browser 兜底（仅在 API 失败时执行）】

⚠️ 此阶段仅在阶段 1 API 抓取失败时才进入。browser 兜底目标是临时救场或确认是否存在验证码/登录/403。
⚠️ browser 兜底不作为主力提取手段，只提取有限数据供参考。

第一步：确认页面状态
1. browser screenshot targetId:\"{targetId_B}\"
   exec command:\"sleep 2\"
2. 用 image 工具判断页面状态：
   - 正常搜索页（看到搜索框和搜索按钮）→ 继续第二步
   - tipsPage 重定向 → browser snapshot targetId:\"{targetId_B}\" → 找关闭按钮 ref → browser click ref:\"{关闭ref}\" targetId:\"{targetId_B}\" → browser navigate url:\"https://gdgpo.czt.gd.gov.cn/maincms-web/fullSearchingGd\" targetId:\"{targetId_B}\"
   - 403/空白 → exec command:\"sleep 10\" → browser navigate 重试一次
   - 验证码/登录 → 在回复中说明「⚠️ 广东省政府采购网: 检测到验证码/需要登录，需要人工处理」→ exec command:\"sleep 30\" → 等待主 Agent 发送继续消息

第二步：执行搜索
1. browser snapshot targetId:\"{targetId_B}\" 获取可访问性树
   exec command:\"sleep 1\"
2. 在树中找到搜索输入框的 ref（placeholder 包含「查询」或「搜索」的 input 元素）
3. browser click ref:\"{搜索框ref}\" targetId:\"{targetId_B}\"
   exec command:\"sleep 1\"
4. 尝试输入：browser act kind:fill ref:\"{搜索框ref}\" text:\"体育\" targetId:\"{targetId_B}\"
   exec command:\"sleep 1\"
5. browser screenshot targetId:\"{targetId_B}\" → 用 image 确认搜索框中是否出现「体育」
   - 如果搜索框为空或 fill 报错 → 在回复中说明「⚠️ 广东省政府采购网: 自动输入失败，请在搜索框中手动输入"体育"并点击搜索，完成后回复"好了"」→ exec command:\"sleep 30\" → 等待继续消息
6. 在 snapshot 中找到搜索按钮（文字「搜索」）的 ref
7. browser click ref:\"{搜索按钮ref}\" targetId:\"{targetId_B}\"
   exec command:\"sleep 5\"
8. browser screenshot targetId:\"{targetId_B}\" → image 确认是否出现搜索结果列表

第三步：提取结果
1. browser screenshot targetId:\"{targetId_B}\"
   用 image 工具读取可见的搜索结果，提取每条的标题、发布日期
2. browser snapshot targetId:\"{targetId_B}\"
   从可访问性树中提取结果链接的 href（用于后续导航到详情页）
3. 对前 5 条体育相关公告逐个提取详情：
   a. browser navigate url:\"详情页URL\" targetId:\"{targetId_B}\"
      exec command:\"sleep 3\"
   b. browser screenshot targetId:\"{targetId_B}\" → image 提取标题、日期、采购人、预算、正文前 500 字
   c. exec command:\"sleep 2\"
4. 如果不足 5 条，尝试翻页（最多 2 次）：
   browser snapshot targetId:\"{targetId_B}\" → 找「下一页」按钮 ref → browser click ref:\"{下一页ref}\" targetId:\"{targetId_B}\" → exec command:\"sleep 3\" → 重复提取

【输出数据】

如果 API 模式成功，读取 /tmp/gdgpo_raw.json 内容作为最终输出。

如果 browser 兜底模式，将结果以如下 JSON 格式输出：
```json
{
  \"status\": \"completed\",
  \"site\": \"广东省政府采购网\",
  \"items\": [
    {
      \"source_site\": \"广东省政府采购网\",
      \"title\": \"公告标题\",
      \"publish_date\": \"YYYY-MM-DD\",
      \"url\": \"完整 URL\",
      \"summary\": \"正文摘要前 500 字\",
      \"detail_text\": \"详情正文前 500 字\"
    }
  ],
  \"errors\": []
}
```
如果没有找到体育相关公告，items 为空数组，在 errors 中说明原因。

【注意事项】
- API-first 模式不需要 browser 操作，直接通过 exec 执行 Python 脚本
- browser 兜底时每条命令必须带 targetId:\"{targetId_B}\"
- 最多采集 5 条体育相关公告
- 单条失败不影响其他条目
- 禁止使用 browser open（标签页已分配给你）
- 禁止使用 browser type（报 request required 错误）" label:"bid-scout-gdgpo" mode:"session"
```

**⚠️ 记录两个子 Agent 的 `runId`**，后续人工接管时需要用 `sessions_send` 向子 Agent 发消息。

### 第五步：监控子 Agent 并处理人工接管

两个子 Agent 并发执行。主 Agent 需要**主动监控**子 Agent 的状态。

**人工接管通信流程**：

```
子 Agent 检测到验证码 → 输出"需要人工处理" → sleep 30 等待
         ↓
主 Agent 收到 announce → 转发给用户
         ↓
用户在浏览器中处理验证码 → 回复"好了"
         ↓
主 Agent 用 sessions_send 向子 Agent 发送"继续"
         ↓
子 Agent 收到消息 → 重新检查页面 → 继续采集
```

具体操作：

1. **等待子 Agent announce**。当你收到子 Agent 的消息时，检查内容：
   - 如果包含「需要人工处理」「验证码」「需要登录」→ 转入人工接管流程
   - 如果包含完整的 JSON 结果 → 该站点采集完成

2. **人工接管流程**：
   a. 告诉用户哪个站点遇到了什么问题，例如：
      > ⚠️ **广州市体育局**遇到验证码，请在浏览器中完成验证，完成后回复"**好了**"，或回复"**跳过**"。
   b. 等待用户回复
   c. 如果用户回复「好了」→ 使用 `sessions_send` 向对应子 Agent 发送继续指令：
      ```
      sessions_send sessionKey:"agent::subagent:{runId_A}" message:"用户已处理完毕，请重新检查页面状态并继续采集任务。"
      ```
   d. 如果用户回复「跳过」→ 记录该站点为跳过状态，不再等待该子 Agent

3. **超时处理**：如果子 Agent 超过 5 分钟没有 announce，认为超时，跳过继续。

### 第六步：汇总结果与生成报告

收到所有子 Agent 的最终结果后：

1. **合并数据**：
   - 广州市体育局：从子 Agent A 的回复中提取 JSON，用 cat heredoc 写入 `/tmp/bid_site_a.json`
   - 广东省政府采购网：
     - 如果 API 模式成功，`/tmp/gdgpo_raw_items.json` 已自动生成（由 gdgpo_api_fetch.py 输出）
     - 如果 browser 兜底模式，从子 Agent B 的回复中提取 JSON，写入 `/tmp/bid_site_b.json`

2. **写入站点 A 数据**（从子 Agent A 回复中提取的 items 数组）：
```
exec command:"cat > /tmp/bid_site_a.json << 'JSONEOF'
[站点 A 的 items JSON 数组]
JSONEOF"
```

3. **合并两站数据并筛选**：
```
exec command:"python3 {skill_dir}/tools/keyword_filter.py --input /tmp/gdgpo_raw_items.json --output /tmp/gdgpo_filtered.json"
exec command:"python3 {skill_dir}/tools/keyword_filter.py --input /tmp/bid_site_a.json --output /tmp/site_a_filtered.json"
```

> 如需合并为单个文件再统一筛选：
> ```
> exec command:"python3 -c 'import json, pathlib; a=json.loads(pathlib.Path(\"/tmp/bid_site_a.json\").read_text(encoding=\"utf-8\")); b=json.loads(pathlib.Path(\"/tmp/gdgpo_raw_items.json\").read_text(encoding=\"utf-8\")) if pathlib.Path(\"/tmp/gdgpo_raw_items.json\").exists() else []; pathlib.Path(\"/tmp/bid_raw.json\").write_text(json.dumps(a+b,ensure_ascii=False),encoding=\"utf-8\")'"
> exec command:"python3 {skill_dir}/tools/keyword_filter.py --input /tmp/bid_raw.json --output /tmp/bid_filtered.json"
> ```

4. **生成 CSV**：
```
exec command:"python3 {skill_dir}/tools/generate_csv.py --input /tmp/bid_filtered.json --output /home/node/.openclaw/workspace/bid_report.csv"
```

5. **清理标签页**（可选）：
```
browser close targetId:"{targetId_A}"
browser close targetId:"{targetId_B}"
```

6. **向用户报告**：
   - 输出采集摘要（各站点采集数量、成功/失败状态）
   - 输出高匹配度条目的标题和分数
   - 告知 CSV 文件路径

### 第七步：报告格式

向用户回复时，使用 Markdown 表格展示精简结果：

```
## 📋 招投标采集报告

| # | 来源 | 标题 | 日期 | 匹配度 |
|---|------|------|------|--------|
| 1 | 广州体育局 | xxx | 2026-03-10 | ★★★ 高 |
| 2 | 广东政府采购网 | xxx | 2026-03-09 | ★★ 中 |

📄 完整报告：`/home/node/.openclaw/workspace/bid_report.csv`
```

匹配度星级：
- ★★★ 高 (score >= 0.8)
- ★★ 中 (score >= 0.5)
- ★ 低-中 (score >= 0.2)
- 无星 (score < 0.2)

## browser 工具用法

### 主 Agent 可用命令

1. **打开新标签页**：`browser open url:"https://..."` → 获取 `targetId`
2. **关闭标签页**：`browser close targetId:"..."`
3. **列出标签页**：`browser tabs`

### 子 Agent 可用命令（每条必须带 `targetId`）

1. **导航**：`browser navigate url:"https://..." targetId:"{targetId}"`
2. **截图**：`browser screenshot targetId:"{targetId}"`
3. **可访问性树**：`browser snapshot targetId:"{targetId}"`
4. **滚动**：`browser scroll direction:down amount:800 targetId:"{targetId}"`
5. **点击**：`browser click ref:"N" targetId:"{targetId}"`

等待页面加载用 exec，不要用 browser 的 sleep：
```
exec command:"sleep 3"
```

### ⛔ 禁止使用的命令
- `browser type` — 报 "request required"
- 子 Agent 禁止 `browser open`（标签页由主 Agent 管理）

### ⚠️ 谨慎使用的命令
- `browser act kind:fill ref:"{ref}" text:"..."` — 参数容易出错（可能报 "fields are required"），仅在需要文字输入时尝试，失败后切换为人工协助

## 容错策略

| 情况 | 处理 |
|------|------|
| **广东站 API 抓取成功** | 直接使用 `/tmp/gdgpo_raw.json` 结果，不启动 browser |
| **广东站 API 返回 403/429** | API 脚本内部自动重试；最终失败则退回 browser 兜底 |
| **广东站 API 接口变化/JSON 解析失败** | 输出 status=failed 的结构化 JSON，退回 browser 兜底 |
| **广东站 API + browser 均失败** | 记录错误，跳过继续采集其他站点 |
| 搜索无结果 | 记录"该站点搜索关键词无相关公告"，继续 |
| 自动输入失败（fill 命令报错） | 切换为人工协助输入：announce 通知主 Agent → 用户手动输入关键词 → `sessions_send` 继续 |
| 搜索超时（点击搜索后长时间无结果） | sleep 5 后重新截图检查；如仍无结果，重新导航到搜索页重试一次 |
| 登录页 | 子 Agent announce → 主 Agent 通知用户 → `sessions_send` 继续 |
| 验证码/滑块 | 子 Agent announce → 主 Agent 通知用户 → `sessions_send` 继续 |
| 403/访问被拒 | sleep 10 重试 → 尝试备用首页 URL `https://gdgpo.czt.gd.gov.cn/` → 记录失败 |
| tipsPage 重定向（搜索页低概率） | screenshot + snapshot 找关闭按钮 → click → 重新导航到搜索页 |
| 浏览器报错 | 重试 2 次，仍失败记录错误 |
| 单站点彻底失败 | **绝不终止任务**，跳过继续 |
| 子 Agent 超时 | 5 分钟无 announce → 记录超时，使用已有结果继续 |
| `browser open` 失败 | 改用 `browser navigate` 在当前标签页导航，然后顺序而非并发执行 |

## 降级策略：顺序执行模式

当以下任一情况发生时，放弃子 Agent 并发模式，切换为顺序执行：
- `browser open` 报错（如 "tab not found"）
- 只获取到一个 `targetId`
- 浏览器连接不稳定

**顺序执行流程**：

1. **不创建子 Agent**，主 Agent 自己依次采集
2. 在当前标签页中采集站点 A（广州体育局）：
   - `browser navigate url:"https://tyj.gz.gov.cn/tzgg/cgzb/"`
   - screenshot → image 识别 → snapshot → 提取数据
   - 逐个进入详情页提取摘要
3. 采集完站点 A 后，`exec command:"sleep 3"`
4. 采集站点 B（广东政府采购网）— **API-first 模式**：
   - 首先尝试 API 抓取：
     `exec command:"python3 {skill_dir}/tools/gdgpo_api_fetch.py --keyword 体育 --pages 5 --config {skill_dir}/config/gdgpo_api.json --output /tmp/gdgpo_raw.json --verbose"`
   - 检查 `/tmp/gdgpo_raw.json` 中 `status` 和 `items` 数量
   - 如果 API 成功（items 非空）→ 直接使用 API 结果，跳到步骤 6
   - 如果 API 失败 → 退回 browser 兜底：
     - `browser navigate url:"https://gdgpo.czt.gd.gov.cn/maincms-web/fullSearchingGd"`
     - screenshot 确认页面状态
     - snapshot 找输入框 → 尝试 fill → 如失败则人工协助
     - browser 兜底只做基本提取，不依赖 image 做主力
5. 人工接管直接在主会话中进行（无需 sessions_send）
6. 采集完成后，合并结果 → keyword_filter.py → generate_csv.py → 报告用户

顺序模式下人工接管更简单：主 Agent 直接告知用户，等用户回复后继续。
广东站 API 模式下无需人工接管，仅 browser 兜底时可能需要。

## 注意事项

- 每次页面操作后间隔 2-3 秒
- 截图路径从 `MEDIA:` 行提取，image 工具使用该路径读取
- Python 工具路径基于 SKILL.md 所在目录解析为绝对路径
- 如果用户只想查某一个站点，只创建对应的一个子 Agent 即可
- CSV 使用 `utf-8-sig` 编码，确保 Excel 正确显示中文
- `sessions_send` 的 `sessionKey` 格式为 `agent::subagent:{runId}`，`runId` 来自 `sessions_spawn` 的返回
