import React, { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Cpu,
  DollarSign,
  RefreshCw,
  Search,
  ShieldAlert,
  Sliders,
  Terminal,
  UserCheck,
  Zap,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  HelpCircle,
  BarChart2
} from 'lucide-react'
import { getAdminLLMOpsMetrics, getAdminLLMOpsTraces } from '../api/admin'
import toast from 'react-hot-toast'

export const LLMOpsDashboard = () => {
  const [metrics, setMetrics] = useState(null)
  const [tracesData, setTracesData] = useState({ total: 0, traces: [] })
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  
  // Filters & Pagination
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedAgent, setSelectedAgent] = useState('')
  const [selectedStatus, setSelectedStatus] = useState('')
  const [expandedTraceId, setExpandedTraceId] = useState(null)
  const [page, setPage] = useState(0)
  const pageSize = 20

  const fetchData = useCallback(async (isManualRefresh = false) => {
    if (isManualRefresh) setRefreshing(true)
    try {
      const [mRes, tRes] = await Promise.all([
        getAdminLLMOpsMetrics(),
        getAdminLLMOpsTraces({
          search: searchQuery || undefined,
          agent: selectedAgent || undefined,
          status: selectedStatus || undefined,
          offset: page * pageSize,
          limit: pageSize
        })
      ])
      setMetrics(mRes)
      setTracesData(tRes)
      if (isManualRefresh) {
        toast.success('LLMOps telemetry synced')
      }
    } catch (err) {
      console.error('Failed to load LLMOps telemetry:', err)
      toast.error(err.response?.data?.detail || 'Failed to load telemetry')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [searchQuery, selectedAgent, selectedStatus, page])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const toggleTraceExpand = (idx) => {
    setExpandedTraceId(expandedTraceId === idx ? null : idx)
  }

  if (loading && !metrics) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <RefreshCw className="w-8 h-8 text-brand-indigo animate-spin mb-3" />
        <p className="text-txt-secondary text-sm font-medium">Loading LLMOps Telemetry Engine...</p>
      </div>
    )
  }

  const overview = metrics?.overview || {}
  const tokenEco = metrics?.token_economics || {}
  const latency = overview?.latency_ms || {}
  const taxonomy = metrics?.error_taxonomy?.breakdown || {}
  const agents = metrics?.agents || {}
  const humanEval = metrics?.human_alignment || {}

  return (
    <div className="space-y-6 text-txt-primary">
      {/* Header Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-bg-card p-5 rounded-xl border border-border-custom shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg">
              <Activity className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-bold tracking-tight">LLMOps Observability & Error Taxonomy</h1>
          </div>
          <p className="text-xs text-txt-secondary mt-1">
            Real-time multi-agent execution telemetry, Error Taxonomy (E101–E106) diagnostics, and token economics.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => fetchData(true)}
            disabled={refreshing}
            className="flex items-center gap-2 px-3.5 py-2 bg-bg-surface hover:bg-bg-page border border-border-custom rounded-lg text-xs font-semibold text-txt-primary transition-colors cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            <span>{refreshing ? 'Refreshing...' : 'Sync Telemetry'}</span>
          </button>
        </div>
      </div>

      {/* Primary KPI Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Operations */}
        <div className="bg-bg-card p-5 rounded-xl border border-border-custom shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-txt-secondary text-xs font-semibold">
            <span>TOTAL TRACED RUNS</span>
            <Zap className="w-4 h-4 text-brand-indigo" />
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-txt-primary">
              {overview.total_traced_calls?.toLocaleString() || 0}
            </span>
            <div className="flex items-center gap-2 mt-1 text-xs">
              <span className="text-emerald-400 font-medium flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                {overview.success_rate_pct}% Success
              </span>
              {overview.retry_count > 0 && (
                <span className="text-amber-400 font-medium">
                  ({overview.retry_count} retries)
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Latency P95 */}
        <div className="bg-bg-card p-5 rounded-xl border border-border-custom shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-txt-secondary text-xs font-semibold">
            <span>P95 SLA LATENCY</span>
            <Clock className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-emerald-400">
              {latency.p95 || 0} <span className="text-sm font-normal text-txt-secondary">ms</span>
            </span>
            <div className="flex items-center justify-between mt-1 text-xs text-txt-secondary">
              <span>P50: {latency.p50 || 0}ms</span>
              <span>P99: {latency.p99 || 0}ms</span>
            </div>
          </div>
        </div>

        {/* Token Economics */}
        <div className="bg-bg-card p-5 rounded-xl border border-border-custom shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-txt-secondary text-xs font-semibold">
            <span>TOKEN CONSUMPTION</span>
            <DollarSign className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-txt-primary">
              {tokenEco.total_tokens?.toLocaleString() || 0} <span className="text-sm font-normal text-txt-secondary">tok</span>
            </span>
            <div className="flex items-center justify-between mt-1 text-xs text-amber-400/90 font-medium">
              <span>Est. Cost: ${tokenEco.total_cost_usd || 0}</span>
              <span className="text-[10px] text-txt-tertiary">Groq Llama 3.1</span>
            </div>
          </div>
        </div>

        {/* Human Alignment */}
        <div className="bg-bg-card p-5 rounded-xl border border-border-custom shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-txt-secondary text-xs font-semibold">
            <span>HITL ALIGNMENT</span>
            <UserCheck className="w-4 h-4 text-purple-400" />
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-purple-400">
              {humanEval.mean_overall ? `${humanEval.mean_overall} / 5.0` : '5.0 / 5.0'}
            </span>
            <div className="flex items-center justify-between mt-1 text-xs text-txt-secondary">
              <span className="text-purple-300 font-medium">{humanEval.alignment_rate_pct}% Aligned</span>
              <span>{humanEval.total_ratings} Reviews</span>
            </div>
          </div>
        </div>
      </div>

      {/* Latency Percentile Profile */}
      <div className="bg-bg-card p-5 rounded-xl border border-border-custom shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-brand-indigo" />
            <h2 className="text-sm font-bold tracking-tight">Latency Distribution Profile (Percentiles)</h2>
          </div>
          <span className="text-xs text-txt-secondary">Mean Execution: {latency.mean || 0} ms</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {[
            { label: 'Min', val: latency.min, color: 'text-txt-secondary' },
            { label: 'P50 (Median)', val: latency.p50, color: 'text-emerald-400' },
            { label: 'P90', val: latency.p90, color: 'text-blue-400' },
            { label: 'P95 (SLA)', val: latency.p95, color: 'text-indigo-400' },
            { label: 'P99', val: latency.p99, color: 'text-amber-400' },
            { label: 'Max', val: latency.max, color: 'text-rose-400' },
          ].map((item, i) => (
            <div key={i} className="bg-bg-surface p-3.5 rounded-lg border border-border-custom">
              <div className="text-[11px] font-medium text-txt-secondary">{item.label}</div>
              <div className={`text-lg font-bold mt-1 ${item.color}`}>
                {item.val ?? 0} <span className="text-[10px] text-txt-tertiary">ms</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Error Taxonomy (E101 - E106) Matrix */}
      <div className="bg-bg-card p-5 rounded-xl border border-border-custom shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            <h2 className="text-sm font-bold tracking-tight">Error Taxonomy & Resilience Architecture (E101–E106)</h2>
          </div>
          <span className="text-xs text-txt-secondary">
            Total Intercepted Errors: {metrics?.error_taxonomy?.total_errors || 0}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(taxonomy).map(([code, item]) => {
            const isZero = (item.count || 0) === 0
            const sevColor =
              item.severity === 'CRITICAL'
                ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                : item.severity === 'HIGH'
                ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                : 'bg-blue-500/10 text-blue-400 border-blue-500/20'

            return (
              <div
                key={code}
                className="bg-bg-surface p-4 rounded-xl border border-border-custom flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 text-xs font-mono font-bold bg-bg-card rounded border border-border-custom text-brand-indigo">
                        {code}
                      </span>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${sevColor}`}>
                        {item.severity}
                      </span>
                    </div>
                    <span className={`text-sm font-bold ${isZero ? 'text-txt-tertiary' : 'text-amber-400'}`}>
                      {item.count || 0} runs
                    </span>
                  </div>

                  <h3 className="text-xs font-semibold text-txt-primary mt-2">{item.name}</h3>
                  <p className="text-[11px] text-txt-secondary mt-1">{item.description}</p>
                </div>

                <div className="mt-3 pt-3 border-t border-border-custom/50 text-[10px] text-emerald-400/90 font-medium">
                  <span className="text-txt-tertiary font-normal">Recovery: </span>
                  {item.remediation}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Multi-Agent Telemetry Breakdown Table */}
      <div className="bg-bg-card rounded-xl border border-border-custom shadow-sm overflow-hidden">
        <div className="p-5 border-b border-border-custom flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-brand-indigo" />
            <h2 className="text-sm font-bold tracking-tight">Agent-Specific Telemetry Breakdown</h2>
          </div>
          <span className="text-xs text-txt-secondary">Active Agents: {Object.keys(agents).length}</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-border-custom bg-bg-surface text-txt-secondary">
                <th className="p-3.5 font-semibold">Agent / Subsystem</th>
                <th className="p-3.5 font-semibold text-center">Invocations</th>
                <th className="p-3.5 font-semibold text-center">Success Rate</th>
                <th className="p-3.5 font-semibold text-center">Mean Latency</th>
                <th className="p-3.5 font-semibold text-center">P95 Latency</th>
                <th className="p-3.5 font-semibold text-center">Retries / Errors</th>
                <th className="p-3.5 font-semibold text-right">Token Usage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-custom">
              {Object.entries(agents).map(([agentName, stats]) => (
                <tr key={agentName} className="hover:bg-bg-surface/50 transition-colors">
                  <td className="p-3.5 font-semibold text-txt-primary flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-brand-indigo" />
                    {agentName}
                  </td>
                  <td className="p-3.5 text-center font-medium">{stats.total_calls}</td>
                  <td className="p-3.5 text-center">
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                        stats.success_rate_pct >= 95
                          ? 'bg-emerald-500/10 text-emerald-400'
                          : 'bg-amber-500/10 text-amber-400'
                      }`}
                    >
                      {stats.success_rate_pct}%
                    </span>
                  </td>
                  <td className="p-3.5 text-center font-mono text-txt-secondary">{stats.mean_latency_ms} ms</td>
                  <td className="p-3.5 text-center font-mono text-txt-primary font-medium">{stats.p95_latency_ms} ms</td>
                  <td className="p-3.5 text-center text-txt-secondary">
                    {stats.retry_count} / {stats.error_count}
                  </td>
                  <td className="p-3.5 text-right font-mono text-txt-secondary">
                    {(stats.input_tokens + stats.output_tokens).toLocaleString()}
                  </td>
                </tr>
              ))}
              {Object.keys(agents).length === 0 && (
                <tr>
                  <td colSpan={7} className="p-6 text-center text-txt-secondary">
                    No agent telemetry records found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Live Audit Traces & Log Stream */}
      <div className="bg-bg-card rounded-xl border border-border-custom shadow-sm overflow-hidden">
        <div className="p-5 border-b border-border-custom">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-brand-indigo" />
              <h2 className="text-sm font-bold tracking-tight">Live Structured Audit Trace Log Stream</h2>
            </div>
            <div className="text-xs text-txt-secondary">
              Showing {tracesData.traces?.length || 0} of {tracesData.total || 0} matching records
            </div>
          </div>

          {/* Filters Bar */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-txt-tertiary absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search request_id, agent, details..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value)
                  setPage(0)
                }}
                className="w-full bg-bg-surface border border-border-custom rounded-lg pl-9 pr-3 py-1.5 text-xs text-txt-primary placeholder:text-txt-tertiary focus:outline-none focus:border-brand-indigo"
              />
            </div>

            <select
              value={selectedAgent}
              onChange={(e) => {
                setSelectedAgent(e.target.value)
                setPage(0)
              }}
              className="bg-bg-surface border border-border-custom rounded-lg px-3 py-1.5 text-xs text-txt-primary focus:outline-none focus:border-brand-indigo"
            >
              <option value="">All Agents</option>
              {Object.keys(agents).map((ag) => (
                <option key={ag} value={ag}>
                  {ag}
                </option>
              ))}
            </select>

            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value)
                setPage(0)
              }}
              className="bg-bg-surface border border-border-custom rounded-lg px-3 py-1.5 text-xs text-txt-primary focus:outline-none focus:border-brand-indigo"
            >
              <option value="">All Statuses</option>
              <option value="SUCCESS">SUCCESS</option>
              <option value="HTTP_2">HTTP 2xx</option>
              <option value="RETRY_RECOMMENDED">RETRY_RECOMMENDED</option>
              <option value="FAILED">FAILED</option>
              <option value="HTTP_4">HTTP 4xx</option>
              <option value="HTTP_5">HTTP 5xx</option>
            </select>
          </div>
        </div>

        {/* Traces List */}
        <div className="divide-y divide-border-custom">
          {tracesData.traces?.map((trace, idx) => {
            const isExpanded = expandedTraceId === idx
            const isSuccess =
              trace.status === 'SUCCESS' ||
              (typeof trace.status === 'string' && trace.status.startsWith('HTTP_2'))
            const isRetry = trace.status === 'RETRY_RECOMMENDED'
            const isFail = !isSuccess && !isRetry

            return (
              <div key={idx} className="p-4 hover:bg-bg-surface/40 transition-colors">
                <div
                  onClick={() => toggleTraceExpand(idx)}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                        isSuccess
                          ? 'bg-emerald-500/10 text-emerald-400'
                          : isRetry
                          ? 'bg-amber-500/10 text-amber-400'
                          : 'bg-rose-500/10 text-rose-400'
                      }`}
                    >
                      {trace.status}
                    </span>
                    <span className="font-semibold text-xs text-txt-primary">{trace.agent}</span>
                    {trace.tool && (
                      <span className="text-xs text-txt-secondary font-mono bg-bg-surface px-2 py-0.5 rounded border border-border-custom">
                        {String(trace.tool)}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-4 text-xs text-txt-secondary">
                    <span className="font-mono text-txt-primary font-medium">{trace.latency_ms} ms</span>
                    <span className="text-[11px] text-txt-tertiary">
                      {trace.timestamp ? new Date(trace.timestamp).toLocaleTimeString() : ''}
                    </span>
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-txt-tertiary" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-txt-tertiary" />
                    )}
                  </div>
                </div>

                {/* Expanded Details Drawer */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mt-3 pt-3 border-t border-border-custom text-xs"
                    >
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3 text-txt-secondary">
                        <div>
                          <span className="text-txt-tertiary">Request ID: </span>
                          <span className="font-mono text-txt-primary">{trace.request_id}</span>
                        </div>
                        <div>
                          <span className="text-txt-tertiary">User ID: </span>
                          <span className="font-mono text-txt-primary">{trace.user_id ?? 'Anonymous'}</span>
                        </div>
                        <div>
                          <span className="text-txt-tertiary">Input Tokens: </span>
                          <span className="font-mono text-txt-primary">{trace.input_tokens ?? 0}</span>
                        </div>
                        <div>
                          <span className="text-txt-tertiary">Output Tokens: </span>
                          <span className="font-mono text-txt-primary">{trace.output_tokens ?? 0}</span>
                        </div>
                      </div>

                      <div className="bg-bg-page p-3 rounded-lg border border-border-custom font-mono text-[11px] overflow-x-auto text-txt-secondary">
                        <div className="text-txt-tertiary mb-1 font-sans text-[10px]">Execution Details JSON:</div>
                        <pre className="whitespace-pre-wrap">{JSON.stringify(trace.details || {}, null, 2)}</pre>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )
          })}

          {tracesData.traces?.length === 0 && (
            <div className="p-8 text-center text-txt-secondary text-xs">
              No trace logs found matching the filter criteria.
            </div>
          )}
        </div>

        {/* Pagination Footer */}
        {tracesData.total > pageSize && (
          <div className="p-3.5 border-t border-border-custom flex items-center justify-between text-xs text-txt-secondary">
            <span>
              Page {page + 1} of {Math.ceil(tracesData.total / pageSize)}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-3 py-1 bg-bg-surface border border-border-custom rounded hover:bg-bg-page disabled:opacity-40"
              >
                Previous
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={(page + 1) * pageSize >= tracesData.total}
                className="px-3 py-1 bg-bg-surface border border-border-custom rounded hover:bg-bg-page disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default LLMOpsDashboard

