---
name: bilibili-snapshot-report
description: 打开B站(bilibili.com)搜索"Openclaw项目"，对搜索结果截图进行视觉分析，生成结构化 HTML 报告。当用户需要查看B站Openclaw项目相关视频、分析B站搜索结果、或生成B站快照报告时使用此技能。
---

# B站Openclaw项目搜索快照报告

## 能力范围

- 使用浏览器打开 bilibili.com 并搜索"Openclaw项目"
- 对搜索结果页截图，通过视觉分析提取视频列表信息
- 生成结构稳定的 HTML 格式报告，保存到工作区

## 操作流程

### 第一步：打开B站并搜索

1. 使用 `browser-use` 子代理或浏览器工具导航到B站搜索页：
   ```
   导航到 https://search.bilibili.com/all?keyword=Openclaw项目
   等待页面加载完成（3-5秒）
   ```
2. 如果页面弹出登录提示或通知弹窗，关闭弹窗继续
3. 确认搜索结果页已正常加载（页面应显示"Openclaw项目"相关视频列表）

### 第二步：截图与视觉分析

1. 对搜索结果页截图，用视觉能力获取页面整体布局和可见文字内容
2. **获取可访问性树/DOM**：截图仅用于理解布局，**视频链接必须从 DOM 或可访问性树中提取真实 `href` 属性**，禁止通过 OCR 截图识别 BV 号（视觉模型极易误读字符，导致链接 404）
3. 综合截图和 DOM 信息，提取以下数据：
   - **搜索结果概况**：结果数量、排序方式、筛选条件等
   - **视频列表**（6-10 条）：
     - 标题：从 DOM 文本节点提取
     - UP主：从 DOM 文本节点提取
     - 播放量：从 DOM 文本节点或截图提取
     - **视频链接**：必须从 `<a>` 标签的 `href` 属性提取完整 URL，不可手动拼接 BV 号
   - **相关标签/分类**：页面上可见的相关推荐标签
   - **页面整体描述**：简要描述搜索结果页当前状态
4. 如果首屏结果不够，向下滚动一屏后再次截图 + 获取 DOM，补充更多视频条目

### 第三步：生成 HTML 报告

将分析结果写入 HTML 文件。

**报告目录**：`{workspace}/bilibili-reports/`（首次运行时自动创建）

**文件命名**：`bilibili-openclaw-report_YYYY-MM-DD_HHmmss.html`

示例：`bilibili-openclaw-report_2026-03-11_150230.html`

使用以下 HTML 模板（**必须严格遵循此结构**）：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>B站Openclaw项目搜索报告</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: #f4f5f7; color: #222; line-height: 1.6;
    }
    .container { max-width: 960px; margin: 0 auto; padding: 24px; }
    header {
      background: linear-gradient(135deg, #00a1d6, #fb7299);
      color: #fff; padding: 32px 24px; border-radius: 12px; margin-bottom: 24px;
    }
    header h1 { font-size: 28px; margin-bottom: 8px; }
    header p { opacity: 0.9; font-size: 14px; }
    .section {
      background: #fff; border-radius: 12px; padding: 24px;
      margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .section h2 {
      font-size: 18px; color: #00a1d6; margin-bottom: 16px;
      padding-bottom: 8px; border-bottom: 2px solid #00a1d6;
    }
    .video-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
    .video-card {
      border: 1px solid #e7e7e7; border-radius: 8px; padding: 16px;
      transition: box-shadow 0.2s;
    }
    .video-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .video-card h3 { font-size: 15px; margin-bottom: 8px; }
    .video-card h3 a { color: #333; text-decoration: none; }
    .video-card h3 a:hover { color: #00a1d6; }
    .video-card .meta { font-size: 13px; color: #999; }
    .video-card .meta span { margin-right: 12px; }
    .tag-list { display: flex; flex-wrap: wrap; gap: 8px; }
    .tag {
      background: #e3f6fd; color: #00a1d6; padding: 4px 12px;
      border-radius: 16px; font-size: 13px;
    }
    .summary-text { font-size: 15px; color: #555; }
    footer { text-align: center; padding: 24px; color: #999; font-size: 13px; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>B站Openclaw项目搜索报告</h1>
      <p>生成时间：{timestamp} | 搜索关键词：Openclaw项目 | 数据来源：bilibili.com</p>
    </header>

    <!-- 搜索概览 -->
    <div class="section">
      <h2>搜索结果概览</h2>
      <p class="summary-text">{page_overview}</p>
    </div>

    <!-- 筛选条件/推荐标签 -->
    <div class="section">
      <h2>筛选条件 / 推荐标签</h2>
      <ul>
        <!-- 每条筛选项或推荐标签一个 <li>，示例：<li>「综合排序」</li> -->
        {banner_items}
      </ul>
    </div>

    <!-- 搜索结果视频 -->
    <div class="section">
      <h2>搜索结果视频</h2>
      <div class="video-grid">
        <!-- 对每个视频重复此卡片 -->
        <div class="video-card">
          <h3><a href="{video_url}" target="_blank" rel="noopener">{video_title}</a></h3>
          <div class="meta">
            <span>UP主：{uploader}</span>
            <span>播放：{play_count}</span>
          </div>
        </div>
        <!-- /重复结束 -->
      </div>
    </div>

    <!-- 相关标签 -->
    <div class="section">
      <h2>相关标签</h2>
      <div class="tag-list">
        <!-- 每个标签一个 tag，示例：<span class="tag">美食</span> -->
        {category_tags}
      </div>
    </div>

    <footer>
      本报告由 bilibili-snapshot-report 技能自动生成
    </footer>
  </div>
</body>
</html>
```

**占位符替换规则**：

| 占位符 | 替换内容 |
|--------|----------|
| `{timestamp}` | 当前日期时间，格式 `YYYY-MM-DD HH:mm` |
| `{page_overview}` | 2-3 句话描述搜索结果页状态（结果数量、排序等） |
| `{banner_items}` | `<li>` 列表，每条为搜索页顶部的推荐标签或筛选项；若无则填 `<li>无</li>` |
| `{video_title}` | 视频标题 |
| `{video_url}` | 视频链接，**必须从 DOM 的 `href` 属性原样复制**，禁止 OCR 拼接；无法提取则填 `#` |
| `{uploader}` | UP主名称，未知则填"未知" |
| `{play_count}` | 播放量，未知则填"--" |
| `{category_tags}` | `<span class="tag">标签名</span>` 若干个，来自搜索页的相关推荐标签 |

### 第四步：完成报告

1. 确保 `{workspace}/bilibili-reports/` 目录存在，不存在则创建
2. 将填充好的 HTML 写入 `{workspace}/bilibili-reports/bilibili-openclaw-report_YYYY-MM-DD_HHmmss.html`
3. 告知用户报告完整路径
4. 简要总结发现的内容亮点（2-3 句话）

## 容错策略

| 情况 | 处理 |
|------|------|
| 页面加载缓慢 | 等待 5 秒后重试一次 |
| 弹出登录/通知弹窗 | 关闭弹窗继续 |
| 搜索结果为空 | 记录"无搜索结果"，报告中标注说明 |
| 截图模糊或内容过少 | 滚动页面后再次截图补充 |
| 部分信息无法提取 | 用"--"或"未知"填充，不中断流程 |

## 注意事项

- HTML 模板结构**不可修改**，仅替换占位符内容
- 报告文件编码使用 `UTF-8`
- 尽可能多地提取可见信息，但不强求完美
- 整个流程应在 1-2 分钟内完成
