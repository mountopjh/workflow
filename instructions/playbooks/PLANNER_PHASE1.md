# Playbook · 规划师 · 开新单（PHASE_1 / ROUTE_A_PASS 共用）

> 适用触发：`TRIGGER_PHASE_1_PLAN.md` 或 `TRIGGER_ROUTE_A_PASS.md`  
> 前置：已读 `PLANNER_CORE.md`、`<项目根>/plan/PLAN_INDEX.md`、`<项目根>/docs/EXECUTION_PLAN.md`

---

## 本次额外允许读
- `<项目根>/plan/PLAN_BACKLOG.md`（排下一单时必读）
- `<项目根>/docs/PRD.md`（首单或方向重大调整时）
- `<项目根>/docs/TECH_DESIGN.md`（步骤需要查接口/数据结构时）
- `playbooks/PLANNER_FIRST_PRINCIPLES.md`（仅当本次任务命中第一性原理触发条件）

> 仍**禁读** `EXECUTOR_OUTPUT.md`、`PLAN_DONE.md`、历史 REVIEW 正文。

---

## 标准动作序列

### Step 1 · 读 PLAN_INDEX 与执行方案
- 从 `PLAN_INDEX.md` 取当前焦点（哪个环节 / 哪个工单已完成 / 下一个候选）。
- 翻 `EXECUTION_PLAN.md` 找到对应"环节 N"。
- **三级版本校验**（任一不一致 → 投递 ESCALATE，不得自行拆单）：
  1. `PLAN_INDEX.md` 的"关联执行方案版本" == `EXECUTION_PLAN.md` 元信息"版本"
  2. `EXECUTION_PLAN.md` 元信息"关联 PRD 版本" == `<项目根>/docs/PRD.md` 元信息"版本"（首单或读 PRD 时校验，仅读这两份元信息表，禁全文）
  3. `EXECUTION_PLAN.md` 元信息"关联技术文档版本" == `<项目根>/docs/TECH_DESIGN.md` 元信息"版本"（读 TECH_DESIGN 时校验）

  > 任意校验失败说明上游文档被改但下游未跟，必须人工介入决定如何对齐版本——你只能 ESCALATE，不能猜。

### Step 2 · ROUTE_A_PASS 专属：归档上一单
（仅 ROUTE_A_PASS 触发时执行；PHASE_1 跳过）
1. 在 `PLAN_INDEX.md` 中把当前焦点任务划销，"完成" +1。
2. 把刚完成任务从 `PLAN_BACKLOG.md` 移动到 `PLAN_DONE.md`。
3. 检查刚完成的工单是否是当前环节的最后一单：
   - 是 → 该环节标记完成；如果执行方案中该环节"是否打 Git tag"= 是，在 `PLAN_INDEX.md` 中标注"环节 N 全部完成，需打 tag <tag 名>"，大总管会读这个标记触发打 tag。
   - 否 → 继续。
4. 更新 `PLAN_INDEX.md`（先 `.tmp` → `rename`）。

### Step 3 · 选下一单
- 从 `EXECUTION_PLAN.md §N.5` 取**下一个未发出的工单**（按工单序号顺序）。
- 不允许跳过工单、不允许合并工单、不允许新增工单。
- 检查该工单是否需要打 `#FirstPrinciples` 标签：
  - 执行方案中该步骤显式引用第一性原理；或
  - **当前工单累计驳回 ≥ 1**（查询方式见下方"驳回数查询"）；或
  - 属新功能 / 架构选型 / 性能优化。
- 如命中 → **加载 `PLANNER_FIRST_PRINCIPLES.md`** 完成 §5 段。

#### 驳回数查询（权威来源 = `.meta.json`）

驳回数的**唯一权威来源**是 `<项目根>/reviews/REVIEW_REPORT_v[*].meta.json`，不要看 `PLAN_INDEX.md` 的"累计统计"（那是项目级总数，不是单个工单）。

查询步骤：
1. 列出 `<项目根>/reviews/` 下所有 `.meta.json`
2. 筛选 `task_id` 等于即将发出的工单 ID 的条目
3. 取版本号最大的那条，读 `reject_count_after_this` 字段
4. 该值即"当前工单累计驳回数"

若 `reviews/` 目录不存在或无匹配条目 → 累计为 0（首次发单/全新工单）。

> 仅本步骤允许 `ls reviews/` 与读 `.meta.json`，**禁读** REVIEW 正文（仍在禁读清单内，除 ESCALATE 路径外）。

### Step 4 · 写 CURRENT_TASK.md
按 `PLANNER_CORE.md §2` 的骨架填全 6 段。**关键约束**：
- §1 必含 `**执行方案锚点**：本单对应 EXECUTION_PLAN.md V<x.y> 环节 N · 工单 K`
- §2 任务点 = 执行方案 §N.5 工单 K 的步骤清单，**逐字抄录禁增减**
- §3 授权文件 = 执行方案 §N.5 工单 K 的"预计授权文件"
- §4 适用红线 = 执行方案 §N.5 工单 K 的"适用红线"
- 颗粒度红线：任务点 ≤ 5 / 授权文件 ≤ 5 / 总长 ≤ 200 行  
- 原子落盘：先 `.tmp` → `rename`

### Step 5 · 同步 PLAN_INDEX
把新工单设为"当前焦点（执行中）"，更新"下一步候选"和"当前环节进度（K/总数）"。  
原子落盘：先 `.tmp` → `rename`。

### Step 6 · 投递触发器（最后一动）
在 `<项目根>/Shadow/` 生成 `TRIGGER_PHASE_2_EXECUTE.tmp` → `rename` 为 `.md`。

完成后**停手等待**，不要做其他动作。

---

## 常见踩坑

- ❌ 在执行方案之外凭空发明任务点 → 严禁
- ❌ 步骤复述时"优化"措辞 → 必须逐字抄
- ❌ 忘记在 §1 写"执行方案锚点" → 审计员定位不到对应工单，可能 REJECT
- ❌ 执行方案版本与 PLAN_INDEX 记录不一致还硬发单 → 应当 ESCALATE
- ❌ 第一性原理触发条件命中却不加载 `PLANNER_FIRST_PRINCIPLES.md` → 审计员反向追问并 REJECT
- ❌ 忘了更新 `PLAN_INDEX.md` 累计统计 → 大总管打 tag 逻辑会失败
