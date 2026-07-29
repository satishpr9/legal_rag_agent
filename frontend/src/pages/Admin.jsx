import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Scale, ArrowLeft, Database, Upload, RefreshCw, Users, Shield, 
  Award, AlertCircle, FileText, CheckCircle2, Mail, Lock, LogOut, Search,
  Sparkles, FileUp, CheckCircle, Server
} from 'lucide-react';

export default function Admin() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');

  // Core States
  const [profile, setProfile] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [users, setUsers] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [docSearch, setDocSearch] = useState('');

  // Status States
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Admin Dedicated Login States
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);

  useEffect(() => {
    if (token) {
      fetchProfile();
    }
  }, [token]);

  const fetchProfile = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Unauthorized');
      const data = await res.json();

      if (data.role !== 'admin') {
        setError('Access Denied. Administrator privileges required.');
        setProfile(null);
        return;
      }

      setProfile(data);
      setError('');
      fetchDocuments();
      fetchUsers();
    } catch (err) {
      localStorage.removeItem('token');
      setProfile(null);
    }
  };

  const handleAdminLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoginLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await fetch('http://localhost:8000/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Authentication failed.');
      }

      const data = await response.json();
      localStorage.setItem('token', data.access_token);
      window.dispatchEvent(new Event('auth-change'));

      const profileRes = await fetch('http://localhost:8000/api/v1/auth/me', {
        headers: { 'Authorization': `Bearer ${data.access_token}` }
      });

      if (!profileRes.ok) throw new Error('Failed to load profile');
      const profileData = await profileRes.json();

      if (profileData.role !== 'admin') {
        localStorage.removeItem('token');
        throw new Error('Access Denied. Administrator privileges required.');
      }

      setProfile(profileData);
      setError('');
      fetchDocuments();
      fetchUsers();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoginLoading(false);
    }
  };

  const fetchDocuments = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/admin/documents', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to load documents');
      const data = await res.json();
      setDocuments(data);
    } catch (err) {
      setError('Failed to fetch documents catalog.');
    }
  };

  const fetchUsers = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/admin/users', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to load users');
      const data = await res.json();
      setUsers(data);
    } catch (err) {
      setError('Failed to load users catalog.');
    }
  };

  const handleUploadDocument = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;
    setUploading(true);
    setError('');
    setSuccess('');

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const res = await fetch('http://localhost:8000/api/v1/admin/documents/upload', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to upload document');
      }

      setSuccess(`Document "${selectedFile.name}" ingested successfully! Vector indexing complete.`);
      setSelectedFile(null);
      await fetchDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const filteredDocuments = documents.filter(doc => 
    doc.filename.toLowerCase().includes(docSearch.toLowerCase())
  );

  // Unauthenticated / Non-Admin Fallback View
  if (!profile) {
    return (
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2.5rem 1.5rem',
        minHeight: 'calc(100vh - 65px)'
      }}>
        <div className="glass-card animate-fade-in" style={{ maxWidth: '440px', width: '100%', padding: '2.5rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <div style={{
              width: '56px',
              height: '56px',
              borderRadius: '14px',
              background: 'rgba(226, 184, 87, 0.15)',
              border: '1px solid var(--accent-gold)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent-gold)',
              marginBottom: '1rem',
              boxShadow: 'var(--shadow-glow-gold)'
            }}>
              <Shield size={28} />
            </div>
            <h2 style={{ fontSize: '1.6rem', fontWeight: 800, marginBottom: '0.4rem' }}>Admin Console Access</h2>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)' }}>Enter administrator credentials to manage vector index & users</p>
          </div>

          {error && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              background: 'rgba(244, 63, 94, 0.12)',
              border: '1px solid rgba(244, 63, 94, 0.3)',
              padding: '0.8rem 1rem',
              borderRadius: 'var(--radius-md)',
              color: 'var(--accent-danger)',
              fontSize: '0.85rem',
              marginBottom: '1.5rem'
            }}>
              <AlertCircle size={18} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleAdminLogin}>
            <div className="input-group">
              <label className="input-label" htmlFor="admin-email">Admin Email</label>
              <div style={{ position: 'relative' }}>
                <input
                  className="input-field"
                  type="email"
                  id="admin-email"
                  placeholder="admin@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  style={{ width: '100%', paddingLeft: '2.5rem' }}
                  required
                />
                <Mail size={16} color="var(--text-subtle)" style={{ position: 'absolute', left: '0.9rem', top: '50%', transform: 'translateY(-50%)' }} />
              </div>
            </div>

            <div className="input-group">
              <label className="input-label" htmlFor="admin-password">Password</label>
              <div style={{ position: 'relative' }}>
                <input
                  className="input-field"
                  type="password"
                  id="admin-password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={{ width: '100%', paddingLeft: '2.5rem' }}
                  required
                />
                <Lock size={16} color="var(--text-subtle)" style={{ position: 'absolute', left: '0.9rem', top: '50%', transform: 'translateY(-50%)' }} />
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-gold"
              disabled={loginLoading}
              style={{ width: '100%', padding: '0.85rem', marginTop: '1rem' }}
            >
              {loginLoading ? 'Authenticating...' : 'Sign In to Console'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // Admin Dashboard Main Layout
  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      padding: '2rem',
      maxWidth: '1400px',
      margin: '0 auto',
      width: '100%',
      gap: '2rem'
    }}>
      {/* Console Title Banner */}
      <div className="glass-card" style={{ padding: '1.5rem 2rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            width: '44px',
            height: '44px',
            borderRadius: '12px',
            background: 'var(--accent-gold-gradient)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#060912',
            boxShadow: 'var(--shadow-glow-gold)'
          }}>
            <Shield size={22} />
          </div>
          <div>
            <h1 style={{ fontSize: '1.4rem', fontWeight: 800 }}>Admin Command Center</h1>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Document Ingestion Studio & Platform Management</p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button className="btn btn-ghost" onClick={fetchDocuments}>
            <RefreshCw size={15} /> Sync State
          </button>
        </div>
      </div>

      {/* Status Alerts */}
      {error && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.6rem',
          background: 'rgba(244, 63, 94, 0.12)',
          border: '1px solid rgba(244, 63, 94, 0.3)',
          padding: '1rem 1.2rem',
          borderRadius: 'var(--radius-md)',
          color: 'var(--accent-danger)'
        }}>
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.6rem',
          background: 'rgba(16, 185, 129, 0.12)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          padding: '1rem 1.2rem',
          borderRadius: 'var(--radius-md)',
          color: 'var(--accent-success)'
        }}>
          <CheckCircle size={20} />
          <span>{success}</span>
        </div>
      )}

      {/* Metrics Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
        <div className="glass-card glass-card-hover" style={{ padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '1.2rem' }}>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '12px',
            background: 'rgba(226, 184, 87, 0.12)',
            border: '1px solid var(--accent-gold)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--accent-gold)'
          }}>
            <FileText size={22} />
          </div>
          <div>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-subtle)', textTransform: 'uppercase' }}>Indexed Documents</span>
            <h3 style={{ fontSize: '1.8rem', fontWeight: 800, marginTop: '0.1rem' }}>{documents.length}</h3>
          </div>
        </div>

        <div className="glass-card glass-card-hover" style={{ padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '1.2rem' }}>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '12px',
            background: 'rgba(56, 189, 248, 0.12)',
            border: '1px solid var(--accent-blue)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--accent-blue)'
          }}>
            <Users size={22} />
          </div>
          <div>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-subtle)', textTransform: 'uppercase' }}>Registered Users</span>
            <h3 style={{ fontSize: '1.8rem', fontWeight: 800, marginTop: '0.1rem' }}>{users.length}</h3>
          </div>
        </div>

        <div className="glass-card glass-card-hover" style={{ padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '1.2rem' }}>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '12px',
            background: 'rgba(16, 185, 129, 0.12)',
            border: '1px solid var(--accent-success)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--accent-success)'
          }}>
            <Server size={22} />
          </div>
          <div>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-subtle)', textTransform: 'uppercase' }}>Qdrant Vector DB</span>
            <span className="badge badge-success" style={{ marginTop: '0.4rem', display: 'inline-flex' }}>
              Connected & Healthy
            </span>
          </div>
        </div>
      </div>

      {/* Main Console Studio Split Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '2rem' }}>
        
        {/* Document Ingestion Studio Table */}
        <div className="glass-card" style={{ padding: '1.8rem', display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Database size={18} color="var(--accent-gold)" /> Ingested Legal Documents
            </h2>
          </div>

          <div style={{ position: 'relative' }}>
            <input
              className="input-field"
              type="text"
              placeholder="Filter catalog by document title..."
              value={docSearch}
              onChange={(e) => setDocSearch(e.target.value)}
              style={{ width: '100%', paddingLeft: '2.4rem', fontSize: '0.88rem' }}
            />
            <Search size={16} color="var(--text-subtle)" style={{ position: 'absolute', left: '0.9rem', top: '50%', transform: 'translateY(-50%)' }} />
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--glass-border-subtle)', textAlign: 'left', color: 'var(--text-subtle)' }}>
                  <th style={{ padding: '0.75rem 0.5rem', fontWeight: 700 }}>Filename</th>
                  <th style={{ padding: '0.75rem 0.5rem', fontWeight: 700 }}>Date</th>
                  <th style={{ padding: '0.75rem 0.5rem', fontWeight: 700, textAlign: 'right' }}>Indexing Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredDocuments.length > 0 ? (
                  filteredDocuments.map(doc => (
                    <tr key={doc.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.03)' }}>
                      <td style={{ padding: '0.85rem 0.5rem', fontWeight: 600, color: 'var(--text-main)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <FileText size={15} color="var(--accent-gold)" />
                          <span>{doc.filename}</span>
                        </div>
                      </td>
                      <td style={{ padding: '0.85rem 0.5rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                        {new Date(doc.created_at).toLocaleDateString()}
                      </td>
                      <td style={{ padding: '0.85rem 0.5rem', textAlign: 'right' }}>
                        <span className={`badge ${doc.status === 'completed' ? 'badge-success' : doc.status === 'failed' ? 'badge-danger' : 'badge-gold'}`}>
                          {doc.status || 'indexed'}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={3} style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-subtle)' }}>
                      No matching documents found in catalog.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Side: Upload Studio & User Directory */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          
          {/* File Upload Studio */}
          <div className="glass-card" style={{ padding: '1.8rem' }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FileUp size={18} color="var(--accent-gold)" /> Ingest & Embed New Document
            </h2>

            <form onSubmit={handleUploadDocument} style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
              <div style={{
                border: '2px dashed var(--glass-border)',
                borderRadius: 'var(--radius-lg)',
                padding: '2.5rem 1.5rem',
                textAlign: 'center',
                background: 'rgba(6, 9, 18, 0.4)',
                cursor: 'pointer',
                position: 'relative',
                transition: 'var(--transition-smooth)'
              }}>
                <input
                  type="file"
                  accept=".pdf,.txt,.docx"
                  onChange={(e) => setSelectedFile(e.target.files[0])}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    opacity: 0,
                    cursor: 'pointer'
                  }}
                  required
                />
                <div style={{ pointerEvents: 'none', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.6rem' }}>
                  <Upload size={32} color="var(--accent-gold)" />
                  <span style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-main)' }}>
                    {selectedFile ? selectedFile.name : 'Select PDF, TXT, or DOCX File'}
                  </span>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-subtle)' }}>
                    Automated chunking & Qdrant vector embedding will launch on upload
                  </span>
                </div>
              </div>

              <button
                type="submit"
                className="btn btn-gold"
                disabled={uploading || !selectedFile}
                style={{ width: '100%', padding: '0.85rem' }}
              >
                {uploading ? 'Processing File & Generating Embeddings...' : 'Ingest Document into RAG'}
              </button>
            </form>
          </div>

          {/* User Management List */}
          <div className="glass-card" style={{ padding: '1.8rem' }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Users size={18} color="var(--accent-blue)" /> Platform User Directory
            </h2>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {users.map(u => (
                <div
                  key={u.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.75rem 1rem',
                    background: 'rgba(20, 29, 51, 0.5)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--glass-border-subtle)'
                  }}
                >
                  <div>
                    <h4 style={{ fontSize: '0.9rem', fontWeight: 700 }}>{u.full_name || 'User'}</h4>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-subtle)' }}>{u.email}</span>
                  </div>

                  <span className={`badge ${u.role === 'admin' ? 'badge-gold' : 'badge-blue'}`}>
                    {u.role}
                  </span>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
