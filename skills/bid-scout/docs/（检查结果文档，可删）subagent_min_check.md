# 最小双子 Agent 并发验证方案

> **目标**：验证 OpenClaw 环境是否支持 `sessions_spawn` + 多标签页 + `targetId` 这条并发技术路线。  
> **不做**：真实采集、关键词筛选、报告生成、人工接管。  
> **预计耗时**：3-5 分钟。

---

## 1. 并发依赖点摘要

bid-scout 的多站点并发采集依赖以下 6 个能力层，任何一层失败都会导致并发方案不可用：

| # | 能力层 | 依赖的 OpenClaw 工具 | 已知风险 |
|---|--------|----------------------|----------|
| L1 | 浏览器连接 | `browser status` | Chrome Relay 未开启 |
| L2 | 多标签页创建 | `browser open url:"..."` | 返回 "tab not found" |
| L3 | targetId 稳定性 | `browser screenshot targetId:"..."` | targetId 存在但后续操作报错 |
| L4 | 子 Agent 创建 | `sessions_spawn ... mode:"session"` | 返回 runId 但子 Agent 实际不存在 |
| L5 | 子 Agent 可查询 | `sessions_list` / `subagents` | 看不到已创建的子 Agent |
| L6 | 子 Agent + targetId 联动 | 子 Agent 内执行 `browser screenshot targetId:"..."` | 子 Agent 无法操作指定标签页 |

---

## 2. 最小验证步骤（共 7 步）

### 检查点 0：浏览器连接

```
browser status
```

- **通过**：返回 connected / 显示 tab 信息
- **失败**：报错或 disconnected → 先连接 Chrome Relay 再继续

---

### 检查点 1：创建 2 个标签页

**标签页 A**（当前标签页导航）：
```
browser navigate url:"https://example.com"
```
→ 记录返回的 `targetId`，记为 **TID_A**

等待 2 秒：
```
exec command:"sleep 2"
```

**标签页 B**（新开标签页）：
```
browser open url:"https://httpbin.org/html"
```
→ 记录返回的 `targetId`，记为 **TID_B**

等待 2 秒：
```
exec command:"sleep 2"
```

**列出所有标签页**：
```
browser tabs
```

- **通过**：tabs 列表中出现 2 个 tab，且能看到 example.com 和 httpbin.org
- **失败**：`browser open` 报错 / tabs 只看到 1 个 / TID_B 为空

---

### 检查点 2：验证 targetId 稳定性

分别对两个 targetId 执行 screenshot：

```
browser screenshot targetId:"{TID_A}"
```

```
browser screenshot targetId:"{TID_B}"
```

- **通过**：两张截图分别显示 example.com 和 httpbin.org 的页面内容
- **失败**：报 "tab not found" / 截图内容与预期 URL 不匹配

---

### 检查点 3：创建子 Agent A

```
sessions_spawn task:"你是最小验证子 Agent A。

你的唯一任务：
1. 执行 browser screenshot targetId:\"{TID_A}\"
2. 如果成功，回复：CHECK_A_PASS: screenshot 成功，targetId={TID_A}
3. 如果失败（报错），回复：CHECK_A_FAIL: [错误信息]

注意：
- 只做这一件事，不做其他任何操作
- 必须携带 targetId 参数
- 完成后立即结束" label:"min-check-A" mode:"session"
```

→ 记录返回的 `runId`，记为 **RUN_A**

- **通过**：返回 runId（非空字符串），无报错
- **失败**：报 "thread=true not available" / 返回错误 / runId 为空

---

### 检查点 4：创建子 Agent B

```
sessions_spawn task:"你是最小验证子 Agent B。

你的唯一任务：
1. 执行 browser screenshot targetId:\"{TID_B}\"
2. 如果成功，回复：CHECK_B_PASS: screenshot 成功，targetId={TID_B}
3. 如果失败（报错），回复：CHECK_B_FAIL: [错误信息]

注意：
- 只做这一件事，不做其他任何操作
- 必须携带 targetId 参数
- 完成后立即结束" label:"min-check-B" mode:"session"
```

