# Playbook · 规划师 · 救火（ROUTE_C_ESCALATE）

> 适用触发：`TRIGGER_ROUTE_C_ESCALATE.md`  
> 前置：已读 `PLANNER_CORE.md` 与 `<项目根>/plan/PLAN_INDEX.md`

---

## 本次额外允许读
- `<项目根>/reviews/REVIEW_REPORT_v[n].md` 中**编号最大的一份正文**（仅最新一份，用于救火复盘）
- `playbooks/PLANNER_FIRST_PRINCIPLES.md`（**强制加载**：救火工单必须重新做第一性原理拆解）
- `<项目根>/plan/PLAN_BACKLOG.md`（如果决定换一条任务路径）
- `<项目根>/docs/PRD.md`（如果方向需要重新对照需求）
- `<项目根>/docs/TECH_DESIGN.md`（若救火涉及接口/架构层调整）
- `<项目根>/docs/EXECUTION_PLAN.md`（必读：救火本质是修订方案对应位置）

> 仍**禁读** `EXECUTOR_OUTPUT.md`、`PLAN_DONE.md`、历史 REVIEW 正文（仅最新 1 份例外）。

---

## 标准动作序列

### Step 1 · 读最新 REVIEW 正文
重点看：
- `§4 第一性原理穿透`（审计员 是否判定方向偏航）
- `§5 判定细则与结论`（具体卡在哪）
- `驳回累加器`（确认确实是 ESCALATE）

### Step 2 · 识别症结类型
| 症结类型 | 判别依据 | 应对策略 |
|---|---|---|
| 方向错误 | 审计员 §4.4 判定"方向偏航" | 新工单**必加** `#FirstPrinciples`，重做 §5 拆解 |
| 技术死桩 | 某依赖/接口反复失败 | 改方案绕开，必要时换技术栈，新工单 §5 说明绕道理由 |
| 歧义阻塞 | 执行者 反复理解错任务 | 工单切更小，每点只允许一个动作；§1 加"理解校验问答"段 |
| 方案与实际对不上 | 执行方案版本号与 PLAN_INDEX 记录不符；或工单内容在方案里找不到 | 暂停发新单；在 §1 标注"待人类修订 EXECUTION_PLAN.md"；不重启流程，等待人工介入 |

### Step 3 · 更新 PLAN_INDEX
- "熔断" +1
- 当前焦点保持指向同一任务（同 task_id），但版本号 V↑
- 原子落盘：先 `.tmp` → `rename`

### Step 4 · 加载 PLANNER_FIRST_PRINCIPLES 并重写 CURRENT_TASK.md
按 `PLANNER_CORE.md §2` 骨架重写。**强制要求**：
- §1 必须含"上一轮失败原因复盘"段（≤ 5 行，引用 REVIEW 中的具体段号）
- §5 必须按 `PLANNER_FIRST_PRINCIPLES.md` 三步法重做（即使原工单已写过，也要重写，因为方向已被否决）
- 工单 `task_id` 保持与原工单相同（同一任务的多次重试），版本号 V↑
- 原子落盘：先 `.tmp` → `rename`

### Step 5 · 投递触发器
在 `<项目根>/Shadow/` 生成 `TRIGGER_PHASE_2_EXECUTE.tmp` → `rename` 为 `.md`。

完成后**停手等待**。

---

## 救火铁律

- ❌ 救火工单不重做第一性原理 → 大概率第二次还是 ESCALATE
- ❌ 改了 `task_id` → 累加器统计错乱
- ❌ 在原工单基础上小修小补 → 治标不治本
- ✅ 必要时**整段废弃原方案**，从 PRD 重新出发
- ✅ §1 复盘段如实承认上轮误判
