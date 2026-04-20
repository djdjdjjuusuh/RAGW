export interface ChatRequestPayload {
  message: string
  session_id?: string | null
}

export interface SessionPreview {
  session_id: string
  preview: string
  name: string
  updated_at: number
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function fetchSessions(): Promise<SessionPreview[]> {
  const response = await fetch(`${API_BASE}/api/sessions`)
  return response.json()
}

export async function fetchHistory(sessionId: string): Promise<{ session_id: string; messages: ChatMessage[] }> {
  const response = await fetch(`${API_BASE}/api/history/${sessionId}`)
  return response.json()
}

export async function uploadFile(file: File): Promise<{ file_id: string; status: string; message: string }> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await fetch(`${API_BASE}/api/upload`, {
    method: 'POST',
    body: formData,
  })
  return response.json()
}

export async function getUploadStatus(fileId: string): Promise<{ status: string; chunk_count?: number; error?: string }> {
  const response = await fetch(`${API_BASE}/api/upload-status/${fileId}`)
  return response.json()
}

export async function deleteSession(sessionId: string): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: 'DELETE',
  })
  return response.json()
}

export interface UploadedFile {
  file_id: string
  file_name: string
  status: string
  chunk_count: number
  upload_time: string
  error?: string
}

export async function fetchFiles(): Promise<UploadedFile[]> {
  const response = await fetch(`${API_BASE}/api/files`)
  return response.json()
}

export async function deleteFile(fileId: string): Promise<{ file_id: string; status: string }> {
  const response = await fetch(`${API_BASE}/api/files/${fileId}`, {
    method: 'DELETE',
  })
  return response.json()
}

export async function sendChatStream(
  payload: ChatRequestPayload,
  onEvent: (data: Record<string, unknown>) => void,
  onDone: () => void,
  abortController?: AbortController
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: abortController?.signal,
  })

  if (!response.body) {
    throw new Error('后端未返回流式响应')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let doneCalled = false

  try {
    while (true) {
      // 检查是否被中止
      if (abortController?.signal.aborted) {
        break
      }

      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''

      for (const part of parts) {
        const lines = part.split('\n').filter(Boolean)
        const dataLine = lines.find((line) => line.startsWith('data:'))
        if (!dataLine) continue

        const raw = dataLine.slice(5).trim()
        try {
          const data = JSON.parse(raw)
          if (data.type === 'done') {
            if (!doneCalled) {
              doneCalled = true
              onDone()
            }
          } else {
            onEvent(data)
          }
        } catch (error) {
          console.warn('解析 SSE 数据失败', error)
        }
      }
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      // 正常的中止，不抛出错误
      return
    }
    throw error
  } finally {
    // 确保关闭 reader
    try {
      await reader.cancel()
    } catch (error) {
      console.warn('关闭 reader 失败', error)
    }
  }

  if (!doneCalled) {
    onDone()
  }
}
