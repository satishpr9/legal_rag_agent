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
      background: 'rgba(6, 9, 18, 0.85)',
      backdropFilter: 'blur(16px)',
      WebkitBackdropFilter: 'blur(16px)',
      borderBottom: '1px solid rgba(226, 184, 87, 0.12)',
      padding: '0.75rem 1.5rem'
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
            background: 'linear-gradient(135deg, #e2b857 0%, #b8860b 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 15px rgba(226, 184, 87, 0.3)'
          }}>
            <Scale size={22} color="#060912" strokeWidth={2.5} />
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
              <span className="text-gold-gradient">LegalAI</span>
              <span style={{ color: 'var(--text-main)' }}>Pro</span>
              <Sparkles size={14} color="#e2b857" style={{ opacity: 0.8 }} />
            </div>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-subtle)', letterSpacing: '0.08em', textTransform: 'uppercase', display: 'block', marginTop: '-3px' }}>
              Intelligence Engine
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
                  className={`btn ${isActive('/chat') || isActive('/') ? 'btn-gold' : 'btn-ghost'}`}
                  style={{ fontSize: '0.85rem', padding: '0.5rem 1rem' }}
                >
                  <MessageSquare size={16} />
                  <span>AI Workspace</span>
                </Link>
              )}

              {user?.role === 'admin' && (
                <Link
                  to="/admin"
                  className={`btn ${isActive('/admin') ? 'btn-gold' : 'btn-ghost'}`}
                  style={{ fontSize: '0.85rem', padding: '0.5rem 1rem' }}
                >
                  <ShieldCheck size={16} />
                  <span>Admin Console</span>
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
                background: 'rgba(20, 29, 51, 0.6)',
                border: '1px solid var(--glass-border-subtle)',
                padding: '0.35rem 0.85rem',
                borderRadius: '9999px'
              }}>
                <div style={{
                  width: '26px',
                  height: '26px',
                  borderRadius: '50%',
                  background: 'rgba(226, 184, 87, 0.2)',
                  border: '1px solid var(--accent-gold)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  color: 'var(--accent-gold)'
                }}>
                  {user?.full_name ? user.full_name.charAt(0).toUpperCase() : <User size={14} />}
                </div>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)' }}>
                  {user?.full_name || user?.email || 'User'}
                </span>
                {user?.role === 'admin' && (
                  <span className="badge badge-gold" style={{ fontSize: '0.65rem', padding: '0.1rem 0.4rem' }}>
                    ADMIN
                  </span>
                )}
              </div>

              <button
                onClick={handleLogout}
                className="btn btn-ghost"
                title="Sign Out"
                style={{ padding: '0.5rem', borderRadius: '50%' }}
              >
                <LogOut size={18} color="var(--accent-danger)" />
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <Link to="/login" className="btn btn-ghost" style={{ fontSize: '0.85rem' }}>
                Sign In
              </Link>
              <Link to="/signup" className="btn btn-gold" style={{ fontSize: '0.85rem' }}>
                Get Started
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
