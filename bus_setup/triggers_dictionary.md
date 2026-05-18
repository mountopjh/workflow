# 大总管（RPA）信号字典（路由总表）

> 大总管监听 `<项目根>/Shadow/` 目录。一旦发现以下任一文件，按对应行执行动作。  
> 所有动作的最后一步都是**删除该信号文件**，防止状态机卡死。

---

## 1. 路由表

| 信号文件 | 大总管激活的窗口 | 注入提示词来源 | 动作 |
|---|---|---|---|
| `TRIGGER_PHASE_1_PLAN.md` | 规划师客户端 | `prompts/phase1_to_planner.txt` | 切窗 → 剪贴板 → Ctrl+V → Enter → 删除信号 |
| `TRIGGER_PHASE_2_EXECUTE.md` | 执行者客户端 | `prompts/phase2_to_executor.txt` | 同上 |
| `TRIGGER_PHASE_3_AUDIT.md` | 审计员客户端 | `prompts/phase3_to_auditor.txt` | 同上 |
| `TRIGGER_ROUTE_A_PASS.md` | 规划师客户端 | `prompts/route_a_pass.txt` | **先调 `bus_setup/git_commit.bat`（自动 commit + 按需打 tag）→ 再切窗注入 → 删除信号** |
| `TRIGGER_ROUTE_B_REJECT.md` | 执行者客户端 | `prompts/route_b_reject.txt` | 同上（不 commit） |
| `TRIGGER_ROUTE_C_ESCALATE.md` | 规划师客户端 | `prompts/route_c_escalate.txt` | **先调 Webhook（POST `webhook_url`）→ 再切窗注入 → 删除信号**（不 commit） |
| `TRIGGER_QUERY_TO_PLANNER.md` | 规划师客户端 | `prompts/query_to_planner.txt` | 切窗 → 剪贴板 → Ctrl+V → Enter → 删除信号（不 commit、不计驳回） |
| `TRIGGER_QUERY_REPLY.md` | 执行者客户端 | `prompts/query_reply.txt` | 同上（不 commit、不计驳回） |

---

## 2. 状态机视图

```
        ┌──────────────────────────────────────────┐
        │                                          │
        ▼                                          │
[PHASE_1_PLAN] ──► 规划师 出 CURRENT_TASK ──┐         │
                                          ▼         │
                                  [PHASE_2_EXECUTE]  │
                                          │         │
                                          ▼         │
                                  执行者 出 OUTPUT   │
                                          │         │
                                          ▼         │
                                  [PHASE_3_AUDIT]   │
                                          │         │
                            ┌─────────────┼─────────┘
                            │             │
                            ▼             ▼
                      审计员 出 REPORT + meta.json
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        [ROUTE_A_PASS] [ROUTE_B_REJECT] [ROUTE_C_ESCALATE]
              │             │             │
              ▼             ▼             ▼
            回 规划师       回 执行者     Webhook + 回 规划师
         （发下一单）   （针对性返工）   （改 PLAN 救火）
```

---

## 3. 守门规则

1. **顺序锁**：同时间 `Shadow/` 里只允许有一个 `TRIGGER_*.md`。大总管处理一个就立刻删一个，再监听下一个。
2. **20 分钟超时**：监听超过 20 分钟无新信号 → 大总管调 `webhook_url` 推送阻断告警，不退出主循环。
3. **路由完，必删信号**：删除是最后一步，防止重复触发。
4. **窗口标题识别**：大总管通过窗口标题精准切窗。如果标题被改，路由会失败，必须在 大总管配置里同步更新窗口标题匹配规则。
5. **剪贴板强注**：所有提示词必须通过"写剪贴板 → Ctrl+V"注入，**禁止**用模拟键盘逐字打。
6. **请示通道独立**：`QUERY_*` 路由**不影响**主流程驳回累加器。规划师回复后，执行者继续接着原工单干，不重发 PHASE_2、不写 EXECUTOR_OUTPUT。

---

## 4. QUERY 请示通道（执行者 → 规划师 → 执行者）

**何时用**：执行者实现到一半发现工单本身有问题（如未声明依赖、接口契约与依赖冲突、步骤之间相互矛盾），又不至于阻塞全部进度。走请示比走 REJECT 更省一次驳回额度。

**何时不用**：
- 工单完全没法干（接口设计错误、范围越界）→ 仍走 REJECT 路径，由审计员发现并 ESCALATE
- 实现纯技术问题（不知道用什么算法）→ 不要请示，自己看 TECH_DESIGN 引用章节决定

**流程**：
```
执行者发现问题
    │
    ▼
执行者写 <项目根>/QUERY.md（含问题、上下文、倾向方案）
执行者投递 Shadow/TRIGGER_QUERY_TO_PLANNER.md
    │
    ▼
大总管路由 → 规划师
    │
    ▼
规划师追加回复到 QUERY.md 末尾（或修订 CURRENT_TASK 递增版本，仍不计驳回）
规划师投递 Shadow/TRIGGER_QUERY_REPLY.md
    │
    ▼
大总管路由 → 执行者
    │
    ▼
执行者按回复继续原工单（不重起 PHASE_2，不重写 EXECUTOR_OUTPUT）
最终交卷时仍按 PHASE_3 走审计
```

**铁律**：
- 请示**不计**驳回累加器
- QUERY.md 由执行者起头、规划师回复，对话式追加（每段标注角色 + 时间戳到秒）
- 同一工单的 QUERY 次数无硬上限，但 ≥ 3 次仍未对齐建议主动 ESCALATE
- 工单交卷归档时（PASS 后）QUERY.md 应被规划师挪到 `<项目根>/_archive/queries/<task_id>_query.md`
