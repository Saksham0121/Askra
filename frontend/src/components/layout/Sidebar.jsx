import React, { useState, useEffect } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import api from '../../api/client';
import {
  MessageSquare, FileText, BarChart2, Shield,
  LogOut, Plus, PanelLeft, Clock, Sparkles
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

  useEffect(() => {
    closeMobileSidebar?.();
  }, [location.pathname]);

  useEffect(() => {
    let isMounted = true;
    const fetchSessions = async () => {
      try {
        const { data } = await api.get('/api/chat/sessions');
        if (isMounted && data.sessions) {
          setSessions(data.sessions);
        }
      } catch (err) {
        // Silent catch
      }
    };
    fetchSessions();
    return () => { isMounted = false; };
  }, [location.pathname, activeSessionId]);

  const handleLogout = () => { logout(); navigate('/login'); };

  const visibleNav = NAV.filter(n => !n.roles || n.roles.includes(user?.role));
  const initials = user?.full_name
    ?.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() || 'U';

  return (
    <aside className={`chat-gpt-sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      {/* Top Header */}
      <div className="sidebar-top">
        <div className="sidebar-brand">
          <div className="brand-logo">
            <Sparkles size={18} color="#FFAA85" />
          </div>
          {!isCollapsed && <span className="brand-name">Askrab</span>}
        </div>
        <button className="sidebar-toggle-btn" onClick={toggleSidebar} title="Toggle Sidebar">
          <PanelLeft size={18} />
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
                    onSelectSession?.(s._id);
                    navigate('/chat');
                  }}
                >
                  <MessageSquare size={14} className="recent-icon" />
                  <span className="recent-title">
                    Session {s._id.slice(-6)}
                  </span>
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
