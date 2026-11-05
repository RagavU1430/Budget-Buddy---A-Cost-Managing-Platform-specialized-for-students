import api from './client'

export const getMonthlySummary = (month) => api.get('/analytics/summary/', { params: { month } })
export const getMonthlyTrends = (months = 6) => api.get('/analytics/trends/', { params: { months } })
export const getCategoryTrends = (months = 3) =>
  api.get('/analytics/category-trends/', { params: { months } })
