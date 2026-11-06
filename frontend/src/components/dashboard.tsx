"use client";

import {
  AlertCircle, ArrowDown, ArrowDownRight, ArrowUpRight, Check, ChevronDown,
  ChevronRight, CircleHelp, Code2, Download, FileCode2, FileText, Filter,
  GitPullRequest, ListFilter, LoaderCircle, LockKeyhole, Network, RotateCcw,
  Search, Settings2, ShieldAlert, SlidersHorizontal, X,
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
  used_as_with_context?: boolean; nesting_depth?: number; control_kind?: string;
  binding_name?: string; binding_form?: string; value_length?: number; value_preview?: string;
  mutable_state_form?: string; binding_targets?: string[];
  path_class?: string; additions?: number; deletions?: number; content_change?: string;
};
type Finding = {
  rule_id: string; severity: string; message: string;
  suggested_action: string; evidence: Evidence[];
};
type DiffLine = { kind: "context" | "add" | "delete"; old_line: number | null; new_line: number | null; text: string };
type Hunk = { old_start: number; old_count: number; new_start: number; new_count: number; lines: DiffLine[] };
type DiffFile = {
  path: string; old_path?: string; new_path?: string; role: string; status: string;
  is_python: boolean; binary: boolean; additions: number; deletions: number;
  hunks: Hunk[]; parse_status: Record<string, string>; parse_errors: { side?: string; message?: string; line?: number; column?: number }[];
};
type Config = {
  enabled_rules: string[]; rule_weights: Record<string, number>;
  test_collaboration_weight: number; test_collaboration_enabled: boolean;
  thresholds: { medium: number; high: number };
};
type Report = {
  status: string; repo: string; pr_number?: number; title: string; author?: string; url?: string;
  project?: Project; base_ref?: string; head_ref?: string; merge_base_sha?: string; diff_mode?: string;
  base_sha?: string; head_sha?: string; score: number; risk_level: string;
  score_basis: { earned_points: number; maximum_points: number; matched_rule_ids: string[]; test_collaboration: boolean; configuration: Config };
  summary: {
    finding_count: number; domains?: string[]; files_changed: number; business_files: number;
    test_files: number; additions: number; deletions: number; business_changed: boolean;
    test_changed: boolean; test_cochanged: boolean; test_collaboration_gap: boolean; parse_degraded: boolean;
    unanalyzed?: { path: string; reason: string }[];
  };
  files: DiffFile[]; findings: Finding[]; limitations: string[];
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
  "workflow.test_collaboration_gap": "生产代码变更未见测试路径变更",
};
const initialConfig: Config = {
  enabled_rules: Object.keys(ruleLabels),
  rule_weights: {
    "api.signature_changed": 2, "auth.permission_structure_changed": 3, "data.transaction_structure_changed": 2,
    "config.configuration_structure_changed": 1, "code.exception_structure_changed": 1,
    "code.swallowed_exception": 0, "code.bare_exception": 0, "code.dynamic_execution": 0,
    "code.unmanaged_open": 0, "code.deep_control_flow": 0,
    "code.hardcoded_secret": 0, "code.global_mutable_state": 0,
    "workflow.test_collaboration_gap": 1,
  },
  test_collaboration_weight: 1, test_collaboration_enabled: true, thresholds: { medium: 30, high: 65 },
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
  if (typeof item.nesting_depth === "number") return `嵌套深度 ${item.nesting_depth}`;
  if (item.binding_name) return `绑定 ${item.binding_name}，长度 ${item.value_length}`;
  if (item.mutable_state_form === "global_statement") return `global ${(item.binding_targets || []).join("、")}`;
  if (item.mutable_state_form === "mutable_binding") return `可变绑定 ${(item.binding_targets || []).join("、")}`;
  if (item.path_class === "production" && typeof item.additions === "number" && typeof item.deletions === "number") {
    return `生产代码 +${item.additions} / -${item.deletions}`;
  }
  if (item.used_as_with_context === false) return "直接 open 未作为 with 上下文";
  if (item.callee_name) return `直接调用 ${item.callee_name}`;
  if (item.handler_body_is_single_pass) return "处理体只有 pass";
  return "";
}
function configFromReport(report: Report): Config { return report.score_basis.configuration; }

