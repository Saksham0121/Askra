import React, { useEffect, useState, useMemo } from 'react';
import {
  Shield, Trash2, Edit2, Check, X, Users, UserCheck, ShieldAlert,
  Search, AlertCircle, CheckCircle, Database
} from 'lucide-react';
import api from '../api/client';
import { useAuthStore } from '../store/authStore';

const ROLES = [
  { value: 'admin', label: 'Admin' },
  { value: 'hr', label: 'HR' },
  { value: 'manager', label: 'Manager' },
  { value: 'employee', label: 'Employee' },
];

const DEPTS = ['general', 'legal', 'hr', 'engineering', 'finance'];

function RoleBadge({ role }) {
  const r = (role || 'employee').toLowerCase();
  const labelMap = {
    admin: 'ADMIN',
    hr: 'HR',
    manager: 'MANAGER',
    employee: 'EMPLOYEE',
  };
  return (
    <span className={`badge badge-${r}`}>
      {labelMap[r] || r.toUpperCase()}
    </span>
  );
}

function UserAvatar({ name }) {
  const initials = name
    ? name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
    : 'U';
  return (
    <div style={{
      width: 34, height: 34, borderRadius: '50%',
      background: 'rgba(110,67,49,0.3)', border: '1px solid var(--border)',
      display: 'flex', alignItems: 'center', justifyCenter: 'center',
      fontSize: 12, fontWeight: 700, color: 'var(--accent-glow)', flexShrink: 0
    }}>
      {initials}
    </div>
  );
}

