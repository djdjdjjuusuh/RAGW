import { useEffect, useState, useRef } from 'react'
import { FiSend } from 'react-icons/fi'
import { fetchHistory, sendChatStream, ChatMessage } from '../api'

interface ChatBoxProps {
  sessionId: string | null
  onSessionCreated: (sessionId: string) => void
  onConversationUpdated: () => void
}

// 增强的 Markdown 解析函数
const parseMarkdown = (text: string): JSX.Element[] => {
  const lines = text.split('\n')
  const elements: JSX.Element[] = []
  
  const parseInlineFormatting = (content: string): string => {
    let result = content
    
    // 处理粗斜体组合 ***text***
    result = result.replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>')
    
    // 处理粗体 **text**
    result = result.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    
    // 处理斜体 *text*
    result = result.replace(/\*(.*?)\*/g, '<em>$1</em>')
    
    return result
  }
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    
    // 标题
    if (line.match(/^#{1,6}\s/)) {
      const level = (line.match(/^#+/))?.[0].length || 1
      const content = line.replace(/^#{1,6}\s/, '')
      const parsedContent = parseInlineFormatting(content)
      switch (level) {
        case 1:
          elements.push(<h1 key={i} dangerouslySetInnerHTML={{ __html: parsedContent }} />)
          break
        case 2:
          elements.push(<h2 key={i} dangerouslySetInnerHTML={{ __html: parsedContent }} />)
          break
        case 3:
          elements.push(<h3 key={i} dangerouslySetInnerHTML={{ __html: parsedContent }} />)
          break
        default:
          elements.push(<h4 key={i} dangerouslySetInnerHTML={{ __html: parsedContent }} />)
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
      const content = line.replace(/^-\s/, '')
      const parsedContent = parseInlineFormatting(content)
      elements.push(
        <li key={i} className="list-item" dangerouslySetInnerHTML={{ __html: parsedContent }} />
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
      const parsedContent = parseInlineFormatting(line)
      elements.push(
        <p key={i} dangerouslySetInnerHTML={{ __html: parsedContent }} />
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
  const abortControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    // 检查是否是从 null 变为新会话
    const wasNull = activeSessionRef.current === null
    activeSessionRef.current = sessionId
    
    // 只有当不是从 null 变为新会话时才取消流
    // 这样可以避免中断第一个消息的回复
    if (!wasNull && abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    
    // 重置状态，但保留 loading 状态
    // 因为 loading 状态由 handleSend 控制，不应该在会话切换时重置
    setInputValue('')
    setError('')
    
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

    // 取消之前的请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    
    // 创建新的 AbortController
    const abortController = new AbortController()
    abortControllerRef.current = abortController

    try {
      await sendChatStream(
        { message: userText, session_id: activeSessionRef.current || undefined },
        (data) => {
          // 检查当前会话是否仍然是活跃会话
          // 对于新会话，我们需要允许消息处理，即使 sessionId 发生了变化
          if (activeSessionRef.current !== sessionId && sessionId !== null) {
            return
          }
          
          if (data.type === 'session' && typeof data.session_id === 'string') {
            onSessionCreated(data.session_id)
          }
          if (data.type === 'delta' && typeof data.text === 'string') {
            appendAssistantChunk(data.text)
          }
        },
        () => {
          if (activeSessionRef.current === sessionId || sessionId === null) {
            setLoading(false)
            onConversationUpdated()
          }
        },
        abortController
      )
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError('发送失败，请检查后端服务和网络连接。')
      }
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