---
name: bid-scout
description: 招投标信息智能采集工具。当用户需要查询、采集、监控政府招投标公告（如广州体育局、广东政府采购网等）时使用此技能。支持多站点并发子 Agent 采集、关键词筛选打分、人工接管验证码/登录，输出 CSV 报告。
metadata: { "openclaw": { "emoji": "📋" } }
---

# 招投标信息智能采集 (BidScout)

## 能力范围

- **多站点并发采集**：通过 `sessions_spawn` 创建子 Agent，每个子 Agent 负责一个站点
- **智能页面解析**：browser 导航 + screenshot + image 视觉识别 + snapshot 可访问性树
- **关键词筛选打分**：体育关键词 + 服务运营关键词交叉打分
- **人工接管**：遇到验证码/登录/403 时通知用户处理
- **CSV 报告输出**：生成 Excel 兼容的 CSV 文件

## 核心原则（必须严格遵守）

⛔ **禁止事项**：
1. **禁止使用 `browser act kind:fill`** — 参数容易出错
2. **禁止使用 `browser type`** — 报 "request required" 错误
3. **禁止使用 `browser open`** — 会打开新标签页导致 tab not found
4. **禁止放弃** — 单个站点失败绝不终止整个任务，跳过继续下一个

✅ **必须事项**：
- **宿主机浏览器**：通过 Chrome 扩展控制用户 Chrome，有登录态和 cookie
- **image 工具是你的眼睛**：页面内容通过 `image` 工具读取截图获取
- **两个站点之间间隔 3 秒**（`sleep 3`），避免并发操作冲突
- **browser 工具只用这 5 个命令**：`navigate`、`screenshot`、`snapshot`、`scroll`、`click`

## 目标站点

| 站点 | 入口 URL | 备用 URL |
|------|----------|----------|
| 广州市体育局 | `https://tyj.gz.gov.cn/tzgg/cgzb/` | — |
| 广东省政府采购网 | `https://gdgpo.czt.gd.gov.cn/cms-gd/site/guangdong/cggg/index.html` | `https://gdgpo.czt.gd.gov.cn/freecms/site/guangdong/wlzfcgxx/index.html`、`https://gdgpo.czt.gd.gov.cn/` |

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

### 第二步：创建子 Agent

使用 `sessions_spawn` 为每个站点创建独立的子 Agent。两个子 Agent **并发执行**。

**创建子 Agent A（广州市体育局）**：

```
sessions_spawn task:"你是招投标信息采集子 Agent。你的任务是从广州市体育局网站采集最新的招投标公告。

【目标站点】
- 名称：广州市体育局
- 入口 URL：https://tyj.gz.gov.cn/tzgg/cgzb/

【采集步骤】
1. browser navigate url:\"https://tyj.gz.gov.cn/tzgg/cgzb/\"
2. exec command:\"sleep 3\"
3. browser screenshot → 用 image 工具判断页面状态
4. 如果页面正常：
   a. 用 browser snapshot 获取可访问性树
   b. 用 image 工具读取截图，提取列表中的公告标题、发布日期、链接
   c. 对前 5 条公告，逐个 browser navigate 进入详情页
   d. 每个详情页：browser screenshot → image 提取正文摘要（前 500 字）
5. 如果遇到验证码/滑块：告诉用户「检测到验证码，请在浏览器中完成验证，完成后回复 好了」，然后停止等用户回复
6. 如果遇到登录页：告诉用户「需要登录，请在浏览器中登录，完成后回复 好了，或回复 跳过」
7. 如果遇到 403/访问被拒：exec command:\"sleep 10\"，然后重试一次，仍然失败则记录错误

【数据格式】
采集完成后，将结果以如下 JSON 格式 announce 回主会话：
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

【注意事项】
- 每次页面操作后 sleep 2 秒
- 最多采集 5 条
- 单条失败不影响其他条目
- browser 工具只用 navigate/screenshot/snapshot/scroll/click" label:"bid-scout-gz-tyj"
```

**创建子 Agent B（广东省政府采购网）**：

