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
  createSession, getOHLCV, strategyScan, getSectors, runBacktest, getLoginUrl, getRecommendations
} from './api';

const SYMBOLS = ['RELIANCE', 'INFY', 'TCS', 'HDFCBANK', 'ICICIBANK'];

const tvLink = (symbol) => `https://www.tradingview.com/chart/?symbol=NSE:${symbol}`;

function TVLink({ symbol, className = '', children }) {
  return (
    <a
      href={tvLink(symbol)}
      target="_blank"
      rel="noopener noreferrer"
      title={`Open ${symbol} on TradingView`}
      onClick={e => e.stopPropagation()}
      className={`hover:text-blue-400 hover:underline transition-colors cursor-pointer ${className}`}
    >
      {children || symbol}
    </a>
  );
}

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
        <TVLink symbol={item.symbol} className="font-semibold text-white font-mono text-sm" />
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
      <td className="py-2 px-3 text-xs font-semibold">
        {trade.symbol ? <TVLink symbol={trade.symbol}>{trade.symbol}</TVLink> : '-'}
      </td>
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
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    const timer = setTimeout(() => {
      getOHLCV(symbol)
        .then(res => {
          const raw = res.data.candles || res.data.data || [];
          const data = raw.slice(-40).map((d, i) => ({
            i,
            price: d.close ? parseFloat(Number(d.close).toFixed(2)) : null,
            sma20: d.sma_20 ? parseFloat(Number(d.sma_20).toFixed(2)) : null,
            ema9: d.ema_9 ? parseFloat(Number(d.ema_9).toFixed(2)) : null,
            label: d.timestamp ? String(d.timestamp).slice(11, 16) : String(i),
          }));
          setChartData(data);
        })
        .catch(e => {
          const msg = e?.response?.data?.detail || e?.response?.statusText || e.message || 'Failed to load chart';
          const status = e?.response?.status;
          setError(status === 429 ? 'Rate limited — please wait a moment and click Retry' : msg);
        })
        .finally(() => setLoading(false));
    }, 600);
    return () => clearTimeout(timer);
  }, [symbol]);

  useEffect(() => { const cancel = load(); return cancel; }, [load]);

  if (loading) return <div className="flex items-center justify-center h-40 text-slate-500 text-sm animate-pulse">Loading {symbol} chart...</div>;
  if (error) return (
    <div className="flex flex-col items-center justify-center h-40 gap-2">
      <p className="text-red-400 text-xs">{error}</p>
      <button onClick={load} className="text-xs text-blue-400 underline">Retry</button>
    </div>
  );
  if (!chartData.length) return <div className="flex items-center justify-center h-40 text-slate-500 text-sm">No chart data available</div>;

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey="label" tick={{ fontSize: 9, fill: '#475569' }} interval={7} />
        <YAxis domain={['auto', 'auto']} tick={{ fontSize: 10, fill: '#64748b' }} />
        <Tooltip
          contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 11 }}
          labelStyle={{ color: '#94a3b8' }}
        />
        <Line type="monotone" dataKey="price" stroke="#3b82f6" strokeWidth={2} dot={false} name="Price" connectNulls />
        <Line type="monotone" dataKey="sma20" stroke="#f59e0b" strokeWidth={1} dot={false} strokeDasharray="4 2" name="SMA20" connectNulls />
        <Line type="monotone" dataKey="ema9" stroke="#10b981" strokeWidth={1} dot={false} strokeDasharray="2 2" name="EMA9" connectNulls />
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
  const [strategyData, setStrategyData] = useState(null);
  const [strategyLoading, setStrategyLoading] = useState(false);
  const [btData, setBtData] = useState(null);
  const [btLoading, setBtLoading] = useState(false);
  const [btYears, setBtYears] = useState([2015, 2026]);
  const [recData, setRecData] = useState(null);
  const [recLoading, setRecLoading] = useState(false);

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
    { id: 'strategy', label: 'NSE Strategy', icon: Target },
    { id: 'recommendations', label: '🎯 Recommendations', icon: ArrowUpRight },
    { id: 'backtest', label: 'Backtest', icon: BarChart2 },
    { id: 'signals', label: 'AI Signals', icon: Zap },
    { id: 'chart', label: 'Charts', icon: Clock },
    { id: 'trades', label: 'Trades', icon: DollarSign },
    { id: 'settings', label: 'Settings', icon: Shield },
  ];

  const loadRecs = async () => {
    setRecLoading(true);
    try {
      const r = await getRecommendations();
      setRecData(r.data);
    } catch(e) { notify('Failed to load recommendations', 'error'); }
    finally { setRecLoading(false); }
  };

  useEffect(() => { if (activeTab === 'recommendations' && !recData) loadRecs(); }, [activeTab]);

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
                          <div className="text-xs font-semibold text-white mb-1 flex items-center justify-between">
                            <span>{sym}</span>
                            <TVLink symbol={sym} className="text-slate-500 text-xs">📊</TVLink>
                          </div>
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

            {/* Strategy Tab */}
            {activeTab === 'strategy' && (
              <div className="flex flex-col gap-5">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-sm font-bold text-white flex items-center gap-2"><Target size={14} className="text-blue-400" /> NSE Sector Scope Strategy</h2>
                    <p className="text-xs text-slate-500 mt-0.5">Sector momentum → Stock filter → Options CE/PE → Claude AI validation</p>
                  </div>
                  <button
                    onClick={async () => { setStrategyLoading(true); try { const r = await strategyScan(true); setStrategyData(r.data); } catch(e) { notify('Strategy scan failed', 'error'); } finally { setStrategyLoading(false); } }}
                    disabled={strategyLoading}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-50 transition-all"
                  >
                    {strategyLoading ? <><RefreshCw size={12} className="animate-spin" /> Scanning...</> : <><Zap size={12} /> Run Strategy Scan</>}
                  </button>
                </div>

                {!strategyData && (
                  <div className="glass rounded-xl p-8 text-center">
                    <Target size={32} className="text-slate-600 mx-auto mb-3" />
                    <p className="text-slate-400 text-sm font-medium">Click "Run Strategy Scan" to start</p>
                    <p className="text-slate-600 text-xs mt-1">Scans NSE sectors → filters stocks → picks CE/PE options → Claude validates</p>
                  </div>
                )}

                {strategyData && (
                  <>
                    {/* Sector Heatmap */}
                    <div className="glass rounded-xl p-4">
                      <h3 className="text-xs font-semibold text-white mb-3 flex items-center gap-2"><BarChart2 size={13} className="text-blue-400" /> Sector Momentum Ranking</h3>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                        {(strategyData.sector_scan || []).map((s, i) => {
                          const isUp = s.trend?.includes('UP');
                          const isStrong = s.trend?.startsWith('STRONG');
                          return (
                            <div key={s.sector} className={`rounded-lg p-3 border ${
                              isStrong && isUp ? 'bg-emerald-500/10 border-emerald-500/30' :
                              isUp ? 'bg-blue-500/10 border-blue-500/20' :
                              isStrong ? 'bg-red-500/10 border-red-500/30' :
                              'bg-slate-800/50 border-slate-700/30'
                            }`}>
                              <div className="text-xs font-medium text-slate-300 truncate">{s.sector.replace('NIFTY ', '')}</div>
                              <div className={`text-sm font-bold mt-1 ${isUp ? 'text-emerald-400' : 'text-red-400'}`}>{s.change_pct > 0 ? '+' : ''}{s.change_pct}%</div>
                              <div className="text-xs text-slate-500">{s.trend}</div>
                              <div className="w-full bg-slate-800 rounded-full h-1 mt-2">
                                <div className={`h-1 rounded-full ${isUp ? 'bg-emerald-500' : 'bg-red-500'}`} style={{ width: `${s.momentum_score}%` }} />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Filtered Stocks */}
                    {strategyData.filtered_stocks?.length > 0 && (
                      <div className="glass rounded-xl p-4">
                        <h3 className="text-xs font-semibold text-white mb-3 flex items-center gap-2"><Activity size={13} className="text-amber-400" /> Filtered Stocks (High Turnover + Institutional Buying + 5-min Low Hold)</h3>
                        <div className="overflow-x-auto">
                          <table className="w-full">
                            <thead>
                              <tr className="text-xs text-slate-500 border-b border-slate-800">
                                <th className="text-left py-2 px-3">Symbol</th>
                                <th className="text-left py-2 px-3">Sector</th>
                                <th className="text-left py-2 px-3">Change%</th>
                                <th className="text-left py-2 px-3">Turnover</th>
                                <th className="text-left py-2 px-3">Delivery%</th>
                                <th className="text-left py-2 px-3">5min Low</th>
                                <th className="text-left py-2 px-3">Score</th>
                              </tr>
                            </thead>
                            <tbody>
                              {strategyData.filtered_stocks.map((s, i) => (
                                <tr key={s.symbol} className="border-b border-slate-800 hover:bg-slate-800/30">
                                  <td className="py-2 px-3 text-xs font-bold font-mono">
                                    <TVLink symbol={s.symbol} className="text-white font-bold" />
                                  </td>
                                  <td className="py-2 px-3 text-xs text-slate-400">{(s.sector || '').replace('NIFTY ', '')}</td>
                                  <td className="py-2 px-3 text-xs text-emerald-400">+{s.change_pct}%</td>
                                  <td className="py-2 px-3 text-xs text-blue-400">₹{s.turnover}Cr</td>
                                  <td className="py-2 px-3 text-xs text-purple-400">{s.delivery_pct}%</td>
                                  <td className="py-2 px-3">{s['5min_low_hold'] ? <span className="text-emerald-400 text-xs">✓ Holding</span> : <span className="text-red-400 text-xs">✗ Broken</span>}</td>
                                  <td className="py-2 px-3"><span className="bg-blue-500/20 text-blue-400 text-xs px-2 py-0.5 rounded">{s.filter_score}/100</span></td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {/* Claude-Validated Option Picks */}
                    <div>
                      <h3 className="text-xs font-semibold text-white mb-3 flex items-center gap-2"><Zap size={13} className="text-yellow-400" /> Claude AI Validated Option Picks</h3>
                      {strategyData.picks?.length === 0 && (
                        <div className="glass rounded-xl p-6 text-center text-slate-500 text-sm">No qualifying picks right now. Run scan during 9:15–10:00 AM for best results.</div>
                      )}
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {(strategyData.picks || []).map((pick, i) => (
                          <div key={pick.option_symbol} className={`glass rounded-xl p-4 border ${
                            pick.option_type === 'CE' ? 'border-emerald-500/30' : 'border-red-500/30'
                          }`}>
                            <div className="flex items-center justify-between mb-3">
                              <div>
                                <TVLink symbol={pick.symbol} className="text-sm font-bold text-white font-mono" />
                                <div className="text-xs text-slate-500 font-mono">{pick.option_symbol}</div>
                              </div>
                              <span className={`px-2 py-1 rounded text-xs font-bold ${
                                pick.option_type === 'CE' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
                              }`}>{pick.option_type === 'CE' ? '📈 CALL' : '📉 PUT'}</span>
                            </div>

                            <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                              <div><div className="text-slate-500">Strike</div><div className="text-white font-mono font-bold">{pick.strike}</div></div>
                              <div><div className="text-slate-500">Premium</div><div className="text-blue-400 font-mono">₹{pick.premium}</div></div>
                              <div><div className="text-slate-500">Target</div><div className="text-emerald-400 font-mono">₹{pick.adjusted_target_premium || pick.target_premium}</div></div>
                              <div><div className="text-slate-500">Stop Loss</div><div className="text-red-400 font-mono">₹{pick.adjusted_sl_premium || pick.sl_premium}</div></div>
                              <div><div className="text-slate-500">R:R</div><div className="text-amber-400 font-bold">{(pick.adjusted_risk_reward || pick.risk_reward).toFixed(2)}x</div></div>
                              <div><div className="text-slate-500">Max Lots</div><div className="text-white">{pick.max_lots || 1}</div></div>
                            </div>

                            <div className="mb-2">
                              <div className="flex justify-between text-xs text-slate-500 mb-1"><span>AI Confidence</span><span className="text-blue-400">{pick.confidence}%</span></div>
                              <div className="w-full bg-slate-800 rounded-full h-1.5"><div className="h-1.5 rounded-full bg-blue-500" style={{ width: `${pick.confidence}%` }} /></div>
                            </div>

                            <p className="text-xs text-slate-400 italic leading-relaxed mb-2">"{pick.reasoning}"</p>
                            <p className="text-xs text-amber-400/80 leading-relaxed">💡 {pick.improvement}</p>

                            <div className="mt-2 pt-2 border-t border-slate-700 flex items-center gap-2 text-xs text-slate-500">
                              <span>Lot: {pick.lot_size}</span>
                              <span>·</span>
                              <span>Cost/lot: ₹{pick.cost_per_lot?.toLocaleString('en-IN')}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Backtest Tab */}
            {activeTab === 'backtest' && (
              <div className="flex flex-col gap-5">
                {/* Header + Controls */}
                <div className="glass rounded-xl p-5">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                      <h2 className="text-sm font-bold text-white flex items-center gap-2"><BarChart2 size={14} className="text-blue-400" /> 10-Year Strategy Backtest</h2>
                      <p className="text-xs text-slate-500 mt-0.5">Simulates the NSE Sector Scope strategy on 2,500+ trading days (2015–2024)</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-2 text-xs">
                        <span className="text-slate-500">From</span>
                        <select value={btYears[0]} onChange={e => setBtYears([+e.target.value, btYears[1]])} className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-white text-xs">
                          {[2015,2016,2017,2018,2019,2020].map(y => <option key={y} value={y}>{y}</option>)}
                        </select>
                        <span className="text-slate-500">To</span>
                        <select value={btYears[1]} onChange={e => setBtYears([btYears[0], +e.target.value])} className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-white text-xs">
                          {[2020,2021,2022,2023,2024].map(y => <option key={y} value={y}>{y}</option>)}
                        </select>
                      </div>
                      <button
                        onClick={async () => { setBtLoading(true); try { const r = await runBacktest(btYears[0], btYears[1]); setBtData(r.data); } catch(e) { notify('Backtest failed', 'error'); } finally { setBtLoading(false); } }}
                        disabled={btLoading}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-50 transition-all"
                      >
                        {btLoading ? <><RefreshCw size={12} className="animate-spin" /> Running...</> : <><Zap size={12} /> Run Backtest</>}
                      </button>
                    </div>
                  </div>
                </div>

                {!btData && (
                  <div className="glass rounded-xl p-12 text-center">
                    <BarChart2 size={40} className="text-slate-700 mx-auto mb-3" />
                    <p className="text-slate-400 text-sm font-medium">Click "Run Backtest" to simulate 10 years of strategy performance</p>
                    <p className="text-slate-600 text-xs mt-1">Processes 7,000+ option trades across 40 NSE stocks</p>
                  </div>
                )}

                {btData && (() => {
                  const s = btData.summary;
                  const maxYearPnl = Math.max(...Object.values(btData.by_year).map(y => y.pnl));
                  return (
                    <>
                      {/* Summary Stats */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <StatCard icon={TrendingUp} label="Total PnL" value={`₹${(s.total_pnl/100000).toFixed(1)}L`} color="green" sub={`${s.total_trades} trades`} />
                        <StatCard icon={Target} label="Win Rate" value={`${s.win_rate_pct}%`} color="blue" sub={`${s.winners}W / ${s.losers}L`} />
                        <StatCard icon={Shield} label="Profit Factor" value={s.profit_factor} color="purple" sub={`Avg Win ₹${s.avg_win_per_trade?.toFixed(0)}`} />
                        <StatCard icon={Activity} label="Target Hit" value={`${s.target_hit_pct}%`} color="amber" sub={`SL Hit: ${s.sl_hit_pct}%`} />
                      </div>

                      {/* Exit Breakdown */}
                      <div className="glass rounded-xl p-4">
                        <h3 className="text-xs font-semibold text-white mb-3">Exit Breakdown</h3>
                        <div className="flex gap-4 flex-wrap">
                          {[['TARGET_HIT', 'bg-emerald-500', s.target_hit_pct], ['EOD_EXIT', 'bg-blue-500', s.eod_exit_pct], ['SL_HIT', 'bg-red-500', s.sl_hit_pct]].map(([label, color, pct]) => (
                            <div key={label} className="flex-1 min-w-32">
                              <div className="flex justify-between text-xs text-slate-400 mb-1"><span>{label}</span><span>{pct}%</span></div>
                              <div className="w-full bg-slate-800 rounded-full h-2"><div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }} /></div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* TOP 5 WINNING TRADES */}
                      <div>
                        <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2"><TrendingUp size={14} className="text-emerald-400" /> Top 5 Winning Option Trades (10 Years)</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                          {(btData.top5_by_pnl || []).map((t, i) => (
                            <div key={t.trade_id} className="glass rounded-xl p-4 border border-emerald-500/30">
                              <div className="flex items-start justify-between mb-2">
                                <div>
                                  <div className="flex items-center gap-2">
                                    <span className="text-xs bg-emerald-500/20 text-emerald-400 font-bold px-2 py-0.5 rounded">#{i + 1}</span>
                                    <TVLink symbol={t.symbol} className="text-sm font-bold text-white font-mono" />
                                    <span className={`text-xs px-1.5 py-0.5 rounded font-bold ${t.option_type === 'CE' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>{t.option_type}</span>
                                  </div>
                                  <div className="text-xs text-slate-500 mt-0.5">{t.date} · Strike {t.strike} · {t.expiry}</div>
                                </div>
                                <div className="text-right">
                                  <div className="text-emerald-400 font-bold text-sm">+₹{t.total_pnl?.toLocaleString('en-IN')}</div>
                                  <div className="text-xs text-emerald-300">+{t.return_pct}%</div>
                                </div>
                              </div>
                              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs mb-3">
                                <div className="text-slate-500">Entry Premium <span className="text-blue-400 font-mono">₹{t.entry_premium}</span></div>
                                <div className="text-slate-500">Exit Premium <span className="text-white font-mono">₹{t.exit_premium}</span></div>
                                <div className="text-slate-500">Lot Size <span className="text-white">{t.lot_size?.toLocaleString('en-IN')}</span></div>
                                <div className="text-slate-500">Exit <span className={t.exit_reason === 'TARGET_HIT' ? 'text-emerald-400' : t.exit_reason === 'SL_HIT' ? 'text-red-400' : 'text-amber-400'}>{t.exit_reason}</span></div>
                                <div className="text-slate-500">Delivery <span className="text-purple-400">{t.delivery_pct}%</span></div>
                                <div className="text-slate-500">Turnover <span className="text-blue-400">₹{t.turnover_cr}Cr</span></div>
                                <div className="text-slate-500">5min Low <span className={t.five_min_low_held ? 'text-emerald-400' : 'text-red-400'}>{t.five_min_low_held ? '✓ Held' : '✗ Broken'}</span></div>
                                <div className="text-slate-500">Score <span className="text-amber-400">{t.signal_score}/100</span></div>
                              </div>
                              <div className="text-xs text-slate-500 bg-slate-800/50 rounded px-2 py-1">{t.sector?.replace('NIFTY ', '')}</div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Year-by-Year Performance */}
                      <div className="glass rounded-xl p-4">
                        <h3 className="text-xs font-semibold text-white mb-4">Year-by-Year PnL Performance</h3>
                        <div className="flex flex-col gap-2">
                          {Object.entries(btData.by_year).map(([yr, d]) => (
                            <div key={yr} className="flex items-center gap-3">
                              <span className="text-xs text-slate-400 w-10">{yr}</span>
                              <div className="flex-1 bg-slate-800 rounded-full h-5 relative overflow-hidden">
                                <div
                                  className={`h-5 rounded-full ${d.pnl >= 0 ? 'bg-emerald-500/70' : 'bg-red-500/70'} transition-all`}
                                  style={{ width: `${Math.min(100, Math.abs(d.pnl) / maxYearPnl * 100)}%` }}
                                />
                                <span className="absolute inset-0 flex items-center px-2 text-xs font-medium text-white">
                                  ₹{(d.pnl / 100000).toFixed(1)}L · {d.win_rate}% win · {d.trades} trades
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Sector Performance */}
                      <div className="glass rounded-xl p-4">
                        <h3 className="text-xs font-semibold text-white mb-3">Sector-wise Performance</h3>
                        <div className="overflow-x-auto">
                          <table className="w-full">
                            <thead>
                              <tr className="text-xs text-slate-500 border-b border-slate-800">
                                <th className="text-left py-2 px-3">Sector</th>
                                <th className="text-left py-2 px-3">Trades</th>
                                <th className="text-left py-2 px-3">Win %</th>
                                <th className="text-left py-2 px-3">Total PnL</th>
                              </tr>
                            </thead>
                            <tbody>
                              {Object.entries(btData.by_sector).sort((a, b) => b[1].pnl - a[1].pnl).map(([sec, d]) => (
                                <tr key={sec} className="border-b border-slate-800 hover:bg-slate-800/30">
                                  <td className="py-2 px-3 text-xs font-medium text-white">{sec.replace('NIFTY ', '')}</td>
                                  <td className="py-2 px-3 text-xs text-slate-400">{d.trades}</td>
                                  <td className="py-2 px-3">
                                    <span className={`text-xs font-bold ${d.win_rate >= 70 ? 'text-emerald-400' : d.win_rate >= 60 ? 'text-amber-400' : 'text-red-400'}`}>{d.win_rate}%</span>
                                  </td>
                                  <td className="py-2 px-3 text-xs font-bold text-emerald-400">₹{(d.pnl / 100000).toFixed(2)}L</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </>
                  );
                })()}
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
                      <div key={sym} className="flex items-center gap-1">
                        <button onClick={() => setSelectedSymbol(sym)}
                          className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${selectedSymbol === sym ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'}`}>
                          {sym}
                        </button>
                        <TVLink symbol={sym} className="text-slate-500 hover:text-blue-400 text-xs">📊</TVLink>
                      </div>
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

            {/* Recommendations Tab */}
            {activeTab === 'recommendations' && (
              <div className="flex flex-col gap-5">
                <div className="flex items-center justify-between flex-wrap gap-3">
                  <div>
                    <h2 className="text-base font-bold text-white flex items-center gap-2"><ArrowUpRight size={16} className="text-emerald-400" /> Trade Recommendations</h2>
                    <p className="text-xs text-slate-400 mt-0.5">Backtest-scored picks (2015–2026) with exact entry, strike, stop-loss & target</p>
                  </div>
                  <div className="flex items-center gap-3">
                    {recData && <span className="text-xs text-slate-500">Generated: {recData.generated_at}</span>}
                    <button onClick={loadRecs} disabled={recLoading}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-50 transition-colors">
                      <RefreshCw size={12} className={recLoading ? 'animate-spin' : ''} />
                      {recLoading ? 'Scanning...' : 'Refresh'}
                    </button>
                  </div>
                </div>

                {/* Summary pills */}
                {recData && (
                  <div className="flex gap-3 flex-wrap">
                    <div className="glass rounded-lg px-4 py-2 text-center">
                      <div className="text-lg font-bold text-white">{recData.total}</div>
                      <div className="text-xs text-slate-400">Total Picks</div>
                    </div>
                    <div className="glass rounded-lg px-4 py-2 text-center border border-emerald-500/30">
                      <div className="text-lg font-bold text-emerald-400">{recData.high_prob_count}</div>
                      <div className="text-xs text-slate-400">≥80% Win Prob</div>
                    </div>
                    <div className="glass rounded-lg px-4 py-2 text-center">
                      <div className="text-lg font-bold text-blue-400">{recData.recommendations?.filter(r=>r.option_type==='CE').length || 0}</div>
                      <div className="text-xs text-slate-400">BUY CE (Bullish)</div>
                    </div>
                    <div className="glass rounded-lg px-4 py-2 text-center">
                      <div className="text-lg font-bold text-red-400">{recData.recommendations?.filter(r=>r.option_type==='PE').length || 0}</div>
                      <div className="text-xs text-slate-400">BUY PE (Bearish)</div>
                    </div>
                  </div>
                )}

                {recLoading && <div className="flex items-center justify-center py-24 text-slate-400 text-sm animate-pulse">Scanning live NSE data & scoring with backtest engine...</div>}

                {!recLoading && recData?.recommendations?.length === 0 && (
                  <div className="glass rounded-xl p-10 text-center text-slate-400 text-sm">No high-confidence setups right now. Market may be sideways — check back after 9:30 AM.</div>
                )}

                {!recLoading && recData?.recommendations?.map(rec => (
                  <div key={rec.symbol + rec.strike + rec.option_type}
                    className={`glass rounded-xl p-5 border ${
                      rec.grade === 'A+' ? 'border-emerald-500/50' :
                      rec.grade === 'A'  ? 'border-emerald-500/30' :
                      rec.grade === 'B+' ? 'border-blue-500/30' :
                                          'border-slate-700/40'
                    }`}>

                    {/* Header row */}
                    <div className="flex items-start justify-between flex-wrap gap-3 mb-4">
                      <div className="flex items-center gap-3">
                        <div className={`text-lg font-black px-3 py-1 rounded-lg ${
                          rec.grade === 'A+' ? 'bg-emerald-500/20 text-emerald-300' :
                          rec.grade === 'A'  ? 'bg-emerald-500/10 text-emerald-400' :
                          rec.grade === 'B+' ? 'bg-blue-500/10 text-blue-300' :
                                              'bg-slate-700 text-slate-300'
                        }`}>{rec.grade}</div>
                        <div>
                          <div className="flex items-center gap-2">
                            <TVLink symbol={rec.symbol} className="text-white font-bold text-base hover:text-blue-400">{rec.symbol}</TVLink>
                            <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                              rec.option_type === 'CE' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
                            }`}>{rec.option_type === 'CE' ? '▲ CALL' : '▼ PUT'}</span>
                            <span className="text-xs text-slate-400">#{rec.rank}</span>
                          </div>
                          <div className="text-xs text-slate-400 mt-0.5">{rec.sector} · Signal Score: <span className="text-white font-semibold">{rec.signal_score}/100</span></div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className={`text-2xl font-black ${
                          rec.win_probability >= 80 ? 'text-emerald-400' : rec.win_probability >= 70 ? 'text-blue-400' : 'text-slate-300'
                        }`}>{rec.win_probability}%</div>
                        <div className="text-xs text-slate-400">Win Probability</div>
                      </div>
                    </div>

                    {/* Trade action banner */}
                    <div className={`rounded-lg px-4 py-3 mb-4 text-sm font-bold ${
                      rec.option_type === 'CE' ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300' : 'bg-red-500/10 border border-red-500/30 text-red-300'
                    }`}>
                      📌 {rec.action} · Expiry: {rec.expiry}
                    </div>

                    {/* Key numbers grid */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                      <div className="bg-slate-800/60 rounded-lg p-3">
                        <div className="text-xs text-slate-400 mb-1">Underlying Price</div>
                        <div className="text-sm font-bold text-white">₹{rec.underlying_price.toFixed(2)}</div>
                      </div>
                      <div className="bg-slate-800/60 rounded-lg p-3">
                        <div className="text-xs text-slate-400 mb-1">Strike Price</div>
                        <div className="text-sm font-bold text-yellow-300">₹{rec.strike}</div>
                      </div>
                      <div className="bg-slate-800/60 rounded-lg p-3">
                        <div className="text-xs text-slate-400 mb-1">Entry Premium</div>
                        <div className="text-sm font-bold text-blue-300">₹{rec.entry_premium}</div>
                      </div>
                      <div className="bg-slate-800/60 rounded-lg p-3">
                        <div className="text-xs text-slate-400 mb-1">Lot Size</div>
                        <div className="text-sm font-bold text-white">{rec.lot_size.toLocaleString()}</div>
                      </div>
                    </div>

                    {/* SL / Target / RR */}
                    <div className="grid grid-cols-3 gap-3 mb-4">
                      <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-center">
                        <div className="text-xs text-red-400 mb-1 font-medium">🛑 STOP LOSS</div>
                        <div className="text-base font-black text-red-300">₹{rec.stop_loss_premium}</div>
                        <div className="text-xs text-red-400/70">-₹{rec.sl_points} / unit</div>
                        <div className="text-xs text-red-400 font-semibold mt-1">Max Loss: ₹{rec.max_loss.toLocaleString()}</div>
                      </div>
                      <div className="bg-slate-800/60 border border-slate-700 rounded-lg p-3 text-center">
                        <div className="text-xs text-slate-400 mb-1 font-medium">📊 R:R RATIO</div>
                        <div className="text-base font-black text-white">{rec.rr_ratio} : 1</div>
                        <div className="text-xs text-slate-500">Risk/Reward</div>
                        <div className="text-xs text-slate-400 font-semibold mt-1">Capital: ₹{rec.capital_required.toLocaleString()}</div>
                      </div>
                      <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3 text-center">
                        <div className="text-xs text-emerald-400 mb-1 font-medium">🎯 TARGET</div>
                        <div className="text-base font-black text-emerald-300">₹{rec.target_premium}</div>
                        <div className="text-xs text-emerald-400/70">+₹{rec.target_points} / unit</div>
                        <div className="text-xs text-emerald-400 font-semibold mt-1">Max Profit: ₹{rec.max_profit.toLocaleString()}</div>
                      </div>
                    </div>

                    {/* Supporting data row */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
                      <div className="text-xs text-slate-400">Delivery %: <span className="text-white font-semibold">{rec.delivery_pct}%</span></div>
                      <div className="text-xs text-slate-400">Turnover: <span className="text-white font-semibold">₹{rec.turnover_cr}Cr</span></div>
                      <div className="text-xs text-slate-400">Sector Chg: <span className={rec.sector_change_pct >= 0 ? 'text-emerald-400 font-semibold' : 'text-red-400 font-semibold'}>{rec.sector_change_pct > 0 ? '+' : ''}{rec.sector_change_pct}%</span></div>
                      <div className="text-xs text-slate-400">5-min Low: <span className={rec.five_min_low_held ? 'text-emerald-400 font-semibold' : 'text-red-400 font-semibold'}>{rec.five_min_low_held ? '✅ Holding' : '❌ Broken'}</span></div>
                    </div>

                    {/* EV + timing */}
                    <div className="flex items-center justify-between flex-wrap gap-2 pt-3 border-t border-slate-800">
                      <div className="text-xs text-slate-400">
                        ⏰ Entry: <span className="text-white">{rec.entry_time}</span> &nbsp;|&nbsp;
                        Exit: <span className="text-white">{rec.exit_time}</span>
                      </div>
                      <div className={`text-xs font-semibold ${rec.expected_value >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        Expected Value: {rec.expected_value >= 0 ? '+' : ''}₹{rec.expected_value.toLocaleString()}
                      </div>
                    </div>
                    <div className="text-xs text-slate-600 mt-2 italic">{rec.basis}</div>
                  </div>
                ))}
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
                  <a href="#" target="_blank" rel="noopener noreferrer"
                    className="inline-block text-xs text-blue-400 underline mb-3" onClick={async (e) => {
                      e.preventDefault();
                      try {
                        const r = await getLoginUrl();
                        window.open(r.data.login_url, '_blank');
                      } catch(err) {
                        notify('Failed to get login URL', 'error');
                      }
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