→ 记录返回的 `runId`，记为 **RUN_B**

- **通过**：返回 runId（非空字符串），无报错
- **失败**：同检查点 3

---

### 检查点 5：验证子 Agent 可查询

等待 10 秒让子 Agent 执行：
```
exec command:"sleep 10"
```

查询子 Agent 列表：
```
sessions_list
```

或：
```
subagents
```

- **通过**：列表中出现 min-check-A 和 min-check-B（或对应 sessionKey）
- **失败**：列表为空 / 看不到已创建的子 Agent

---

### 检查点 6：收集子 Agent 结果

查看子 Agent A 的历史：
```
sessions_history sessionKey:"agent::subagent:{RUN_A}"
```

查看子 Agent B 的历史：
```
sessions_history sessionKey:"agent::subagent:{RUN_B}"
```

- **通过**：
  - A 的历史中包含 `CHECK_A_PASS` 字样
  - B 的历史中包含 `CHECK_B_PASS` 字样
  - 两个子 Agent 分别在不同 targetId 上完成了 screenshot
- **部分通过**：只有一个 PASS
- **失败**：两个都是 FAIL / 历史为空 / sessionKey 不存在

---

### 检查点 7：清理

```
browser close targetId:"{TID_B}"
```

（TID_A 是原始标签页，通常不需要关闭）

---

## 3. 可直接发送给 OpenClaw Agent 的验证指令

将以下内容**完整复制**，发送给你的 OpenClaw Agent（通过飞书）：

---

```
请执行最小双子 Agent 并发验证，不要做真实采集。严格按以下步骤操作，每一步都报告结果：

【第一步】检查浏览器连接
browser status
→ 报告：connected 还是 disconnected

【第二步】创建 2 个标签页
1. browser navigate url:"https://example.com"
   → 记录 targetId 为 TID_A
2. exec command:"sleep 2"
3. browser open url:"https://httpbin.org/html"
   → 记录 targetId 为 TID_B
4. exec command:"sleep 2"
5. browser tabs
   → 报告：看到几个 tab，TID_A 和 TID_B 分别是什么

【第三步】验证 targetId
1. browser screenshot targetId:"{TID_A}"
   → 报告：截图是否显示 example.com
2. browser screenshot targetId:"{TID_B}"
   → 报告：截图是否显示 httpbin.org

【第四步】创建子 Agent A
sessions_spawn task:"你是最小验证子 Agent A。你的唯一任务：1. 执行 browser screenshot targetId:\"{TID_A}\" 2. 如果成功回复 CHECK_A_PASS: screenshot 成功 3. 如果失败回复 CHECK_A_FAIL: 错误信息。只做这一件事。" label:"min-check-A" mode:"session"
→ 报告：runId 是什么，是否报错

【第五步】创建子 Agent B
sessions_spawn task:"你是最小验证子 Agent B。你的唯一任务：1. 执行 browser screenshot targetId:\"{TID_B}\" 2. 如果成功回复 CHECK_B_PASS: screenshot 成功 3. 如果失败回复 CHECK_B_FAIL: 错误信息。只做这一件事。" label:"min-check-B" mode:"session"
→ 报告：runId 是什么，是否报错

【第六步】等待并查询
1. exec command:"sleep 15"
2. sessions_list
   → 报告：能看到哪些子 Agent
3. sessions_history sessionKey:"agent::subagent:{RUN_A 的值}"
   → 报告：A 的结果是 PASS 还是 FAIL
4. sessions_history sessionKey:"agent::subagent:{RUN_B 的值}"
   → 报告：B 的结果是 PASS 还是 FAIL

【第七步】清理
browser close targetId:"{TID_B}"

【最后】汇总报告
请用表格汇总每个检查点的通过/失败状态：
| 检查点 | 能力 | 结果 | 备注 |
并给出最终结论：并发技术路线是否可行。
```

---

## 4. 判定标准

### 全部通过 ✅

所有 7 个检查点均 PASS → 并发技术路线可行，可以在 bid-scout 中使用 sessions_spawn + 多 tab + targetId 方案。

