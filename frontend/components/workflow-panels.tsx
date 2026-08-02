"use client";

import {
  Activity,
  Check,
  ChevronRight,
  CircleAlert,
  FlaskConical,
  GitCompareArrows,
  Plus,
  Rocket,
  X,
} from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";
import {
  api,
  type Application,
  type EvaluationDataset,
  type EvaluationRun,
  type PromptComparison,
  type PromptVersion,
  type RegisterApplicationInput,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

type Refresh = () => void;

export function ApplicationsPanel({ applications, refresh }: { applications: Application[]; refresh: Refresh }) {
  const [open, setOpen] = useState(false);
  const [datasets, setDatasets] = useState<EvaluationDataset[]>([]);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    api.datasets(controller.signal).then(setDatasets).catch(() => setDatasets([]));
    return () => controller.abort();
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const input: RegisterApplicationInput = {
      name: String(data.get("name")),
      description: String(data.get("description") || "") || undefined,
      provider: String(data.get("provider")),
      model: String(data.get("model")),
      prompt_template: String(data.get("prompt_template")),
      prompt_change_summary: "Initial production prompt",
      evaluation_dataset_id: String(data.get("dataset") || "") || undefined,
    };
    setSaving(true);
    setMessage("");
    try {
      await api.registerApplication(input);
      setOpen(false);
      refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Registration failed");
    } finally {
      setSaving(false);
    }
  }

  return <>
    <PanelHeading eyebrow="Registry" title="AI applications" description="Register models, prompts, datasets, and release policies in one governed inventory.">
      <button className="primary-button" onClick={() => setOpen(true)}><Plus size={17} />Register application</button>
    </PanelHeading>
    <div className="application-grid">
      {applications.map((application) => <Card className="application-card" key={application.id}>
        <div className="application-card-top"><div className="large-app-icon">{application.name.slice(0, 2).toUpperCase()}</div><Badge tone={application.deployment_status}>{application.deployment_status}</Badge></div>
        <h2>{application.name}</h2><p>{application.description || "No description provided."}</p>
        <div className="application-spec"><span>Provider<strong>{application.provider}</strong></span><span>Model<strong>{application.model}</strong></span><span>Active prompt<strong>v{application.active_prompt_version.version}</strong></span><span>Dataset<strong>{application.evaluation_dataset_id ? "Attached" : "Missing"}</strong></span></div>
        <div className="gate-summary"><span><Check size={13} />Quality ≥ {(application.release_gate_policy.minimum_quality_score * 100).toFixed(0)}%</span><span>Latency ≤ {application.release_gate_policy.maximum_latency_ms} ms</span></div>
      </Card>)}
      {!applications.length && <EmptyState title="No applications registered" copy="Create the first application to establish its model, prompt, and evaluation dataset." />}
    </div>
    {open && <div className="dialog-backdrop" role="presentation"><div className="dialog" role="dialog" aria-modal="true" aria-labelledby="register-title">
      <div className="dialog-heading"><div><p className="eyebrow">New registry entry</p><h2 id="register-title">Register AI application</h2></div><button className="icon-button" onClick={() => setOpen(false)} aria-label="Close"><X size={17} /></button></div>
      <form onSubmit={submit} className="form-grid">
        <label>Name<input name="name" required maxLength={255} placeholder="Support Copilot" /></label>
        <label>Provider<select name="provider" defaultValue="ollama"><option value="ollama">Ollama</option><option value="openai">OpenAI</option><option value="anthropic">Anthropic</option><option value="gemini">Gemini</option></select></label>
        <label className="span-2">Description<textarea name="description" rows={2} placeholder="What this application does and who owns it" /></label>
        <label>Model<input name="model" required placeholder="llama3.2:3b" /></label>
        <label>Evaluation dataset<select name="dataset" defaultValue=""><option value="">Attach later</option>{datasets.map((dataset) => <option value={dataset.id} key={dataset.id}>{dataset.name} · {dataset.items.length} items</option>)}</select></label>
        <label className="span-2">Initial prompt template<textarea name="prompt_template" required rows={6} placeholder={"Answer the user request using the supplied context.\n\nRequest: {{ input }}"} /></label>
        {message && <div className="form-error span-2"><CircleAlert size={15} />{message}</div>}
        <div className="dialog-actions span-2"><button type="button" className="secondary-button" onClick={() => setOpen(false)}>Cancel</button><button className="primary-button" disabled={saving}>{saving ? "Registering…" : "Register application"}</button></div>
      </form>
    </div></div>}
  </>;
}

