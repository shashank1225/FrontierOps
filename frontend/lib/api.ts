export type DeploymentStatus =
  | "draft"
  | "evaluating"
  | "approved"
  | "blocked"
  | "deployed"
  | "archived";

export type EvaluationStatus = "pending" | "running" | "completed" | "failed" | "cancelled";
export type ReleaseDecision = "pending" | "approved" | "blocked";

export interface Application {
  id: string;
  name: string;
  description: string | null;
  provider: string;
  model: string;
  deployment_status: DeploymentStatus;
  evaluation_dataset_id: string | null;
  active_prompt_version: PromptVersion;
  release_gate_policy: {
    minimum_quality_score: number;
    maximum_latency_ms: number;
    maximum_failure_rate: number;
    maximum_cost_usd: number | null;
  };
  created_at: string;
  updated_at: string;
}

export interface PromptVersion {
  id: string;
  application_id?: string;
  version: number;
  template: string;
  change_summary: string | null;
  is_active: boolean;
  created_at: string;
}

export interface EvaluationDataset {
  id: string;
  name: string;
  description: string | null;
  items: Array<{ id: string; input_text: string }>;
  created_at: string;
  updated_at: string;
}

export interface EvaluationJob {
  id: string;
  application_id: string;
  status: "queued" | "running" | "completed" | "failed";
  enqueued_at: string;
  run_id: string | null;
  error_message: string | null;
}

export interface PromptComparison {
  baseline_version_id: string;
  candidate_version_id: string;
  baseline_run_id: string;
  candidate_run_id: string;
  quality_delta: number | null;
  latency_delta_ms: number | null;
  latency_delta_percent: number | null;
  cost_delta_usd: string;
  cost_delta_percent: number | null;
  failure_rate_delta: number | null;
  regression_detected: boolean;
  regression_reasons: string[];
}

export interface RegisterApplicationInput {
  name: string;
  description?: string;
  provider: string;
  model: string;
  prompt_template: string;
  prompt_change_summary?: string;
  evaluation_dataset_id?: string;
}

export interface EvaluationRun {
  id: string;
  application_id: string;
  prompt_version_id: string;
  provider: string;
  model: string;
  status: EvaluationStatus;
  release_decision: ReleaseDecision;
  total_items: number;
  successful_items: number;
  average_quality_score: number | null;
  average_latency_ms: number | null;
  failure_rate: number | null;
  total_cost_usd: string;
  created_at: string;
}

export interface EvaluationRunPage {
  items: EvaluationRun[];
  total: number;
  offset: number;
  limit: number;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    throw new Error(`FrontierOps API returned ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function mutate<T>(path: string, method: "POST" | "PUT", body?: unknown): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: unknown } | null;
    const detail = typeof payload?.detail === "string" ? payload.detail : null;
    throw new Error(detail ?? `FrontierOps API returned ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  applications: (signal?: AbortSignal) => request<Application[]>("/applications?limit=100", signal),
  evaluationRuns: (signal?: AbortSignal) =>
    request<EvaluationRunPage>("/evaluation-runs?limit=50", signal),
  datasets: (signal?: AbortSignal) => request<EvaluationDataset[]>("/datasets?limit=100", signal),
  registerApplication: (input: RegisterApplicationInput) =>
    mutate<Application>("/applications", "POST", input),
  enqueueEvaluation: (applicationId: string) =>
    mutate<EvaluationJob>(`/applications/${applicationId}/evaluations`, "POST"),
  promptVersions: (applicationId: string, signal?: AbortSignal) =>
    request<PromptVersion[]>(`/applications/${applicationId}/prompt-versions`, signal),
  createPromptVersion: (applicationId: string, template: string, changeSummary: string) =>
    mutate<PromptVersion>(`/applications/${applicationId}/prompt-versions`, "POST", {
      template,
      change_summary: changeSummary || null,
    }),
  activatePromptVersion: (applicationId: string, promptVersionId: string) =>
    mutate<PromptVersion>(
      `/applications/${applicationId}/prompt-versions/${promptVersionId}/activate`,
      "PUT",
    ),
  comparePromptVersions: (applicationId: string, baselineId: string, candidateId: string) =>
    request<PromptComparison>(
      `/applications/${applicationId}/prompt-versions/compare?baseline_version_id=${baselineId}&candidate_version_id=${candidateId}`,
    ),
};
