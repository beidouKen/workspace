# 广东省政府采购网探索 - 完整指南

## 📋 任务完成情况

### ✅ 已完成

1. **静态 HTML 分析**
   - 确认页面需要 JavaScript 渲染
   - 测试了 3 种 URL 参数格式（均无效）
   - 生成了初步探索报告

2. **创建自动化探索脚本**
   - `explore_gdgpo.py` - 静态 HTML 分析脚本
   - `explore_gdgpo_selenium.py` - 完整 Selenium 探索脚本
   - `explore_gdgpo_quick.py` - 快速 Selenium 探索脚本（推荐使用）

3. **生成详细报告**
   - `gdgpo_exploration_report.json/md` - 静态分析报告
   - `gdgpo_exploration_final_report.md` - 综合探索报告
   - `gdgpo_exploration_progress.md` - 进度记录

### ⏳ 待完成（需要浏览器工具）

由于系统提示中提到的 `cursor-ide-browser` 工具在当前环境不可用，以下步骤需要通过其他方式完成：

1. **动态页面结构分析**
   - 搜索输入框的精确定位
   - 搜索按钮的精确定位
   - 搜索结果列表结构
   - 分页机制分析
   - 详情页链接格式

2. **弹窗处理验证**
   - 确认弹窗是否出现
   - 测试关闭方法

---

## 🚀 接下来如何操作

### 方案 1: 运行快速探索脚本（推荐）

这个脚本会自动下载 ChromeDriver 并打开浏览器进行探索。

```bash
# 1. 确保安装了依赖
pip install selenium webdriver-manager

# 2. 运行脚本
cd d:\openclaw\workspace
python explore_gdgpo_quick.py
```

**脚本会做什么**:
- ✅ 自动下载并配置 ChromeDriver
- ✅ 打开 Chrome 浏览器
- ✅ 访问搜索页面并截图
- ✅ 检测并尝试关闭弹窗
- ✅ 查找所有可能的搜索输入框（包含 XPath）
- ✅ 查找所有可能的搜索按钮（包含 XPath）
- ✅ 测试 URL 参数是否有效
- ✅ 尝试自动执行一次搜索
- ✅ 生成详细的 JSON 和 TXT 报告
- ✅ 保存 3 张截图

**预计时间**: 30-60 秒

**输出文件**:
- `gdgpo_quick_exploration.json` - 结构化数据
- `gdgpo_quick_exploration.txt` - 可读报告
- `screenshot_01_initial.png` - 初始页面
- `screenshot_02_after_popup.png` - 关闭弹窗后
- `screenshot_03_search_results.png` - 搜索结果

---

### 方案 2: 手动浏览器探索（最快）

如果你想立即了解页面结构，手动探索是最快的方法。

#### 步骤

1. **打开浏览器并访问页面**
   ```
   https://gdgpo.czt.gd.gov.cn/maincms-web/fullSearchingGd
   ```

2. **打开开发者工具**
   - 按 `F12` 或右键 → 检查

3. **观察并记录**

**A. 检查弹窗**
   - 页面加载后是否出现弹窗？
   - 弹窗的 class 名称是什么？
   - 关闭按钮的选择器是什么？
   
**B. 查找搜索输入框**
   - 在开发者工具中定位搜索框元素
   - 记录：
     ```
     id: _____________
     name: _____________
     class: _____________
     placeholder: _____________
     ```
   - 右键元素 → Copy → Copy selector / Copy XPath

**C. 查找搜索按钮**
   - 定位搜索按钮
   - 记录：
     ```
     按钮文字: _____________
     id: _____________
     class: _____________
     XPath: _____________
     ```

**D. 测试搜索**
   - 在搜索框输入"体育"
   - 点击搜索按钮
   - 观察搜索结果的结构：
     ```
     结果列表容器的 class: _____________
     单条结果的 class: _____________
     标题元素: _____________
     日期元素: _____________
     链接元素: _____________
     ```

**E. 检查分页**
   - 分页按钮的位置
   - "下一页"按钮的选择器
   - 页码的显示方式

4. **填写发现**

将你的发现填写到以下模板中：

```markdown
## 探索发现

### 弹窗
- 是否有弹窗: [ ] 是 [ ] 否
- 弹窗 class: _______________
- 关闭按钮选择器: _______________

### 搜索输入框
- 元素类型: <input>
- ID: _______________
- Name: _______________
- Class: _______________
- Placeholder: _______________
- XPath: _______________

### 搜索按钮
- 元素类型: [ ] <button> [ ] <input>
- 按钮文字: _______________
- ID: _______________
- Class: _______________
- XPath: _______________

### 搜索结果
- 结果列表容器: _______________
- 单条结果选择器: _______________
- 标题路径: _______________
- 日期路径: _______________
- 链接路径: _______________

### 分页
- 分页类型: [ ] 传统页码 [ ] 滚动加载 [ ] 加载更多按钮
- 下一页按钮: _______________
```

---

### 方案 3: 使用 OpenClaw Browser 工具

如果你的环境中有 OpenClaw Browser Relay 扩展（根据 bid-scout 文档），这是最佳方案。

#### 步骤

1. **连接浏览器**
   - 在 Chrome 中打开任意网页
   - 点击 OpenClaw Browser Relay 扩展图标
   - 确保徽章显示为 ON

2. **运行探索命令**

```bash
# 导航到搜索页面
browser navigate url:"https://gdgpo.czt.gd.gov.cn/maincms-web/fullSearchingGd"

# 截图查看页面
browser screenshot

# 获取页面结构
browser snapshot

# 根据 snapshot 结果，查找搜索框和按钮的 ref 编号
# 然后可以点击、输入等操作
```

