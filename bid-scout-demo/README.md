# BidScout Demo — 体育服务运营类招投标信息采集

## 概述

BidScout 是一个基于 Playwright 的多站点招投标信息采集 demo，验证以下能力链路：

1. 稳定打开并操作两个政府网站
2. 为两个网站创建固定标签页，子 agent 在各自标签页内工作
3. 从每个网站抓取少量有效信息（3-5 条）
4. 基于关键词做"体育服务运营"相关性筛选
5. 汇总为 JSON + HTML 报告
6. 子 agent 生命周期管理（创建、等待、回收、清理）

## 目标网站

| 站点 | URL | 策略 |
|------|-----|------|
| 广州市体育局（高精度） | https://tyj.gz.gov.cn/tzgg/cgzb/ | 列表页直接提取 + 详情页摘要 |
| 广东政府采购网（高覆盖） | https://gdgpo.czt.gd.gov.cn/ | 多候选入口探测 + 列表提取 |

## 快速开始

### 1. 安装依赖

```bash
cd d:\openclaw\workspace\bid-scout-demo
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. 运行 demo

```bash
# 默认模式：打开浏览器窗口，可观察采集过程
python main.py

# 无头模式
python main.py --headless

# 自定义参数
python main.py --max-items 3 --verbose
```

### 3. 查看输出

运行完成后，会在 `output/` 目录生成：

- `output/report.json` — 结构化 JSON 数据
- `output/report.html` — 可视化 HTML 报告（浏览器打开）
- `output/screenshots/` — 各页面截图

## 项目结构

```
bid-scout-demo/
├── main.py                  # 总控入口
├── config.py                # 全局配置
├── orchestrator.py          # 编排器：子agent生命周期管理
├── tab_manager.py           # 标签页管理：创建/绑定/锁/校验
├── agents/
│   ├── base_agent.py        # 子agent基类
│   ├── gz_tyj_agent.py      # 广州体育局采集agent
│   └── gdgpo_agent.py       # 广东政府采购网采集agent
├── adapters/
│   ├── gz_tyj_adapter.py    # 广州体育局页面解析
│   └── gdgpo_adapter.py     # 广东政府采购网页面解析
├── filters/
│   └── keyword_filter.py    # 关键词匹配与打分
├── reporters/
│   ├── json_writer.py       # JSON 输出
│   └── html_reporter.py     # HTML 报告
└── output/                  # 运行输出
```

## 架构设计

### 子 agent 生命周期

```
Orchestrator
  ├── 创建 TabManager → 建立 2 个固定标签页
  ├── 创建 subagent_a (广州体育局) → 绑定 tab_gz_tyj
  ├── 创建 subagent_b (广东采购网) → 绑定 tab_gdgpo
  ├── asyncio.gather 并发启动两个 agent
  │   ├── agent 内部: initialize → execute → cleanup
  │   └── 浏览器操作通过 asyncio.Lock 串行化
  ├── 汇总结果 → 关键词筛选 → 生成报告
  └── 清理所有资源
```

### 标签页绑定机制

每个标签页通过 `TabBinding` 绑定：
- `alias`: 唯一标识（`tab_gz_tyj` / `tab_gdgpo`）
- `expected_domain`: 域名校验
- `page`: Playwright Page 对象引用
- `lock`: asyncio.Lock 互斥锁

每次浏览器操作前自动校验 URL 域名匹配，不匹配则重新导航。

### 浏览器动作串行 + agent 逻辑并行

两个 agent 通过 asyncio 并发运行，但浏览器操作通过标签页级 `asyncio.Lock` 串行化。原因：
- OpenClaw relay 模式同一时刻只能 attach 一个标签页
- 串行操作避免触发政府网站 WAF 风控
- demo 级数据量下串行性能完全可接受

## 关键词筛选

| 场景 | 等级 | 分数范围 |
|------|------|----------|
| 同时命中体育词 + 服务运营词 | high | 0.8 - 1.0 |
| 仅命中体育词 | medium | 0.5 - 0.7 |
| 仅命中服务运营词 | low-medium | 0.2 - 0.4 |
| 均未命中 | low | 0.0 |

## 遇到验证码/登录怎么办

demo 不包含任何验证码绕过逻辑。如果遇到：
1. 在 `--headless` 模式下不可处理，请改用默认模式（有浏览器窗口）
2. 在浏览器窗口中手动完成验证/登录
3. 当前 demo 无暂停等待机制，如需此功能属于后续扩展

## 当前 demo 已支持

- [x] 双站点固定标签页创建与绑定
- [x] 标签页级互斥锁
- [x] 域名校验与自动恢复
- [x] 广州体育局列表页 + 详情页采集
- [x] 广东政府采购网多入口探测 + 列表采集
- [x] 关键词双维度打分（体育词 + 服务运营词）
- [x] JSON + HTML 报告输出
- [x] 子 agent 生命周期管理（创建/执行/清理）
- [x] 单站点失败不阻塞另一站点
- [x] 页面截图保存
- [x] 异常信息记录

## 当前限制

- 不支持大规模翻页（仅抓取当前页）
- 不支持验证码自动处理
- 不支持登录态管理
- 适配器选择器可能因网站改版失效（需维护更新）
- 浏览器操作串行（非真正并行）
- 广东政府采购网页面结构复杂，提取稳定性低于广州体育局

## 后续扩展建议（优先级排序）

1. **人工接管机制**: 检测到验证码时暂停 agent，等用户手动处理后恢复
2. **分页支持**: 实现翻页逻辑，提高数据覆盖量
3. **选择器维护工具**: 提供选择器调试/验证工具，降低页面改版适配成本
4. **OpenClaw relay 集成**: 通过 OpenClaw Gateway API 发送 browser 命令，实现真正的 relay 模式
5. **更多站点适配**: 添加中国政府采购网等全国性平台
6. **NLP 增强筛选**: 引入文本相似度/语义匹配替代简单关键词
7. **定时调度**: 通过 cron/heartbeat 定期执行采集
8. **增量采集**: 基于已采集 URL 去重，仅抓取新公告
