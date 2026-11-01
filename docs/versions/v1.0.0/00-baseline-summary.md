# v1.0.0 基线摘要

Prisk-System v1.0.0 是本地离线后端代码审查支持工具。系统读取已提交的 base/head 快照，生成统一 Diff、AST 结构、规则证据和透明复核评分。

v1.0.0 功能基线在本次冻结整理前采用 `src/prisk` 和 `apps/web` 布局；待发布工作区已将工程目录整理为 `backend/` 与 `frontend/`。Python 运行依赖为标准库，前端使用 Next.js、React、TypeScript 和 Tailwind CSS。冻结阶段记录、脱敏样本及可复用 JSONL/manifest 均在本目录归档；完整上游仓库、API 缓存和个人材料不纳入。

v1.0.0 以人工复核为目标，不自动确认缺陷，不执行 checkout、fetch、merge、pull，不纳入未提交工作区。
