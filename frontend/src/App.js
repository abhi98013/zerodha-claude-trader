import React, { useState, useEffect, useCallback } from 'react';
import {
  TrendingUp, TrendingDown, Activity, Shield, Bot, RefreshCw,
  Play, Square, AlertTriangle, CheckCircle, XCircle, Zap,
  BarChart2, DollarSign, Clock, Target, ArrowUpRight, ArrowDownRight
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine
} from 'recharts';
import {
  getHealth, getAuthStatus, getQuotes, analyzeAll,
  executeTrade, squareoffAll, getTradeHistory, getOpenPositions,
  getRiskStats, startBot, stopBot, getBotStatus, resetDaily,
  createSession, getOHLCV
} from './api';

const SYMBOLS = ['RELIANCE', 'INFY', 'TCS', 'HDFCBANK', 'ICICIBANK'];

function Badge({ type, children }) {
  const styles = {
    BUY: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
    SELL: 'bg-red-500/20 text-red-400 border border-red-500/30',
    HOLD: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
    success: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
    error: 'bg-red-500/20 text-red-400 border border-red-500/30',
    info: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
    paper: 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${styles[type] || styles.info}`}>
      {children}
    </span>
  );
}

function StatCard({ icon: Icon, label, value, sub, color = 'blue', trend }) {
  const colors = {
    blue: 'text-blue-400', green: 'text-emerald-400',
    red: 'text-red-400', amber: 'text-amber-400', purple: 'text-purple-400',
  };
  return (
    <div className="glass rounded-xl p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">{label}</span>
        <Icon size={16} className={colors[color]} />
      </div>
      <div className={`text-2xl font-bold ${colors[color]}`}>{value}</div>
      {sub && <div className="text-slate-500 text-xs">{sub}</div>}
      {trend !== undefined && (
        <div className={`flex items-center gap-1 text-xs ${trend >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {trend >= 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
          {Math.abs(trend).toFixed(2)}%
        </div>
      )}
    </div>
  );
}

