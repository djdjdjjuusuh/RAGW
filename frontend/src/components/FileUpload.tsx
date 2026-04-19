import { useState, useEffect, type DragEvent } from 'react'
import { FiUploadCloud, FiTrash2, FiCheck, FiAlertCircle } from 'react-icons/fi'
import { uploadFile, getUploadStatus, fetchFiles, deleteFile, type UploadedFile } from '../api'

interface FileUploadProps {
  onUploadSuccess: () => void
}

export default function FileUpload({ onUploadSuccess }: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false)
  const [status, setStatus] = useState('拖拽文件或点击上传')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [refreshing, setRefreshing] = useState(false)

  const loadFiles = async () => {
    setRefreshing(true)
    try {
      const fileList = await fetchFiles()
      setFiles(fileList)
    } catch (error) {
      console.error('加载文件列表失败', error)
    } finally {
      setRefreshing(false)
    }
  }

  useEffect(() => {
    loadFiles()
  }, [])

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    setStatus('上传中...')
    setIsAnalyzing(true)
    try {
      const result = await uploadFile(files[0])
      const fileId = result.file_id
      setStatus('分析中...')
      
      let completed = false
      let attempts = 0
      while (!completed && attempts < 120) {
        await new Promise(resolve => setTimeout(resolve, 1000))
        const statusResult = await getUploadStatus(fileId)
        if (statusResult.status === 'completed') {
          setStatus(`✅ 分析完成！已提取 ${statusResult.chunk_count} 个文本片段`)
          completed = true
          onUploadSuccess()
          loadFiles()
        } else if (statusResult.status === 'failed') {
          setStatus(`❌ 分析失败：${statusResult.error}`)
          completed = true
          loadFiles()
        }
        attempts++
      }
      if (!completed) {
        setStatus('分析超时，请稍后重试')
      }
    } catch (error) {
      setStatus('上传失败，请重试。')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleDrop = async (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setDragActive(false)
    await handleFiles(event.dataTransfer.files)
  }

  const handleDeleteFile = async (fileId: string) => {
    if (confirm('确定要删除这个文件吗？')) {
      try {
        await deleteFile(fileId)
        loadFiles()
        onUploadSuccess()
      } catch (error) {
        console.error('删除文件失败', error)
      }
    }
  }

  const formatDate = (timestamp: string) => {
    if (!timestamp) return '未知时间'
    const date = new Date(parseFloat(timestamp) * 1000)
    return date.toLocaleString('zh-CN')
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <FiCheck size={16} className="text-green-500" />
      case 'failed':
        return <FiAlertCircle size={16} className="text-red-500" />
      default:
        return null
    }
  }

  return (
    <div className="upload-card">
      <div className={`upload-area ${dragActive ? 'drag-active' : ''}`}
        onDragOver={(event) => {
          event.preventDefault()
          setDragActive(true)
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
      >
        <div className="upload-icon"> <FiUploadCloud size={28} /> </div>
        <div className="upload-title">上传文档索引</div>
        <div className="upload-hint">支持 .txt/.pdf/.docx，后台自动解析并构建向量索引</div>
        <label className="upload-button">
          选择文件上传
          <input
            type="file"
            accept=".txt,.pdf,.docx"
            onChange={(event) => handleFiles(event.target.files)}
            hidden
          />
        </label>
        <div className="upload-status">{status}</div>
      </div>

      <div className="files-section">
        <div className="files-header">
          <h3>已上传文件</h3>
          <button 
            className="refresh-button" 
            onClick={loadFiles} 
            disabled={refreshing}
          >
            {refreshing ? '刷新中...' : '刷新'}
          </button>
        </div>
        
        {files.length === 0 ? (
          <div className="empty-files">还没有上传文件</div>
        ) : (
          <div className="files-list">
            {files.map((file) => (
              <div key={file.file_id} className="file-item">
                <div className="file-info">
                  {getStatusIcon(file.status)}
                  <div style={{ flex: 1 }}>
                    <div className="file-name">{file.file_name}</div>
                    <div className="file-meta">
                      {file.status === 'completed' ? `文本片段: ${file.chunk_count}` : file.status}
                      {' · '}
                      {formatDate(file.upload_time)}
                    </div>
                  </div>
                </div>
                <button 
                  className="delete-button" 
                  onClick={() => handleDeleteFile(file.file_id)}
                >
                  <FiTrash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
