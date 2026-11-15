import { useMemo, useState } from 'react'
import type { LucideIcon } from 'lucide-react'
import ReviewQueue from "./ReviewQueue"
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowUpRight,
  Bell, CheckCircle2, ChevronDown, Clock3,
  FileText, Filter, LayoutDashboard,
  Menu, MoreHorizontal, Search, Settings, ShieldCheck,
  UploadCloud, X, Inbox, BarChart3,
  History, Sparkles
} from 'lucide-react'

const navigation: { name: string; icon: LucideIcon; count?: string }[] = [
  { name: 'Overview', icon: LayoutDashboard },
  { name: 'Invoices', icon: FileText },
  { name: 'Review Queue', icon: Inbox },
  { name: 'Analytics', icon: BarChart3 },
  { name: 'Audit Trail', icon: History },
]

const invoices = [
  { id: 'INV-2026-1042', supplier: 'Apex Technologies', date: '15 Nov 2026', amount: '₹84,500', status: 'Verified', confidence: '99.2%' },
  { id: 'INV-2026-1041', supplier: 'Global Office Supplies', date: '15 Nov 2026', amount: '₹32,800', status: 'Review', confidence: '87.4%' },
  { id: 'INV-2026-1040', supplier: 'Vertex Solutions', date: '14 Nov 2026', amount: '₹1,24,000', status: 'Exception', confidence: '62.1%' },
  { id: 'INV-2026-1039', supplier: 'Prime Logistics', date: '14 Nov 2026', amount: '₹56,200', status: 'Verified', confidence: '98.6%' },
  { id: 'INV-2026-1038', supplier: 'Nexus Digital', date: '13 Nov 2026', amount: '₹19,750', status: 'Verified', confidence: '97.8%' },
]

const reviews = [
  { id: 'RVW-0081', supplier: 'Global Office Supplies', reason: 'PO mismatch', amount: '₹32,800', priority: 'Medium' },
  { id: 'RVW-0080', supplier: 'Vertex Solutions', reason: 'Anomaly detected', amount: '₹1,24,000', priority: 'High' },
  { id: 'RVW-0079', supplier: 'Metro Components', reason: 'GST discrepancy', amount: '₹48,600', priority: 'High' },
]

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    Verified: 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20',
    Review: 'bg-amber-400/10 text-amber-300 border-amber-400/20',
    Exception: 'bg-rose-400/10 text-rose-400 border-rose-400/20',
  }

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${styles[status] || styles.Review}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {status}
    </span>
  )
}