export function EvaluationsPanel({ applications, runs, refresh }: { applications: Application[]; runs: EvaluationRun[]; refresh: Refresh }) {
  const [selected, setSelected] = useState(applications[0]?.id ?? "");
  const [status, setStatus] = useState("");
  const [running, setRunning] = useState(false);
  const selectedId = selected || applications[0]?.id || "";

  async function enqueue() {
    if (!selectedId) return;
    setRunning(true); setStatus("");
    try {
      const job = await api.enqueueEvaluation(selectedId);
      setStatus(`Evaluation queued · job ${job.id.slice(0, 8)}`);
      refresh();
    } catch (error) { setStatus(error instanceof Error ? error.message : "Unable to queue evaluation"); }
    finally { setRunning(false); }
  }

  return <>
    <PanelHeading eyebrow="Validation" title="Evaluation runs" description="Execute datasets against active prompts and inspect quality, performance, cost, and release decisions.">
      <div className="heading-action"><select value={selectedId} onChange={(event) => setSelected(event.target.value)} aria-label="Application to evaluate"><option value="">Select application</option>{applications.map((app) => <option value={app.id} key={app.id}>{app.name}</option>)}</select><button className="primary-button" onClick={enqueue} disabled={!selectedId || running}><FlaskConical size={17} />{running ? "Queueing…" : "Run evaluation"}</button></div>
    </PanelHeading>
    {status && <div className="notice"><Rocket size={16} />{status}</div>}
    <Card className="runs-card"><div className="card-heading"><div><h2>Evaluation history</h2><p>Persisted executions, newest first</p></div><Badge tone="neutral">{runs.length} runs</Badge></div>
      <div className="table-wrap"><table><thead><tr><th>Application</th><th>Status</th><th>Quality</th><th>Failure rate</th><th>Latency</th><th>Cost</th><th>Release gate</th></tr></thead><tbody>{runs.map((run) => {
        const app = applications.find((candidate) => candidate.id === run.application_id);
        return <tr key={run.id}><td><div className="table-app"><span>{(app?.name ?? "AI").slice(0, 2).toUpperCase()}</span><strong>{app?.name ?? "Unknown"}</strong></div></td><td><Badge tone={run.status}>{run.status}</Badge></td><td>{run.average_quality_score === null ? "—" : `${(run.average_quality_score * 100).toFixed(1)}%`}</td><td>{run.failure_rate === null ? "—" : `${(run.failure_rate * 100).toFixed(1)}%`}</td><td>{run.average_latency_ms === null ? "—" : `${run.average_latency_ms.toFixed(0)} ms`}</td><td>${Number(run.total_cost_usd).toFixed(4)}</td><td><Badge tone={run.release_decision}>{run.release_decision}</Badge></td></tr>;
      })}{!runs.length && <tr><td colSpan={7}><EmptyState title="No evaluation runs" copy="Select an application and queue its first evaluation." /></td></tr>}</tbody></table></div>
    </Card>
  </>;
}

