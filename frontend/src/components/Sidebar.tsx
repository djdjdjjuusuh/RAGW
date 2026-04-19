import { useState } from 'react'
import { FiPlus, FiTrash2 } from 'react-icons/fi'
import { deleteSession } from '../api'
import type { SessionPreview } from '../api'

interface SidebarProps {
  sessions: SessionPreview[]
  activeSessionId: string | null
  onSelect: (sessionId: string) => void
  onNewSession: () => void
  onSessionDeleted: () => void
}

export default function Sidebar({ sessions, activeSessionId, onSelect, onNewSession, onSessionDeleted }: SidebarProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [isDeleteMode, setIsDeleteMode] = useState(false)

  const handleSessionClick = (sessionId: string) => {
    if (isDeleteMode) {
      setSelectedIds(prev => {
        const newSet = new Set(prev)
        if (newSet.has(sessionId)) {
          newSet.delete(sessionId)
        } else {
          newSet.add(sessionId)
        }
        return newSet
      })
    } else {
      onSelect(sessionId)
    }
  }

  const handleDeleteSelected = async () => {
    if (selectedIds.size === 0) return
    try {
      for (const sessionId of selectedIds) {
        await deleteSession(sessionId)
      }
      setSelectedIds(new Set())
      setIsDeleteMode(false)
      onSessionDeleted()
    } catch (error) {
      console.error('删除会话失败', error)
    }
  }

  return (
    <aside className="sidebar-card">
      <div className="sidebar-header">
        <div>
          <h2>会话列表</h2>
          <p>{isDeleteMode ? `已选 ${selectedIds.size} 个` : '点击切换或新建可爱的对话'}</p>
        </div>
        {isDeleteMode ? (
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="pill-button" onClick={() => {
              setIsDeleteMode(false)
              setSelectedIds(new Set())
            }} style={{ background: '#e8e8e8', color: '#666' }}>
              取消
            </button>
            <button className="pill-button" onClick={handleDeleteSelected} style={{ background: '#ff6b6b', color: '#fff' }}>
              <FiTrash2 /> 删除
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="pill-button" onClick={() => setIsDeleteMode(true)} style={{ background: '#f0f0f0', color: '#666' }}>
              <FiTrash2 />
            </button>
            <button className="pill-button" onClick={onNewSession}>
              <FiPlus /> 新对话
            </button>
          </div>
        )}
      </div>

      <div className="session-list">
        {sessions.length === 0 ? (
          <div className="empty-state">还没有会话，先开始一个吧～</div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.session_id}
              className={`session-item ${activeSessionId === session.session_id ? 'selected' : ''} ${isDeleteMode && selectedIds.has(session.session_id) ? 'delete-selected' : ''}`}
              onClick={() => handleSessionClick(session.session_id)}
              style={{
                display: 'flex',
                gap: '12px',
                alignItems: 'center',
                cursor: 'pointer',
                background: isDeleteMode && selectedIds.has(session.session_id) ? '#ffe8e8' : '',
              }}
            >
              {isDeleteMode && (
                <input
                  type="checkbox"
                  checked={selectedIds.has(session.session_id)}
                  onChange={(e) => e.stopPropagation()}
                  style={{ width: '18px', height: '18px', cursor: 'pointer', flexShrink: 0 }}
                />
              )}
              <span className="session-icon">💬</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="session-preview">{session.name || '新对话'}</div>
                <div className="session-time">最近</div>
              </div>
            </div>
          ))
        )}
      </div>
    </aside>
  )
}
