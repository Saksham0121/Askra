import React, { useState, useRef, useCallback } from 'react';
import { Upload, FileText, Trash2, CheckCircle, AlertCircle, Loader } from 'lucide-react';
import api from '../api/client';
import { useAuthStore } from '../store/authStore';

const ALLOWED = ['.pdf', '.docx', '.pptx', '.txt', '.md'];

function DocCard({ doc, onDelete, isAdmin }) {
  const statusIcon = {
    ready: <CheckCircle size={14} style={{ color: 'var(--accent-green)' }} />,
    processing: <Loader size={14} style={{ color: 'var(--accent-teal)', animation: 'spin 1s linear infinite' }} />,
    error: <AlertCircle size={14} style={{ color: 'var(--accent-red)' }} />,
  }[doc.status] || null;

  return (
    <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
      <div style={{ padding: 10, background: 'rgba(56,189,248,0.1)', borderRadius: 10 }}>
        <FileText size={22} style={{ color: 'var(--accent-teal)' }} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: 14, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {doc.filename}
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
          {doc.department} · {doc.chunk_count ? `${doc.chunk_count} chunks` : ''} · {new Date(doc.created_at).toLocaleDateString()}
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span className={`badge badge-${doc.status === 'ready' ? 'success' : doc.status === 'error' ? 'error' : 'manager'}`}>
          {statusIcon} {doc.status}
        </span>
        {isAdmin && (
          <button className="btn btn-danger btn-sm btn-icon" onClick={() => onDelete(doc._id)}>
            <Trash2 size={14} />
          </button>
        )}
      </div>
    </div>
  );
}

export default function Documents() {
  const { user } = useAuthStore();
  const isAdmin = user?.role === 'admin';
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [department, setDepartment] = useState('general');
  const fileRef = useRef(null);

  React.useEffect(() => { fetchDocs(); }, []);

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/api/documents');
      setDocs(data.documents);
    } catch {}
    setLoading(false);
  };

  const handleUpload = useCallback(async (file) => {
    if (!file) return;
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED.includes(ext)) return alert(`File type not supported. Use: ${ALLOWED.join(', ')}`);

    setUploading(true);
    setUploadProgress(0);
    const fd = new FormData();
    fd.append('file', file);
    fd.append('department', department);

    try {
      await api.post('/api/documents/upload', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => setUploadProgress(Math.round(e.loaded / e.total * 100)),
      });
      await fetchDocs();
    } catch (err) {
      alert(err.response?.data?.detail || 'Upload failed');
    }
    setUploading(false);
    setUploadProgress(null);
  }, [department]);

  const handleDelete = async (id) => {
    if (!confirm('Delete this document?')) return;
    try {
      await api.delete(`/api/documents/${id}`);
      setDocs(prev => prev.filter(d => d._id !== id));
    } catch (err) {
      alert(err.response?.data?.detail || 'Delete failed');
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  return (
    <div className="page-body">
      <div className="section-title">Documents</div>
      <div className="section-sub">Upload and manage your enterprise knowledge base</div>

      {/* Upload Area */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center' }}>
          <select className="input" style={{ width: 180 }} value={department} onChange={e => setDepartment(e.target.value)}>
            <option value="general">General</option>
            <option value="legal">Legal</option>
            <option value="hr">HR</option>
            <option value="engineering">Engineering</option>
            <option value="finance">Finance</option>
          </select>
          <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Select department before uploading</span>
        </div>

        <div
          className={`dropzone ${dragOver ? 'drag-over' : ''}`}
          onDragOver={e => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => !uploading && fileRef.current?.click()}
        >
          <input ref={fileRef} type="file" hidden accept={ALLOWED.join(',')}
            onChange={e => handleUpload(e.target.files[0])} />
          {uploading ? (
            <>
              <div className="dropzone-icon">📤</div>
              <div className="dropzone-text">Uploading & indexing...</div>
              <div style={{ marginTop: 12, width: '60%', margin: '12px auto 0' }}>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${uploadProgress}%` }} />
                </div>
                <div style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                  {uploadProgress}%
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="dropzone-icon"><Upload size={40} style={{ color: 'var(--accent-teal)' }} /></div>
              <div className="dropzone-text">Drag & drop a document here, or click to browse</div>
              <div className="dropzone-hint">Supported: PDF, DOCX, PPTX, TXT, MD</div>
            </>
          )}
        </div>
      </div>

      {/* Document List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {loading ? (
          [1,2,3].map(i => <div key={i} className="skeleton" style={{ height: 74, borderRadius: 12 }} />)
        ) : docs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)' }}>
            <FileText size={40} style={{ opacity: 0.3, marginBottom: 12 }} />
            <div>No documents yet. Upload your first document above.</div>
          </div>
        ) : docs.map(doc => (
          <DocCard key={doc._id} doc={doc} onDelete={handleDelete} isAdmin={isAdmin} />
        ))}
      </div>
    </div>
  );
}
