import api from './client'

export const getReports = () => api.get('/api/reports/')
export const generateReport = (payload) => api.post('/api/reports/generate/', payload)
export const getDownloadUrl = (id) => `${api.defaults.baseURL}/api/reports/${id}/download/`
export const downloadReport = (id) => api.get(`/api/reports/${id}/download/`, { responseType: 'blob' })
