# 影刀 RPA 搭建大总管总线全程操作手册（小白版）

> 适用：你从来没用过影刀，想让本工作流通过"影刀"自动跑起来。  
> 读完即可上手。配套理论参考 `BUS_SETUP_GUIDE.md`，本手册只讲"鼠标怎么点"。

---

## 0. 30 秒读懂这份手册要带你做的事

工作流里有个角色叫 **大总管**（由影刀 RPA 实际承载执行）——它是一个"邮差机器人"，干三件事：

1. 盯着 `<项目根>/Shadow/` 文件夹，等里面出现 `TRIGGER_*.md` 文件
2. 一旦出现，把对应的**提示词文本**复制到剪贴板，切到对应的 **AI 客户端窗口**，按 `Ctrl+V` + `Enter` 发出去
3. 删掉这个 `TRIGGER_*.md`，回到第 1 步继续盯

**就这么三件事**，干一辈子。我们要做的事就是用影刀把这三件事拼成一个"流程"。

> 项目里已经有个 Python 版本（`bus_setup/bus_monitor.py`），影刀版的目标是用零代码方式实现同样的功能。两者二选一即可，不要同时跑。

---

## 1. 影刀是什么（小白第一课）

- **影刀 RPA** 是一款国产可视化"流程机器人"软件，把"鼠标点哪、键盘按啥、什么时候做"用拖块的方式画出来。
- 官网：<https://www.yingdao.com/>（免费个人版够用）
- 关键词速对照：
  - **应用 / 流程**：你画的那个"机器人脚本"，相当于一个 `.py` 文件
  - **流程块 / 指令**：每一个动作，相当于一行代码
  - **变量**：拖来拖去的数据
  - **运行 / 调试**：手动跑一遍看效果

---

## 2. 安装与首次启动

1. 浏览器打开 <https://www.yingdao.com/>，注册账号（手机号即可）。
2. 下载并安装"影刀 RPA"客户端（Windows 版，本工作流只在 Windows 上验证过）。
3. 启动影刀，登录账号。首次会引导你看 1-2 个 demo，**跳过即可**，我们这就开始建自己的。
4. 主界面左上角点 **「我的应用」 → 「新建应用」**，类型选 **「桌面应用」**，名字填 `RPA_Bus`。
5. 进入应用后看到"画布 + 左侧指令面板"。这就是我们工作的地方。

---

## 3. 核心概念图解（看一遍就够）

```
影刀的画布 ≈ 一段顺序代码
    ┌─────────────────────────────────────────┐
    │  指令1：循环 (LOOP)                     │
    │  ┌─────────────────────────────────┐    │
    │  │ 指令2：获取文件夹列表           │    │
    │  │ 指令3：判断 (IF)                │    │
    │  │   ┌───────────────────────┐     │    │
    │  │   │ 指令4：读文件         │     │    │
    │  │   │ 指令5：写剪贴板       │     │    │
    │  │   │ 指令6：激活窗口       │     │    │
    │  │   │ 指令7：模拟按键       │     │    │
    │  │   │ 指令8：删除文件       │     │    │
    │  │   └───────────────────────┘     │    │
    │  │ 指令9：等待 5 秒                │    │
    │  └─────────────────────────────────┘    │
    └─────────────────────────────────────────┘
```

每个指令都有"参数面板"，比如"读文件"要你填路径；"模拟按键"要你填要按的键。**不写一行代码**，全是表单填空。

---

## 4. 这次要让影刀做的事（流程总图）

```
┌───────────────────────────────────────────────────────────────┐
│ 主循环（永远不停）                                            │
│                                                               │
│   1. 列出 G:\60 AllProgram\02 program\Shadow\TRIGGER_*.md     │
│   2. 如果一个都没有 → 等 5 秒 → 回到 1                       │
│   3. 如果有 → 取第一个，重命名为 *.handling（防止重触）       │
│   4. 从文件名提取"信号 key"（比如 TRIGGER_PHASE_1_PLAN）      │
│   5. 根据信号 key 走对应分支：                                │
│        - 准备好"目标窗口名"（planner / executor / auditor）  │
│        - 准备好"提示词文件"（phase1_to_planner.txt 等）      │
│        - 如有需要，先跑 git_commit.bat 或发 Webhook          │
│   6. 子流程：注入提示词                                       │
│        a. 读取提示词 .txt 文件内容                            │
│        b. 写入剪贴板                                          │
│        c. 激活目标窗口（前台显示）                            │
│        d. Ctrl+A 选中已有内容（避免追加在后面）               │
│        e. Ctrl+V 粘贴                                         │
│        f. Enter 发送                                          │
│   7. 删除 *.handling                                          │
│   8. 回到 1                                                   │
└───────────────────────────────────────────────────────────────┘
```

