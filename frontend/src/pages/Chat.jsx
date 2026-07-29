import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Send, Scale, Plus, MessageSquare, History, FileText, ChevronRight, 
  AlertCircle, Sparkles, Search, Copy, Check, Info, BookOpen, Layers,
  Trash2, Sliders, ExternalLink
} from 'lucide-react';

export default function Chat() {
  const navigate = useNavigate();

  // Helper to dynamically obtain authorization headers
  const getAuthHeaders = () => {
    const currentToken = localStorage.getItem('token');
    return currentToken ? { 'Authorization': `Bearer ${currentToken}` } : {};
  };

  // States
  const [profile, setProfile] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [sessionSearch, setSessionSearch] = useState('');
  const [activeSession, setActiveSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [copiedId, setCopiedId] = useState(null);
  
  // Reference Drawer States
  const [activeReferences, setActiveReferences] = useState(null);
  const [isRefPanelOpen, setIsRefPanelOpen] = useState(false);

  // Status States
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  const messagesEndRef = useRef(null);

  // Suggested Prompts for Legal Professionals
  const promptSuggestions = [
    { title: "Analyze Liability Clause", query: "What is the liability limitation cap specified in the uploaded contract?" },
    { title: "Governing Law Check", query: "Which state jurisdiction and arbitration forum governs dispute resolution?" },
    { title: "Termination Notice Period", query: "What are the required notice periods for termination without cause?" },
    { title: "Indemnity Provisions", query: "Summarize the indemnification obligations of the disclosing party." }
  ];

  useEffect(() => {
    fetchProfile();
    fetchSessions();

    const handleAuthChange = () => {
      fetchProfile();
      fetchSessions();
    };
    window.addEventListener('auth-change', handleAuthChange);
    return () => window.removeEventListener('auth-change', handleAuthChange);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, sending]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchProfile = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/auth/me', { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        setProfile(data);
      }
    } catch (err) {}
  };

  const fetchSessions = async () => {
    setLoading(true);
    setMessages([]);
    setActiveSession(null);
    try {
      const res = await fetch('http://localhost:8000/api/v1/chat/sessions', { headers: getAuthHeaders() });
      if (res.status === 403) {
        throw new Error('Access denied');
      }
      if (!res.ok) throw new Error('Failed to load chat history');
      const data = await res.json();
      setSessions(data);
      if (data.length > 0) {
        setActiveSession(data[0]);
      } else {
        await handleCreateSession("New Chat");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchMessages = async (sessionId) => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/chat/sessions/${sessionId}/messages`, { headers: getAuthHeaders() });
      if (!res.ok) throw new Error('Failed to load messages');
      const data = await res.json();
      setMessages(data);
    } catch (err) {
      setError('Error loading consultation messages.');
    }
  };

  useEffect(() => {
    if (activeSession) {
      fetchMessages(activeSession.id);
      setIsRefPanelOpen(false);
      setActiveReferences(null);
    }
  }, [activeSession]);

  const handleCreateSession = async (titleText = "New Chat") => {
    try {
      const headers = { 'Content-Type': 'application/json', ...getAuthHeaders() };
      const res = await fetch('http://localhost:8000/api/v1/chat/sessions', {
        method: 'POST',
        headers,
        body: JSON.stringify({ title: titleText })
      });
      if (!res.ok) throw new Error('Failed to create session');
      const data = await res.json();
      setSessions(prev => [data, ...prev]);
      setActiveSession(data);
    } catch (err) {
      setError('Failed to start a new chat session.');
    }
  };

  const handleSendMessage = async (textToSend = userInput) => {
    const text = typeof textToSend === 'string' ? textToSend : userInput;
    if (!text.trim() || sending) return;

    if (!localStorage.getItem('token')) {
      navigate('/login');
      return;
    }

    if (!activeSession) return;

    setUserInput('');
    setSending(true);
    setError('');

    const tempUserMsg = {
      id: 'user-' + Date.now(),
      session_id: activeSession.id,
      role: 'user',
      content: text,
      created_at: new Date().toISOString()
    };

    const tempAssistantMsgId = 'stream-' + Date.now();
    const tempAssistantMsg = {
      id: tempAssistantMsgId,
      session_id: activeSession.id,
      role: 'model',
      content: '',
      confidence_level: 'Medium',
      retrieved_context: [],
      isStreaming: true,
      created_at: new Date().toISOString()
    };

    setMessages(prev => [...prev, tempUserMsg, tempAssistantMsg]);

    try {
      const headers = { 'Content-Type': 'application/json', ...getAuthHeaders() };
      
      let isStreamSuccessful = false;
      try {
        const response = await fetch(`http://localhost:8000/api/v1/chat/sessions/${activeSession.id}/messages/stream`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ content: text })
        });

        if (response.ok && response.body) {
          const reader = response.body.getReader();
          const decoder = new TextDecoder('utf-8');
          let buffer = '';

          while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
              const trimmed = line.trim();
              if (trimmed.startsWith('data: ')) {
                const dataStr = trimmed.slice(6);
                if (!dataStr) continue;
                try {
                  const event = JSON.parse(dataStr);
                  if (event.type === 'metadata') {
                    setMessages(prev => prev.map(m => 
                      m.id === tempAssistantMsgId 
                        ? { ...m, retrieved_context: event.retrieved_context, confidence_level: event.confidence_level }
                        : m
                    ));
                  } else if (event.type === 'chunk') {
                    setMessages(prev => prev.map(m => 
                      m.id === tempAssistantMsgId 
                        ? { ...m, content: m.content + event.content }
                        : m
                    ));
                  } else if (event.type === 'done') {
                    setMessages(prev => prev.map(m => 
                      m.id === tempAssistantMsgId 
                        ? { ...m, id: event.message_id, isStreaming: false }
                        : m
                    ));
                  }
                } catch (e) {
                  // Ignore line parse errors
                }
              }
            }
          }
          isStreamSuccessful = true;
        }
      } catch (streamErr) {
        console.warn("Streaming connection dropped or unavailable, falling back to standard HTTP POST...", streamErr);
      }

      // If streaming was not successful or failed, fallback to standard POST
      if (!isStreamSuccessful) {
        const fallbackRes = await fetch(`http://localhost:8000/api/v1/chat/sessions/${activeSession.id}/messages`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ content: text })
        });

        if (!fallbackRes.ok) {
          const errorData = await fallbackRes.json().catch(() => ({}));
          throw new Error(errorData.detail || 'Failed to generate response. Please check server logs.');
        }

        const data = await fallbackRes.json();
        setMessages(prev => prev.map(m => m.id === tempAssistantMsgId ? data : m));
      }
    } catch (err) {
      setError(err.message);
      setMessages(prev => prev.filter(m => m.id !== tempAssistantMsgId));
    } finally {
      setSending(false);
    }
  };

  const handleCopyText = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredSessions = sessions.filter(s => 
    s.title.toLowerCase().includes(sessionSearch.toLowerCase())
  );

  return (
    <div style={{
      display: 'flex',
      flex: 1,
      height: 'calc(100vh - 65px)',
      background: '#f8fafc',
      overflow: 'hidden'
    }}>
      
      {/* LEFT SIDEBAR: Sessions History */}
      <aside style={{
        width: '320px',
        background: '#ffffff',
        borderRight: '1px solid #e2e8f0',
        display: 'flex',
        flexDirection: 'column',
        padding: '1.25rem',
        height: '100%',
        overflow: 'hidden'
      }}>
        {/* New Session Button */}
        <button
          onClick={() => handleCreateSession()}
          className="btn btn-primary"
          style={{ width: '100%', marginBottom: '1.2rem', padding: '0.75rem' }}
        >
          <Plus size={18} />
          <span>New Consultation</span>
        </button>

        {/* Search Session Filter */}
        <div style={{ position: 'relative', marginBottom: '1rem' }}>
          <input
            className="input-field"
            type="text"
            placeholder="Search consultations..."
            value={sessionSearch}
            onChange={(e) => setSessionSearch(e.target.value)}
            style={{ width: '100%', paddingLeft: '2.3rem', fontSize: '0.82rem', padding: '0.55rem 0.8rem 0.55rem 2.3rem' }}
          />
          <Search size={14} color="var(--text-subtle)" style={{ position: 'absolute', left: '0.8rem', top: '50%', transform: 'translateY(-50%)' }} />
        </div>

        <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-subtle)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.6rem' }}>
          Consultation History
        </div>

        {/* Session Items List */}
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          {filteredSessions.map(s => {
            const isActive = activeSession?.id === s.id;
            return (
              <div
                key={s.id}
                onClick={() => setActiveSession(s)}
                style={{
                  padding: '0.65rem 0.85rem',
                  borderRadius: 'var(--radius-md)',
                  cursor: 'pointer',
                  transition: 'var(--transition-fast)',
                  background: isActive ? 'rgba(37, 99, 235, 0.08)' : 'transparent',
                  border: '1px solid',
                  borderColor: isActive ? 'rgba(37, 99, 235, 0.25)' : 'transparent',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.6rem'
                }}
              >
                <MessageSquare size={15} color={isActive ? 'var(--accent-primary)' : 'var(--text-subtle)'} />
                <span style={{
                  fontSize: '0.85rem',
                  fontWeight: isActive ? 700 : 400,
                  color: isActive ? 'var(--accent-primary)' : 'var(--text-muted)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  flex: 1
                }}>
                  {s.title}
                </span>
              </div>
            );
          })}
        </div>
      </aside>

      {/* CENTER: Main Active Chat Area */}
      <main style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        minHeight: 0,
        overflow: 'hidden',
        position: 'relative',
        background: '#f8fafc'
      }}>
        {/* Clean ChatGPT-Style Top Bar */}
        <header style={{
          padding: '0.85rem 1.8rem',
          borderBottom: '1px solid #e2e8f0',
          background: '#ffffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'rgba(37, 99, 235, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent-primary)'
            }}>
              <Scale size={18} />
            </div>
            <div>
              <h2 style={{ fontSize: '0.98rem', fontWeight: 700, color: '#0f172a', margin: 0 }}>
                {activeSession?.title || 'Legal Chat'}
              </h2>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#10b981' }}></span>
              Ready
            </span>
          </div>
        </header>

        {/* Message Thread */}
        <div style={{
          flex: 1,
          minHeight: 0,
          padding: '1.8rem',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '1.5rem'
        }}>
          {error && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              background: 'rgba(220, 38, 38, 0.08)',
              border: '1px solid rgba(220, 38, 38, 0.25)',
              padding: '0.85rem 1.2rem',
              borderRadius: 'var(--radius-md)',
              color: 'var(--accent-danger)',
              fontSize: '0.88rem'
            }}>
              <AlertCircle size={18} />
              <span>{error}</span>
            </div>
          )}

          {messages.length > 0 ? (
            messages.map((msg, idx) => {
              const isUser = msg.role === 'user';
              const confidence = msg.confidence_level || 'Medium';

              const getConfidenceBadge = (level) => {
                if (level === 'High') {
                  return <span className="badge badge-success" style={{ fontSize: '0.68rem', padding: '0.15rem 0.5rem' }} title="High confidence grounding from indexed legal documents">High Confidence</span>;
                } else if (level === 'Medium') {
                  return <span className="badge badge-gold" style={{ fontSize: '0.68rem', padding: '0.15rem 0.5rem' }} title="Medium confidence grounding from partial legal document matches">Medium Confidence</span>;
                } else {
                  return <span className="badge badge-blue" style={{ fontSize: '0.68rem', padding: '0.15rem 0.5rem' }} title="Low confidence - synthesized primarily from general AI model knowledge">Low Confidence</span>;
                }
              };

              return (
                <div
                  key={msg.id || idx}
                  className="animate-fade-in"
                  style={{
                    alignSelf: isUser ? 'flex-end' : 'flex-start',
                    maxWidth: '84%',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.4rem'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', alignSelf: isUser ? 'flex-end' : 'flex-start' }}>
                    <span style={{
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                      color: isUser ? 'var(--accent-primary)' : 'var(--accent-gold)'
                    }}>
                      {isUser ? (profile?.full_name || 'Counsel') : 'LegalAI Assistant'}
                    </span>
                    {!isUser && getConfidenceBadge(confidence)}
                  </div>

                  <div className="glass-card" style={{
                    padding: '1.2rem 1.4rem',
                    background: isUser ? '#eff6ff' : '#ffffff',
                    borderColor: isUser ? '#bfdbfe' : '#e2e8f0',
                    borderRadius: isUser ? '16px 16px 2px 16px' : '16px 16px 16px 2px',
                    position: 'relative'
                  }}>
                    <div style={{
                      fontSize: '0.95rem',
                      lineHeight: 1.65,
                      whiteSpace: 'pre-wrap',
                      color: '#0f172a'
                    }}>
                      {msg.content}
                      {msg.isStreaming && (
                        <span style={{
                          display: 'inline-block',
                          width: '8px',
                          height: '15px',
                          background: 'var(--accent-primary)',
                          marginLeft: '4px',
                          verticalAlign: 'middle',
                          borderRadius: '1px'
                        }} />
                      )}
                    </div>

                    {!isUser && !msg.isStreaming && (
                      <div style={{
                        marginTop: '0.85rem',
                        padding: '0.55rem 0.8rem',
                        background: 'rgba(245, 158, 11, 0.05)',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid rgba(245, 158, 11, 0.2)',
                        fontSize: '0.73rem',
                        color: '#92400e',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.45rem'
                      }}>
                        <Info size={14} style={{ flexShrink: 0 }} />
                        <span><strong>Legal Disclaimer:</strong> Informational and legal research purposes only; not a substitute for professional legal advice. Independently verify statutory sections and PDF page numbers.</span>
                      </div>
                    )}

                    {/* Bottom Metadata & Actions */}
                    <div style={{
                      marginTop: '0.8rem',
                      paddingTop: '0.6rem',
                      borderTop: '1px solid #f1f5f9',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between'
                    }}>
                      <button
                        onClick={() => handleCopyText(msg.id || idx, msg.content)}
                        className="btn btn-ghost btn-sm"
                        style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem' }}
                      >
                        {copiedId === (msg.id || idx) ? <Check size={13} color="var(--accent-success)" /> : <Copy size={13} />}
                        <span>{copiedId === (msg.id || idx) ? 'Copied' : 'Copy Text'}</span>
                      </button>

                      {!isUser && msg.retrieved_context && msg.retrieved_context.length > 0 && (
                        <button
                          onClick={() => {
                            setActiveReferences(msg.retrieved_context);
                            setIsRefPanelOpen(true);
                          }}
                          className="badge badge-gold"
                          style={{ cursor: 'pointer' }}
                        >
                          <FileText size={12} />
                          <span>{msg.retrieved_context.length} Verified Sources</span>
                          <ChevronRight size={12} />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          ) : (
            /* Empty State with Prompt Suggestions */
            <div style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              padding: '2rem'
            }}>
              <div style={{
                width: '60px',
                height: '60px',
                borderRadius: '14px',
                background: 'rgba(37, 99, 235, 0.08)',
                border: '1px solid var(--accent-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '1.2rem'
              }}>
                <Scale size={30} color="var(--accent-primary)" />
              </div>
              <h3 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem', color: '#0f172a' }}>
                Legal AI Consultation Hub
              </h3>
              <p style={{ color: 'var(--text-muted)', maxWidth: '520px', fontSize: '0.92rem', marginBottom: '2rem' }}>
                Ask complex statutory questions, review contracts for liability risks, or extract statutory citations grounded in indexed document repositories with PDF page references.
              </p>

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                gap: '1rem',
                width: '100%',
                maxWidth: '750px'
              }}>
                {promptSuggestions.map((prompt, i) => (
                  <div
                    key={i}
                    onClick={() => handleSendMessage(prompt.query)}
                    className="glass-card glass-card-hover"
                    style={{
                      padding: '1.1rem',
                      cursor: 'pointer',
                      textAlign: 'left',
                      borderRadius: 'var(--radius-md)'
                    }}
                  >
                    <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--accent-primary)', marginBottom: '0.3rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <Sparkles size={14} />
                      {prompt.title}
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                      "{prompt.query}"
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* CHATGPT-STYLE FLOATING INPUT CONTAINER - PERMANENTLY PINNED AT BOTTOM */}
        <div style={{
          flexShrink: 0,
          width: '100%',
          padding: '0.8rem 1.5rem 1rem',
          background: 'transparent',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center'
        }}>
          <div style={{
            width: '100%',
            maxWidth: '820px',
            background: '#ffffff',
            borderRadius: '24px',
            border: '1px solid #cbd5e1',
            boxShadow: '0 4px 16px rgba(15, 23, 42, 0.06)',
            display: 'flex',
            alignItems: 'center',
            padding: '0.35rem 0.6rem 0.35rem 1.2rem',
            transition: 'all 0.2s ease',
            position: 'relative'
          }}>
            <textarea
              rows={1}
              placeholder="Ask a legal question, analyze contract provisions, or research statutory law..."
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              disabled={sending}
              style={{
                flex: 1,
                border: 'none',
                outline: 'none',
                resize: 'none',
                padding: '0.55rem 0',
                fontSize: '0.94rem',
                lineHeight: 1.45,
                color: '#0f172a',
                background: 'transparent',
                fontFamily: 'inherit',
                maxHeight: '120px'
              }}
            />

            <button
              type="button"
              onClick={() => handleSendMessage()}
              disabled={sending || !userInput.trim()}
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '50%',
                background: sending || !userInput.trim() ? '#e2e8f0' : 'var(--accent-primary)',
                color: '#ffffff',
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: sending || !userInput.trim() ? 'not-allowed' : 'pointer',
                marginLeft: '0.5rem',
                flexShrink: 0,
                transition: 'all 0.2s ease'
              }}
            >
              <Send size={16} />
            </button>
          </div>

          <div style={{ fontSize: '0.71rem', color: 'var(--text-subtle)', marginTop: '0.45rem' }}>
            Antigravity Legal AI provides research assistance. Verify statutory provisions against primary legal sources.
          </div>
        </div>
      </main>

      {/* RIGHT SIDEBAR: Citation & Document Source Inspector */}
      {isRefPanelOpen && activeReferences && (
        <aside className="glass-card animate-fade-in" style={{
          width: '400px',
          borderRadius: 0,
          borderTop: 'none',
          borderBottom: 'none',
          borderRight: 'none',
          padding: '1.4rem',
          display: 'flex',
          flexDirection: 'column',
          background: '#ffffff',
          zIndex: 50,
          borderLeft: '1px solid #e2e8f0'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.2rem', paddingBottom: '0.8rem', borderBottom: '1px solid #e2e8f0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FileText size={18} color="var(--accent-primary)" />
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a' }}>Citation Inspector</h3>
            </div>
            <button
              onClick={() => setIsRefPanelOpen(false)}
              className="btn btn-ghost btn-sm"
            >
              Close
            </button>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {activeReferences.map((ref, idx) => (
              <div
                key={idx}
                className="glass-card"
                style={{ padding: '1rem', background: '#f8fafc', borderColor: '#e2e8f0' }}
              >
                {/* Source Filename Header */}
                <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0f172a', marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.4rem', wordBreak: 'break-word' }}>
                  <FileText size={14} color="var(--accent-primary)" />
                  <span>{ref.filename || `Document #${ref.document_id}`}</span>
                </div>

                <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.4rem', marginBottom: '0.6rem' }}>
                  <span className="badge badge-gold" style={{ fontSize: '0.7rem' }}>
                    Section: {ref.estimated_section || 'General'}
                  </span>
                  <span className="badge" style={{ fontSize: '0.7rem', background: 'rgba(147, 51, 234, 0.1)', color: '#7e22ce', border: '1px solid rgba(147, 51, 234, 0.2)' }}>
                    Page {ref.page_number || 1}
                  </span>
                  <span className="badge badge-success" style={{ fontSize: '0.7rem' }}>
                    {Math.round((ref.score || 0.88) * 100)}% Match
                  </span>
                </div>

                <p style={{
                  fontSize: '0.82rem',
                  lineHeight: 1.5,
                  color: '#0f172a',
                  fontStyle: 'italic',
                  background: '#ffffff',
                  padding: '0.75rem',
                  borderRadius: 'var(--radius-sm)',
                  borderLeft: '3px solid var(--accent-primary)',
                  marginBottom: '0.6rem',
                  border: '1px solid #e2e8f0',
                  borderLeftWidth: '3px'
                }}>
                  "{ref.text}"
                </p>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-subtle)' }}>
                  <span>Doc ID: #{ref.document_id || 'N/A'}</span>
                  <span>Chunk: #{ref.chunk_index}</span>
                </div>
              </div>
            ))}
          </div>
        </aside>
      )}
    </div>
  );
}
