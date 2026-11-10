---
task_id: "029"
target_version: "v1.3.0"
title: "前端工作台 GitHub 风格重构与交互布局优化"
status: "Accepted"
branch: "refactor/029-frontend-github-ui-refactor"
date: "2026-11-10"
---

# 029：前端工作台 GitHub 风格重构与交互布局优化

## 1. 背景与目标

在 Task 026–028 完成运行时配置解耦、快照局部重跑与可复现审查报告导出后，系统进入实际多文件分支审计（如包含 23 个变更文件的 `EiheiZone-experience` 分支）。实际使用中暴露了 5 项核心体验与视觉痛点：
1. **左侧栏字符溢出超限**：长路径（如 `D:\Data\Obsidian_Data\...`）与长分支名突破左侧边栏右边界，发生严重穿透截断；
2. **左侧导航栏空旷且缺少常驻规则入口**：左侧栏除项目切换外大面积留白，而 29 条规则目录深藏在三级 Tab 底部；
3. **顶栏视觉层级冗余繁琐**：Topbar、大号 PR 标题区与 Tab 导航三层堆叠，存在较多重复信息与紧凑度不足；
4. **字体偏浅、背景偏浅、字号偏小（8px~10px）导致可读性极差**：低对比度浅灰绿色字体在浅底上识别费力；
5. **代码变更页文件列表顺延导致右侧大片留白**：多文件 PR 下左侧文件列表把整个页面纵向撑得极长，右侧单文件 Diff 区域下方空出一大半。

本任务定位为 **v1.3.0 动态交互工作台的前端视觉与交互深度优化**，借鉴 **GitHub PR "Files changed"（Primer Design System）** 优秀范式：
- 修复所有字符超限与容器溢出问题；
- 在左侧栏常驻 29 条规则目录导航树（按 6 大关注域分组，实时标注 `Hit / NotFound / Unanalyzed`），支持全局抽屉查阅规则卡片；
- 精简顶栏为紧凑双层 GitHub PR 头部；
- 全面引入 GitHub Primer 高对比度色板，正文字号提升至 13px~14px，彻底废除 <12px 超小文字；
- 将代码变更重构为「左侧 Sticky 层级目录树 + 右侧多文件连续 Diff 卡片流」，支持单文件折叠与 `Viewed（已审阅）` 状态跟踪。

## 2. 范围与边界

### 纳入范围

1. **GitHub Primer 色板与文字可读性升级**：深炭黑文字（`#1f2328`）、高对比次级文字（`#59636e`）、清晰边框（`#d0d7de`），字号升级为 12px~20px 阶梯。
2. **左侧栏防溢出与 29 条规则目录常驻**：路径与分支名省略约束；新增左侧规则目录导航树，支持搜索、终态筛选与规则卡片抽屉弹窗。
3. **紧凑 GitHub PR 头部与导航栏**：整合原 Topbar 与 PR Heading，高对比度展示风险等级徽标、预设、指纹、重跑 Tier 与操作按钮。
4. **GitHub 风格 Files Changed 代码审查工作区**：
   - 左侧：Sticky 固定高度目录树，支持文件夹折叠与文件过滤；
   - 右侧：多文件连续 Diff 卡片流，带单文件折叠、差异比例条与 GitHub 同款 `Viewed` 已审阅复选框。
5. **各 Tab 页高对比度样式精修**：概览卡片、风险规则 Finding 证据链、评分配置预设卡片及阈值输入面板。

### 不做事项（技术边界）

- 不改动后端 Python 任何分析算法、检测器逻辑、评分逻辑与 HTTP API 接口契约。
- 不修改 `rule-registry.json` 或 26 张规则卡片原文。
- 保持所有 209 项后端单元测试无感通过。

## 3. 技术方案与契约设计

### 核心方案

- **CSS 色彩与排版变量体系**：基于 GitHub Primer 规范定义 `--fg-default`、`--fg-muted`、`--bg-canvas`、`--bg-default`、`--border-default`、`--accent-fg`、`--success-fg`、`--danger-fg`、`--attention-fg`。
- **文件路径树形聚合算法 (`buildFileTree`)**：将扁平的 `report.files` 数组解析为按 `/` 分隔的层级树，对单分支连续路径进行合并显示（如 `backend/app/modules/posts/`），提升目录阅读效率。
- **双模式代码审查视图**：提供「连续流模式（Stream Mode，默认）」与「单文件聚焦模式（Single File Mode）」，满足多文件快速扫视与超大文件精准定位的双重需求。
- **规则卡片侧边弹窗抽屉 (`selectedCatalogRule`)**：点击左侧栏任意规则，右侧弹出高对比度规则卡片面板，包含触发条件、适用范围、复核建议、局限性以及本次分析如果命中时的具体代码行与证据。

### 契约与兼容性

- **接口与数据契约**：前端仅对既有 `Report`、`Dataset`、`Config` 等 Schema 做交互与视觉升级，不改变任何前后端交互协议。
- **满分与权重基线**：完全维持当前 29 条规则与场景预设体系不变。

## 4. 交付物与改动清单

### 改动文件

- **前端样式**：[`frontend/src/app/globals.css`](../../frontend/src/app/globals.css)（全量重写为 Primer 色彩系统与 GitHub 布局规范）；
- **前端组件**：[`frontend/src/components/dashboard.tsx`](../../frontend/src/components/dashboard.tsx)（左侧规则树导航、紧凑头部、Sticky 目录树与连续 Diff 流、规则抽屉）；
- **任务与阶段索引**：
  - 新增 [`docs/tasks/029-frontend-github-ui-refactor.md`](029-frontend-github-ui-refactor.md)（本文件）；
  - 更新 [`docs/tasks/README.md`](README.md)；
  - 更新 [`docs/tasks/v1.3-entry.md`](v1.3-entry.md)。

## 5. 验证与验收

### 验收要点

- 左侧栏长路径与长分支名正常以省略号截断并带完整 tooltip，无文字横向穿透；
- 左侧栏常驻 29 条规则目录，带搜索与终态过滤，点击可弹出规则卡片详情；
- 页面深色文字与浅底对比度清晰锐利，无 `<12px` 超小难辨字体；
- 代码变更页左侧树 Sticky 固定高度，右侧多文件连续 Diff 卡片平滑滚动，支持折叠与 `Viewed` 标记；
- 全量 209 项后端测试通过，前端 lint / typecheck 零错误通过，git diff --check 零格式警告。

### 执行检查

- **后端测试**：`backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -t backend`
- **前端检查**：
  - `npm --prefix frontend run lint`
  - `npm --prefix frontend run typecheck`
- **格式检查**：`git diff --check`

## 6. 已知限制与残余风险

- **特大 Diff 渲染开销**：当单次分析包含上百个文件或上万行变动时，建议勾选「单文件聚焦模式」或批量点击「全部折叠」以减少 DOM 节点开销。
