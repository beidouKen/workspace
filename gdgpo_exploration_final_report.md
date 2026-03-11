# 广东省政府采购网全文搜索页面探索报告

**报告时间**: 2026-03-11  
**探索状态**: 部分完成（静态分析完成，动态分析受限）

---

## 执行摘要

通过静态 HTML 分析，我们确认广东省政府采购网的全文搜索页面是一个需要 JavaScript 渲染的单页应用（SPA）。静态请求无法获取页面的实际结构，必须使用浏览器自动化工具才能进行深入探索。

## 1. 基础页面信息

### 1.1 URL 结构

**搜索页面基础 URL**:
```
https://gdgpo.czt.gd.gov.cn/maincms-web/fullSearchingGd
```

**状态**: 
- HTTP 状态码: 200
- 无服务器端重定向
- 页面可正常访问

### 1.2 页面技术特征

| 特征 | 值 | 说明 |
|------|-----|------|
| 需要 JS 渲染 | ✓ | 必须 |
| 静态 HTML 大小 | 2,104 字节 | 仅包含框架 |
| SPA 指标 | 检测到 | 包含 app.js/bundle.js 引用 |
| 框架 | 未检测到 | 不是 React/Vue/Angular |

### 1.3 重定向与弹窗问题（来自文档）

根据 `bid-scout` 技能文档，该站点已知存在以下问题：

**A. tipsPage 重定向**
- **现象**: 首次访问可能被重定向到 `/tipsPage` 系统提示页
- **处理**: 需要找到并点击关闭/确定按钮，然后重新导航到目标页面

**B. 服务指引弹窗**（高概率出现）
- **名称**: "广东政府采购智慧云平台服务指引"
- **DOM 结构**:
  ```html
  <div class="mainNoticeBox">
    <div class="mainNotice">
      <div class="noticeContent">...</div>
      <div class="noticeCloseBtn">x</div>  <!-- 关闭按钮 -->
    </div>
  </div>
  ```
- **关闭方式**: 点击文字为 "x" 的 `noticeCloseBtn` 元素
- **重要**: 关闭按钮文字是**小写** "x"，不是"关闭"、"确定"或"我知道了"

## 2. URL 参数测试结果

### 2.1 测试用例

测试了以下 URL 参数格式，均**未能成功**通过 URL 参数直接触发搜索：

| 参数名 | 测试 URL | 结果 |
|--------|----------|------|
| `keywords` | `?keywords=体育` | ❌ 失败 |
| `searchWord` | `?searchWord=体育` | ❌ 失败 |
| `keyword` | `?keyword=体育` | ❌ 失败 |

### 2.2 结论

**URL 参数搜索不可行**。必须通过以下方式进行搜索：
1. 在页面上找到搜索输入框
2. 输入关键词
3. 点击搜索按钮
4. 或通过 JavaScript 直接调用搜索函数

## 3. 搜索表单结构（需要浏览器工具探索）

### 3.1 静态分析结果

从静态 HTML 中**未找到**以下元素：
- ❌ 搜索表单 (`<form>`)
- ❌ 搜索输入框 (`<input>`)
- ❌ 搜索按钮 (`<button>`)
- ❌ 任何可交互元素

### 3.2 需要动态探索的内容

使用浏览器工具时，需要查找以下信息：

**搜索输入框**:
- `name` 属性
- `id` 属性
- `class` 属性
- `placeholder` 文本
- XPath 或 CSS 选择器
- 是否需要先聚焦才能输入

**搜索按钮**:
- 按钮类型（`<button>` 或 `<input type="submit">`）
- 按钮文字
- `id` / `class` 属性
- 点击事件绑定方式
- XPath 或 CSS 选择器

**筛选条件**（如果有）:
- 日期范围选择器
- 类别下拉菜单
- 地区选择器
- 其他过滤条件

## 4. 搜索结果结构（待探索）

### 4.1 需要确认的结构信息

**结果列表容器**:
- 容器元素的 class 或 id
- 列表项的选择器
- 每条结果包含哪些字段

**单条结果的典型结构**（预期）:
```
- 标题：公告标题
- 日期：发布日期（格式：YYYY-MM-DD）
- 链接：详情页 URL
- 摘要：简短描述（可选）
- 采购单位：发布单位名称（可选）
- 项目编号：采购项目编号（可选）
```

