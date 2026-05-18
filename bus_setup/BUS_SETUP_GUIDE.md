# 大总管（RPA）总线搭建指南

> 大总管（RPA）在本工作流中的角色是**纯信号总线**，绝不执行业务代码。

---

## 0. 前置准备

1. 已部署 大总管（RPA）。
2. 已分别启动以下三个客户端，记录其窗口标题（用于 大总管切窗匹配）：
   - **规划师专属客户端**
   - **执行者专属客户端**
   - **审计员客户端**
3. 已克隆模板到目标项目目录，例如 `03MyProject/`。
4. 已编辑 `config/workflow.toml`，填入：
   - `shadow_path`：指向 `<项目根>/Shadow/` 的绝对路径
   - `webhook_url`：钉钉/飞书机器人地址（暂可留空 `""`）
   - 三个 AI 客户端的窗口标题匹配模式

---

## 1. 主循环逻辑（伪代码）

```
LOOP forever:
    file = wait_file_appear(shadow_path, pattern="TRIGGER_*.md", timeout=1200s)
    if timeout:
        http_post(webhook_url, body="[BLOCKED] 20 min no signal")
        continue  # 继续监听，不退出

    name = basename(file)
    route(name, file)
    delete_file(file)
END LOOP
```

`route(name, file)` 按 `triggers_dictionary.md` 的路由表分发。

---

## 2. 路由动作（每条 = 一个 大总管步骤）

每条信号的处理动作模式相同：

```
STEP 1  激活目标窗口         （根据 workflow.toml 中的窗口标题匹配）
STEP 2  等待 0.5 - 1 秒       （窗口前台稳定）
STEP 3  读取提示词文件         （从 bus_setup/prompts/<对应>.txt）
STEP 4  写入系统剪贴板         （UTF-8 文本）
STEP 5  模拟按键 Ctrl+V        （粘贴）
STEP 6  模拟按键 Enter         （发送）
STEP 7  删除原信号文件         （TRIGGER_*.md）
```

`TRIGGER_ROUTE_C_ESCALATE.md` 例外：在 STEP 1 之前先执行一次 `http_post(webhook_url, ...)`，发不出去也不阻塞后续。

---

## 3. 窗口标题匹配建议

每个 AI 角色实际由哪个 IDE / 客户端承载（如 Kiro / Codex / CodeBuddy / 其他）由你（项目维护者）决定。把对应客户端窗口标题中**最稳定的关键字或正则**填进 `config/workflow.toml` 的 `[bus_windows]` 段。

| 角色 | 在 workflow.toml 中的 key | 应填值（举例：填客户端的窗口标题特征） |
|---|---|---|
| 规划师 | `planner_pattern` | 填承载规划师的客户端窗口标题特征 |
| 执行者 | `executor_pattern` | 填承载执行者的客户端窗口标题特征 |
| 审计员 | `auditor_pattern` | 填承载审计员的客户端窗口标题特征 |

如同时打开两份相同客户端实例，用更严格的标题（如包含项目名）防止误切。

---

## 4. 防呆与避坑

### 4.1 信号去重
偶发情况下 大总管可能在文件 rename 完成那一瞬间触发两次。建议在路由开头加幂等锁：处理某信号时立即 `rename` 它为 `TRIGGER_xxx.handling`，路由完再删除，避免重复触发。

### 4.2 剪贴板冲突
若用户期间手动复制了别的内容到剪贴板，大总管注入的提示词会被覆盖。建议：
- 提示词写入剪贴板后立刻 Ctrl+V（间隔 < 100ms）；
- 写入前备份原剪贴板，路由结束后还原。

### 4.3 窗口被最小化
若目标窗口被最小化或被另一个全屏程序遮挡，大总管切窗可能失败。建议在 STEP 1 加重试：失败后 sleep 1s 再试，最多 3 次。

### 4.4 Shadow/ 残留信号
启动 大总管（RPA） 主循环前，建议先**清空** `Shadow/` 目录里的旧 `TRIGGER_*.md`（用 `bootstrap_reset.bat`）。否则可能上来就跑错路由。

