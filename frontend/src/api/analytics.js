import api from './client'

export const getMonthlySummary = (month) => api.get('/api/analytics/summary/', { params: { month } })
export const getMonthlyTrends = (months = 6) => api.get('/api/analytics/trends/', { params: { months } })
export const getCategoryTrends = (months = 3) =>
  api.get('/api/analytics/category-trends/', { params: { months } })
