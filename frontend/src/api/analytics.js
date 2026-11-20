import api from './client'

export const getMonthlySummary = (month, { signal } = {}) => api.get('/analytics/summary/', { params: { month }, signal })
export const getMonthlyTrends = (months = 6, { signal } = {}) => api.get('/analytics/trends/', { params: { months }, signal })
export const getCategoryTrends = (months = 3, { signal } = {}) =>
  api.get('/analytics/category-trends/', { params: { months }, signal })
