export type ReviewDecision =
  | "APPROVE"
  | "REJECT"
  | "REQUEST_CORRECTION"

export interface ReviewCase {
  case_id: string
  document_id: string
  ai_decision: "REVIEW" | "EXCEPTION"
  review_status: "PENDING" | "APPROVED" | "REJECTED" | "CORRECTION_REQUESTED"
  reasons: string[]
  report: Record<string, unknown>
  created_at: string
  updated_at: string
  reviewer_id?: string | null
  reviewer_decision?: string | null
  reviewer_comment?: string | null
  reviewed_at?: string | null
}

export interface ReviewAuditEvent {
  event_id: string
  case_id: string
  event_type: string
  actor_id: string
  event_data_json: string
  created_at: string
}

export interface ReviewQueueResponse {
  count: number
  reviews: ReviewCase[]
}

export interface ReviewDetailsResponse {
  case: ReviewCase
  audit_history: ReviewAuditEvent[]
}

async function apiRequest<T>(
  endpoint: string,
  token: string,
  options: RequestInit = {}
): Promise<T> {
  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "")
  const response = await fetch(`${apiBaseUrl}${endpoint}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...options.headers,
    },
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const message =
      typeof data.detail === "string"
        ? data.detail
        : `API request failed (${response.status})`

    throw new Error(message)
  }

  return data as T
}

export function authenticateReviewer(token: string) {
  return apiRequest<ReviewQueueResponse>("/api/reviews/", token)
}

export function fetchReviewQueue(token: string) {
  return apiRequest<ReviewQueueResponse>("/api/reviews/", token)
}

export function fetchReviewDetails(token: string, caseId: string) {
  return apiRequest<ReviewDetailsResponse>(
    `/api/reviews/${encodeURIComponent(caseId)}`,
    token
  )
}

export function submitReviewDecision(
  token: string,
  caseId: string,
  decision: ReviewDecision,
  comment: string
) {
  return apiRequest<{ message: string; case: ReviewCase }>(
    `/api/reviews/${encodeURIComponent(caseId)}/decision`,
    token,
    {
      method: "POST",
      body: JSON.stringify({ decision, comment }),
    }
  )
}
