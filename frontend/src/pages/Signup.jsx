import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Scale, Lock, Mail, User, AlertCircle, CheckCircle, Sparkles, ArrowRight, Shield } from 'lucide-react';

export default function Signup() {
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('associate');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSignup = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/v1/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          full_name: fullName,
          password,
          role,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Registration failed. Try again.');
      }

      setSuccess(true);
      setTimeout(() => {
        navigate('/login');
      }, 1800);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

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
      <div style={{
        width: '100%',
        maxWidth: '1020px',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
        gap: '2.5rem',
        alignItems: 'center'
      }}>
        {/* Left Side: Brand Showcase */}
        <div style={{ padding: '1rem' }}>
          <div className="badge badge-gold" style={{ marginBottom: '1.2rem' }}>
            <Sparkles size={12} /> ENTERPRISE REGISTRATION
          </div>
          <h1 style={{
            fontSize: '2.4rem',
            lineHeight: 1.2,
            fontWeight: 800,
            marginBottom: '1rem',
            color: '#0f172a'
          }}>
            Join the Premier <span className="text-gold-gradient">AI Legal Platform</span>
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '1rem', marginBottom: '2rem', lineHeight: 1.6 }}>
            Equip your legal practice with automated case law indexing, multi-document semantic search, and real-time citation analysis.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
              <div style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                background: 'rgba(217, 119, 6, 0.1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--accent-gold)'
              }}>
                <Shield size={20} />
              </div>
              <div>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#0f172a' }}>Custom Firm Workspace Isolation</h4>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Vector stores segregated per workspace and user role</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Auth White Card */}
        <div className="glass-card animate-fade-in" style={{ padding: '2.5rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <h2 style={{ fontSize: '1.6rem', fontWeight: 800, marginBottom: '0.4rem', color: '#0f172a' }}>Create Account</h2>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)' }}>Get instant access to AI statutory analysis</p>
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

          {success && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              background: 'rgba(22, 163, 74, 0.08)',
              border: '1px solid rgba(22, 163, 74, 0.25)',
              padding: '0.8rem 1rem',
              borderRadius: 'var(--radius-md)',
              color: 'var(--accent-success)',
              fontSize: '0.85rem',
              marginBottom: '1.5rem'
            }}>
              <CheckCircle size={18} style={{ flexShrink: 0 }} />
              <span>Account created! Redirecting to sign in...</span>
            </div>
          )}

          <form onSubmit={handleSignup}>
            <div className="input-group">
              <label className="input-label" htmlFor="fullName">Full Name</label>
              <div style={{ position: 'relative' }}>
                <input
                  className="input-field"
                  type="text"
                  id="fullName"
                  placeholder="Jane Doe"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  style={{ width: '100%', paddingLeft: '2.5rem' }}
                  required
                />
                <User size={16} color="var(--text-subtle)" style={{ position: 'absolute', left: '0.9rem', top: '50%', transform: 'translateY(-50%)' }} />
              </div>
            </div>

            <div className="input-group">
              <label className="input-label" htmlFor="email">Email Address</label>
              <div style={{ position: 'relative' }}>
                <input
                  className="input-field"
                  type="email"
                  id="email"
                  placeholder="jane@lexfirm.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  style={{ width: '100%', paddingLeft: '2.5rem' }}
                  required
                />
                <Mail size={16} color="var(--text-subtle)" style={{ position: 'absolute', left: '0.9rem', top: '50%', transform: 'translateY(-50%)' }} />
              </div>
            </div>

            <div className="input-group">
              <label className="input-label" htmlFor="password">Password</label>
              <div style={{ position: 'relative' }}>
                <input
                  className="input-field"
                  type="password"
                  id="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={{ width: '100%', paddingLeft: '2.5rem' }}
                  required
                />
                <Lock size={16} color="var(--text-subtle)" style={{ position: 'absolute', left: '0.9rem', top: '50%', transform: 'translateY(-50%)' }} />
              </div>
            </div>

            <div className="input-group">
              <label className="input-label" htmlFor="role">Role / Position</label>
              <select
                className="input-field"
                id="role"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                style={{ width: '100%', cursor: 'pointer' }}
              >
                <option value="associate">Associate Lawyer</option>
                <option value="partner">Firm Partner</option>
              </select>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || success}
              style={{ width: '100%', padding: '0.85rem', marginTop: '1rem', fontSize: '0.92rem' }}
            >
              {loading ? 'Creating Account...' : (
                <>
                  <span>Create Account</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          <div style={{ marginTop: '1.8rem', textAlign: 'center', fontSize: '0.88rem', color: 'var(--text-muted)' }}>
            Already registered?{' '}
            <Link to="/login" style={{ color: 'var(--accent-primary)', fontWeight: 600, textDecoration: 'none' }}>
              Sign In Here
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
