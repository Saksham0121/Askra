import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, RefreshCw, BookOpen, Cpu, Zap } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import api from '../api/client';

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const PIPELINE_LAYERS = [
  { id: 'L0', label: 'L0 · Safety Guardrail' },
  { id: 'L1', label: 'L1 · Intent Classifier' },
  { id: 'L2', label: 'L2 · Decision Router' },
  { id: 'L3', label: 'L3 · Tool Execution' },
  { id: 'L4', label: 'L4 · NLI Validation' },
  { id: 'L5', label: 'L5 · Reflection Loop' },
  { id: 'L6', label: 'L6 · Response Assembly' },
];

const STATUS_TO_LAYER = {
  'Checking safety': 'L0', 'safety': 'L0',
  'Refining': 'L1', 'query': 'L1',
  'Deciding': 'L2', 'answer': 'L2',
  'Scanning': 'L3', 'Ranking': 'L3', 'Reading': 'L3', 'Drafting': 'L3', 'Writing': 'L3',
  'Evaluating': 'L4', 'quality': 'L4',
  'Refin': 'L5', 'scored': 'L5',
  'result': 'L6',
};

function guessLayer(msg) {
  for (const [key, layer] of Object.entries(STATUS_TO_LAYER)) {
    if (msg.includes(key)) return layer;
  }
  return null;
}