> ⚠ 这套流程**不读业务代码**，不跑 `pytest`，不动 git 历史（除了 PASS 时调一下 `git_commit.bat`）。它就是个邮差。

---

## 5. 动手前先把这 7 样东西备好（清单 = 进度条）

| # | 要备好的东西 | 怎么确认 OK |
|---|---|---|
| 1 | 项目根目录（你的 = `G:\60 AllProgram\02 program\`） | 目录里能看到 `workflow_template/` 和 `Shadow/` 两个文件夹 |
| 2 | `Shadow/` 文件夹存在 | 没有就先双击 `workflow_template\init_project.bat` |
| 3 | 三个 AI 客户端各自打开，标题里有 **稳定关键字** | 比如 Kiro / Codex / RPA 等 |
| 4 | `workflow_template\config\workflow.toml` 里 `[bus_windows]` 三行已填窗口标题特征 | 用记事本打开，三个 `_pattern` 不为空 |
| 5 | `workflow_template\bus_setup\prompts\` 下 8 个 `.txt` 文件齐全 | 文件夹里数到 8 个 |
| 6 | `Shadow/` 里**没有**残留的 `TRIGGER_*.md` | 有就先双击 `bootstrap_reset.bat` 清场 |
| 7 | 项目根有 `.git`（PASS 自动 commit 用） | 文件夹里能看到 `.git` 文件夹（隐藏文件） |

> 第 4 项最容易漏。这是影刀切窗的"地址簿"，没填好后面 100% 卡死。

`workflow.toml` 示例（请按你机器实际改）：

```toml
[bus_windows]
planner_pattern  = "Kiro"
executor_pattern = "Codex"
auditor_pattern  = "RPA"
```

---

## 6. 第一步：在影刀里新建应用并先放一个"最小循环"

> 目标：先让影刀**每 5 秒打印一次"我活着"**。跑通了再加复杂逻辑。这是 RPA 调试铁律。

1. 打开影刀客户端 → **「我的应用」 → 「新建应用」 → 「桌面应用」**，命名 `RPA_Bus`。
2. 进入应用画布，左侧指令栏搜索 **「循环」**，拖一个**「按次数循环」**到画布中央，把次数改大如 `99999`。
   > 影刀的"无限循环"通常用大数 + 内部退出条件实现。
3. 在循环里面拖一个 **「输出日志」**（搜"日志"），内容填 `心跳：$当前时间`。
4. 在循环里再拖一个 **「等待」 → 「按时间等待」**，填 `5` 秒。
5. 点画布右上角 **「运行」** 按钮，看输出栏每 5 秒打印一行。看到了就停下。

✅ **里程碑 1 达成**：影刀的循环骨架可以跑了。

---

## 7. 第二步：让循环知道"Shadow 里来活了"

我们把"打印心跳"换成"扫 Shadow 文件夹"。

1. 删掉刚才的「输出日志」。
2. 在循环开头放一个 **「文件操作」 → 「获取文件夹中文件列表」**：
   - 文件夹路径：`G:\60 AllProgram\02 program\Shadow`（**填你机器上的真实绝对路径**）
   - 文件名通配：`TRIGGER_*.md`
   - 是否递归：否
   - 输出变量名：`triggerList`（影刀里点"+"新建变量）
3. 紧接着拖 **「条件判断」 → 「if 条件」**：
   - 条件：`triggerList` 的长度 `> 0`（影刀里写 `len(triggerList) > 0` 或在条件面板用图形化方式选"列表长度大于"）
   - 真分支里我们后面填路由逻辑
   - 假分支留空（直接进入后面的等待 5 秒即可）
4. 点运行，把一份测试触发文件丢进 `Shadow/`：
   ```cmd
   echo test > "G:\60 AllProgram\02 program\Shadow\TRIGGER_PHASE_1_PLAN.md"
   ```
   看影刀是否进入"真分支"（可以临时在真分支放一个「输出日志」打印 `命中了：$triggerList`）。

✅ **里程碑 2 达成**：影刀已经能"看见"信号文件。

---

## 8. 第三步：把信号文件改名为 `.handling` 防重触

> 偶发情况下文件刚 rename 完成那一瞬间会被检测两次。先抢锁。

在第 7 步的"真分支"里：

1. 拖 **「列表/字典 → 取列表元素」**：从 `triggerList` 取第 0 个，赋值给变量 `signalFile`。
2. 从 `signalFile` 拆出"纯文件名"：拖 **「文本处理 → 字符串截取」** 或直接用影刀的"获取文件名"指令，赋给 `signalName`（如 `TRIGGER_PHASE_1_PLAN.md`）。
3. 拖 **「文件操作 → 重命名文件」**：
   - 源文件：`signalFile`
   - 新名称：`signalFile + ".handling"`（影刀里用变量拼接：`{{signalFile}}.handling`）
   - 输出新路径变量：`handlingFile`
4. 紧接着拖 **「文本处理 → 字符串去掉后缀」**：把 `signalName` 末尾的 `.md` 去掉，赋给变量 `routeKey`（如 `TRIGGER_PHASE_1_PLAN`）。

✅ **里程碑 3 达成**：影刀已抢锁并算出"路由 key"。

---

## 9. 第四步：搭建路由分发（8 选 1）

工作流一共有 **8 个 TRIGGER 文件**，每个对应不同的"目标窗口 + 提示词文件 + 前置动作"：

| 信号 key（routeKey） | 目标窗口角色 | 提示词文件 | 前置动作 |
|---|---|---|---|
| `TRIGGER_PHASE_1_PLAN` | planner | `phase1_to_planner.txt` | 无 |
| `TRIGGER_PHASE_2_EXECUTE` | executor | `phase2_to_executor.txt` | 无 |
| `TRIGGER_PHASE_3_AUDIT` | auditor | `phase3_to_auditor.txt` | 无 |
| `TRIGGER_ROUTE_A_PASS` | planner | `route_a_pass.txt` | **先跑 git_commit.bat** |
| `TRIGGER_ROUTE_B_REJECT` | executor | `route_b_reject.txt` | 无 |
| `TRIGGER_ROUTE_C_ESCALATE` | planner | `route_c_escalate.txt` | **先发 Webhook** |
| `TRIGGER_QUERY_TO_PLANNER` | planner | `query_to_planner.txt` | 无（不计驳回） |
| `TRIGGER_QUERY_REPLY` | executor | `query_reply.txt` | 无（不计驳回） |

**实现方式**（影刀里推荐"多个 if-else 串联"，不要嵌套太深）：

1. 在 `routeKey` 算出之后，**串 8 个独立的 if 判断**，每个判断条件是 `routeKey == "TRIGGER_XXX"`。
2. 每个 if 的真分支里设两个变量：
   - `targetRole`：值为 `planner` / `executor` / `auditor`
   - `promptFileName`：值为对应的 `.txt` 文件名
   - `preAction`：值为 `none` / `git_commit` / `webhook`
3. 8 个 if 都跑完后（其实只会命中其中一个），下面放统一的"前置动作 + 注入子流程"。

> 影刀也支持 **「分支选择 / Switch」**指令（搜"分支"），更整洁。但小白用 8 个 if 串行更直观。

✅ **里程碑 4 达成**：影刀已经能"读懂"是哪种信号、要去哪个窗口、要发什么。

---

## 10. 第五步：搭建"注入提示词"子流程（核心动作）

这是大总管最核心的一段，**所有路由都要走**。强烈建议封装成"子流程"（影刀里点"+"新建子流程，命名 `inject_to_window`），主流程调用即可。

子流程入参：
- `targetRole`（字符串）
- `promptFileName`（字符串）

子流程内部步骤：

### 10.1 读取提示词文本
1. 拼出绝对路径：`promptPath = G:\60 AllProgram\02 program\workflow_template\bus_setup\prompts\{{promptFileName}}`
2. 拖 **「文件操作 → 读取文本文件」**：
   - 路径：`promptPath`
   - 编码：**UTF-8**（必须！中文不会乱码）
   - 输出变量：`promptText`

### 10.2 根据角色读取窗口标题特征
1. 拖 **「文件操作 → 读取文本文件」** 读 `workflow_template\config\workflow.toml`，输出 `tomlText`。
2. 用「文本处理 → 正则匹配」从 `tomlText` 抓出三个 `_pattern`：
   - `planner_pattern\s*=\s*"(.+?)"` → 赋给 `pPlanner`
   - `executor_pattern\s*=\s*"(.+?)"` → 赋给 `pExecutor`
   - `auditor_pattern\s*=\s*"(.+?)"` → 赋给 `pAuditor`
3. 用一个 if-else 链，根据 `targetRole` 选出 `windowPattern`：
   - 如果 `targetRole == "planner"` → `windowPattern = pPlanner`
   - 否则如果 `== "executor"` → `windowPattern = pExecutor`
   - 否则 `windowPattern = pAuditor`

> 偷懒做法：不读 toml，把三个窗口标题硬编码到子流程里。**初学者推荐这个**，跑通了再优化。

### 10.3 写入剪贴板
拖 **「剪贴板 → 设置剪贴板内容」**：
- 内容：`promptText`
- 编码：UTF-8

### 10.4 激活目标窗口（关键步骤！）
拖 **「窗口操作 → 激活窗口」**：
- 标题：`windowPattern`
- 匹配方式：**包含**（不要选"完全相等"，AI 客户端的标题经常会带文件名）
- 如果窗口最小化：勾选「自动恢复」
- 失败重试：3 次，间隔 1 秒（防止偶发"切窗失败"）

紧接着拖 **「等待 → 按时间等待」**，填 `1` 秒，让窗口稳定到前台。

### 10.5 聚焦输入框（影刀的小坑）
不同 AI 客户端输入框位置不一样。两种方案：

**方案 A：用 Tab 键导航（推荐，跨客户端通用）**
- 拖 **「键盘操作 → 模拟按键」**，按 `Tab` 几次（一般 1-3 次能到输入框，得自己试）
- 不灵的话切方案 B

**方案 B：双击输入框坐标（精准但要标定）**
- 用影刀的 **「鼠标操作 → 鼠标移动并点击」**，模式选"双击"，坐标用窗口相对坐标
- Kiro 输入框大致：窗口右下角往上 45 px、向右 55% 处
- Codex（浏览器版）：窗口下部往上 120 px、水平居中
- 这些坐标在 `bus_monitor.py` 的 `get_input_coords()` 函数里有参考实现

定好聚焦动作后，再拖 **「键盘操作 → 组合键」**：
- 第 1 次：`Ctrl+A`（全选已有内容，防止追加）
- 等待 0.3 秒
- 第 2 次：`Ctrl+V`（粘贴）
- 等待 0.8 秒
- 第 3 次：单键 `Enter`（发送）

### 10.6（可选）发后截图存证
- 拖 **「图像操作 → 截图」**，保存到 `Shadow\_post_inject_{{当前时间戳}}.png`
- 排查问题时可以倒带看注入是不是真发出去了

---

## 11. 第六步：处理两种"前置动作"

主流程调用子流程**之前**，根据 `preAction` 干一件特殊事。

### 11.1 `preAction == "git_commit"`（仅 ROUTE_A_PASS）
- 拖 **「系统操作 → 启动程序」**：
  - 程序路径：`cmd.exe`
  - 启动参数：`/c "G:\60 AllProgram\02 program\workflow_template\bus_setup\git_commit.bat"`
  - 工作目录：项目根 `G:\60 AllProgram\02 program\`
  - 是否等待：**等待结束**
  - 是否隐藏窗口：是
- 给它最多 30 秒超时，失败也别阻塞后续——脚本本身有失败兜底（写到 `Shadow\_git_fallback.log`）。

### 11.2 `preAction == "webhook"`（仅 ROUTE_C_ESCALATE）
- 拖 **「网络 → HTTP 请求」**：
  - 方法：POST
  - URL：从 toml 读出来的 `webhook.url`（空的话直接跳过这步）
  - Body（JSON）：
    ```json
    {
      "event": "ESCALATE",
      "project": "你的项目名",
      "timestamp": "{{当前时间ISO8601}}",
      "detail": "{{routeKey}}"
    }
    ```
  - 超时：10 秒
  - 失败处理：写入 `Shadow\_webhook_fallback.log`，**不阻塞**

> 影刀的"取当前时间"可以用 **「时间日期 → 获取当前时间」** 指令，格式选 `yyyy-MM-ddTHH:mm:ss+08:00`。

---

## 12. 第七步：路由收尾

子流程返回主流程后：

1. 拖 **「文件操作 → 删除文件」**：路径 = `handlingFile`（就是步骤 8 改名后的那个）。
2. 拖 **「输出日志」**：内容 `[ROUTE-OK] {{routeKey}} → {{targetRole}}`。
3. 自然进入循环下一轮。

---

## 13. 第八步：加超时告警（20 分钟无信号）

> 这个不重要，**先跳过也能跑**。但工作流文档要求有，这里给做法。

1. 在主循环外面新建一个变量 `lastSignalTime`，初值 = 当前时间。
2. 每次成功处理一个信号，更新 `lastSignalTime` = 当前时间。
3. 在循环底部"等待 5 秒"之前加一个 if：
   - 条件：`当前时间 - lastSignalTime > 1200 秒`
   - 真分支：发一次 Webhook（同 11.2，但 event 改成 `BLOCKED`）+ 把 `lastSignalTime` 重置为当前时间（避免反复告警）

---

## 14. 第九步：第一次跑通（最小可用测试）

> 不要急着跑完整工作流，先用"假信号"打通管道。

1. 三个 AI 客户端先**都打开一个**（哪怕只是空白对话窗口），保证窗口标题能匹配到 `bus_windows` 里的 pattern。
2. 在影刀画布右上角点 **「运行」**，让大循环跑起来，输出栏应该一直滚 `获取到 0 个文件 → 等待 5 秒`。
3. 打开命令行（`Win+R` → `cmd`），手动投一个测试信号：
   ```cmd
   echo bootstrap > "G:\60 AllProgram\02 program\Shadow\TRIGGER_PHASE_1_PLAN.md"
   ```
4. 5 秒内你应该看到：
   - 影刀输出栏打印命中
   - planner 那个客户端窗口被切到前台
   - 提示词被粘到输入框并按了回车
   - 该信号文件消失
5. 都对 → ✅ **里程碑 5 达成**：管道通了。

---

## 15. 第十步：完整跑一次工作流

确认管道 OK 后：

1. 双击 `workflow_template\bootstrap_reset.bat` → 输入 `YES` 清场。
2. 准备好 `<项目根>/docs/PRD.md`、`TECH_DESIGN.md`、`EXECUTION_PLAN.md` 三件套（至少有内容，否则规划师无单可拆）。
3. 让影刀的大循环保持运行。
4. 双击 `workflow_template\bootstrap.bat`，投递首封 `TRIGGER_PHASE_1_PLAN.md`。
5. 之后只需观察 `Shadow/` 目录里信号文件的来去（每个出现 → 影刀路由 → 消失），以及三个 AI 客户端依次被点亮、互相点名。

---

## 16. 常见问题与排查

### 16.1 信号文件出现了但影刀没反应
- 检查路径：`Shadow/` 路径里有空格（你的 = `02 program`），影刀里**必须用反斜杠 + 整段**填，不要漏。
- 检查通配：`TRIGGER_*.md` 不是 `TRIGGER_*` 也不是 `*.md`。
- 检查"获取文件夹列表"是否勾选"递归"——**不能勾**，否则把 `_archive/` 里的旧信号也扫进来。

### 16.2 切窗失败 / 切错窗
- 用 **Spy++** 或者影刀自带的"窗口拾取器"看真实窗口标题，把 `bus_windows` 里的 pattern 改更精确（比如包含项目名）。
- 同一个 AI 客户端开了多个实例 → 关掉多余实例，或在 pattern 里加项目名区分。

### 16.3 粘贴出来是上一次的内容
- 剪贴板被别的程序抢走了。在"设置剪贴板"和"Ctrl+V"之间加 0.5 秒等待。
- 自动化跑的时候你**不要手动 Ctrl+C 别的东西**。

### 16.4 中文乱码
- "读取文本文件"务必选 **UTF-8**。
- 影刀环境编码默认 UTF-8，如果出问题进 **影刀设置 → 环境编码**确认。

### 16.5 信号被处理两次
- 你忘了第 8 步的 `.handling` 重命名抢锁。补上。
- 或者两个影刀实例同时在跑——只允许一个。

### 16.6 git_commit.bat 没反应
- 项目根没 `.git` 文件夹 → 跑 `init_project.bat` 或手动 `git init`。
- `git config user.name` / `user.email` 没配 → 在项目根跑：
  ```cmd
  git config user.name "you"
  git config user.email "you@local"
  ```

### 16.7 想中途停下
- 影刀画布右上角"停止"按钮一键停。
- 残留的 `*.handling` 文件**手动删一下**，否则下次启动会被忽略。

---

## 17. 附录 A：路由表速查（贴在显示器边上）

| routeKey | targetRole | promptFileName | preAction |
|---|---|---|---|
| `TRIGGER_PHASE_1_PLAN` | planner | `phase1_to_planner.txt` | none |
| `TRIGGER_PHASE_2_EXECUTE` | executor | `phase2_to_executor.txt` | none |
| `TRIGGER_PHASE_3_AUDIT` | auditor | `phase3_to_auditor.txt` | none |
| `TRIGGER_ROUTE_A_PASS` | planner | `route_a_pass.txt` | git_commit |
| `TRIGGER_ROUTE_B_REJECT` | executor | `route_b_reject.txt` | none |
| `TRIGGER_ROUTE_C_ESCALATE` | planner | `route_c_escalate.txt` | webhook |
| `TRIGGER_QUERY_TO_PLANNER` | planner | `query_to_planner.txt` | none |
| `TRIGGER_QUERY_REPLY` | executor | `query_reply.txt` | none |

---

## 18. 附录 B：影刀关键指令速查

| 你想做的事 | 影刀指令名（搜索关键字） |
|---|---|
| 永远循环 | 循环 / 按次数循环 |
| 读文件夹下文件名列表 | 文件 / 获取文件列表 |
| 读文本文件内容 | 文件 / 读取文本文件 |
| 改文件名 | 文件 / 重命名文件 |
| 删文件 | 文件 / 删除文件 |
| 写剪贴板 | 剪贴板 / 设置剪贴板 |
| 切到某窗口 | 窗口 / 激活窗口 |
| 按一组键（Ctrl+V） | 键盘 / 组合键（或"模拟按键"） |
| 鼠标双击 | 鼠标 / 鼠标点击（双击） |
| 跑 .bat | 系统 / 启动程序（cmd /c xxx.bat） |
| 发 HTTP | 网络 / HTTP 请求 |
| 截图存盘 | 图像 / 截图 |
| 等几秒 | 等待 / 按时间等待 |
| 字符串截取/匹配 | 文本处理 / 字符串... 或 正则匹配 |
| if / else | 流程控制 / 条件判断 |
| 取列表第 N 个 | 列表 / 取列表元素 |
| 当前时间 | 时间日期 / 获取当前时间 |

---

## 19. 附录 C：影刀版 vs Python 版（`bus_monitor.py`）

工作流不强制用哪种。两者实现的是**同一份契约**，由 `bus_setup/triggers_dictionary.md` 定义。

| 维度 | 影刀版（本手册） | Python 版（`bus_monitor.py`） |
|---|---|---|
| 上手成本 | 低（拖块 + 表单） | 中（要会 Python，要装依赖 pyautogui/pyperclip） |
| 调试 | 可视化单步 | 看 `Shadow/_bus_log.txt` |
| 修改路由 | 改画布 | 改代码 |
| 跨机器复用 | 导出影刀应用包 | 直接复制 `.py` |
| 后台运行 | 影刀客户端要开着 | 命令行启动即可，可设服务 |

**建议**：先用影刀版跑通流程把工作流走顺，等熟了想"长期挂机 + 服务化"再切到 Python 版。两边切换无成本（信号文件协议完全一样）。

---

## 20. 收尾 Checklist

最后再确认一遍：

- [ ] 影刀应用名 `RPA_Bus` 已建好
- [ ] 主循环 + 等待 5 秒已搭好
- [ ] `Shadow/` 路径硬编码或读 toml 都行，反正是绝对路径
- [ ] 8 个 if 路由分支都填好了 `targetRole` / `promptFileName` / `preAction`
- [ ] 子流程 `inject_to_window` 完整：读 prompt → 写剪贴板 → 激活窗口 → Ctrl+A → Ctrl+V → Enter
- [ ] PASS 路径前置调了 `git_commit.bat`
- [ ] ESCALATE 路径前置发了 Webhook（或写日志兜底）
- [ ] 处理完信号删 `.handling` 文件
- [ ] 三个 AI 客户端都开着，窗口标题能被 `bus_windows` 三个 pattern 匹配上
- [ ] 用手动 `echo` 测试投信能跑通完整一轮
- [ ] 用 `bootstrap.bat` 投递真信号能进入第一轮规划

全打勾 → 收工 ✅。后面让 `bootstrap.bat` 一键启动，全自动跑就行。

---

> 本手册版本 V1.0 · 配套工作流版本 V6.0 · 最后更新 2026-05-17  
> 如果某条指令在你装的影刀版本里名字不一样，**优先按"功能描述"找**，不要按字面找。
