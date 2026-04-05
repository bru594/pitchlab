// src/pages/Billing.jsx
import { useState, useEffect } from 'react'
import { CheckCircle, Zap, CreditCard } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'
import { useAuthStore } from '../lib/store'
import './Billing.css'

export default function Billing() {
  const { user } = useAuthStore()
  const [credits, setCredits]   = useState(null)
  const [plans, setPlans]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [upgrading, setUpgrading] = useState(false)

  useEffect(() => {
    Promise.all([
      api.get('/credits/balance'),
      api.get('/billing/plans'),
    ]).then(([c, p]) => {
      setCredits(c.data)
      setPlans(p.data.plans)
    }).finally(() => setLoading(false))
  }, [])

  const upgrade = async (planId) => {
    if (planId === 'free') return
    setUpgrading(true)
    try {
      const { data } = await api.post('/billing/create-checkout', {
        plan: planId,
        success_url: `${window.location.origin}/billing?upgraded=1`,
        cancel_url: `${window.location.origin}/billing`,
      })
      if (data.checkout_url === 'https://checkout.stripe.com/mock') {
        toast('Stripe not configured — set STRIPE_* env vars to enable payments', { icon: '⚠️', duration: 6000 })
      } else {
        window.location.href = data.checkout_url
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not start checkout')
    } finally {
      setUpgrading(false)
    }
  }

  if (loading) return (
    <div style={{ textAlign: 'center', padding: 60 }}>
      <span className="spinner" style={{ width: 28, height: 28, borderWidth: 3 }} />
    </div>
  )

  const pct = credits ? Math.round((credits.balance / credits.monthly_allocation) * 100) : 0

  return (
    <div className="billing-page fade-in">
      <div className="page-header">
        <h1>Billing & Credits</h1>
        <p>Manage your plan and track credit usage.</p>
      </div>

      {/* Current credits */}
      <div className="credit-detail-card card">
        <div className="credit-detail-header">
          <Zap size={20} className="text-accent" />
          <h3>Credit Balance</h3>
          <span className={`badge badge-${credits?.plan}`}>{(credits?.plan || '').toUpperCase()}</span>
        </div>
        <div className="credit-numbers">
          <div>
            <div style={{ fontSize: '3rem', fontFamily: 'var(--font-display)', fontWeight: 800, color: 'var(--accent)', lineHeight: 1 }}>
              {credits?.balance}
            </div>
            <div className="text-muted text-sm">of {credits?.monthly_allocation} monthly credits remaining</div>
          </div>
          <div className="credit-meta-grid">
            <div><div className="text-dim text-xs">Lifetime used</div><div style={{ fontWeight: 600 }}>{credits?.lifetime_used}</div></div>
            <div><div className="text-dim text-xs">Next reset</div><div style={{ fontWeight: 600 }}>{credits?.next_reset_at ? new Date(credits.next_reset_at).toLocaleDateString() : '—'}</div></div>
          </div>
        </div>
        <div className="score-bar-track" style={{ height: 8, marginTop: 16 }}>
          <div className="score-bar-fill" style={{ width: `${pct}%`, background: pct > 30 ? 'var(--accent)' : 'var(--red)' }} />
        </div>
        <div className="credit-costs-row">
          {credits?.costs && Object.entries(credits.costs).map(([k, v]) => (
            <div key={k} className="cost-item">
              <div className="text-dim text-xs">{k.replace('_', ' ')}</div>
              <div style={{ fontWeight: 600, color: 'var(--accent)' }}>{v}cr</div>
            </div>
          ))}
        </div>
      </div>

      {/* Plans */}
      <h3 style={{ margin: '28px 0 16px' }}>Plans</h3>
      <div className="plans-grid">
        {plans.map((plan) => {
          const isCurrent = credits?.plan === plan.id
          const isPro = plan.id === 'pro'
          return (
            <div key={plan.id} className={`plan-card card ${isPro ? 'plan-pro' : ''} ${isCurrent ? 'plan-current' : ''}`}>
              {isPro && <div className="plan-badge">Most Popular</div>}
              <div className="plan-name">{plan.name}</div>
              <div className="plan-price">
                {plan.price_monthly === 0 ? (
                  <span>Free</span>
                ) : (
                  <><span style={{ fontSize: '2.5rem' }}>${plan.price_monthly}</span><span className="text-muted text-sm">/mo</span></>
                )}
              </div>
              <div className="plan-credits">{plan.credits_monthly} credits/month</div>
              <ul className="plan-features">
                {plan.features.map((f) => (
                  <li key={f}><CheckCircle size={14} style={{ color: 'var(--green)' }} /> {f}</li>
                ))}
              </ul>
              {isCurrent ? (
                <button className="btn btn-ghost w-full" disabled>Current plan</button>
              ) : (
                <button
                  className={`btn w-full ${isPro ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => upgrade(plan.id)}
                  disabled={upgrading || plan.id === 'free'}
                >
                  {upgrading ? <span className="spinner" /> : isPro ? <><CreditCard size={15} /> Upgrade to Pro</> : 'Downgrade'}
                </button>
              )}
            </div>
          )
        })}
      </div>

      {/* Recent transactions */}
      {credits?.recent_transactions?.length > 0 && (
        <div style={{ marginTop: 32 }}>
          <h3 style={{ marginBottom: 14 }}>Recent Transactions</h3>
          <div className="transactions card">
            {credits.recent_transactions.map((t, i) => (
              <div key={i} className="transaction-row">
                <span className="text-sm">{t.reason.replace(/_/g, ' ')}</span>
                <span style={{ color: t.amount > 0 ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>
                  {t.amount > 0 ? '+' : ''}{t.amount} cr
                </span>
                <span className="text-dim text-xs">{new Date(t.created_at).toLocaleDateString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
