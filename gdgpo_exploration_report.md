# 广东省政府采购网搜索页面探索报告
**探索时间**: 2026-03-11 19:03:37
---

## 1. 基础页面分析
- **URL**: https://gdgpo.czt.gd.gov.cn/maincms-web/fullSearchingGd
- **最终URL**: https://gdgpo.czt.gd.gov.cn/maincms-web/fullSearchingGd
- **状态码**: 200
- **重定向**: 无

## 2. URL参数测试结果

| 参数 | 搜索框包含关键词 | 搜索结果数量 | 是否成功 |
|------|----------------|-------------|----------|
| `keywords` | False | 0 | [FAIL] |
| `searchWord` | False | 0 | [FAIL] |
| `keyword` | False | 0 | [FAIL] |

## 3. 搜索表单结构

## 4. 搜索结果结构
- **结果数量**: 0

## 5. 分页机制
- **分页元素数量**: 0

## 6. 详情页链接格式

## 7. 其他发现

### JavaScript渲染检查
- **可能需要JS**: True
- **检测到React**: False
- **检测到Vue**: False
- **检测到Angular**: False
- **检测到SPA指标**: True
- **HTML长度**: 2104

---

## 自动化脚本建议

根据探索结果，建议使用以下策略编写自动化脚本:

1. **使用浏览器自动化工具**（如Selenium、Playwright、Puppeteer），因为页面需要JavaScript渲染
2. **URL参数**: 测试的参数均未能直接触发搜索，可能需要通过表单提交

---

*此报告由 GDGPOExplorer 自动生成*
