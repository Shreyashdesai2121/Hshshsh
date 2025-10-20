import React, { useState } from 'react'
import { Play, Square, AlertTriangle, Settings } from 'lucide-react'

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

interface ControlPanelProps {
  status: SystemStatus | null
  onStart: () => void
  onStop: () => void
  onForceClose: () => void
}

const ControlPanel: React.FC<ControlPanelProps> = ({ status, onStart, onStop, onForceClose }) => {
  const [showSettings, setShowSettings] = useState(false)
  const [quantity, setQuantity] = useState(1)
  const [oneTradePerDay, setOneTradePerDay] = useState(true)

  const handleStart = () => {
    if (window.confirm('Are you sure you want to start the trading strategy?')) {
      onStart()
    }
  }

  const handleStop = () => {
    if (window.confirm('Are you sure you want to stop the trading strategy?')) {
      onStop()
    }
  }

  const handleForceClose = () => {
    if (window.confirm('This will force close ALL open positions. Are you sure?')) {
      onForceClose()
    }
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-gray-900">Strategy Control</h2>
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="btn btn-secondary"
        >
          <Settings className="h-4 w-4 mr-2" />
          Settings
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Start/Stop Buttons */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">Strategy Control</label>
          <div className="flex space-x-2">
            {status?.running ? (
              <button
                onClick={handleStop}
                className="btn btn-danger flex-1"
              >
                <Square className="h-4 w-4 mr-2" />
                Stop Strategy
              </button>
            ) : (
              <button
                onClick={handleStart}
                className="btn btn-success flex-1"
              >
                <Play className="h-4 w-4 mr-2" />
                Start Strategy
              </button>
            )}
          </div>
        </div>

        {/* Force Close */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">Emergency Actions</label>
          <button
            onClick={handleForceClose}
            className="btn btn-warning w-full"
            disabled={!status?.open_positions}
          >
            <AlertTriangle className="h-4 w-4 mr-2" />
            Force Close All
          </button>
        </div>

        {/* Status Info */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">System Status</label>
          <div className="text-sm text-gray-600">
            <p>Mode: <span className="font-medium">Dry Run</span></p>
            <p>Positions: <span className="font-medium">{status?.open_positions || 0}</span></p>
            <p>Errors: <span className="font-medium">{status?.error_count || 0}</span></p>
          </div>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h3 className="text-md font-medium text-gray-900 mb-4">Configuration</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Quantity per Trade
              </label>
              <input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                min="1"
                max="10"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                One Trade Per Day
              </label>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={oneTradePerDay}
                  onChange={(e) => setOneTradePerDay(e.target.checked)}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <span className="ml-2 text-sm text-gray-600">Limit to one trade per day</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ControlPanel