import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'ngrok-skip-browser-warning': 'true',
  },
});

export const getHealth = () => api.get('/health');
export const getAuthStatus = () => api.get('/auth/status');
export const getLoginUrl = () => api.get('/auth/login-url');
export const createSession = (token) => api.post('/auth/session', { request_token: token });
export const getQuotes = () => api.get('/market/quote');
export const getOHLCV = (symbol) => api.get(`/market/ohlcv/${symbol}?days=2`);
export const getMarketContext = (symbol) => api.get(`/market/context/${symbol}`);
export const analyzeSymbol = (symbol) => api.get(`/ai/analyze/${symbol}`);
export const analyzeAll = () => api.get('/ai/analyze-all');
export const executeTrade = (symbol) => api.post(`/trade/execute/${symbol}`);
export const manualTrade = (data) => api.post('/trade/manual', data);
export const squareoffAll = () => api.post('/trade/squareoff-all');
export const getTradeHistory = () => api.get('/trade/history');
export const getOpenPositions = () => api.get('/trade/positions');
export const getRiskStats = () => api.get('/risk/stats');
export const resetDaily = () => api.post('/risk/reset-daily');
export const getBotStatus = () => api.get('/bot/status');
export const startBot = () => api.post('/bot/start');
export const stopBot = () => api.post('/bot/stop');
export const updateWatchlist = (symbols) => api.put('/bot/watchlist', { symbols });

export const strategyScan = (force = false) => api.get(`/strategy/scan?force=${force}`);
export const getSectors = () => api.get('/strategy/sectors');
export const getFilteredStocks = () => api.get('/strategy/stocks');
export const getOptionPicks = () => api.get('/strategy/options');
export const runBacktest = (startYear = 2015, endYear = 2026, minScore = 55) =>
  api.get(`/strategy/backtest?start_year=${startYear}&end_year=${endYear}&min_score=${minScore}`);
