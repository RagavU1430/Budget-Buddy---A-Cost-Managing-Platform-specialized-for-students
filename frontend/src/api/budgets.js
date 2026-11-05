import api from './client'

export const getBudgets = (params = {}) => api.get('/budgets/', { params })
export const createBudget = (payload) => api.post('/budgets/', payload)
export const updateBudget = (id, payload) => api.patch(`/budgets/${id}/`, payload)
export const deleteBudget = (id) => api.delete(`/budgets/${id}/`)
