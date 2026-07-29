import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Scale, MessageSquare, ShieldCheck, LogOut, User, Sparkles } from 'lucide-react';

export default function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const [user, setUser] = useState(null);

  const token = localStorage.getItem('token');

  const fetchUserProfile = () => {
    const currentToken = localStorage.getItem('token');
    if (!currentToken) {
      setUser(null);
      return;
    }

    fetch('http://localhost:8000/api/v1/auth/me', {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    })
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data) setUser(data);
        else setUser(null);
      })
      .catch(() => setUser(null));
  };

  useEffect(() => {
    fetchUserProfile();

    const handleAuthChange = () => fetchUserProfile();
    window.addEventListener('auth-change', handleAuthChange);
    window.addEventListener('storage', handleAuthChange);

    return () => {
      window.removeEventListener('auth-change', handleAuthChange);
      window.removeEventListener('storage', handleAuthChange);
    };
  }, [location.pathname]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    setUser(null);
    window.dispatchEvent(new Event('auth-change'));
    navigate('/login');
  };

  const isActive = (path) => location.pathname === path;

  return (
    <header style={{
      position: 'sticky',
      top: 0,
      zIndex: 100,
      background: '#ffffff',
      borderBottom: '1px solid #e2e8f0',
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.04)',
      padding: '0.75rem 1.8rem'
    }}>
      <div style={{
        maxWidth: '1400px',
        margin: '0 auto',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        {/* Brand Logo */}
        <Link to="/" style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          textDecoration: 'none'
        }}>
          <div style={{
            width: '38px',
            height: '38px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 2px 8px rgba(37, 99, 235, 0.25)'
          }}>
            <Scale size={22} color="#ffffff" strokeWidth={2.2} />
          </div>
          <div>
            <div style={{
              fontSize: '1.2rem',
              fontWeight: 800,
              fontFamily: 'var(--font-heading)',
              letterSpacing: '-0.02em',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem'
            }}>
              <span style={{ color: '#0f172a' }}>LegalAI</span>
              <span style={{ color: 'var(--accent-primary)' }}>Pro</span>
              <Sparkles size={14} color="#d97706" />
            </div>
            <span style={{ fontSize: '0.65rem', color: '#64748b', letterSpacing: '0.08em', textTransform: 'uppercase', display: 'block', marginTop: '-3px' }}>
              Intelligence Platform
            </span>
          </div>
        </Link>

        {/* Navigation Links */}
        <nav style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          {token && (
            <>
              {user?.role !== 'admin' && (
                <Link
                  to="/chat"
                  className={`btn ${isActive('/chat') || isActive('/') ? 'btn-primary' : 'btn-ghost'}`}
                  style={{ fontSize: '0.85rem', padding: '0.5rem 1rem' }}
                >
                  <MessageSquare size={16} />
                  <span>AI Workspace</span>
                </Link>
              )}

              {user?.role === 'admin' && (
                <Link
                  to="/admin"
                  className={`btn ${isActive('/admin') ? 'btn-primary' : 'btn-ghost'}`}
                  style={{ fontSize: '0.85rem', padding: '0.5rem 1rem' }}
                >
                  <ShieldCheck size={16} />
                  <span>Admin Panel & Dashboard</span>
                </Link>
              )}
            </>
          )}
        </nav>

        {/* User Profile / Auth Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {token ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.6rem',
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                padding: '0.35rem 0.85rem',
                borderRadius: '9999px'
              }}>
                <div style={{
                  width: '26px',
                  height: '26px',
                  borderRadius: '50%',
                  background: 'rgba(37, 99, 235, 0.1)',
                  border: '1px solid var(--accent-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  color: 'var(--accent-primary)'
                }}>
                  {user?.full_name ? user.full_name.charAt(0).toUpperCase() : <User size={14} />}
                </div>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#0f172a' }}>
                  {user?.full_name || user?.email || 'User'}
                </span>
                {user?.role === 'admin' ? (
                  <span className="badge badge-gold" style={{ fontSize: '0.65rem', padding: '0.1rem 0.4rem' }}>
                    ADMIN
                  </span>
                ) : (
                  <span className="badge badge-blue" style={{ fontSize: '0.65rem', padding: '0.1rem 0.4rem' }}>
                    {user?.role || 'USER'}
                  </span>
                )}
              </div>

              <button
                onClick={handleLogout}
                className="btn btn-ghost"
                title="Sign Out"
                style={{ padding: '0.5rem', borderRadius: '50%' }}
              >
                <LogOut size={17} color="var(--accent-danger)" />
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <Link to="/login" className="btn btn-ghost" style={{ fontSize: '0.85rem' }}>
                Sign In
              </Link>
              <Link to="/signup" className="btn btn-primary" style={{ fontSize: '0.85rem' }}>
                Get Started
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