function SignalCard({ item, onExecute, executing }) {
  const signal = item.signal || {};
  const action = signal.action || 'HOLD';
  const conf = signal.confidence || 0;
  const confColor = conf >= 75 ? 'text-emerald-400' : conf >= 60 ? 'text-amber-400' : 'text-red-400';
  const confBarColor = conf >= 75 ? 'bg-emerald-500' : conf >= 60 ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div className="glass rounded-xl p-4 flex flex-col gap-3 hover:border-slate-600 transition-all">
      <div className="flex items-center justify-between">
        <span className="font-semibold text-white font-mono text-sm">{item.symbol}</span>
        <Badge type={action}>{action}</Badge>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <div className="text-slate-500">Price</div>
          <div className="text-white font-mono">₹{(item.current_price || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
        </div>
        <div>
          <div className="text-slate-500">Confidence</div>
          <div className={`font-bold ${confColor}`}>{conf}%</div>
        </div>
        <div>
          <div className="text-slate-500">Target</div>
          <div className="text-emerald-400 font-mono">₹{(signal.target || 0).toFixed(2)}</div>
        </div>
        <div>
          <div className="text-slate-500">Stop Loss</div>
          <div className="text-red-400 font-mono">₹{(signal.stop_loss || 0).toFixed(2)}</div>
        </div>
        <div>
          <div className="text-slate-500">R:R</div>
          <div className="text-blue-400">{(signal.risk_reward_ratio || 0).toFixed(2)}x</div>
        </div>
        <div>
          <div className="text-slate-500">Valid</div>
          <div>{item.trade_valid ? <CheckCircle size={14} className="text-emerald-400" /> : <XCircle size={14} className="text-red-400" />}</div>
        </div>
      </div>

      <div>
        <div className="flex justify-between text-xs text-slate-500 mb-1">
          <span>Signal Strength</span><span className={confColor}>{conf}%</span>
        </div>
        <div className="w-full bg-slate-800 rounded-full h-1.5">
          <div className={`h-1.5 rounded-full transition-all duration-500 ${confBarColor}`} style={{ width: `${conf}%` }} />
        </div>
      </div>

      {signal.reasoning && (
        <p className="text-slate-500 text-xs leading-relaxed italic">"{signal.reasoning}"</p>
      )}

      {item.trade_valid && action !== 'HOLD' && (
        <button
          onClick={() => onExecute(item.symbol)}
          disabled={executing === item.symbol}
          className="w-full py-2 rounded-lg text-xs font-semibold transition-all bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {executing === item.symbol ? '⏳ Executing...' : `Execute ${action}`}
        </button>
      )}
    </div>
  );
}

function TradeRow({ trade, index }) {
  const pnl = trade.pnl;
  return (
    <tr className="border-b border-slate-800 hover:bg-slate-800/30">
      <td className="py-2 px-3 text-xs text-slate-400 font-mono">{trade.order_id}</td>
      <td className="py-2 px-3 text-xs font-semibold">{trade.symbol || '-'}</td>
      <td className="py-2 px-3"><Badge type={trade.action}>{trade.action || '-'}</Badge></td>
      <td className="py-2 px-3 text-xs text-slate-300">{trade.qty || '-'}</td>
      <td className="py-2 px-3 text-xs font-mono">₹{(trade.entry_price || trade.price || 0).toFixed(2)}</td>
      <td className="py-2 px-3 text-xs">
        {pnl !== undefined
          ? <span className={pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}>
              {pnl >= 0 ? '+' : ''}₹{pnl.toFixed(2)}
            </span>
          : <span className="text-amber-400">Open</span>
        }
      </td>
      <td className="py-2 px-3 text-xs text-slate-500">
        {trade.status === 'CLOSED' ? '✅' : trade.status === 'OPEN' ? '🟡' : '✅'}
      </td>
    </tr>
  );
}

function ChartPanel({ symbol }) {
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getOHLCV(symbol)
      .then(res => {
        const data = res.data.data.slice(-40).map((d, i) => ({
          i,
          price: parseFloat(d.close?.toFixed(2) || 0),
          sma20: d.sma_20 ? parseFloat(d.sma_20.toFixed(2)) : null,
          ema9: d.ema_9 ? parseFloat(d.ema_9.toFixed(2)) : null,
        }));
        setChartData(data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [symbol]);

  if (loading) return <div className="flex items-center justify-center h-40 text-slate-500 text-sm">Loading chart...</div>;

  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey="i" hide />
        <YAxis domain={['auto', 'auto']} tick={{ fontSize: 10, fill: '#64748b' }} />
        <Tooltip
          contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 11 }}
          labelStyle={{ color: '#94a3b8' }}
        />
        <Line type="monotone" dataKey="price" stroke="#3b82f6" strokeWidth={2} dot={false} name="Price" />
        <Line type="monotone" dataKey="sma20" stroke="#f59e0b" strokeWidth={1} dot={false} strokeDasharray="4 2" name="SMA20" />
        <Line type="monotone" dataKey="ema9" stroke="#10b981" strokeWidth={1} dot={false} strokeDasharray="2 2" name="EMA9" />
      </LineChart>
    </ResponsiveContainer>
  );
}

