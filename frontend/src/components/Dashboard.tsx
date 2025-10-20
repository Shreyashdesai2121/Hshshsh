import React, { useState, useEffect } from 'react'
import { Play, Square, TrendingUp, TrendingDown, DollarSign, Target, AlertCircle } from 'lucide-react'
import MetricCard from './MetricCard'
import ControlPanel from './ControlPanel'
import PositionsTable from './PositionsTable'
import TradesTable from './TradesTable'
import LogsViewer from './LogsViewer'
import PerformanceChart from './PerformanceChart'
import BacktestResults from './BacktestResults'
import LiveMonitor from './LiveMonitor'
import { useApi } from '../contexts/ApiContext'
import { useWebSocket } from '../contexts/WebSocketContext'

interface SystemStatus {
  running: boolean
  last_run_time: string | null
  last_candle_time: string | null
  open_positions: number
  today_trades: number
  total_trades: number
  total_pnl: number
  win_rate: number
  error_count: number
  last_error: string | null
  strategy_start_time: string | null
}

interface PerformanceMetrics {
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  total_pnl: number
  avg_trade_pnl: number
  best_trade: number
  worst_trade: number
  open_positions: number
  today_trades: number
  error_count: number
}

const Dashboard: React.FC = () => {
  const { baseUrl } = useApi()
  const { isConnected, lastMessage } = useWebSocket()
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [performance, setPerformance] = useState<PerformanceMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStatus = async () => {
    try {
      const response = await fetch(`${baseUrl}/status`)
      if (!response.ok) throw new Error('Failed to fetch status')
      const data = await response.json()
      setStatus(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
  }

  const fetchPerformance = async () => {
    try {
      const response = await fetch(`${baseUrl}/performance`)
      if (!response.ok) throw new Error('Failed to fetch performance')
      const data = await response.json()
      setPerformance(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
  }

  const startStrategy = async () => {
    try {
      const response = await fetch(`${baseUrl}/start_strategy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'dry_run' })
      })
      if (!response.ok) throw new Error('Failed to start strategy')
      await fetchStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
  }

  const stopStrategy = async () => {
    try {
      const response = await fetch(`${baseUrl}/stop_strategy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      if (!response.ok) throw new Error('Failed to stop strategy')
      await fetchStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
  }

  const forceCloseAll = async () => {
    if (!window.confirm('Are you sure you want to force close all positions?')) return
    
    try {
      const response = await fetch(`${baseUrl}/force_close_all`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      if (!response.ok) throw new Error('Failed to force close positions')
      await fetchStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
  }

  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      await Promise.all([fetchStatus(), fetchPerformance()])
      setLoading(false)
    }
    
    loadData()
    
    // Refresh data every 30 seconds
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [])

  // Update data when WebSocket message received
  useEffect(() => {
    if (lastMessage) {
      fetchStatus()
      fetchPerformance()
    }
  }, [lastMessage])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <div className="bg-blue-600 p-2 rounded-lg mr-4">
                <TrendingUp className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">King21's Algorithm</h1>
                <p className="text-sm text-gray-500">Advanced Pattern Detection & Live Trading</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="flex items-center">
                <div className={`w-2 h-2 rounded-full mr-2 ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className="text-sm text-gray-600">
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              
              <div className="flex items-center space-x-2">
                {status?.running ? (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    <Play className="w-3 h-3 mr-1" />
                    Running
                  </span>
                ) : (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                    <Square className="w-3 h-3 mr-1" />
                    Stopped
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex">
              <AlertCircle className="h-5 w-5 text-red-400 mr-3" />
              <div>
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Control Panel */}
        <div className="mb-8">
          <ControlPanel
            status={status}
            onStart={startStrategy}
            onStop={stopStrategy}
            onForceClose={forceCloseAll}
          />
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Today's P&L"
            value={performance?.total_pnl || 0}
            icon={DollarSign}
            color={performance?.total_pnl && performance.total_pnl >= 0 ? 'success' : 'danger'}
            format="currency"
          />
          <MetricCard
            title="Open Positions"
            value={status?.open_positions || 0}
            icon={Target}
            color="primary"
          />
          <MetricCard
            title="Trades Today"
            value={status?.today_trades || 0}
            icon={TrendingUp}
            color="primary"
          />
          <MetricCard
            title="Win Rate"
            value={performance?.win_rate || 0}
            icon={TrendingDown}
            color="success"
            format="percentage"
          />
        </div>

        {/* Live Monitoring Section - MOVED TO TOP */}
        <div className="mb-8">
          <LiveMonitor />
        </div>

        {/* Charts and Tables */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <PerformanceChart performance={performance} />
          <LogsViewer />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <PositionsTable />
          <TradesTable />
        </div>

        {/* Backtesting Section - MOVED TO BOTTOM */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Historical Backtesting</h2>
          <BacktestResults />
        </div>
      </main>
    </div>
  )
}

export default Dashboard