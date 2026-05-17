### [YYYY-MM-DD HH:MM:SS] [版本: V0.1] PLAN_INDEX

> 极简大盘视图。**总长度上限 30 行。** 仅规划师必读。

## 关联执行方案
- 版本：EXECUTION_PLAN V1.0

## 摘要
> [3 句话内：项目宏观进度 / 最近解决了什么 / 下一阶段焦点]

## 当前焦点（执行中）
- 环节 N · 工单 K：TASK-XXX [一行描述]
- 当前环节进度：K / <环节总工单数>

## 下一步候选
- 环节 N · 工单 K+1：TASK-YYY [一行描述]

## 待打 Git tag
- （留空 / 或：环节 1 全部完成，待打 phase-1-done）

## 累计统计（项目级，仅供人类总览，不作为 #FirstPrinciples 触发判定依据）
- 完成: 0 单 | 项目总驳回: 0 次 | 熔断: 0 次

> 单个工单的驳回数权威来源是 `reviews/REVIEW_REPORT_v[*].meta.json` 的 `reject_count_after_this` 字段。

## 文件指引（按需读）
- 待办全集 → PLAN_BACKLOG.md（仅规划师排单时读）
- 历史归档 → PLAN_DONE.md（仅人类查阅，AI 禁读）
