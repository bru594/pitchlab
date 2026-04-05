// src/pages/Login.jsx
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Zap } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'
import { useAuthStore } from '../lib/store'
import './Auth.css'

export default function Login() {
  const [form, setForm] = useState({ email: '', password: '' })
  const [loading, setLoading] = useState(false)
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  const handle = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const { data } = await api.post('/auth/login', form)
      setAuth(data.user, data.access_token)
      navigate('/')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Login failed')
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
        <h2>Welcome back</h2>
        <p className="auth-sub">Sign in to your account</p>

        <form onSubmit={submit}>
          <div className="form-group">
            <label>Email</label>
            <input className="input" name="email" type="email" value={form.email}
              onChange={handle} placeholder="you@example.com" required />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input className="input" name="password" type="password" value={form.password}
              onChange={handle} placeholder="••••••••" required />
          </div>
          <button className="btn btn-primary w-full btn-lg" disabled={loading}>
            {loading ? <span className="spinner" /> : 'Sign in'}
          </button>
        </form>

        <p className="auth-switch">
          Don't have an account? <Link to="/register">Create one free</Link>
        </p>
      </div>

      <div className="auth-demo-note">
        <strong>Demo:</strong> Register with any email to try the platform
      </div>
    </div>
  )
}
