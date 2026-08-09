import React, { useEffect, useState } from 'react';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend
} from 'recharts';
import { TrendingUp, Zap, FileText, Users, Clock, Target } from 'lucide-react';
import api from '../api/client';

const COLORS = ['#38bdf8', '#a78bfa', '#34d399', '#fbbf24', '#f87171'];

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 14px', fontSize: 12 }}>
      <p style={{ color: 'var(--text-muted)', marginBottom: 4 }}>{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }}>{p.name}: <strong>{p.value}</strong></p>
      ))}
    </div>
  );
};

export default function Analytics() {
  const [overview, setOverview] = useState(null);
  const [trends, setTrends] = useState([]);
  const [toolUsage, setToolUsage] = useState([]);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchAll(); }, [days]);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [ov, tr, tu] = await Promise.all([
        api.get('/api/analytics/overview'),
        api.get(`/api/analytics/query-trends?days=${days}`),
        api.get('/api/analytics/tool-usage'),
      ]);
      setOverview(ov.data);
      setTrends(tr.data.trends);
      setToolUsage(tu.data.tool_usage.map(t => ({
        name: t.source.toUpperCase().replace('_', ' '),
        value: t.count,
      })));
    } catch {}
    setLoading(false);
  };

  const statCards = overview ? [
    { label: 'Total Queries', value: overview.total_queries, icon: TrendingUp, color: 'var(--accent-teal)' },
    { label: 'Documents', value: overview.total_documents, icon: FileText, color: 'var(--accent-violet)' },
    { label: 'Total Users', value: overview.total_users, icon: Users, color: 'var(--accent-green)' },
    { label: 'Avg Latency', value: `${overview.avg_latency_ms}ms`, icon: Clock, color: 'var(--accent-amber)' },
    { label: 'Avg Confidence', value: `${(overview.avg_confidence * 10).toFixed(0)}%`, icon: Target, color: 'var(--accent-teal)' },
  ] : [];

  return (
    <div className="page-body">
      <div className="page-header flex-header" style={{ marginBottom: 24 }}>
        <div>
          <h1 className="page-title">Analytics Dashboard</h1>
          <p className="page-subtitle">Pipeline performance and usage insights</p>
        </div>
        <select className="input analytics-days-select" style={{ width: 140 }} value={days} onChange={e => setDays(Number(e.target.value))}>
          <option value={7}>Last 7 days</option>
          <option value={14}>Last 14 days</option>
          <option value={30}>Last 30 days</option>
        </select>
      </div>

      {/* Stat Cards */}
      {loading ? (
        <div className="analytics-stat-grid" style={{ marginBottom: 24 }}>
          {[1,2,3,4,5].map(i => <div key={i} className="skeleton" style={{ height: 100, borderRadius: 12 }} />)}
        </div>
      ) : (
        <div className="analytics-stat-grid" style={{ marginBottom: 24 }}>
          {statCards.map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="card stat-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div className="stat-value" style={{ color }}>{value}</div>
                  <div className="stat-label">{label}</div>
                </div>
                <Icon size={20} style={{ color, opacity: 0.6 }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Charts Row */}
      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* Query Trends */}
        <div className="card">
          <div className="card-title">Query Volume</div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={trends}>
              <defs>
                <linearGradient id="cTeal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="queries" stroke="#38bdf8" fill="url(#cTeal)" strokeWidth={2} name="Queries" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Avg Confidence */}
        <div className="card">
          <div className="card-title">Avg Confidence Score (0–10)</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={trends}>
              <CartesianGrid stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <YAxis domain={[0, 10]} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="avg_confidence" fill="#a78bfa" radius={[4,4,0,0]} name="Confidence" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Tool Usage + Latency */}
      <div className="grid-2">
        <div className="card">
          <div className="card-title">Tool Usage Breakdown</div>
          {toolUsage.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={toolUsage} cx="50%" cy="50%" outerRadius={80} dataKey="value" nameKey="name" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                  {toolUsage.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              No data yet
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-title">Avg Response Latency (ms)</div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={trends}>
              <defs>
                <linearGradient id="cGreen" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#34d399" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#34d399" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="avg_latency_ms" stroke="#34d399" fill="url(#cGreen)" strokeWidth={2} name="Latency (ms)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
