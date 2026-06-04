import type {
  BackendCapability,
  JobCreateResponse,
  JobRequest,
  JobSummary,
  NormalizedJobResult
} from "../types/quantum";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers ?? {})
      },
      ...options
    });
  } catch {
    throw new Error("Backend server is unavailable. Make sure FastAPI is running at the configured API URL.");
  }

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const detail = typeof payload === "object" && payload !== null && "detail" in payload ? String(payload.detail) : String(payload);
    throw new Error(detail || `Request failed with status ${response.status}.`);
  }

  return payload as T;
}

export const quantumApi = {
  health: () => request<{ status: string }>("/health"),
  backends: () => request<BackendCapability[]>("/backends"),
  submitJob: (job: JobRequest) =>
    request<JobCreateResponse>("/jobs", {
      method: "POST",
      body: JSON.stringify(job)
    }),
  jobs: () => request<JobSummary[]>("/jobs"),
  job: (jobId: string) => request<NormalizedJobResult>(`/jobs/${jobId}`),
  result: (jobId: string) => request<NormalizedJobResult>(`/jobs/${jobId}/result`),
  rerun: (jobId: string) =>
    request<JobCreateResponse>(`/jobs/${jobId}/rerun`, {
      method: "POST"
    })
};

export { API_BASE_URL };
