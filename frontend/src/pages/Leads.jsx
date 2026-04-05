// src/pages/Leads.jsx
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Star, Globe, AlertCircle, MapPin, Filter } from 'lucide-react'
import api from '../lib/api'
import './Leads.css'

const STATUS_COLORS = {
  new: 'badge-new', contacted: 'badge-contacted',
  replied: 'badge-replied', closed: 'badge-closed', ignored: 'badge-ignored',
}

export default function Leads() {
  const [leads, setLeads] = useState([])
  const [total, setTotal]  = useState(0)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState({ status: '', has_website: '', page: 1 })

  const load = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ per_page: 30, page: filter.page })
      if (filter.status) params.set('status', filter.status)
      if (filter.has_website !== '') params.set('has_website', filter.has_website)
      const { data } = await api.get(`/leads/?${params}`)
      setLeads(data.leads)
      setTotal(data.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [filter])

  return (
    <div className="leads-page fade-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1>My Leads <span className="text-dim text-sm">({total})</span></h1>
          <p>All saved leads. Click any to audit, pitch, and reach out.</p>
        </div>
        <Link to="/find" className="btn btn-primary">+ Find More</Link>
      </div>

      {/* Filters */}
      <div className="leads-filters">
        <Filter size={14} className="text-dim" />
        <select className="select" style={{ width: 140 }}
          value={filter.status} onChange={(e) => setFilter((f) => ({ ...f, status: e.target.value, page: 1 }))}>
          <option value="">All statuses</option>
          <option value="new">New</option>
          <option value="contacted">Contacted</option>
          <option value="replied">Replied</option>
          <option value="closed">Closed</option>
          <option value="ignored">Ignored</option>
        </select>
        <select className="select" style={{ width: 150 }}
          value={filter.has_website} onChange={(e) => setFilter((f) => ({ ...f, has_website: e.target.value, page: 1 }))}>
          <option value="">All leads</option>
          <option value="false">No website</option>
          <option value="true">Has website</option>
        </select>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-2)' }}>
          <span className="spinner" style={{ width: 28, height: 28, borderWidth: 3 }} />
        </div>
      ) : leads.length === 0 ? (
        <div className="empty-state">
          <h3>No leads yet</h3>
          <p>Use the Lead Finder to discover local businesses.</p>
          <Link to="/find" className="btn btn-primary" style={{ marginTop: 16 }}>Find Leads →</Link>
        </div>
      ) : (
        <div className="leads-table">
          <div className="leads-table-head">
            <span>Business</span>
            <span>Location</span>
            <span>Rating</span>
            <span>Website</span>
            <span>Status</span>
            <span>Audit</span>
            <span />
          </div>
          {leads.map((lead) => (
            <Link key={lead.id} to={`/leads/${lead.id}`} className="leads-table-row">
              <span className="lead-biz-name">{lead.business_name}</span>
              <span className="text-dim text-sm"><MapPin size={11} /> {lead.city}, {lead.state}</span>
              <span>
                {lead.rating
                  ? <span className="text-sm"><Star size={11} style={{ color: 'var(--accent)' }} /> {lead.rating}</span>
                  : <span className="text-dim text-sm">—</span>}
              </span>
              <span>
                {lead.has_website
                  ? <span className="meta-chip"><Globe size={11} /> Site</span>
                  : <span className="meta-chip no-site"><AlertCircle size={11} /> None</span>}
              </span>
              <span><span className={`badge ${STATUS_COLORS[lead.status] || 'badge-new'}`}>{lead.status}</span></span>
              <span>
                {lead.has_audit
                  ? <span className="text-green text-xs">✓ Done</span>
                  : <span className="text-dim text-xs">Pending</span>}
              </span>
              <span className="text-accent text-sm">Open →</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
