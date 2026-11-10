"use client";

import {
  AlertCircle, ArrowDownRight, ArrowUpRight, Check, ChevronDown,
  ChevronRight, CircleHelp, Code2, Download, FileCode2, FileText,
  Folder, FolderOpen, GitPullRequest, ListFilter, LoaderCircle, LockKeyhole,
  Network, RotateCcw, Search, Settings2, ShieldAlert, SlidersHorizontal, X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

type Rule = {
  rule_id: string; severity: string; trigger: string;
  evidence_type: string; applicable_scope: string; suggested_action: string;
  limitations: string; default_weight: number; enabled_by_default: boolean;
};
type Evidence = {
  path: string; node_id: string; node_kind: string; structural_change_type: string;
  lines: number[]; qualified_name?: string; source_segment?: string;
  capture_form?: string; callee_name?: string; handler_body_is_single_pass?: boolean;
  used_as_with_context?: boolean; nesting_depth?: number; depth_threshold?: number; control_kind?: string;
  binding_name?: string; binding_form?: string; value_length?: number; value_preview?: string;
  mutable_state_form?: string; binding_targets?: string[];
  path_class?: string; additions?: number; deletions?: number; content_change?: string;
  operation?: string; route?: string; action_name?: string; setting_name?: string; direction?: string;
  permission_policy?: string; decorator?: string; signal?: string; old_field?: string; new_field?: string;
  parameter_name?: string; container_kind?: string; mapped_framework_base?: string;
};
type Finding = {
  rule_id: string; severity: string; message: string;
  suggested_action: string; evidence: Evidence[];
};
type OutcomeObject = { path: string; node_id?: string };
type RuleOutcome = {
  rule_id: string; state: "Hit" | "NotFound" | "Unanalyzed";
  reasons?: { reason: string; objects: OutcomeObject[] }[];
};
type DiffLine = { kind: "context" | "add" | "delete"; old_line: number | null; new_line: number | null; text: string };
type Hunk = { old_start: number; old_count: number; new_start: number; new_count: number; lines: DiffLine[] };
type DiffFile = {
  path: string; old_path?: string; new_path?: string; role: string; status: string;
  is_python: boolean; binary: boolean; additions: number; deletions: number;
  hunks: Hunk[]; parse_status: Record<string, string>; parse_errors: { side?: string; message?: string; line?: number; column?: number }[];
};
type RuleThresholds = {
  "code.deep_control_flow"?: { max_depth: number };
  "code.hardcoded_secret"?: { min_length: number };
};
type Config = {
  preset?: string;
  enabled_rules: string[];
  rule_weights: Record<string, number>;
  test_collaboration_weight: number;
  test_collaboration_enabled: boolean;
  thresholds: { medium: number; high: number };
  rule_thresholds?: RuleThresholds;
};
type PresetItem = {
  preset: string;
  name: string;
  description: string;
  enabled_rule_count: number;
  enabled_rules?: string[];
  rule_weights?: Record<string, number>;
  test_collaboration_weight?: number;
  test_collaboration_enabled?: boolean;
  thresholds: { medium: number; high: number };
  rule_thresholds: RuleThresholds;
};
type SnapshotMeta = {
  cache_hit: boolean;
  rerun_tier: "full_run" | "stage05_rules_rerun" | "stage07_rescore_only";
  diff_reused: boolean;
  ast_reused: boolean;
  rules_reused: boolean;
  cache_key?: string;
};
type ConfigSnapshot = {
  schema_version: string;
  preset: string;
  preset_name: string;
  customized: boolean;
  config_digest: string;
  enabled_rule_count: number;
  disabled_rule_count: number;
  enabled_rules: string[];
  disabled_rules: string[];
  rule_weights: Record<string, number>;
  test_collaboration_enabled: boolean;
  test_collaboration_weight: number;
  thresholds: { medium: number; high: number };
  rule_thresholds: RuleThresholds;
};
type GatekeeperHit = { rule_id: string; path: string; node_id: string; operation: string };
type ScoreBasis = {
  earned_points: number;
  maximum_points: number;
  matched_rule_ids: string[];
  test_collaboration: boolean;
  configuration: Config;
  gatekeeper_lift?: boolean;
  gatekeeper_finding_rule_ids?: string[];
  gatekeeper_structural_rule_ids?: string[];
  gatekeeper_structural_hits?: GatekeeperHit[];
  registry_gatekeeper_rule_ids?: string[];
};
type Report = {
  status: string; repo: string; pr_number?: number; title: string; author?: string; url?: string;
  project?: Project; base_ref?: string; head_ref?: string; merge_base_sha?: string; diff_mode?: string;
  base_sha?: string; head_sha?: string; score: number; risk_level: string;
  snapshot_meta?: SnapshotMeta;
  config_snapshot?: ConfigSnapshot;
  score_basis: ScoreBasis;
  summary: {
    finding_count: number; domains?: string[]; files_changed: number; business_files: number;
    test_files: number; additions: number; deletions: number; business_changed: boolean;
    test_changed: boolean; test_cochanged: boolean; test_collaboration_gap: boolean; parse_degraded: boolean;
    unanalyzed?: { path: string; reason: string; node_ids?: string[] }[];
  };
  files: DiffFile[]; findings: Finding[]; limitations: string[];
  rule_outcomes?: RuleOutcome[] | null;
  rule_outcome_availability?: "recorded" | "unavailable";
};
type PRItem = {
  pr_number: number; title: string; author?: string; url?: string; status: string;
  score: number; risk_level: string; finding_count: number; domains: string[]; additions: number; deletions: number;
};
type Dataset = {
  counts: { records: number; analyzable: number; excluded: number; with_findings: number; without_findings: number; levels: Record<string, number> };
  rules: Rule[]; prs: PRItem[];
};
type Branch = { ref: string; kind: string; sha: string; short_sha: string; subject: string; committed_at: string };
type Project = { project_id: string; name: string; path: string; default_branch: string; current_head: string; current_branch: string; branches: Branch[] };
type RecentProject = { project_id: string; name: string; path: string };

type TabId = "overview" | "code" | "rules" | "scoring";
const tabs: { id: TabId; label: string; icon: typeof FileText }[] = [
  { id: "overview", label: "概览", icon: FileText },
  { id: "code", label: "代码变更", icon: Code2 },
  { id: "rules", label: "风险规则", icon: ShieldAlert },
  { id: "scoring", label: "评分配置", icon: SlidersHorizontal },
];
const domainLabels: Record<string, string> = {
  api: "接口行为", auth: "认证与权限", data: "数据与持久化", config: "应用配置", code: "代码结构", workflow: "过程协同",
};
const ruleLabels: Record<string, string> = {
  "api.signature_changed": "接口签名变化",
  "auth.permission_structure_changed": "权限结构变化",
  "data.transaction_structure_changed": "数据 / 事务结构变化",
  "config.configuration_structure_changed": "配置结构变化",
  "code.exception_structure_changed": "异常处理结构变化",
  "code.swallowed_exception": "静默吞异常",
  "code.bare_exception": "宽泛或裸异常捕获",
  "code.dynamic_execution": "动态代码执行",
  "code.unmanaged_open": "未用 with 管理的 open",
  "code.deep_control_flow": "深层控制流嵌套",
  "code.hardcoded_secret": "硬编码敏感字面量",
  "code.global_mutable_state": "全局可变状态",
  "data.django_raw_sql_execution": "Django 原生 SQL 执行",
  "auth.django_csrf_exempt_added": "新增 CSRF 豁免装饰器",
  "api.drf_viewset_action_changed": "DRF ViewSet 动作变更",
  "data.django_destructive_migration": "Django 破坏性迁移操作",
  "auth.drf_permission_policy_downgrade": "DRF 权限策略降级",
  "config.django_sensitive_settings_changed": "Django 敏感部署设置放宽",
  "data.django_non_null_constraint_tightened": "Django 非空约束收紧缺默认值",
  "auth.drf_permission_decorator_removed": "DRF 权限装饰器移除",
  "auth.drf_queryset_scope_tighten_bypassed": "DRF QuerySet 范围收窄绕过",
  "data.django_signal_receiver_leak": "Django 信号接收器缺少 dispatch_uid",
  "data.django_field_rename_without_db_column": "Django 字段改名未指定 db_column",
  "api.drf_public_parameter_added": "DRF 公开接口新增必填参数",
  "api.drf_public_parameter_removed": "DRF 公开接口删除参数或字段",
  "api.django_url_pattern_changed": "Django URL 路由模式变更",
  "code.assert_in_production": "生产代码中使用 assert",
  "code.mutable_default_argument": "函数可变默认参数",
  "workflow.test_collaboration_gap": "生产代码变更未见测试路径变更",
};
const outcomeLabels: Record<RuleOutcome["state"], string> = {
  Hit: "命中", NotFound: "未发现", Unanalyzed: "无法分析",
};
const reasonLabels: Record<string, string> = {
  path_classification_unavailable: "路径无法分类",
  diff_stats_unavailable: "差异统计不完整",
  unsupported_stage04_details: "结构细节不足",
  syntax_error: "语法解析失败",
  head_parse_failed: "头版本解析失败",
  git_show_error: "源码无法读取",
  missing_framework_context: "缺少该规则的框架或路径上下文",
  context_not_established: "没有可完成判断的对象",
  missing_file_change_channel: "没有文件变更通道",
  prior_stage_unavailable: "前置阶段不可用",
};
const fallbackPresets: PresetItem[] = [
  {
    preset: "balanced",
    name: "均衡基线",
    description: "全量 29 条规则分层赋予 1~3 启发式分值，兼顾安全性、框架契约与代码健康度",
    enabled_rule_count: 29,
    thresholds: { medium: 30, high: 65 },
    rule_thresholds: { "code.deep_control_flow": { max_depth: 4 }, "code.hardcoded_secret": { min_length: 8 } },
  },
  {
    preset: "security_focus",
    name: "安全加固审查",
    description: "聚焦认证权限降级、凭据泄露、CSRF 与危险执行等高危操作",
    enabled_rule_count: 29,
    thresholds: { medium: 25, high: 55 },
    rule_thresholds: { "code.deep_control_flow": { max_depth: 4 }, "code.hardcoded_secret": { min_length: 6 } },
  },
  {
    preset: "framework_upgrade",
    name: "框架与迁移升级",
    description: "聚焦破坏性迁移、数据库字段改名、URL 路由与公开 API 参数兼容性",
    enabled_rule_count: 29,
    thresholds: { medium: 30, high: 65 },
    rule_thresholds: { "code.deep_control_flow": { max_depth: 4 }, "code.hardcoded_secret": { min_length: 8 } },
  },
  {
    preset: "daily_review",
    name: "日常代码合规",
    description: "聚焦测试覆盖协同、深层控制流、静默异常与可变默认参数等代码异味",
    enabled_rule_count: 29,
    thresholds: { medium: 30, high: 60 },
    rule_thresholds: { "code.deep_control_flow": { max_depth: 3 }, "code.hardcoded_secret": { min_length: 8 } },
  },
  {
    preset: "legacy_baseline",
    name: "历史兼容基线",
    description: "保持 v1.0~v1.2 初始 10 分满分基线（结构 9 分 + 协同 1 分），供历史测试与回归比对",
    enabled_rule_count: 29,
    thresholds: { medium: 30, high: 65 },
    rule_thresholds: { "code.deep_control_flow": { max_depth: 4 }, "code.hardcoded_secret": { min_length: 8 } },
  },
];

function reasonText(reason: string) { return reasonLabels[reason] ?? reason; }
function outcomesRecorded(report: Report) { return report.rule_outcome_availability === "recorded" && Array.isArray(report.rule_outcomes); }
function outcomeFor(report: Report, ruleId: string) {
  return report.rule_outcomes?.find((item) => item.rule_id === ruleId);
}
function outcomeNote(outcome: RuleOutcome) {
  if (outcome.state !== "Unanalyzed") return "";
  return (outcome.reasons ?? []).map((item) => {
    const objects = item.objects.map((object) => object.node_id ? `${object.path || "本次变更"}:${object.node_id}` : (object.path || "本次变更")).filter(Boolean);
    const shown = objects.slice(0, 3).join("、");
    const extra = objects.length > 3 ? ` 等 ${objects.length} 个对象` : "";
    return `${reasonText(item.reason)}${shown ? `（${shown}${extra}）` : ""}`;
  }).join("；");
}
function findingAbsenceCopy(report: Report) {
  if (!outcomesRecorded(report)) return "这次结果没有规则终态记录。没有 Finding 不能当成未发现或已通过，也不表示代码安全。";
  const outcomes = report.rule_outcomes ?? [];
  const unanalyzed = outcomes.filter((item) => item.state === "Unanalyzed").length;
  const notFound = outcomes.filter((item) => item.state === "NotFound").length;
  if (unanalyzed > 0) return `没有规则命中。${notFound} 条规则在适用上下文中未发现特征，${unanalyzed} 条无法分析。无法分析不是通过，也不表示代码安全。`;
  return "已启用且上下文适用的规则均未发现风险特征。这不是安全结论。";
}
function collaborationCopy(report: Report) {
  const outcome = outcomeFor(report, "workflow.test_collaboration_gap");
  if (!outcomesRecorded(report) || !outcome) {
    return { tone: "neutral", text: "历史快照没有测试协同规则的终态。文件计数不能当成已有测试覆盖，也不表示代码安全。" };
  }
  if (outcome.state === "Hit") return { tone: "attention", text: "生产代码变更未见测试路径变更。这是复核提示，不是测试缺失或安全结论。" };
  if (outcome.state === "NotFound") return { tone: "neutral", text: "测试协同规则已在适用的文件变更里完整执行，未发现该复核特征。这不是安全结论。" };
  return { tone: "attention", text: "测试协同规则无法分析。没有可成立的测试上下文结论，不能当成已通过或代码安全。" };
}
function rerunTierLabel(meta?: SnapshotMeta) {
  if (!meta) return "全量执行";
  if (meta.rerun_tier === "stage07_rescore_only") return "Tier 2 · 仅重算评分";
  if (meta.rerun_tier === "stage05_rules_rerun") return "Tier 1 · 复用 AST 重算规则";
  return "Tier 0 · 全量执行";
}
function gatekeeperSummary(report: Report) {
  const basis = report.score_basis;
  if (!basis.gatekeeper_lift) return null;
  const rules = Array.from(new Set([
    ...(basis.gatekeeper_finding_rule_ids ?? []),
    ...(basis.gatekeeper_structural_rule_ids ?? []),
  ]));
  const hits = basis.gatekeeper_structural_hits ?? [];
  return {
    rules,
    hits,
    text: `触发一票抬升（Gatekeeper）：命中高危契约特征（${rules.map((id) => ruleLabels[id] ?? id).join("、") || "高危规则"}），无论综合加权分是否达标，均强制抬升复核优先级为「优先复核」。`,
  };
}

const initialConfig: Config = {
  preset: "legacy_baseline",
  enabled_rules: Object.keys(ruleLabels),
  rule_weights: {
    "api.signature_changed": 2,
    "auth.permission_structure_changed": 3,
    "data.transaction_structure_changed": 2,
    "config.configuration_structure_changed": 1,
    "code.exception_structure_changed": 1,
    "code.swallowed_exception": 0,
    "code.bare_exception": 0,
    "code.dynamic_execution": 0,
    "code.unmanaged_open": 0,
    "code.deep_control_flow": 0,
    "code.hardcoded_secret": 0,
    "code.global_mutable_state": 0,
    "data.django_raw_sql_execution": 0,
    "auth.django_csrf_exempt_added": 0,
    "api.drf_viewset_action_changed": 0,
    "data.django_destructive_migration": 0,
    "auth.drf_permission_policy_downgrade": 0,
    "config.django_sensitive_settings_changed": 0,
    "data.django_non_null_constraint_tightened": 0,
    "auth.drf_permission_decorator_removed": 0,
    "auth.drf_queryset_scope_tighten_bypassed": 0,
    "data.django_signal_receiver_leak": 0,
    "data.django_field_rename_without_db_column": 0,
    "api.drf_public_parameter_added": 0,
    "api.drf_public_parameter_removed": 0,
    "api.django_url_pattern_changed": 0,
    "code.assert_in_production": 0,
    "code.mutable_default_argument": 0,
    "workflow.test_collaboration_gap": 1,
  },
  test_collaboration_weight: 1,
  test_collaboration_enabled: true,
  thresholds: { medium: 30, high: 65 },
  rule_thresholds: {
    "code.deep_control_flow": { max_depth: 4 },
    "code.hardcoded_secret": { min_length: 8 },
  },
};

function riskLabel(level: string) { return level === "high" ? "优先复核" : level === "medium" ? "建议复核" : "常规"; }
function riskClass(level: string) { return level === "high" ? "risk-high" : level === "medium" ? "risk-medium" : "risk-low"; }
function ruleDomain(ruleId: string) { return ruleId.split(".", 1)[0]; }
function domainIcon(domain: string) {
  if (domain === "api") return <Network size={15} />;
  if (domain === "auth") return <LockKeyhole size={15} />;
  if (domain === "data") return <Settings2 size={15} />;
  if (domain === "workflow") return <GitPullRequest size={15} />;
  return <AlertCircle size={15} />;
}
function roleLabel(role: string) { return role === "business" ? "业务" : role === "test" ? "测试" : "其他"; }
function shortSha(value?: string) { return value ? value.slice(0, 7) : "—"; }
function evidenceDetail(item: Evidence) {
  if (item.capture_form) return `捕获形式 ${item.capture_form}`;
  if (typeof item.nesting_depth === "number") {
    return `嵌套深度 ${item.nesting_depth}${typeof item.depth_threshold === "number" ? `（阈值 ${item.depth_threshold}）` : ""}`;
  }
  if (item.binding_name) return `绑定 ${item.binding_name}，长度 ${item.value_length}`;
  if (item.mutable_state_form === "global_statement") return `global ${(item.binding_targets || []).join("、")}`;
  if (item.mutable_state_form === "mutable_binding") return `可变绑定 ${(item.binding_targets || []).join("、")}`;
  if (item.path_class === "production" && typeof item.additions === "number" && typeof item.deletions === "number") {
    return `生产代码 +${item.additions} / -${item.deletions}`;
  }
  if (item.used_as_with_context === false) return "open 未作为 with 上下文";
  if (item.operation) return `操作 ${item.operation}`;
  if (item.setting_name) return `设置 ${item.setting_name}${item.direction ? ` (${item.direction})` : ""}`;
  if (item.permission_policy) return `权限策略 ${item.permission_policy}`;
  if (item.decorator) return `装饰器 ${item.decorator}`;
  if (item.signal) return `信号 ${item.signal}`;
  if (item.old_field && item.new_field) return `字段 ${item.old_field} → ${item.new_field}`;
  if (item.parameter_name) return `参数/字段 ${item.parameter_name}`;
  if (item.route) return `路由 ${item.route}`;
  if (item.action_name) return `动作 ${item.action_name}`;
  if (item.container_kind) return `默认容器 ${item.container_kind}`;
  if (item.callee_name) return `直接调用 ${item.callee_name}`;
  if (item.handler_body_is_single_pass) return "处理体只有 pass";
  return "";
}
function configFromReport(report: Report): Config {
  const snap = report.config_snapshot;
  const base = report.score_basis.configuration;
  return {
    preset: snap?.preset ?? base.preset ?? "legacy_baseline",
    enabled_rules: snap?.enabled_rules ?? base.enabled_rules,
    rule_weights: { ...initialConfig.rule_weights, ...(snap?.rule_weights ?? base.rule_weights) },
    test_collaboration_weight: snap?.test_collaboration_weight ?? base.test_collaboration_weight,
    test_collaboration_enabled: snap?.test_collaboration_enabled ?? base.test_collaboration_enabled,
    thresholds: snap?.thresholds ?? base.thresholds,
    rule_thresholds: snap?.rule_thresholds ?? base.rule_thresholds ?? initialConfig.rule_thresholds,
  };
}

export function Dashboard() {
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [presets, setPresets] = useState<PresetItem[]>(fallbackPresets);
  const [activePr, setActivePr] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [report, setReport] = useState<Report | null>(null);
  const [baselineScore, setBaselineScore] = useState<number | null>(null);
  const [config, setConfig] = useState<Config>(initialConfig);
  const [selectedPath, setSelectedPath] = useState("");
  const [focusLines, setFocusLines] = useState<number[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("all");
  const [domainFilter, setDomainFilter] = useState("all");
  const [expandedRule, setExpandedRule] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [analysisMode, setAnalysisMode] = useState<"project" | "sample">("project");
  const [project, setProject] = useState<Project | null>(null);
  const [projectPath, setProjectPath] = useState("");
  const [baseRef, setBaseRef] = useState("");
  const [headRef, setHeadRef] = useState("");
  const [projectBusy, setProjectBusy] = useState(false);
  const [recentProjects, setRecentProjects] = useState<RecentProject[]>([]);

  // Sidebar Rule Catalog Explorer state
  const [sidebarRuleSearch, setSidebarRuleSearch] = useState("");
  const [sidebarStateFilter, setSidebarStateFilter] = useState<string>("all");
  const [collapsedDomains, setCollapsedDomains] = useState<Record<string, boolean>>({});
  const [selectedCatalogRule, setSelectedCatalogRule] = useState<string | null>(null);

  const writeLocation = useCallback((pr: number, tab: TabId, mode: "push" | "replace" = "push") => {
    const query = new URLSearchParams(window.location.search);
    query.delete("project"); query.delete("base"); query.delete("head");
    query.set("pr", String(pr));
    query.set("tab", tab);
    const url = `${window.location.pathname}?${query.toString()}`;
    if (mode === "push") window.history.pushState(null, "", url);
    else window.history.replaceState(null, "", url);
  }, []);

  const loadPr = useCallback(async (prNumber: number, tab: TabId, nextConfig?: Config, historyMode: "push" | "replace" = "push") => {
    setBusy(true);
    setError("");
    setActivePr(prNumber);
    setActiveTab(tab);
    setReport(null);
    setFocusLines([]);
    setDrawerOpen(false);
    setAnalysisMode("sample");
    if (nextConfig) setConfig(nextConfig);
    writeLocation(prNumber, tab, historyMode);
    try {
      const response = await fetch(`/api/pr/${prNumber}`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "无法载入该 PR");
      const reportConfig = nextConfig ?? configFromReport(payload as Report);
      if (!nextConfig) setConfig(reportConfig);
      setReport(payload as Report);
      const firstFile = (payload as Report).files.find((file) => file.role === "business" && file.hunks.length > 0)
        ?? (payload as Report).files.find((file) => file.hunks.length > 0)
        ?? (payload as Report).files[0];
      setSelectedPath(firstFile?.path ?? "");
      setBaselineScore((payload as Report).score);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "载入 PR 失败");
    } finally {
      setBusy(false);
    }
  }, [writeLocation]);

  const loadProject = useCallback(async (path: string) => {
    setProjectBusy(true); setError(""); setReport(null); setActivePr(null); setAnalysisMode("project");
    try {
      const response = await fetch("/api/projects/load", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path }) });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error?.message || payload.error || "项目加载失败");
      const loaded = payload.project as Project;
      const query = new URLSearchParams(window.location.search);
      const requestedProject = query.get("project");
      const sameProject = requestedProject === loaded.project_id;
      setProject(loaded); setProjectPath(loaded.path);
      const savedRecent = JSON.parse(window.localStorage.getItem("prisk.recentProjects") ?? "[]") as Array<string | RecentProject>;
      const recent = [{ project_id: loaded.project_id, name: loaded.name, path: loaded.path }, ...savedRecent.map((item) => typeof item === "string" ? { project_id: "", name: item.split(/[\\/]/).pop() ?? item, path: item } : item).filter((item) => item.path !== loaded.path)].slice(0, 5);
      setRecentProjects(recent); window.localStorage.setItem("prisk.recentProjects", JSON.stringify(recent));
      const requestedBase = sameProject ? query.get("base") : null; const requestedHead = sameProject ? query.get("head") : null;
      const requestedTab = query.get("tab") as TabId | null;
      if (sameProject && tabs.some((item) => item.id === requestedTab)) setActiveTab(requestedTab as TabId);
      else setActiveTab("overview");
      const nextBase = loaded.branches.some((item) => item.ref === requestedBase) ? requestedBase! : loaded.default_branch;
      const currentBranch = loaded.branches.find((item) => item.ref === loaded.current_branch && item.ref !== nextBase)?.ref;
      const nextHead = loaded.branches.some((item) => item.ref === requestedHead) ? requestedHead! : (currentBranch ?? loaded.branches.find((item) => item.ref !== nextBase)?.ref ?? nextBase);
      setBaseRef(nextBase); setHeadRef(nextHead);
      query.set("project", loaded.project_id); query.set("base", nextBase); query.set("head", nextHead); query.set("tab", sameProject && tabs.some((item) => item.id === requestedTab) ? requestedTab! : "overview");
      for (const key of ["pr"]) query.delete(key);
      window.history.replaceState(null, "", `${window.location.pathname}?${query.toString()}`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "项目加载失败"); }
    finally { setProjectBusy(false); }
  }, []);

  const analyzeBranch = useCallback(async (loaded: Project, base: string, head: string, nextConfig?: Config, refresh = false) => {
    setBusy(true); setError(""); setAnalysisMode("project");
    try {
      const response = await fetch("/api/branch-analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: loaded.project_id, base_ref: base, head_ref: head, config: nextConfig, refresh }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error?.message || payload.error || "分支分析失败");
      const nextReport = { ...payload, title: `${base} → ${head}`, repo: loaded.name, author: "本地 Git 分支", url: undefined, pr_number: undefined } as Report;
      setProject(loaded); setBaseRef(base); setHeadRef(head); setReport(nextReport);
      setConfig(nextConfig ?? configFromReport(nextReport));
      if (!nextConfig) setBaselineScore(nextReport.score);
      setSelectedPath((nextReport.files.find((file) => file.role === "business" && file.hunks.length > 0) ?? nextReport.files.find((file) => file.hunks.length > 0) ?? nextReport.files[0])?.path ?? "");
      if (refresh) {
        setNotice("已强制刷新 Git/AST 快照并全量重算");
        window.setTimeout(() => setNotice(""), 1800);
      } else if (nextConfig) {
        setNotice(`已按新配置重算（${rerunTierLabel(nextReport.snapshot_meta)}）`);
        window.setTimeout(() => setNotice(""), 1800);
      }
      const query = new URLSearchParams(window.location.search); query.delete("pr"); query.set("project", loaded.project_id); query.set("base", base); query.set("head", head); query.set("tab", activeTab); window.history.pushState(null, "", `${window.location.pathname}?${query.toString()}`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "分支分析失败"); }
    finally { setBusy(false); }
  }, [activeTab]);

  const runAnalysis = useCallback(async () => {
    if (analysisMode === "project" && project) {
      await analyzeBranch(project, baseRef, headRef, config, false);
      return;
    }
    if (activePr === null) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/analyze", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pr_number: activePr, config }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "重算失败");
      const nextReport = payload as Report;
      setReport(nextReport);
      setNotice(`当前 PR 已按新配置重算（${rerunTierLabel(nextReport.snapshot_meta)}）`);
      window.setTimeout(() => setNotice(""), 1800);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "重算失败");
    } finally {
      setBusy(false);
    }
  }, [activePr, analysisMode, project, baseRef, headRef, config, analyzeBranch]);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/config/presets").then(async (response) => {
      if (!response.ok) return null;
      return response.json() as Promise<{ presets?: PresetItem[] }>;
    }).then((payload) => {
      if (!cancelled && payload?.presets?.length) {
        setPresets(payload.presets);
      }
    }).catch(() => undefined);

    fetch("/api/dataset").then(async (response) => {
      if (!response.ok) throw new Error("演示 API 暂不可用");
      return response.json() as Promise<Dataset>;
    }).then((data) => {
      if (cancelled) return;
      setDataset(data);
      const savedRecent = JSON.parse(window.localStorage.getItem("prisk.recentProjects") ?? "[]") as Array<string | RecentProject>;
      const recent = savedRecent.map((item) => typeof item === "string" ? { project_id: "", name: item.split(/[\\/]/).pop() ?? item, path: item } : item);
      setRecentProjects(recent);
      const requestedProject = new URLSearchParams(window.location.search).get("project");
      const selectedRecent = recent.find((item) => item.project_id === requestedProject) ?? recent[0];
      if (selectedRecent) { setProjectPath(selectedRecent.path); void loadProject(selectedRecent.path); }
    }).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "初始化失败"));
    return () => { cancelled = true; };
  }, [loadProject]);

  useEffect(() => {
    const onPopState = () => {
      const query = new URLSearchParams(window.location.search);
      const number = Number(query.get("pr"));
      const tab = query.get("tab") as TabId | null;
      if (dataset?.prs.some((item) => item.pr_number === number && item.status === "ok")) {
        void loadPr(number, tabs.some((item) => item.id === tab) ? tab as TabId : "overview", undefined, "replace");
      }
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [dataset, loadPr]);

  useEffect(() => {
    if (analysisMode === "sample" && activePr !== null) writeLocation(activePr, activeTab, "replace");
    if (analysisMode === "project" && project) {
      const query = new URLSearchParams(window.location.search); query.set("project", project.project_id); query.set("base", baseRef); query.set("head", headRef); query.set("tab", activeTab);
      window.history.replaceState(null, "", `${window.location.pathname}?${query.toString()}`);
    }
  }, [activePr, activeTab, analysisMode, project, baseRef, headRef, writeLocation]);

  useEffect(() => {
    if (activeTab !== "code" || focusLines.length === 0 || !selectedPath) return;
    const targetLine = focusLines[0];
    requestAnimationFrame(() => {
      const rows = [...document.querySelectorAll<HTMLElement>("[data-diff-old-line], [data-diff-new-line]")];
      const target = rows.find((row) => row.dataset.filePath === selectedPath && (
        Number(row.dataset.diffOldLine) === targetLine || Number(row.dataset.diffNewLine) === targetLine
      ));
      target?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }, [activeTab, focusLines, selectedPath]);

  const filteredPrs = useMemo(() => (dataset?.prs ?? []).filter((item) => {
    if (item.status !== "ok") return false;
    if (riskFilter !== "all" && item.risk_level !== riskFilter) return false;
    if (domainFilter !== "all" && !item.domains.includes(domainFilter)) return false;
    return `${item.pr_number} ${item.title} ${item.author ?? ""}`.toLowerCase().includes(search.toLowerCase());
  }), [dataset, riskFilter, domainFilter, search]);

  const openTab = (tab: TabId) => {
    setActiveTab(tab);
    if (activePr !== null) writeLocation(activePr, tab);
  };
  const choosePr = (item: PRItem) => {
    setConfig(initialConfig);
    void loadPr(item.pr_number, "overview", initialConfig);
  };
  const locateEvidence = (evidence: Evidence) => {
    const file = report?.files.find((item) => item.path === evidence.path || item.old_path === evidence.path || item.new_path === evidence.path);
    if (!file) return;
    setSelectedPath(file.path);
    setFocusLines(evidence.lines);
    setExpandedRule(null);
    setSelectedCatalogRule(null);
    openTab("code");
    // Scroll file card into view
    setTimeout(() => {
      const el = document.getElementById(`diff-file-${encodeURIComponent(file.path)}`);
      el?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
  };
  const updateRuleWeight = (ruleId: string, value: number) => setConfig((current) => ({
    ...current,
    rule_weights: { ...current.rule_weights, [ruleId]: value },
    ...(ruleId === "workflow.test_collaboration_gap" ? { test_collaboration_weight: value } : {}),
  }));
  const toggleRule = (ruleId: string) => setConfig((current) => {
    const enabled = current.enabled_rules.includes(ruleId);
    const enabledRules = enabled
      ? current.enabled_rules.filter((item) => item !== ruleId)
      : [...current.enabled_rules, ruleId];
    if (ruleId !== "workflow.test_collaboration_gap") {
      return { ...current, enabled_rules: enabledRules };
    }
    return { ...current, enabled_rules: enabledRules, test_collaboration_enabled: !enabled };
  });
  const selectPreset = (item: PresetItem) => {
    setConfig((current) => ({
      preset: item.preset,
      enabled_rules: item.enabled_rules ? [...item.enabled_rules] : (dataset?.rules.map((r) => r.rule_id) ?? current.enabled_rules),
      rule_weights: item.rule_weights ? { ...item.rule_weights } : current.rule_weights,
      test_collaboration_weight: item.test_collaboration_weight ?? item.rule_weights?.["workflow.test_collaboration_gap"] ?? current.test_collaboration_weight,
      test_collaboration_enabled: item.test_collaboration_enabled ?? true,
      thresholds: { ...item.thresholds },
      rule_thresholds: {
        "code.deep_control_flow": { max_depth: item.rule_thresholds?.["code.deep_control_flow"]?.max_depth ?? 4 },
        "code.hardcoded_secret": { min_length: item.rule_thresholds?.["code.hardcoded_secret"]?.min_length ?? 8 },
      },
    }));
  };

  const downloadReport = (format: "json" | "md") => {
    if (!report) return;
    const content = format === "json" ? JSON.stringify(report, null, 2) : renderMarkdown(report);
    const blob = new Blob([content], { type: format === "json" ? "application/json" : "text/markdown" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `prisk-${report.pr_number ? `pr-${report.pr_number}` : `branch-${report.base_ref}-to-${report.head_ref}`}-report.${format}`;
    link.click();
    URL.revokeObjectURL(link.href);
  };

  const resetConfig = () => {
    setConfig(initialConfig);
    if (analysisMode === "project" && project) {
      void analyzeBranch(project, baseRef, headRef, initialConfig);
      return;
    }
    if (activePr !== null) {
      void fetch("/api/analyze", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pr_number: activePr, config: initialConfig }),
      }).then((response) => response.json()).then((payload) => setReport(payload as Report));
    }
  };

  // Group rules by domain for sidebar
  const allKnownRuleIds = Object.keys(ruleLabels);
  const groupedRules = useMemo(() => {
    const groups: Record<string, string[]> = {
      api: [], auth: [], data: [], config: [], code: [], workflow: [],
    };
    for (const ruleId of allKnownRuleIds) {
      const d = ruleDomain(ruleId);
      if (groups[d]) groups[d].push(ruleId);
    }
    return groups;
  }, [allKnownRuleIds]);

  const sidebarFilteredRules = useMemo(() => {
    return allKnownRuleIds.filter((id) => {
      const label = ruleLabels[id] ?? id;
      const matchSearch = !sidebarRuleSearch || id.toLowerCase().includes(sidebarRuleSearch.toLowerCase()) || label.includes(sidebarRuleSearch);
      if (!matchSearch) return false;
      if (sidebarStateFilter === "all" || !report) return true;
      const state = catalogState(report, id);
      return state.stateKey === sidebarStateFilter;
    });
  }, [allKnownRuleIds, sidebarRuleSearch, sidebarStateFilter, report]);

  if (analysisMode === "project" && !report) {
    return <ProjectPicker
      path={projectPath} setPath={setProjectPath} project={project} baseRef={baseRef} setBaseRef={setBaseRef}
      headRef={headRef} setHeadRef={setHeadRef} busy={projectBusy || busy} error={error}
      onLoad={(path) => void loadProject(path)} onAnalyze={() => project && void analyzeBranch(project, baseRef, headRef)}
      onSample={() => { setProject(null); void loadPr(226, "overview"); }}
      recentProjects={recentProjects}
    />;
  }

  const selectedRuleMeta = dataset?.rules.find((r) => r.rule_id === selectedCatalogRule);

  return (
    <div className="review-shell">
      {/* =========================================================================
          LEFT SIDEBAR: Brand + Project/Branch + Rule Catalog Explorer
          ========================================================================= */}
      <aside className="review-sidebar">
        <div className="review-brand">
          <span className="brand-mark"><Code2 size={16} /></span>
          <strong>prisk<span>.</span></strong>
          <span className="brand-tag">REVIEW</span>
        </div>

        {/* Project Context Button (with ellipsis) */}
        <button
          className="repo-context"
          onClick={() => { setReport(null); setAnalysisMode("project"); }}
          title={project?.path ?? (report?.repo ?? "选择项目")}
        >
          <span className="repo-avatar">{(report?.repo ?? project?.name ?? "P").slice(0, 1).toUpperCase()}</span>
          <div className="repo-context-main">
            <strong>{report?.repo ?? project?.name ?? "选择项目"}</strong>
            <small>{project?.path ?? (analysisMode === "sample" ? "冻结 NetBox 样本" : "加载本地 Git 仓库")}</small>
          </div>
        </button>

        {/* Current Analysis Branch/PR Button */}
        <button
          className="current-pr-button"
          onClick={() => analysisMode === "sample" ? setDrawerOpen(true) : (setReport(null), setAnalysisMode("project"))}
          title={report ? (report.pr_number ? `#${report.pr_number} ${report.title}` : `${report.base_ref} → ${report.head_ref}`) : "选择分析对象"}
        >
          <GitPullRequest size={15} />
          <span>
            <small>{analysisMode === "sample" ? "Pull Request" : "分支审计"}</small>
            <strong>{report ? (report.pr_number ? `#${report.pr_number}` : `${report.base_ref} → ${report.head_ref}`) : "选择对象"}</strong>
          </span>
          <ChevronDown size={14} />
        </button>

        {/* 29 Rules Sidebar Catalog */}
        <section className="sidebar-rule-section" aria-label="规则目录">
          <div className="sidebar-rule-header">
            <h3>规则目录</h3>
            <span className="sidebar-rule-count">{report ? `${report.findings.length} 命中 / 29 规则` : "29 条规则"}</span>
          </div>

          <div className="sidebar-rule-search">
            <Search size={13} />
            <input
              value={sidebarRuleSearch}
              onChange={(e) => setSidebarRuleSearch(e.target.value)}
              placeholder="搜索规则名称或 ID..."
            />
            {sidebarRuleSearch && <button onClick={() => setSidebarRuleSearch("")} className="icon-button" style={{ width: 16, height: 16, border: 0 }}><X size={12} /></button>}
          </div>

          <div className="sidebar-rule-filter-chips">
            <button className={`rule-chip ${sidebarStateFilter === "all" ? "active" : ""}`} onClick={() => setSidebarStateFilter("all")}>全部</button>
            <button className={`rule-chip ${sidebarStateFilter === "Hit" ? "active" : ""}`} onClick={() => setSidebarStateFilter("Hit")}>命中</button>
            <button className={`rule-chip ${sidebarStateFilter === "NotFound" ? "active" : ""}`} onClick={() => setSidebarStateFilter("NotFound")}>未发现</button>
            <button className={`rule-chip ${sidebarStateFilter === "Unanalyzed" ? "active" : ""}`} onClick={() => setSidebarStateFilter("Unanalyzed")}>无法分析</button>
          </div>

          <div className="sidebar-rule-tree">
            {Object.entries(groupedRules).map(([domain, ruleIds]) => {
              const visibleRules = ruleIds.filter((id) => sidebarFilteredRules.includes(id));
              if (visibleRules.length === 0) return null;
              const isCollapsed = Boolean(collapsedDomains[domain]);
              return (
                <div key={domain} className="sidebar-domain-group">
                  <button
                    className="sidebar-domain-head"
                    onClick={() => setCollapsedDomains((c) => ({ ...c, [domain]: !c[domain] }))}
                  >
                    <span>
                      {domainIcon(domain)}
                      {domainLabels[domain] ?? domain}
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <span className="nav-tab-count" style={{ height: 16, minWidth: 16, fontSize: 10 }}>{visibleRules.length}</span>
                      {isCollapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
                    </span>
                  </button>

                  {!isCollapsed && visibleRules.map((ruleId) => {
                    const st = report ? catalogState(report, ruleId) : null;
                    const isSelected = selectedCatalogRule === ruleId;
                    return (
                      <button
                        key={ruleId}
                        className={`sidebar-rule-item ${isSelected ? "selected" : ""}`}
                        onClick={() => setSelectedCatalogRule(ruleId)}
                        title={`点击查看规则说明卡片：${ruleLabels[ruleId] ?? ruleId}`}
                      >
                        <div>
                          <strong>{ruleLabels[ruleId] ?? ruleId}</strong>
                          <small>{ruleId}</small>
                        </div>
                        {st && (
                          <span className={`rule-state-pill ${st.className}`}>
                            {st.stateKey === "Hit" ? "Hit" : st.stateKey === "NotFound" ? "OK" : st.stateKey === "Unanalyzed" ? "Gap" : "Off"}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </section>

        <div className="sidebar-footer">
          <span><span className="status-dot" /> {analysisMode === "sample" ? "本地冻结样本" : "本地分支审计"}</span>
          <span>v1.3</span>
        </div>
      </aside>

      {/* =========================================================================
          MAIN WORKSPACE: GitHub PR Style Header + Tabs + Content
          ========================================================================= */}
      <main className="review-main">
        {/* Compact GitHub PR Style Header */}
        <header className="gh-header">
          <div className="gh-header-row1">
            <div className="gh-title-group">
              <h1>
                {report ? (
                  report.pr_number ? (
                    <>#{report.pr_number} {report.title}</>
                  ) : (
                    <><code>{report.base_ref}</code> → <code>{report.head_ref}</code></>
                  )
                ) : "载入分析"}
              </h1>
              {report && (
                <span className={`risk-pill ${riskClass(report.risk_level)}`}>
                  {riskLabel(report.risk_level)} · {report.score}/100
                </span>
              )}
              {report?.score_basis.gatekeeper_lift && (
                <span className="gatekeeper-pill">
                  <ShieldAlert size={13} /> 一票抬升
                </span>
              )}
            </div>

            <div className="gh-header-actions">
              {analysisMode === "project" && project && (
                <button
                  className="secondary-button"
                  onClick={() => void analyzeBranch(project, baseRef, headRef, config, true)}
                  disabled={busy}
                  title="强制丢弃缓存并重新提取 Git Diff 与 AST"
                >
                  <RotateCcw size={14} /> 强制刷新快照
                </button>
              )}
              {analysisMode === "sample" ? (
                <button className="secondary-button" onClick={() => setDrawerOpen(true)} disabled={!dataset}>
                  <ListFilter size={14} /> 切换 PR
                </button>
              ) : (
                <button className="secondary-button" onClick={() => { setReport(null); setAnalysisMode("project"); }}>
                  <ListFilter size={14} /> 更换项目
                </button>
              )}
              <button
                className="secondary-button"
                onClick={() => downloadReport("md")}
                disabled={!report}
                title="导出包含完整运行配置快照的 Markdown 审查报告"
              >
                <FileText size={14} /> 导出复核报告
              </button>
              <button
                className="icon-button"
                title="下载 JSON 报告（含配置快照与可复现载荷）"
                onClick={() => downloadReport("json")}
                disabled={!report}
              >
                <Download size={15} />
              </button>
            </div>
          </div>

          {/* Metadata Row */}
          <div className="gh-header-meta">
            {report && (
              <>
                <span className="meta-item">
                  {analysisMode === "sample" ? report.author ?? "NetBox contributor" : project?.name}
                </span>
                <span>·</span>
                <span className="meta-item">
                  commit <code>{shortSha(report.base_sha)}</code> → <code>{shortSha(report.head_sha)}</code>
                </span>
                <span>·</span>
                <span className="meta-item">
                  {report.summary.files_changed} 个变更文件（<span className="plus">+{report.summary.additions}</span> / <span className="minus">−{report.summary.deletions}</span>）
                </span>
                {report.snapshot_meta && (
                  <span className="meta-badge meta-tier" title={`执行层级：${report.snapshot_meta.rerun_tier}`}>
                    {rerunTierLabel(report.snapshot_meta)}
                  </span>
                )}
                {report.config_snapshot && (
                  <span className="meta-badge" title={`配置确定性指纹：${report.config_snapshot.config_digest}`}>
                    预设：{report.config_snapshot.preset_name}{report.config_snapshot.customized ? " (已定制)" : ""} · #{report.config_snapshot.config_digest.slice(0, 8)}
                  </span>
                )}
              </>
            )}
          </div>

          {/* GitHub UnderlineNav Tabs */}
          <nav className="gh-nav-tabs" aria-label="PR 审计视图">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                className={activeTab === id ? "gh-nav-tab active" : "gh-nav-tab"}
                onClick={() => openTab(id)}
              >
                <Icon size={16} />
                {label}
                {id === "code" && report && (
                  <span className="nav-tab-count">{report.files.length}</span>
                )}
                {id === "rules" && report && (
                  <span className="nav-tab-count">{report.findings.length}</span>
                )}
              </button>
            ))}
          </nav>
        </header>

        {/* Banners & Notices */}
        <div className="review-content">
          {error && <div className="error-banner"><AlertCircle size={16} />{error}</div>}
          {notice && <div className="toast"><Check size={16} />{notice}</div>}

          {!report ? (
            <div className="loading-panel">
              <LoaderCircle className="spin" size={24} />
              {busy ? "正在读取并分析分支快照…" : "等待选择分析对象"}
            </div>
          ) : (
            <>
              {activeTab === "overview" && (
                <Overview
                  report={report}
                  baselineScore={baselineScore}
                  onShowRules={() => openTab("rules")}
                  onShowCode={() => openTab("code")}
                  onLocate={locateEvidence}
                />
              )}
              {activeTab === "code" && (
                <CodeReview
                  report={report}
                  selectedPath={selectedPath}
                  setSelectedPath={(path) => { setSelectedPath(path); setFocusLines([]); }}
                  focusLines={focusLines}
                />
              )}
              {activeTab === "rules" && (
                <RulesView
                  report={report}
                  catalog={dataset?.rules ?? []}
                  expandedRule={expandedRule}
                  setExpandedRule={setExpandedRule}
                  onLocate={locateEvidence}
                  onOpenRuleCard={(id) => setSelectedCatalogRule(id)}
                />
              )}
              {activeTab === "scoring" && (
                <ScoringView
                  report={report}
                  catalog={dataset?.rules ?? []}
                  presets={presets}
                  config={config}
                  setConfig={setConfig}
                  onSelectPreset={selectPreset}
                  onWeight={updateRuleWeight}
                  onToggle={toggleRule}
                  onApply={() => void runAnalysis()}
                  onReset={resetConfig}
                  busy={busy}
                  baselineScore={baselineScore}
                />
              )}
            </>
          )}

          <footer className="review-footer">
            <span>
              <span className="status-dot" /> 本地审计链路 · {analysisMode === "project" ? "stage03.v1 · stage04.v1 · stage05.v2 · stage08.branch-report.v1 · config.snapshot.v1" : "stage03.v1 · stage04.v1 · stage05.v2 · stage07.report.v2 · config.snapshot.v1"}
            </span>
            <span>评分表示人工复核优先级，不是缺陷概率</span>
          </footer>
        </div>
      </main>

      {/* =========================================================================
          RULE DETAILS DRAWER / MODAL: Open when any rule is clicked in sidebar or table
          ========================================================================= */}
      {selectedCatalogRule && (
        <div className="drawer-backdrop" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) setSelectedCatalogRule(null); }}>
          <section className="rule-drawer" role="dialog" aria-modal="true" aria-labelledby="rule-drawer-title">
            <header className="rule-drawer-head">
              <div>
                <span className="risk-pill" style={{ fontSize: 11, background: "#ddf4ff", color: "#0969da", border: "1px solid #54aeff" }}>
                  {domainLabels[ruleDomain(selectedCatalogRule)] ?? ruleDomain(selectedCatalogRule)}
                </span>
                <h2 id="rule-drawer-title">{ruleLabels[selectedCatalogRule] ?? selectedCatalogRule}</h2>
                <code>{selectedCatalogRule}</code>
              </div>
              <button className="icon-button" title="关闭" onClick={() => setSelectedCatalogRule(null)}>
                <X size={18} />
              </button>
            </header>

            <div className="rule-drawer-body">
              {report && (
                <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", background: "#f6f8fa", borderRadius: 6, border: "1px solid #d0d7de" }}>
                  <strong>本次分析终态：</strong>
                  {(() => {
                    const st = catalogState(report, selectedCatalogRule);
                    return (
                      <span className={`risk-pill ${st.className === "hit" ? "risk-high" : st.className === "unanalyzed" ? "risk-medium" : "risk-low"}`}>
                        {st.label}
                      </span>
                    );
                  })()}
                </div>
              )}

              {/* Finding Evidence if hit */}
              {report?.findings.filter((f) => f.rule_id === selectedCatalogRule).map((finding, idx) => (
                <div key={idx} style={{ padding: "12px 14px", background: "#ffebe9", border: "1px solid #ff8182", borderRadius: 6 }}>
                  <strong style={{ color: "#cf222e", display: "block", marginBottom: 6 }}>本次命中证据（{finding.evidence.length} 项）：</strong>
                  <p style={{ margin: "0 0 8px", fontSize: 13, color: "#1f2328" }}>{finding.message}</p>
                  {finding.evidence.map((ev, eIdx) => (
                    <div key={eIdx} className="evidence-card" style={{ background: "#fff" }}>
                      <div>
                        <strong>{ev.path}</strong>
                        <div><code>{ev.lines.map((l) => `L${l}`).join(", ") || "无 Diff 行号"}</code> · <span>{ev.node_kind} · {ev.structural_change_type}</span></div>
                        {evidenceDetail(ev) ? <small style={{ color: "#59636e" }}>{evidenceDetail(ev)}</small> : null}
                      </div>
                      <button className="secondary-button" onClick={() => locateEvidence(ev)} disabled={!ev.lines.length}>
                        定位代码 <ArrowUpRight size={13} />
                      </button>
                    </div>
                  ))}
                </div>
              ))}

              <div className="drawer-field">
                <span>触发条件 (Trigger Feature)</span>
                <p>{selectedRuleMeta?.trigger || "基于局部 AST / Diff 结构特征闭集提取"}</p>
              </div>

              <div className="drawer-field">
                <span>适用范围 (Applicability)</span>
                <p>{selectedRuleMeta?.applicable_scope || "适用对应语言/框架的局部变更范围"}</p>
              </div>

              <div className="drawer-field">
                <span>复核建议 (Suggested Action)</span>
                <p>{selectedRuleMeta?.suggested_action || "检查该结构变更是否符合预期，排查潜在边界风险"}</p>
              </div>

              <div className="drawer-field">
                <span>已知限制 (Limitations)</span>
                <p>{selectedRuleMeta?.limitations || "单文件局部 AST 分析，未跨文件追踪符号全局定义"}</p>
              </div>

              <div className="drawer-field">
                <span>启发式权重</span>
                <p>当前启用权重：<strong>{config.rule_weights[selectedCatalogRule] ?? selectedRuleMeta?.default_weight ?? 0}</strong>（基线默认权重：{selectedRuleMeta?.default_weight ?? 0}）</p>
              </div>
            </div>
          </section>
        </div>
      )}

      {/* PR Selection Drawer (for NetBox sample mode) */}
      {drawerOpen && (
        <div className="drawer-backdrop" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) setDrawerOpen(false); }}>
          <section className="pr-drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
            <header className="drawer-header">
              <div>
                <h2 id="drawer-title">选择 Pull Request 样本</h2>
                <small style={{ color: "#59636e" }}>{dataset?.counts.analyzable ?? 0} 条可分析 PR</small>
              </div>
              <button className="icon-button" title="关闭" onClick={() => setDrawerOpen(false)}><X size={18} /></button>
            </header>
            <div className="drawer-controls">
              <div className="gh-search-input-box" style={{ height: 34, marginBottom: 8 }}>
                <Search size={15} />
                <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="搜索 PR 编号、标题或作者..." />
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <select className="secondary-button" style={{ flex: 1 }} value={riskFilter} onChange={(e) => setRiskFilter(e.target.value)}>
                  <option value="all">全部风险等级</option>
                  <option value="high">优先复核</option>
                  <option value="medium">建议复核</option>
                  <option value="low">常规</option>
                </select>
                <select className="secondary-button" style={{ flex: 1 }} value={domainFilter} onChange={(e) => setDomainFilter(e.target.value)}>
                  <option value="all">全部关注域</option>
                  {Object.entries(domainLabels).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
                </select>
              </div>
            </div>
            <div className="drawer-pr-list">
              {filteredPrs.map((item) => (
                <button
                  key={item.pr_number}
                  className={`drawer-pr ${item.pr_number === activePr ? "selected" : ""}`}
                  onClick={() => choosePr(item)}
                >
                  <div>
                    <span style={{ color: "#0969da", fontFamily: "var(--mono)", fontSize: 13, fontWeight: 600 }}>#{item.pr_number}</span>
                    <strong>{item.title}</strong>
                    <small>{item.author ?? "NetBox contributor"}</small>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <span className={`risk-pill ${riskClass(item.risk_level)}`}>{riskLabel(item.risk_level)}</span>
                    <small style={{ display: "block", marginTop: 4 }}>{item.finding_count} 命中</small>
                  </div>
                </button>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

/* ==========================================================================
   Project Picker Component
   ========================================================================== */
function ProjectPicker({
  path, setPath, project, baseRef, setBaseRef, headRef, setHeadRef, busy, error,
  onLoad, onAnalyze, onSample, recentProjects,
}: {
  path: string; setPath: (value: string) => void; project: Project | null; baseRef: string; setBaseRef: (value: string) => void;
  headRef: string; setHeadRef: (value: string) => void; busy: boolean; error: string; onLoad: (path: string) => void;
  onAnalyze: () => void; onSample: () => void; recentProjects: RecentProject[];
}) {
  const branches = project?.branches ?? [];
  return (
    <main className="project-picker-shell">
      <header className="picker-topbar">
        <span className="brand-mark"><Code2 size={18} /></span>
        <strong>prisk<span>.</span></strong>
        <span>本地 Git 分支审计</span>
      </header>
      <section className="project-picker-content">
        <h1>选择或输入本地 Git 项目</h1>
        <p className="picker-intro">读取本地仓库提交，通过 Git 三点 Diff 与 AST 分析，生成可追溯可复现的审查报告。</p>
        <form className="project-load-form" onSubmit={(e) => { e.preventDefault(); onLoad(path); }}>
          <label htmlFor="repo-path">本地仓库绝对路径</label>
          <div className="project-path-row">
            <input
              id="repo-path"
              value={path}
              onChange={(e) => setPath(e.target.value)}
              placeholder="例如 D:\\work\\my-django-project"
            />
            <button className="primary-button" disabled={busy || !path.trim()}>
              {busy ? <LoaderCircle size={15} className="spin" /> : <Search size={15} />}
              加载仓库
            </button>
          </div>
          {recentProjects.length > 0 && (
            <div className="recent-project-list">
              <span>最近使用的项目：</span>
              {recentProjects.map((recent) => (
                <button
                  type="button"
                  className="recent-project"
                  key={recent.path}
                  onClick={() => { setPath(recent.path); onLoad(recent.path); }}
                >
                  <RotateCcw size={14} />
                  <strong>{recent.name}</strong>
                  <code>{recent.path}</code>
                </button>
              ))}
            </div>
          )}
        </form>

        {error && <div className="error-banner" style={{ marginTop: 16 }}><AlertCircle size={16} />{error}</div>}

        {project && (
          <section className="loaded-project">
            <div className="loaded-project-heading">
              <span className="repo-avatar">{project.name.slice(0, 1).toUpperCase()}</span>
              <div>
                <h2>{project.name}</h2>
                <p>{project.path}</p>
                <small>{project.branches.length} 个分支 · 当前分支 {project.current_branch || "分离 HEAD"} · HEAD {shortSha(project.current_head)}</small>
              </div>
            </div>
            <div className="branch-selectors">
              <label>
                基准分支 (base)
                <select value={baseRef} onChange={(e) => setBaseRef(e.target.value)}>
                  {branches.map((b) => <option key={b.ref} value={b.ref}>{b.ref} ({b.short_sha})</option>)}
                </select>
              </label>
              <ArrowDownRight size={18} />
              <label>
                目标分支 (head)
                <select value={headRef} onChange={(e) => setHeadRef(e.target.value)}>
                  {branches.map((b) => <option key={b.ref} value={b.ref}>{b.ref} ({b.short_sha})</option>)}
                </select>
              </label>
            </div>
            <div className="project-actions">
              <small>采用 base...head 三点 Diff，不影响本地工作区，不执行任何写操作。</small>
              <button
                className="primary-button"
                onClick={onAnalyze}
                disabled={busy || !baseRef || !headRef || baseRef === headRef}
              >
                {busy ? <LoaderCircle size={15} className="spin" /> : <GitPullRequest size={15} />}
                开始审查分支
              </button>
            </div>
          </section>
        )}

        <div className="sample-entry">
          <div>
            <strong>需要体验？</strong>
            <span>可以加载已验证的冻结 NetBox PR 样本，查阅完整的审计与三态结果。</span>
          </div>
          <button className="secondary-button" onClick={onSample}>
            <FileText size={15} /> 加载冻结 NetBox 样本
          </button>
        </div>
      </section>
    </main>
  );
}

/* ==========================================================================
   Overview Tab Component
   ========================================================================== */
function Overview({
  report, baselineScore, onShowRules, onShowCode, onLocate,
}: {
  report: Report; baselineScore: number | null; onShowRules: () => void; onShowCode: () => void; onLocate: (evidence: Evidence) => void;
}) {
  const topFindings = report.findings.slice(0, 5);
  const collaboration = collaborationCopy(report);
  const gatekeeper = gatekeeperSummary(report);

  return (
    <div className="overview-page">
      <div className="overview-summary">
        <div className="score-summary">
          <span>当前复核优先级</span>
          <strong>{report.score}<small>/100</small></strong>
          <span className={`risk-pill ${riskClass(report.risk_level)}`}>
            {riskLabel(report.risk_level)}
          </span>
          <small>
            基线：{baselineScore ?? report.score} · 阈值：{report.score_basis.configuration.thresholds.medium}/{report.score_basis.configuration.thresholds.high}
          </small>
        </div>
        <div className="summary-details">
          <div className="summary-stat">
            <span>变更文件</span>
            <strong>{report.summary.files_changed}</strong>
          </div>
          <div className="summary-stat">
            <span>新增行数</span>
            <strong className="plus">+{report.summary.additions}</strong>
          </div>
          <div className="summary-stat">
            <span>删除行数</span>
            <strong className="minus">−{report.summary.deletions}</strong>
          </div>
          <div className="summary-stat">
            <span>业务 / 测试文件</span>
            <strong>{report.summary.business_files} / {report.summary.test_files}</strong>
          </div>
          <div className="summary-stat">
            <span>规则命中数</span>
            <strong>{report.findings.length}</strong>
          </div>
          <div className="summary-stat">
            <span>命中关注域</span>
            <strong style={{ fontSize: 14 }}>
              {(report.summary.domains ?? []).map((d) => domainLabels[d] ?? d).join("、") || "无"}
            </strong>
          </div>
        </div>
      </div>

      {gatekeeper && (
        <div className="gatekeeper-banner">
          <ShieldAlert size={20} style={{ flexShrink: 0, marginTop: 2 }} />
          <div>
            <strong>{gatekeeper.text}</strong>
            {gatekeeper.hits.length > 0 && (
              <small>结构证据：{gatekeeper.hits.map((h) => `${h.path} (${h.operation})`).join("；")}</small>
            )}
          </div>
        </div>
      )}

      <div className={`collab-banner ${collaboration.tone}`}>
        {collaboration.tone === "attention" ? <AlertCircle size={18} style={{ color: "#9a6700" }} /> : <CircleHelp size={18} />}
        <span>{collaboration.text}</span>
        <small>辅助协同信号</small>
      </div>

      <div className="overview-columns">
        <div className="overview-card">
          <div className="overview-card-header">
            <div>
              <h2>重点风险线索</h2>
              <p>本次分析命中的核心结构特征</p>
            </div>
            <button className="secondary-button" onClick={onShowRules} style={{ fontSize: 12, padding: "2px 8px" }}>
              查看全部 <ChevronRight size={13} />
            </button>
          </div>
          {topFindings.length ? (
            <div>
              {topFindings.map((finding, index) => (
                <button
                  key={`${finding.rule_id}-${index}`}
                  className="finding-item-btn"
                  onClick={() => finding.evidence[0] && onLocate(finding.evidence[0])}
                >
                  <span style={{ color: "#0969da" }}>{domainIcon(ruleDomain(finding.rule_id))}</span>
                  <div className="finding-item-info">
                    <strong>{ruleLabels[finding.rule_id] ?? finding.rule_id}</strong>
                    <small>{finding.evidence.length} 条证据 · {finding.evidence[0]?.path}</small>
                  </div>
                  <ArrowUpRight size={15} style={{ color: "#59636e" }} />
                </button>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <CircleHelp size={20} />
              {findingAbsenceCopy(report)}
            </div>
          )}
        </div>

        <div className="overview-card">
          <div className="overview-card-header">
            <div>
              <h2>变更范围与快照</h2>
              <p>{report.diff_mode === "three_dot" ? "来自 base...head 三点对比" : "来自冻结 PR 三点快照"}</p>
            </div>
            <button className="secondary-button" onClick={onShowCode} style={{ fontSize: 12, padding: "2px 8px" }}>
              审查代码 <ChevronRight size={13} />
            </button>
          </div>
          <div style={{ display: "grid", gap: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #d8dee4" }}>
              <span>业务代码文件</span>
              <strong>{report.summary.business_files}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #d8dee4" }}>
              <span>测试代码文件</span>
              <strong>{report.summary.test_files}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #d8dee4" }}>
              <span>其他配置文件</span>
              <strong>{Math.max(0, report.summary.files_changed - report.summary.business_files - report.summary.test_files)}</strong>
            </div>
            <div style={{ padding: "8px 0", fontSize: 13, color: "#59636e" }}>
              base: <code>{shortSha(report.base_sha)}</code> → head: <code>{shortSha(report.head_sha)}</code>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ==========================================================================
   Code Review (Files Changed) Component - GitHub Primer Style
   ========================================================================== */
type FileTreeNode =
  | { kind: "dir"; name: string; fullPath: string; children: FileTreeNode[]; fileCount: number }
  | { kind: "file"; name: string; fullPath: string; file: DiffFile };

function buildFileTree(files: DiffFile[]): FileTreeNode[] {
  type IntermediateDir = { dirs: Record<string, IntermediateDir>; files: DiffFile[] };
  const root: IntermediateDir = { dirs: {}, files: [] };

  for (const f of files) {
    const parts = f.path.split("/");
    let cur = root;
    for (let i = 0; i < parts.length - 1; i++) {
      const p = parts[i];
      if (!cur.dirs[p]) cur.dirs[p] = { dirs: {}, files: [] };
      cur = cur.dirs[p];
    }
    cur.files.push(f);
  }

  function convert(dir: IntermediateDir, parentPath = ""): FileTreeNode[] {
    const res: FileTreeNode[] = [];
    const dirEntries = Object.entries(dir.dirs).sort(([a], [b]) => a.localeCompare(b));

    for (const [dName, initialSub] of dirEntries) {
      let sub = initialSub;
      let combinedPath = parentPath ? `${parentPath}/${dName}` : dName;
      let displayName = dName;
      // Compact single child dirs (e.g. backend/app/modules)
      while (Object.keys(sub.dirs).length === 1 && sub.files.length === 0) {
        const nextKey = Object.keys(sub.dirs)[0];
        displayName += `/${nextKey}`;
        combinedPath += `/${nextKey}`;
        sub = sub.dirs[nextKey];
      }
      const children = convert(sub, combinedPath);
      const totalFiles = children.reduce((acc, c) => acc + (c.kind === "file" ? 1 : c.fileCount), 0);
      res.push({
        kind: "dir",
        name: displayName,
        fullPath: combinedPath,
        children,
        fileCount: totalFiles,
      });
    }

    const fileEntries = dir.files.sort((a, b) => a.path.localeCompare(b.path));
    for (const f of fileEntries) {
      const parts = f.path.split("/");
      res.push({
        kind: "file",
        name: parts[parts.length - 1],
        fullPath: f.path,
        file: f,
      });
    }
    return res;
  }

  return convert(root);
}

function CodeReview({
  report, selectedPath, setSelectedPath, focusLines,
}: {
  report: Report; selectedPath: string; setSelectedPath: (path: string) => void; focusLines: number[];
}) {
  const [fileSearch, setFileSearch] = useState("");
  const [viewMode, setViewMode] = useState<"stream" | "single">("stream");
  const [collapsedFiles, setCollapsedFiles] = useState<Record<string, boolean>>({});
  const [viewedFiles, setViewedFiles] = useState<Record<string, boolean>>({});
  const [collapsedDirs, setCollapsedDirs] = useState<Record<string, boolean>>({});

  const filteredFiles = useMemo(() => {
    return report.files.filter((f) => f.path.toLowerCase().includes(fileSearch.toLowerCase()));
  }, [report.files, fileSearch]);

  const treeNodes = useMemo(() => buildFileTree(filteredFiles), [filteredFiles]);

  const viewedCount = Object.values(viewedFiles).filter(Boolean).length;
  const totalCount = report.files.length;

  const toggleViewed = (path: string) => {
    setViewedFiles((prev) => {
      const nextVal = !prev[path];
      if (nextVal) {
        // Auto-collapse when viewed
        setCollapsedFiles((c) => ({ ...c, [path]: true }));
      }
      return { ...prev, [path]: nextVal };
    });
  };

  const toggleCollapse = (path: string) => {
    setCollapsedFiles((prev) => ({ ...prev, [path]: !prev[path] }));
  };

  const collapseAll = () => {
    const all: Record<string, boolean> = {};
    for (const f of report.files) all[f.path] = true;
    setCollapsedFiles(all);
  };

  const expandAll = () => {
    setCollapsedFiles({});
  };

  const selectAndScroll = (path: string) => {
    setSelectedPath(path);
    if (viewMode === "stream") {
      setCollapsedFiles((prev) => ({ ...prev, [path]: false }));
      const target = document.getElementById(`diff-file-${encodeURIComponent(path)}`);
      target?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const renderTree = (nodes: FileTreeNode[]) => {
    return nodes.map((node) => {
      if (node.kind === "dir") {
        const isCollapsed = Boolean(collapsedDirs[node.fullPath]);
        return (
          <div key={node.fullPath} className="tree-dir-node">
            <button
              className="tree-dir-head"
              onClick={() => setCollapsedDirs((prev) => ({ ...prev, [node.fullPath]: !prev[node.fullPath] }))}
            >
              {isCollapsed ? <Folder size={14} style={{ color: "#54aeff" }} /> : <FolderOpen size={14} style={{ color: "#54aeff" }} />}
              <span>{node.name}</span>
              <small style={{ color: "#656d76", marginLeft: "auto", fontSize: 11 }}>({node.fileCount})</small>
            </button>
            {!isCollapsed && (
              <div style={{ paddingLeft: 12 }}>
                {renderTree(node.children)}
              </div>
            )}
          </div>
        );
      }
      const f = node.file;
      const isSelected = selectedPath === f.path;
      const isViewed = Boolean(viewedFiles[f.path]);
      return (
        <button
          key={f.path}
          className={`tree-file-node ${isSelected ? "active" : ""}`}
          onClick={() => selectAndScroll(f.path)}
          title={f.path}
        >
          <FileCode2 size={13} className="tree-file-icon" />
          <span className="tree-file-name">{node.name}</span>
          {isViewed ? (
            <span className="tree-file-viewed" title="已审阅">✓</span>
          ) : (
            <span className="tree-file-diffstat">
              <span className="plus">+{f.additions}</span> <span className="minus">−{f.deletions}</span>
            </span>
          )}
        </button>
      );
    });
  };

  const filesToRender = viewMode === "single"
    ? report.files.filter((f) => f.path === selectedPath)
    : filteredFiles;

  return (
    <div className="gh-code-workspace">
      {/* ================= Left Sticky Directory Tree ================= */}
      <aside className="gh-file-tree-panel">
        <div className="gh-file-tree-header">
          <strong>变更文件</strong>
          <small>{filteredFiles.length} / {totalCount} 个文件</small>
        </div>
        <div className="gh-file-tree-search">
          <div className="gh-search-input-box">
            <Search size={13} style={{ color: "#656d76" }} />
            <input
              value={fileSearch}
              onChange={(e) => setFileSearch(e.target.value)}
              placeholder="按路径过滤文件..."
            />
            {fileSearch && <button onClick={() => setFileSearch("")} style={{ border: 0, background: "none" }}><X size={12} /></button>}
          </div>
        </div>
        <div className="gh-tree-scroll">
          {treeNodes.length > 0 ? renderTree(treeNodes) : <div className="empty-state">无匹配文件</div>}
        </div>
      </aside>

      {/* ================= Right Multi-File Diff Stream ================= */}
      <section className="gh-diff-stream" aria-label="代码差异审查">
        {/* Progress & Controls Bar */}
        <div className="gh-diff-controls">
          <div className="gh-diff-progress">
            <span>已审阅 {viewedCount} / {totalCount} 个文件</span>
            <div style={{ width: 100, height: 6, background: "#d0d7de", borderRadius: 3, overflow: "hidden" }}>
              <div style={{ width: `${(viewedCount / Math.max(1, totalCount)) * 100}%`, height: "100%", background: "#1f883d" }} />
            </div>
          </div>
          <div className="gh-diff-view-modes">
            <button className="secondary-button" onClick={expandAll} style={{ padding: "0 8px", fontSize: 12 }}>全部展开</button>
            <button className="secondary-button" onClick={collapseAll} style={{ padding: "0 8px", fontSize: 12 }}>全部折叠</button>
            <span style={{ color: "#d0d7de" }}>|</span>
            <button
              className={`secondary-button ${viewMode === "stream" ? "primary-button" : ""}`}
              onClick={() => setViewMode("stream")}
              style={{ padding: "0 8px", fontSize: 12 }}
            >
              连续显示全部
            </button>
            <button
              className={`secondary-button ${viewMode === "single" ? "primary-button" : ""}`}
              onClick={() => setViewMode("single")}
              style={{ padding: "0 8px", fontSize: 12 }}
            >
              单文件聚焦
            </button>
          </div>
        </div>

        {/* Files Stream */}
        {filesToRender.map((f) => {
          const isCollapsed = Boolean(collapsedFiles[f.path]);
          const isViewed = Boolean(viewedFiles[f.path]);
          return (
            <article
              key={f.path}
              id={`diff-file-${encodeURIComponent(f.path)}`}
              className="gh-diff-file-card"
            >
              {/* Card Header (Sticky) */}
              <header className="gh-file-card-header">
                <div className="gh-file-card-left">
                  <button
                    className="gh-collapse-toggle"
                    onClick={() => toggleCollapse(f.path)}
                    title={isCollapsed ? "展开文件" : "折叠文件"}
                  >
                    {isCollapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
                  </button>
                  <div className="gh-file-path-title">
                    {f.old_path && f.new_path && f.old_path !== f.new_path ? (
                      <><span>{f.old_path}</span> → <strong>{f.new_path}</strong></>
                    ) : (
                      <strong>{f.path}</strong>
                    )}
                  </div>
                  <div className="gh-file-tags">
                    <span className={`role-badge role-${f.role}`}>{roleLabel(f.role)}</span>
                    <span className="status-badge">{fileStatusLabel(f.status)}</span>
                    {f.parse_status.head && (
                      <span className={`ast-badge ${f.parse_status.head === "ok" ? "ast-ok" : "ast-degraded"}`}>
                        AST {f.parse_status.head === "ok" ? "已解析" : "降级"}
                      </span>
                    )}
                  </div>
                </div>

                <div className="gh-file-card-right">
                  <div className="diffstat-block">
                    <span className="plus">+{f.additions}</span>
                    <span className="minus">−{f.deletions}</span>
                  </div>
                  <label className="viewed-checkbox-label">
                    <input
                      type="checkbox"
                      checked={isViewed}
                      onChange={() => toggleViewed(f.path)}
                    />
                    <span>已审阅</span>
                  </label>
                </div>
              </header>

              {/* Card Body */}
              {!isCollapsed && (
                <div>
                  {f.parse_errors.length > 0 && (
                    <div style={{ padding: "8px 14px", background: "#fff8c5", borderBottom: "1px solid #d4a72c", color: "#745c34", fontSize: 12 }}>
                      <AlertCircle size={14} style={{ display: "inline", verticalAlign: "middle", marginRight: 6 }} />
                      {f.parse_errors.map((e, idx) => (
                        <span key={idx}>{e.side ?? "版本"}：{e.message ?? "解析异常"}{e.line ? ` (${e.line}:${e.column ?? 0})` : ""} </span>
                      ))}
                    </div>
                  )}

                  {f.binary ? (
                    <div className="empty-state" style={{ padding: 24 }}>二进制文件差异暂不可直接预览。</div>
                  ) : f.hunks.length === 0 ? (
                    <div className="empty-state" style={{ padding: 24 }}>此文件无行级文本变动（可能是纯重命名或权限变更）。</div>
                  ) : (
                    <div className="gh-diff-table">
                      {f.hunks.map((hunk, hIdx) => (
                        <div key={`${hunk.old_start}-${hunk.new_start}-${hIdx}`}>
                          <div className="hunk-heading">
                            @@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@
                          </div>
                          {hunk.lines.map((line, lIdx) => (
                            <DiffRow
                              key={`${line.kind}-${line.old_line}-${line.new_line}-${lIdx}`}
                              line={line}
                              filePath={f.path}
                              highlighted={focusLines.some((num) => line.old_line === num || line.new_line === num)}
                            />
                          ))}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </article>
          );
        })}
        {filesToRender.length === 0 && (
          <div className="empty-state" style={{ background: "#fff", border: "1px solid #d0d7de", borderRadius: 6 }}>
            没有匹配的变更文件。
          </div>
        )}
      </section>
    </div>
  );
}

function DiffRow({ line, filePath, highlighted }: { line: DiffLine; filePath: string; highlighted: boolean }) {
  const prefix = line.kind === "add" ? "+" : line.kind === "delete" ? "−" : " ";
  return (
    <div
      className={`diff-row diff-${line.kind}${highlighted ? " diff-highlight" : ""}`}
      data-file-path={filePath}
      data-diff-old-line={line.old_line ?? undefined}
      data-diff-new-line={line.new_line ?? undefined}
    >
      <span className="line-number old-line-number">{line.old_line ?? ""}</span>
      <span className="line-number new-line-number">{line.new_line ?? ""}</span>
      <span className="diff-marker">{prefix}</span>
      <code>{line.text || " "}</code>
    </div>
  );
}

/* ==========================================================================
   Rules & Findings Tab Component
   ========================================================================== */
function catalogState(report: Report, ruleId: string) {
  if (!outcomesRecorded(report)) return { stateKey: "unavailable", className: "unavailable", label: "终态未记录", note: "历史快照没有这条规则的终态记录。" };
  const outcome = outcomeFor(report, ruleId);
  if (!outcome) return { stateKey: "disabled", className: "disabled", label: "未启用", note: "" };
  return {
    stateKey: outcome.state,
    className: outcome.state === "Hit" ? "hit" : outcome.state === "NotFound" ? "not-found" : "unanalyzed",
    label: outcomeLabels[outcome.state],
    note: outcomeNote(outcome),
  };
}

function RulesView({
  report, catalog, expandedRule, setExpandedRule, onLocate, onOpenRuleCard,
}: {
  report: Report; catalog: Rule[]; expandedRule: string | null; setExpandedRule: (key: string | null) => void;
  onLocate: (evidence: Evidence) => void;
  onOpenRuleCard: (ruleId: string) => void;
}) {
  const [stateFilter, setStateFilter] = useState<string>("all");
  const [ruleDomainFilter, setRuleDomainFilter] = useState<string>("all");
  const recorded = outcomesRecorded(report);
  const outcomes = recorded ? report.rule_outcomes ?? [] : [];
  const outcomeSummary = recorded
    ? `命中 ${outcomes.filter((item) => item.state === "Hit").length} · 未发现 ${outcomes.filter((item) => item.state === "NotFound").length} · 无法分析 ${outcomes.filter((item) => item.state === "Unanalyzed").length}`
    : "终态未记录";

  const allRules = catalog.length > 0 ? catalog : Object.keys(ruleLabels).map((id) => ({
    rule_id: id,
    severity: "Medium",
    trigger: "",
    evidence_type: "",
    applicable_scope: "",
    suggested_action: "",
    limitations: "",
    default_weight: 0,
    enabled_by_default: true,
  }));

  const filteredCatalog = allRules.filter((rule) => {
    if (ruleDomainFilter !== "all" && ruleDomain(rule.rule_id) !== ruleDomainFilter) return false;
    if (stateFilter === "all") return true;
    const state = catalogState(report, rule.rule_id);
    return state.stateKey === stateFilter;
  });

  return (
    <div className="rules-page">
      {/* Top: Findings List */}
      <section className="rules-section-card">
        <div className="rules-section-head">
          <div>
            <h2>本次分析命中线索 (Findings)</h2>
            <p>{report.findings.length} 条命中 · {outcomeSummary} · 展开可查阅证据节点并跳转至代码</p>
          </div>
          <span className="nav-tab-count" style={{ fontSize: 13, height: 24, minWidth: 24 }}>
            {report.findings.length}
          </span>
        </div>

        {report.summary.unanalyzed?.length ? (
          <div style={{ padding: "10px 18px", background: "#fff8c5", borderBottom: "1px solid #d4a72c", fontSize: 13, color: "#745c34" }}>
            <AlertCircle size={15} style={{ display: "inline", verticalAlign: "middle", marginRight: 6 }} />
            {report.summary.unanalyzed.length} 项变更存在分析缺口（未作为代码安全通过处理）：
            {report.summary.unanalyzed.map((item) => `${item.path || "本次变更"} (${reasonText(item.reason)})`).join("；")}
          </div>
        ) : null}

        {report.findings.length ? (
          <div>
            {report.findings.map((finding, index) => (
              <article className="matched-finding" key={`${finding.rule_id}-${index}`}>
                <button
                  className="matched-finding-head"
                  onClick={() => setExpandedRule(expandedRule === `${finding.rule_id}-${index}` ? null : `${finding.rule_id}-${index}`)}
                  aria-expanded={expandedRule === `${finding.rule_id}-${index}`}
                >
                  <span style={{ color: "#cf222e" }}>{domainIcon(ruleDomain(finding.rule_id))}</span>
                  <div className="matched-finding-title">
                    <strong>{ruleLabels[finding.rule_id] ?? finding.rule_id}</strong>
                    <span>{finding.message}</span>
                    <small>{finding.rule_id}</small>
                  </div>
                  <span className={`risk-pill ${finding.severity === "high" ? "risk-high" : finding.severity === "medium" ? "risk-medium" : "risk-low"}`}>
                    {severityLabel(finding.severity)}
                  </span>
                  <span style={{ color: "#59636e", fontSize: 12 }}>{finding.evidence.length} 证据</span>
                  {expandedRule === `${finding.rule_id}-${index}` ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </button>

                {expandedRule === `${finding.rule_id}-${index}` && (
                  <div className="matched-evidence-box">
                    <p><strong>复核建议：</strong>{finding.suggested_action}</p>
                    {finding.evidence.map((item, evIndex) => (
                      <div className="evidence-card" key={`${item.node_id}-${evIndex}`}>
                        <div>
                          <strong>{item.path}</strong>
                          <div><span>{item.node_kind} · {item.structural_change_type}</span> · <small>{item.qualified_name ?? item.node_id}</small></div>
                          {evidenceDetail(item) ? <small style={{ color: "#59636e" }}>{evidenceDetail(item)}</small> : null}
                          <code>{item.lines.map((line) => `L${line}`).join(", ") || "无 Diff 行号"}</code>
                        </div>
                        <button className="secondary-button" onClick={() => onLocate(item)} disabled={!item.lines.length}>
                          定位到代码 <ArrowUpRight size={13} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <CircleHelp size={22} />
            {findingAbsenceCopy(report)}
          </div>
        )}
      </section>

      {/* Bottom: 29 Rules Table */}
      <section className="rules-section-card">
        <div className="rules-section-head">
          <div>
            <h2>规则终态与完整目录表</h2>
            <p>已落地的 29 条规则触发条件与适用边界。终态按本次分析记录，未发现不是代码安全结论。</p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <select className="secondary-button" value={stateFilter} onChange={(e) => setStateFilter(e.target.value)}>
              <option value="all">全部终态</option>
              <option value="Hit">命中 (Hit)</option>
              <option value="NotFound">未发现 (NotFound)</option>
              <option value="Unanalyzed">无法分析 (Unanalyzed)</option>
              <option value="disabled">未启用</option>
            </select>
            <select className="secondary-button" value={ruleDomainFilter} onChange={(e) => setRuleDomainFilter(e.target.value)}>
              <option value="all">全部关注域</option>
              {Object.entries(domainLabels).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
            </select>
          </div>
        </div>

        <table className="rules-table">
          <thead>
            <tr>
              <th style={{ width: 40 }}></th>
              <th>规则名称 / ID</th>
              <th>关注域</th>
              <th>严重级别</th>
              <th>本次终态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {filteredCatalog.map((rule) => {
              const st = catalogState(report, rule.rule_id);
              return (
                <tr key={rule.rule_id}>
                  <td style={{ color: "#0969da" }}>{domainIcon(ruleDomain(rule.rule_id))}</td>
                  <td>
                    <strong style={{ display: "block", color: "#1f2328" }}>{ruleLabels[rule.rule_id] ?? rule.rule_id}</strong>
                    <code style={{ fontSize: 11, color: "#59636e" }}>{rule.rule_id}</code>
                    {st.note && <small style={{ display: "block", color: "#9a6700", marginTop: 2 }}>{st.note}</small>}
                  </td>
                  <td>{domainLabels[ruleDomain(rule.rule_id)] ?? ruleDomain(rule.rule_id)}</td>
                  <td>
                    <span className={`risk-pill ${rule.severity === "High" || rule.severity === "Critical" ? "risk-high" : rule.severity === "Medium" ? "risk-medium" : "risk-low"}`}>
                      {rule.severity}
                    </span>
                  </td>
                  <td>
                    <span className={`risk-pill ${st.className === "hit" ? "risk-high" : st.className === "unanalyzed" ? "risk-medium" : "risk-low"}`}>
                      {st.label}
                    </span>
                  </td>
                  <td>
                    <button className="secondary-button" style={{ padding: "0 8px", fontSize: 12 }} onClick={() => onOpenRuleCard(rule.rule_id)}>
                      查看卡片
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </div>
  );
}

/* ==========================================================================
   Scoring & Configuration Tab Component
   ========================================================================== */
function ScoringView({
  report, catalog, presets, config, setConfig, onSelectPreset, onWeight, onToggle, onApply, onReset, busy, baselineScore,
}: {
  report: Report; catalog: Rule[]; presets: PresetItem[]; config: Config; setConfig: React.Dispatch<React.SetStateAction<Config>>;
  onSelectPreset: (item: PresetItem) => void;
  onWeight: (ruleId: string, value: number) => void; onToggle: (ruleId: string) => void;
  onApply: () => void; onReset: () => void; busy: boolean; baselineScore: number | null;
}) {
  const gatekeeper = gatekeeperSummary(report);
  const deepDepth = config.rule_thresholds?.["code.deep_control_flow"]?.max_depth ?? 4;
  const secretLen = config.rule_thresholds?.["code.hardcoded_secret"]?.min_length ?? 8;

  const allRules = catalog.length > 0 ? catalog : Object.keys(ruleLabels).map((id) => ({
    rule_id: id,
    severity: "Medium",
    trigger: "",
    evidence_type: "",
    applicable_scope: "",
    suggested_action: "",
    limitations: "",
    default_weight: 0,
    enabled_by_default: true,
  }));

  return (
    <div className="scoring-page">
      <div className="scoring-summary-card">
        <div>
          <span>当前分析评分</span>
          <strong>{report.score}<small style={{ fontSize: 16 }}>/100</small></strong>
          <span className={`risk-pill ${riskClass(report.risk_level)}`} style={{ marginLeft: 8 }}>
            {riskLabel(report.risk_level)}
          </span>
        </div>
        <div>
          <span>计分依据（已得权重 / 可得权重）</span>
          <strong>{report.score_basis.earned_points} <small style={{ fontSize: 16 }}>/ {report.score_basis.maximum_points}</small></strong>
        </div>
        <div>
          <span>基线对比</span>
          <strong>{baselineScore ?? report.score}</strong>
          <small style={{ display: "block", color: "#59636e", marginTop: 4 }}>
            {report.config_snapshot ? `指纹 #${report.config_snapshot.config_digest.slice(0, 8)} · ${rerunTierLabel(report.snapshot_meta)}` : "基线得分"}
          </small>
        </div>
      </div>

      {gatekeeper && (
        <div className="gatekeeper-banner">
          <ShieldAlert size={20} style={{ flexShrink: 0 }} />
          <div><strong>{gatekeeper.text}</strong></div>
        </div>
      )}

      {/* Preset Cards */}
      <section>
        <div style={{ marginBottom: 12 }}>
          <h2 style={{ margin: "0 0 4px", fontSize: 16, fontWeight: 600 }}>审查场景预设 (Presets)</h2>
          <p style={{ margin: 0, color: "#59636e", fontSize: 13 }}>选择预设可快速载入 29 条规则的推荐权重与阈值组合，选定后可随时在下方微调。</p>
        </div>
        <div className="preset-grid">
          {presets.map((item) => (
            <button
              type="button"
              key={item.preset}
              className={`preset-card ${config.preset === item.preset ? "active" : ""}`}
              onClick={() => onSelectPreset(item)}
            >
              <div>
                <strong>{item.name}</strong>
                <code style={{ display: "block", marginTop: 2 }}>{item.preset}</code>
              </div>
              <p>{item.description}</p>
              <small>阈值 {item.thresholds.medium}/{item.thresholds.high} · 深度&gt;{item.rule_thresholds?.["code.deep_control_flow"]?.max_depth ?? 4} · 密钥≥{item.rule_thresholds?.["code.hardcoded_secret"]?.min_length ?? 8}</small>
            </button>
          ))}
        </div>
      </section>

      {/* Weights and Thresholds Layout */}
      <div className="scoring-layout">
        <section className="scoring-weights-card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h2 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>规则启用开关与启发式权重</h2>
              <p style={{ margin: "3px 0 0", color: "#59636e", fontSize: 13 }}>已启用 {config.enabled_rules.length} / {allRules.length} 条规则</p>
            </div>
            <button className="secondary-button" onClick={onReset} title="恢复基线">
              <RotateCcw size={14} /> 恢复默认
            </button>
          </div>

          <div className="weight-rule-list">
            {allRules.map((rule) => (
              <div className="weight-rule" key={rule.rule_id}>
                <label className="weight-rule-toggle">
                  <input
                    type="checkbox"
                    checked={config.enabled_rules.includes(rule.rule_id)}
                    onChange={() => onToggle(rule.rule_id)}
                  />
                  <div>
                    <strong>{ruleLabels[rule.rule_id] ?? rule.rule_id}</strong>
                    <small>{rule.rule_id}</small>
                  </div>
                </label>
                <div className="weight-slider">
                  <input
                    type="range"
                    min={0}
                    max={5}
                    step={1}
                    value={config.rule_weights[rule.rule_id] ?? rule.default_weight}
                    disabled={!config.enabled_rules.includes(rule.rule_id)}
                    onChange={(e) => onWeight(rule.rule_id, Number(e.target.value))}
                  />
                  <output>{config.rule_weights[rule.rule_id] ?? rule.default_weight}</output>
                </div>
              </div>
            ))}
          </div>
        </section>

        <aside className="threshold-panel">
          <h2 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>复核等级阈值</h2>
          <p style={{ margin: "4px 0 12px", color: "#59636e", fontSize: 12 }}>调整人工复核优先级划分分段</p>

          <label>
            建议复核 (medium)
            <input
              type="number"
              min={0}
              max={99}
              value={config.thresholds.medium}
              onChange={(e) => setConfig((c) => ({ ...c, thresholds: { ...c.thresholds, medium: Number(e.target.value) } }))}
            />
          </label>
          <label>
            优先复核 (high)
            <input
              type="number"
              min={1}
              max={100}
              value={config.thresholds.high}
              onChange={(e) => setConfig((c) => ({ ...c, thresholds: { ...c.thresholds, high: Number(e.target.value) } }))}
            />
          </label>

          <div style={{ height: 1, background: "#d0d7de", margin: "18px 0 14px" }} />

          <h2 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>规则内部判定阈值</h2>
          <p style={{ margin: "4px 0 12px", color: "#59636e", fontSize: 12 }}>修改将触发 Tier 1 局部重跑（复用 AST，重算规则）</p>

          <label>
            深层控制流深度 (2~10)
            <input
              type="number"
              min={2}
              max={10}
              value={deepDepth}
              onChange={(e) => {
                const val = Math.max(2, Math.min(10, Number(e.target.value) || 4));
                setConfig((c) => ({ ...c, rule_thresholds: { ...c.rule_thresholds, "code.deep_control_flow": { max_depth: val } } }));
              }}
            />
          </label>

          <label>
            敏感字面量长度 (4~32)
            <input
              type="number"
              min={4}
              max={32}
              value={secretLen}
              onChange={(e) => {
                const val = Math.max(4, Math.min(32, Number(e.target.value) || 8));
                setConfig((c) => ({ ...c, rule_thresholds: { ...c.rule_thresholds, "code.hardcoded_secret": { min_length: val } } }));
              }}
            />
          </label>

          <button
            className="primary-button"
            onClick={onApply}
            disabled={busy}
            style={{ width: "100%", marginTop: 18 }}
          >
            {busy ? <LoaderCircle size={15} className="spin" /> : <Settings2 size={15} />}
            应用并重算当前分析
          </button>
        </aside>
      </div>
    </div>
  );
}

function fileStatusLabel(status: string) {
  if (status === "added") return "新增";
  if (status === "deleted") return "删除";
  if (status === "renamed") return "重命名";
  return "修改";
}
function severityLabel(value: string) { return value === "high" || value === "Critical" ? "高" : value === "medium" || value === "Medium" ? "中" : "低"; }

function renderMarkdown(report: Report) {
  const snap = report.config_snapshot;
  const cfg = configFromReport(report);
  const enabledRules = snap?.enabled_rules ?? cfg.enabled_rules;
  const allKnownRules = Object.keys(ruleLabels);
  const disabledRules = snap?.disabled_rules ?? allKnownRules.filter((id) => !enabledRules.includes(id));
  const deepDepth = (snap?.rule_thresholds ?? cfg.rule_thresholds)?.["code.deep_control_flow"]?.max_depth ?? 4;
  const secretLen = (snap?.rule_thresholds ?? cfg.rule_thresholds)?.["code.hardcoded_secret"]?.min_length ?? 8;
  const gatekeeper = gatekeeperSummary(report);
  const recorded = outcomesRecorded(report);
  const outcomeByRule = new Map((report.rule_outcomes ?? []).map((o) => [o.rule_id, o]));

  const reproPayload = {
    preset: snap?.preset ?? cfg.preset ?? "legacy_baseline",
    config_digest: snap?.config_digest ?? "",
    enabled_rules: enabledRules,
    rule_weights: snap?.rule_weights ?? cfg.rule_weights,
    test_collaboration_enabled: snap?.test_collaboration_enabled ?? cfg.test_collaboration_enabled,
    test_collaboration_weight: snap?.test_collaboration_weight ?? cfg.test_collaboration_weight,
    thresholds: snap?.thresholds ?? cfg.thresholds,
    rule_thresholds: {
      "code.deep_control_flow": { max_depth: deepDepth },
      "code.hardcoded_secret": { min_length: secretLen },
    },
  };

  return [
    `# ${report.pr_number ? `PR #${report.pr_number}` : `${report.base_ref} → ${report.head_ref}`} 代码变更复核`,
    "",
    `- 标题：${report.title}`,
    `- 仓库：${report.repo ?? "未知"}`,
    `- 作者：${report.author ?? "未知"}`,
    `- 提交快照：base \`${shortSha(report.base_sha)}\` → head \`${shortSha(report.head_sha)}\``,
    `- 复核优先级：${report.score}/100（${riskLabel(report.risk_level)}，不是缺陷概率）`,
    `- 计分依据：${report.score_basis.earned_points} / ${report.score_basis.maximum_points}（已得权重 / 可得权重）`,
    `- 一票抬升（Gatekeeper）：${gatekeeper ? `已触发（强制抬升为优先复核，触发规则：${gatekeeper.rules.join(", ")}）` : "未触发"}`,
    `- 变更规模：${report.summary.files_changed} 个文件，+${report.summary.additions} / -${report.summary.deletions}`,
    ...(report.snapshot_meta ? [`- 执行层级：\`${report.snapshot_meta.rerun_tier}\`（cache_hit=${report.snapshot_meta.cache_hit}）`] : []),
    "",
    "## 运行配置快照（可复现封存）",
    "",
    `- 配置 Schema：\`${snap?.schema_version ?? "config.snapshot.v1"}\``,
    `- 配置指纹（SHA-256）：\`${snap?.config_digest ?? "local"}\``,
    `- 场景预设：\`${snap?.preset ?? cfg.preset ?? "legacy_baseline"}\`（${snap?.preset_name ?? "自定义/基线"}，自定义覆盖：\`${Boolean(snap?.customized)}\`）`,
    `- 等级分段阈值：建议复核 \`medium >= ${cfg.thresholds.medium}\`，优先复核 \`high >= ${cfg.thresholds.high}\``,
    `- 规则内部判定阈值：\`code.deep_control_flow.max_depth = ${deepDepth}\`，\`code.hardcoded_secret.min_length = ${secretLen}\``,
    `- 测试协同配置：\`enabled = ${cfg.test_collaboration_enabled}\`，\`weight = ${cfg.test_collaboration_weight}\``,
    `- 启用规则数：${enabledRules.length} / ${allKnownRules.length}`,
    `- 已禁用规则：${disabledRules.length ? disabledRules.map((r) => `\`${r}\``).join(", ") : "无（全部 29 条规则均已启用）"}`,
    "",
    "### 启用规则与权重明细",
    "",
    "| 规则 ID | 规则名称 | 启发式权重 | 本次终态 |",
    "| :--- | :--- | :---: | :--- |",
    ...enabledRules.map((ruleId) => {
      const weight = (snap?.rule_weights ?? cfg.rule_weights)[ruleId] ?? 0;
      const outcome = outcomeByRule.get(ruleId);
      const stateText = recorded && outcome ? outcomeLabels[outcome.state] : "终态未记录";
      return `| \`${ruleId}\` | ${ruleLabels[ruleId] ?? ruleId} | ${weight} | ${stateText} |`;
    }),
    "",
    "### 可复现配置载荷",
    "",
    "```json",
    JSON.stringify(reproPayload, null, 2),
    "```",
    "",
    "## 规则终态",
    recorded
      ? (report.rule_outcomes ?? []).flatMap((outcome) => [
        `- ${outcome.rule_id}：${outcomeLabels[outcome.state]}${outcomeNote(outcome) ? `。${outcomeNote(outcome)}` : ""}`,
      ]).concat(["", "未发现不是安全结论。无法分析不是通过。"])
      : ["- 这次结果没有规则终态记录。没有 Finding 不能解释为未发现或已通过。"],
    "",
    "## 规则线索",
    ...report.findings.flatMap((finding) => [
      "", `### ${finding.rule_id}`, `- ${finding.message}`, `- 复核建议：${finding.suggested_action}`,
      ...finding.evidence.map((item) => `- ${item.path}:${item.lines.join(",")} · ${item.node_kind} · ${item.structural_change_type} · ${item.qualified_name ?? item.node_id}${evidenceDetail(item) ? ` · ${evidenceDetail(item)}` : ""}`),
    ]),
    "",
    "## 说明",
    ...report.limitations.map((item) => `- ${item}`),
  ].join("\n");
}