```
sessions_spawn task:"你是招投标信息采集子 Agent。你的任务是从广东省政府采购网采集最新的招投标公告。

【目标站点】
- 名称：广东省政府采购网
- 入口 URL：https://gdgpo.czt.gd.gov.cn/cms-gd/site/guangdong/cggg/index.html
- 备用 URL 1：https://gdgpo.czt.gd.gov.cn/freecms/site/guangdong/wlzfcgxx/index.html
- 备用 URL 2：https://gdgpo.czt.gd.gov.cn/

【采集步骤】
1. browser navigate url:\"https://gdgpo.czt.gd.gov.cn/cms-gd/site/guangdong/cggg/index.html\"
2. exec command:\"sleep 3\"
3. browser screenshot → 用 image 工具判断页面状态
4. 如果页面返回 403/空白/错误：依次尝试备用 URL
5. 如果页面正常：
   a. 用 browser snapshot 获取可访问性树
   b. 用 image 工具读取截图，提取列表中的公告标题、发布日期、链接
   c. 对前 5 条公告，逐个 browser navigate 进入详情页
   d. 每个详情页：browser screenshot → image 提取正文摘要（前 500 字）
6. 如果遇到验证码/滑块：告诉用户「检测到验证码，请在浏览器中完成验证，完成后回复 好了」，然后停止等用户回复
7. 如果遇到登录页：告诉用户「需要登录，请在浏览器中登录，完成后回复 好了，或回复 跳过」
8. 如果遇到 403/访问被拒：exec command:\"sleep 10\"，然后重试，仍然失败则尝试备用 URL

【数据格式】
采集完成后，将结果以如下 JSON 格式 announce 回主会话：
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

【注意事项】
- 每次页面操作后 sleep 2 秒
- 最多采集 5 条
- 单条失败不影响其他条目
- browser 工具只用 navigate/screenshot/snapshot/scroll/click
- 该站点经常返回 403，务必尝试全部备用 URL 再放弃" label:"bid-scout-gdgpo"
```

### 第三步：等待子 Agent 完成

两个子 Agent 并发执行，各自完成后会通过 announce 将结果发回。等待两个子 Agent 都 announce 结果。

如果某个子 Agent 报告了人工接管需求（验证码/登录），你会收到通知。此时：
1. 将该信息转发给用户
2. 等待用户回复「好了」或「跳过」
3. 如果用户说「好了」，该子 Agent 会自动继续
4. 如果用户说「跳过」，记录该站点为跳过状态

### 第四步：汇总结果与生成报告

收到所有子 Agent 的 announce 后：

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

5. **向用户报告**：
   - 输出采集摘要（各站点采集数量、成功/失败状态）
   - 输出高匹配度条目的标题和分数
   - 告知 CSV 文件路径

### 第五步：报告格式

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

## browser 工具正确用法

**只用这 5 个命令**：

1. **导航**：`browser navigate url:"https://..."`
2. **截图**：`browser screenshot`
3. **可访问性树**：`browser snapshot`
4. **滚动**：`browser scroll direction:down amount:800`
5. **点击**：`browser click ref:"N"`（ref 必须来自 snapshot 结果）

等待页面加载用 exec，不要用 browser 的 sleep：
```
exec command:"sleep 3"
```

## 容错策略

| 情况 | 处理 |
|------|------|
| 搜索无结果 | 记录"该站点无相关公告"，继续 |
| 登录页 | 通知用户登录，等回复 |
| 验证码/滑块 | 通知用户处理，等回复 |
| 403/访问被拒 | sleep 10 重试 → 尝试备用 URL → 记录失败 |
| 浏览器报错 | 重试 2 次，仍失败记录错误 |
| 单站点彻底失败 | **绝不终止任务**，跳过继续 |
| 子 Agent 超时/异常 | 记录错误，使用已有结果继续生成报告 |

## 注意事项

- 每次页面操作后间隔 2-3 秒
- 两个子 Agent 使用同一个浏览器的不同标签页，注意操作顺序
- 截图路径从 `MEDIA:` 行提取，image 工具使用该路径读取
- Python 工具路径基于 SKILL.md 所在目录解析为绝对路径
- 如果用户只想查某一个站点，只创建对应的一个子 Agent 即可
- CSV 使用 `utf-8-sig` 编码，确保 Excel 正确显示中文
