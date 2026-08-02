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
  active_prompt_version: { id: string; version: number; template: string };
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

export const api = {
  applications: (signal?: AbortSignal) => request<Application[]>("/applications?limit=100", signal),
  evaluationRuns: (signal?: AbortSignal) =>
    request<EvaluationRunPage>("/evaluation-runs?limit=50", signal),
};
