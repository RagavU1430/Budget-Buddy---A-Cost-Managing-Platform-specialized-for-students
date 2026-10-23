export function formatError(error) {
  const data = error?.response?.data

  if (!data) return error?.message || 'Something went wrong. Please try again.'
  if (typeof data === 'string') return data
  if (data.detail) return data.detail

  const messages = Object.entries(data).flatMap(([key, value]) =>
    (Array.isArray(value) ? value : [value]).map((message) => `${key}: ${message}`),
  )

  return messages.length ? messages.join(' ') : 'Request failed.'
}
