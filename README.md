# 通用 AI 协作开发工作流 V6.0

> 规划师（规划）─ 执行者（执行）─ 审计员（审计）─ 大总管（总线） 四角协同  
> 文件驱动通信 · `.tmp` 原子重命名 · 抗提示注入 · 3 次驳回熔断 · 第一性原理穿透  
> 适用范围：任何项目（语言/技术栈无关）

---

## 0. 30 秒读懂

1. 你写好三份输入文档放进 `<项目根>/docs/`：**PRD**（要解决什么）、**TECH_DESIGN**（用什么方案）、**EXECUTION_PLAN**（按环节+步骤的执行序列）。
2. 双击 `bootstrap.bat` 投递首封触发信。
3. **规划师 → 执行者 → 审计员** 三方在本地文件系统里写卷宗、互相点名，**大总管（Workbuddy）是邮差**：监听 `<项目根>/Shadow/`，激活窗口、注入提示词、销毁信号。
4. 规划师**严格按执行方案拆单**——禁凭空发明任务。
5. 审计通过则进入下一单 + 自动 `git commit`；某环节最后一单通过则自动打 `git tag`。驳回回炉；累计驳回 3 次熔断 + Webhook 报警。
6. 全程**所有文件先写 `.tmp`、再 rename 成正式名**。

---

## 1. 四个角色

| 角色 | 实体 | 职责 | 专属规章（**该角色唯一允许读的规则文件**） |
|---|---|---|---|
| **规划师** | 规划师专属客户端 | 维护 `PLAN_INDEX.md` → 拆战术工单 `CURRENT_TASK.md` | `instructions/PLANNER_CORE.md` + 场景 playbook |
| **执行者** | 执行者专属客户端 | 盲读工单 → 写代码+自测 → 产 `EXECUTOR_OUTPUT.md` | `instructions/EXECUTOR_CORE.md` + 场景 playbook |
| **审计员** | 审计员专属客户端 | 拉真实源码 → 比对裁决 → 出 `REVIEW_REPORT_v[n].md` | `instructions/AUDITOR_CORE.md` + `playbooks/AUDITOR_AUDIT.md` |
| **总线** | 大总管（Workbuddy） | 监听 `Shadow/` → 激活窗口 → 剪贴板注入 → 销毁信号 | `bus_setup/BUS_SETUP_GUIDE.md` |

> **铁律 1**：大总管永远只搬信、不跑代码。  
> **铁律 2**：每个 AI 角色**只读自己专属的 CORE + 当前场景 playbook + 工单流转中明确指定的文档**。禁止读其他角色的规则、其他角色的产出原文（除非工单流程明确要求）。
> **铁律 3**：每次唤醒的 prompts 会**显式列出本次允许读取的最小集**，不在清单内的文件一律不读，节流 Token。

---

## 2. 目录结构（关键约定：项目根 = workflow 文件夹的父目录）

