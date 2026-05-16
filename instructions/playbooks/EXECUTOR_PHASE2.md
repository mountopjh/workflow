# Playbook · 执行者 · 首次开干（PHASE_2）

> 适用触发：`TRIGGER_PHASE_2_EXECUTE.md`  
> 前置：已读 `EXECUTOR_CORE.md` 与 `<项目根>/CURRENT_TASK.md`

---

## 本次额外允许读
- 工单 §3 授权清单内的源码 + 直接依赖
- `config/redlines_index.md`（按工单 §4 编号查询）
- `playbooks/EXECUTOR_FIRST_PRINCIPLES.md`（仅当工单 §5 已触发第一性原理）
- `<项目根>/plan/PLAN_INDEX.md`（仅工单标签含 `#ReadPlan` 时）

> 仍**禁读** `PLANNER_*` / `AUDITOR_*`、PLAN（`#ReadPlan` 例外）、PRD、历史 REVIEW、旧版 OUTPUT。

---

## 标准动作序列

### Step 1 · 解析工单
- 抄录 §3 授权文件清单到便签
- 列出 §4 引用的红线编号
- 检查 §5 是否触发第一性原理（如触发 → **加载 `EXECUTOR_FIRST_PRINCIPLES.md`**）
- 检查 §6 的测试命令

### Step 2 · 按需查红线
对 §4 列出的每个编号，去 `config/redlines_index.md` 查具体要求，写在便签上随时核对。

### Step 3 · 写代码
- **仅修改 §3 授权清单内的文件**（越权直接 REJECT）
- 遵守查到的红线（如 R1 流式分批、R3 跨边界容错、R5 文件行数上限等）
- 所有源码改动：先 `.tmp` 落盘 → close → `rename` 为最终扩展名

### Step 4 · 写测试
- 新功能必须有单元测试覆盖
- 测试文件位于 `<项目根>/tests/`，命名遵守 R6（语义化，禁 `test_misc.py` / `helper_test.go` 等）

### Step 5 · 跑测试
执行工单 §6 指定的命令（或 `config/workflow.toml` 的 `[test_commands].default`）。  
**必须全绿**。任何失败 → 回 Step 3 修，**不允许直接交卷**。

### Step 6 · 写 EXECUTOR_OUTPUT.md
按 `EXECUTOR_CORE.md §2` 骨架填全 6 段：
- §3 红线打卡：**逐条**给证据指针（指向源码行号），禁笼统"全部通过"
- §5 第一性原理对照：仅触发时按 `EXECUTOR_FIRST_PRINCIPLES.md` 写，否则一行"本工单不触发"
- §6 风险与遗留：如实写"事实违反"，**禁瞒**

原子落盘：先 `.tmp` → close → `rename`。

### Step 7 · 投递触发器（最后一动）
在 `<项目根>/Shadow/` 生成 `TRIGGER_PHASE_3_AUDIT.tmp` → `rename` 为 `.md`。

完成后**停手等待**。

---

## 常见踩坑

- ❌ 改了授权清单外的文件（哪怕只是修个 import） → REJECT
- ❌ 测试只跑了一部分就交卷 → REJECT
- ❌ §3 红线打卡写"R1 已遵守"无证据 → REJECT
- ❌ 隐瞒"事实违反" → REJECT 且驳回累加器 +1
- ❌ 引入工单未声明的新依赖 → REJECT
- ✅ 改完跑测试，跑过再交卷
- ✅ 模糊的地方在 §6 写明假设，让 审计员 判断
