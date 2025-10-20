import React, { useState, useEffect } from 'react'
import { useApi } from '../contexts/ApiContext'

const LogsViewer: React.FC = () => {
  const { baseUrl } = useApi()
  const [logs, setLogs] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  const fetchLogs = async () => {
    try {
      const response = await fetch(`${baseUrl}/logs?lines=50`)
      if (!response.ok) throw new Error('Failed to fetch logs')
      const data = await response.json()
      setLogs(data.logs || [])
    } catch (error) {
      console.error('Error fetching logs:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
    const interval = setInterval(fetchLogs, 10000) // Refresh every 10 seconds
    return () => clearInterval(interval)
  }, [])

  const getLogLevel = (logLine: string) => {
    if (logLine.includes('ERROR')) return 'text-danger-600'
    if (logLine.includes('WARNING')) return 'text-warning-600'
    if (logLine.includes('INFO')) return 'text-primary-600'
    if (logLine.includes('DEBUG')) return 'text-gray-600'
    return 'text-gray-700'
  }

  if (loading) {
    return (
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">System Logs</h2>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="space-y-2">
            {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
              <div key={i} className="h-3 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">System Logs</h2>
        <button
          onClick={fetchLogs}
          className="text-sm text-primary-600 hover:text-primary-700"
        >
          Refresh
        </button>
      </div>
      
      <div className="bg-gray-900 rounded-lg p-4 h-64 overflow-y-auto">
        {logs.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <p>No logs available</p>
          </div>
        ) : (
          <div className="space-y-1">
            {logs.map((log, index) => (
              <div
                key={index}
                className={`text-xs font-mono ${getLogLevel(log)}`}
              >
                {log}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default LogsViewer