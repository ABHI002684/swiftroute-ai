import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowDownToLine,
  ArrowRight,
  CheckCircle2,
  Clock3,
  LayoutDashboard,
  MapPin,
  Package,
  RefreshCw,
  Truck,
  Users,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

import api from '../../services/api'
import type { DashboardOverview } from './types/dashboard'
import '../../App.css'

const statusColors: Record<string, string> = {
  Delivered: '#16a36a',
  Pending: '#e7a23b',
  'In transit': '#477ee8',
  Delayed: '#e15b5b',
  Failed: '#858b98',
}

function MetricCard({
  label,
  value,
  icon: Icon,
  color,
  detail,
}: {
  label: string
  value: string | number
  icon: LucideIcon
  color: string
  detail: string
}) {
  return (
    <article className="metric-card">
      <div className="metric-top">
        <span className="metric-label">{label}</span>
        <span className={`metric-icon ${color}`}>
          <Icon size={19} />
        </span>
      </div>
      <div className="metric-value">{value}</div>
      <div className="metric-detail">{detail}</div>
    </article>
  )
}

function Dashboard() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')

  const fetchOverview = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }

    setError('')

    try {
      const response = await api.get<DashboardOverview>('/dashboard/overview')
      setOverview(response.data)
    } catch {
      setError(
        'Unable to load dashboard data. Check that the backend is running and try again.',
      )
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
  const controller = new AbortController()

  api
    .get<DashboardOverview>('/dashboard/overview', {
      signal: controller.signal,
    })
    .then((response) => {
      setOverview(response.data)
    })
    .catch(() => {
      if (!controller.signal.aborted) {
        setError(
          'Unable to load dashboard data. Check that the backend is running and try again.',
        )
      }
    })
    .finally(() => {
      if (!controller.signal.aborted) {
        setLoading(false)
      }
    })

  return () => controller.abort()
}, [])

  const statusData = useMemo(() => {
    if (!overview) return []

    return [
      { name: 'Delivered', value: overview.delivered },
      { name: 'Pending', value: overview.pending },
      { name: 'In transit', value: overview.in_transit },
      { name: 'Delayed', value: overview.delayed },
      { name: 'Failed', value: overview.failed },
    ]
  }, [overview])

  const visibleStatusTotal = statusData.reduce(
  (total, item) => total + item.value,
  0,
  )
  const formattedDate = new Intl.DateTimeFormat('en-IN', {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date())

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Truck size={23} />
          </div>
          <div>
            <div className="brand-name">SwiftRoute</div>
            <div className="brand-subtitle">INTELLIGENT LOGISTICS</div>
          </div>
        </div>

        <div className="nav-section-label">WORKSPACE</div>
        <nav className="sidebar-nav">
          <a className="nav-link active" href="#dashboard">
            <LayoutDashboard size={18} />
            <span>Dashboard</span>
          </a>
          <a className="nav-link disabled" href="#deliveries" aria-disabled="true">
            <Package size={18} />
            <span>Deliveries</span>
            <span className="nav-soon">Soon</span>
          </a>
          <a className="nav-link disabled" href="#employees" aria-disabled="true">
            <Users size={18} />
            <span>Employees</span>
            <span className="nav-soon">Soon</span>
          </a>
          <a className="nav-link disabled" href="#analytics" aria-disabled="true">
            <Activity size={18} />
            <span>Analytics</span>
            <span className="nav-soon">Soon</span>
          </a>
        </nav>

        <div className="sidebar-bottom">
          <div className="system-status">
            <span className="status-dot" />
            <div>
              <strong>Operations system</strong>
              <small>Dashboard workspace</small>
            </div>
          </div>
          <div className="sidebar-version">SWIFTROUTE AI · DEMO</div>
        </div>
      </aside>

      <main className="main-content" id="dashboard">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span> <strong>Dashboard</strong>
          </div>
          <div className="topbar-right">
            <span className="date-label">
              <Clock3 size={15} />
              {formattedDate}
            </span>
            <div className="avatar">SR</div>
          </div>
        </header>

        <section className="dashboard-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">OPERATIONS OVERVIEW</div>
              <h1>Good day, Operations Team</h1>
              <p>Monitor deliveries and track your logistics performance.</p>
            </div>
            <button
              className="refresh-button"
              onClick={() => void fetchOverview(true)}
              disabled={loading || refreshing}
            >
              <RefreshCw
                size={16}
                className={refreshing ? 'spin' : ''}
              />
              {refreshing ? 'Refreshing...' : 'Refresh data'}
            </button>
          </div>

          {error && (
            <div className="error-banner" role="alert">
              <AlertCircle size={19} />
              <span>{error}</span>
              <button onClick={() => void fetchOverview()}>
                Try again
              </button>
            </div>
          )}

          {loading && !overview ? (
            <div className="loading-panel">
              <RefreshCw className="spin" size={25} />
              <span>Loading your operations overview...</span>
            </div>
          ) : overview ? (
            <>
              <section className="metrics-grid">
                <MetricCard
                  label="Total deliveries"
                  value={overview.total_deliveries.toLocaleString('en-IN')}
                  icon={Package}
                  color="blue"
                  detail="All recorded shipments"
                />
                <MetricCard
                  label="Delivered"
                  value={overview.delivered.toLocaleString('en-IN')}
                  icon={CheckCircle2}
                  color="green"
                  detail={`${overview.completion_rate}% completion rate`}
                />
                <MetricCard
                  label="In transit"
                  value={overview.in_transit.toLocaleString('en-IN')}
                  icon={Truck}
                  color="purple"
                  detail="Currently on the move"
                />
                <MetricCard
                  label="Pending"
                  value={overview.pending.toLocaleString('en-IN')}
                  icon={Clock3}
                  color="orange"
                  detail="Awaiting next action"
                />
                <MetricCard
                  label="Delayed"
                  value={overview.delayed.toLocaleString('en-IN')}
                  icon={AlertTriangle}
                  color="red"
                  detail="Marked as delayed"
                />
                <MetricCard
                  label="Active employees"
                  value={overview.active_employees.toLocaleString('en-IN')}
                  icon={Users}
                  color="teal"
                  detail="Available workforce"
                />
              </section>

              <section className="insight-grid">
                <article className="panel chart-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Delivery status</h2>
                      <p>Breakdown of key delivery statuses</p>
                    </div>
                    <span className="panel-icon">
                      <Activity size={18} />
                    </span>
                  </div>

                  {visibleStatusTotal === 0 ? (
                    <div className="empty-chart">No delivery data available.</div>
                  ) : (
                    <div className="chart-content">
                      <div className="donut-chart">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={statusData}
                              dataKey="value"
                              nameKey="name"
                              innerRadius="66%"
                              outerRadius="90%"
                              paddingAngle={3}
                              stroke="none"
                            >
                              {statusData.map((item) => (
                                <Cell
                                  key={item.name}
                                  fill={statusColors[item.name]}
                                />
                              ))}
                            </Pie>
                            <Tooltip />
                          </PieChart>
                        </ResponsiveContainer>
                        <div className="chart-center">
                          <strong>{visibleStatusTotal}</strong>
                          <span>Shown statuses</span>
                        </div>
                      </div>

                      <div className="chart-legend">
                        {statusData.map((item) => (
                          <div className="legend-row" key={item.name}>
                            <span
                              className="legend-dot"
                              style={{ background: statusColors[item.name] }}
                            />
                            <span className="legend-name">{item.name}</span>
                            <strong>{item.value}</strong>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </article>

                <article className="panel attention-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Needs attention</h2>
                      <p>Deliveries requiring operational action</p>
                    </div>
                    <span className="panel-icon warning-icon">
                      <AlertTriangle size={18} />
                    </span>
                  </div>

                  <div className="attention-total">
                    {overview.deliveries_requiring_attention}
                    <span>deliveries</span>
                  </div>

                  <div className="attention-item">
                    <div className="attention-icon red">
                      <AlertCircle size={17} />
                    </div>
                    <div>
                      <strong>Overdue deliveries</strong>
                      <small>Past their scheduled delivery time</small>
                    </div>
                    <b>{overview.overdue_deliveries}</b>
                  </div>

                  <div className="attention-item">
                    <div className="attention-icon orange">
                      <AlertTriangle size={17} />
                    </div>
                    <div>
                      <strong>Delayed deliveries</strong>
                      <small>Currently marked as delayed</small>
                    </div>
                    <b>{overview.delayed}</b>
                  </div>

                  <div className="attention-note">
                    <MapPin size={15} />
                    Review these deliveries to prevent further delays.
                  </div>
                </article>
              </section>

              <section className="panel performance-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Delivery performance</h2>
                    <p>Overall completion progress</p>
                  </div>
                  <span className="completion-value">
                    {overview.completion_rate}%
                  </span>
                </div>
                <div
                  className="progress-track"
                  role="progressbar"
                  aria-label="Delivery completion rate"
                  aria-valuenow={overview.completion_rate}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <div
                    className="progress-fill"
                    style={{
                      width: `${Math.min(100, Math.max(0, overview.completion_rate))}%`,
                    }}
                  />
                </div>
                <div className="progress-caption">
                  <span>{overview.delivered} completed</span>
                  <span>{overview.total_deliveries} total deliveries</span>
                </div>
              </section>

              <footer className="dashboard-footer">
                <span>SwiftRoute AI · Logistics Operations</span>
                <span>
                  Live data from backend <ArrowRight size={13} />
                </span>
              </footer>
            </>
          ) : (
            <div className="empty-state">
              <ArrowDownToLine size={28} />
              <h2>No dashboard data</h2>
              <p>Refresh to try loading your operations data again.</p>
              <button
                className="refresh-button"
                onClick={() => void fetchOverview()}
              >
                <RefreshCw size={16} />
                Retry
              </button>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

export default Dashboard
