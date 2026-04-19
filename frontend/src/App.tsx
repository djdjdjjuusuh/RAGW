import { useEffect, useState } from 'react'
import Sidebar from './components/Sidebar'
import ChatBox from './components/ChatBox'
import FileUpload from './components/FileUpload'
import { fetchSessions, type SessionPreview } from './api'

export default function App() {
  const [sessions, setSessions] = useState<SessionPreview[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  const loadSessions = async () => {
    const sessionList = await fetchSessions()
    setSessions(sessionList)
  }

  useEffect(() => {
    loadSessions()
  }, [refreshKey])

  const handleNewSession = () => {
    setActiveSessionId(null)
  }

  const handleSessionCreated = (sessionId: string) => {
    setActiveSessionId(sessionId)
    setRefreshKey((value) => value + 1)
  }

  const handleConversationUpdated = () => {
    setRefreshKey((value) => value + 1)
  }

  return (
    <div className="app-shell">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={setActiveSessionId}
        onNewSession={handleNewSession}
        onSessionDeleted={handleConversationUpdated}
      />

      <main className="main-layout">
        {!activeSessionId ? (
          <div className="hero-card">
            <div>
              <h1>RAG 聊天助手</h1>
              <p>上传文档并与大模型对话，助手会检索知识库并实时输出结果。</p>
            </div>
          </div>
        ) : null}

        <div className="content-grid">
          <ChatBox
            sessionId={activeSessionId}
            onSessionCreated={handleSessionCreated}
            onConversationUpdated={handleConversationUpdated}
          />
          <FileUpload onUploadSuccess={handleConversationUpdated} />
        </div>
      </main>
    </div>
  )
}
