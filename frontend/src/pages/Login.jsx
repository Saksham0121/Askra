import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import { useAuthStore } from '../store/authStore';

export default function Login() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [form, setForm] = useState({ email: '', password: '', full_name: '', department: 'general' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      if (mode === 'login') {
        const { data } = await api.post('/auth/login', { email: form.email, password: form.password });
        setAuth(data.user, data.access_token, data.refresh_token);
        navigate('/chat');
      } else {
        await api.post('/auth/register', form);
        setMode('login');
        setError('');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-bg" />

      <div className="login-card">
        <div className="login-logo">
          <div className="login-logo-text">Askrab</div>
          <div className="login-subtitle">Intelligent Agentic RAG System</div>
        </div>

        {error && <div className="login-error">{error}</div>}

        <form className="login-form" onSubmit={handleSubmit}>
          {mode === 'register' && (
            <>
              <div className="form-group">
                <label className="form-label">Full Name</label>
                <input className="input" name="full_name" placeholder="John Doe"
                  value={form.full_name} onChange={handleChange} required />
              </div>
              <div className="form-group">
                <label className="form-label">Department</label>
                <select className="input" name="department" value={form.department} onChange={handleChange}>
                  <option value="general">General</option>
                  <option value="legal">Legal</option>
                  <option value="hr">HR</option>
                  <option value="engineering">Engineering</option>
                  <option value="finance">Finance</option>
                </select>
              </div>
            </>
          )}

          <div className="form-group">
            <label className="form-label">Email</label>
            <input className="input" name="email" type="email" placeholder="you@company.com"
              value={form.email} onChange={handleChange} required />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input className="input" name="password" type="password" placeholder="••••••••"
              value={form.password} onChange={handleChange} required />
          </div>

          <button className="login-btn" type="submit" disabled={loading}>
            {loading ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <div className="login-switch">
          {mode === 'login' ? (
            <>Don't have an account? <span onClick={() => { setMode('register'); setError(''); }}>Sign up</span></>
          ) : (
            <>Already have an account? <span onClick={() => { setMode('login'); setError(''); }}>Sign in</span></>
          )}
        </div>

        {mode === 'login' && (
          <div style={{ marginTop: 24, padding: '12px', background: 'rgba(56,189,248,0.05)', borderRadius: 8, border: '1px solid rgba(56,189,248,0.1)', fontSize: 12, color: 'var(--text-muted)' }}>
            <strong style={{ color: 'var(--text-secondary)' }}>Demo credentials</strong><br />
            Register a new account to get started.
          </div>
        )}
      </div>
    </div>
  );
}