```
<项目根>/                                       ← 你的项目根目录
│
├── workflow_template/                    ← workflow（结构永不动）
│   ├── README.md / AGENTS.md
│   ├── bootstrap.bat                          ← 冷启动：在父目录建 Shadow/TRIGGER_PHASE_1_PLAN.md
│   ├── bootstrap_reset.bat                    ← 清场：归档父目录 Shadow/reviews/plan
│   ├── init_project.bat                       ← 初始化：在父目录建空目录骨架 + 复制 PLAN 模板
│   │
│   ├── instructions/                          ← 角色规则
│   │   ├── PLANNER_CORE.md                       ← 规划师 每次必读
│   │   ├── EXECUTOR_CORE.md                      ← 执行者 每次必读
│   │   ├── AUDITOR_CORE.md                  ← 审计员 每次必读
│   │   └── playbooks/                         ← 场景特化（按 prompts 点名加载）
│   │       ├── PLANNER_PHASE1.md / PLANNER_ESCALATE.md / PLANNER_FIRST_PRINCIPLES.md
│   │       ├── EXECUTOR_PHASE2.md / EXECUTOR_REWORK.md / EXECUTOR_FIRST_PRINCIPLES.md
│   │       └── AUDITOR_AUDIT.md / AUDITOR_FIRST_PRINCIPLES.md
│   │
│   ├── templates/                             ← 流转期文档模板（仅人类参考）
│   │   ├── PLAN_INDEX.md / PLAN_BACKLOG.md / PLAN_DONE.md
│   │   ├── CURRENT_TASK.md / EXECUTOR_OUTPUT.md
│   │   └── REVIEW_REPORT_v[n].md / .meta.json
│   │
│   ├── bus_setup/
│   │   ├── BUS_SETUP_GUIDE.md / triggers_dictionary.md
│   │   └── prompts/{6 个 .txt}                ← 哑文本剪贴板源
│   │
│   └── config/
│       ├── workflow.toml                      ← 项目名、超时、Webhook、熔断阈值
│       ├── redlines.toml                      ← 完整红线
│       └── redlines_index.md                  ← AI 按编号查
│
├── Shadow/                                    ← 死信箱（大总管监听这里）
├── src/                                       ← 项目源码（执行者 写）
├── tests/                                     ← 项目测试（执行者 写）
├── plan/                                      ← 大盘（规划师 维护）
│   ├── PLAN_INDEX.md
│   ├── PLAN_BACKLOG.md
│   └── PLAN_DONE.md
├── reviews/                                   ← 审计报告（审计员 写）
│   ├── REVIEW_REPORT_v[n].md
│   └── REVIEW_REPORT_v[n].meta.json
├── docs/                                      ← 项目文档
│   └── PRD.md
├── CURRENT_TASK.md                            ← 规划师 写、执行者 读
└── EXECUTOR_OUTPUT.md                            ← 执行者 写、审计员 读
```

> 这条约定是**物理事实**，不需要任何配置项。所有 prompts 和 instructions 中的 `<项目根>/X` 都基于"workflow 父目录"自动解析。

---

## 3. 各角色读取边界（强制最小集，节省 Token）

每次 大总管注入的提示词会**显式列出本次允许读的最小集**，不在清单内的文件一律不读。

| 角色 | 必读 | 条件读 | **禁读** |
|---|---|---|---|
| **规划师** | `PLANNER_CORE.md` + 当次 playbook（`PLANNER_PHASE1` 或 `PLANNER_ESCALATE`）、`PLAN_INDEX.md` | 排单读 `PLAN_BACKLOG.md`；ESCALATE 救火读最新 1 份 REVIEW 正文；触发条件成立时加载 `PLANNER_FIRST_PRINCIPLES.md` | AGENTS.md、执行者任何产出、其他角色 instructions、`PLAN_DONE.md`、templates |
| **执行者** | `EXECUTOR_CORE.md` + 当次 playbook（`EXECUTOR_PHASE2` 或 `EXECUTOR_REWORK`）、`CURRENT_TASK.md` | 返工读最新 1 份 REVIEW 正文（**仅最新，不读历史**）；按工单 §4 编号查 `redlines_index.md`；工单 §5 触发时加载 `EXECUTOR_FIRST_PRINCIPLES.md` | AGENTS.md、PLAN（除 `#ReadPlan` 例外）、其他角色 instructions、PRD、历史 REVIEW、templates |
| **审计员** | `AUDITOR_CORE.md` + `AUDITOR_AUDIT.md`、`CURRENT_TASK.md`、`EXECUTOR_OUTPUT.md`、全部 `.meta.json`、真实源码 | 累加器 ≥ 1 时加载 `AUDITOR_FIRST_PRINCIPLES.md` + 上一份 REVIEW 正文；按需查 `redlines_index.md` | AGENTS.md、PLAN 任何文件、其他角色 instructions、PRD、历史 REVIEW 正文（除上述例外）、templates |

---

## 4. 一次完整流转