3. **分析 snapshot 输出**
   - 查找包含 "search"、"keyword"、"搜索" 等关键词的元素
   - 记录元素的 ref 编号
   - 使用这些 ref 进行后续操作

---

## 📊 当前已知信息

### ✓ 确认的事实

1. **页面技术**: 单页应用（SPA），需要 JavaScript 渲染
2. **HTML 大小**: 静态 HTML 只有 2104 字节
3. **URL 参数**: 以下参数**无效**
   - `?keywords=体育`
   - `?searchWord=体育`
   - `?keyword=体育`
4. **搜索方式**: 必须通过页面表单提交，不能通过 URL 参数

### ⚠ 已知问题（来自文档）

根据 `bid-scout/SKILL.md`，该站点可能出现：

1. **tipsPage 重定向**
   - 首次访问可能跳转到系统提示页
   - 需要关闭提示后重新导航

2. **服务指引弹窗**
   - class: `mainNoticeBox`
   - 关闭按钮: class `noticeCloseBtn`，文字 "x"（小写）

### ❓ 待确认信息

需要通过浏览器工具探索以确认：

- [ ] 搜索输入框的确切选择器
- [ ] 搜索按钮的确切选择器
- [ ] 搜索结果列表的 DOM 结构
- [ ] 分页机制（页码 vs 滚动加载）
- [ ] 详情页链接的 URL 格式
- [ ] 弹窗是否真的出现
- [ ] 是否需要登录

---

## 🛠 自动化脚本模板

一旦你完成探索，可以使用以下模板编写采集脚本：

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# 初始化浏览器
driver = webdriver.Chrome()
driver.get("https://gdgpo.czt.gd.gov.cn/maincms-web/fullSearchingGd")
time.sleep(3)

# 1. 关闭弹窗（如果有）
try:
    close_btn = driver.find_element(By.CLASS_NAME, "noticeCloseBtn")
    close_btn.click()
    time.sleep(2)
except:
    pass

# 2. 等待搜索框可见
search_input = WebDriverWait(driver, 10).until(
    EC.visibility_of_element_located((By.ID, "搜索框ID"))  # 替换为实际ID
)

# 3. 输入搜索关键词
search_input.clear()
search_input.send_keys("体育")

# 4. 点击搜索按钮
search_btn = driver.find_element(By.ID, "搜索按钮ID")  # 替换为实际ID
search_btn.click()
time.sleep(3)

# 5. 等待结果加载
results = WebDriverWait(driver, 10).until(
    EC.presence_of_all_elements_located((By.CLASS_NAME, "结果项CLASS"))  # 替换
)

# 6. 提取结果
data = []
for result in results:
    title = result.find_element(By.CLASS_NAME, "title").text
    date = result.find_element(By.CLASS_NAME, "date").text
    link = result.find_element(By.TAG_NAME, "a").get_attribute("href")
    
    data.append({
        "title": title,
        "date": date,
        "url": link
    })

# 7. 处理分页
# ... 根据实际分页方式实现

print(f"采集了 {len(data)} 条数据")
driver.quit()
```

---

## 📁 已创建的文件清单

### 探索脚本
1. `explore_gdgpo.py` - 静态 HTML 分析（已运行）
2. `explore_gdgpo_selenium.py` - 完整 Selenium 脚本
3. `explore_gdgpo_quick.py` - 快速探索脚本 ⭐ **推荐使用**

### 报告文档
1. `gdgpo_exploration_report.json` - 静态分析 JSON
2. `gdgpo_exploration_report.md` - 静态分析 Markdown
3. `gdgpo_exploration_final_report.md` - 综合报告 ⭐ **详细参考**
4. `gdgpo_exploration_progress.md` - 进度记录
5. `gdgpo_exploration_guide.md` - 本指南文档

### 待生成文件（运行脚本后）
- `gdgpo_quick_exploration.json`
- `gdgpo_quick_exploration.txt`
- `screenshot_01_initial.png`
- `screenshot_02_after_popup.png`
- `screenshot_03_search_results.png`

---

## 💡 建议

### 立即行动

**最快获取结果的方法**:
1. 运行 `explore_gdgpo_quick.py` 脚本（5 分钟）
2. 查看生成的截图和报告
3. 如果脚本找到了输入框和按钮，直接使用它们的 XPath
4. 如果没有，手动在浏览器中探索（10 分钟）

### 长期方案

如果要构建稳定的采集系统：
1. 完成页面结构探索
2. 编写健壮的采集脚本
3. 添加错误处理和重试逻辑
4. 实现增量采集和去重
5. 添加数据验证和质量检查

---

## 🆘 故障排除

### 问题: Selenium 无法启动浏览器

**解决方案**:
```bash
pip install --upgrade selenium webdriver-manager
```

### 问题: ChromeDriver 版本不匹配

**解决方案**:
`explore_gdgpo_quick.py` 脚本使用 `webdriver-manager` 会自动处理这个问题。

### 问题: 页面加载很慢

**解决方案**:
增加 `time.sleep()` 的时间，或使用显式等待：
```python
WebDriverWait(driver, 30).until(...)  # 增加到 30 秒
```

### 问题: 找不到元素

**解决方案**:
1. 检查元素是否在 iframe 中
2. 检查是否需要先关闭弹窗
3. 使用浏览器开发者工具确认选择器

---

## 📞 下一步

1. **立即**: 运行 `explore_gdgpo_quick.py` 或手动浏览器探索
2. **完成后**: 查看报告和截图
3. **然后**: 根据发现的结构编写采集脚本
4. **最后**: 测试和优化采集脚本

---

*创建时间: 2026-03-11*  
*工具: Python + Selenium + BeautifulSoup*  
*状态: 等待运行探索脚本或手动探索*
