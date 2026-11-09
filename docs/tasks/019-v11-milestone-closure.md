---
task_id: "019"
target_version: "v1.1.0"
title: "v1.1 阶段里程碑收工归档与文档对齐精简"
status: "Accepted"
branch: "docs/019-v11-milestone-closure"
date: "2026-11-09"
---

# 019：v1.1 阶段里程碑收工归档与文档对齐精简

## 目标

在已合并的 Task 018（`766cacc`）之上，完成 v1.1.0 的阶段成果收口与里程碑归档。本任务定义为**内部阶段任务收工（Stage Closure）**，**非对外软件发布（Not a Release）**，**不打 Git Tag**。

核心工作：
1. 升级完善卡片母版 [rule-card-template.md](../rules/rule-card-template.md)，固化 26 张卡片实际采用的标准化第 4 节结构，并与 Schema 统一验证义务枚举；
2. 修复 `backend/tests/domain/test_rule_outcomes.py` 中因 Windows CRLF 换行符导致的 `docs/blueprint.md` SHA256 哈希断言失败；
3. 清理各文档中关于 PR #18 尚未合并等过时陈旧描述，修正责任矩阵中的历史规则计数笔误，大幅精简冗长嵌套的免责声明；
4. 建立 `docs/versions/v1.1.0/` 冻结归档目录，迁移归档 001–018 任务，并建立面向下一阶段的 [v1.2 入口](v1.2-entry.md)；
5. 修订根目录 `AGENTS.md`，补齐 `docs/` 职责地图、任务规范与环境命令指引，保持客观中立规范表达。

## 范围

- 卡片母版升级：采用实际卡片沉淀的 12 项标准化结构（比较单位、适用性、闭集、触发条件、触发特征、不触发条件、输入、Finding、证据位置、上下文切片、影响类型、规则终态、构造样例）；在有效性计划中补齐 `implementation_only`。
- 测试归一化：在 `test_rule_outcomes.py` 中将 `docs/blueprint.md` 换行符统一归一化为 `\n` 计算哈希，确保多平台通过。
- 文档精简与陈旧清理：
  - 更新 `docs/README.md`，确认 PR #18 已合入事实，精简历史递归声明。
  - 更新 `docs/versions/README.md`，增加 `v1.1.0` 冻结归档记录与完整任务索引。
  - 修正 `docs/rules/rule-responsibility-matrix.md` 中“四条结构规则”为“五条历史结构规则”。
- 阶段归档：
  - 新建 `docs/versions/v1.1.0/README.md`、`00-baseline-summary.md`、`v1.1-entry.md`。
  - 将 `001-*.md` 至 `018-*.md` 归档迁移至 `docs/versions/v1.1.0/tasks/`。
  - 在归档中说明 Task 013 先行合入的事实（带入 `data.django_raw_sql_execution` 检测器使运行时规则达 14 条）。
  - 新建 `docs/tasks/v1.2-entry.md`，并更新 `docs/tasks/README.md`。
  - 更新 `docs/standards/branching-and-tasks.md`，标注 019 状态，注明下一个未使用任务编号为 020。
- 根目录规范维护：
  - 更新 `AGENTS.md`，明确文档职责分工、开发工作流与检查命令。

## 不做事项

- 不改动运行时规则代码（`backend/prisk/domain/rules/` 等）。
- 不改动 26 张规则卡片的实际内容与判定逻辑。
- 不修改 `docs/blueprint.md` 原文，严格保持规范基准。
- 不创建 Git Tag，不执行对外软件发布。

## 验证与验收

- `backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -t backend`：121 项测试逻辑全部通过，换行符断言问题彻底解决。
- `detailed_card_check.py`：26 张卡片与 Schema / 登记册 100% 对齐，0 处错误。
- 前端检查：`npm run lint` 和 `npm run typecheck` 均 100% 通过（退出码 0）。
- `git diff --check`：无格式或冲突残留。
- 归档链接与目录结构完整有效。
