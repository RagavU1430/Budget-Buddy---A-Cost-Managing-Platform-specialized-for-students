import api from './client'

export const getExpenses = (params = {}) => api.get('/api/expenses/', { params })
export const createExpense = (payload) => api.post('/api/expenses/', payload)
export const updateExpense = (id, payload) => api.patch(`/api/expenses/${id}/`, payload)
export const deleteExpense = (id) => api.delete(`/api/expenses/${id}/`)
