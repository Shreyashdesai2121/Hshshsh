import React, { useState, useEffect } from 'react';
import { Play, Square, Activity, Target, Zap, TrendingUp, AlertCircle, Clock, DollarSign } from 'lucide-react';

interface LiveAlert {
  symbol: string;
  strike: number;
  option_type: string;
  pattern_type: string;
  current_price: number;
  strength: number;
  status: string;
  step: string;
  timestamp: string;
  target_price?: number;
  stop_loss_price?: number;
  entry_price?: number;
  channel_breakout_price?: number;
}

interface PastSignal {
  signal_id: string;
  symbol: string;
  strike: number;
  option_type: string;
  entry_price: number;
  target_price: number;
  stop_loss_price: number;
  current_price: number;
  signal_time: string;
  outcome: string;
  profit_loss_pct: number;
  profit_loss_amount: number;
  last_updated: string | null;
}

interface PerformanceSummary {
  total_signals: number;
  total_invested: number;
  total_current_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  targets_hit: number;
  stop_losses_hit: number;
  still_running: number;
}

interface ContractStatus {
  symbol: string;
  strike: number;
  option_type: string;
  expiry: string;
  current_price: number;
  status: string;
  step: string;
  strength: number;
  last_update: string | null;
}

interface LiveStatus {
  monitoring_active: boolean;
  contracts_count: number;
  alerts_count: number;
  last_update: string;
}

