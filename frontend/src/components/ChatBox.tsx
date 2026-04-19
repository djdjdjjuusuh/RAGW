import { useEffect, useState, useRef } from 'react'
import { FiSend } from 'react-icons/fi'
import { fetchHistory, sendChatStream, ChatMessage } from '../api'

interface ChatBoxProps {
  sessionId: string | null
  onSessionCreated: (sessionId: string) => void
  onConversationUpdated: () => void
}

// 简单的 Markdown 解析函数
const parseMarkdown = (text: string): JSX.Element[] => {
  const lines = text.split('\n')
  const elements: JSX.Element[] = []
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    
    // 标题
    if (line.match(/^#{1,6}\s/)) {
      const level = (line.match(/^#+/))?.[0].length || 1
      const content = line.replace(/^#{1,6}\s/, '')
      switch (level) {
        case 1:
          elements.push(<h1 key={i}>{content}</h1>)
          break
        case 2:
          elements.push(<h2 key={i}>{content}</h2>)
          break
        case 3:
          elements.push(<h3 key={i}>{content}</h3>)
          break
        default:
          elements.push(<h4 key={i}>{content}</h4>)
          break
      }
    }
    // 代码块
    else if (line === '```') {
      let codeContent = ''
      i++
      while (i < lines.length && lines[i] !== '```') {
        codeContent += lines[i] + '\n'
        i++
      }
      elements.push(
        <pre key={i} className="code-block">
          <code>{codeContent}</code>
        </pre>
      )
    }
    // 列表项
    else if (line.match(/^-\s/)) {
      elements.push(
        <li key={i} className="list-item">
          {line.replace(/^-\s/, '')}
        </li>
      )
    }
    // 链接
    else if (line.match(/\[.*\]\(.*\)/)) {
      const match = line.match(/\[(.*)\]\((.*)\)/)
      if (match) {
        const [, text, url] = match
        elements.push(
          <p key={i}>
            <a href={url} target="_blank" rel="noopener noreferrer">
              {text}
            </a>
          </p>
        )
      }
    }
    // 普通段落
    else if (line.trim()) {
      // 处理粗体和斜体
      let processedLine = line
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
      
      elements.push(
        <p key={i} dangerouslySetInnerHTML={{ __html: processedLine }} />
      )
    }
    // 空行
    else {
      elements.push(<br key={i} />)
    }
  }
  
  return elements
}

export default function ChatBox({ sessionId, onSessionCreated, onConversationUpdated }: ChatBoxProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const activeSessionRef = useRef<string | null>(sessionId)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    activeSessionRef.current = sessionId
    if (!sessionId) {
      setMessages([])
      return
    }

    fetchHistory(sessionId)
      .then((data) => setMessages(data.messages))
      .catch(() => setMessages([]))
  }, [sessionId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const appendAssistantChunk = (chunk: string) => {
    setMessages((prev) => {
      if (prev.length === 0 || prev[prev.length - 1].role !== 'assistant') {
        return [...prev, { role: 'assistant', content: chunk }]
      }
      const updated = [...prev]
      updated[updated.length - 1] = {
        ...updated[updated.length - 1],
        content: updated[updated.length - 1].content + chunk,
      }
      return updated
    })
  }

  const handleSend = async () => {
    if (!inputValue.trim()) return
    setError('')
    setLoading(true)
    const userText = inputValue.trim()
    setInputValue('')
    setMessages((prev) => [...prev, { role: 'user', content: userText }, { role: 'assistant', content: '' }])

    try {
      await sendChatStream(
        { message: userText, session_id: activeSessionRef.current || undefined },
        (data) => {
          if (data.type === 'session' && typeof data.session_id === 'string') {
            onSessionCreated(data.session_id)
          }
          if (data.type === 'delta' && typeof data.text === 'string') {
            appendAssistantChunk(data.text)
          }
        },
        () => {
          setLoading(false)
          onConversationUpdated()
        },
      )
    } catch (err) {
      setError('发送失败，请检查后端服务和网络连接。')
      setLoading(false)
    }
  }

  return (
    <section className="chat-card">
      <div className="chat-header">
        <div>
          <h2>可爱对话助手</h2>
          <p>输入你想问的问题，助手会结合已上传文档给你答案。</p>
        </div>
      </div>

      <div className="message-window">
        {messages.map((message, index) => (
          <div key={index} className={`message-row ${message.role}`}>
            <div className={`message-bubble ${message.role}`}>
              {message.role === 'assistant' && message.content === '' && loading ? (
                <span className="typing">✨ 正在思考...</span>
              ) : message.role === 'assistant' ? (
                <div className="markdown-content">
                  {parseMarkdown(message.content)}
                </div>
              ) : (
                message.content.split('\n').map((line, idx) => <p key={idx}>{line}</p>)
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-panel">
        <input
          value={inputValue}
          placeholder="输入你的问题，像和小伙伴聊天一样～"
          onChange={(event) => setInputValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              if (!loading) handleSend()
            }
          }}
          disabled={loading}
        />
        <button className="send-button" onClick={handleSend} disabled={loading}>
          <FiSend /> 发送
        </button>
      </div>
      {error && <div className="error-note">{error}</div>}
    </section>
  )
}