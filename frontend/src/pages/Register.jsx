// src/pages/Register.jsx
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Zap } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'
import { useAuthStore } from '../lib/store'
import './Auth.css'

export default function Register() {
  const [form, setForm] = useState({ email: '', password: '', full_name: '' })
  const [loading, setLoading] = useState(false)
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  const handle = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    if (form.password.length < 8) return toast.error('Password must be at least 8 characters')
    setLoading(true)
    try {
      const { data } = await api.post('/auth/register', form)
      setAuth(data.user, data.access_token)
      toast.success(`Welcome to PitchLab, ${data.user.full_name || 'friend'}! 🎉`)
      navigate('/')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card fade-in">
        <div className="auth-logo">
          <Zap size={24} />
          <span>PitchLab</span>
        </div>
        <h2>Start for free</h2>
        <p className="auth-sub">Find leads and close deals faster</p>

        <div className="auth-perks">
          {['25 free credits', 'Lead finder', 'AI pitch generator', 'Email outreach'].map((p) => (
            <span key={p} className="perk">✓ {p}</span>
          ))}
        </div>

        <form onSubmit={submit}>
          <div className="form-group">
            <label>Your name</label>
            <input className="input" name="full_name" value={form.full_name}
              onChange={handle} placeholder="Brandon" required />
          </div>
          <div className="form-group">
            <label>Email</label>
            <input className="input" name="email" type="email" value={form.email}
              onChange={handle} placeholder="you@example.com" required />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input className="input" name="password" type="password" value={form.password}
              onChange={handle} placeholder="8+ characters" minLength={8} required />
          </div>
          <button className="btn btn-primary w-full btn-lg" disabled={loading}>
            {loading ? <span className="spinner" /> : 'Create free account'}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
