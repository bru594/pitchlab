// src/pages/LeadFinder.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, MapPin, Filter, ExternalLink, Phone, Star, Globe, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'
import './LeadFinder.css'

const NICHES = [
  'Plumber', 'Electrician', 'Roofer', 'HVAC', 'Landscaper',
  'Painter', 'Contractor', 'Dentist', 'Chiropractor', 'Auto Repair',
  'Restaurant', 'Locksmith', 'Pest Control', 'Moving Company', 'Photographer',
]

export default function LeadFinder() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    location: '',
    niche: '',
    max_results: 20,
    no_website_only: false,
    poor_website_only: false,
    low_reviews_only: false,
  })
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [showFilters, setShowFilters] = useState(false)

  const handle = (e) => {
    const { name, value, type, checked } = e.target
    setForm((f) => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }

  const search = async (e) => {
    e.preventDefault()
    if (!form.location.trim()) return toast.error('Enter a location')
    if (!form.niche.trim()) return toast.error('Select a business type')

    setLoading(true)
    setResults(null)
    try {
      const { data } = await api.post('/leads/search', form)
      setResults(data)
      if (data.saved === 0 && data.found > 0) {
        toast('All found leads are already in your list', { icon: 'ℹ️' })
      } else if (data.saved > 0) {
        toast.success(`${data.saved} new leads added to your list`)
      }
    } catch (err) {
      if (err.response?.status !== 402) {
        toast.error(err.response?.data?.detail || 'Search failed')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="lead-finder fade-in">
      <div className="page-header">
        <h1>Find Leads</h1>
        <p>Search for local businesses that need a better website.</p>
      </div>

      {/* Search form */}
      <div className="search-card card">
        <form onSubmit={search}>
          <div className="search-main-row">
            <div className="form-group" style={{ flex: 2 }}>
              <label><MapPin size={13} style={{ marginRight: 5 }} />Location</label>
              <input
                className="input"
                name="location"
                value={form.location}
                onChange={handle}
                placeholder="e.g. Haverhill, MA or North Shore Boston"
                required
              />
            </div>
            <div className="form-group" style={{ flex: 1.5 }}>
              <label><Search size={13} style={{ marginRight: 5 }} />Business Type</label>
              <select className="select" name="niche" value={form.niche} onChange={handle} required>
                <option value="">Select niche…</option>
                {NICHES.map((n) => <option key={n} value={n.toLowerCase()}>{n}</option>)}
                <option value="">──</option>
                <option value="custom">Custom…</option>
              </select>
            </div>
            {form.niche === 'custom' && (
              <div className="form-group" style={{ flex: 1.5 }}>
                <label>Custom niche</label>
                <input className="input" name="niche" placeholder="e.g. tattoo shop"
                  onChange={handle} />
              </div>
            )}
            <div className="search-btn-wrap">
              <button className="btn btn-primary btn-lg" disabled={loading} type="submit">
                {loading ? <span className="spinner" /> : <><Search size={16} /> Search</>}
              </button>
            </div>
          </div>

          {/* Filters toggle */}
          <div className="filter-toggle" onClick={() => setShowFilters(!showFilters)}>
            <Filter size={14} />
            <span>Filters {showFilters ? '▲' : '▼'}</span>
            {(form.no_website_only || form.poor_website_only || form.low_reviews_only) && (
              <span className="filter-active-dot" />
            )}
          </div>

          {showFilters && (
            <div className="filters-row fade-in">
              <label className="checkbox-label">
                <input type="checkbox" name="no_website_only" checked={form.no_website_only} onChange={handle} />
                No website only
              </label>
              <label className="checkbox-label">
                <input type="checkbox" name="poor_website_only" checked={form.poor_website_only} onChange={handle} />
                Poor/cheap website
              </label>
              <label className="checkbox-label">
                <input type="checkbox" name="low_reviews_only" checked={form.low_reviews_only} onChange={handle} />
                Low reviews / rating
              </label>
              <div style={{ marginLeft: 'auto' }}>
                <label style={{ marginBottom: 0, display: 'inline' }}>Max results: </label>
                <select className="select" style={{ width: 80, display: 'inline-block', marginLeft: 8 }}
                  name="max_results" value={form.max_results} onChange={handle}>
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                </select>
              </div>
            </div>
          )}
        </form>
      </div>

      {/* Cost hint */}
      <div className="cost-hint text-xs text-dim">
        <AlertCircle size={12} /> Each search costs 5 credits · Results are saved to My Leads
      </div>

      {/* Results */}
      {loading && (
        <div className="search-loading">
          <span className="spinner" style={{ width: 28, height: 28, borderWidth: 3 }} />
          <p>Searching {form.niche}s in {form.location}…</p>
        </div>
      )}

      {results && !loading && (
        <div className="results fade-in">
          <div className="results-header">
            <h3>{results.found} leads found · {results.saved} new</h3>
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/leads')}>
              View all my leads →
            </button>
          </div>

          <div className="leads-list">
            {results.leads.length === 0 ? (
              <div className="empty-state">
                <p>All results already in your leads list, or no new matches.</p>
              </div>
            ) : (
              results.leads.map((lead) => (
                <LeadRow key={lead.id} lead={lead} onView={() => navigate(`/leads/${lead.id}`)} />
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function LeadRow({ lead, onView }) {
  return (
    <div className="lead-row card card-hover">
      <div className="lead-row-main">
        <div>
          <div className="lead-name">{lead.business_name}</div>
          <div className="lead-address text-dim text-sm">
            <MapPin size={12} /> {lead.address || `${lead.city}, ${lead.state}`}
          </div>
        </div>
        <div className="lead-meta">
          {lead.rating && (
            <span className="meta-chip"><Star size={12} /> {lead.rating} ({lead.review_count})</span>
          )}
          {lead.phone && (
            <span className="meta-chip"><Phone size={12} /> {lead.phone}</span>
          )}
          <span className={`meta-chip ${lead.has_website ? '' : 'no-site'}`}>
            {lead.has_website ? <><Globe size={12} /> Has site</> : <><AlertCircle size={12} /> No website</>}
          </span>
        </div>
      </div>
      <div className="lead-row-actions">
        {lead.website && (
          <a href={lead.website} target="_blank" rel="noreferrer" className="btn btn-ghost btn-sm">
            <ExternalLink size={13} />
          </a>
        )}
        <button className="btn btn-secondary btn-sm" onClick={onView}>
          Open →
        </button>
      </div>
    </div>
  )
}