export default function ChatWindow() {
  const { accessToken } = useAuthStore();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [activeLayer, setActiveLayer] = useState(null);
  const [doneLayerIds, setDoneLayerIds] = useState([]);
  const [directRag, setDirectRag] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);
  const esRef = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const autoResize = () => {
    const ta = textareaRef.current;
    if (ta) { ta.style.height = 'auto'; ta.style.height = ta.scrollHeight + 'px'; }
  };

  const sendMessage = useCallback(async () => {
    const query = input.trim();
    if (!query || isStreaming) return;

    setInput('');
    setIsStreaming(true);
    setStatusMsg('');
    setActiveLayer('L0');
    setDoneLayerIds([]);

    const userMsg = { role: 'user', content: query, id: Date.now() };
    const assistantMsg = { role: 'assistant', content: '', id: Date.now() + 1, streaming: true, sources: [], confidence_score: null, answer_source: '', iterations: 1, latency_ms: 0 };
    setMessages(prev => [...prev, userMsg, assistantMsg]);

    const params = new URLSearchParams({ query, direct_rag: directRag });
    if (sessionId) params.append('session_id', sessionId);

    const es = new EventSource(`${BASE}/api/chat/stream?${params}&_token=${accessToken}`);
    esRef.current = es;

    // Since EventSource doesn't support custom headers, we pass the token as query param.
    // Backend needs to support this — fallback: use fetch with SSE manually
    es.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);
        if (event.type === 'status') {
          setStatusMsg(event.message);
          const layer = guessLayer(event.message);
          if (layer) {
            setActiveLayer(layer);
            const idx = PIPELINE_LAYERS.findIndex(l => l.id === layer);
            setDoneLayerIds(PIPELINE_LAYERS.slice(0, idx).map(l => l.id));
          }
        } else if (event.type === 'chunk') {
          setMessages(prev => prev.map(m =>
            m.id === assistantMsg.id ? { ...m, content: m.content + event.content } : m
          ));
        } else if (event.type === 'clear_chunks') {
          setMessages(prev => prev.map(m =>
            m.id === assistantMsg.id ? { ...m, content: '' } : m
          ));
        } else if (event.type === 'result') {
          if (event.session_id) setSessionId(event.session_id);
          setDoneLayerIds(PIPELINE_LAYERS.map(l => l.id));
          setActiveLayer(null);
          setMessages(prev => prev.map(m =>
            m.id === assistantMsg.id ? {
              ...m,
              content: event.answer || m.content,
              streaming: false,
              sources: event.sources || [],
              confidence_score: event.confidence_score,
              answer_source: event.answer_source,
              confidence_badge: event.confidence_badge,
              answer_source_label: event.answer_source_label,
              iterations: event.iterations,
              latency_ms: event.latency_ms,
              validation_reasoning: event.validation_reasoning,
            } : m
          ));
          setIsStreaming(false);
          setStatusMsg('');
          es.close();
        } else if (event.type === 'error') {
          setMessages(prev => prev.map(m =>
            m.id === assistantMsg.id ? { ...m, content: `⚠️ ${event.message}`, streaming: false } : m
          ));
          setIsStreaming(false);
          es.close();
        }
      } catch {}
    };

    es.onerror = () => {
      setIsStreaming(false);
      es.close();
    };
  }, [input, isStreaming, directRag, sessionId, accessToken]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  return (
    <div className="chat-layout">
      {/* Pipeline Trace Sidebar */}
      <div className="chat-sidebar">
        <div style={{ padding: '16px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>
            Pipeline Trace
          </div>
        </div>
        <div style={{ padding: '16px', flex: 1 }}>
          <div className="pipeline-layers">
            {PIPELINE_LAYERS.map(layer => {
              const isDone = doneLayerIds.includes(layer.id);
              const isActive = activeLayer === layer.id;
              return (
                <div key={layer.id}
                  className={`layer-item ${isActive ? 'active' : ''} ${isDone ? 'done' : 'pending'}`}
                >
                  <div className={`layer-dot ${isActive ? 'active' : isDone ? 'done' : 'pending'}`} />
                  <span>{layer.label}</span>
                </div>
              );
            })}
          </div>

          {statusMsg && (
            <div className="status-pill" style={{ marginTop: 16, width: '100%', justifyContent: 'flex-start' }}>
              <RefreshCw size={12} style={{ animation: 'spin 1s linear infinite' }} />
              {statusMsg}
            </div>
          )}
        </div>

        <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border)' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 13, color: 'var(--text-secondary)' }}>
            <input type="checkbox" checked={directRag} onChange={e => setDirectRag(e.target.checked)} />
            Direct RAG mode
          </label>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="chat-main">
        <div className="messages-container">
          {messages.length === 0 && (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, color: 'var(--text-muted)', padding: '60px 20px' }}>
              <Zap size={48} style={{ color: 'var(--accent-teal)', opacity: 0.5 }} />
              <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-secondary)' }}>Ask anything</div>
              <div style={{ fontSize: 14, textAlign: 'center', maxWidth: 380 }}>
                Ask questions about your uploaded documents, write code, or just chat. The 7-layer pipeline handles the rest.
              </div>
            </div>
          )}

          {messages.map(msg => (
            <div key={msg.id} className="message-group">
              <div className={`message-bubble ${msg.role} ${msg.streaming ? 'streaming' : ''}`}>
                {msg.role === 'user' ? (
                  msg.content
                ) : (
                  <div className="markdown">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content || (msg.streaming ? '▋' : '')}</ReactMarkdown>
                  </div>
                )}
              </div>

              {/* Message metadata */}
              {msg.role === 'assistant' && !msg.streaming && msg.confidence_score !== null && (
                <div className="message-meta">
                  <span>{msg.confidence_badge}</span>
                  <span>·</span>
                  <span>{msg.answer_source_label}</span>
                  <span>·</span>
                  <span>{msg.latency_ms}ms</span>
                  {msg.iterations > 1 && <><span>·</span><span>🔄 {msg.iterations} iterations</span></>}
                </div>
              )}

              {/* Citations */}
              {msg.role === 'assistant' && msg.sources?.length > 0 && (
                <div className="citations">
                  <BookOpen size={12} style={{ color: 'var(--accent-teal)', marginTop: 2 }} />
                  {msg.sources.map((s, i) => (
                    <span key={i} className="citation-chip">📄 {s}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input Area */}
        <div className="chat-input-area">
          <div className="chat-input-wrapper">
            <textarea
              ref={textareaRef}
              className="chat-textarea"
              placeholder="Ask a question about your documents, write code, or just chat..."
              value={input}
              onChange={e => { setInput(e.target.value); autoResize(); }}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={isStreaming}
            />
            <button className="send-btn" onClick={sendMessage} disabled={!input.trim() || isStreaming}>
              <Send size={16} color="#fff" />
            </button>
          </div>
          <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-muted)', textAlign: 'center' }}>
            Press Enter to send · Shift+Enter for new line · 7-layer agentic pipeline active
          </div>
        </div>
      </div>
    </div>
  );
}
