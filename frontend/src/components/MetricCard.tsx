import React from 'react'
import { LucideIcon } from 'lucide-react'

interface MetricCardProps {
  title: string
  value: number
  icon: LucideIcon
  color: 'primary' | 'success' | 'danger' | 'warning'
  format?: 'currency' | 'percentage' | 'number'
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, icon: Icon, color, format = 'number' }) => {
  const formatValue = (val: number) => {
    switch (format) {
      case 'currency':
        return `₹${val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
      case 'percentage':
        return `${val.toFixed(2)}%`
      default:
        return val.toLocaleString()
    }
  }

  const colorClasses = {
    primary: 'text-primary-600 bg-primary-100',
    success: 'text-success-600 bg-success-100',
    danger: 'text-danger-600 bg-danger-100',
    warning: 'text-warning-600 bg-warning-100'
  }

  return (
    <div className="metric-card">
      <div className="flex items-center">
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          <Icon className="h-6 w-6" />
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-semibold text-gray-900">
            {formatValue(value)}
          </p>
        </div>
      </div>
    </div>
  )
}

export default MetricCard