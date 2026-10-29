import api from './client'

export const getGoals = (params = {}) => api.get('/api/goals/', { params })
export const createGoal = (payload) => api.post('/api/goals/', payload)
export const updateGoal = (id, payload) => api.patch(`/api/goals/${id}/`, payload)
export const deleteGoal = (id) => api.delete(`/api/goals/${id}/`)
export const depositToGoal = (id, amount) => api.post(`/api/goals/${id}/deposit/`, { amount })
