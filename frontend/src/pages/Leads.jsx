// src/pages/Leads.jsx — Fixed spreadsheet table
import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Star, Globe, AlertCircle, MapPin, Search, Trash2, ChevronDown } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'
import './Leads.css'

export default function Leads() {
  const navigate = useNavigate()
  const [leads, setLeads]       = useState([])
  const [total, setTotal]       = useState(0)
  const [loading, setLoading]   = useState(true)
  const [selected, setSelected] = useState(new Set())
  const [search, setSearch]     = useState('')
  const [filter, setFilter]     = useState({ status: 'all', website: 'all', page: 1 })
  const [deleting, setDeleting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ per_page: 50, page: filter.page })
      if (filter.status !== 'all') params.set('status', filter.status)
      if (filter.website === 'no_website') params.set('has_website', 'false')
      if (filter.website === 'has_website') params.set('has_website', 'true')
      const { data } = await api.get(`/leads/?${params}`)
      setLeads(data.leads)
      setTotal(data.total)
      setSelected(new Set())
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => { load() }, [load])

  const filtered = leads.filter(l =>
    !search ||
    l.business_name.toLowerCase().includes(search.toLowerCase()) ||
    (l.city || '').toLowerCase().includes(search.toLowerCase())
  )

  const allSelected = filtered.length > 0 && filtered.every(l => selected.has(l.id))

  const toggleAll = () => {
    if (allSelected) setSelected(new Set())
    else setSelected(new Set(filtered.map(l => l.id)))
  }

  const toggleOne = (id) => {
    const next = new Set(selected)
    next.has(id) ? next.delete(id) : next.add(id)
    setSelected(next)
  }

  const deleteSelected = async () => {
    if (selected.size === 0) return
    if (!window.confirm(`Delete ${selected.size} lead${selected.size > 1 ? 's' : ''}? This cannot be undone.`)) return
    setDeleting(true)
    try {
      await Promise.all([...selected].map(id => api.delete(`/leads/${id}`)))
      toast.success(`Deleted ${selected.size} lead${selected.size > 1 ? 's' : ''}`)
      load()
    } catch {
      toast.error('Failed to delete some leads')
    } finally {
      setDeleting(false)
    }
  }

  const deleteOne = async (e, id) => {
    e.stopPropagation()
    e.preventDefault()
    if (!window.confirm('Delete this lead?')) return
    try {
      await api.delete(`/leads/${id}`)
      setLeads(prev => prev.filter(l => l.id !== id))
      setTotal(t => t - 1)
      toast.success('Lead deleted')
    } catch {
      toast.error('Failed to delete')
    }
  }

  const updateStatus = async (e, id, status) => {
    e.stopPropagation()
    try {
      await api.patch(`/leads/${id}/status`, { status })
      setLeads(prev => prev.map(l => l.id === id ? { ...l, status } : l))
    } catch {
      toast.error('Failed to update status')
    }
  }

  return (
    <div className="leads-page fade-in">
      {/* Header */}
      <div className="leads-header">
        <div>
          <h1>My Leads <span className="leads-count">{total}</span></h1>
          <p>Click any lead to audit, pitch, and reach out.</p>
        </div>
        <Link to="/find" className="btn btn-primary">+ Find More</Link>
      </div>

      {/* Toolbar */}
      <div className="leads-toolbar">
        <div className="leads-search-wrap">
          <Search size={14} className="search-icon" />
          <input
            className="leads-search"
            placeholder="Search by name or city…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        <div className="filter-select-wrap">
          <select
            className="filter-select"
            value={filter.status}
            onChange={e => setFilter(f => ({ ...f, status: e.target.value, page: 1 }))}
          >
            <option value="all">All statuses</option>
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="replied">Replied</option>
            <option value="closed">Closed</option>
            <option value="ignored">Ignored</option>
          </select>
          <ChevronDown size={12} className="filter-chevron" />
        </div>

        <div className="filter-select-wrap">
          <select
            className="filter-select"
            value={filter.website}
            onChange={e => setFilter(f => ({ ...f, website: e.target.value, page: 1 }))}
          >
            <option value="all">All leads</option>
            <option value="no_website">No website</option>
            <option value="has_website">Has website</option>
          </select>
          <ChevronDown size={12} className="filter-chevron" />
        </div>

        {selected.size > 0 && (
          <button className="btn btn-danger btn-sm" onClick={deleteSelected} disabled={deleting}>
            <Trash2 size={13} />
            Delete {selected.size}
          </button>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <div className="leads-loading">
          <span className="spinner" style={{ width: 26, height: 26, borderWidth: 3 }} />
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <h3>{search ? 'No results found' : 'No leads yet'}</h3>
          <p>{search ? 'Try a different search term.' : 'Use the Lead Finder to discover local businesses.'}</p>
          {!search && <Link to="/find" className="btn btn-primary" style={{ marginTop: 16 }}>Find Leads →</Link>}
        </div>
      ) : (
        <div className="leads-table-wrap">
          <table className="leads-table">
            <thead>
              <tr>
                <th style={{ width: 44, paddingLeft: 16 }}>
                  <input type="checkbox" checked={allSelected} onChange={toggleAll} />
                </th>
                <th>Business</th>
                <th>Location</th>
                <th>Rating</th>
                <th>Website</th>
                <th>Status</th>
                <th>Audit</th>
                <th style={{ width: 44 }} />
              </tr>
            </thead>
            <tbody>
              {filtered.map(lead => (
                <tr
                  key={lead.id}
                  className={`lead-row ${selected.has(lead.id) ? 'row-selected' : ''}`}
                  onClick={() => navigate(`/leads/${lead.id}`)}
                >
                  <td style={{ paddingLeft: 16 }} onClick={e => { e.stopPropagation(); toggleOne(lead.id) }}>
                    <input type="checkbox" checked={selected.has(lead.id)} onChange={() => {}} />
                  </td>

                  <td>
                    <div className="lead-name">{lead.business_name}</div>
                    {lead.niche && <div className="lead-niche">{lead.niche}</div>}
                  </td>

                  <td>
                    <div className="lead-location">
                      <MapPin size={11} />
                      {lead.city}{lead.state ? `, ${lead.state}` : ''}
                    </div>
                  </td>

                  <td>
                    {lead.rating ? (
                      <div className="lead-rating">
                        <Star size={11} />
                        {lead.rating}
                        <span className="rating-count">({lead.review_count})</span>
                      </div>
                    ) : <span className="text-dim">—</span>}
                  </td>

                  <td>
                    {lead.has_website
                      ? <span className="site-badge has-site"><Globe size={11} /> Site</span>
                      : <span className="site-badge no-site"><AlertCircle size={11} /> None</span>}
                  </td>

                  <td onClick={e => e.stopPropagation()}>
                    <select
                      className={`status-select status-${lead.status}`}
                      value={lead.status}
                      onChange={e => updateStatus(e, lead.id, e.target.value)}
                    >
                      <option value="new">New</option>
                      <option value="contacted">Contacted</option>
                      <option value="replied">Replied</option>
                      <option value="closed">Closed</option>
                      <option value="ignored">Ignored</option>
                    </select>
                  </td>

                  <td>
                    {lead.has_audit
                      ? <span className="audit-done">✓ Done</span>
                      : <span className="audit-pending">Pending</span>}
                  </td>

                  <td onClick={e => e.stopPropagation()}>
                    <button className="delete-btn" onClick={e => deleteOne(e, lead.id)} title="Delete">
                      <Trash2 size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