const LiveMonitor: React.FC = () => {
  const [alerts, setAlerts] = useState<LiveAlert[]>([]);
  const [contracts, setContracts] = useState<ContractStatus[]>([]);
  const [pastSignals, setPastSignals] = useState<PastSignal[]>([]);
  const [performance, setPerformance] = useState<PerformanceSummary | null>(null);
  const [status, setStatus] = useState<LiveStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAlerts = async () => {
    try {
      const response = await fetch('/live/alerts');
      const data = await response.json();
      if (data.alerts) {
        setAlerts(data.alerts);
      }
    } catch (err) {
      console.error('Error fetching alerts:', err);
    }
  };

  const fetchStatus = async () => {
    try {
      const response = await fetch('/live/status');
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      console.error('Error fetching status:', err);
    }
  };

  const fetchContracts = async () => {
    try {
      const response = await fetch('/live/contracts');
      const data = await response.json();
      if (data.contracts) {
        setContracts(data.contracts);
      }
    } catch (err) {
      console.error('Error fetching contracts:', err);
    }
  };

  const fetchPastSignals = async () => {
    try {
      const response = await fetch('/live/past-signals');
      const data = await response.json();
      if (data.signals) {
        setPastSignals(data.signals);
      }
    } catch (err) {
      console.error('Error fetching past signals:', err);
    }
  };

  const fetchPerformance = async () => {
    try {
      const response = await fetch('/live/performance');
      const data = await response.json();
      setPerformance(data);
    } catch (err) {
      console.error('Error fetching performance:', err);
    }
  };

  const startMonitoring = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/live/start', { method: 'POST' });
      const data = await response.json();
      if (data.error) {
        setError(data.error);
      } else {
            // Start polling for updates
            setInterval(fetchAlerts, 5000); // Update every 5 seconds
            setInterval(fetchStatus, 10000); // Update status every 10 seconds
            setInterval(fetchContracts, 10000); // Update contracts every 10 seconds
            setInterval(fetchPastSignals, 10000); // Update past signals every 10 seconds
            setInterval(fetchPerformance, 10000); // Update performance every 10 seconds
      }
    } catch (err) {
      setError('Failed to start monitoring');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchAlerts();
    fetchContracts();
    fetchPastSignals();
    fetchPerformance();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pattern_detected':
        return 'bg-yellow-100 text-yellow-800';
      case 'kst_overlap':
        return 'bg-orange-100 text-orange-800';
      case 'breakout_confirmed':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'pattern_detected':
        return 'Pattern Detected';
      case 'kst_overlap':
        return 'KST Overlap - Ready for Breakout';
      case 'breakout_confirmed':
        return 'BREAKOUT CONFIRMED - TRADE SIGNAL!';
      default:
        return 'No Pattern Yet';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pattern_detected':
        return <Target className="w-4 h-4" />;
      case 'kst_overlap':
        return <Activity className="w-4 h-4" />;
      case 'breakout_confirmed':
        return <Zap className="w-4 h-4" />;
      default:
        return <Clock className="w-4 h-4" />;
    }
  };

  const getOutcomeColor = (outcome: string) => {
    switch (outcome) {
      case 'target_hit':
        return 'bg-green-100 text-green-800';
      case 'stop_loss_hit':
        return 'bg-red-100 text-red-800';
      case 'running':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getOutcomeText = (outcome: string) => {
    switch (outcome) {
      case 'target_hit':
        return 'Target Hit';
      case 'stop_loss_hit':
        return 'Stop Loss Hit';
      case 'running':
        return 'Running';
      default:
        return 'Unknown';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Live Pattern Monitoring</h2>
          <p className="text-sm text-gray-500">Real-time Pattern Detection & Trade Signals</p>
        </div>
        
        <div className="flex items-center space-x-4">
          {status && (
            <div className="flex items-center">
              <div className={`w-2 h-2 rounded-full mr-2 ${status.monitoring_active ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className="text-sm text-gray-600">
                {status.monitoring_active ? 'Monitoring Active' : 'Monitoring Inactive'}
              </span>
            </div>
          )}
          
          <button
            onClick={startMonitoring}
            disabled={isLoading || (status?.monitoring_active)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2 inline-block"></div>
                Starting...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2 inline" />
                Start Monitoring
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      {/* Status Cards */}
      {status && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-gray-500">Contracts Monitored</h3>
            <p className="text-2xl font-bold text-gray-900">{status.contracts_count}</p>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-gray-500">Active Alerts</h3>
            <p className="text-2xl font-bold text-gray-900">{status.alerts_count}</p>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-gray-500">Last Update</h3>
            <p className="text-sm text-gray-900">
              {status.last_update ? new Date(status.last_update).toLocaleTimeString() : 'Never'}
            </p>
          </div>
        </div>
      )}

      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-medium text-gray-900 mb-4">Contract Status ({contracts.length} contracts)</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {contracts.map((contract, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50">
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-medium text-gray-900">
                    {contract.symbol} {contract.strike}{contract.option_type}
                  </h4>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(contract.status)}`}>
                    {getStatusText(contract.status)}
                  </span>
                </div>
                <div className="space-y-1 text-sm text-gray-600">
                  <div><span className="font-medium">Price:</span> ₹{contract.current_price.toFixed(2)}</div>
                  <div><span className="font-medium">Step:</span> {contract.step}</div>
                  {contract.strength > 0 && (
                    <div><span className="font-medium">Strength:</span> {(contract.strength * 100).toFixed(1)}%</div>
                  )}
                  {contract.last_update && (
                    <div><span className="font-medium">Updated:</span> {new Date(contract.last_update).toLocaleTimeString()}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-lg font-medium text-gray-900">Live Alerts</h3>
          {alerts.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No alerts yet. Start monitoring to see live pattern detection.
            </div>
          ) : (
            <div className="space-y-3">
              {alerts.map((alert, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center space-x-4">
                        <h4 className="font-medium text-gray-900">
                          {alert.symbol} {alert.strike}{alert.option_type}
                        </h4>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(alert.status)}`}>
                          {getStatusText(alert.status)}
                        </span>
                      </div>
                      <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600">
                        <div>
                          <span className="font-medium">Pattern:</span> {alert.pattern_type}
                        </div>
                        <div>
                          <span className="font-medium">Price:</span> ₹{alert.current_price.toFixed(2)}
                        </div>
                        <div>
                          <span className="font-medium">Strength:</span> {(alert.strength * 100).toFixed(1)}%
                        </div>
                        <div>
                          <span className="font-medium">Time:</span> {new Date(alert.timestamp).toLocaleTimeString()}
                        </div>
                      </div>
                      {alert.target_price && (
                        <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600">
                          <div>
                            <span className="font-medium">Entry:</span> ₹{alert.entry_price?.toFixed(2) || alert.current_price.toFixed(2)}
                          </div>
                          <div>
                            <span className="font-medium">Target:</span> ₹{alert.target_price.toFixed(2)}
                          </div>
                          <div>
                            <span className="font-medium">Stop Loss:</span> ₹{alert.stop_loss_price?.toFixed(2) || 'N/A'}
                          </div>
                          <div>
                            <span className="font-medium">Breakout:</span> ₹{alert.channel_breakout_price?.toFixed(2) || 'N/A'}
                          </div>
                        </div>
                      )}
                      <div className="mt-2 text-sm text-blue-600">
                        <span className="font-medium">Step:</span> {alert.step}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Performance Summary */}
        {performance && performance.total_signals > 0 && (
          <div className="mt-8">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Performance Summary (₹10,000 per signal assumption)</h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-gray-50 p-4 rounded-lg">
                <h4 className="text-sm font-medium text-gray-500">Total Signals</h4>
                <p className="text-2xl font-bold text-gray-900">{performance.total_signals}</p>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <h4 className="text-sm font-medium text-gray-500">Total Invested</h4>
                <p className="text-2xl font-bold text-gray-900">₹{performance.total_invested.toLocaleString()}</p>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <h4 className="text-sm font-medium text-gray-500">Current Value</h4>
                <p className="text-2xl font-bold text-gray-900">₹{performance.total_current_value.toLocaleString()}</p>
              </div>
              <div className={`p-4 rounded-lg ${performance.total_pnl >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
                <h4 className="text-sm font-medium text-gray-500">Total P&L</h4>
                <p className={`text-2xl font-bold ${performance.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  ₹{performance.total_pnl.toLocaleString()} ({performance.total_pnl_pct.toFixed(1)}%)
                </p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-green-50 p-4 rounded-lg">
                <h4 className="text-sm font-medium text-green-700">Targets Hit</h4>
                <p className="text-xl font-bold text-green-600">{performance.targets_hit}</p>
              </div>
              <div className="bg-red-50 p-4 rounded-lg">
                <h4 className="text-sm font-medium text-red-700">Stop Losses Hit</h4>
                <p className="text-xl font-bold text-red-600">{performance.stop_losses_hit}</p>
              </div>
              <div className="bg-blue-50 p-4 rounded-lg">
                <h4 className="text-sm font-medium text-blue-700">Still Running</h4>
                <p className="text-xl font-bold text-blue-600">{performance.still_running}</p>
              </div>
            </div>
          </div>
        )}

        {/* Past Signals Section */}
        <div className="mt-8">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Past Signals ({pastSignals.length} signals)</h3>
          {pastSignals.length === 0 ? (
            <div className="text-center py-8 text-gray-500 bg-gray-50 rounded-lg border border-gray-200">
              <Clock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-lg text-gray-600">No past signals yet</p>
              <p className="text-sm text-gray-500 mt-1">Signals will appear here once generated</p>
            </div>
          ) : (
            <div className="space-y-3">
              {pastSignals.map((signal, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center space-x-4 mb-2">
                        <h4 className="font-medium text-gray-900">
                          {signal.symbol} {signal.strike}{signal.option_type}
                        </h4>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getOutcomeColor(signal.outcome)}`}>
                          {getOutcomeText(signal.outcome)}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600 mb-2">
                        <div>
                          <span className="font-medium">Entry:</span> ₹{signal.entry_price.toFixed(2)}
                        </div>
                        <div>
                          <span className="font-medium">Target:</span> ₹{signal.target_price.toFixed(2)}
                        </div>
                        <div>
                          <span className="font-medium">Stop Loss:</span> ₹{signal.stop_loss_price.toFixed(2)}
                        </div>
                        <div>
                          <span className="font-medium">Current:</span> ₹{signal.current_price.toFixed(2)}
                        </div>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm text-gray-600">
                        <div>
                          <span className="font-medium">Signal Time:</span> {new Date(signal.signal_time).toLocaleString()}
                        </div>
                        <div>
                          <span className="font-medium">P&L:</span> 
                          <span className={`ml-1 ${signal.profit_loss_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {signal.profit_loss_pct.toFixed(1)}% (₹{signal.profit_loss_amount.toFixed(0)})
                          </span>
                        </div>
                        {signal.last_updated && (
                          <div>
                            <span className="font-medium">Updated:</span> {new Date(signal.last_updated).toLocaleTimeString()}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LiveMonitor;

