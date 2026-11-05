import api from './client'

export const getReports = () => api.get('/reports/')
export const generateReport = (payload) => api.post('/reports/generate/', payload)
export const getDownloadUrl = (id) => `${api.defaults.baseURL}/reports/${id}/download/`
export const downloadReport = (id) => api.get(`/reports/${id}/download/`, { responseType: 'blob' })