### 4.2 结果列表定位

需要找到：
- 结果列表的父容器选择器
- 单条结果的选择器
- 如何遍历所有结果

## 5. 分页机制（待探索）

### 5.1 可能的分页方式

需要确认该页面使用以下哪种分页方式：

**A. 传统分页**:
- 页码按钮（1, 2, 3...）
- 上一页/下一页按钮
- 跳转到指定页

**B. 滚动加载**:
- 滚动到底部自动加载更多
- "加载更多"按钮

**C. 混合方式**:
- 结合传统分页和滚动加载

### 5.2 需要获取的信息

- 分页控件的选择器
- 当前页码的识别方式
- 总页数的获取方式
- 下一页按钮的选择器
- 是否需要等待加载完成

## 6. 详情页链接格式（待探索）

### 6.1 链接结构

需要确认详情页 URL 的格式：

**可能的格式**:
```
/detail?id=12345
/view/公告ID
/article/类别/ID
/maincms-web/detail/...
```

### 6.2 需要获取的信息

- 详情页完整 URL 示例
- URL 参数含义
- 是否是相对路径还是绝对路径
- 详情页是否也需要处理弹窗

## 7. 自动化脚本建议

### 7.1 推荐的技术栈

根据探索结果，推荐使用以下工具：

**方案 A: OpenClaw Browser 工具**（推荐）
- 使用 OpenClaw 项目内置的浏览器工具
- 通过 Chrome 扩展控制
- 优势：利用已有登录态，支持标签页隔离
- 参考：`bid-scout/SKILL.md` 文档

**方案 B: Selenium**
- 适用于没有 OpenClaw Browser 的情况
- 需要 ChromeDriver
- 完整的浏览器控制能力

**方案 C: Playwright**
- 现代化的浏览器自动化工具
- 更好的性能和稳定性
- 内置等待机制

### 7.2 采集流程建议

```
1. 初始化浏览器
   ↓
2. 导航到搜索页面
   ├→ 检测 tipsPage 重定向 → 关闭 → 重新导航
   └→ 检测服务指引弹窗 → 点击 "x" 关闭
   ↓
3. 等待页面完全加载
   ├→ 等待搜索输入框可见
   └→ 等待搜索按钮可见
   ↓
4. 执行搜索
   ├→ 定位搜索输入框
   ├→ 输入关键词（如"体育"）
   ├→ 点击搜索按钮
   └→ 等待搜索结果加载
   ↓
5. 提取搜索结果
   ├→ 定位结果列表容器
   ├→ 遍历每条结果
   ├→ 提取：标题、日期、链接、摘要等
   └→ 保存到数组
   ↓
6. 处理分页
   ├→ 检查是否有下一页
   ├→ 点击下一页/滚动加载更多
   ├→ 重复步骤 5
   └→ 直到所有页面采集完毕
   ↓
7. 访问详情页（可选）
   ├→ 对每个结果，点击详情链接
   ├→ 等待详情页加载
   ├→ 提取详细内容
   └→ 返回列表页继续
   ↓
8. 数据处理与输出
   ├→ 数据清洗
   ├→ 格式化
   └→ 输出为 JSON/CSV
```

### 7.3 关键代码模式

**弹窗处理**:
```python
# 检测并关闭服务指引弹窗
try:
    close_btn = driver.find_element(By.CSS_SELECTOR, ".mainNoticeBox .noticeCloseBtn")
    if close_btn.is_displayed():
        close_btn.click()
        time.sleep(2)
except:
    pass  # 弹窗可能不出现
```

**等待元素加载**:
```python
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 等待搜索框可见
search_input = WebDriverWait(driver, 10).until(
    EC.visibility_of_element_located((By.ID, "search-input-id"))
)
```

**提取搜索结果**:
```python
# 找到所有结果项
results = driver.find_elements(By.CSS_SELECTOR, ".result-item")

for result in results:
    title = result.find_element(By.CSS_SELECTOR, ".title").text
    date = result.find_element(By.CSS_SELECTOR, ".date").text
    link = result.find_element(By.TAG_NAME, "a").get_attribute("href")
    
    data.append({
        "title": title,
        "date": date,
        "url": link
    })
```

## 8. 下一步行动

### 8.1 立即可执行的步骤

**选项 1: 使用 OpenClaw Browser 工具**（如果可用）