### 4.5 中文路径
若项目目录含中文（如 `02 program`），确保 大总管的文件监听器使用 UTF-8 路径解析；剪贴板写入也用 UTF-8。

### 4.6 自动 Git 提交（PASS 路径专属）

当大总管检测到 `TRIGGER_ROUTE_A_PASS.md` 时，路由动作的**第一步**是调用 `bus_setup/git_commit.bat`（**先于切窗注入提示词**）。该脚本：

1. 读取 `<项目根>/reviews/` 下编号最大的 `.meta.json`，确认 status = PASS
2. 提取 `task_id` / `version` / `reason_short`
3. 在 `<项目根>` 下执行 `git add . && git commit -m "[TASK-XXX][V<n>][PASS] <reason_short>"`
4. 检查 `<项目根>/plan/PLAN_INDEX.md` 是否含"待打 phase-N-done"标记，若有则 `git tag phase-N-done`

**约束**：
- 仅在 PASS 路径自动 commit。REJECT / ESCALATE 永不 commit（避免污染历史）。
- 项目目录无 `.git` → 脚本静默跳过，不阻塞路由。
- commit 失败（冲突、签名要求等）→ 大总管记录到 `<项目根>/Shadow/_git_fallback.log` 并继续路由（不阻塞流程）。
- 推荐 `init_project.bat` 已在初始化时执行 `git init` + 首个空 commit 作为基线，避免首次 commit 失败。

### 4.7 时间格式速查（铁律）

工作流中**所有产出物**的时间字段必须精确到秒。各处具体格式：

| 出现位置 | 格式 | 示例 |
|---|---|---|
| 文档标题（`CURRENT_TASK.md` / `EXECUTOR_OUTPUT.md` / `REVIEW_REPORT_v[n].md` / `PLAN_INDEX.md`） | `[YYYY-MM-DD HH:MM:SS]` | `[2026-05-16 14:30:22]` |
| 元信息表"生成时间"（`PRD.md` / `TECH_DESIGN.md` / `EXECUTION_PLAN.md`） | `YYYY-MM-DD HH:MM:SS` | `2026-05-16 14:30:22` |
| `EXECUTION_PLAN.md` 变更日志 | `（YYYY-MM-DD HH:MM:SS）` | `（2026-05-16 14:30:22）` |
| `PLAN_DONE.md` 归档行 | `[完成于 YYYY-MM-DD HH:MM:SS]` | `[完成于 2026-05-16 14:30:22]` |
| `REVIEW_REPORT_v[n].meta.json` 的 `timestamp` | ISO 8601 含秒和时区 | `"2026-05-16T14:30:22+08:00"` |
| Webhook body 的 `timestamp` | 同上 | `"2026-05-16T14:30:22+08:00"` |
| 归档目录名（`bootstrap_reset.bat` 自动生成） | `YYYYMMDD_HHMMSS` | `20260516_143022` |

**禁止**：仅日期、`HH:MM`、模糊措辞（"刚才"、"上午"、"昨天"）。

---

## 5. Webhook 推送约定

`config/workflow.toml` 中 `webhook_url` 为空时，所有推送动作改为本地写日志（追加到 `<项目根>/Shadow/_webhook_fallback.log`），不阻塞流程。

推送 body 模板（JSON）：

```json
{
  "event": "BLOCKED" | "ESCALATE",
  "project": "<项目名>",
  "timestamp": "YYYY-MM-DDTHH:MM:SS+08:00",
  "detail": "<简短原因>"
}
```

---

## 6. 启动顺序

1. 三个 AI 客户端打开并登录就绪
2. 双击 `bootstrap_reset.bat` 清场（首次可跳过）
3. 启动 大总管（RPA） 主循环（按本指南配置好的工作流）
4. 双击 `bootstrap.bat` 投递首封 `TRIGGER_PHASE_1_PLAN.md`
5. 之后只需观察 `Shadow/` 里的信号流转