function App() {
  const [active, setActive] = useState('Overview')
  const [query, setQuery] = useState('')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)

  const filteredInvoices = useMemo(() => invoices.filter(invoice =>
    `${invoice.id} ${invoice.supplier} ${invoice.status}`.toLowerCase().includes(query.toLowerCase())
  ), [query])

  const pageTitle = active === 'Overview' ? 'Overview' : active

  return (
    <div className="min-h-screen bg-[#071411] text-[#E7F0EB]">
      <div className="flex min-h-screen">
        {mobileOpen && (
          <button aria-label="Close navigation" onClick={() => setMobileOpen(false)}
            className="fixed inset-0 z-40 bg-black/60 lg:hidden" />
        )}

        <aside className={`fixed inset-y-0 left-0 z-50 flex w-[258px] flex-col border-r border-[#233A32] bg-[#0B1F19] transition-transform lg:static lg:translate-x-0 ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}>
          <div className="flex h-[82px] items-center gap-3 border-b border-[#233A32] px-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-400 text-[#071411] shadow-lg shadow-emerald-500/10">
              <ShieldCheck size={23} strokeWidth={2.4} />
            </div>
            <div>
              <p className="text-[17px] font-bold tracking-tight">FinGuard<span className="text-emerald-400"> AI</span></p>
              <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-[#91A59B]">Intelligent verification</p>
            </div>
            <button onClick={() => setMobileOpen(false)} className="ml-auto rounded-lg p-2 text-[#91A59B] hover:bg-white/5 lg:hidden">
              <X size={18} />
            </button>
          </div>

          <div className="px-4 pt-7">
            <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.19em] text-[#71877C]">Workspace</p>
            <nav className="space-y-1">
              {navigation.map(item => {
                const Icon = item.icon
                const selected = active === item.name
                return (
                  <button key={item.name} onClick={() => { setActive(item.name); setMobileOpen(false) }}
                    className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-[13px] font-medium transition ${selected ? 'bg-emerald-400/10 text-emerald-300 ring-1 ring-emerald-400/15' : 'text-[#91A59B] hover:bg-white/[0.04] hover:text-white'}`}>
                    <Icon size={18} />
                    <span>{item.name}</span>
                    {item.count && <span className="ml-auto rounded-md bg-amber-400/10 px-2 py-0.5 text-[10px] text-amber-300">{item.count}</span>}
                    {selected && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-emerald-400" />}
                  </button>
                )
              })}
            </nav>
          </div>

          <div className="mt-9 px-4">
            <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.19em] text-[#71877C]">System</p>
            <button onClick={() => setActive('Settings')} className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-[13px] font-medium ${active === 'Settings' ? 'bg-emerald-400/10 text-emerald-300' : 'text-[#91A59B] hover:bg-white/[0.04] hover:text-white'}`}>
              <Settings size={18} /> Settings
            </button>
          </div>

          <div className="mt-auto p-4">
            <div className="rounded-2xl border border-emerald-400/15 bg-gradient-to-br from-[#123329] to-[#0D201A] p-4">
              <div className="mb-3 flex items-center gap-2 text-emerald-300">
                <Sparkles size={16} />
                <span className="text-xs font-semibold">AI Monitoring</span>
              </div>
              <p className="text-xs leading-5 text-[#A7B9AF]">Your verification workspace is ready for intelligent document analysis.</p>
              <div className="mt-4 flex items-center gap-2 text-[10px] text-emerald-300">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                Interface preview
              </div>
            </div>
            <div className="mt-4 flex items-center gap-3 border-t border-[#233A32] pt-4">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#24513F] text-xs font-bold text-emerald-200">FA</div>
              <div className="min-w-0">
                <p className="text-xs font-semibold">FinGuard Admin</p>
                <p className="text-[10px] text-[#91A59B]">Administrator</p>
              </div>
              <MoreHorizontal size={18} className="ml-auto text-[#91A59B]" />
            </div>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <header className="sticky top-0 z-30 flex h-[82px] items-center justify-between border-b border-[#233A32] bg-[#071411]/95 px-4 backdrop-blur-xl sm:px-7 xl:px-10">
            <div className="flex items-center gap-3">
              <button onClick={() => setMobileOpen(true)} className="rounded-lg p-2 text-[#91A59B] hover:bg-white/5 lg:hidden">
                <Menu size={20} />
              </button>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-lg font-semibold tracking-tight sm:text-xl">{pageTitle}</h1>
                  <span className="hidden rounded-md border border-emerald-400/20 bg-emerald-400/10 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-emerald-300 sm:inline-flex">Preview</span>
                </div>
                <p className="mt-0.5 text-[11px] text-[#91A59B]">Financial intelligence workspace</p>
              </div>
            </div>

            <div className="flex items-center gap-2 sm:gap-4">
              <div className="hidden items-center gap-2 rounded-xl border border-[#233A32] bg-[#0D1715] px-3 py-2 text-[11px] text-[#91A59B] md:flex">
                <Activity size={14} className="text-emerald-400" />
                System interface preview
              </div>
              <div className="relative">
                <button aria-label="Notifications" onClick={() => setShowNotifications(!showNotifications)} className="relative rounded-xl border border-[#233A32] p-2.5 text-[#91A59B] hover:bg-white/5 hover:text-white">
                  <Bell size={17} />
                  <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-emerald-400" />
                </button>
                {showNotifications && <div className="absolute right-0 top-12 w-64 rounded-xl border border-[#29483B] bg-[#111F1B] p-4 shadow-2xl">
                  <p className="text-sm font-semibold">Notifications</p>
                  <p className="mt-2 text-xs leading-5 text-[#91A59B]">This preview does not yet load live notifications from the API.</p>
                </div>}
              </div>
              <div className="hidden h-8 w-px bg-[#233A32] sm:block" />
              <div className="hidden items-center gap-2 sm:flex">
                <div className="flex h-9 w-9 items-center justify-center rounded-full border border-emerald-400/20 bg-[#123329] text-xs font-bold text-emerald-300">FA</div>
                <ChevronDown size={14} className="text-[#91A59B]" />
              </div>
            </div>
          </header>

          <div className="mx-auto max-w-[1500px] space-y-7 p-4 sm:p-7 xl:p-10">
            {active === 'Review Queue' ? (
              <div className="py-2">
                <ReviewQueue />
              </div>
            ) : (
              <>

            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
              <div>
                <p className="text-xs font-medium text-emerald-400">SUNDAY, 15 NOVEMBER 2026</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-[28px]">Financial intelligence, at a glance.</h2>
                <p className="mt-2 text-sm text-[#91A59B]">Monitor invoices, verification outcomes and human-review activity.</p>
              </div>
              <label className="flex cursor-pointer items-center justify-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-semibold text-[#071411] shadow-lg shadow-emerald-500/10 transition hover:bg-emerald-300">
                <UploadCloud size={16} /> Upload invoice
                <input type="file" accept=".pdf,.png,.jpg,.jpeg" className="hidden" onChange={e => e.currentTarget.files?.[0] && alert(`Selected: ${e.currentTarget.files[0].name}. API upload integration is the next step.`)} />
              </label>
            </div>

            <div className="rounded-xl border border-amber-400/20 bg-amber-400/[0.06] px-4 py-3 text-xs leading-5 text-amber-200/90">
              <span className="font-semibold">Demonstration data:</span> Dashboard analytics and invoice records are illustrative. The human review queue uses live backend data.
            </div>

            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {[
                { label: 'Total invoices processed', value: '1,284', change: '+12.8%', icon: FileText, tone: 'text-sky-300', bg: 'bg-sky-400/10', trend: 'up' },
                { label: 'Successfully verified', value: '1,106', change: '+8.4%', icon: CheckCircle2, tone: 'text-emerald-300', bg: 'bg-emerald-400/10', trend: 'up' },
                { label: 'Pending human review', value: '08', change: 'Needs attention', icon: Clock3, tone: 'text-amber-300', bg: 'bg-amber-400/10', trend: 'neutral' },
                { label: 'Exceptions detected', value: '23', change: 'Requires action', icon: AlertTriangle, tone: 'text-rose-300', bg: 'bg-rose-400/10', trend: 'down' },
              ].map((metric) => {
                const Icon = metric.icon
                return (
                  <div key={metric.label} className="rounded-2xl border border-[#233A32] bg-[#0D1915] p-5 transition hover:border-[#365746]">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-[#91A59B]">{metric.label}</span>
                      <div className={`rounded-xl p-2.5 ${metric.bg} ${metric.tone}`}><Icon size={18} /></div>
                    </div>
                    <p className="mt-5 text-[30px] font-semibold tracking-tight">{metric.value}</p>
                    <div className="mt-2 flex items-center gap-1.5 text-[11px]">
                      {metric.trend === 'up' ? <ArrowUpRight size={14} className="text-emerald-400" /> : metric.trend === 'down' ? <ArrowDownRight size={14} className="text-rose-400" /> : <Clock3 size={13} className="text-amber-300" />}
                      <span className={metric.trend === 'up' ? 'text-emerald-400' : metric.trend === 'down' ? 'text-rose-400' : 'text-amber-300'}>{metric.change}</span>
                      {metric.trend !== 'neutral' && <span className="text-[#71877C]">vs previous period</span>}
                    </div>
                  </div>
                )
              })}
            </section>

            <section className="grid gap-5 xl:grid-cols-[1.55fr_1fr]">
              <div className="rounded-2xl border border-[#233A32] bg-[#0D1915] p-5 sm:p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold">Verification performance</h3>
                    <p className="mt-1 text-[11px] text-[#91A59B]">Illustrative weekly invoice outcomes</p>
                  </div>
                  <button className="flex items-center gap-2 rounded-lg border border-[#29483B] px-3 py-2 text-[11px] text-[#A7B9AF]">Last 7 days <ChevronDown size={13} /></button>
                </div>
                <div className="mt-7 flex h-[190px] items-end justify-between gap-3 border-b border-[#29483B] pb-0">
                  {[
                    { day: 'Mon', verified: 65, review: 15 },
                    { day: 'Tue', verified: 82, review: 22 },
                    { day: 'Wed', verified: 72, review: 13 },
                    { day: 'Thu', verified: 93, review: 19 },
                    { day: 'Fri', verified: 78, review: 27 },
                    { day: 'Sat', verified: 58, review: 12 },
                    { day: 'Sun', verified: 88, review: 17 },
                  ].map((bar) => (
                    <div key={bar.day} className="flex h-full flex-1 flex-col items-center justify-end gap-2">
                      <div className="flex h-full w-full max-w-10 flex-col justify-end overflow-hidden rounded-t-md bg-[#172923]">
                        <div className="w-full rounded-t-sm bg-amber-400/80" style={{ height: `${bar.review}%` }} />
                        <div className="w-full bg-emerald-400" style={{ height: `${bar.verified}%` }} />
                      </div>
                      <span className="mb-2 text-[10px] text-[#71877C]">{bar.day}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-5 flex flex-wrap gap-5 text-[11px] text-[#91A59B]">
                  <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-sm bg-emerald-400" />Verified</span>
                  <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-sm bg-amber-400" />Review / exception</span>
                </div>
              </div>

              <div className="rounded-2xl border border-[#233A32] bg-[#0D1915] p-5 sm:p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold">Verification breakdown</h3>
                    <p className="mt-1 text-[11px] text-[#91A59B]">Illustrative distribution</p>
                  </div>
                  <MoreHorizontal size={19} className="text-[#91A59B]" />
                </div>
                <div className="flex items-center justify-center py-7">
                  <div className="relative flex h-40 w-40 items-center justify-center rounded-full" style={{ background: 'conic-gradient(#34D399 0% 86%, #FBBF24 86% 94%, #FB7185 94% 100%)' }}>
                    <div className="flex h-[116px] w-[116px] flex-col items-center justify-center rounded-full bg-[#0D1915]">
                      <span className="text-3xl font-semibold">86%</span>
                      <span className="mt-1 text-[10px] text-[#91A59B]">Verified</span>
                    </div>
                  </div>
                </div>
                <div className="space-y-4">
                  {[
                    { label: 'Verified', amount: '1,106', percent: '86%', color: 'bg-emerald-400' },
                    { label: 'Review required', amount: '101', percent: '8%', color: 'bg-amber-400' },
                    { label: 'Exceptions', amount: '77', percent: '6%', color: 'bg-rose-400' },
                  ].map(row => (
                    <div key={row.label} className="flex items-center justify-between text-xs">
                      <span className="flex items-center gap-2 text-[#A7B9AF]"><span className={`h-2 w-2 rounded-full ${row.color}`} />{row.label}</span>
                      <span className="font-medium">{row.amount} <span className="ml-2 text-[#71877C]">{row.percent}</span></span>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section className="grid gap-5 xl:grid-cols-[1.55fr_1fr]">
              <div className="overflow-hidden rounded-2xl border border-[#233A32] bg-[#0D1915]">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#233A32] p-5 sm:px-6">
                  <div>
                    <h3 className="text-sm font-semibold">Recent invoices</h3>
                    <p className="mt-1 text-[11px] text-[#91A59B]">Latest document processing activity</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-2 rounded-lg border border-[#29483B] bg-[#071411] px-3 py-2">
                      <Search size={13} className="text-[#71877C]" />
                      <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search invoices..." className="w-28 bg-transparent text-[11px] text-white outline-none placeholder:text-[#71877C] sm:w-36" />
                    </div>
                    <button aria-label="Filter invoices" className="rounded-lg border border-[#29483B] p-2 text-[#91A59B]"><Filter size={15} /></button>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[650px] text-left">
                    <thead className="bg-white/[0.02] text-[10px] uppercase tracking-wider text-[#71877C]">
                      <tr><th className="px-6 py-3 font-medium">Invoice / Supplier</th><th className="px-4 py-3 font-medium">Date</th><th className="px-4 py-3 font-medium">Amount</th><th className="px-4 py-3 font-medium">Confidence</th><th className="px-4 py-3 font-medium">Status</th></tr>
                    </thead>
                    <tbody className="divide-y divide-[#233A32]">
                      {filteredInvoices.map(invoice => (
                        <tr key={invoice.id} className="transition hover:bg-white/[0.025]">
                          <td className="px-6 py-4"><p className="text-xs font-medium text-white">{invoice.id}</p><p className="mt-1 text-[10px] text-[#91A59B]">{invoice.supplier}</p></td>
                          <td className="px-4 py-4 text-[11px] text-[#91A59B]">{invoice.date}</td>
                          <td className="px-4 py-4 text-xs font-medium">{invoice.amount}</td>
                          <td className="px-4 py-4 text-xs text-[#A7B9AF]">{invoice.confidence}</td>
                          <td className="px-4 py-4"><StatusBadge status={invoice.status} /></td>
                        </tr>
                      ))}
                      {filteredInvoices.length === 0 && <tr><td colSpan={5} className="px-6 py-8 text-center text-xs text-[#91A59B]">No matching invoices found.</td></tr>}
                    </tbody>
                  </table>
                </div>
                <div className="border-t border-[#233A32] px-6 py-3 text-[10px] text-[#71877C]">Showing illustrative invoice records</div>
              </div>

              <div className="overflow-hidden rounded-2xl border border-[#233A32] bg-[#0D1915]">
                <div className="flex items-center justify-between border-b border-[#233A32] p-5">
                  <div>
                    <h3 className="text-sm font-semibold">Human review queue</h3>
                    <p className="mt-1 text-[11px] text-[#91A59B]">Items awaiting reviewer attention</p>
                  </div>
                  <span className="rounded-lg bg-amber-400/10 px-2.5 py-1 text-xs font-semibold text-amber-300">03</span>
                </div>
                <div className="divide-y divide-[#233A32]">
                  {reviews.map(review => (
                    <div key={review.id} className="p-4 transition hover:bg-white/[0.02]">
                      <div className="flex items-start justify-between gap-2">
                        <div><p className="text-xs font-medium">{review.supplier}</p><p className="mt-1 text-[10px] text-[#71877C]">{review.id}</p></div>
                        <span className={`rounded-md px-2 py-1 text-[9px] font-semibold ${review.priority === 'High' ? 'bg-rose-400/10 text-rose-300' : 'bg-amber-400/10 text-amber-300'}`}>{review.priority}</span>
                      </div>
                      <div className="mt-3 flex items-center justify-between text-[10px]">
                        <span className="text-[#91A59B]">{review.reason}</span>
                        <span className="font-semibold">{review.amount}</span>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="border-t border-[#233A32] p-4">
                  <button onClick={() => setActive('Review Queue')} className="flex w-full items-center justify-center gap-2 rounded-lg border border-[#29483B] py-2.5 text-[11px] font-medium text-emerald-300 transition hover:bg-emerald-400/5">
                    View review queue <ArrowUpRight size={14} />
                  </button>
                </div>
              </div>
            </section>

              </>
            )}

            <footer className="flex flex-col justify-between gap-2 border-t border-[#233A32] pt-5 text-[10px] text-[#71877C] sm:flex-row">
              <span>© 2026 FinGuard AI. Intelligent Financial Document Verification.</span>
              <span className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> Review API connected · Analytics and invoice data illustrative</span>
            </footer>
          </div>
        </main>
      </div>
    </div>
  )
}

export default App
