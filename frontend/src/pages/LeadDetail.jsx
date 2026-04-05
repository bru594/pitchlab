// src/pages/LeadDetail.jsx
import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Globe, Phone, MapPin, Star, Zap,
  Copy, Mail, MessageSquare, PhoneCall, RefreshCw,
  CheckCircle, AlertTriangle, AlertCircle, Info, Send
} from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'
import './LeadDetail.css'

const STATUS_OPTIONS = ['new', 'contacted', 'replied', 'closed', 'ignored']

export default function LeadDetail() {
  const { id } = useParams()
  const navigate = useNavigate()

  const [lead, setLead]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab]         = useState('audit')   // audit | pitch | send

  const [auditing, setAuditing]   = useState(false)
  const [pitching, setPitching]   = useState(false)
  const [sending, setSending]     = useState(false)
  const [sendForm, setSendForm]   = useState({ channel: 'email', subject: '', body: '', to_address: '' })

  const loadLead = useCallback(async () => {
    try {
      const { data } = await api.get(`/leads/${id}`)
      setLead(data)
    } catch {
      toast.error('Lead not found')
      navigate('/leads')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { loadLead() }, [loadLead])

  const runAudit = async () => {
    setAuditing(true)
    try {
      await api.post(`/audits/${id}/run`)
      await loadLead()
      toast.success('Audit complete!')
      setTab('audit')
    } catch (err) {
      if (err.response?.status !== 402)
        toast.error(err.response?.data?.detail || 'Audit failed')
    } finally {
      setAuditing(false)
    }
  }

  const generatePitch = async () => {
    if (!lead?.audit) return toast.error('Run an audit first')
    setPitching(true)
    try {
      await api.post(`/pitches/${id}/generate`)
      await loadLead()
      toast.success('Pitches generated!')
      setTab('pitch')
    } catch (err) {
      if (err.response?.status !== 402)
        toast.error(err.response?.data?.detail || 'Generation failed')
    } finally {
      setPitching(false)
    }
  }

  const updateStatus = async (status) => {
    try {
      await api.patch(`/leads/${id}/status`, { status })
      setLead((l) => ({ ...l, status }))
      toast.success(`Status → ${status}`)
    } catch {
      toast.error('Failed to update status')
    }
  }

  const sendMessage = async (e) => {
    e.preventDefault()
    setSending(true)
    try {
      await api.post('/messaging/send', { lead_id: Number(id), ...sendForm })
      toast.success('Message sent!')
      setSendForm((f) => ({ ...f, body: '', subject: '' }))
      updateStatus('contacted')
    } catch (err) {
      if (err.response?.status !== 402)
        toast.error(err.response?.data?.detail || 'Send failed')
    } finally {
      setSending(false)
    }
  }

  const copyText = (text) => {
    navigator.clipboard.writeText(text)
    toast.success('Copied to clipboard')
  }

  const fillFromPitch = (type) => {
    const pitch = lead?.pitches?.[0]
    if (!pitch) return
    if (type === 'email') {
      const lines = (pitch.cold_email || '').split('\n')
      const subjectLine = lines[0]?.replace('Subject:', '').trim() || ''
      const body = lines.slice(2).join('\n').trim()
      setSendForm((f) => ({ ...f, channel: 'email', subject: subjectLine, body }))
    } else if (type === 'sms') {
      setSendForm((f) => ({ ...f, channel: 'sms', body: pitch.sms || '' }))
    }
    setTab('send')
  }

  if (loading) return (
    <div style={{ padding: 60, textAlign: 'center' }}>
      <span className="spinner" style={{ width: 32, height: 32, borderWidth: 3 }} />
    </div>
  )

  const audit  = lead?.audit
  const pitch  = lead?.pitches?.[0]
  const score  = audit?.score ?? null

  const scoreColor = (s) => s >= 70 ? 'var(--green)' : s >= 40 ? 'var(--orange)' : 'var(--red)'
  const scoreGrade = (s) => s >= 80 ? 'A' : s >= 65 ? 'B' : s >= 50 ? 'C' : s >= 35 ? 'D' : 'F'

  return (
    <div className="lead-detail fade-in">
      {/* Back nav */}
      <button className="btn btn-ghost btn-sm back-btn" onClick={() => navigate('/leads')}>
        <ArrowLeft size={15} /> Back to leads
      </button>

      {/* Header */}
      <div className="detail-header">
        <div className="detail-header-left">
          <h1>{lead.business_name}</h1>
          <div className="detail-meta">
            {lead.phone    && <span><Phone size={13} /> {lead.phone}</span>}
            {lead.address  && <span><MapPin size={13} /> {lead.address}</span>}
            {lead.website  && <a href={lead.website} target="_blank" rel="noreferrer"><Globe size={13} /> {lead.website}</a>}
            {lead.rating   && <span><Star size={13} style={{ color: 'var(--accent)' }} /> {lead.rating} ({lead.review_count} reviews)</span>}
            {!lead.has_website && <span className="text-orange"><AlertCircle size={13} /> No website</span>}
          </div>
        </div>
        <div className="detail-header-right">
          <select className="select" style={{ width: 130 }} value={lead.status}
            onChange={(e) => updateStatus(e.target.value)}>
            {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      {/* Action bar */}
      <div className="action-bar">
        <button className="btn btn-secondary" onClick={runAudit} disabled={auditing}>
          {auditing ? <span className="spinner" /> : <RefreshCw size={15} />}
          {audit ? 'Re-run Audit' : 'Run Audit'} <span className="credit-cost">3cr</span>
        </button>
        <button className="btn btn-secondary" onClick={generatePitch} disabled={pitching || !audit}>
          {pitching ? <span className="spinner" /> : <Zap size={15} />}
          {pitch ? 'Regenerate Pitch' : 'Generate Pitch'} <span className="credit-cost">2cr</span>
        </button>
        {pitch && (
          <>
            <button className="btn btn-ghost btn-sm" onClick={() => fillFromPitch('email')}>
              <Mail size={14} /> Use Email Pitch
            </button>
            <button className="btn btn-ghost btn-sm" onClick={() => fillFromPitch('sms')}>
              <MessageSquare size={14} /> Use SMS Pitch
            </button>
          </>
        )}
      </div>

      {/* Tabs */}
      <div className="tabs">
        {[
          { id: 'audit', label: 'Audit Results', done: !!audit },
          { id: 'pitch', label: 'AI Pitches',    done: !!pitch },
          { id: 'send',  label: 'Send Message',  done: false },
        ].map(({ id: tid, label, done }) => (
          <div
            key={tid}
            className={`tab ${tab === tid ? 'active' : ''}`}
            onClick={() => setTab(tid)}
          >
            {done && <CheckCircle size={12} style={{ color: 'var(--green)', marginRight: 5 }} />}
            {label}
          </div>
        ))}
      </div>

      {/* ── AUDIT TAB ───────────────────────────────────────────── */}
      {tab === 'audit' && (
        <div className="tab-content fade-in">
          {!audit ? (
            <div className="empty-state">
              <RefreshCw size={32} className="text-dim" />
              <h3>No audit yet</h3>
              <p>Click "Run Audit" to analyze this business's online presence.</p>
              <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={runAudit} disabled={auditing}>
                {auditing ? <span className="spinner" /> : 'Run Audit (3 credits)'}
              </button>
            </div>
          ) : (
            <>
              {/* Overall score */}
              <div className="audit-score-row">
                <div className="score-ring" style={{ '--score-color': scoreColor(score) }}>
                  <div className="score-ring-value">{score}</div>
                  <div className="score-ring-grade">{scoreGrade(score)}</div>
                </div>
                <div className="sub-scores">
                  {[
                    { label: 'Speed',  value: audit.speed_score  },
                    { label: 'Mobile', value: audit.mobile_score },
                    { label: 'SEO',    value: audit.seo_score    },
                    { label: 'Design', value: audit.design_score },
                  ].map(({ label, value }) => (
                    <div key={label} className="sub-score">
                      <div className="sub-score-label">{label}</div>
                      <div className="score-bar-track" style={{ flex: 1 }}>
                        <div className="score-bar-fill"
                          style={{ width: `${value}%`, background: scoreColor(value) }} />
                      </div>
                      <div className="sub-score-val" style={{ color: scoreColor(value) }}>{value}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Sales summary */}
              {audit.sales_summary && (
                <div className="sales-summary card">
                  <div className="sales-summary-header">
                    <Zap size={16} className="text-accent" />
                    <span>Sales Summary</span>
                    <button className="btn btn-ghost btn-sm" style={{ marginLeft: 'auto' }}
                      onClick={() => copyText(audit.sales_summary)}>
                      <Copy size={13} /> Copy
                    </button>
                  </div>
                  <pre className="sales-summary-text">{audit.sales_summary}</pre>
                </div>
              )}

              {/* Issues */}
              {audit.issues?.length > 0 && (
                <div className="issues-list">
                  <h3 style={{ marginBottom: 12 }}>Issues Found ({audit.issues.length})</h3>
                  {audit.issues.map((issue, i) => (
                    <IssueRow key={i} issue={issue} />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── PITCH TAB ───────────────────────────────────────────── */}
      {tab === 'pitch' && (
        <div className="tab-content fade-in">
          {!pitch ? (
            <div className="empty-state">
              <Zap size={32} className="text-dim" />
              <h3>No pitch generated yet</h3>
              <p>{!audit ? 'Run an audit first, then generate pitches.' : 'Generate AI pitches based on the audit results.'}</p>
              <button className="btn btn-primary" style={{ marginTop: 16 }}
                onClick={generatePitch} disabled={pitching || !audit}>
                {pitching ? <span className="spinner" /> : 'Generate Pitches (2 credits)'}
              </button>
            </div>
          ) : (
            <div className="pitches">
              <PitchBlock
                icon={<Mail size={16} />}
                label="Cold Email"
                content={pitch.cold_email}
                onCopy={() => copyText(pitch.cold_email)}
                onUse={() => fillFromPitch('email')}
                useLabel="Use in Send"
              />
              <PitchBlock
                icon={<PhoneCall size={16} />}
                label="Cold Call Script"
                content={pitch.cold_call}
                onCopy={() => copyText(pitch.cold_call)}
              />
              <PitchBlock
                icon={<MessageSquare size={16} />}
                label="SMS"
                content={pitch.sms}
                onCopy={() => copyText(pitch.sms)}
                onUse={() => fillFromPitch('sms')}
                useLabel="Use in Send"
              />
            </div>
          )}
        </div>
      )}

      {/* ── SEND TAB ────────────────────────────────────────────── */}
      {tab === 'send' && (
        <div className="tab-content fade-in">
          <form onSubmit={sendMessage} className="send-form">
            <div className="form-row">
              <div className="form-group">
                <label>Channel</label>
                <select className="select" value={sendForm.channel}
                  onChange={(e) => setSendForm((f) => ({ ...f, channel: e.target.value }))}>
                  <option value="email">Email</option>
                  <option value="sms">SMS</option>
                </select>
              </div>
              <div className="form-group">
                <label>To {sendForm.channel === 'email' ? 'email address' : 'phone number'}</label>
                <input className="input" value={sendForm.to_address}
                  onChange={(e) => setSendForm((f) => ({ ...f, to_address: e.target.value }))}
                  placeholder={sendForm.channel === 'email' ? 'owner@business.com' : '+1 (555) 000-0000'}
                />
              </div>
            </div>
            {sendForm.channel === 'email' && (
              <div className="form-group">
                <label>Subject line</label>
                <input className="input" value={sendForm.subject}
                  onChange={(e) => setSendForm((f) => ({ ...f, subject: e.target.value }))}
                  placeholder="Quick question about your website…" />
              </div>
            )}
            <div className="form-group">
              <label>Message body</label>
              <textarea className="textarea" rows={8} value={sendForm.body}
                onChange={(e) => setSendForm((f) => ({ ...f, body: e.target.value }))}
                placeholder="Write your message here, or use a pitch above to auto-fill…"
                required />
            </div>
            <div className="send-form-footer">
              <span className="text-dim text-xs"><Info size={12} /> Costs 1 credit per send</span>
              <button className="btn btn-primary" disabled={sending || !sendForm.body.trim()}>
                {sending ? <span className="spinner" /> : <><Send size={15} /> Send Message</>}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}

// ── Sub-components ──────────────────────────────────────────────────

function IssueRow({ issue }) {
  const Icon = issue.severity === 'critical' ? AlertCircle
             : issue.severity === 'warning'  ? AlertTriangle
             : Info
  const color = issue.severity === 'critical' ? 'var(--red)'
              : issue.severity === 'warning'  ? 'var(--orange)'
              : 'var(--text-3)'
  return (
    <div className="issue-row">
      <Icon size={15} style={{ color, flexShrink: 0 }} />
      <span>{issue.message}</span>
    </div>
  )
}

function PitchBlock({ icon, label, content, onCopy, onUse, useLabel }) {
  const [expanded, setExpanded] = useState(true)
  return (
    <div className="pitch-block card">
      <div className="pitch-block-header">
        <div className="pitch-block-title">{icon} {label}</div>
        <div style={{ display: 'flex', gap: 8 }}>
          {onUse && (
            <button className="btn btn-secondary btn-sm" onClick={onUse}>
              <Send size={13} /> {useLabel}
            </button>
          )}
          <button className="btn btn-ghost btn-sm" onClick={onCopy}>
            <Copy size={13} /> Copy
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => setExpanded(!expanded)}>
            {expanded ? '▲' : '▼'}
          </button>
        </div>
      </div>
      {expanded && <pre className="pitch-content">{content}</pre>}
    </div>
  )
}
