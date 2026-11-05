import api from './client'

export const getExpenses = (params = {}) => api.get('/expenses/', { params })
export const createExpense = (payload) => api.post('/expenses/', payload)
export const updateExpense = (id, payload) => api.patch(`/expenses/${id}/`, payload)
export const deleteExpense = (id) => api.delete(`/expenses/${id}/`)
