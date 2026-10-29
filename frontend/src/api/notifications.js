import api from './client'

export const getNotifications = (params = {}) => api.get('/api/notifications/', { params })
export const markAllRead = () => api.post('/api/notifications/mark-all-read/')
export const getUnreadCount = () => api.get('/api/notifications/unread-count/')
export const markNotificationRead = (id) => api.patch(`/api/notifications/${id}/`, { is_read: true })
export const deleteNotification = (id) => api.delete(`/api/notifications/${id}/`)
