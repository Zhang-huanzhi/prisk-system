---
task_id: "003"
target_version: "v1.1.0"
title: "规则 ID 命名迁移与四拆五解耦"
status: "Accepted"
branch: "docs/rule-id-naming"
date: "2026-11-04"
---

# 003：规则 ID 命名迁移与四拆五解耦

## 目标

统一规则 ID 的关注域命名，并将配置与异常处理从一条混合运行时规则拆成两条规则。规则检测意图保持不变；本迭代不扩展其他规则。

## 命名规范

规则 ID 使用两段式格式：`<domain>.<rule_slug>`。允许的 domain 为 `api`、`auth`、`data`、`config`、`code` 和 `workflow`。`rule_family` 仍是登记对象属性，不进入 ID。

分类遵循三条仲裁原则：框架语义优先于通用语法；直接检测对象优先于潜在影响；具体功能域优先于 `code`，`code` 只承载语言级规则。

## 四拆五

- `interface.signature_changed` → `api.signature_changed`；
- `auth.permission_structure_changed` 保持不变；
- `data.transaction_structure_changed` 保持不变；
- `config.exception_structure_changed` 拆为 `config.configuration_structure_changed` 和 `code.exception_structure_changed`。

配置规则只匹配 settings/configuration 路径，异常规则只匹配 `except_handler`。两条规则分别生成 Finding；不在运行时兼容旧 ID。

## 接口迁移

后端 Finding 和规则目录不再发送冗余 `scene` 字段，报告和数据集使用由规则 ID 第一段聚合得到的 `domains`。前端从规则 ID 解析 domain，并维护标签、图标、筛选和权重配置。

草稿规则可以直接改名；`registered` 或 `implemented` 规则在本次迁移中记录旧 ID 到新 ID 的映射。

## 验收

- 规则目录从四条变为五条；
- 全部当前规则 ID 为两段式、唯一且使用允许 domain；
- 配置文件和异常节点分别命中对应规则；
- 当前数据和演示配置使用新 ID；
- 后端测试、前端 lint/typecheck/build 和 `git diff --check` 通过。

## 实际验证

- 后端 unittest：41 项通过；
- 前端 `lint`、`typecheck`、`build`：通过；
- 冻结 NetBox stage05：120 条记录，99 条可分析，1,155 条 Finding，证据完整率 1.0；
- 规则 ID 登记册：23 条，23 个唯一且全部符合两段式格式；
- `git diff --check`：通过。
