import api from './client.js'

export async function sendChatMessage(message) {
  const { data } = await api.post('/api/assistant/chat/', { message })
  return data
}

export async function getChatHistory() {
  const { data } = await api.get('/api/assistant/chat/')
  return data
}

export async function getAssistantSummary() {
  const { data } = await api.get('/api/assistant/summary/')
  return data
}

export async function clearChatHistory() {
  const { data } = await api.post('/api/assistant/clear/')
  return data
}
