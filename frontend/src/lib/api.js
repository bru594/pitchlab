// src/lib/api.js — Axios instance with auth interceptors
import axios from 'axios'
import toast from 'react-hot-toast'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('pl_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Handle auth errors globally
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('pl_token')
      localStorage.removeItem('pl_user')
      window.location.href = '/login'
    }
    if (err.response?.status === 402) {
      toast.error('Not enough credits. Upgrade your plan or wait for monthly reset.')
    }
    return Promise.reject(err)
  }
)

export default api
