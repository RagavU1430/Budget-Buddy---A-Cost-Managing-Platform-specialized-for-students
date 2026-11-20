import api from './client'

export const getBudgets = ({ signal, ...params } = {}) => api.get('/budgets/', { params, signal })
export const createBudget = (payload) => api.post('/budgets/', payload)
export const updateBudget = (id, payload) => api.patch(`/budgets/${id}/`, payload)
export const deleteBudget = (id) => api.delete(`/budgets/${id}/`)
