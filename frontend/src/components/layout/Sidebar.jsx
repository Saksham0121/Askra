import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import {
  MessageSquare, FileText, BarChart2, Settings,
  Shield, LogOut, Zap
} from 'lucide-react';

const NAV = [
  { to: '/chat',      icon: MessageSquare, label: 'Chat' },
  { to: '/documents', icon: FileText,       label: 'Documents' },
  { to: '/analytics', icon: BarChart2,      label: 'Analytics', roles: ['manager','admin'] },
  { to: '/admin',     icon: Shield,         label: 'Admin',     roles: ['admin'] },
];

export default function Sidebar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => { logout(); navigate('/login'); };

  const visibleNav = NAV.filter(n => !n.roles || n.roles.includes(user?.role));

  const initials = user?.full_name
    ?.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() || 'U';

  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Zap size={20} style={{ color: 'var(--accent-teal)' }} />
          <div>
            <div className="sidebar-logo-title">Askrab</div>
            <div className="sidebar-logo-sub">7-Layer Agentic RAG</div>
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {visibleNav.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="user-card">
          <div className="avatar">{initials}</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="user-name" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.full_name}
            </div>
            <div className="user-role">{user?.role}</div>
          </div>
          <button className="btn-icon btn-ghost" onClick={handleLogout} title="Logout">
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
