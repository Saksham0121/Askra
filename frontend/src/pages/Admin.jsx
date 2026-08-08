import React, { useEffect, useState } from 'react';
import { Shield, Trash2, Edit2, Check, X } from 'lucide-react';
import api from '../api/client';
import { useAuthStore } from '../store/authStore';

const ROLES = ['employee', 'manager', 'admin'];
const DEPTS = ['general', 'legal', 'hr', 'engineering', 'finance'];

function RoleBadge({ role }) {
  return <span className={`badge badge-${role}`}>{role}</span>;
}

export default function Admin() {
  const { user: me } = useAuthStore();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [editForm, setEditForm] = useState({});

  useEffect(() => { fetchUsers(); }, []);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/api/admin/users');
      setUsers(data.users);
    } catch {}
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
    } catch (err) {
      alert(err.response?.data?.detail || 'Update failed');
    }
  };

  const deleteUser = async (id) => {
    if (!confirm('Delete this user? This cannot be undone.')) return;
    try {
      await api.delete(`/api/admin/users/${id}`);
      setUsers(prev => prev.filter(u => u._id !== id));
    } catch (err) {
      alert(err.response?.data?.detail || 'Delete failed');
    }
  };

  return (
    <div className="page-body">
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
        <Shield size={22} style={{ color: 'var(--accent-violet)' }} />
        <div className="section-title">Admin Panel</div>
      </div>
      <div className="section-sub">Manage users, roles, and permissions</div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div style={{ fontSize: 14, fontWeight: 600 }}>
            All Users <span style={{ color: 'var(--text-muted)', fontWeight: 400, fontSize: 13 }}>({users.length})</span>
          </div>
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Department</th>
                <th>Status</th>
                <th>Joined</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                [1,2,3].map(i => (
                  <tr key={i}>
                    {[1,2,3,4,5,6,7].map(j => (
                      <td key={j}><div className="skeleton" style={{ height: 16, borderRadius: 4 }} /></td>
                    ))}
                  </tr>
                ))
              ) : users.map(user => (
                <tr key={user._id}>
                  <td style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{user.full_name}</td>
                  <td>{user.email}</td>
                  <td>
                    {editing === user._id ? (
                      <select className="input" style={{ padding: '4px 8px', fontSize: 12, width: 110 }}
                        value={editForm.role} onChange={e => setEditForm({ ...editForm, role: e.target.value })}>
                        {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                      </select>
                    ) : <RoleBadge role={user.role} />}
                  </td>
                  <td>
                    {editing === user._id ? (
                      <select className="input" style={{ padding: '4px 8px', fontSize: 12, width: 120 }}
                        value={editForm.department} onChange={e => setEditForm({ ...editForm, department: e.target.value })}>
                        {DEPTS.map(d => <option key={d} value={d}>{d}</option>)}
                      </select>
                    ) : user.department}
                  </td>
                  <td>
                    {editing === user._id ? (
                      <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
                        <input type="checkbox" checked={editForm.is_active}
                          onChange={e => setEditForm({ ...editForm, is_active: e.target.checked })} />
                        Active
                      </label>
                    ) : (
                      <span className={`badge badge-${user.is_active ? 'success' : 'error'}`}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    )}
                  </td>
                  <td>{new Date(user.created_at).toLocaleDateString()}</td>
                  <td>
                    {me?._id === user._id ? (
                      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>You</span>
                    ) : editing === user._id ? (
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button className="btn btn-primary btn-sm btn-icon" onClick={() => saveEdit(user._id)}>
                          <Check size={13} />
                        </button>
                        <button className="btn btn-ghost btn-sm btn-icon" onClick={() => setEditing(null)}>
                          <X size={13} />
                        </button>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button className="btn btn-ghost btn-sm btn-icon" onClick={() => startEdit(user)}>
                          <Edit2 size={13} />
                        </button>
                        <button className="btn btn-danger btn-sm btn-icon" onClick={() => deleteUser(user._id)}>
                          <Trash2 size={13} />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
