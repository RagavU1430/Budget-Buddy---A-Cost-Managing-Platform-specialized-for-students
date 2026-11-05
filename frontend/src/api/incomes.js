import api from './client'

export const getIncomes = (params = {}) => api.get('/incomes/', { params })
export const createIncome = (payload) => api.post('/incomes/', payload)
export const updateIncome = (id, payload) => api.patch(`/incomes/${id}/`, payload)
export const deleteIncome = (id) => api.delete(`/incomes/${id}/`)
