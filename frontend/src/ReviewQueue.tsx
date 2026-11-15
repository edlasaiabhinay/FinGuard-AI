import { useCallback, useEffect, useState } from "react"
import {
  ShieldCheck, RefreshCw, LogOut, FileText, Clock3,
  CheckCircle2, XCircle, AlertTriangle, Eye, LockKeyhole
} from "lucide-react"

import {
  authenticateReviewer,
  fetchReviewQueue,
  fetchReviewDetails,
  submitReviewDecision,
  type ReviewCase,
  type ReviewDetailsResponse,
  type ReviewDecision,
} from "./api"

export default function ReviewQueue() {
  const [token, setToken] = useState("")
  const [tokenInput, setTokenInput] = useState("")
  const [authenticated, setAuthenticated] = useState(false)
  const [reviews, setReviews] = useState<ReviewCase[]>([])
  const [selected, setSelected] = useState<ReviewDetailsResponse | null>(null)
  const [comment, setComment] = useState("")
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")

  const loadQueue = useCallback(async (activeToken: string) => {
    setLoading(true)
    setError("")
    try {
      const result = await fetchReviewQueue(activeToken)
      setReviews(result.reviews)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load review queue.")
    } finally {
      setLoading(false)
    }
  }, [])

  const login = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const candidate = tokenInput.trim()
    if (!candidate) return

    setLoading(true)
    setError("")
    try {
      await authenticateReviewer(candidate)
      setToken(candidate)
      setAuthenticated(true)
      setTokenInput("")
      await loadQueue(candidate)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed.")
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    setToken("")
    setTokenInput("")
    setAuthenticated(false)
    setReviews([])
    setSelected(null)
    setComment("")
    setError("")
    setSuccess("")
  }

  const openCase = async (caseId: string) => {
    setError("")
    setSuccess("")
    setLoading(true)
    try {
      const result = await fetchReviewDetails(token, caseId)
      setSelected(result)
      setComment("")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load case details.")
    } finally {
      setLoading(false)
    }
  }

  const decide = async (decision: ReviewDecision) => {
    if (!selected) return

    const labels: Record<ReviewDecision, string> = {
      APPROVE: "approve this case",
      REJECT: "reject this case",
      REQUEST_CORRECTION: "request a correction",
    }

    if (!window.confirm(`Are you sure you want to ${labels[decision]}?`)) return

    setActionLoading(true)
    setError("")
    setSuccess("")

    try {
      await submitReviewDecision(
        token,
        selected.case.case_id,
        decision,
        comment.trim()
      )

      setSuccess("Reviewer decision recorded successfully.")
      setSelected(null)
      setComment("")
      await loadQueue(token)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Decision submission failed.")
    } finally {
      setActionLoading(false)
    }
  }

  useEffect(() => {
    if (!authenticated || !token) return

    const interval = window.setInterval(() => {
      loadQueue(token)
    }, 30000)

    return () => window.clearInterval(interval)
  }, [authenticated, token, loadQueue])

  const panel = "rounded-2xl border border-[#233A32] bg-[#0D1915]"
  const muted = "text-[#91A59B]"

  if (!authenticated) {
    return (
      <div className="mx-auto max-w-xl py-10">
        <div className={`${panel} p-7 sm:p-9`}>
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-400/10 text-emerald-300">
            <LockKeyhole size={27} />
          </div>

          <h2 className="mt-5 text-center text-xl font-semibold">
            Reviewer authentication
          </h2>
          <p className={`mt-2 text-center text-sm ${muted}`}>
            Sign in with your authorized FinGuard reviewer token to access pending cases.
          </p>

          <form onSubmit={login} className="mt-7 space-y-4">
            <label className="block text-xs font-medium text-[#A7B9AF]">
              Reviewer bearer token
              <input
                type="password"
                value={tokenInput}
                onChange={event => setTokenInput(event.target.value)}
                placeholder="Enter your reviewer token"
                autoComplete="off"
                required
                className="mt-2 w-full rounded-xl border border-[#29483B] bg-[#071411] px-4 py-3 text-sm text-white outline-none focus:border-emerald-400"
              />
            </label>

            {error && (
              <p role="alert" className="rounded-lg border border-rose-400/20 bg-rose-400/10 p-3 text-xs text-rose-300">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading || !tokenInput.trim()}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-400 py-3 text-sm font-semibold text-[#071411] transition hover:bg-emerald-300 disabled:opacity-50"
            >
              <ShieldCheck size={17} />
              {loading ? "Authenticating..." : "Access review queue"}
            </button>
          </form>

          <p className={`mt-5 text-center text-[10px] ${muted}`}>
            Token remains in memory only and is cleared when you log out or reload.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-emerald-400">HUMAN-IN-THE-LOOP</p>
          <h2 className="mt-2 text-2xl font-semibold">Review workspace</h2>
          <p className={`mt-1 text-sm ${muted}`}>
            Review AI-flagged documents and record authorized decisions.
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => loadQueue(token)}
            disabled={loading}
            className="flex items-center gap-2 rounded-xl border border-[#29483B] px-3 py-2.5 text-xs text-emerald-300 hover:bg-white/5 disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
          <button
            onClick={logout}
            className="flex items-center gap-2 rounded-xl border border-[#29483B] px-3 py-2.5 text-xs text-[#A7B9AF] hover:bg-white/5"
          >
            <LogOut size={14} /> Logout
          </button>
        </div>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-rose-400/20 bg-rose-400/10 p-3 text-xs text-rose-300">
          {error}
        </div>
      )}

      {success && (
        <div role="status" className="rounded-xl border border-emerald-400/20 bg-emerald-400/10 p-3 text-xs text-emerald-300">
          {success}
        </div>
      )}

      <div className={`${panel} flex items-center justify-between p-5`}>
        <div>
          <p className={`text-xs ${muted}`}>Pending human-review cases</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums">{reviews.length}</p>
        </div>
        <div className="rounded-xl bg-amber-400/10 p-3 text-amber-300">
          <Clock3 size={23} />
        </div>
      </div>

      <div className="grid items-start gap-5 xl:grid-cols-[1fr_1.15fr]">
        <section className={`${panel} overflow-hidden`}>
          <div className="border-b border-[#233A32] p-5">
            <h3 className="text-sm font-semibold">Pending cases</h3>
            <p className={`mt-1 text-[11px] ${muted}`}>
              Live data from the FinGuard review database
            </p>
          </div>

          {loading && reviews.length === 0 ? (
            <p className={`p-7 text-center text-xs ${muted}`}>Loading review cases...</p>
          ) : reviews.length === 0 ? (
            <div className="p-9 text-center">
              <CheckCircle2 size={30} className="mx-auto text-emerald-400" />
              <p className="mt-3 text-sm font-medium">No pending reviews</p>
              <p className={`mt-1 text-xs ${muted}`}>
                New cases will appear here when the AI workflow requests human review.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-[#233A32]">
              {reviews.map(review => (
                <button
                  key={review.case_id}
                  onClick={() => openCase(review.case_id)}
                  className={`w-full p-4 text-left transition hover:bg-white/[0.035] ${
                    selected?.case.case_id === review.case_id ? "bg-emerald-400/[0.06]" : ""
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-xs font-semibold">{review.document_id}</p>
                      <p className={`mt-1 break-all text-[10px] ${muted}`}>
                        {review.case_id}
                      </p>
                    </div>
                    <span className={`shrink-0 rounded-md px-2 py-1 text-[9px] font-semibold ${
                      review.ai_decision === "EXCEPTION"
                        ? "bg-rose-400/10 text-rose-300"
                        : "bg-amber-400/10 text-amber-300"
                    }`}>
                      {review.ai_decision}
                    </span>
                  </div>
                  <p className={`mt-3 text-[10px] ${muted}`}>
                    {review.reasons?.length ?? 0} review reason(s) · {review.created_at}
                  </p>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className={`${panel} min-h-[300px] overflow-hidden`}>
          {!selected ? (
            <div className="flex min-h-[300px] flex-col items-center justify-center p-8 text-center">
              <Eye size={30} className="text-emerald-400" />
              <p className="mt-3 text-sm font-medium">Select a review case</p>
              <p className={`mt-1 text-xs ${muted}`}>
                Case information, verification report and audit history will appear here.
              </p>
            </div>
          ) : (
            <>
              <div className="border-b border-[#233A32] p-5">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-400">
                  Case details
                </p>
                <h3 className="mt-2 break-all text-sm font-semibold">
                  {selected.case.document_id}
                </h3>
                <p className={`mt-1 break-all text-[10px] ${muted}`}>
                  {selected.case.case_id}
                </p>
              </div>

              <div className="space-y-5 p-5">
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl bg-[#071411] p-3">
                    <p className={`text-[10px] ${muted}`}>AI decision</p>
                    <p className="mt-1 text-sm font-semibold">{selected.case.ai_decision}</p>
                  </div>
                  <div className="rounded-xl bg-[#071411] p-3">
                    <p className={`text-[10px] ${muted}`}>Review status</p>
                    <p className="mt-1 text-sm font-semibold">{selected.case.review_status}</p>
                  </div>
                </div>

                <div>
                  <h4 className="mb-3 flex items-center gap-2 text-xs font-semibold">
                    <AlertTriangle size={14} className="text-amber-300" />
                    Review reasons
                  </h4>
                  {selected.case.reasons?.length ? (
                    <ul className="space-y-2">
                      {selected.case.reasons.map((reason, index) => (
                        <li key={index} className={`rounded-lg bg-[#071411] p-3 text-xs ${muted}`}>
                          {reason}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className={`text-xs ${muted}`}>No reason details supplied.</p>
                  )}
                </div>

                <div>
                  <h4 className="mb-3 flex items-center gap-2 text-xs font-semibold">
                    <FileText size={14} className="text-emerald-300" />
                    Verification report
                  </h4>
                  <pre className="max-h-64 overflow-auto rounded-xl bg-[#071411] p-3 text-[10px] leading-5 text-[#A7B9AF]">
                    {JSON.stringify(selected.case.report, null, 2)}
                  </pre>
                </div>

                <div>
                  <h4 className="mb-3 text-xs font-semibold">Audit history</h4>
                  {selected.audit_history.length ? (
                    <div className="space-y-3">
                      {selected.audit_history.map(event => (
                        <div key={event.event_id} className="border-l border-emerald-400/30 pl-3">
                          <p className="text-xs font-medium">{event.event_type}</p>
                          <p className={`mt-1 text-[10px] ${muted}`}>
                            {event.actor_id} · {event.created_at}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className={`text-xs ${muted}`}>No audit events available.</p>
                  )}
                </div>

                {selected.case.review_status === "PENDING" && (
                  <div className="space-y-3 border-t border-[#233A32] pt-5">
                    <label className="block text-xs font-medium text-[#A7B9AF]">
                      Reviewer comment (optional)
                      <textarea
                        value={comment}
                        onChange={event => setComment(event.target.value)}
                        maxLength={4000}
                        rows={3}
                        placeholder="Enter your review observations..."
                        className="mt-2 w-full resize-y rounded-xl border border-[#29483B] bg-[#071411] p-3 text-xs text-white outline-none focus:border-emerald-400"
                      />
                    </label>

                    <div className="grid gap-2 sm:grid-cols-3">
                      <button
                        disabled={actionLoading}
                        onClick={() => decide("APPROVE")}
                        className="flex items-center justify-center gap-1.5 rounded-lg bg-emerald-400/15 px-2 py-3 text-[10px] font-semibold text-emerald-300 hover:bg-emerald-400/25 disabled:opacity-50"
                      >
                        <CheckCircle2 size={14} /> Approve
                      </button>
                      <button
                        disabled={actionLoading}
                        onClick={() => decide("REJECT")}
                        className="flex items-center justify-center gap-1.5 rounded-lg bg-rose-400/10 px-2 py-3 text-[10px] font-semibold text-rose-300 hover:bg-rose-400/20 disabled:opacity-50"
                      >
                        <XCircle size={14} /> Reject
                      </button>
                      <button
                        disabled={actionLoading}
                        onClick={() => decide("REQUEST_CORRECTION")}
                        className="flex items-center justify-center gap-1.5 rounded-lg bg-amber-400/10 px-2 py-3 text-[10px] font-semibold text-amber-300 hover:bg-amber-400/20 disabled:opacity-50"
                      >
                        <AlertTriangle size={14} /> Correction
                      </button>
                    </div>
                    {actionLoading && (
                      <p className={`text-center text-[10px] ${muted}`}>
                        Submitting reviewer decision...
                      </p>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  )
}