如果你的环境中有 OpenClaw Browser Relay 扩展，请按以下步骤操作：

1. 在 Chrome 浏览器中打开任意网页
2. 点击 **OpenClaw Browser Relay** 扩展图标
3. 确保徽章显示为 **ON**
4. 使用 `browser` 命令进行探索：

```bash
# 导航到搜索页面
browser navigate url:"https://gdgpo.czt.gd.gov.cn/maincms-web/fullSearchingGd"

# 截图查看页面
browser screenshot

# 获取页面结构
browser snapshot

# 查找并点击弹窗关闭按钮（如果有）
browser click ref:"N"  # N 是 snapshot 中显示的元素引用编号
```

**选项 2: 手动浏览器探索**（最快）

1. 打开 Chrome 浏览器
2. 访问: `https://gdgpo.czt.gd.gov.cn/maincms-web/fullSearchingGd`
3. 打开开发者工具（F12）
4. 观察并记录：
   - 弹窗结构和关闭按钮
   - 搜索输入框的 id/class/name
   - 搜索按钮的选择器
   - 搜索结果列表的结构
   - 分页按钮的选择器
5. 手动在搜索框输入"体育"并搜索
6. 观察搜索结果的 DOM 结构
7. 记录所有关键选择器

**选项 3: 运行改进的 Selenium 脚本**

我可以创建一个使用 `webdriver-manager` 的改进版本，自动下载和管理 ChromeDriver：

```bash
pip install webdriver-manager
python explore_gdgpo_selenium_v2.py
```

### 8.2 预期输出

完成探索后，你将获得：

1. **页面结构文档**
   - 搜索输入框的精确选择器
   - 搜索按钮的精确选择器
   - 搜索结果列表的结构
   - 分页控件的选择器
   - 详情页链接的格式

2. **弹窗处理方案**
   - 确认弹窗是否出现
   - 关闭按钮的精确位置
   - 处理时机和方法

3. **自动化脚本模板**
   - 可直接使用的代码模板
   - 包含错误处理
   - 包含等待和重试逻辑

## 9. 已知限制与注意事项

### 9.1 技术限制

- **JavaScript 必需**: 页面完全依赖 JS 渲染，无法通过静态爬虫获取数据
- **可能的反爬措施**: 未知是否有验证码、频率限制等
- **登录要求**: 未确认是否需要登录才能搜索

### 9.2 注意事项

1. **礼貌爬取**: 每次请求间隔 2-3 秒，避免给服务器造成压力
2. **User-Agent**: 使用真实的浏览器 User-Agent
3. **Cookie 管理**: 保持 session 一致性
4. **错误处理**: 网络错误、元素未找到等情况的处理
5. **数据验证**: 确保提取的数据完整性

## 10. 附录

### 10.1 相关文档

- `bid-scout/SKILL.md` - 招投标信息采集技能文档
- `gdgpo_exploration_report.json` - 静态分析 JSON 报告
- `gdgpo_exploration_report.md` - 静态分析 Markdown 报告
- `explore_gdgpo.py` - 静态 HTML 探索脚本
- `explore_gdgpo_selenium.py` - Selenium 自动化探索脚本

### 10.2 有用的选择器模式

基于类似政府采购网站的经验，以下是常见的选择器模式：

**搜索框**:
```css
input[name*="search"]
input[name*="keyword"]
input[placeholder*="搜索"]
#searchInput
.search-input
```

**搜索按钮**:
```css
button[type="submit"]
button:contains("搜索")
.search-btn
#searchBtn
```

**结果列表**:
```css
.result-list .result-item
ul.list li.item
[class*="result"]
```

**分页**:
```css
.pagination a
.page-nav button
[class*="page"] [class*="next"]
```

---

## 总结

广东省政府采购网的全文搜索页面是一个现代化的 SPA 应用，需要使用浏览器自动化工具才能有效探索和采集数据。静态分析已确认了这一点，下一步需要通过浏览器工具或 Selenium 来获取页面的实际DOM结构。

**推荐行动**: 如果你有 OpenClaw Browser 工具，使用它是最佳选择。否则，手动浏览器探索是最快获取结构信息的方法，然后再编写自动化脚本。

---

*报告生成时间: 2026-03-11*  
*工具: Python + Requests + BeautifulSoup (静态分析)*  
*状态: 等待浏览器工具探索以完成动态结构分析*
