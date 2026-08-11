import React, { useState, useEffect } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import api from '../../api/client';
import {
  MessageSquare, FileText, BarChart2, Shield,
  LogOut, Plus, PanelLeft, Clock, Trash2, X
} from 'lucide-react';

const NAV = [
  { to: '/chat',      icon: MessageSquare, label: 'Chat' },
  { to: '/documents', icon: FileText,       label: 'Library' },
  { to: '/analytics', icon: BarChart2,      label: 'Analytics', roles: ['manager','admin'] },
  { to: '/admin',     icon: Shield,         label: 'Admin',     roles: ['admin'] },
];

export default function Sidebar({ isCollapsed, toggleSidebar, closeMobileSidebar, onNewChat, activeSessionId, onSelectSession }) {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [sessions, setSessions] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [editingName, setEditingName] = useState('');

  useEffect(() => {
    closeMobileSidebar?.();
  }, [location.pathname]);

  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      try {
        const { data } = await api.get('/api/chat/sessions');
        if (isMounted && data.sessions) setSessions(data.sessions);
      } catch { /* silent */ }
    };
    load();
    return () => { isMounted = false; };
  }, [location.pathname, activeSessionId]);

  const handleLogout = () => { logout(); navigate('/login'); };

  const startRename = (e, session) => {
    e.stopPropagation();
    setEditingId(session._id);
    setEditingName(session.name || '');
  };

  const commitRename = async (sessionId) => {
    const trimmed = editingName.trim();
    if (!trimmed) { setEditingId(null); return; }
    try {
      await api.patch(`/api/chat/sessions/${sessionId}`, { name: trimmed });
      setSessions(prev => prev.map(s => s._id === sessionId ? { ...s, name: trimmed } : s));
    } catch { /* silent */ }
    setEditingId(null);
  };

  const deleteSession = async (e, sessionId) => {
    e.stopPropagation();
    if (!window.confirm('Delete this chat? This cannot be undone.')) return;
    try {
      await api.delete(`/api/chat/sessions/${sessionId}`);
      setSessions(prev => prev.filter(s => s._id !== sessionId));
      // If the deleted session was active, clear the chat
      if (activeSessionId === sessionId) onSelectSession?.(null);
    } catch { /* silent */ }
  };

  const visibleNav = NAV.filter(n => !n.roles || n.roles.includes(user?.role));
  const initials = user?.full_name
    ?.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() || 'U';

  return (
    <aside className={`chat-gpt-sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      {/* Top Header */}
      <div className="sidebar-top">
        <div className="sidebar-brand">
          <div className="brand-logo">
            <img src="/Askra_logo.png" alt="Askra" className="brand-logo-img" />
          </div>
          {!isCollapsed && <span className="brand-name">Askra</span>}
        </div>
        <button className="sidebar-toggle-btn" onClick={toggleSidebar} title="Toggle Sidebar">
          <PanelLeft size={18} />
        </button>
        <button className="sidebar-close-btn" onClick={closeMobileSidebar} title="Close Menu">
          <X size={18} />
        </button>
      </div>

      {/* New Chat Button */}
      <div className="sidebar-action">
        <button className="new-chat-btn" onClick={() => { onNewChat?.(); navigate('/chat'); }}>
          <Plus size={18} />
          {!isCollapsed && <span>New chat</span>}
        </button>
      </div>

      {/* Main Navigation */}
      <nav className="sidebar-nav-list">
        {visibleNav.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to}
            className={({ isActive }) => `nav-item-gpt ${isActive ? 'active' : ''}`}
            title={label}
          >
            <Icon size={18} />
            {!isCollapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Recents Chat Sessions Section */}
      {!isCollapsed && (
        <div className="sidebar-recents">
          <div className="recents-header">
            <Clock size={12} />
            <span>Recents</span>
          </div>
          <div className="recents-list">
            {sessions.length === 0 ? (
              <div className="recents-empty">No recent chats</div>
            ) : (
              sessions.map((s) => (
                <div
                  key={s._id}
                  className={`recent-item ${s._id === activeSessionId ? 'active' : ''}`}
                  onClick={() => {
                    if (editingId === s._id) return;
                    onSelectSession?.(s._id);
                    navigate('/chat');
                  }}
                >
                  <MessageSquare size={14} className="recent-icon" />

                  {editingId === s._id ? (
                    <input
                      className="recent-rename-input"
                      value={editingName}
                      autoFocus
                      onChange={e => setEditingName(e.target.value)}
                      onBlur={() => commitRename(s._id)}
                      onKeyDown={e => {
                        if (e.key === 'Enter') { e.preventDefault(); commitRename(s._id); }
                        if (e.key === 'Escape') { setEditingId(null); }
                      }}
                      onClick={e => e.stopPropagation()}
                    />
                  ) : (
                    <>  
                      <span
                        className="recent-title"
                        onDoubleClick={e => startRename(e, s)}
                        title="Double-click to rename"
                      >
                        {s.name || `Session ${s._id.slice(-6)}`}
                      </span>
                      <button
                        className="rename-pencil-btn"
                        title="Rename"
                        onClick={e => startRename(e, s)}
                      >
                        ✏️
                      </button>
                      <button
                        className="delete-session-btn"
                        title="Delete chat"
                        onClick={e => deleteSession(e, s._id)}
                      >
                        <Trash2 size={13} />
                      </button>
                    </>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* User Footer Profile */}
      <div className="sidebar-user-footer">
        <div className="user-profile-card">
          <div className="user-avatar">{initials}</div>
          {!isCollapsed && (
            <div className="user-info">
              <div className="user-name">{user?.full_name}</div>
              <div className="user-role">{user?.role}</div>
            </div>
          )}
          {!isCollapsed && (
            <button className="logout-btn" onClick={handleLogout} title="Logout">
              <LogOut size={16} />
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
