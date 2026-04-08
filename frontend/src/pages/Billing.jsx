// src/pages/Billing.jsx — Fixed: no fake features
import { useState, useEffect } from 'react'
import { CheckCircle, Zap, CreditCard } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'
import { useAuthStore } from '../lib/store'
import PromoBox from '../components/PromoBox'
import './Billing.css'

export default function Billing() {
  const { user } = useAuthStore()
  const [credits, setCredits]     = useState(null)
  const [plans, setPlans]         = useState([])
  const [loading, setLoading]     = useState(true)
  const [upgrading, setUpgrading] = useState(false)
  const [cancelled, setCancelled] = useState(
    () => localStorage.getItem('sub_cancelled') === 'true'
  )

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
      localStorage.removeItem('sub_cancelled')
      const userRes = await api.get('/auth/me')
      const { useAuthStore: store } = await import('../lib/store')
      const token = localStorage.getItem('pl_token')
      useAuthStore.getState().setAuth(userRes.data, token)

      const { data } = await api.post('/billing/create-checkout', {
        plan: planId,
        success_url: `${window.location.origin}/billing?upgraded=1`,
        cancel_url:  `${window.location.origin}/billing`,
      })

      if (data.checkout_url === 'https://checkout.stripe.com/mock') {
        toast('Stripe not configured — set STRIPE_* env vars', { icon: '⚠️', duration: 5000 })
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

  const pct = credits
    ? Math.round((credits.balance / credits.monthly_allocation) * 100)
    : 0

  return (
    <div className="billing-page fade-in">
      <div className="page-header">
        <h1>Billing & Credits</h1>
        <p>Manage your plan and track credit usage.</p>
      </div>

      {/* Credit balance */}
      <div className="credit-detail-card card" style={{ marginBottom: 24 }}>
        <div className="credit-detail-header">
          <Zap size={18} />
          <h3>Credit Balance</h3>
          <span className={`badge badge-${credits?.plan}`}>
            {(credits?.plan || '').toUpperCase()}
          </span>
        </div>

        <div className="credit-numbers">
          <div>
            <div style={{
              fontSize: '2.75rem',
              fontFamily: 'var(--font-display)',
              fontWeight: 800,
              color: 'var(--accent)',
              lineHeight: 1,
              letterSpacing: '-0.03em',
            }}>
              {credits?.balance}
            </div>
            <div className="text-muted text-sm" style={{ marginTop: 4 }}>
              of {credits?.monthly_allocation} monthly credits remaining
            </div>
          </div>
          <div className="credit-meta-grid">
            <div>
              <div className="text-dim text-xs">Lifetime used</div>
              <div style={{ fontWeight: 700, marginTop: 2 }}>{credits?.lifetime_used}</div>
            </div>
            <div>
              <div className="text-dim text-xs">Next reset</div>
              <div style={{ fontWeight: 700, marginTop: 2 }}>
                {credits?.next_reset_at
                  ? new Date(credits.next_reset_at).toLocaleDateString()
                  : '—'}
              </div>
            </div>
          </div>
        </div>

        <div className="score-bar-track" style={{ height: 7, margin: '16px 0 12px' }}>
          <div
            className="score-bar-fill"
            style={{
              width: `${pct}%`,
              background: pct > 30 ? 'var(--accent)' : 'var(--red)',
            }}
          />
        </div>

        <div className="credit-costs-row">
          {credits?.costs && Object.entries(credits.costs).map(([k, v]) => (
            <div key={k}>
              <div className="text-dim text-xs" style={{ marginBottom: 2 }}>
                {k.replace(/_/g, ' ')}
              </div>
              <div style={{ fontWeight: 700, color: 'var(--accent)', fontSize: '0.9rem' }}>
                {v} cr
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Plans */}
      <h3 style={{ marginBottom: 14 }}>Plans</h3>
      <div className="plans-grid">
        {plans.map((plan) => {
          const isCurrent = credits?.plan === plan.id
          const isPro     = plan.id === 'pro'
          const isStarter = plan.id === 'starter'

          return (
            <div
              key={plan.id}
              className={`plan-card ${isPro ? 'plan-pro' : ''} ${isCurrent ? 'plan-current' : ''}`}
            >
              {isPro && <div className="plan-badge">Most Popular</div>}

              <div className="plan-name">{plan.name}</div>

              <div className="plan-price">
                {plan.price_monthly === 0
                  ? <span>Free</span>
                  : <><span>${plan.price_monthly}</span><span style={{ fontSize: '0.9rem', fontWeight: 400, color: 'var(--text-2)' }}>/mo</span></>
                }
              </div>

              <div className="plan-credits">{plan.credits_monthly} credits/month</div>

              <ul className="plan-features">
                {plan.features.map((f) => (
                  <li key={f}>
                    <div style={{
                      width: 16, height: 16, borderRadius: '50%',
                      background: 'var(--green-bg)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      flexShrink: 0,
                    }}>
                      <CheckCircle size={10} style={{ color: 'var(--green)' }} />
                    </div>
                    {f}
                  </li>
                ))}
              </ul>

              {isCurrent ? (
                <div>
                  <button className="btn btn-ghost w-full" disabled style={{ marginBottom: 8 }}>
                    Current plan
                  </button>
                  {(isPro || isStarter) && (
                    <CancelButton onCancelled={() => {
                      localStorage.setItem('sub_cancelled', 'true')
                      setCancelled(true)
                    }} />
                  )}
                  {(isPro || isStarter) && cancelled && (
                    <div style={{
                      marginTop: 10, padding: '10px 14px',
                      background: '#fffbeb',
                      border: '1px solid rgba(217,119,6,0.25)',
                      borderRadius: 6, fontSize: '0.8125rem',
                      color: 'var(--orange)',
                    }}>
                      ⚠️ Cancelled — you keep access until end of billing period.
                    </div>
                  )}
                </div>
              ) : (
                <button
                  className={`btn w-full ${isPro || isStarter ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => upgrade(plan.id)}
                  disabled={upgrading || plan.id === 'free'}
                >
                  {upgrading
                    ? <span className="spinner" />
                    : plan.id === 'free'
                      ? 'Free plan'
                      : <><CreditCard size={14} /> Upgrade to {plan.name}</>}
                </button>
              )}
            </div>
          )
        })}
      </div>

      {/* Promo code */}
      <div style={{ marginTop: 28 }}>
        <h3 style={{ marginBottom: 12 }}>Redeem Promo Code</h3>
        <PromoBox />
      </div>

      {/* Transactions */}
      {credits?.recent_transactions?.length > 0 && (
        <div style={{ marginTop: 28 }}>
          <h3 style={{ marginBottom: 12 }}>Recent Transactions</h3>
          <div className="transactions card">
            {credits.recent_transactions.map((t, i) => (
              <div key={i} className="transaction-row">
                <span className="text-sm">{t.reason.replace(/_/g, ' ')}</span>
                <span style={{
                  color: t.amount > 0 ? 'var(--green)' : 'var(--red)',
                  fontWeight: 700,
                  fontSize: '0.875rem',
                }}>
                  {t.amount > 0 ? '+' : ''}{t.amount} cr
                </span>
                <span className="text-dim text-xs">
                  {new Date(t.created_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function CancelButton({ onCancelled }) {
  const [loading, setLoading] = useState(false)

  const cancel = async () => {
    if (!window.confirm('Cancel your subscription? You keep access until end of billing period.')) return
    setLoading(true)
    try {
      await api.post('/billing/cancel')
      toast.success('Cancelled — you keep access until end of billing period')
      if (onCancelled) onCancelled()
      setTimeout(() => window.location.reload(), 1500)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not cancel')
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      className="btn btn-danger w-full"
      style={{ marginTop: 6 }}
      onClick={cancel}
      disabled={loading}
    >
      {loading ? <span className="spinner" /> : 'Cancel subscription'}
    </button>
  )
}
