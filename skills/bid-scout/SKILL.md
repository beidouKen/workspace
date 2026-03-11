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
1. **禁止使用 `browser act kind:fill`** — 参数容易出错
2. **禁止使用 `browser type`** — 报 "request required" 错误
3. **子 Agent 禁止使用 `browser open`** — 标签页由主 Agent 预创建并分配
4. **禁止放弃** — 单个站点失败绝不终止整个任务，跳过继续下一个

✅ **必须事项**：
- **宿主机浏览器**：通过 Chrome 扩展控制用户 Chrome，有登录态和 cookie
- **image 工具是你的眼睛**：页面内容通过 `image` 工具读取截图获取
- **标签页隔离**：子 Agent 的每一条 browser 命令都必须携带 `targetId` 参数
- **子 Agent 使用 `mode: "session"`**：以支持人工接管时的双向通信

## 目标站点

| 站点 | 入口 URL | 备用 URL | 备注 |
|------|----------|----------|------|
| 广州市体育局 | `https://tyj.gz.gov.cn/tzgg/cgzb/` | — | 天然体育相关，直接采集列表 |
| 广东省政府采购网 | `https://gdgpo.czt.gd.gov.cn/` | — | 从首页「项目采购公告」板块进入；公告量大需筛选体育关键词 |

## 工具路径

本技能附带 Python 工具，相对于 SKILL.md 所在目录：
- **关键词筛选**：`tools/keyword_filter.py`
- **CSV 生成**：`tools/generate_csv.py`

调用时必须使用绝对路径，基于技能目录解析。例如：
```
exec command:"python3 {skill_dir}/tools/keyword_filter.py --input /tmp/bid_raw.json --output /tmp/bid_filtered.json"
exec command:"python3 {skill_dir}/tools/generate_csv.py --input /tmp/bid_filtered.json --output /home/node/.openclaw/workspace/bid_report.csv"
```

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

**第二个标签页**（广东省政府采购网）：
```
browser open url:"https://gdgpo.czt.gd.gov.cn/"
```
→ 从返回结果中提取 `targetId` 字段（如 `"BBB222..."`），记为 **targetId_B**

**⚠️ 首页弹窗 / tipsPage 处理**（广东省政府采购网特有）：

该站点有两种可能的阻挡情况，需按顺序检查：

**情况 A：tipsPage 重定向**
检查 `browser open` 返回的 `url` 字段。如果 URL 包含 `tipsPage`，说明被重定向到了系统提示页。处理步骤：

1. 截图 + snapshot 查找关闭/确定按钮：
```
browser screenshot targetId:"{targetId_B}"
browser snapshot targetId:"{targetId_B}"
```
找到按钮 ref → 点击关闭：
```
browser click ref:"N" targetId:"{targetId_B}"
exec command:"sleep 2"
```

2. 关闭提示后重新导航到首页：
```
browser navigate url:"https://gdgpo.czt.gd.gov.cn/" targetId:"{targetId_B}"
exec command:"sleep 3"
```

**情况 B：首页「服务指引」通知弹窗（高概率出现）**
即使没有 tipsPage 重定向，首页加载后通常会弹出一个 **「广东政府采购智慧云平台服务指引」** 通知弹窗（class: `mainNoticeBox`），覆盖整个页面。**必须关闭此弹窗才能操作首页内容。**

弹窗 HTML 结构：
```html
<div class="mainNoticeBox">
  <div class="mainNotice">
    <div class="noticeContent">...</div>
    <div class="noticeCloseBtn">x</div>  <!-- 关闭按钮，文字是 "x" -->
  </div>
</div>
```

处理步骤：
1. 截图确认弹窗存在：
```
browser screenshot targetId:"{targetId_B}"
```
2. 获取 snapshot 查找关闭按钮（文字为 **"x"**，class 为 `noticeCloseBtn`）：
```
browser snapshot targetId:"{targetId_B}"
```
3. 在 snapshot 中找到文字为 "x" 且位于通知弹窗内的元素 ref，点击关闭：
```
browser click ref:"{关闭按钮ref}" targetId:"{targetId_B}"
exec command:"sleep 2"
```
4. 再次截图确认弹窗已关闭、首页内容可见：
```
browser screenshot targetId:"{targetId_B}"
```

**⚠️ 重要：弹窗关闭按钮文字是小写 "x"，不是"关闭"、"确定"或"我知道了"。在 snapshot 中搜索文本 "x" 或 class 包含 "close"/"Close" 的元素。**

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

**创建子 Agent B（广东省政府采购网）**：