### 部分通过 ⚠️

| 通过到哪一步 | 含义 | 后续建议 |
|-------------|------|----------|
| 到检查点 1 | 多 tab 可用，但 targetId 或子 Agent 有问题 | 需要排查 L3-L6 |
| 到检查点 2 | targetId 稳定，但 sessions_spawn 失败 | 只能用顺序执行模式 |
| 到检查点 4 | 子 Agent 创建成功，但查询不到或结果失败 | 排查 L5-L6 |
| 到检查点 5 | 子 Agent 存在但 browser 操作失败 | targetId 在子 Agent 上下文中不可用 |

### 全部失败 ❌

检查点 0 就失败 → 浏览器未连接，先解决 Chrome Relay。
检查点 1 就失败 → 单 tab 都不稳定，所有 browser 方案都有问题。

---

## 5. 故障排查层级

按优先级从高到低排查：

### Level 1: `browser open` 失败
- **现象**：报 "tab not found" 或返回空 targetId
- **原因**：Chrome Relay 扩展版本不支持 `open` / 浏览器连接不稳定
- **对策**：确认 Relay 扩展版本；尝试手动在 Chrome 中新开标签页后 `browser tabs` 看能否发现

### Level 2: `targetId` 不稳定
- **现象**：tabs 看得到，但 `screenshot targetId:"..."` 报错
- **原因**：targetId 是 Chrome DevTools Protocol 的 target ID，标签页刷新/导航后可能变化
- **对策**：在 screenshot 前再次 `browser tabs` 确认 targetId 未变

### Level 3: `sessions_spawn` 失败
- **现象**：报 "thread=true not available" 或返回错误
- **原因**：当前 model provider 不支持 thread/session 模式
- **对策**：检查 `models.json` 中的 provider 配置；尝试不带 `mode:"session"` 只用默认模式

### Level 4: `mode:"session"` 失败
- **现象**：`sessions_spawn` 不带 mode 成功，带 `mode:"session"` 失败
- **原因**：session 模式需要额外的 runtime 支持
- **对策**：先用默认 mode 验证子 Agent 基本能力；session 模式仅影响人工接管通信

### Level 5: 子 Agent 无法使用 `targetId`
- **现象**：子 Agent 创建成功，但 browser 命令报错
- **原因**：子 Agent 的 browser 工具上下文可能与主 Agent 不共享 tab 列表
- **对策**：在子 Agent task 中先让它执行 `browser tabs` 看能否看到标签页列表

### Level 6: `sessions_list` / `sessions_history` 不可用
- **现象**：查询不到子 Agent 或历史为空
- **原因**：sessionKey 格式不正确 / 子 Agent 还没执行完 / sessions 功能受限
- **对策**：延长等待时间；尝试 `subagents` 命令替代；检查 sessionKey 格式

---

## 6. 回传日志要求

执行完毕后，请将以下内容回传：

1. **OpenClaw Agent 的完整回复**（包含每一步的执行结果）
2. 如果 Agent 在某一步卡住或报错，**截图报错信息**
3. 特别关注以下字段：
   - `browser open` 返回的完整 JSON（包含 targetId）
   - `sessions_spawn` 返回的完整 JSON（包含 runId / childSessionKey）
   - `sessions_list` 的完整输出
   - `sessions_history` 的完整输出
   - 任何包含 `error`、`not found`、`not available` 的错误信息

---

## 7. 备选验证：不使用 sessions_spawn

如果 `sessions_spawn` 在检查点 3 即失败，可改为验证"多 tab + 主 Agent 顺序操作"是否可行：

1. 主 Agent 在 TID_A 上 screenshot → 确认 example.com
2. 主 Agent 在 TID_B 上 screenshot → 确认 httpbin.org
3. 主 Agent 在 TID_A 上 snapshot → 获取可访问性树
4. 主 Agent 在 TID_B 上 snapshot → 获取可访问性树

如果以上均成功 → "多 tab + 顺序执行"降级方案可行（bid-scout SKILL.md 中已有此降级策略）。
