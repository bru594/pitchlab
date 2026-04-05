// src/pages/Dashboard.jsx
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Search, Users, Mail, TrendingUp, ArrowRight, Zap } from 'lucide-react'
import api from '../lib/api'
import { useAuthStore } from '../lib/store'
import './Dashboard.css'

export default function Dashboard() {
  const { user } = useAuthStore()
  const [credits, setCredits] = useState(null)
  const [stats, setStats] = useState({ leads: 0, audits: 0, messages: 0, sequences: 0 })

  useEffect(() => {
    api.get('/credits/balance').then(({ data }) => setCredits(data)).catch(() => {})
    // Pull lead count
    api.get('/leads/?per_page=1').then(({ data }) => {
      setStats((s) => ({ ...s, leads: data.total || 0 }))
    }).catch(() => {})
    api.get('/messaging/sequences').then(({ data }) => {
      setStats((s) => ({ ...s, sequences: data.length || 0 }))
    }).catch(() => {})
    api.get('/messaging/history').then(({ data }) => {
      setStats((s) => ({ ...s, messages: data.length || 0 }))
    }).catch(() => {})
  }, [])

  const pct = credits
    ? Math.round((credits.balance / credits.monthly_allocation) * 100)
    : 0

  return (
    <div className="dashboard fade-in">
      <div className="page-header">
        <h1>Good to see you, {user?.full_name?.split(' ')[0] || 'there'} 👋</h1>
        <p>Here's your pipeline at a glance.</p>
      </div>

      {/* Credit widget */}
      <div className="credit-widget card">
        <div className="credit-widget-top">
          <div>
            <div className="credit-balance">{credits?.balance ?? '—'}</div>
            <div className="credit-label">credits remaining</div>
          </div>
          <div className="credit-plan">
            <span className={`badge badge-${credits?.plan || 'free'}`}>
              {(credits?.plan || 'free').toUpperCase()}
            </span>
            {credits?.plan === 'free' && (
              <Link to="/billing" className="btn btn-primary btn-sm" style={{ marginLeft: 10 }}>
                Upgrade →
              </Link>
            )}
          </div>
        </div>
        <div className="credit-bar-track">
          <div
            className="credit-bar-fill"
            style={{ width: `${pct}%`, background: pct > 30 ? 'var(--accent)' : 'var(--red)' }}
          />
        </div>
        <div className="credit-reset text-xs text-dim">
          {credits?.next_reset_at
            ? `Resets ${new Date(credits.next_reset_at).toLocaleDateString()}`
            : 'Monthly reset included'}
          {' · '}
          <span className="text-muted">
            Searches cost {credits?.costs?.lead_search ?? 5}cr ·
            Audits {credits?.costs?.audit ?? 3}cr ·
            Pitches {credits?.costs?.pitch_generation ?? 2}cr
          </span>
        </div>
      </div>

      {/* Stats row */}
      <div className="stats-grid">
        {[
          { icon: Users,    label: 'Total Leads',    value: stats.leads,     to: '/leads' },
          { icon: Search,   label: 'Active Sequences', value: stats.sequences, to: '/messaging' },
          { icon: Mail,     label: 'Messages Sent',  value: stats.messages,  to: '/messaging' },
          { icon: TrendingUp, label: 'Audits Run',   value: stats.audits,    to: '/leads' },
        ].map(({ icon: Icon, label, value, to }) => (
          <Link key={label} to={to} className="stat-card card card-hover">
            <div className="stat-icon"><Icon size={20} /></div>
            <div className="stat-value">{value}</div>
            <div className="stat-label text-muted text-sm">{label}</div>
          </Link>
        ))}
      </div>

      {/* Workflow CTA */}
      <div className="workflow-section">
        <h3 className="text-muted" style={{ marginBottom: 14, fontSize: '0.875rem', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          Your workflow
        </h3>
        <div className="workflow-steps">
          {[
            { num: '01', label: 'Find Leads',      sub: 'Search by location + niche', to: '/find',      color: 'var(--blue)'   },
            { num: '02', label: 'Audit Websites',  sub: 'Score + expose their problems', to: '/leads',  color: 'var(--orange)' },
            { num: '03', label: 'Generate Pitch',  sub: 'AI writes your outreach',    to: '/leads',     color: 'var(--accent)' },
            { num: '04', label: 'Send & Follow Up', sub: 'Automated sequences',       to: '/messaging', color: 'var(--green)'  },
          ].map(({ num, label, sub, to, color }, i, arr) => (
            <div key={num} className="workflow-step-wrap">
              <Link to={to} className="workflow-step card card-hover">
                <div className="step-num" style={{ color }}>{num}</div>
                <div className="step-label">{label}</div>
                <div className="step-sub text-dim text-xs">{sub}</div>
              </Link>
              {i < arr.length - 1 && (
                <ArrowRight size={18} className="step-arrow" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Quick start CTA if no leads */}
      {stats.leads === 0 && (
        <div className="quickstart card" style={{ marginTop: 24 }}>
          <Zap size={24} className="text-accent" />
          <div>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>Start finding leads</div>
            <div className="text-muted text-sm">Search for local businesses in your area to get started.</div>
          </div>
          <Link to="/find" className="btn btn-primary">Find leads →</Link>
        </div>
      )}
    </div>
  )
}