export default function Admin() {
  const { user: me } = useAuthStore();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [editForm, setEditForm] = useState({});

  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [filterRole, setFilterRole] = useState('all');
  const [filterDept, setFilterDept] = useState('all');

  // Modal & Notification state
  const [deleteTargetUser, setDeleteTargetUser] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => { fetchUsers(); }, []);

  const showToast = (msg, type = 'info') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/api/admin/users');
      setUsers(data.users || []);
    } catch (err) {
      showToast('Failed to fetch user directory', 'error');
    }
    setLoading(false);
  };

  const startEdit = (user) => {
    setEditing(user._id);
    setEditForm({ role: user.role, department: user.department, is_active: user.is_active });
  };

  const saveEdit = async (id) => {
    try {
      await api.patch(`/api/admin/users/${id}`, editForm);
      setUsers(prev => prev.map(u => u._id === id ? { ...u, ...editForm } : u));
      setEditing(null);
      showToast('User updated successfully', 'success');
    } catch (err) {
      alert(err.response?.data?.detail || 'Update failed');
    }
  };

  const confirmDeleteUser = async () => {
    if (!deleteTargetUser) return;
    setDeleting(true);
    try {
      await api.delete(`/api/admin/users/${deleteTargetUser._id}`);
      setUsers(prev => prev.filter(u => u._id !== deleteTargetUser._id));
      showToast(`User "${deleteTargetUser.full_name}" deleted successfully`, 'success');
      setDeleteTargetUser(null);
    } catch (err) {
      alert(err.response?.data?.detail || 'Delete failed');
    }
    setDeleting(false);
  };

  // Filtered Users
  const filteredUsers = useMemo(() => {
    return users.filter(u => {
      const matchSearch =
        u.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        u.email.toLowerCase().includes(searchQuery.toLowerCase());
      const matchRole = filterRole === 'all' || u.role === filterRole;
      const matchDept = filterDept === 'all' || u.department === filterDept;
      return matchSearch && matchRole && matchDept;
    });
  }, [users, searchQuery, filterRole, filterDept]);

  // Metric counts
  const countAdmin = useMemo(() => users.filter(u => u.role === 'admin').length, [users]);
  const countHR = useMemo(() => users.filter(u => u.role === 'hr').length, [users]);
  const countManager = useMemo(() => users.filter(u => u.role === 'manager').length, [users]);
  const countEmployee = useMemo(() => users.filter(u => u.role === 'employee').length, [users]);

  return (
    <div className="page-body">
      {/* Toast Notification */}
      {toast && (
        <div style={{
          position: 'fixed', top: 20, right: 20, zIndex: 1100,
          background: toast.type === 'error' ? 'var(--accent-red)' : 'var(--border-active)',
          color: '#fff', padding: '10px 18px', borderRadius: 'var(--radius-md)',
          boxShadow: 'var(--shadow-md)', fontWeight: 600, fontSize: 13, display: 'flex', alignItems: 'center', gap: 8
        }}>
          {toast.type === 'error' ? <AlertCircle size={16} /> : <CheckCircle size={16} />}
          <span>{toast.msg}</span>
        </div>
      )}

      {/* Page Header */}
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
          <Shield size={26} style={{ color: 'var(--accent-glow)' }} />
          <h1 className="page-title">Admin Management Console</h1>
        </div>
        <p className="page-subtitle">Manage organization users, role assignments, department scopes, and RBAC permissions</p>
      </div>

      {/* Summary Metrics Grid */}
      <div className="doc-stats-grid">
        <div className="doc-stat-card">
          <div className="doc-stat-icon"><Users size={20} /></div>
          <div>
            <div className="doc-stat-num">{users.length}</div>
            <div className="doc-stat-lbl">Total Registered Users</div>
          </div>
        </div>
        <div className="doc-stat-card">
          <div className="doc-stat-icon"><ShieldAlert size={20} /></div>
          <div>
            <div className="doc-stat-num">{countAdmin}</div>
            <div className="doc-stat-lbl">Admins</div>
          </div>
        </div>
        <div className="doc-stat-card">
          <div className="doc-stat-icon"><UserCheck size={20} /></div>
          <div>
            <div className="doc-stat-num">{countHR}</div>
            <div className="doc-stat-lbl">HR Specialists</div>
          </div>
        </div>
        <div className="doc-stat-card">
          <div className="doc-stat-icon"><Database size={20} /></div>
          <div>
            <div className="doc-stat-num">{countManager} / {countEmployee}</div>
            <div className="doc-stat-lbl">Managers / Employees</div>
          </div>
        </div>
      </div>

      {/* Main Table Card */}
      <div className="card">
        {/* Search & Filter Bar */}
        <div className="doc-filter-bar">
          <div className="doc-search-box">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              className="input"
              placeholder="Search users by name or email..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>

          <select
            className="input doc-filter-select"
            value={filterRole}
            onChange={e => setFilterRole(e.target.value)}
          >
            <option value="all">All Roles</option>
            <option value="admin">Admin</option>
            <option value="hr">HR Specialist</option>
            <option value="manager">Manager</option>
            <option value="employee">Employee</option>
          </select>

          <select
            className="input doc-filter-select"
            value={filterDept}
            onChange={e => setFilterDept(e.target.value)}
          >
            <option value="all">All Departments</option>
            <option value="general">General</option>
            <option value="legal">Legal</option>
            <option value="hr">HR</option>
            <option value="engineering">Engineering</option>
            <option value="finance">Finance</option>
          </select>
        </div>

        {/* Data Table */}
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>User Profile</th>
                <th>Email Address</th>
                <th>Role</th>
                <th>Department</th>
                <th>Status</th>
                <th>Joined Date</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                [1, 2, 3, 4].map(i => (
                  <tr key={i}>
                    {[1, 2, 3, 4, 5, 6, 7].map(j => (
                      <td key={j}><div className="skeleton" style={{ height: 20, borderRadius: 6 }} /></td>
                    ))}
                  </tr>
                ))
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
                    No matching users found in the directory.
                  </td>
                </tr>
              ) : (
                filteredUsers.map(user => (
                  <tr key={user._id}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <UserAvatar name={user.full_name} />
                        <div>
                          <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                            {user.full_name}
                            {me?._id === user._id && (
                              <span style={{ marginLeft: 8, fontSize: 11, background: 'var(--bg-card-hover)', color: 'var(--accent-glow)', padding: '2px 6px', borderRadius: 4, fontWeight: 600 }}>
                                YOU
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </td>

                    <td style={{ color: 'var(--text-muted)', fontFamily: 'monospace', fontSize: 12 }}>
                      {user.email}
                    </td>

                    <td>
                      {editing === user._id ? (
                        <select
                          className="input"
                          style={{ padding: '4px 8px', fontSize: 12, width: 120 }}
                          value={editForm.role}
                          onChange={e => setEditForm({ ...editForm, role: e.target.value })}
                        >
                          {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                        </select>
                      ) : (
                        <RoleBadge role={user.role} />
                      )}
                    </td>

                    <td>
                      {editing === user._id ? (
                        <select
                          className="input"
                          style={{ padding: '4px 8px', fontSize: 12, width: 130 }}
                          value={editForm.department}
                          onChange={e => setEditForm({ ...editForm, department: e.target.value })}
                        >
                          {DEPTS.map(d => <option key={d} value={d}>{d}</option>)}
                        </select>
                      ) : (
                        <span style={{ textTransform: 'capitalize', color: 'var(--text-secondary)' }}>
                          {user.department || 'general'}
                        </span>
                      )}
                    </td>

                    <td>
                      {editing === user._id ? (
                        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
                          <input
                            type="checkbox"
                            checked={editForm.is_active}
                            onChange={e => setEditForm({ ...editForm, is_active: e.target.checked })}
                          />
                          <span>Active</span>
                        </label>
                      ) : (
                        <span className={`badge badge-${user.is_active ? 'success' : 'error'}`}>
                          {user.is_active ? 'ACTIVE' : 'INACTIVE'}
                        </span>
                      )}
                    </td>

                    <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>

                    <td style={{ textAlign: 'right' }}>
                      {me?._id === user._id ? (
                        <span style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>Current User</span>
                      ) : editing === user._id ? (
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 6 }}>
                          <button className="action-icon-btn" title="Save Changes" onClick={() => saveEdit(user._id)}>
                            <Check size={14} style={{ color: 'var(--accent-green)' }} />
                          </button>
                          <button className="action-icon-btn" title="Cancel" onClick={() => setEditing(null)}>
                            <X size={14} style={{ color: 'var(--text-muted)' }} />
                          </button>
                        </div>
                      ) : (
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 6 }}>
                          <button className="action-icon-btn" title="Edit User Role & Department" onClick={() => startEdit(user)}>
                            <Edit2 size={14} />
                          </button>
                          <button className="action-icon-btn delete-btn" title="Delete User" onClick={() => setDeleteTargetUser(user)}>
                            <Trash2 size={14} />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Delete User Confirmation Modal */}
      {deleteTargetUser && (
        <div className="modal-overlay" onClick={() => setDeleteTargetUser(null)}>
          <div className="confirm-modal-box" onClick={e => e.stopPropagation()}>
            <div className="confirm-modal-header">
              <div className="confirm-modal-icon">
                <Trash2 size={20} />
              </div>
              <div className="confirm-modal-title">Delete User Account?</div>
            </div>

            <div className="confirm-modal-body">
              Are you sure you want to delete this user from the organization? This action will revoke all session access and remove their user account.
              <div className="confirm-doc-target">
                <span>👤 {deleteTargetUser.full_name} ({deleteTargetUser.email})</span>
              </div>
            </div>

            <div className="confirm-modal-footer">
              <button className="btn btn-ghost" onClick={() => setDeleteTargetUser(null)} disabled={deleting}>
                Cancel
              </button>
              <button className="btn btn-danger" onClick={confirmDeleteUser} disabled={deleting}>
                {deleting ? 'Deleting...' : 'Delete User'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
