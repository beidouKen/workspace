# 广东省政府采购网搜索页面探索报告 (Selenium)

**探索时间**: 2026-03-11 19:06:20

---

## 1. 基础页面分析

- **URL**: https://gdgpo.czt.gd.gov.cn/maincms-web/fullSearchingGd
- **最终URL**: https://gdgpo.czt.gd.gov.cn/maincms-web/fullSearchingGd
- **有tipsPage重定向**: False
- **页面HTML长度**: 58317 字节

## 2. URL参数测试结果

| 参数 | 搜索框包含关键词 | 搜索结果数量 | 是否成功 |
|------|----------------|-------------|----------|
| `keywords` | False | 6 | [OK] |
| `searchWord` | False | 6 | [OK] |
| `keyword` | False | 6 | [OK] |

## 3. 搜索表单结构

**搜索表单数量**: 0

### 搜索输入框

**输入框 1**:
- **name**: `key`
- **id**: `title`
- **type**: `text`
- **placeholder**: `输入查询内容`
- **class**: `searchValue`
- **是否可见**: True
- **xpath**: `//*[@id="title"]`

**输入框 2**:
- **name**: ``
- **id**: ``
- **type**: `text`
- **placeholder**: `请选择区划`
- **class**: `el-input__inner`
- **是否可见**: True
- **xpath**: `//*[@id="app"]/section[1]/header[1]/div[3]/div[1]/div[1]/div[1]/input[1]`

**输入框 3**:
- **name**: ``
- **id**: ``
- **type**: `text`
- **placeholder**: `请输入关键字`
- **class**: `containerInput`
- **是否可见**: True
- **xpath**: `//*[@id="app"]/section[1]/div[1]/div[1]/div[1]/div[1]/input[1]`

**输入框 4**:
- **name**: ``
- **id**: ``
- **type**: `text`
- **placeholder**: `请选择区划`
- **class**: `el-input__inner`
- **是否可见**: True
- **xpath**: `//*[@id="app"]/section[1]/div[1]/div[1]/div[2]/div[3]/div[1]/div[1]/div[1]/input[1]`

**输入框 5**:
- **name**: ``
- **id**: ``
- **type**: `text`
- **placeholder**: ``
- **class**: `el-input__inner`
- **是否可见**: True
- **xpath**: `//*[@id="app"]/section[1]/div[1]/div[1]/div[2]/div[4]/div[1]/input[1]`

**输入框 6**:
- **name**: ``
- **id**: ``
- **type**: `text`
- **placeholder**: ``
- **class**: `el-input__inner`
- **是否可见**: True
- **xpath**: `//*[@id="app"]/section[1]/div[1]/div[1]/div[2]/div[4]/div[2]/input[1]`

**输入框 7**:
- **name**: ``
- **id**: ``
- **type**: `text`
- **placeholder**: `开始日期`
- **class**: `el-range-input`
- **是否可见**: True
- **xpath**: `//*[@id="app"]/section[1]/div[1]/div[1]/div[2]/div[5]/div[2]/div[1]/input[1]`

**输入框 8**:
- **name**: ``
- **id**: ``
- **type**: `text`
- **placeholder**: `结束日期`
- **class**: `el-range-input`
- **是否可见**: True
- **xpath**: `//*[@id="app"]/section[1]/div[1]/div[1]/div[2]/div[5]/div[2]/div[1]/input[2]`

**输入框 9**:
- **name**: ``
- **id**: ``
- **type**: `text`
- **placeholder**: `请选择`
- **class**: `el-input__inner`
- **是否可见**: True
- **xpath**: `//*[@id="app"]/section[1]/div[1]/div[2]/div[2]/ul[1]/div[1]/span[2]/div[1]/div[1]/input[1]`

### 搜索按钮

**按钮 1**:
- **text**: `搜索`
- **id**: ``
- **type**: `submit`
- **class**: `megaloscope`
- **xpath**: `//*[@id="app"]/section[1]/div[1]/div[1]/div[1]/div[1]/button[1]`

**按钮 2**:
- **value**: `搜索`
- **id**: `megaloscopebtn`
- **type**: `submit`
- **class**: `submit`
- **xpath**: `//*[@id="megaloscopeBtn"]`


## 4. 搜索结果结构

- **结果数量**: 6

### 示例结果条目

**条目 1**:

**条目 2**:

**条目 3**:

## 5. 分页机制

- **分页元素数量**: 1

## 6. 详情页链接格式

### 示例详情页链接

**链接 1**:
- **URL**: `https://bszs.conac.cn/sitename?method=show&id=05ED98C8AABE5B4CE053012819ACD35B`
- **文本**: 

---

## 自动化脚本建议

根据 Selenium 探索结果:

1. **搜索输入框已找到**，可以使用以下 XPath 定位:
   - `//*[@id="title"]`
   - `//*[@id="app"]/section[1]/header[1]/div[3]/div[1]/div[1]/div[1]/input[1]`

2. **URL参数**: 使用 `keywords` 参数可以直接触发搜索
   - 示例: `fullSearchingGd?keywords=体育`


---

*此报告由 GDGPOSeleniumExplorer 自动生成*
