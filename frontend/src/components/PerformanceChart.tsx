import React from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

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

interface PerformanceChartProps {
  performance: PerformanceMetrics | null
}

const PerformanceChart: React.FC<PerformanceChartProps> = ({ performance }) => {
  // Mock data for demonstration - in real app, this would come from historical data
  const mockData = [
    { time: '09:00', pnl: 0 },
    { time: '10:00', pnl: performance?.total_pnl ? performance.total_pnl * 0.1 : 0 },
    { time: '11:00', pnl: performance?.total_pnl ? performance.total_pnl * 0.3 : 0 },
    { time: '12:00', pnl: performance?.total_pnl ? performance.total_pnl * 0.5 : 0 },
    { time: '13:00', pnl: performance?.total_pnl ? performance.total_pnl * 0.7 : 0 },
    { time: '14:00', pnl: performance?.total_pnl ? performance.total_pnl * 0.9 : 0 },
    { time: '15:00', pnl: performance?.total_pnl || 0 },
  ]

  const formatCurrency = (value: number) => {
    return `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  return (
    <div className="card">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Performance Chart</h2>
      
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={mockData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" />
            <YAxis 
              tickFormatter={formatCurrency}
              domain={['dataMin - 1000', 'dataMax + 1000']}
            />
            <Tooltip 
              formatter={(value: number) => [formatCurrency(value), 'P&L']}
              labelStyle={{ color: '#374151' }}
              contentStyle={{ 
                backgroundColor: '#f9fafb', 
                border: '1px solid #e5e7eb',
                borderRadius: '6px'
              }}
            />
            <Line 
              type="monotone" 
              dataKey="pnl" 
              stroke="#3b82f6" 
              strokeWidth={2}
              dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6, stroke: '#3b82f6', strokeWidth: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      
      {performance && (
        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-600">Total Trades:</span>
            <span className="ml-2 font-medium">{performance.total_trades}</span>
          </div>
          <div>
            <span className="text-gray-600">Win Rate:</span>
            <span className="ml-2 font-medium">{performance.win_rate.toFixed(1)}%</span>
          </div>
          <div>
            <span className="text-gray-600">Best Trade:</span>
            <span className="ml-2 font-medium text-success-600">
              {formatCurrency(performance.best_trade)}
            </span>
          </div>
          <div>
            <span className="text-gray-600">Worst Trade:</span>
            <span className="ml-2 font-medium text-danger-600">
              {formatCurrency(performance.worst_trade)}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

export default PerformanceChart