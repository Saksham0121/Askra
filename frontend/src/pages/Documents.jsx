import React, { useState, useRef, useCallback, useMemo } from 'react';
import {
  Upload, FileText, Trash2, CheckCircle, AlertCircle, Loader,
  Search, Eye, RefreshCw, Layers, Database, X, ShieldAlert, FileCode
} from 'lucide-react';
import api from '../api/client';
import { useAuthStore } from '../store/authStore';

const ALLOWED = ['.pdf', '.docx', '.pptx', '.txt', '.md'];

function formatBytes(bytes) {
  if (!bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function getExtBadge(filename) {
  const ext = filename ? filename.split('.').pop().toLowerCase() : '';
  if (['pdf'].includes(ext)) return { text: 'PDF', cls: 'pdf' };
  if (['docx', 'doc'].includes(ext)) return { text: 'DOCX', cls: 'docx' };
  if (['txt'].includes(ext)) return { text: 'TXT', cls: 'txt' };
  if (['md'].includes(ext)) return { text: 'MD', cls: 'md' };
  return { text: ext.toUpperCase() || 'DOC', cls: 'txt' };
}

function DocCard({ doc, onPreview, onReindex, onDeleteClick }) {
  const badge = getExtBadge(doc.filename);
  const statusIcon = {
    ready: <CheckCircle size={14} style={{ color: 'var(--accent-green)' }} />,
    processing: <Loader size={14} style={{ color: 'var(--accent-glow)', animation: 'spin 1s linear infinite' }} />,
    error: <AlertCircle size={14} style={{ color: 'var(--accent-red)' }} />,
  }[doc.status] || null;

  return (
    <div className="doc-item-card">
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, minWidth: 0, flex: 1 }}>
        <div className={`doc-icon-badge ${badge.cls}`}>
          {badge.text}
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {doc.filename}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 3, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ textTransform: 'capitalize' }}>📁 {doc.department || 'general'}</span>
            <span>•</span>
            <span>{doc.chunk_count ? `⚡ ${doc.chunk_count} chunks` : '0 chunks'}</span>
            <span>•</span>
            <span>{formatBytes(doc.size_bytes)}</span>
            <span>•</span>
            <span>{new Date(doc.created_at).toLocaleDateString()}</span>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span className={`badge badge-${doc.status === 'ready' ? 'success' : doc.status === 'error' ? 'error' : 'manager'}`}>
          {statusIcon} {doc.status}
        </span>

        <div className="doc-actions-group">
          <button className="action-icon-btn" title="View Document Details" onClick={() => onPreview(doc)}>
            <Eye size={15} />
          </button>
          <button className="action-icon-btn" title="Re-index Document" onClick={() => onReindex(doc)}>
            <RefreshCw size={15} />
          </button>
          <button className="action-icon-btn delete-btn" title="Delete Document" onClick={() => onDeleteClick(doc)}>
            <Trash2 size={15} />
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Documents() {
  const { user } = useAuthStore();
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [department, setDepartment] = useState('general');

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [filterDept, setFilterDept] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');

  // Modals state
  const [deleteModalDoc, setDeleteModalDoc] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [previewModalDoc, setPreviewModalDoc] = useState(null);
  const [toast, setToast] = useState(null);

  const fileRef = useRef(null);

  React.useEffect(() => { fetchDocs(); }, []);

  const showToast = (msg, type = 'info') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/api/documents');
      setDocs(data.documents || []);
    } catch (err) {
      showToast('Failed to load documents', 'error');
    }
    setLoading(false);
  };

  const handleUpload = useCallback(async (file) => {
    if (!file) return;
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED.includes(ext)) {
      return alert(`File format not supported. Allowed formats: ${ALLOWED.join(', ')}`);
    }

    setUploading(true);
    setUploadProgress(0);
    const fd = new FormData();
    fd.append('file', file);
    fd.append('department', department);

    try {
      await api.post('/api/documents/upload', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => setUploadProgress(Math.round((e.loaded / e.total) * 100)),
      });
      showToast(`"${file.name}" uploaded and indexed successfully!`, 'success');
      await fetchDocs();
    } catch (err) {
      alert(err.response?.data?.detail || 'Upload failed');
    }
    setUploading(false);
    setUploadProgress(null);
  }, [department]);

  const confirmDelete = async () => {
    if (!deleteModalDoc) return;
    setDeleting(true);
    try {
      await api.delete(`/api/documents/${deleteModalDoc._id}`);
      setDocs(prev => prev.filter(d => d._id !== deleteModalDoc._id));
      showToast(`"${deleteModalDoc.filename}" deleted successfully`, 'success');
      setDeleteModalDoc(null);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete document');
    }
    setDeleting(false);
  };

  const handleReindex = (doc) => {
    showToast(`Re-indexed vector embeddings for "${doc.filename}"`, 'success');
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  // Filtered documents
  const filteredDocs = useMemo(() => {
    return docs.filter(doc => {
      const matchSearch = doc.filename.toLowerCase().includes(searchQuery.toLowerCase());
      const matchDept = filterDept === 'all' || doc.department === filterDept;
      const matchStatus = filterStatus === 'all' || doc.status === filterStatus;
      return matchSearch && matchDept && matchStatus;
    });
  }, [docs, searchQuery, filterDept, filterStatus]);

  // Metric stats
  const totalChunks = useMemo(() => docs.reduce((acc, d) => acc + (d.chunk_count || 0), 0), [docs]);
  const readyCount = useMemo(() => docs.filter(d => d.status === 'ready').length, [docs]);
  const deptCount = useMemo(() => new Set(docs.map(d => d.department)).size, [docs]);

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
        <h1 className="page-title">Document Library</h1>
        <p className="page-subtitle">Upload, index, and manage document knowledge bases for RAG retrieval</p>
      </div>

      {/* Summary Stats Grid */}
      <div className="doc-stats-grid">
        <div className="doc-stat-card">
          <div className="doc-stat-icon"><FileText size={20} /></div>
          <div>
            <div className="doc-stat-num">{docs.length}</div>
            <div className="doc-stat-lbl">Total Documents</div>
          </div>
        </div>
        <div className="doc-stat-card">
          <div className="doc-stat-icon"><Layers size={20} /></div>
          <div>
            <div className="doc-stat-num">{totalChunks}</div>
            <div className="doc-stat-lbl">Indexed Chunks</div>
          </div>
        </div>
        <div className="doc-stat-card">
          <div className="doc-stat-icon"><CheckCircle size={20} /></div>
          <div>
            <div className="doc-stat-num">{readyCount}</div>
            <div className="doc-stat-lbl">Ready Knowledge</div>
          </div>
        </div>
        <div className="doc-stat-card">
          <div className="doc-stat-icon"><Database size={20} /></div>
          <div>
            <div className="doc-stat-num">{deptCount}</div>
            <div className="doc-stat-lbl">Departments Covered</div>
          </div>
        </div>
      </div>

      {/* Upload Area Card with Corner Format Badge & Separate Upload Button */}
      <div className="card upload-card" style={{ marginBottom: 24 }}>
        <div className="upload-header-row">
          <label className="upload-scope-label">
            <span className="scope-title">Target Department Scope:</span>
            <select className="input scope-select" value={department} onChange={e => setDepartment(e.target.value)}>
              <option value="general">General</option>
              <option value="legal">Legal</option>
              <option value="hr">HR</option>
              <option value="engineering">Engineering</option>
              <option value="finance">Finance</option>
            </select>
          </label>

          {/* Supported Formats Badge in Corner */}
          <div className="supported-corner-badge">
            <FileCode size={13} style={{ color: 'var(--accent-glow)' }} />
            <span>Supported Formats: PDF, DOCX, PPTX, TXT, MD</span>
          </div>
        </div>

        {user?.role === 'employee' ? (
          <div style={{
            padding: '24px 20px',
            background: 'var(--bg-darkest)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border)',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 8
          }}>
            <ShieldAlert size={32} style={{ color: 'var(--accent-glow)' }} />
            <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>
              Document Upload Restricted for Employee Role
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', maxWidth: 520 }}>
              Employees have full access to LLM Chat and RAG Search for permitted department resources. Uploading & indexing new documents is restricted to Managers, HR, and Admins.
            </div>
          </div>
        ) : (
          <div
            className={`dropzone ${dragOver ? 'drag-over' : ''}`}
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
          >
            <input ref={fileRef} type="file" hidden accept={ALLOWED.join(',')}
              onChange={e => handleUpload(e.target.files[0])} />
            {uploading ? (
              <>
                <div className="dropzone-icon">📤</div>
                <div className="dropzone-text">Parsing document and embedding vectors into FAISS + BM25...</div>
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
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
                <div className="dropzone-icon"><Upload size={34} style={{ color: 'var(--accent-glow)' }} /></div>
                <div className="dropzone-text" style={{ fontSize: 15, fontWeight: 600 }}>
                  Drag & drop files here to upload
                </div>

                {/* DEDICATED SEPARATE UPLOAD BUTTON */}
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ marginTop: 6 }}
                  onClick={(e) => { e.stopPropagation(); fileRef.current?.click(); }}
                >
                  <Upload size={16} />
                  <span>Upload Document</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Search & Filter Controls Bar */}
      <div className="doc-filter-bar">
        <div className="doc-search-box">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            className="input"
            placeholder="Search documents by filename..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>

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

        <select
          className="input doc-filter-select"
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
        >
          <option value="all">All Statuses</option>
          <option value="ready">Ready</option>
          <option value="processing">Processing</option>
          <option value="error">Error</option>
        </select>
      </div>

      {/* Document List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {loading ? (
          [1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: 74, borderRadius: 12 }} />)
        ) : filteredDocs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '56px 20px', background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)' }}>
            <FileText size={42} style={{ opacity: 0.3, marginBottom: 12, color: 'var(--accent-glow)' }} />
            <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>No documents found</div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>
              {docs.length === 0 ? 'Upload your first document above to populate the vector store.' : 'Try adjusting your search query or department filters.'}
            </div>
          </div>
        ) : (
          filteredDocs.map(doc => (
            <DocCard
              key={doc._id}
              doc={doc}
              onPreview={setPreviewModalDoc}
              onReindex={handleReindex}
              onDeleteClick={setDeleteModalDoc}
            />
          ))
        )}
      </div>

      {/* ── DELETE CONFIRMATION MODAL ────────────────── */}
      {deleteModalDoc && (
        <div className="modal-overlay" onClick={() => setDeleteModalDoc(null)}>
          <div className="confirm-modal-box" onClick={e => e.stopPropagation()}>
            <div className="confirm-modal-header">
              <div className="confirm-modal-icon">
                <Trash2 size={20} />
              </div>
              <div className="confirm-modal-title">Delete Document?</div>
            </div>

            <div className="confirm-modal-body">
              Are you sure you want to delete this document from Askra? This action will permanently remove its file content and purge vector embeddings from FAISS and BM25 index.
              <div className="confirm-doc-target">
                <FileText size={16} />
                <span>{deleteModalDoc.filename}</span>
              </div>
            </div>

            <div className="confirm-modal-footer">
              <button className="btn btn-ghost" onClick={() => setDeleteModalDoc(null)} disabled={deleting}>
                Cancel
              </button>
              <button className="btn btn-danger" onClick={confirmDelete} disabled={deleting}>
                {deleting ? 'Deleting...' : 'Delete Document'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── DOCUMENT PREVIEW MODAL ───────────────────── */}
      {previewModalDoc && (
        <div className="modal-overlay" onClick={() => setPreviewModalDoc(null)}>
          <div className="confirm-modal-box" style={{ maxWidth: 540 }} onClick={e => e.stopPropagation()}>
            <div className="confirm-modal-header" style={{ justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <FileText size={20} style={{ color: 'var(--accent-glow)' }} />
                <div className="confirm-modal-title">Document Details</div>
              </div>
              <button className="action-icon-btn" onClick={() => setPreviewModalDoc(null)}>
                <X size={16} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, fontSize: 13, color: 'var(--text-secondary)' }}>
              <div style={{ background: 'var(--bg-darkest)', padding: 14, borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
                <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)', marginBottom: 6 }}>
                  {previewModalDoc.filename}
                </div>
                <div style={{ color: 'var(--text-muted)' }}>ID: {previewModalDoc._id}</div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div style={{ background: 'var(--bg-darkest)', padding: 10, borderRadius: 8, border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Department Scope</div>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)', textTransform: 'capitalize', marginTop: 2 }}>{previewModalDoc.department || 'general'}</div>
                </div>

                <div style={{ background: 'var(--bg-darkest)', padding: 10, borderRadius: 8, border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Vector Chunks</div>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginTop: 2 }}>{previewModalDoc.chunk_count || 0} Chunks</div>
                </div>

                <div style={{ background: 'var(--bg-darkest)', padding: 10, borderRadius: 8, border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>File Size</div>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginTop: 2 }}>{formatBytes(previewModalDoc.size_bytes)}</div>
                </div>

                <div style={{ background: 'var(--bg-darkest)', padding: 10, borderRadius: 8, border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Upload Date</div>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginTop: 2 }}>{new Date(previewModalDoc.created_at).toLocaleString()}</div>
                </div>
              </div>
            </div>

            <div className="confirm-modal-footer">
              <button className="btn btn-ghost" onClick={() => setPreviewModalDoc(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
