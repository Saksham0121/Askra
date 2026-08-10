import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Send, RefreshCw, BookOpen, ChevronDown, Plus, Mic, MicOff,
  Sparkles, Layers, FileText, Code, BarChart2, CheckCircle2,
  ArrowUp, ShieldAlert, Cpu, Menu
} from 'lucide-react';
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

const PROMPT_SUGGESTIONS = [
  {
    icon: FileText,
    title: 'Summarize Policy Documents',
    desc: 'Extract key clauses and contract details from uploaded files',
    prompt: 'Can you summarize the key points and policy details from the uploaded documents?'
  },
  {
    icon: Sparkles,
    title: 'Force RAG Search',
    desc: 'Perform direct vector retrieval with exact citations',
    prompt: 'Search the document store for exact facts and provide source citations.',
    mode: 'rag'
  },
  {
    icon: Code,
    title: 'Explain Code & Logic',
    desc: 'Analyze Python algorithms, SQL queries, or system specs',
    prompt: 'Explain the architecture and execution logic of this project in detail.'
  },
  {
    icon: BarChart2,
    title: 'Extract Metrics & Insights',
    desc: 'Find numbers, dates, and compliance milestones',
    prompt: 'Extract key metrics, financial figures, and important milestones.'
  }
];

export default function ChatWindow({ activeSessionId, toggleMobileSidebar }) {
  const { accessToken } = useAuthStore();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [activeLayer, setActiveLayer] = useState(null);
  const [doneLayerIds, setDoneLayerIds] = useState([]);
  
  // Mode State: 'auto' | 'rag'
  const [mode, setMode] = useState('auto'); // Default: Auto Router
  const [showModeMenu, setShowModeMenu] = useState(false);
  const [showTraceDrawer, setShowTraceDrawer] = useState(false);
  const [isListening, setIsListening] = useState(false);
  
  const [sessionId, setSessionId] = useState(activeSessionId || null);
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);
  const esRef = useRef(null);

  useEffect(() => {
    // When session changes: load history or clear for new chat
    if (activeSessionId === sessionId) return;
    setSessionId(activeSessionId);
    setMessages([]);
    setIsStreaming(false);
    setStatusMsg('');
    setActiveLayer(null);
    setDoneLayerIds([]);

    if (!activeSessionId) return; // New Chat — just clear

    // Load history for the selected session
    let cancelled = false;
    api.get(`/api/chat/sessions/${activeSessionId}/messages`)
      .then(({ data }) => {
        if (cancelled) return;
        const loaded = [];
        (data.messages || []).forEach((msg, i) => {
          loaded.push({
            role: 'user',
            content: msg.query,
            id: `hist-u-${i}`,
          });
          loaded.push({
            role: 'assistant',
            content: msg.answer,
            id: `hist-a-${i}`,
            streaming: false,
            sources: msg.sources || [],
            confidence_score: msg.confidence_score ?? null,
            answer_source: msg.answer_source || '',
            confidence_badge: null,
            answer_source_label: msg.answer_source || '',
            iterations: msg.iterations || 1,
            latency_ms: msg.latency_ms || 0,
          });
        });
        setMessages(loaded);
      })
      .catch(() => {}); // Silent on error
    return () => { cancelled = true; };
  }, [activeSessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const autoResize = () => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = 'auto';
      ta.style.height = Math.min(ta.scrollHeight, 160) + 'px';
    }
  };

  const toggleVoiceInput = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Voice dictation is not supported in your browser.');
      return;
    }

    if (isListening) {
      setIsListening(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onstart = () => setIsListening(true);
      recognition.onend = () => setIsListening(false);
      recognition.onerror = () => setIsListening(false);

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInput(prev => (prev ? prev + ' ' + transcript : transcript));
        autoResize();
      };

      recognition.start();
    } catch {
      setIsListening(false);
    }
  };

  const sendMessage = useCallback(async (customQuery = null, customMode = null) => {
    const query = (customQuery || input).trim();
    if (!query || isStreaming) return;

    const currentDirectRag = (customMode || mode) === 'rag';

    setInput('');
    setIsStreaming(true);
    setStatusMsg('');
    setActiveLayer('L0');
    setDoneLayerIds([]);

    const userMsg = { role: 'user', content: query, id: Date.now() };
    const assistantMsg = {
      role: 'assistant',
      content: '',
      id: Date.now() + 1,
      streaming: true,
      sources: [],
      confidence_score: null,
      answer_source: '',
      iterations: 1,
      latency_ms: 0
    };
    setMessages(prev => [...prev, userMsg, assistantMsg]);

    const params = new URLSearchParams({ query, direct_rag: currentDirectRag });
    if (sessionId) params.append('session_id', sessionId);

    const es = new EventSource(`${BASE}/api/chat/stream?${params}&_token=${accessToken}`);
    esRef.current = es;

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
  }, [input, isStreaming, mode, sessionId, accessToken]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="gpt-chat-view">
      {/* ChatGPT Top Header Bar */}
      <header className="gpt-top-header">
        <div className="header-left">
          <button className="mobile-menu-btn" onClick={toggleMobileSidebar} title="Open Menu">
            <Menu size={20} />
          </button>

          {/* Mode Selector Dropdown */}
          <div className="mode-selector-wrapper">
            <button
              className="mode-selector-btn"
              onClick={() => setShowModeMenu(prev => !prev)}
            >
              <span className="mode-model-name">Mode</span>
              <ChevronDown size={14} className={`chevron-icon ${showModeMenu ? 'open' : ''}`} />
            </button>

            {showModeMenu && (
              <div className="mode-dropdown-menu">
                <div
                  className={`menu-item ${mode === 'auto' ? 'active' : ''}`}
                  onClick={() => { setMode('auto'); setShowModeMenu(false); }}
                >
                  <div className="item-icon"><Sparkles size={16} color="#FFAA85" /></div>
                  <div className="item-content">
                    <div className="item-title">Auto Router Mode</div>
                    <div className="item-desc">Intelligent 7-layer pipeline routing between chat, RAG, and code</div>
                  </div>
                  {mode === 'auto' && <CheckCircle2 size={16} color="#FFAA85" />}
                </div>

                <div
                  className={`menu-item ${mode === 'rag' ? 'active' : ''}`}
                  onClick={() => { setMode('rag'); setShowModeMenu(false); }}
                >
                  <div className="item-icon"><FileText size={16} color="#14b8a6" /></div>
                  <div className="item-content">
                    <div className="item-title">Force RAG Mode</div>
                    <div className="item-desc">Bypass router and force direct document vector search</div>
                  </div>
                  {mode === 'rag' && <CheckCircle2 size={16} color="#FFAA85" />}
                </div>
              </div>
            )}
          </div>

          {/* Quick Segmented Toggle Button */}
          <div className="segmented-toggle">
            <button
              className={`toggle-option ${mode === 'auto' ? 'active' : ''}`}
              onClick={() => setMode('auto')}
            >
              🤖 Auto
            </button>
            <button
              className={`toggle-option ${mode === 'rag' ? 'active' : ''}`}
              onClick={() => setMode('rag')}
            >
              ⚡ Force RAG
            </button>
          </div>
        </div>

        <div className="header-right">
          <button
            className={`trace-drawer-btn ${showTraceDrawer ? 'active' : ''}`}
            onClick={() => setShowTraceDrawer(prev => !prev)}
            title="Toggle Pipeline Trace Panel"
          >
            <Layers size={16} />
            <span>Trace Panel</span>
          </button>
        </div>
      </header>

      {/* Main Workspace Layout */}
      <div className="gpt-workspace">
        {/* Chat Stream View */}
        <main className="gpt-messages-workspace">
          <div className="messages-scroll-area">
            {messages.length === 0 ? (
              /* ChatGPT Initial Screen View */
              <div className="gpt-empty-screen">
                <div className="empty-title">Where should we begin?</div>
                <div className="empty-sub">
                  Powered by 7-Layer Agentic RAG Architecture & Groq LLM
                </div>

                <div className="prompt-grid">
                  {PROMPT_SUGGESTIONS.map((item, idx) => {
                    const IconComp = item.icon;
                    return (
                      <div
                        key={idx}
                        className="prompt-card"
                        onClick={() => sendMessage(item.prompt, item.mode)}
                      >
                        <div className="card-header">
                          <IconComp size={18} className="card-icon" />
                          <span className="card-title">{item.title}</span>
                        </div>
                        <div className="card-desc">{item.desc}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              /* Message Stream */
              messages.map(msg => (
                <div key={msg.id} className={`gpt-message-row ${msg.role}`}>
                  <div className="msg-avatar">
                    {msg.role === 'user' ? 'U' : <Sparkles size={16} color="#FFAA85" />}
                  </div>

                  <div className="msg-body">
                    <div className="msg-author">
                      {msg.role === 'user' ? 'You' : 'Askrab'}
                    </div>

                    <div className={`msg-content ${msg.streaming ? 'is-streaming' : ''}`}>
                      {msg.role === 'user' ? (
                        msg.content
                      ) : (
                        <div className="markdown-body">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.content || (msg.streaming ? '▋' : '')}
                          </ReactMarkdown>
                        </div>
                      )}
                    </div>

                    {/* Metadata & Badges */}
                    {msg.role === 'assistant' && !msg.streaming && msg.confidence_score !== null && (
                      <div className="msg-metadata-strip">
                        <span className="meta-badge confidence">{msg.confidence_badge}</span>
                        <span className="meta-dot">•</span>
                        <span className="meta-badge source">{msg.answer_source_label}</span>
                        <span className="meta-dot">•</span>
                        <span className="meta-time">{msg.latency_ms}ms</span>
                        {msg.iterations > 1 && (
                          <>
                            <span className="meta-dot">•</span>
                            <span className="meta-iterations">🔄 {msg.iterations} iterations</span>
                          </>
                        )}
                      </div>
                    )}

                    {/* Citations */}
                    {msg.role === 'assistant' && msg.sources?.length > 0 && (
                      <div className="citations-box">
                        <div className="citations-label">
                          <BookOpen size={13} color="#FFAA85" />
                          <span>Sources Referenced:</span>
                        </div>
                        <div className="citations-chips">
                          {msg.sources.map((src, i) => (
                            <span key={i} className="citation-chip">📄 {src}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            <div ref={bottomRef} />
          </div>

          {/* ChatGPT Capsule Floating Input Bar */}
          <div className="gpt-input-dock">
            <div className="capsule-input-bar">
              <button className="plus-btn" title="Attach file or context" onClick={() => alert('Quick document upload available in Library tab.')}>
                <Plus size={18} />
              </button>

              <textarea
                ref={textareaRef}
                className="capsule-textarea"
                placeholder="Ask anything..."
                value={input}
                onChange={e => { setInput(e.target.value); autoResize(); }}
                onKeyDown={handleKeyDown}
                rows={1}
                disabled={isStreaming}
              />

              <button
                className={`voice-btn ${isListening ? 'listening' : ''}`}
                onClick={toggleVoiceInput}
                title={isListening ? 'Listening...' : 'Voice Dictation'}
              >
                {isListening ? <MicOff size={18} color="#f87171" /> : <Mic size={18} />}
              </button>

              <button
                className="capsule-send-btn"
                onClick={() => sendMessage()}
                disabled={!input.trim() || isStreaming}
              >
                <ArrowUp size={18} />
              </button>
            </div>

            <div className="dock-footer-info">
              <span>Mode: <strong>{mode === 'auto' ? 'Auto Router' : 'Force RAG'}</strong></span>
              <span>•</span>
              <span>Press Enter to send · Shift+Enter for new line</span>
            </div>
          </div>
        </main>

        {/* Pipeline Trace Collapsible Right Panel */}
        {showTraceDrawer && (
          <aside className="gpt-trace-drawer">
            <div className="drawer-header">
              <div className="drawer-title">
                <Cpu size={16} color="#FFAA85" />
                <span>Pipeline Execution Trace</span>
              </div>
            </div>

            <div className="drawer-body">
              <div className="trace-layers-list">
                {PIPELINE_LAYERS.map(layer => {
                  const isDone = doneLayerIds.includes(layer.id);
                  const isActive = activeLayer === layer.id;
                  return (
                    <div
                      key={layer.id}
                      className={`trace-layer-row ${isActive ? 'active' : ''} ${isDone ? 'done' : 'pending'}`}
                    >
                      <div className={`status-dot ${isActive ? 'pulse' : isDone ? 'check' : ''}`} />
                      <span className="layer-name">{layer.label}</span>
                    </div>
                  );
                })}
              </div>

              {statusMsg && (
                <div className="trace-status-box">
                  <RefreshCw size={14} className="spin-icon" />
                  <span>{statusMsg}</span>
                </div>
              )}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
