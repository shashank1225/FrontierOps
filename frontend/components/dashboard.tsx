"use client";

import {
  Activity,
  AppWindow,
  ArrowDownRight,
  ArrowUpRight,
  Boxes,
  CheckCircle2,
  ChevronRight,
  CircleDollarSign,
  Clock3,
  FlaskConical,
  Gauge,
  GitBranch,
  LayoutDashboard,
  Menu,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type Application, type EvaluationRun } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

const navItems = [
  [LayoutDashboard, "Overview", true],
  [AppWindow, "Applications", false],
  [FlaskConical, "Evaluations", false],
  [GitBranch, "Prompt versions", false],
  [Activity, "Observability", false],
] as const;

function formatNumber(value: number | null, suffix = "") {
  return value === null ? "—" : `${value.toLocaleString(undefined, { maximumFractionDigits: 1 })}${suffix}`;
}

function relativeDate(value: string) {
  const minutes = Math.max(1, Math.round((Date.now() - new Date(value).getTime()) / 60000));
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function Dashboard() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const load = useCallback(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(false);
    Promise.all([api.applications(controller.signal), api.evaluationRuns(controller.signal)])
      .then(([apps, history]) => {
        setApplications(apps);
        setRuns(history.items);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([api.applications(controller.signal), api.evaluationRuns(controller.signal)])
      .then(([apps, history]) => {
        setApplications(apps);
        setRuns(history.items);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  const completed = useMemo(() => runs.filter((run) => run.status === "completed"), [runs]);
  const approved = completed.filter((run) => run.release_decision === "approved").length;
  const avgQuality = completed.length
    ? completed.reduce((sum, run) => sum + (run.average_quality_score ?? 0), 0) / completed.length
    : null;
  const avgLatency = completed.length
    ? completed.reduce((sum, run) => sum + (run.average_latency_ms ?? 0), 0) / completed.length
    : null;
  const totalCost = completed.reduce((sum, run) => sum + Number(run.total_cost_usd), 0);

  const chartData = useMemo(
    () =>
      [...completed]
        .reverse()
        .slice(-12)
        .map((run, index) => ({
          name: `R${index + 1}`,
          quality: Math.round((run.average_quality_score ?? 0) * 100),
          latency: run.average_latency_ms ?? 0,
        })),
    [completed],
  );

  return (
    <div className="app-shell">
      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
        <div className="brand"><div className="brand-mark"><Sparkles size={18} /></div><span>FrontierOps</span></div>
        <button className="mobile-close" onClick={() => setMenuOpen(false)} aria-label="Close navigation"><X /></button>
        <nav className="nav-list" aria-label="Primary navigation">
          <p className="nav-label">Workspace</p>
          {navItems.map(([Icon, label, active]) => (
            <button type="button" className={`nav-item ${active ? "active" : ""}`} key={label}>
              <Icon size={18} /><span>{label}</span>{active && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="environment"><span className="status-pulse" /><div><strong>Platform healthy</strong><small>Local environment</small></div></div>
          <button type="button" className="nav-item"><Settings size={18} /><span>Settings</span></button>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <button className="menu-button" onClick={() => setMenuOpen(true)} aria-label="Open navigation"><Menu /></button>
          <div className="search"><Search size={17} /><span>Search applications, runs, prompts…</span><kbd>⌘ K</kbd></div>
          <div className="topbar-actions"><span className="live-indicator"><span />Live</span><button className="avatar">SK</button></div>
        </header>

        <div className="page-content">
          <section className="page-heading">
            <div><p className="eyebrow">AI control plane</p><h1>Operational overview</h1><p>Quality, performance, and release readiness across your AI applications.</p></div>
            <button className="primary-button"><FlaskConical size={17} />Run evaluation</button>
          </section>

          {error && <div className="connection-banner"><div><strong>Backend connection unavailable</strong><span>Start the FrontierOps API to load live platform data.</span></div><button onClick={load}><RefreshCw size={15} />Retry</button></div>}

          <section className="metric-grid" aria-label="Key metrics">
            <Metric icon={Boxes} label="Applications" value={loading ? "—" : String(applications.length)} detail={`${applications.filter((a) => a.deployment_status === "deployed").length} deployed`} tone="violet" />
            <Metric icon={ShieldCheck} label="Release approval" value={completed.length ? `${Math.round((approved / completed.length) * 100)}%` : "—"} detail={`${approved} of ${completed.length} runs`} tone="emerald" trend="up" />
            <Metric icon={Gauge} label="Average quality" value={avgQuality === null ? "—" : `${(avgQuality * 100).toFixed(1)}%`} detail="Across completed runs" tone="blue" trend="up" />
            <Metric icon={Clock3} label="Average latency" value={formatNumber(avgLatency, " ms")} detail={`$${totalCost.toFixed(4)} total cost`} tone="amber" trend="down" />
          </section>

          <section className="dashboard-grid">
            <Card className="chart-card">
              <div className="card-heading"><div><h2>Quality trend</h2><p>Composite evaluation score by recent run</p></div><Badge tone="neutral">Last 12 runs</Badge></div>
              <div className="chart-wrap">
                {chartData.length ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 12, right: 8, left: -24, bottom: 0 }}>
                      <defs><linearGradient id="quality" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#7c6df2" stopOpacity={0.34} /><stop offset="100%" stopColor="#7c6df2" stopOpacity={0} /></linearGradient></defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e9e7ef" />
                      <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: "#858197", fontSize: 11 }} />
                      <YAxis domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fill: "#858197", fontSize: 11 }} />
                      <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #e2dfee", boxShadow: "0 12px 30px rgba(35,28,70,.12)" }} />
                      <Area type="monotone" dataKey="quality" stroke="#6d5de7" strokeWidth={2.5} fill="url(#quality)" />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : <EmptyChart />}
              </div>
            </Card>

            <Card className="release-card">
              <div className="card-heading"><div><h2>Release readiness</h2><p>Latest application decisions</p></div><button className="icon-button"><ChevronRight size={18} /></button></div>
              <div className="release-list">
                {applications.slice(0, 4).map((application) => (
                  <div className="release-row" key={application.id}>
                    <div className="app-icon">{application.name.slice(0, 2).toUpperCase()}</div>
                    <div className="release-copy"><strong>{application.name}</strong><span>{application.model} · Prompt v{application.active_prompt_version.version}</span></div>
                    <Badge tone={application.deployment_status}>{application.deployment_status}</Badge>
                  </div>
                ))}
                {!applications.length && <EmptyList label="No applications registered yet" />}
              </div>
            </Card>
          </section>

          <Card className="runs-card">
            <div className="card-heading"><div><h2>Recent evaluation runs</h2><p>Latest model validations and gate decisions</p></div><button className="text-button">View history <ChevronRight size={15} /></button></div>
            <div className="table-wrap"><table><thead><tr><th>Application</th><th>Model</th><th>Quality</th><th>Latency</th><th>Cost</th><th>Decision</th><th>Run</th></tr></thead><tbody>
              {runs.slice(0, 6).map((run) => {
                const app = applications.find((item) => item.id === run.application_id);
                return <tr key={run.id}><td><div className="table-app"><span>{(app?.name ?? "AI").slice(0, 2).toUpperCase()}</span><strong>{app?.name ?? "Unknown application"}</strong></div></td><td><code>{run.model}</code></td><td><strong>{run.average_quality_score === null ? "—" : `${(run.average_quality_score * 100).toFixed(1)}%`}</strong></td><td>{formatNumber(run.average_latency_ms, " ms")}</td><td>${Number(run.total_cost_usd).toFixed(4)}</td><td><Badge tone={run.release_decision}>{run.release_decision}</Badge></td><td className="muted">{relativeDate(run.created_at)}</td></tr>;
              })}
              {!runs.length && <tr><td colSpan={7}><EmptyList label="No evaluation runs yet" /></td></tr>}
            </tbody></table></div>
          </Card>
        </div>
      </main>
      {menuOpen && <button className="scrim" onClick={() => setMenuOpen(false)} aria-label="Close navigation overlay" />}
    </div>
  );
}

function Metric({ icon: Icon, label, value, detail, tone, trend }: { icon: typeof Boxes; label: string; value: string; detail: string; tone: string; trend?: "up" | "down" }) {
  return <Card className="metric-card"><div className={`metric-icon metric-${tone}`}><Icon size={19} /></div><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-detail">{trend === "up" ? <ArrowUpRight size={14} /> : trend === "down" ? <ArrowDownRight size={14} /> : <CheckCircle2 size={14} />}{detail}</div></Card>;
}

function EmptyChart() { return <div className="empty-chart"><div className="empty-bars">{[32, 48, 40, 67, 58, 78, 72, 88].map((height, index) => <i key={index} style={{ height: `${height}%` }} />)}</div><span>Quality trends appear after evaluations complete</span></div>; }
function EmptyList({ label }: { label: string }) { return <div className="empty-list"><CircleDollarSign size={20} /><span>{label}</span></div>; }
