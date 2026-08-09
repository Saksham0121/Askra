import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import { useAuthStore } from '../store/authStore';

export default function Login() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [form, setForm] = useState({ email: '', password: '', full_name: '', department: 'general', role: 'employee' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!form.email || !form.email.includes('@')) {
      setError('Please enter a valid email address.');
      return;
    }

    if (!form.password || form.password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }

    if (form.password.length > 72) {
      setError('Password cannot exceed 72 characters.');
      return;
    }

    if (mode === 'register' && !form.full_name.trim()) {
      setError('Full Name is required.');
      return;
    }

    setLoading(true);
    try {
      if (mode === 'login') {
        const { data } = await api.post('/auth/login', { email: form.email, password: form.password });
        setAuth(data.user, data.access_token, data.refresh_token);
        navigate('/chat');
      } else {
        await api.post('/auth/register', form);
        setMode('login');
        setSuccess('Account created successfully! Please sign in.');
      }
    } catch (err) {
      let errMsg = 'Something went wrong. Please try again.';
      const detail = err.response?.data?.detail;

      if (typeof detail === 'string') {
        errMsg = detail;
      } else if (Array.isArray(detail)) {
        errMsg = detail.map((item) => item.msg || item.message).filter(Boolean).join('. ');
      } else if (err.response?.data?.message) {
        errMsg = err.response.data.message;
      } else if (err.message) {
        errMsg = err.message;
      }

      setError(errMsg);
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
        {success && <div style={{ marginBottom: 16, padding: '12px 16px', background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)', borderRadius: 8, color: '#4ade80', fontSize: 13, textAlign: 'center' }}>{success}</div>}

        <form className="login-form" onSubmit={handleSubmit}>
          {mode === 'register' && (
            <>
              <div className="form-group">
                <label className="form-label">Full Name</label>
                <input className="input" name="full_name" placeholder="John Doe"
                  value={form.full_name} onChange={handleChange} required />
              </div>

              <div className="form-group">
                <label className="form-label">Organization Role</label>
                <select className="input" name="role" value={form.role} onChange={handleChange}>
                  <option value="admin">Admin</option>
                  <option value="hr">HR</option>
                  <option value="manager">Manager</option>
                  <option value="employee">Employee</option>
                </select>
              </div>

              {['manager', 'employee'].includes(form.role) && (
                <div className="form-group">
                  <label className="form-label">Department Scope</label>
                  <select className="input" name="department" value={form.department} onChange={handleChange}>
                    <option value="general">General</option>
                    <option value="legal">Legal</option>
                    <option value="hr">HR</option>
                    <option value="engineering">Engineering</option>
                    <option value="finance">Finance</option>
                  </select>
                </div>
              )}
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
