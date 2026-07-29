import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Scale, Lock, Mail, AlertCircle, ShieldCheck, Sparkles, ArrowRight, Eye, EyeOff } from 'lucide-react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await fetch('http://localhost:8000/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Login failed. Please check your credentials.');
      }

      const data = await response.json();
      localStorage.setItem('token', data.access_token);
      window.dispatchEvent(new Event('auth-change'));
      
      if (profileRes.ok) {
        const profileData = await profileRes.json();
        if (profileData.role === 'admin') {
          navigate('/admin');
        } else {
          navigate('/chat');
        }
      } else {
        navigate('/chat');
      }
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
      minHeight: 'calc(100vh - 65px)'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '1050px',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))',
        gap: '2rem',
        alignItems: 'center'
      }}>
        {/* Left Side: Brand Feature Showcase */}
        <div style={{ padding: '1rem' }}>
          <div className="badge badge-gold" style={{ marginBottom: '1.2rem' }}>
            <Sparkles size={12} /> ENTERPRISE LEGAL INTELLIGENCE
          </div>
          <h1 style={{
            fontSize: '2.5rem',
            lineHeight: 1.15,
            fontWeight: 800,
            marginBottom: '1rem'
          }}>
            Accelerate Legal Research with <span className="text-gold-gradient">AI Precision</span>
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '1.05rem', marginBottom: '2rem', lineHeight: 1.6 }}>
            Access instant statutory analysis, case precedent retrieval, and automated document synthesis powered by state-of-the-art vector embedding technology.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: 'rgba(226, 184, 87, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--accent-gold)'
              }}>
                <ShieldCheck size={18} />
              </div>
              <div>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600 }}>SOC2 Type II & End-to-End Encryption</h4>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-subtle)' }}>Your client files remain strict private workspace property</p>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: 'rgba(56, 189, 248, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--accent-blue)'
              }}>
                <Scale size={18} />
              </div>
              <div>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600 }}>Zero-Hallucination Citation Verification</h4>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-subtle)' }}>Every answer links directly to verified source document chunks</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Auth Glass Card */}
        <div className="glass-card animate-fade-in" style={{ padding: '2.5rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <h2 style={{ fontSize: '1.6rem', fontWeight: 700, marginBottom: '0.4rem' }}>Welcome Back</h2>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Sign in to access your firm's AI legal workspace</p>
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

          <form onSubmit={handleLogin}>
            <div className="input-group">
              <label className="input-label" htmlFor="email">Email Address</label>
              <div style={{ position: 'relative' }}>
                <input
                  className="input-field"
                  type="email"
                  id="email"
                  placeholder="associate@lexfirm.com"
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
                  type={showPassword ? "text" : "password"}
                  id="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={{ width: '100%', paddingLeft: '2.5rem', paddingRight: '2.5rem' }}
                  required
                />
                <Lock size={16} color="var(--text-subtle)" style={{ position: 'absolute', left: '0.9rem', top: '50%', transform: 'translateY(-50%)' }} />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{ position: 'absolute', right: '0.8rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--text-subtle)', cursor: 'pointer' }}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-gold"
              disabled={loading}
              style={{ width: '100%', padding: '0.85rem', marginTop: '1rem', fontSize: '0.95rem' }}
            >
              {loading ? 'Authenticating...' : (
                <>
                  <span>Sign In to Workspace</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          <div style={{ marginTop: '1.8rem', textAlign: 'center', fontSize: '0.88rem', color: 'var(--text-muted)' }}>
            Don't have an account?{' '}
            <Link to="/signup" style={{ color: 'var(--accent-gold)', fontWeight: 600, textDecoration: 'none' }}>
              Register Firm Account
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