export function PromptsPanel({ applications, refresh }: { applications: Application[]; refresh: Refresh }) {
  const [applicationId, setApplicationId] = useState(applications[0]?.id ?? "");
  const [versions, setVersions] = useState<PromptVersion[]>([]);
  const [template, setTemplate] = useState("");
  const [summary, setSummary] = useState("");
  const [comparison, setComparison] = useState<PromptComparison | null>(null);
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const selectedApplicationId = applicationId || applications[0]?.id || "";

  useEffect(() => {
    if (!selectedApplicationId) return;
    const controller = new AbortController();
    api.promptVersions(selectedApplicationId, controller.signal).then(setVersions).catch(() => setVersions([]));
    return () => controller.abort();
  }, [selectedApplicationId]);

  const sorted = useMemo(() => [...versions].sort((a, b) => b.version - a.version), [versions]);
  async function create(event: FormEvent) {
    event.preventDefault(); setSaving(true); setMessage("");
    try { const prompt = await api.createPromptVersion(selectedApplicationId, template, summary); setVersions((current) => [prompt, ...current]); setTemplate(""); setSummary(""); setMessage(`Prompt v${prompt.version} created`); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Unable to create prompt"); }
    finally { setSaving(false); }
  }
  async function activate(version: PromptVersion) {
    try { await api.activatePromptVersion(selectedApplicationId, version.id); setVersions((current) => current.map((item) => ({ ...item, is_active: item.id === version.id }))); refresh(); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Activation failed"); }
  }
  async function compare() {
    if (sorted.length < 2) return;
    setMessage("");
    try { setComparison(await api.comparePromptVersions(selectedApplicationId, sorted[1].id, sorted[0].id)); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Both versions need completed evaluation runs before comparison"); }
  }

  return <>
    <PanelHeading eyebrow="Version control" title="Prompt versions" description="Create immutable prompt revisions, activate candidates, compare measured performance, and detect regressions.">
      <select value={selectedApplicationId} onChange={(event) => { setApplicationId(event.target.value); setComparison(null); }} aria-label="Application"><option value="">Select application</option>{applications.map((app) => <option value={app.id} key={app.id}>{app.name}</option>)}</select>
    </PanelHeading>
    <div className="prompt-layout">
      <Card className="prompt-composer"><div className="card-heading"><div><h2>Create prompt version</h2><p>Templates support the <code>{"{{ input }}"}</code> variable</p></div><GitCompareArrows size={18} /></div>
        <form onSubmit={create}><label>Prompt template<textarea value={template} onChange={(event) => setTemplate(event.target.value)} required rows={12} disabled={!selectedApplicationId} placeholder={"Use the context to answer accurately.\n\nUser request: {{ input }}"} /></label><label>Change summary<input value={summary} onChange={(event) => setSummary(event.target.value)} placeholder="Improved grounding instructions" /></label><button className="primary-button" disabled={!selectedApplicationId || saving}>{saving ? "Creating…" : "Create version"}</button></form>
        {message && <div className="inline-message">{message}</div>}
      </Card>
      <Card className="versions-card"><div className="card-heading"><div><h2>Version history</h2><p>{versions.length} immutable revisions</p></div><button className="secondary-button compact" onClick={compare} disabled={sorted.length < 2}><GitCompareArrows size={14} />Compare latest</button></div>
        <div className="version-list">{sorted.map((version) => <div className="version-row" key={version.id}><div className="version-number">v{version.version}</div><div className="version-copy"><strong>{version.change_summary || "Prompt revision"}</strong><span>{new Date(version.created_at).toLocaleDateString()} · {version.template.length} characters</span><p>{version.template}</p></div>{version.is_active ? <Badge tone="approved">active</Badge> : <button className="text-button" onClick={() => activate(version)}>Activate <ChevronRight size={14} /></button>}</div>)}{!versions.length && <EmptyState title="No prompt history" copy="Choose an application to load its prompt versions." />}</div>
      </Card>
    </div>
    {comparison && <Card className={`comparison-card ${comparison.regression_detected ? "has-regression" : ""}`}><div><p className="eyebrow">Latest comparison</p><h2>{comparison.regression_detected ? "Regression detected" : "Candidate is stable"}</h2><p>{comparison.regression_reasons.join(" · ") || "No release-impacting regressions detected."}</p></div><ComparisonMetric label="Quality" value={percentDelta(comparison.quality_delta)} /><ComparisonMetric label="Latency" value={percentDelta(comparison.latency_delta_percent)} /><ComparisonMetric label="Cost" value={percentDelta(comparison.cost_delta_percent)} /></Card>}
  </>;
}

export function ObservabilityPanel() {
  const services = [{ name: "Grafana", copy: "Dashboards and cross-signal analysis", url: "http://localhost:3000", tone: "violet" }, { name: "Prometheus", copy: "Backend and worker time-series metrics", url: "http://localhost:9090", tone: "emerald" }, { name: "Tempo", copy: "Evaluation and provider-call traces", url: "http://localhost:3200", tone: "blue" }];
  return <><PanelHeading eyebrow="Telemetry" title="Observability" description="Follow each evaluation from API request through model inference, scoring, release gates, and persistence." />
    <div className="observability-grid">{services.map((service) => <a href={service.url} target="_blank" rel="noreferrer" key={service.name}><Card className="observability-card"><div className={`metric-icon metric-${service.tone}`}><Activity size={19} /></div><div><h2>{service.name}</h2><p>{service.copy}</p></div><ChevronRight size={18} /></Card></a>)}</div>
  </>;
}

function PanelHeading({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children?: ReactNode }) { return <section className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p>{description}</p></div>{children}</section>; }
function EmptyState({ title, copy }: { title: string; copy: string }) { return <div className="panel-empty"><FlaskConical size={22} /><strong>{title}</strong><span>{copy}</span></div>; }
function ComparisonMetric({ label, value }: { label: string; value: string }) { return <div className="comparison-metric"><span>{label}</span><strong>{value}</strong></div>; }
function percentDelta(value: number | null) { return value === null ? "—" : `${value > 0 ? "+" : ""}${value.toFixed(1)}%`; }
