import api from './client'

export const getIncomes = (params = {}) => api.get('/api/incomes/', { params })
export const createIncome = (payload) => api.post('/api/incomes/', payload)
export const updateIncome = (id, payload) => api.patch(`/api/incomes/${id}/`, payload)
export const deleteIncome = (id) => api.delete(`/api/incomes/${id}/`)
