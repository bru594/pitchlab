// src/lib/store.js — Zustand global state
import { create } from 'zustand'

export const useAuthStore = create((set) => ({
  user: JSON.parse(localStorage.getItem('pl_user') || 'null'),
  token: localStorage.getItem('pl_token') || null,

  setAuth: (user, token) => {
    localStorage.setItem('pl_token', token)
    localStorage.setItem('pl_user', JSON.stringify(user))
    set({ user, token })
  },

  logout: () => {
    localStorage.removeItem('pl_token')
    localStorage.removeItem('pl_user')
    set({ user: null, token: null })
  },
}))

export const useLeadsStore = create((set, get) => ({
  leads: [],
  total: 0,
  loading: false,
  selectedLead: null,

  setLeads: (leads, total) => set({ leads, total }),
  setLoading: (loading) => set({ loading }),
  setSelectedLead: (lead) => set({ selectedLead: lead }),

  updateLeadStatus: (leadId, status) =>
    set((state) => ({
      leads: state.leads.map((l) => (l.id === leadId ? { ...l, status } : l)),
    })),
}))
