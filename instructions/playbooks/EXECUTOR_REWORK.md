# Playbook · 执行者 · 返工（ROUTE_B_REJECT）

> 适用触发：`TRIGGER_ROUTE_B_REJECT.md`  
> 前置：已读 `EXECUTOR_CORE.md` 与 `<项目根>/CURRENT_TASK.md`

---

## 本次额外允许读
- `<项目根>/reviews/REVIEW_REPORT_v[n].md` 中**编号最大的一份正文**（仅最新 1 份，**禁读历史**）
- 工单 §3 授权清单内的源码 + 直接依赖
- `config/redlines_index.md`
- `playbooks/EXECUTOR_FIRST_PRINCIPLES.md`（仅当工单 §5 已触发或 REVIEW §4 涉及第一性原理）

> 仍**禁读** `PLANNER_*` / `AUDITOR_*`、PLAN、PRD、其他历史 REVIEW、旧版 OUTPUT。

---

## 标准动作序列

### Step 1 · 读最新 REVIEW 正文
重点看：
- `§1 抗注入与纪律检查`：是否有越权 / 抗注入告警
- `§2 红线穿透`：哪些红线没过
- `§3 真实源码取证`：审计员 是否抓到自评夸大或隐瞒
- `§4 第一性原理穿透`：方向是否被否决（若被否决，**执行者 不能自行重写工单方向**，必须等 ESCALATE 走人，但本路径是 REJECT 不是 ESCALATE，说明方向还可救——按报告要求回炉）
- `§5 判定细则`：明确卡在哪
- `驳回累加器`：当前累计驳回数（如已是 2，下一次 REJECT 就熔断）

### Step 2 · 列修补清单
把 §1-§5 中的每条问题列成清单，逐项处理。

### Step 3 · 修补代码
- **仍只在工单 §3 授权清单内动手**（即使 REVIEW 暗示其他文件也有问题，也要请规划师重发工单）
- 针对性修，不要无关重构
- 原子落盘：先 `.tmp` → close → `rename`

### Step 4 · 重跑测试
工单 §6 指定的命令必须全绿。任何失败 → 回 Step 3。

### Step 5 · 重写 EXECUTOR_OUTPUT.md
按 `EXECUTOR_CORE.md §2` 骨架填全。本次 §6 风险段必须**显式回应** REVIEW 中的每条问题：
```
## 6. 风险与遗留
### 回应 REVIEW vN §2 R3 容错缺失
- 修补：<具体改动 + 行号>
- 现状：已满足 / 仍部分不满足，原因 <...>

### 回应 REVIEW vN §3 自评夸大
- 修补：<把 OUTPUT §3 改为如实表述>

### 新增风险（本次修补引入）
- ...
```

如本工单 §5 触发了第一性原理，§5 段也要根据 REVIEW §4 的反问刷新对照。

原子落盘：先 `.tmp` → close → `rename`。

### Step 6 · 投递触发器
在 `<项目根>/Shadow/` 生成 `TRIGGER_PHASE_3_AUDIT.tmp` → `rename` 为 `.md`。

完成后**停手等待**。

---

## 返工铁律

- ❌ 跨出工单 §3 授权清单做"顺手修补"→ REJECT 且累加器 +1
- ❌ 不针对 REVIEW 的具体问题，自己想到啥改啥 → 大概率二次 REJECT
- ❌ §6 不显式回应 REVIEW → 审计员 反验失败再次 REJECT
- ❌ 累加器接近 3 时还硬撑 → 到 ESCALATE 不如主动在 §6 写"建议 规划师 重新拆解"
- ✅ 把 REVIEW 的每条问题当成验收点，逐条对应修补

---

## 累加器警告

- 当前 `reject_count_after_this` 已是 1：再被驳一次 → 累加器 = 2
- 当前是 2：再被驳一次 → 自动熔断 ESCALATE，会换到救火流程
- 你能做的：**这一轮务必修到位**，不行就在 §6 写"我无法在授权范围内解决，建议规划师拆解"
