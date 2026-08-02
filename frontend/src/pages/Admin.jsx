import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Shield, Database, Upload, RefreshCw, Users, FileText, 
  CheckCircle2, Mail, Lock, Search, FileUp, CheckCircle, 
  Server, LayoutDashboard, FolderKanban, UserCheck, AlertCircle,
  Activity, Layers, ArrowUpRight, HardDrive, Trash2, LogOut, Sparkles, Sliders
} from 'lucide-react';

export default function Admin() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');

  // Active Tab: 'dashboard' | 'documents' | 'users' | 'health'
  const [activeTab, setActiveTab] = useState('dashboard');

  // Core States
  const [profile, setProfile] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [users, setUsers] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [docSearch, setDocSearch] = useState('');
  const [userSearch, setUserSearch] = useState('');
  
  const [metadata, setMetadata] = useState({
    workspace: 'Labour Law'
  });

  // Status States
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
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

  useEffect(() => {
    if (!profile) return;
    
    // Connect to the new WebSocket endpoint
    const ws = new WebSocket('ws://localhost:8000/api/v1/admin/documents/ws');
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // data format: { document_id, filename, status }
        
        // Use functional state update to patch the specific document's status
        setDocuments(prevDocs => 
          prevDocs.map(doc => 
            doc.id === data.document_id ? { ...doc, status: data.status } : doc
          )
        );
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };

    ws.onclose = () => {
      console.log("WebSocket connection closed.");
    };

    return () => {
      ws.close();
    };
  }, [profile]);

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
      if(metadata.workspace) formData.append('workspace', metadata.workspace);

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

  const handleDeleteDocument = async (docId, filename) => {

    setDeletingId(docId);
    setError('');
    setSuccess('');

    try {
      const res = await fetch(`http://localhost:8000/api/v1/admin/documents/${docId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to delete document');
      }

      setSuccess(`Document "${filename}" deleted successfully.`);
      // Pure React State Updater for instant reactivity
      setDocuments(prevDocs => prevDocs.filter(doc => doc.id !== docId));
    } catch (err) {
      setError(err.message);
      fetchDocuments();
    } finally {
      setDeletingId(null);
    }
  };

  const handleDeleteUser = async (userId, userEmail) => {
    if (profile?.id === userId) {
      setError("Cannot delete your own administrator account.");
      return;
    }

    if (!window.confirm(`Are you sure you want to delete user account "${userEmail}"?`)) {
      return;
    }

    setError('');
    setSuccess('');

    // Pure React State Updater for instant reactivity
    setUsers(prevUsers => prevUsers.filter(u => u.id !== userId));

    try {
      const res = await fetch(`http://localhost:8000/api/v1/admin/users/${userId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to delete user');
      }

      setSuccess(`User "${userEmail}" deleted successfully.`);
    } catch (err) {
      setError(err.message);
      fetchUsers();
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    window.dispatchEvent(new Event('auth-change'));
    navigate('/login');
  };

  const filteredDocuments = documents.filter(doc => 
    doc.filename.toLowerCase().includes(docSearch.toLowerCase())
  );

  const filteredUsers = users.filter(u =>
    u.full_name?.toLowerCase().includes(userSearch.toLowerCase()) ||
    u.email?.toLowerCase().includes(userSearch.toLowerCase())
  );

  // Unauthenticated Fallback Card
  if (!profile) {
    return (
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2.5rem 1.5rem',
        minHeight: 'calc(100vh - 65px)',
        background: '#f8fafc'
      }}>
        <div className="glass-card animate-fade-in" style={{ maxWidth: '420px', width: '100%', padding: '2.5rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <div style={{
              width: '52px',
              height: '52px',
              borderRadius: '12px',
              background: 'rgba(37, 99, 235, 0.1)',
              border: '1px solid var(--accent-primary)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent-primary)',
              marginBottom: '1rem'
            }}>
              <Shield size={26} />
            </div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: '0.4rem', color: '#0f172a' }}>Admin Console Access</h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Enter administrator credentials to access system dashboard</p>
          </div>

          {error && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              background: 'rgba(220, 38, 38, 0.08)',
              border: '1px solid rgba(220, 38, 38, 0.25)',
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
              className="btn btn-primary"
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

  // Admin Panel Main Layout with Left Vertical Sidebar
  return (
    <div style={{
      display: 'flex',
      flex: 1,
      height: '100vh',
      width: '100vw',
      background: '#f8fafc',
      overflow: 'hidden'
    }}>
      {/* LEFT SIDEBAR NAVIGATION */}
      <aside style={{
        width: '280px',
        background: '#ffffff',
        borderRight: '1px solid #e2e8f0',
        display: 'flex',
        flexDirection: 'column',
        padding: '1.4rem 1.2rem',
        justifyContent: 'space-between',
        height: '100%'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Admin Header Branding */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', paddingBottom: '1rem', borderBottom: '1px solid #e2e8f0' }}>
            <div style={{
              width: '38px',
              height: '38px',
              borderRadius: '10px',
              background: 'var(--accent-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff'
            }}>
              <Shield size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 800, color: '#0f172a' }}>Admin Panel</h3>
              <span className="badge badge-gold" style={{ fontSize: '0.62rem', padding: '0.05rem 0.35rem' }}>
                ADMINISTRATOR
              </span>
            </div>
          </div>

          {/* Navigation Menu Links */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            <button
              onClick={() => navigate('/chat')}
              className="btn btn-ghost btn-sm"
              style={{ width: '100%', justifyContent: 'flex-start', fontSize: '0.85rem', marginBottom: '0.6rem', gap: '0.6rem' }}
            >
              <FileText size={16} color="var(--accent-primary)" />
              <span>Back to AI Chat</span>
            </button>

            <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-subtle)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.4rem' }}>
              Dashboard Options
            </div>

            <button
              onClick={() => setActiveTab('dashboard')}
              className={`btn ${activeTab === 'dashboard' ? 'btn-primary' : 'btn-ghost'}`}
              style={{ width: '100%', justifyContent: 'flex-start', fontSize: '0.85rem' }}
            >
              <LayoutDashboard size={16} /> Overview
            </button>

            <button
              onClick={() => setActiveTab('documents')}
              className={`btn ${activeTab === 'documents' ? 'btn-primary' : 'btn-ghost'}`}
              style={{ width: '100%', justifyContent: 'flex-start', fontSize: '0.85rem' }}
            >
              <Database size={16} /> Documents Catalog
            </button>

            <button
              onClick={() => setActiveTab('users')}
              className={`btn ${activeTab === 'users' ? 'btn-primary' : 'btn-ghost'}`}
              style={{ width: '100%', justifyContent: 'flex-start', fontSize: '0.85rem' }}
            >
              <Users size={16} /> User Management
            </button>

            <button
              onClick={() => setActiveTab('health')}
              className={`btn ${activeTab === 'health' ? 'btn-primary' : 'btn-ghost'}`}
              style={{ width: '100%', justifyContent: 'flex-start', fontSize: '0.85rem' }}
            >
              <Activity size={16} /> System Infrastructure
            </button>
          </div>
        </div>

        {/* Bottom Profile Info & Sign Out */}
        <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Logged in as <strong>{profile?.full_name || profile?.email}</strong>
          </div>
          <button
            onClick={handleLogout}
            className="btn btn-danger btn-sm"
            style={{ width: '100%', fontSize: '0.8rem' }}
          >
            <LogOut size={14} /> Sign Out Admin
          </button>
        </div>
      </aside>

      {/* RIGHT MAIN PANEL */}
      <main style={{
        flex: 1,
        padding: '2rem',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem',
        maxWidth: '1200px'
      }}>
        {/* Global Alerts */}
        {error && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.6rem',
            background: 'rgba(220, 38, 38, 0.08)',
            border: '1px solid rgba(220, 38, 38, 0.25)',
            padding: '0.9rem 1.2rem',
            borderRadius: 'var(--radius-md)',
            color: 'var(--accent-danger)',
            fontSize: '0.88rem'
          }}>
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}
        {success && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.6rem',
            background: 'rgba(22, 163, 74, 0.08)',
            border: '1px solid rgba(22, 163, 74, 0.25)',
            padding: '0.9rem 1.2rem',
            borderRadius: 'var(--radius-md)',
            color: 'var(--accent-success)',
            fontSize: '0.88rem'
          }}>
            <CheckCircle size={18} />
            <span>{success}</span>
          </div>
        )}

        {/* TAB 1: DASHBOARD OVERVIEW */}
        {activeTab === 'dashboard' && (
          <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1.8rem' }}>
            <div>
              <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#0f172a' }}>Dashboard Overview</h2>
              <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)' }}>Real-time summary of legal documents, users, and vector database status</p>
            </div>

            {/* Key Metrics Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.2rem' }}>
              <div className="glass-card glass-card-hover" style={{ padding: '1.4rem', display: 'flex', alignItems: 'center', gap: '1.2rem' }}>
                <div style={{
                  width: '46px',
                  height: '46px',
                  borderRadius: '12px',
                  background: 'rgba(37, 99, 235, 0.1)',
                  border: '1px solid rgba(37, 99, 235, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--accent-primary)'
                }}>
                  <FileText size={22} />
                </div>
                <div>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-subtle)', textTransform: 'uppercase' }}>Total Ingested Files</span>
                  <h3 style={{ fontSize: '1.8rem', fontWeight: 800, marginTop: '0.1rem', color: '#0f172a' }}>{documents.length}</h3>
                </div>
              </div>

              <div className="glass-card glass-card-hover" style={{ padding: '1.4rem', display: 'flex', alignItems: 'center', gap: '1.2rem' }}>
                <div style={{
                  width: '46px',
                  height: '46px',
                  borderRadius: '12px',
                  background: 'rgba(217, 119, 6, 0.1)',
                  border: '1px solid rgba(217, 119, 6, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--accent-gold)'
                }}>
                  <Users size={22} />
                </div>
                <div>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-subtle)', textTransform: 'uppercase' }}>Registered Users</span>
                  <h3 style={{ fontSize: '1.8rem', fontWeight: 800, marginTop: '0.1rem', color: '#0f172a' }}>{users.length}</h3>
                </div>
              </div>

              <div className="glass-card glass-card-hover" style={{ padding: '1.4rem', display: 'flex', alignItems: 'center', gap: '1.2rem' }}>
                <div style={{
                  width: '46px',
                  height: '46px',
                  borderRadius: '12px',
                  background: 'rgba(22, 163, 74, 0.1)',
                  border: '1px solid rgba(22, 163, 74, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--accent-success)'
                }}>
                  <Server size={22} />
                </div>
                <div>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-subtle)', textTransform: 'uppercase' }}>Qdrant Vector DB</span>
                  <span className="badge badge-success" style={{ marginTop: '0.3rem', display: 'inline-flex' }}>
                    Port 6333 Healthy
                  </span>
                </div>
              </div>
            </div>

            {/* Quick Actions & Recent Summary Split */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '1.5rem' }}>
              <div className="glass-card" style={{ padding: '1.6rem' }}>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Activity size={18} color="var(--accent-primary)" /> Quick Management Shortcuts
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
                  <div
                    onClick={() => setActiveTab('documents')}
                    className="glass-card glass-card-hover"
                    style={{ padding: '1rem 1.2rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <FileUp size={18} color="var(--accent-primary)" />
                      <div>
                        <h4 style={{ fontSize: '0.92rem', fontWeight: 700 }}>Document Ingestion & Delete Studio</h4>
                        <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Upload new PDF files or remove obsolete documents</p>
                      </div>
                    </div>
                    <ArrowUpRight size={16} color="var(--text-subtle)" />
                  </div>

                  <div
                    onClick={() => setActiveTab('users')}
                    className="glass-card glass-card-hover"
                    style={{ padding: '1rem 1.2rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <Users size={18} color="var(--accent-gold)" />
                      <div>
                        <h4 style={{ fontSize: '0.92rem', fontWeight: 700 }}>Review Registered User Accounts</h4>
                        <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Check associate and partner roles</p>
                      </div>
                    </div>
                    <ArrowUpRight size={16} color="var(--text-subtle)" />
                  </div>
                </div>
              </div>

              {/* Status Breakdown */}
              <div className="glass-card" style={{ padding: '1.6rem' }}>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Layers size={18} color="var(--accent-gold)" /> Ingestion Status Breakdown
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', background: '#f8fafc', borderRadius: 'var(--radius-md)', border: '1px solid #e2e8f0' }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Successfully Indexed</span>
                    <span className="badge badge-success">{documents.filter(d => d.status === 'completed').length} Documents</span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', background: '#f8fafc', borderRadius: 'var(--radius-md)', border: '1px solid #e2e8f0' }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Processing</span>
                    <span className="badge badge-gold">{documents.filter(d => d.status !== 'completed' && d.status !== 'failed').length} Documents</span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', background: '#f8fafc', borderRadius: 'var(--radius-md)', border: '1px solid #e2e8f0' }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Failed Ingestions</span>
                    <span className="badge badge-danger">{documents.filter(d => d.status === 'failed').length} Documents</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: DOCUMENT STUDIO WITH DELETE OPTION */}
        {activeTab === 'documents' && (
          <div className="animate-fade-in" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1.8rem' }}>
            {/* File Upload Studio Form */}
            <div className="glass-card" style={{ padding: '1.8rem' }}>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FileUp size={18} color="var(--accent-primary)" /> Ingest & Embed Legal Document
              </h2>

              <form onSubmit={handleUploadDocument} style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
                <div style={{
                  border: '2px dashed #cbd5e1',
                  borderRadius: 'var(--radius-lg)',
                  padding: '2.5rem 1.5rem',
                  textAlign: 'center',
                  background: '#f8fafc',
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
                    <Upload size={32} color="var(--accent-primary)" />
                    <span style={{ fontSize: '0.95rem', fontWeight: 600, color: '#0f172a' }}>
                      {selectedFile ? selectedFile.name : 'Select PDF, TXT, or DOCX File'}
                    </span>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      Automated chunking & Qdrant vector embedding will launch on upload
                    </span>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                  <div>
                    <label style={{ fontSize: '0.82rem', fontWeight: 700 }}>Workspace</label>
                    <select className="input-field" value={metadata.workspace} onChange={(e) => setMetadata({...metadata, workspace: e.target.value})} style={{ width: '100%', padding: '0.6rem', fontSize: '0.85rem' }}>
                      <option value="Labour Law">Labour Law</option>
                      <option value="Corporate Law">Corporate Law</option>
                      <option value="Criminal Law">Criminal Law</option>
                    </select>
                  </div>
 
 
                </div>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={uploading || !selectedFile}
                  style={{ width: '100%', padding: '0.85rem' }}
                >
                  {uploading ? 'Processing File & Generating Embeddings...' : 'Ingest Document into RAG'}
                </button>
              </form>
            </div>

            {/* Document Directory Table with DELETE Action */}
            <div className="glass-card" style={{ padding: '1.8rem', display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Database size={18} color="var(--accent-primary)" /> Ingested Legal Documents ({filteredDocuments.length})
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
                    <tr style={{ borderBottom: '1px solid #e2e8f0', textAlign: 'left', color: 'var(--text-muted)' }}>
                      <th style={{ padding: '0.75rem 0.5rem', fontWeight: 700 }}>Filename</th>
                      <th style={{ padding: '0.75rem 0.5rem', fontWeight: 700 }}>Status</th>
                      <th style={{ padding: '0.75rem 0.5rem', fontWeight: 700, textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredDocuments.length > 0 ? (
                      filteredDocuments.map(doc => (
                        <tr key={doc.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={{ padding: '0.85rem 0.5rem', fontWeight: 600, color: '#0f172a' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              <FileText size={15} color="var(--accent-primary)" />
                              <span style={{ maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.filename}</span>
                            </div>
                          </td>
                          <td style={{ padding: '0.85rem 0.5rem' }}>
                            <span className={`badge ${doc.status === 'completed' ? 'badge-success' : doc.status === 'failed' ? 'badge-danger' : 'badge-gold'}`}>
                              {doc.status || 'indexed'}
                            </span>
                          </td>
                          <td style={{ padding: '0.85rem 0.5rem', textAlign: 'right' }}>
                            <button
                              onClick={() => handleDeleteDocument(doc.id, doc.filename)}
                              disabled={deletingId === doc.id}
                              className="btn btn-danger btn-sm"
                              title="Delete Document & Purge Vectors"
                            >
                              <Trash2 size={13} />
                              <span>{deletingId === doc.id ? 'Deleting...' : 'Delete'}</span>
                            </button>
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
          </div>
        )}

        {/* TAB 3: USER MANAGEMENT */}
        {activeTab === 'users' && (
          <div className="glass-card animate-fade-in" style={{ padding: '1.8rem', display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Users size={18} color="var(--accent-primary)" /> Registered System User Directory
              </h2>
            </div>

            <div style={{ position: 'relative', maxWidth: '400px' }}>
              <input
                className="input-field"
                type="text"
                placeholder="Search user name or email..."
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
                style={{ width: '100%', paddingLeft: '2.4rem', fontSize: '0.88rem' }}
              />
              <Search size={16} color="var(--text-subtle)" style={{ position: 'absolute', left: '0.9rem', top: '50%', transform: 'translateY(-50%)' }} />
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #e2e8f0', textAlign: 'left', color: 'var(--text-muted)' }}>
                    <th style={{ padding: '0.75rem 0.5rem', fontWeight: 700 }}>Full Name</th>
                    <th style={{ padding: '0.75rem 0.5rem', fontWeight: 700 }}>Email Address</th>
                    <th style={{ padding: '0.75rem 0.5rem', fontWeight: 700 }}>System Role</th>
                    <th style={{ padding: '0.75rem 0.5rem', fontWeight: 700, textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.length > 0 ? (
                    filteredUsers.map(u => (
                      <tr key={u.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '0.85rem 0.5rem', fontWeight: 700, color: '#0f172a' }}>{u.full_name || 'User'}</td>
                        <td style={{ padding: '0.85rem 0.5rem', color: 'var(--text-muted)' }}>{u.email}</td>
                        <td style={{ padding: '0.85rem 0.5rem' }}>
                          <span className={`badge ${u.role === 'admin' ? 'badge-gold' : 'badge-blue'}`}>
                            {u.role}
                          </span>
                        </td>
                        <td style={{ padding: '0.85rem 0.5rem', textAlign: 'right' }}>
                          {profile?.id !== u.id && (
                            <button
                              onClick={() => handleDeleteUser(u.id, u.email)}
                              className="btn btn-danger btn-sm"
                              title="Delete User Account"
                            >
                              <Trash2 size={13} />
                              <span>Delete</span>
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-subtle)' }}>
                        No matching users found in directory.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 4: SYSTEM HEALTH */}
        {activeTab === 'health' && (
          <div className="glass-card animate-fade-in" style={{ padding: '1.8rem', display: 'flex', flexDirection: 'column', gap: '1.4rem' }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Server size={18} color="var(--accent-primary)" /> System Infrastructure & Health Status
            </h2>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.2rem' }}>
              <div style={{ padding: '1.2rem', background: '#f8fafc', borderRadius: 'var(--radius-md)', border: '1px solid #e2e8f0' }}>
                <h4 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '0.4rem' }}>FastAPI Backend Server</h4>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.8rem' }}>Running on port 8000 (Uvicorn ASGI)</p>
                <span className="badge badge-success">Status: Healthy</span>
              </div>

              <div style={{ padding: '1.2rem', background: '#f8fafc', borderRadius: 'var(--radius-md)', border: '1px solid #e2e8f0' }}>
                <h4 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '0.4rem' }}>Qdrant Vector Database</h4>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.8rem' }}>Collection: legal_documents (Port 6333)</p>
                <span className="badge badge-success">Status: Connected</span>
              </div>

              <div style={{ padding: '1.2rem', background: '#f8fafc', borderRadius: 'var(--radius-md)', border: '1px solid #e2e8f0' }}>
                <h4 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '0.4rem' }}>PostgreSQL Database</h4>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.8rem' }}>Database: legal_rag_db (Port 5432)</p>
                <span className="badge badge-success">Status: Active</span>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