```
sessions_spawn task:"你是招投标信息采集子 Agent。你的任务是从广东省政府采购网采集与**体育**相关的招投标公告。

【标签页绑定】
你的专属标签页 targetId 为：{targetId_B}
⚠️ 你的每一条 browser 命令都必须携带 targetId:\"{targetId_B}\" 参数！
例如：
  browser navigate url:\"...\" targetId:\"{targetId_B}\"
  browser screenshot targetId:\"{targetId_B}\"
  browser snapshot targetId:\"{targetId_B}\"
  browser scroll direction:down amount:800 targetId:\"{targetId_B}\"
  browser click ref:\"N\" targetId:\"{targetId_B}\"

如果不带 targetId，操作可能会跑到其他标签页上！

【目标站点】
- 名称：广东省政府采购网
- 入口 URL：https://gdgpo.czt.gd.gov.cn/（首页）

【⚠️ tipsPage / 服务指引弹窗处理（该站点特有）】

该站点有两种阻挡情况：

**情况 A：tipsPage 重定向**
如果截图发现当前在 tipsPage 提示页：
1. browser snapshot targetId:\"{targetId_B}\" 查找关闭/确定按钮
2. browser click ref:\"对应按钮ref\" targetId:\"{targetId_B}\" 关闭提示
3. exec command:\"sleep 2\"
4. browser navigate url:\"https://gdgpo.czt.gd.gov.cn/\" targetId:\"{targetId_B}\"

**情况 B：首页「服务指引」通知弹窗（高概率出现）**
首页加载后通常会出现「广东政府采购智慧云平台服务指引」通知弹窗，覆盖整个页面。
弹窗结构：class=\"mainNoticeBox\" 包含 class=\"noticeCloseBtn\" 的关闭按钮，按钮文字为 **\"x\"**。
处理步骤：
1. browser snapshot targetId:\"{targetId_B}\" 在元素树中查找文本为 \"x\" 的元素（class 包含 noticeCloseBtn 或 close）
2. browser click ref:\"该元素的ref\" targetId:\"{targetId_B}\"
3. exec command:\"sleep 2\"
4. browser screenshot targetId:\"{targetId_B}\" 确认弹窗已关闭
⚠️ 关闭按钮文字是小写 \"x\"，不是「关闭」「确定」「我知道了」！

【采集步骤】

第一步：确认页面状态
1. browser screenshot targetId:\"{targetId_B}\"
   用 image 工具判断当前页面是什么：
   - 首页门户（有多个板块：通知公告、项目采购公告等）→ 进入第二步
   - tipsPage 提示页 → 按上面的 tipsPage 处理步骤关闭，然后重新截图
   - 首页但有「服务指引」弹窗覆盖（看到 mainNoticeBox 或大段服务指引文字）→ 按情况 B 处理：snapshot 找 \"x\" 按钮 → click 关闭 → 重新截图
   - 403/空白/错误 → exec command:\"sleep 10\"，重新导航到首页重试
   - 验证码/登录页 → 说明「⚠️ 广东省政府采购网: 检测到验证码/需要登录，需要人工处理」，然后 exec command:\"sleep 30\" 等待

第二步：从首页「项目采购公告」板块采集
（首页有多个板块，重点关注「项目采购公告」区域）

1. browser screenshot targetId:\"{targetId_B}\"
   用 image 工具读取首页内容，识别「项目采购公告」板块的位置
   该板块通常包含：省级/市级/县区级标签页切换、采购公告/中标结果等子标签、最新公告列表（标题+日期）、[MORE] 链接

2. browser snapshot targetId:\"{targetId_B}\" 获取元素树
   在元素树中查找「项目采购公告」板块的内容

3. 读取板块中展示的公告列表（通常 10-20 条），从中筛选标题包含以下关键词的条目：
   「体育」「运动」「健身」「场馆」「赛事」「全民健身」「体育局」「体育中心」

4. 如果首页可见公告中没有体育相关条目，尝试点击 [MORE] 链接查看更多：
   browser click ref:\"MORE链接ref\" targetId:\"{targetId_B}\"
   exec command:\"sleep 3\"
   - 如果 MORE 链接指向了采购公告列表页且能正常加载 → 进入第三步
   - 如果跳转失败或又到了 tipsPage → 回到首页继续

5. 如果首页展示了「服务指引」弹窗/覆盖层（class: mainNoticeBox），通过 snapshot 找到文本为 \"x\" 的 noticeCloseBtn 元素并点击关闭

第三步：在公告列表页翻页浏览（如果成功进入）

如果通过 MORE 链接成功进入了公告列表页：
1. browser screenshot targetId:\"{targetId_B}\" + image 读取当前可见公告
2. browser scroll direction:down amount:800 targetId:\"{targetId_B}\" 翻页
   exec command:\"sleep 2\"
   browser screenshot targetId:\"{targetId_B}\" + image 继续读取
3. 重复翻页 2-3 次，收集尽可能多的公告标题
4. 从中筛选体育相关条目

第四步：进入详情页提取摘要

对筛选出的体育相关公告（最多 5 条），逐个：
1. browser navigate url:\"详情页URL\" targetId:\"{targetId_B}\"
   exec command:\"sleep 2\"
2. browser screenshot targetId:\"{targetId_B}\" → image 提取正文摘要（前 500 字）
3. 记录数据后继续下一条

如果全程没有找到体育相关公告，记录「该站点近期无体育相关采购公告」

【数据格式】
采集完成后，将结果以如下 JSON 格式在你的最终回复中输出：
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
- 每条 browser 命令必须带 targetId:\"{targetId_B}\"
- 最多采集 5 条体育相关公告
- 该站点公告量大，大部分不是体育相关，需主动从标题中筛选
- 单条失败不影响其他条目
- browser 工具只用 navigate/screenshot/snapshot/scroll/click
- 禁止使用 browser open（标签页已分配给你）
- 每次操作后 exec command:\"sleep 2\"
- 遇到 tipsPage 不要误判为「网站维护中」，关闭提示后导航到首页继续
- 遇到「服务指引」弹窗（mainNoticeBox），通过 snapshot 找文本为 'x' 的 noticeCloseBtn 元素并点击关闭
- 弹窗关闭按钮文字是小写 'x'，不是'关闭'或'确定'" label:"bid-scout-gdgpo" mode:"session"
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

1. **合并数据**：将两个站点的 items 合并为一个 JSON 数组

2. **写入临时文件**：
```
exec command:"cat > /tmp/bid_raw.json << 'JSONEOF'
[合并后的 JSON 数组]
JSONEOF"
```

3. **关键词筛选**：
```
exec command:"python3 {skill_dir}/tools/keyword_filter.py --input /tmp/bid_raw.json --output /tmp/bid_filtered.json"
```

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
- `browser act kind:fill` — 报 "fields are required"
- `browser type` — 报 "request required"
- 子 Agent 禁止 `browser open`（标签页由主 Agent 管理）

## 容错策略

| 情况 | 处理 |
|------|------|
| 搜索无结果 | 记录"该站点无相关公告"，继续 |
| 登录页 | 子 Agent announce → 主 Agent 通知用户 → `sessions_send` 继续 |
| 验证码/滑块 | 子 Agent announce → 主 Agent 通知用户 → `sessions_send` 继续 |
| 403/访问被拒 | sleep 10 重试 → 尝试首页备用 URL → 记录失败 |
| tipsPage 重定向 | screenshot + snapshot 找关闭按钮 → click → 重新导航到目标页 |
| 首页「服务指引」弹窗 | snapshot 找文本为 "x" 的 noticeCloseBtn 元素 → click 关闭（class: mainNoticeBox） |
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
4. 在同一标签页中采集站点 B（广东政府采购网）：
   - `browser navigate url:"https://gdgpo.czt.gd.gov.cn/"`
   - 如跳转到 tipsPage → snapshot 找关闭按钮 → click → 重新导航到首页
   - 如首页出现「服务指引」弹窗（mainNoticeBox）→ snapshot 找文本 "x" 的 noticeCloseBtn → click 关闭
   - 从首页「项目采购公告」板块浏览，筛选体育相关公告
   - 同样的 screenshot → image → snapshot 流程
5. 人工接管直接在主会话中进行（无需 sessions_send）
6. 采集完成后，合并结果 → keyword_filter.py → generate_csv.py → 报告用户

顺序模式下人工接管更简单：主 Agent 直接告知用户，等用户回复后继续。

## 注意事项

- 每次页面操作后间隔 2-3 秒
- 截图路径从 `MEDIA:` 行提取，image 工具使用该路径读取
- Python 工具路径基于 SKILL.md 所在目录解析为绝对路径
- 如果用户只想查某一个站点，只创建对应的一个子 Agent 即可
- CSV 使用 `utf-8-sig` 编码，确保 Excel 正确显示中文
- `sessions_send` 的 `sessionKey` 格式为 `agent::subagent:{runId}`，`runId` 来自 `sessions_spawn` 的返回
