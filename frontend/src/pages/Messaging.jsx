// src/pages/Messaging.jsx
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Mail, MessageSquare, CheckCircle, Clock, AlertCircle, RefreshCw } from 'lucide-react'
import api from '../lib/api'
import './Messaging.css'

const STATUS_ICON = {
  pending:  <Clock size={14} style={{ color: 'var(--text-3)' }} />,
  sent:     <CheckCircle size={14} style={{ color: 'var(--blue)' }} />,
  opened:   <CheckCircle size={14} style={{ color: 'var(--accent)' }} />,
  replied:  <CheckCircle size={14} style={{ color: 'var(--green)' }} />,
  failed:   <AlertCircle size={14} style={{ color: 'var(--red)' }} />,
}

export default function Messaging() {
  const [tab, setTab] = useState('history')
  const [history, setHistory] = useState([])
  const [sequences, setSequences] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get('/messaging/history'),
      api.get('/messaging/sequences'),
    ]).then(([h, s]) => {
      setHistory(h.data)
      setSequences(s.data)
    }).finally(() => setLoading(false))
  }, [])

  const stats = {
    sent:    history.filter(m => ['sent','opened','replied'].includes(m.status)).length,
    opened:  history.filter(m => m.status === 'opened').length,
    replied: history.filter(m => m.status === 'replied').length,
  }

  return (
    <div className="messaging-page fade-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1>Messaging</h1>
          <p>Track your outreach activity and sequences.</p>
        </div>
        <Link to="/leads" className="btn btn-primary">Send to a lead →</Link>
      </div>

      {/* Stats */}
      <div className="msg-stats">
        {[
          { label: 'Sent',    value: stats.sent,    color: 'var(--blue)'   },
          { label: 'Opened',  value: stats.opened,  color: 'var(--accent)' },
          { label: 'Replied', value: stats.replied, color: 'var(--green)'  },
        ].map(({ label, value, color }) => (
          <div key={label} className="msg-stat card">
            <div style={{ color, fontFamily: 'var(--font-display)', fontSize: '1.75rem', fontWeight: 700 }}>{value}</div>
            <div className="text-muted text-sm">{label}</div>
          </div>
        ))}
      </div>

      <div className="tabs">
        <div className={`tab ${tab === 'history' ? 'active' : ''}`} onClick={() => setTab('history')}>
          Message History
        </div>
        <div className={`tab ${tab === 'sequences' ? 'active' : ''}`} onClick={() => setTab('sequences')}>
          Sequences ({sequences.length})
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <span className="spinner" style={{ width: 28, height: 28, borderWidth: 3 }} />
        </div>
      ) : tab === 'history' ? (
        history.length === 0 ? (
          <div className="empty-state">
            <Mail size={32} className="text-dim" />
            <h3>No messages sent yet</h3>
            <p>Open a lead to send your first outreach message.</p>
          </div>
        ) : (
          <div className="msg-list">
            {history.map((msg) => (
              <div key={msg.id} className="msg-row card">
                <div className="msg-row-icon">
                  {msg.channel === 'email' ? <Mail size={15} className="text-muted" /> : <MessageSquare size={15} className="text-muted" />}
                </div>
                <div className="msg-row-body">
                  <div className="msg-subject">{msg.subject || '(SMS)'}</div>
                  <div className="msg-preview text-dim text-sm">{msg.body}</div>
                </div>
                <div className="msg-row-meta">
                  <div className="msg-status">{STATUS_ICON[msg.status]} {msg.status}</div>
                  {msg.sent_at && (
                    <div className="text-dim text-xs">{new Date(msg.sent_at).toLocaleDateString()}</div>
                  )}
                  <Link to={`/leads/${msg.lead_id}`} className="btn btn-ghost btn-sm">View lead</Link>
                </div>
              </div>
            ))}
          </div>
        )
      ) : (
        sequences.length === 0 ? (
          <div className="empty-state">
            <RefreshCw size={32} className="text-dim" />
            <h3>No sequences yet</h3>
            <p>Sequences let you automate multi-step follow-ups. Coming in a future update for easy setup via the lead page.</p>
          </div>
        ) : (
          <div className="seq-list">
            {sequences.map((seq) => (
              <div key={seq.id} className="seq-row card">
                <div>
                  <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600 }}>{seq.name}</div>
                  <div className="text-dim text-sm">
                    Step {seq.current_step}/{seq.total_steps} ·
                    {seq.sent_count} sent
                    {seq.has_reply && <span className="text-green"> · Got a reply!</span>}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                  <span className={`badge ${seq.status === 'active' ? 'badge-new' : seq.status === 'completed' ? 'badge-closed' : seq.status === 'stopped' ? 'badge-replied' : 'badge-ignored'}`}>
                    {seq.status}
                  </span>
                  <Link to={`/leads/${seq.lead_id}`} className="btn btn-ghost btn-sm">View lead</Link>
                </div>
              </div>
            ))}
          </div>
        )
      )}
    </div>
  )
}
