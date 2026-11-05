import api from './client'

export const getGoals = (params = {}) => api.get('/goals/', { params })
export const createGoal = (payload) => api.post('/goals/', payload)
export const updateGoal = (id, payload) => api.patch(`/goals/${id}/`, payload)
export const deleteGoal = (id) => api.delete(`/goals/${id}/`)
export const depositToGoal = (id, amount) => api.post(`/goals/${id}/deposit/`, { amount })
