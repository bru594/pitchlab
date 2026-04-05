import { useState } from 'react'
import { Gift } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'

export default function PromoBox() {
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)

  const redeem = async (e) => {
    e.preventDefault()
    if (!code.trim()) return
    setLoading(true)
    try {
      const { data } = await api.post('/promos/redeem', { code })
      toast.success(data.message)
      setCode('')
      setTimeout(() => window.location.reload(), 1500)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Invalid code')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card" style={{ maxWidth: 400 }}>
      <form onSubmit={redeem} style={{ display: 'flex', gap: 10 }}>
        <input
          className="input"
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          placeholder="Enter promo code"
          style={{ flex: 1 }}
        />
        <button className="btn btn-primary" disabled={loading}>
          {loading ? <span className="spinner" /> : <><Gift size={15} /> Redeem</>}
        </button>
      </form>
    </div>
  )
}