export default function App() {
  const [health, setHealth] = useState(null);
  const [authStatus, setAuthStatus] = useState(null);
  const [quotes, setQuotes] = useState({});
  const [signals, setSignals] = useState([]);
  const [tradeHistory, setTradeHistory] = useState([]);
  const [openPositions, setOpenPositions] = useState({});
  const [riskStats, setRiskStats] = useState(null);
  const [botStatus, setBotStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(null);
  const [botLoading, setBotLoading] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState('RELIANCE');
  const [activeTab, setActiveTab] = useState('dashboard');
  const [notifications, setNotifications] = useState([]);
  const [sessionToken, setSessionToken] = useState('');
  const [sessionLoading, setSessionLoading] = useState(false);

  const notify = (msg, type = 'info') => {
    const id = Date.now();
    setNotifications(prev => [...prev, { id, msg, type }]);
    setTimeout(() => setNotifications(prev => prev.filter(n => n.id !== id)), 4000);
  };

  const fetchAll = useCallback(async () => {
    try {
      const [hRes, aRes, qRes, sRes, tRes, pRes, rRes, bRes] = await Promise.allSettled([
        getHealth(), getAuthStatus(), getQuotes(), analyzeAll(),
        getTradeHistory(), getOpenPositions(), getRiskStats(), getBotStatus(),
      ]);
      if (hRes.status === 'fulfilled') setHealth(hRes.value.data);
      if (aRes.status === 'fulfilled') setAuthStatus(aRes.value.data);
      if (qRes.status === 'fulfilled') setQuotes(qRes.value.data.data || {});
      if (sRes.status === 'fulfilled') setSignals(sRes.value.data.data || []);
      if (tRes.status === 'fulfilled') setTradeHistory(tRes.value.data.trades || []);
      if (pRes.status === 'fulfilled') setOpenPositions(pRes.value.data.positions || {});
      if (rRes.status === 'fulfilled') setRiskStats(rRes.value.data.stats || null);
      if (bRes.status === 'fulfilled') setBotStatus(bRes.value.data);
    } catch (e) {}
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 30000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  const handleExecute = async (symbol) => {
    setExecuting(symbol);
    try {
      const res = await executeTrade(symbol);
      const data = res.data;
      if (data.success) {
        notify(`✅ ${data.signal?.action} order placed for ${symbol} | ID: ${data.order_id}`, 'success');
        fetchAll();
      } else {
        notify(`ℹ️ ${symbol}: ${data.message}`, 'info');
      }
    } catch (e) {
      notify(`❌ Trade failed: ${e.message}`, 'error');
    } finally {
      setExecuting(null);
    }
  };

  const handleSquareOff = async () => {
    try {
      const res = await squareoffAll();
      notify(`✅ Squared off ${res.data.closed_positions} positions`, 'success');
      fetchAll();
    } catch (e) {
      notify(`❌ Square off failed`, 'error');
    }
  };

  const handleBotToggle = async () => {
    setBotLoading(true);
    try {
      if (botStatus?.running) {
        await stopBot();
        notify('🛑 Bot stopped', 'info');
      } else {
        await startBot();
        notify('🤖 Bot started — scanning markets every 5 min', 'success');
      }
      fetchAll();
    } catch (e) {
      notify(`❌ Bot toggle failed`, 'error');
    } finally {
      setBotLoading(false);
    }
  };

  const handleCreateSession = async () => {
    if (!sessionToken.trim()) return;
    setSessionLoading(true);
    try {
      const res = await createSession(sessionToken.trim());
      if (res.data.success) {
        notify('✅ Session created successfully', 'success');
        fetchAll();
      }
    } catch (e) {
      notify('❌ Session creation failed', 'error');
    } finally {
      setSessionLoading(false);
      setSessionToken('');
    }
  };

  const handleResetDaily = async () => {
    await resetDaily();
    notify('🔄 Daily stats reset', 'info');
    fetchAll();
  };

  const buySignals = signals.filter(s => s.signal?.action === 'BUY' && s.trade_valid).length;
  const sellSignals = signals.filter(s => s.signal?.action === 'SELL' && s.trade_valid).length;
  const openPositionCount = Object.keys(openPositions).length;
  const totalPnl = tradeHistory.reduce((sum, t) => sum + (t.pnl || 0), 0);

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'signals', label: 'AI Signals', icon: Zap },
    { id: 'chart', label: 'Charts', icon: BarChart2 },
    { id: 'trades', label: 'Trades', icon: DollarSign },
    { id: 'settings', label: 'Settings', icon: Shield },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Notifications */}
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
        {notifications.map(n => (
          <div key={n.id} className={`glass rounded-lg px-4 py-2 text-sm shadow-lg border ${
            n.type === 'success' ? 'border-emerald-500/30 text-emerald-300' :
            n.type === 'error' ? 'border-red-500/30 text-red-300' : 'border-blue-500/30 text-blue-300'
          } animate-pulse`}>
            {n.msg}
          </div>
        ))}
      </div>

      {/* Header */}
      <header className="glass border-b border-slate-800 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
              <TrendingUp size={16} className="text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-white">Zerodha × Claude AI</h1>
              <p className="text-xs text-slate-500">Automated Trading System</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Badge type="paper">📄 PAPER TRADE</Badge>
            <div className={`flex items-center gap-1.5 text-xs ${health?.status === 'healthy' ? 'text-emerald-400' : 'text-red-400'}`}>
              <div className={`w-2 h-2 rounded-full ${health?.status === 'healthy' ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
              {health?.status === 'healthy' ? 'Live' : 'Offline'}
            </div>
            <button onClick={fetchAll} className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors">
              <RefreshCw size={14} />
            </button>
            <button
              onClick={handleBotToggle}
              disabled={botLoading}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                botStatus?.running ? 'bg-red-600 hover:bg-red-500' : 'bg-emerald-600 hover:bg-emerald-500'
              } text-white disabled:opacity-50`}
            >
              {botStatus?.running ? <><Square size={12} /> Stop Bot</> : <><Play size={12} /> Start Bot</>}
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="max-w-7xl mx-auto px-4 flex gap-1 border-t border-slate-800 overflow-x-auto">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              <tab.icon size={13} />{tab.label}
            </button>
          ))}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-32 gap-4">
            <div className="w-12 h-12 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
            <p className="text-slate-400">Connecting to trading engine...</p>
          </div>
        ) : (
          <>
            {/* Dashboard Tab */}
            {activeTab === 'dashboard' && (
              <div className="flex flex-col gap-6">
                {/* Auth Banner */}
                {!authStatus?.authenticated && (
                  <div className="glass rounded-xl p-4 border border-amber-500/30 flex items-center gap-3">
                    <AlertTriangle size={18} className="text-amber-400 shrink-0" />
                    <div>
                      <p className="text-amber-400 text-sm font-semibold">Paper Trade Mode Active</p>
                      <p className="text-slate-400 text-xs">All trades are simulated. No real money is at risk. Authenticate with Zerodha to go live.</p>
                    </div>
                  </div>
                )}

                {/* Stats Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <StatCard icon={DollarSign} label="Capital" value={`₹${(riskStats?.capital || 100000).toLocaleString('en-IN')}`} color="blue" sub="Available margin" />
                  <StatCard icon={TrendingUp} label="Today's P&L" value={`${totalPnl >= 0 ? '+' : ''}₹${totalPnl.toFixed(2)}`} color={totalPnl >= 0 ? 'green' : 'red'} sub={`${tradeHistory.length} trades`} />
                  <StatCard icon={Activity} label="Open Positions" value={openPositionCount} color="amber" sub="Active trades" />
                  <StatCard icon={Bot} label="AI Signals" value={`${buySignals}B / ${sellSignals}S`} color="purple" sub={`${signals.length} analyzed`} />
                </div>

                {/* Risk Stats */}
                {riskStats && (
                  <div className="glass rounded-xl p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h2 className="text-sm font-semibold text-white flex items-center gap-2"><Shield size={14} className="text-blue-400" /> Risk Monitor</h2>
                      <button onClick={handleResetDaily} className="text-xs text-slate-500 hover:text-slate-300 transition-colors">Reset Daily</button>
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <div className="text-slate-500 text-xs mb-1">Daily P&L</div>
                        <div className={`text-lg font-bold ${riskStats.daily_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {riskStats.daily_pnl >= 0 ? '+' : ''}₹{riskStats.daily_pnl.toFixed(2)}
                        </div>
                      </div>
                      <div>
                        <div className="text-slate-500 text-xs mb-1">Max Loss Limit</div>
                        <div className="text-lg font-bold text-red-400">₹{riskStats.max_daily_loss_amount.toFixed(2)}</div>
                      </div>
                      <div>
                        <div className="text-slate-500 text-xs mb-1">Remaining Risk</div>
                        <div className="text-lg font-bold text-amber-400">₹{riskStats.remaining_risk.toFixed(2)}</div>
                      </div>
                    </div>
                    <div className="mt-3">
                      <div className="flex justify-between text-xs text-slate-500 mb-1">
                        <span>Risk Used</span>
                        <span>{((Math.abs(riskStats.daily_pnl) / riskStats.max_daily_loss_amount) * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-1.5">
                        <div className="h-1.5 rounded-full bg-red-500 transition-all" style={{ width: `${Math.min(100, (Math.abs(riskStats.daily_pnl) / riskStats.max_daily_loss_amount) * 100)}%` }} />
                      </div>
                    </div>
                  </div>
                )}

                {/* Live Quotes */}
                <div className="glass rounded-xl p-4">
                  <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2"><Activity size={14} className="text-blue-400" /> Live Market Quotes</h2>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                    {SYMBOLS.map(sym => {
                      const q = quotes[sym] || {};
                      const change = q.change || 0;
                      return (
                        <div key={sym} className="bg-slate-800/50 rounded-lg p-3 cursor-pointer hover:bg-slate-800 transition-colors" onClick={() => { setSelectedSymbol(sym); setActiveTab('chart'); }}>
                          <div className="text-xs font-semibold text-white mb-1">{sym}</div>
                          <div className="text-sm font-bold text-blue-400 font-mono">₹{(q.last_price || 0).toFixed(2)}</div>
                          <div className={`text-xs ${change >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            {change >= 0 ? '▲' : '▼'} {Math.abs(change).toFixed(2)}%
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Bot Status */}
                <div className="glass rounded-xl p-4">
                  <div className="flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                      <Bot size={14} className={botStatus?.running ? 'text-emerald-400' : 'text-slate-500'} /> Bot Status
                    </h2>
                    <div className={`flex items-center gap-2 text-xs ${botStatus?.running ? 'text-emerald-400' : 'text-slate-500'}`}>
                      <div className={`w-2 h-2 rounded-full ${botStatus?.running ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}`} />
                      {botStatus?.running ? 'Running' : 'Stopped'}
                    </div>
                  </div>
                  {botStatus && (
                    <div className="mt-3 grid grid-cols-3 gap-3 text-xs text-slate-400">
                      <div><span className="text-slate-500">Market Open:</span> {botStatus.market_open}</div>
                      <div><span className="text-slate-500">Market Close:</span> {botStatus.market_close}</div>
                      <div><span className="text-slate-500">Auto Squareoff:</span> {botStatus.squareoff_time}</div>
                    </div>
                  )}
                  <div className="mt-3 flex gap-2">
                    <button onClick={handleSquareOff} className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-600/20 text-amber-400 border border-amber-500/30 hover:bg-amber-600/30 transition-colors">
                      Square Off All
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Signals Tab */}
            {activeTab === 'signals' && (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-sm font-semibold text-white flex items-center gap-2"><Zap size={14} className="text-blue-400" /> Claude AI Signals</h2>
                  <div className="flex gap-2">
                    <Badge type="BUY">{buySignals} BUY</Badge>
                    <Badge type="SELL">{sellSignals} SELL</Badge>
                    <Badge type="HOLD">{signals.length - buySignals - sellSignals} HOLD</Badge>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {signals.map(item => (
                    <SignalCard key={item.symbol} item={item} onExecute={handleExecute} executing={executing} />
                  ))}
                </div>
              </div>
            )}

            {/* Chart Tab */}
            {activeTab === 'chart' && (
              <div className="glass rounded-xl p-4">
                <div className="flex items-center gap-3 mb-4 flex-wrap">
                  <h2 className="text-sm font-semibold text-white flex items-center gap-2"><BarChart2 size={14} className="text-blue-400" /> Price Chart</h2>
                  <div className="flex gap-2 flex-wrap">
                    {SYMBOLS.map(sym => (
                      <button key={sym} onClick={() => setSelectedSymbol(sym)}
                        className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${selectedSymbol === sym ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'}`}>
                        {sym}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="mb-2 flex gap-4 text-xs">
                  <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-blue-500 inline-block" /> Price</span>
                  <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-amber-500 inline-block border-dashed" /> SMA20</span>
                  <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-emerald-500 inline-block border-dashed" /> EMA9</span>
                </div>
                <ChartPanel symbol={selectedSymbol} />
                <div className="mt-3 text-xs text-slate-500 text-center">Last 40 candles (5-min interval) — Click a symbol above to switch</div>
              </div>
            )}

            {/* Trades Tab */}
            {activeTab === 'trades' && (
              <div className="flex flex-col gap-4">
                {/* Open Positions */}
                {Object.keys(openPositions).length > 0 && (
                  <div className="glass rounded-xl p-4">
                    <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2"><Clock size={14} className="text-amber-400" /> Open Positions</h2>
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="text-xs text-slate-500 border-b border-slate-800">
                            <th className="text-left py-2 px-3">Order ID</th>
                            <th className="text-left py-2 px-3">Symbol</th>
                            <th className="text-left py-2 px-3">Action</th>
                            <th className="text-left py-2 px-3">Qty</th>
                            <th className="text-left py-2 px-3">Entry</th>
                            <th className="text-left py-2 px-3">P&L</th>
                            <th className="text-left py-2 px-3">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.values(openPositions).map((pos, i) => <TradeRow key={i} trade={pos} index={i} />)}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Trade History */}
                <div className="glass rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="text-sm font-semibold text-white flex items-center gap-2"><DollarSign size={14} className="text-blue-400" /> Trade History</h2>
                    <div className={`text-sm font-bold ${totalPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      Total P&L: {totalPnl >= 0 ? '+' : ''}₹{totalPnl.toFixed(2)}
                    </div>
                  </div>
                  {tradeHistory.length === 0 ? (
                    <p className="text-slate-500 text-sm text-center py-8">No trades yet. Use AI Signals tab to execute trades.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="text-xs text-slate-500 border-b border-slate-800">
                            <th className="text-left py-2 px-3">Order ID</th>
                            <th className="text-left py-2 px-3">Symbol</th>
                            <th className="text-left py-2 px-3">Action</th>
                            <th className="text-left py-2 px-3">Qty</th>
                            <th className="text-left py-2 px-3">Price</th>
                            <th className="text-left py-2 px-3">P&L</th>
                            <th className="text-left py-2 px-3">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {tradeHistory.slice().reverse().map((trade, i) => <TradeRow key={i} trade={trade} index={i} />)}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Settings Tab */}
            {activeTab === 'settings' && (
              <div className="flex flex-col gap-4 max-w-2xl">
                <div className="glass rounded-xl p-5">
                  <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2"><Shield size={14} className="text-blue-400" /> Zerodha Authentication</h2>
                  <p className="text-xs text-slate-400 mb-3">
                    1. Click "Get Login URL" below<br />
                    2. Login to Zerodha → copy the <code className="bg-slate-800 px-1 rounded">request_token</code> from redirect URL<br />
                    3. Paste it here and click Create Session
                  </p>
                  <a href="/auth/login-url" target="_blank" rel="noopener noreferrer"
                    className="inline-block text-xs text-blue-400 underline mb-3" onClick={async (e) => {
                      e.preventDefault();
                      const res = await fetch('/auth/login-url');
                      const d = await res.json();
                      window.open(d.login_url, '_blank');
                    }}>
                    → Get Zerodha Login URL
                  </a>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Paste request_token here..."
                      value={sessionToken}
                      onChange={e => setSessionToken(e.target.value)}
                      className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                    />
                    <button
                      onClick={handleCreateSession}
                      disabled={sessionLoading || !sessionToken}
                      className="px-4 py-2 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-50 transition-colors"
                    >
                      {sessionLoading ? 'Creating...' : 'Create Session'}
                    </button>
                  </div>
                  <div className="mt-3 flex items-center gap-2 text-xs">
                    <span className="text-slate-500">Status:</span>
                    {authStatus?.authenticated
                      ? <span className="text-emerald-400 flex items-center gap-1"><CheckCircle size={12} /> Authenticated</span>
                      : <span className="text-amber-400 flex items-center gap-1"><AlertTriangle size={12} /> Not authenticated (Paper mode)</span>
                    }
                  </div>
                </div>

                <div className="glass rounded-xl p-5">
                  <h2 className="text-sm font-semibold text-white mb-4">System Configuration</h2>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    {[
                      ['Mode', health?.mode || 'PAPER_TRADE'],
                      ['Bot Active', botStatus?.running ? '✅ Running' : '🛑 Stopped'],
                      ['Watchlist', SYMBOLS.join(', ')],
                      ['Daily Trades', `${riskStats?.daily_trades || 0} / 10`],
                      ['Market Hours', '9:20 AM – 3:15 PM IST'],
                      ['Auto Squareoff', '3:10 PM IST'],
                    ].map(([k, v]) => (
                      <div key={k} className="bg-slate-800/50 rounded-lg p-3">
                        <div className="text-slate-500 mb-1">{k}</div>
                        <div className="text-white font-medium">{v}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="glass rounded-xl p-5 border border-red-500/20">
                  <h2 className="text-sm font-semibold text-red-400 mb-2 flex items-center gap-2"><AlertTriangle size={14} /> Risk Disclaimer</h2>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    This system is for educational purposes. Automated trading carries significant financial risk.
                    Always paper trade for minimum 2 weeks before going live. Never risk more than you can afford to lose.
                    Claude AI analysis is not financial advice. Past performance does not guarantee future results.
                  </p>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
