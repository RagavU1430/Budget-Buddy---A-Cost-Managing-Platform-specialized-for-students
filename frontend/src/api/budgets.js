import api from './client'

export const getBudgets = (params = {}) => api.get('/api/budgets/', { params })
export const createBudget = (payload) => api.post('/api/budgets/', payload)
export const updateBudget = (id, payload) => api.patch(`/api/budgets/${id}/`, payload)
export const deleteBudget = (id) => api.delete(`/api/budgets/${id}/`)