```
人类放下 PRD + 双击 bootstrap.bat
        │
        ▼  Shadow/TRIGGER_PHASE_1_PLAN.md
大总管激活 规划师 → 注入 prompts/phase1_to_planner.txt
        │
        ▼  规划师 写 PLAN_INDEX.md & CURRENT_TASK.md（.tmp→rename）
        ▼  Shadow/TRIGGER_PHASE_2_EXECUTE.md
大总管激活 执行者 → 注入 prompts/phase2_to_executor.txt
        │
        ▼  执行者 写代码+测试 → EXECUTOR_OUTPUT.md
        ▼  Shadow/TRIGGER_PHASE_3_AUDIT.md
大总管激活 审计员 → 注入 prompts/phase3_to_auditor.txt
        │
        ▼  审计员 拉真实源码比对 → REVIEW_REPORT_v[n].md + .meta.json
        ▼  三选一：
   ROUTE_A_PASS ──► 回 规划师 发下一单
   ROUTE_B_REJECT ─► 回 执行者 返工 → 回到第三段
   ROUTE_C_ESCALATE ► Webhook 报警 + 回 规划师 改 PLAN
```

**旁路：QUERY 请示通道（不计驳回）**

执行者实现到一半发现工单本身有问题但又不至于完全卡死时，可走请示路径：
```
执行者 写 QUERY.md → Shadow/TRIGGER_QUERY_TO_PLANNER.md
        ▼
规划师 在 QUERY.md 追加回复（必要时递增 CURRENT_TASK 版本号）
        ▼  Shadow/TRIGGER_QUERY_REPLY.md
执行者 接着原工单干（不重写 EXECUTOR_OUTPUT、不重发 PHASE_2）
```

请示**不影响驳回累加器**。详情见 `bus_setup/triggers_dictionary.md §4`。

---

## 5. 怎么开始一个新项目

> 关键约定：**项目根 = workflow 文件夹的父目录**。把 `workflow_template/` 直接放进你的项目根目录，不要重命名 workflow 文件夹本身。

1. 在你的项目根目录下放入整个 `workflow_template/`（如 `g:\MyProject\workflow_template\`）。
2. 双击 `workflow_template\init_project.bat`，它会：
   - 在父目录建空目录骨架（`Shadow/` `src/` `tests/` `plan/` `reviews/` `docs/`）
   - 复制 `PLAN_*.md` 到 `plan/`
   - 复制 `PRD.md` / `TECH_DESIGN.md` / `EXECUTION_PLAN.md` 到 `docs/`
   - `git init` + 写 `.gitignore` + 首个基线 commit
3. 编辑 `workflow_template\config\workflow.toml`：填 `name`、`webhook_url`、`[bus_windows]` 三个客户端窗口标题。
4. **填写 docs 三件套**：
   - `<项目根>\docs\PRD.md` — 业务目标与硬约束
   - `<项目根>\docs\TECH_DESIGN.md` — 技术方案、模块划分、接口签名、数据结构
   - `<项目根>\docs\EXECUTION_PLAN.md` — 按环节+步骤的执行序列（**这份是规划师拆单的唯一依据**）
5. 编辑 `<项目根>\plan\PLAN_BACKLOG.md` 列出首批任务（也可以直接照执行方案的环节填）。
6. 启动三个 AI 客户端（规划师 / 执行者 / 审计员），保证窗口标题可被大总管识别。
7. 启动大总管（Workbuddy），按 `bus_setup/BUS_SETUP_GUIDE.md` 配置（含自动 git commit 步骤）。
8. **双击 `bootstrap.bat`** 投递首封信。
9. 必要时 `bootstrap_reset.bat` 清场（自动 `git stash` 保护未提交改动）。

---

## 6. 必读顺序（人类）

1. 本 README
2. `AGENTS.md`（铁律详述）
3. `bus_setup/BUS_SETUP_GUIDE.md`
4. 三份 `instructions/*_CORE.md`（按你扮演的角色挑读）
5. `instructions/playbooks/`（场景细节）