export function Dashboard() {
  const [dataset, setDataset] = useState<Dataset | null>(null);
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

  const analyzeBranch = useCallback(async (loaded: Project, base: string, head: string, nextConfig?: Config) => {
    setBusy(true); setError(""); setAnalysisMode("project");
    try {
      const response = await fetch("/api/branch-analysis", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ project_id: loaded.project_id, base_ref: base, head_ref: head, config: nextConfig }) });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error?.message || payload.error || "分支分析失败");
      setProject(loaded); setBaseRef(base); setHeadRef(head); setReport({ ...payload, title: `${base} → ${head}`, repo: loaded.name, author: "本地 Git 分支", url: undefined, pr_number: undefined } as Report);
      setConfig(nextConfig ?? initialConfig); if (!nextConfig) setBaselineScore((payload as Report).score); setSelectedPath(((payload as Report).files.find((file) => file.role === "business" && file.hunks.length > 0) ?? (payload as Report).files.find((file) => file.hunks.length > 0) ?? (payload as Report).files[0])?.path ?? "");
      const query = new URLSearchParams(window.location.search); query.delete("pr"); query.set("project", loaded.project_id); query.set("base", base); query.set("head", head); query.set("tab", activeTab); window.history.pushState(null, "", `${window.location.pathname}?${query.toString()}`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "分支分析失败"); }
    finally { setBusy(false); }
  }, [activeTab]);

  const runAnalysis = useCallback(async () => {
    if (analysisMode === "project" && project) {
      await analyzeBranch(project, baseRef, headRef, config);
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
      setReport(payload as Report);
      setNotice("当前 PR 已按新配置重算");
      window.setTimeout(() => setNotice(""), 1800);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "重算失败");
    } finally {
      setBusy(false);
    }
  }, [activePr, analysisMode, project, baseRef, headRef, config, analyzeBranch]);

  useEffect(() => {
    let cancelled = false;
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

  const selectedFile = report?.files.find((file) => file.path === selectedPath) ?? null;
  const matchedRuleIds = new Set(report?.findings.map((finding) => finding.rule_id) ?? []);
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
    openTab("code");
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

  if (analysisMode === "project" && !report) {
    return <ProjectPicker
      path={projectPath} setPath={setProjectPath} project={project} baseRef={baseRef} setBaseRef={setBaseRef}
      headRef={headRef} setHeadRef={setHeadRef} busy={projectBusy || busy} error={error}
      onLoad={(path) => void loadProject(path)} onAnalyze={() => project && void analyzeBranch(project, baseRef, headRef)}
      onSample={() => { setProject(null); void loadPr(226, "overview"); }}
      recentProjects={recentProjects}
    />;
  }

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

  return (
    <div className="review-shell">
      <aside className="review-sidebar">
        <div className="review-brand"><span className="brand-mark"><Code2 size={18} /></span><strong>prisk<span>.</span></strong><span className="brand-tag">REVIEW</span></div>
        <button className="repo-context repo-context-button" onClick={() => { setReport(null); setAnalysisMode("project"); }}><span className="repo-avatar">{(report?.repo ?? "P").slice(0, 1).toUpperCase()}</span><span><strong>{report?.repo ?? "选择项目"}</strong><small>{project?.path ?? (analysisMode === "sample" ? "冻结 NetBox 样本" : "加载本地 Git 仓库")}</small></span></button>
        <div className="sidebar-caption">当前分析</div>
          <button className="current-pr-button" onClick={() => analysisMode === "sample" ? setDrawerOpen(true) : (setReport(null), setAnalysisMode("project"))} disabled={!dataset}>
          <GitPullRequest size={16} /><span><small>{analysisMode === "sample" ? "Pull Request" : "分支分析"}</small><strong>{report ? (report.pr_number ? `#${report.pr_number}` : `${report.base_ref} → ${report.head_ref}`) : "选择项目"}</strong></span><ChevronDown size={15} />
        </button>
        <div className="sidebar-status"><span className="status-dot" />本地冻结样本</div>
        <div className="sidebar-footer">PRISK SYSTEM <span>06 · 07</span></div>
      </aside>

      <main className="review-main">
        <header className="review-topbar">
            <div className="breadcrumbs">{report?.repo ?? "Prisk"} <ChevronRight size={13} /> {analysisMode === "sample" ? "冻结 PR 样本" : "分支审计"}</div>
          <div className="top-actions"><span className="sample-badge"><span className="status-dot" />离线样本</span>
            <button className="icon-button" title="下载 JSON 报告" onClick={() => downloadReport("json")} disabled={!report}><Download size={16} /></button>
          </div>
        </header>

        <div className="review-content">
          <div className="pr-heading">
            <div className="pr-heading-main">
              <div className="eyebrow">{analysisMode === "sample" ? "PULL REQUEST REVIEW" : "BRANCH REVIEW"} <span>·</span> {report?.repo ?? "本地项目"}</div>
              <div className="pr-title-line"><h1>{report ? (report.pr_number ? `#${report.pr_number} ${report.title}` : `${report.base_ref} → ${report.head_ref}`) : "载入分析"}</h1>
                {report && <span className={`risk-pill ${riskClass(report.risk_level)}`}>{riskLabel(report.risk_level)}</span>}
              </div>
              <p>{report ? <>{analysisMode === "sample" ? report.author ?? "NetBox contributor" : project?.path} <span className="muted-divider">·</span> base {analysisMode === "project" ? report.base_ref : ""} <code>{shortSha(report.base_sha)}</code> <ArrowDown size={12} /> head {analysisMode === "project" ? report.head_ref : ""} <code>{shortSha(report.head_sha)}</code></> : "正在读取分析对象"}</p>
            </div>
            <div className="pr-heading-actions">
              {analysisMode === "sample" ? <button className="secondary-button" onClick={() => setDrawerOpen(true)} disabled={!dataset}><ListFilter size={15} />切换 PR</button> : <button className="secondary-button" onClick={() => { setReport(null); setAnalysisMode("project"); }}><ListFilter size={15} />更换项目</button>}
              {report?.url && <a className="icon-button source-link" href={report.url} target="_blank" rel="noreferrer" title="查看原始 PR"><ArrowUpRight size={16} /></a>}
            </div>
          </div>

          {error && <div className="error-banner"><AlertCircle size={17} />{error}</div>}
          {notice && <div className="toast"><Check size={15} />{notice}</div>}

          <nav className="review-tabs" aria-label="PR 审计视图">
            {tabs.map(({ id, label, icon: Icon }) => <button key={id} className={activeTab === id ? "review-tab active" : "review-tab"} onClick={() => openTab(id)}>
              <Icon size={16} />{label}{id === "rules" && report && <span className="tab-count">{report.findings.length}</span>}
            </button>)}
            <div className="tab-spacer" />
            <button className="export-text" onClick={() => downloadReport("md")} disabled={!report}><FileText size={15} />导出复核摘要</button>
          </nav>

          {!report ? <div className="loading-panel"><LoaderCircle className="spin" size={24} />{busy ? "正在载入 PR 分析对象…" : "等待选择 PR"}</div> : <>
            {activeTab === "overview" && <Overview report={report} baselineScore={baselineScore} onShowRules={() => openTab("rules")} onShowCode={() => openTab("code")} onLocate={locateEvidence} />}
            {activeTab === "code" && <CodeReview report={report} file={selectedFile} selectedPath={selectedPath} setSelectedPath={(path) => { setSelectedPath(path); setFocusLines([]); }} focusLines={focusLines} />}
            {activeTab === "rules" && <RulesView report={report} catalog={dataset?.rules ?? []} expandedRule={expandedRule} setExpandedRule={setExpandedRule} onLocate={locateEvidence} matchedRuleIds={matchedRuleIds} />}
            {activeTab === "scoring" && <ScoringView report={report} catalog={dataset?.rules ?? []} config={config} setConfig={setConfig} onWeight={updateRuleWeight} onToggle={toggleRule} onApply={() => void runAnalysis()} onReset={resetConfig} busy={busy} baselineScore={baselineScore} />}
          </>}
          <footer className="review-footer"><span><span className="status-dot" />本地分析结果</span><span>{analysisMode === "project" ? "stage03.v1 · stage04.v1 · stage05.v1 · stage08.branch-report.v1" : "stage03.v1 · stage04.v1 · stage05.v1 · stage07.report.v1"}</span><span>评分表示复核优先级，不是缺陷概率</span></footer>
        </div>
      </main>

      {drawerOpen && <div className="drawer-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setDrawerOpen(false); }}>
        <section className="pr-drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
          <header className="drawer-header"><div><span className="eyebrow">FROZEN SAMPLE</span><h2 id="drawer-title">选择 Pull Request</h2><p>{dataset?.counts.analyzable ?? 0} 条可分析 PR</p></div><button className="icon-button" title="关闭" onClick={() => setDrawerOpen(false)}><X size={18} /></button></header>
          <div className="drawer-controls"><label className="search-box"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索编号、标题或作者" /></label>
            <div className="drawer-filters"><label><Filter size={14} /><select aria-label="风险等级" value={riskFilter} onChange={(event) => setRiskFilter(event.target.value)}><option value="all">全部等级</option><option value="high">优先复核</option><option value="medium">建议复核</option><option value="low">常规</option></select></label>
              <label><ListFilter size={14} /><select aria-label="关注域" value={domainFilter} onChange={(event) => setDomainFilter(event.target.value)}><option value="all">全部关注域</option>{Object.entries(domainLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label></div>
          </div>
          <div className="drawer-pr-list">{filteredPrs.map((item) => <button key={item.pr_number} className={`drawer-pr ${item.pr_number === activePr ? "selected" : ""}`} onClick={() => choosePr(item)}>
            <span className="drawer-pr-main"><span className="pr-number">#{item.pr_number}</span><strong>{item.title}</strong><small>{item.author ?? "NetBox contributor"}</small></span>
            <span className="drawer-pr-side"><span className={`risk-pill ${riskClass(item.risk_level)}`}>{riskLabel(item.risk_level)}</span><small>{item.finding_count} 条命中</small></span>
          </button>)}{filteredPrs.length === 0 && <div className="empty-list">没有符合条件的 PR</div>}</div>
          <div className="drawer-footer">本次分析只针对当前选中的一个 PR</div>
        </section>
      </div>}
    </div>
  );
}

function ProjectPicker({ path, setPath, project, baseRef, setBaseRef, headRef, setHeadRef, busy, error, onLoad, onAnalyze, onSample, recentProjects }: {
  path: string; setPath: (value: string) => void; project: Project | null; baseRef: string; setBaseRef: (value: string) => void;
  headRef: string; setHeadRef: (value: string) => void; busy: boolean; error: string; onLoad: (path: string) => void;
  onAnalyze: () => void; onSample: () => void; recentProjects: RecentProject[];
}) {
  const branches = project?.branches ?? [];
  return <main className="project-picker-shell">
    <header className="picker-topbar"><span className="brand-mark"><Code2 size={18} /></span><strong>prisk<span>.</span></strong><span>本地代码审计</span></header>
    <section className="project-picker-content">
      <div className="eyebrow">LOCAL PROJECT WORKSPACE</div><h1>选择一个 Git 项目</h1><p className="picker-intro">加载仓库后选择基准分支和目标分支，生成一次可追溯的分支审计。</p>
      <form className="project-load-form" onSubmit={(event) => { event.preventDefault(); onLoad(path); }}>
        <label htmlFor="repo-path">本地仓库路径</label><div className="project-path-row"><input id="repo-path" value={path} onChange={(event) => setPath(event.target.value)} placeholder="例如 D:\\work\\my-project" /><button className="primary-button" disabled={busy || !path.trim()}>{busy ? <LoaderCircle size={15} className="spin" /> : <Search size={15} />}加载项目</button></div>
        {recentProjects.length > 0 && <div className="recent-project-list"><span>最近项目</span>{recentProjects.map((recent) => <button type="button" className="recent-project" key={recent.path} onClick={() => { setPath(recent.path); onLoad(recent.path); }}><RotateCcw size={14} /><strong>{recent.name}</strong><code>{recent.path}</code></button>)}</div>}
      </form>
      {error && <div className="error-banner"><AlertCircle size={16} />{error}</div>}
      {project && <section className="loaded-project"><div className="loaded-project-heading"><span className="repo-avatar">{project.name.slice(0, 1).toUpperCase()}</span><div><h2>{project.name}</h2><p>{project.path}</p><small>{project.branches.length} 个分支 · 当前 {project.current_branch || "分离 HEAD"} · HEAD {shortSha(project.current_head)}</small></div></div>
        <div className="branch-selectors"><label>基准分支<select value={baseRef} onChange={(event) => setBaseRef(event.target.value)}>{branches.map((branch) => <option key={branch.ref} value={branch.ref}>{branch.ref} · {branch.short_sha}</option>)}</select></label><ArrowDownRight size={17} /><label>目标分支<select value={headRef} onChange={(event) => setHeadRef(event.target.value)}>{branches.map((branch) => <option key={branch.ref} value={branch.ref}>{branch.ref} · {branch.short_sha}</option>)}</select></label></div>
        <div className="branch-list"><div className="branch-list-title">仓库分支</div>{branches.map((branch) => <div className="branch-row" key={branch.ref}><span className={`branch-kind ${branch.kind}`}>{branch.kind === "local" ? "本地" : "远程"}</span><strong>{branch.ref}</strong><code>{branch.short_sha}</code><span>{branch.subject}</span></div>)}</div>
        <div className="project-actions"><small>只读取已提交分支，不切换分支，也不包含未提交改动。</small><button className="primary-button" onClick={onAnalyze} disabled={busy || !baseRef || !headRef || baseRef === headRef}>{busy ? <LoaderCircle size={15} className="spin" /> : <GitPullRequest size={15} />}开始分析</button></div>
      </section>}
      <div className="sample-entry"><div><strong>没有本地仓库？</strong><span>可以加载冻结 NetBox PR 样本，查看现有分析结果。</span></div><button className="secondary-button" onClick={onSample}><FileText size={15} />加载冻结 NetBox 样本</button></div>
      <footer className="picker-boundary">分析采用 base...head 三点 Diff · 分数只表示人工复核优先级</footer>
    </section>
  </main>;
}

function Overview({ report, baselineScore, onShowRules, onShowCode, onLocate }: {
  report: Report; baselineScore: number | null; onShowRules: () => void; onShowCode: () => void; onLocate: (evidence: Evidence) => void;
}) {
  const topFindings = report.findings.slice(0, 3);
  return <div className="tab-page overview-page">
    <div className="overview-summary">
      <div className="score-summary"><span>当前复核优先级</span><strong>{report.score}<small>/100</small></strong><span className={`risk-pill ${riskClass(report.risk_level)}`}>{riskLabel(report.risk_level)}</span><small>基线 {baselineScore ?? report.score} · 阈值 {report.score_basis.configuration.thresholds.medium}/{report.score_basis.configuration.thresholds.high}</small></div>
      <div className="summary-details">
        <div className="summary-stat"><span>变更文件</span><strong>{report.summary.files_changed}</strong></div><div className="summary-stat"><span>新增行</span><strong className="plus">+{report.summary.additions}</strong></div><div className="summary-stat"><span>删除行</span><strong className="minus">−{report.summary.deletions}</strong></div><div className="summary-stat"><span>业务 / 测试文件</span><strong>{report.summary.business_files} / {report.summary.test_files}</strong></div>
        <div className="summary-stat"><span>规则命中</span><strong>{report.findings.length}</strong></div><div className="summary-stat"><span>命中关注域</span><strong className="scene-stat">{(report.summary.domains ?? []).map((domain) => domainLabels[domain] ?? domain).join("、") || "无"}</strong></div>
      </div>
    </div>
    <div className={`collab-banner ${report.summary.test_cochanged ? "success" : "attention"}`}><span className="collab-icon">{report.summary.test_cochanged ? <Check size={16} /> : <AlertCircle size={16} />}</span><span>{report.summary.test_cochanged ? "业务代码与测试文件有协同变更" : report.summary.business_changed ? "有业务代码变更，但没有测试文件协同" : "本次变更未涉及业务代码"}</span><small>辅助复核信号，不单独构成风险判断</small></div>
    <div className="overview-columns">
      <section className="overview-section"><div className="section-heading"><div><h2>重点风险线索</h2><p>当前分析命中的结构规则</p></div><button className="text-action" onClick={onShowRules}>查看全部 <ChevronRight size={14} /></button></div>
        {topFindings.length ? <div className="overview-finding-list">{topFindings.map((finding, index) => <button className="overview-finding" key={`${finding.rule_id}-${index}`} onClick={() => finding.evidence[0] && onLocate(finding.evidence[0])}>
          <span className={`finding-symbol domain-${ruleDomain(finding.rule_id)}`}>{domainIcon(ruleDomain(finding.rule_id))}</span><span className="overview-finding-main"><strong>{ruleLabels[finding.rule_id] ?? finding.rule_id}</strong><small>{finding.evidence.length} 条证据 · {finding.evidence[0]?.path}</small></span><ArrowUpRight size={15} />
        </button>)}</div> : <div className="empty-state compact"><Check size={17} />当前已启用规则均未命中，仍可检查全部代码变更。</div>}
      </section>
      <section className="overview-section change-overview"><div className="section-heading"><div><h2>变更范围</h2><p>{report.diff_mode === "three_dot" ? "来自 base...head 三点 Diff" : "来自冻结 PR 三点 Diff"}</p></div><button className="text-action" onClick={onShowCode}>审查代码 <ChevronRight size={14} /></button></div>
        <div className="file-role-summary"><span><FileCode2 size={16} />业务文件<strong>{report.summary.business_files}</strong></span><span><FileCode2 size={16} />测试文件<strong>{report.summary.test_files}</strong></span><span><FileText size={16} />其他文件<strong>{Math.max(0, report.summary.files_changed - report.summary.business_files - report.summary.test_files)}</strong></span></div>
        <div className="sha-summary"><span>BASE {report.base_ref && <b>{report.base_ref}</b>} <code>{shortSha(report.base_sha)}</code></span><ArrowDownRight size={15} /><span>HEAD {report.head_ref && <b>{report.head_ref}</b>} <code>{shortSha(report.head_sha)}</code></span>{report.merge_base_sha && <span>MERGE BASE <code>{shortSha(report.merge_base_sha)}</code></span>}</div>
      </section>
    </div>
  </div>;
}

function CodeReview({ report, file, selectedPath, setSelectedPath, focusLines }: {
  report: Report; file: DiffFile | null; selectedPath: string; setSelectedPath: (path: string) => void; focusLines: number[];
}) {
  const [fileSearch, setFileSearch] = useState("");
  const files = report.files.filter((item) => item.path.toLowerCase().includes(fileSearch.toLowerCase()));
  return <div className="code-workspace">
    <aside className="diff-file-panel"><div className="diff-file-header"><div><h2>变更文件</h2><small>{report.files.length} 个文件 · +{report.summary.additions} −{report.summary.deletions}</small></div><span className="file-count">{files.length}</span></div>
      <label className="file-search"><Search size={14} /><input value={fileSearch} onChange={(event) => setFileSearch(event.target.value)} placeholder="筛选文件" /></label>
      <div className="diff-file-list">{files.map((item) => <button key={`${item.path}-${item.status}`} className={`diff-file-item ${selectedPath === item.path ? "active" : ""}`} onClick={() => setSelectedPath(item.path)}>
        <span className="file-item-path"><FileCode2 size={14} /><span>{item.path}</span></span><span className="file-item-meta"><span className={`role-tag role-${item.role}`}>{roleLabel(item.role)}</span><span className="file-diff"><b className="plus">+{item.additions}</b> <b className="minus">−{item.deletions}</b></span></span>
        {item.status !== "modified" && <span className="file-status">{fileStatusLabel(item.status)}</span>}
      </button>)}{files.length === 0 && <div className="empty-list">没有匹配文件</div>}</div>
    </aside>
    <section className="diff-content" aria-label="代码差异">
      {file ? <>
        <header className="diff-content-header"><div><div className="diff-path">{file.old_path && file.new_path && file.old_path !== file.new_path ? <><span>{file.old_path}</span><ArrowDownRight size={13} /><strong>{file.new_path}</strong></> : <strong>{file.path}</strong>}</div><div className="diff-subline"><span className={`role-tag role-${file.role}`}>{roleLabel(file.role)}</span><span>{fileStatusLabel(file.status)}</span><span className="plus">+{file.additions}</span><span className="minus">−{file.deletions}</span>{file.parse_status.head && <span className={file.parse_status.head === "ok" ? "parse-ok" : "parse-degraded"}>AST {file.parse_status.head === "ok" ? "已解析" : "降级"}</span>}</div></div></header>
        {file.parse_errors.length > 0 && <div className="parse-warning"><AlertCircle size={15} />{file.parse_errors.map((item, index) => <span key={index}>{item.side ?? "版本"}：{item.message ?? "解析失败"}{item.line ? `（${item.line}:${item.column ?? 0}）` : ""}</span>)}</div>}
        {file.binary ? <div className="empty-state diff-empty"><FileText size={19} />二进制文件没有可显示的行级 Diff。</div>
          : file.hunks.length === 0 ? <div className="empty-state diff-empty"><FileText size={19} />此文件没有行级变更内容。可能是纯重命名或 Diff 不可用。</div>
            : <div className="diff-scroll"><div className="diff-table">{file.hunks.map((hunk, hunkIndex) => <section className="diff-hunk" key={`${hunk.old_start}-${hunk.new_start}-${hunkIndex}`}>
              <div className="hunk-heading">@@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@</div>
              {hunk.lines.map((line, lineIndex) => <DiffRow key={`${line.kind}-${line.old_line}-${line.new_line}-${lineIndex}`} line={line} filePath={file.path} highlighted={focusLines.some((number) => line.old_line === number || line.new_line === number)} />)}
            </section>)}</div></div>}
      </> : <div className="empty-state diff-empty">选择左侧文件查看行级变更。</div>}
    </section>
  </div>;
}

function DiffRow({ line, filePath, highlighted }: { line: DiffLine; filePath: string; highlighted: boolean }) {
  const prefix = line.kind === "add" ? "+" : line.kind === "delete" ? "−" : " ";
  return <div className={`diff-row diff-${line.kind}${highlighted ? " diff-highlight" : ""}`} data-file-path={filePath} data-diff-old-line={line.old_line ?? undefined} data-diff-new-line={line.new_line ?? undefined}>
    <span className="line-number old-line-number">{line.old_line ?? ""}</span><span className="line-number new-line-number">{line.new_line ?? ""}</span><span className="diff-marker">{prefix}</span><code>{line.text || " "}</code>
  </div>;
}

function RulesView({ report, catalog, expandedRule, setExpandedRule, onLocate, matchedRuleIds }: {
  report: Report; catalog: Rule[]; expandedRule: string | null; setExpandedRule: (key: string | null) => void;
  onLocate: (evidence: Evidence) => void; matchedRuleIds: Set<string>;
}) {
  return <div className="tab-page rules-page">
    <section className="rules-matched-section"><div className="section-heading"><div><h2>本次分析命中</h2><p>{report.findings.length} 条规则线索 · 展开证据可定位至代码行</p></div><span className="section-number">{report.findings.length}</span></div>
      {report.summary.unanalyzed?.length ? <div className="parse-warning"><AlertCircle size={15} />{report.summary.unanalyzed.length} 项变更未能完成分析，未按通过处理。{report.summary.unanalyzed.map((item) => `${item.path || "本次变更"}：${item.reason === "path_classification_unavailable" ? "路径无法分类" : "差异统计不完整"}`).join("；")}</div> : null}
      {report.findings.length ? <div className="matched-findings">{report.findings.map((finding, index) => <article className="matched-finding" key={`${finding.rule_id}-${index}`}>
        <button className="matched-finding-head" onClick={() => setExpandedRule(expandedRule === `${finding.rule_id}-${index}` ? null : `${finding.rule_id}-${index}`)} aria-expanded={expandedRule === `${finding.rule_id}-${index}`}>
          <span className={`finding-symbol domain-${ruleDomain(finding.rule_id)}`}>{domainIcon(ruleDomain(finding.rule_id))}</span><span className="matched-finding-title"><small>{finding.rule_id}</small><strong>{ruleLabels[finding.rule_id] ?? finding.rule_id}</strong><span>{finding.message}</span></span>
          <span className={`severity-tag severity-${finding.severity}`}>{severityLabel(finding.severity)}</span><span className="evidence-count">{finding.evidence.length} 证据</span>{expandedRule === `${finding.rule_id}-${index}` ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </button>
        {expandedRule === `${finding.rule_id}-${index}` && <div className="matched-evidence-list"><p>复核建议：{finding.suggested_action}</p>{finding.evidence.map((item, evidenceIndex) => <div className="rule-evidence" key={`${item.node_id}-${evidenceIndex}`}>
          <div><strong>{item.path}</strong><span>{item.node_kind} · {item.structural_change_type}</span><small>{item.qualified_name ?? item.node_id}</small>{evidenceDetail(item) ? <small>{evidenceDetail(item)}</small> : null}<code>{item.lines.map((line) => `L${line}`).join(", ") || "无 Diff 行号"}</code></div>
          <button className="text-action" onClick={() => onLocate(item)} disabled={!item.lines.length}>定位到代码 <ArrowUpRight size={14} /></button>
        </div>)}</div>}
      </article>)}</div> : <div className="empty-state"><Check size={18} />本次分析未触发已启用规则。未命中不等于不存在风险，可在下方查看规则定义并复核代码。</div>}
    </section>
    <section className="rule-catalog-section"><div className="section-heading"><div><h2>规则目录</h2><p>当前实现的规则、触发条件与适用边界</p></div><span className="catalog-count">{catalog.length} 条规则</span></div>
      <div className="rule-catalog">{catalog.map((rule) => <article className="catalog-rule" key={rule.rule_id}>
        <div className="catalog-rule-title"><span className={`finding-symbol domain-${ruleDomain(rule.rule_id)}`}>{domainIcon(ruleDomain(rule.rule_id))}</span><div><small>{rule.rule_id}</small><h3>{ruleLabels[rule.rule_id] ?? rule.rule_id}</h3></div><span className={`catalog-state ${matchedRuleIds.has(rule.rule_id) ? "hit" : "miss"}`}>{matchedRuleIds.has(rule.rule_id) ? "本次命中" : "本次未命中"}</span></div>
        <div className="catalog-fields"><CatalogField label="关注域 / 严重程度" value={`${domainLabels[ruleDomain(rule.rule_id)] ?? ruleDomain(rule.rule_id)} · ${severityLabel(rule.severity)}`} /><CatalogField label="触发条件" value={rule.trigger} /><CatalogField label="证据类型" value={rule.evidence_type} /><CatalogField label="适用范围" value={rule.applicable_scope} /><CatalogField label="复核建议" value={rule.suggested_action} /><CatalogField label="当前限制" value={rule.limitations} /></div>
      </article>)}</div>
    </section>
  </div>;
}

function CatalogField({ label, value }: { label: string; value: string }) {
  return <div className="catalog-field"><span>{label}</span><p>{value || "未设置"}</p></div>;
}

function ScoringView({ report, catalog, config, setConfig, onWeight, onToggle, onApply, onReset, busy, baselineScore }: {
  report: Report; catalog: Rule[]; config: Config; setConfig: React.Dispatch<React.SetStateAction<Config>>;
  onWeight: (ruleId: string, value: number) => void; onToggle: (ruleId: string) => void;
  onApply: () => void; onReset: () => void; busy: boolean; baselineScore: number | null;
}) {
  return <div className="tab-page scoring-page">
    <section className="scoring-summary"><div><span>当前分析评分</span><strong>{report.score}<small>/100</small></strong><span className={`risk-pill ${riskClass(report.risk_level)}`}>{riskLabel(report.risk_level)}</span></div><div className="scoring-equation"><strong>{report.score_basis.earned_points}</strong><span>/</span><strong>{report.score_basis.maximum_points}</strong><small>已得权重 / 可得权重</small></div><div className="scoring-baseline"><span>默认分数</span><strong>{baselineScore ?? report.score}</strong><small>仅当前分析的默认配置结果</small></div></section>
    <div className="scoring-layout"><section className="scoring-controls"><div className="section-heading"><div><h2>规则权重</h2><p>开关和权重只用于当前 PR 重算</p></div><button className="icon-button" title="恢复默认" onClick={onReset}><RotateCcw size={16} /></button></div>
      <div className="weight-rule-list">{catalog.map((rule) => <div className="weight-rule" key={rule.rule_id}>
        <label className="rule-toggle"><input type="checkbox" checked={config.enabled_rules.includes(rule.rule_id)} onChange={() => onToggle(rule.rule_id)} /><span className="checkmark"><Check size={12} /></span><span className={`finding-symbol domain-${ruleDomain(rule.rule_id)}`}>{domainIcon(ruleDomain(rule.rule_id))}</span><span><strong>{ruleLabels[rule.rule_id] ?? rule.rule_id}</strong><small>{rule.rule_id}</small></span></label>
        <div className="weight-slider"><input type="range" min={0} max={5} step={1} value={config.rule_weights[rule.rule_id] ?? rule.default_weight} disabled={!config.enabled_rules.includes(rule.rule_id)} onChange={(event) => onWeight(rule.rule_id, Number(event.target.value))} aria-label={`${rule.rule_id} 权重`} /><output>{config.rule_weights[rule.rule_id] ?? rule.default_weight}</output></div>
      </div>)}</div>
      <div className="auxiliary-weight"><label><span><strong>生产代码变更未见测试路径变更</strong><small>与规则行使用同一个权重 1，不另外加分</small></span><input type="checkbox" checked={config.test_collaboration_enabled} onChange={(event) => setConfig((current) => {
        const enabled = event.target.checked;
        const hasRule = current.enabled_rules.includes("workflow.test_collaboration_gap");
        const enabledRules = enabled
          ? (hasRule ? current.enabled_rules : [...current.enabled_rules, "workflow.test_collaboration_gap"])
          : current.enabled_rules.filter((item) => item !== "workflow.test_collaboration_gap");
        return { ...current, test_collaboration_enabled: enabled, enabled_rules: enabledRules };
      })} /></label><div className="weight-slider"><input type="range" min={0} max={5} step={1} value={config.test_collaboration_weight} disabled={!config.test_collaboration_enabled} onChange={(event) => {
        const value = Number(event.target.value);
        setConfig((current) => ({
          ...current,
          test_collaboration_weight: value,
          rule_weights: { ...current.rule_weights, "workflow.test_collaboration_gap": value },
        }));
      }} aria-label="测试协同缺失权重" /><output>{config.test_collaboration_weight}</output></div></div>
    </section>
    <aside className="threshold-panel"><h2>等级阈值</h2><p>调整当前 PR 的复核优先级分段。</p><label>建议复核<input type="number" min={0} max={99} value={config.thresholds.medium} onChange={(event) => setConfig((current) => ({ ...current, thresholds: { ...current.thresholds, medium: Number(event.target.value) } }))} /></label><label>优先复核<input type="number" min={1} max={100} value={config.thresholds.high} onChange={(event) => setConfig((current) => ({ ...current, thresholds: { ...current.thresholds, high: Number(event.target.value) } }))} /></label><button className="primary-button apply-score" onClick={onApply} disabled={busy}>{busy ? <LoaderCircle size={15} className="spin" /> : <Settings2 size={15} />}应用并重算当前 PR</button></aside></div>
    <div className="score-boundary"><CircleHelp size={17} /><div><strong>评分是人工复核优先级，不是缺陷概率。</strong><p>规则按命中与配置权重计分，不按 evidence 条数重复累加。权重尚未通过独立标注集校准。</p></div></div>
  </div>;
}

function fileStatusLabel(status: string) {
  if (status === "added") return "新增";
  if (status === "deleted") return "删除";
  if (status === "renamed") return "重命名";
  return "修改";
}
function severityLabel(value: string) { return value === "high" ? "高" : value === "medium" ? "中" : "低"; }
function renderMarkdown(report: Report) {
  return [
    `# ${report.pr_number ? `PR #${report.pr_number}` : `${report.base_ref} → ${report.head_ref}`} 代码变更复核`, "", `- 标题：${report.title}`, `- 作者：${report.author ?? "未知"}`,
    `- 复核优先级：${report.score}/100（${riskLabel(report.risk_level)}，不是缺陷概率）`,
    `- 变更规模：${report.summary.files_changed} 个文件，+${report.summary.additions} / -${report.summary.deletions}`,
    "", "## 规则线索", ...report.findings.flatMap((finding) => [
      "", `### ${finding.rule_id}`, `- ${finding.message}`, `- 复核建议：${finding.suggested_action}`,
      ...finding.evidence.map((item) => `- ${item.path}:${item.lines.join(",")} · ${item.node_kind} · ${item.structural_change_type} · ${item.qualified_name ?? item.node_id}${evidenceDetail(item) ? ` · ${evidenceDetail(item)}` : ""}`),
    ]), "", "## 说明", ...report.limitations.map((item) => `- ${item}`),
  ].join("\n");
}
