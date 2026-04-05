// src/components/Layout.jsx
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../lib/store'
import {
  LayoutDashboard, Search, Users, Mail,
  CreditCard, LogOut, Zap
} from 'lucide-react'
import './Layout.css'

const NAV = [
  { to: '/',          icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/find',      icon: Search,          label: 'Find Leads' },
  { to: '/leads',     icon: Users,           label: 'My Leads' },
  { to: '/messaging', icon: Mail,            label: 'Messaging' },
  { to: '/billing',   icon: CreditCard,      label: 'Billing' },
]

export default function Layout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <Zap size={20} className="logo-icon" />
          <span>PitchLab</span>
        </div>

        <nav className="sidebar-nav">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <Icon size={17} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-info">
            <div className="user-avatar">
              {(user?.full_name || user?.email || 'U')[0].toUpperCase()}
            </div>
            <div className="user-meta">
              <div className="user-name">{user?.full_name || 'User'}</div>
              <div className={`badge badge-${user?.plan || 'free'}`}>
                {(user?.plan || 'free').toUpperCase()}
              </div>
            </div>
          </div>
          <button className="logout-btn" onClick={handleLogout} title="Logout">
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
