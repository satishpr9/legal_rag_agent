import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Database, FileText, MessageSquare, LogOut, Shield, Award, User, RefreshCw, AlertCircle, Scale, Sparkles, FolderPlus } from 'lucide-react';

export default function Dashboard() {
  const [profile, setProfile] = useState(null);
  const [workspaces, setWorkspaces] = useState([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState(null);
  const [documents, setDocuments] = useState([]);
  
  // Creation States
  const [wsName, setWsName] = useState('');
  const [wsDesc, setWsDesc] = useState('');
  const [docFilename, setDocFilename] = useState('');
  const [docFilePath, setDocFilePath] = useState('');
  
  // Feedback
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const token = localStorage.getItem('token');

  useEffect(() => {
    if (!token) {
      navigate('/login');
      return;
    }
    fetchProfile();
    fetchWorkspaces();
  }, [token]);

  useEffect(() => {
    if (selectedWorkspace) {
      fetchDocuments(selectedWorkspace.id);
    }
  }, [selectedWorkspace]);

  const fetchProfile = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to fetch profile');
      const data = await res.json();
      setProfile(data);
    } catch (err) {
      handleAuthError();
    }
  };

  const fetchWorkspaces = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/admin/workspaces', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to fetch workspaces');
      const data = await res.json();
      setWorkspaces(data);
      if (data.length > 0 && !selectedWorkspace) {
        setSelectedWorkspace(data[0]);
      }
    } catch (err) {
      setError('Error loading workspaces');
    }
  };

  const fetchDocuments = async (workspaceId) => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/admin/workspaces/${workspaceId}/documents`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to fetch documents');
      const data = await res.json();
      setDocuments(data);
    } catch (err) {
      setError('Error loading documents');
    }
  };

  const handleCreateWorkspace = async (e) => {
    e.preventDefault();
    if (!wsName) return;
    setLoading(true);
    setError('');

    try {
      const res = await fetch('http://localhost:8000/api/v1/admin/workspaces', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ name: wsName, description: wsDesc })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to create workspace');
      }

      const data = await res.json();
      setWorkspaces([data, ...workspaces]);
      setSelectedWorkspace(data);
      setWsName('');
      setWsDesc('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerIngestion = async (e) => {
    e.preventDefault();
    if (!docFilename || !docFilePath || !selectedWorkspace) return;
    setLoading(true);
    setError('');

    try {
      const res = await fetch('http://localhost:8000/api/v1/admin/documents/ingest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          filename: docFilename,
          file_path: docFilePath,
          workspace_id: selectedWorkspace.id
        })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to trigger ingestion');
      }

      await fetchDocuments(selectedWorkspace.id);
      setDocFilename('');
      setDocFilePath('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAuthError = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const isAdmin = profile?.role === 'admin';

  return (
    <div style={{
      display: 'flex',
      flex: 1,
      height: 'calc(100vh - 65px)',
      background: 'var(--bg-base)',
      overflow: 'hidden'
    }}>
      {/* Sidebar Workspace Panel */}
      <aside style={{
        width: '320px',
        background: 'rgba(12, 18, 34, 0.7)',
        borderRight: '1px solid var(--glass-border-subtle)',
        padding: '1.4rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.4rem'
      }}>
        {/* Create Workspace Form (Admin) */}
        {isAdmin && (
          <div className="glass-card" style={{ padding: '1.2rem' }}>
            <h3 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-gold)', marginBottom: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <FolderPlus size={16} /> New Workspace
            </h3>
            <form onSubmit={handleCreateWorkspace} style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              <input
                className="input-field"
                type="text"
                placeholder="Workspace Title"
                value={wsName}
                onChange={(e) => setWsName(e.target.value)}
                required
                style={{ fontSize: '0.82rem', padding: '0.55rem 0.8rem' }}
              />
              <input
                className="input-field"
                type="text"
                placeholder="Description..."
                value={wsDesc}
                onChange={(e) => setWsDesc(e.target.value)}
                style={{ fontSize: '0.82rem', padding: '0.55rem 0.8rem' }}
              />
              <button className="btn btn-gold btn-sm" type="submit" disabled={loading} style={{ marginTop: '0.2rem' }}>
                <Plus size={14} /> Create Workspace
              </button>
            </form>
          </div>
        )}

        {/* Workspaces List */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.4rem', overflowY: 'auto' }}>
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-subtle)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.4rem' }}>
            Active Workspaces
          </span>
          {workspaces.map(ws => {
            const isActive = selectedWorkspace?.id === ws.id;
            return (
              <div
                key={ws.id}
                onClick={() => setSelectedWorkspace(ws)}
                style={{
                  padding: '0.75rem 0.9rem',
                  borderRadius: 'var(--radius-md)',
                  cursor: 'pointer',
                  transition: 'var(--transition-fast)',
                  background: isActive ? 'rgba(226, 184, 87, 0.12)' : 'transparent',
                  border: '1px solid',
                  borderColor: isActive ? 'rgba(226, 184, 87, 0.3)' : 'transparent'
                }}
              >
                <p style={{ fontWeight: 600, fontSize: '0.88rem', color: isActive ? 'var(--accent-gold)' : 'var(--text-main)' }}>
                  {ws.name}
                </p>
                {ws.description && (
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-subtle)', marginTop: '0.15rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {ws.description}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </aside>

      {/* Main Workspace Workspace Content */}
      <main style={{ flex: 1, padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1.8rem', overflowY: 'auto' }}>
        {error && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.6rem',
            background: 'rgba(244, 63, 94, 0.12)',
            border: '1px solid rgba(244, 63, 94, 0.3)',
            padding: '1rem',
            borderRadius: 'var(--radius-md)',
            color: 'var(--accent-danger)'
          }}>
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        {selectedWorkspace ? (
          <>
            <div className="glass-card" style={{ padding: '1.8rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2 style={{ fontSize: '1.5rem', fontWeight: 800 }}>{selectedWorkspace.name}</h2>
                <p style={{ color: 'var(--text-muted)', marginTop: '0.2rem', fontSize: '0.9rem' }}>
                  {selectedWorkspace.description || 'Enterprise Workspace Repository'}
                </p>
              </div>
              <button
                className="btn btn-gold"
                onClick={() => navigate('/chat')}
              >
                <MessageSquare size={16} /> Launch AI Consultation
              </button>
            </div>

            {/* Ingestion Panel */}
            {isAdmin && (
              <div className="glass-card" style={{ padding: '1.5rem' }}>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-gold)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Database size={16} /> Backend Document Ingestion Trigger
                </h3>
                <form onSubmit={handleTriggerIngestion} style={{ display: 'grid', gridTemplateColumns: '1fr 2fr auto', gap: '1rem', alignItems: 'center' }}>
                  <input
                    className="input-field"
                    type="text"
                    placeholder="Filename (e.g. nda.pdf)"
                    value={docFilename}
                    onChange={(e) => setDocFilename(e.target.value)}
                    required
                  />
                  <input
                    className="input-field"
                    type="text"
                    placeholder="Backend Path (e.g. uploads/nda.pdf)"
                    value={docFilePath}
                    onChange={(e) => setDocFilePath(e.target.value)}
                    required
                  />
                  <button className="btn btn-gold" type="submit" disabled={loading}>
                    <Database size={15} /> Ingest File
                  </button>
                </form>
              </div>
            )}

            {/* Documents List Table */}
            <div className="glass-card" style={{ padding: '1.8rem', flex: 1, display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.2rem' }}>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <FileText size={18} color="var(--accent-gold)" /> Indexed Workspace Documents ({documents.length})
                </h3>
                <button className="btn btn-ghost btn-sm" onClick={() => fetchDocuments(selectedWorkspace.id)}>
                  <RefreshCw size={13} /> Refresh
                </button>
              </div>

              {documents.length > 0 ? (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--glass-border-subtle)', textAlign: 'left', color: 'var(--text-subtle)' }}>
                        <th style={{ padding: '0.75rem 0.5rem', fontWeight: 700 }}>Filename</th>
                        <th style={{ padding: '0.75rem 0.5rem', fontWeight: 700 }}>Status</th>
                        <th style={{ padding: '0.75rem 0.5rem', fontWeight: 700, textAlign: 'right' }}>Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {documents.map(doc => (
                        <tr key={doc.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.03)' }}>
                          <td style={{ padding: '0.85rem 0.5rem', fontWeight: 600 }}>{doc.filename}</td>
                          <td style={{ padding: '0.85rem 0.5rem' }}>
                            <span className={`badge ${doc.status === 'completed' ? 'badge-success' : 'badge-gold'}`}>
                              {doc.status || 'indexed'}
                            </span>
                          </td>
                          <td style={{ padding: '0.85rem 0.5rem', textAlign: 'right', color: 'var(--text-subtle)' }}>
                            {new Date(doc.created_at).toLocaleDateString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem', color: 'var(--text-subtle)' }}>
                  <Database size={40} style={{ marginBottom: '0.8rem' }} />
                  <p>No documents found in this workspace repository.</p>
                </div>
              )}
            </div>
          </>
        ) : (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-subtle)' }}>
            <Scale size={48} style={{ marginBottom: '1rem' }} />
            <h3>Select a Workspace</h3>
          </div>
        )}
      </main>
    </div>
  );
}
