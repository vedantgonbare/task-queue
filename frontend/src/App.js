import { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';

const API = 'http://localhost:8000';
// const ws = 'ws://localhost:8000/ws';

export default function App() {
  const [tasks, setTasks]           = useState([]);
  const [connected, setConnected]   = useState(false);
  const [filter, setFilter]         = useState('all');
  const [endpoint, setEndpoint]     = useState(API);
  const [payload, setPayload]       = useState('{"type": "email_batch", "count": 100}');
  const [payloadErr, setPayloadErr] = useState('');
  const [log, setLog]               = useState(['Waiting for events…']);
  const [time, setTime]             = useState('');
  const wsRef = useRef(null);

  // Clock
  useEffect(() => {
    const tick = () => setTime(new Date().toTimeString().slice(0, 8));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const addLog = useCallback((msg, type = '') => {
    const ts = new Date().toTimeString().slice(0, 8);
    setLog(prev => {
      const clean = prev[0] === 'Waiting for events…' ? [] : prev;
      return [`[${ts}] ${msg}`, ...clean].slice(0, 50);
    });
  }, []);

  // Load existing tasks
  const loadTasks = useCallback(async (base) => {
    try {
      const res  = await fetch(`${base}/tasks/`);
      const data = await res.json();
      setTasks(data.map(t => ({ id: t.id, payload: t.payload, status: t.status })));
      addLog(`Loaded ${data.length} existing task(s)`, 'info');
    } catch {
      addLog('Could not load tasks from GET /tasks/', '');
    }
  }, [addLog]);

  // WebSocket
  const connect = useCallback(() => {
    if (wsRef.current) wsRef.current.close();
    const wsUrl = endpoint.replace(/^http/, 'ws') + '/ws';
    addLog(`Connecting to ${wsUrl}…`, 'info');
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setConnected(true);
      addLog('WebSocket connected ✓', 'success');
      loadTasks(endpoint);
    };

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        const taskId = data.task_id || data.id;
        setTasks(prev => {
          const idx = prev.findIndex(t => t.id === taskId);
          if (idx >= 0) {
            const next = [...prev];
            next[idx] = { ...next[idx], status: data.status };
            return next;
          }
          return [{ id: taskId, payload: data.payload || '…', status: data.status || 'pending' }, ...prev];
        });
        addLog(`Task #${taskId} → ${data.status}`, data.status === 'done' ? 'success' : 'info');
      } catch {
        addLog(`WS: ${e.data}`);
      }
    };

    ws.onclose = () => { setConnected(false); addLog('WebSocket disconnected', 'error'); wsRef.current = null; };
    ws.onerror = () => addLog('WebSocket error — is the server running?', 'error');
    wsRef.current = ws;
  }, [endpoint, addLog, loadTasks]);

  // Dispatch
  const dispatch = async () => {
    setPayloadErr('');
    let obj;
    try { obj = JSON.parse(payload); } catch { setPayloadErr('Invalid JSON'); return; }
    addLog('Dispatching task…', 'info');
    try {
      const res  = await fetch(`${endpoint}/tasks/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payload: JSON.stringify(obj) }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setTasks(prev => [{ id: data.id, payload, status: data.status || 'pending' }, ...prev]);
      addLog(`Task #${data.id} dispatched ✓`, 'success');
    } catch (err) {
      setPayloadErr(`Dispatch failed — ${err.message}`);
      addLog(`Dispatch failed: ${err.message}`, 'error');
    }
  };

  const filtered = filter === 'all' ? tasks : tasks.filter(t => t.status === filter);
  const counts   = {
    total:   tasks.length,
    pending: tasks.filter(t => t.status === 'pending').length,
    running: tasks.filter(t => t.status === 'running').length,
    done:    tasks.filter(t => t.status === 'done').length,
  };

  return (
    <div className="app">

      {/* ── Header ── */}
      <header className="header">
        <div className="logo-row">
          <div className="logo-icon">⚡</div>
          <div>
            <h1>TaskQueue</h1>
            <p>Distributed Worker System</p>
          </div>
        </div>
        <div className="header-right">
          <button className={`status-badge ${connected ? 'connected' : ''}`} onClick={connect}>
            <span className={`dot ${connected ? 'connected' : ''}`} />
            {connected ? 'Connected' : 'Disconnected'}
          </button>
          <div className="clock">{time}</div>
        </div>
      </header>

      {/* ── Stat Cards ── */}
      <div className="stat-grid">
        {[
          { key: 'total',   label: 'TOTAL',   icon: '📋', color: 'purple' },
          { key: 'pending', label: 'PENDING',  icon: '⏳', color: 'amber'  },
          { key: 'running', label: 'RUNNING',  icon: '⚡', color: 'blue'   },
          { key: 'done',    label: 'DONE',     icon: '✅', color: 'green'  },
        ].map(({ key, label, icon, color }) => (
          <div className={`stat-card ${color}`} key={key}>
            <span className="stat-icon">{icon}</span>
            <span className="stat-num">{counts[key]}</span>
            <span className="stat-label">{label}</span>
            <div className="stat-bg" />
          </div>
        ))}
      </div>

      {/* ── Main Grid ── */}
      <div className="main-grid">

        {/* Task Feed */}
        <div className="panel">
          <div className="panel-title">
            Task Feed
            <span className="live-badge"><span className="live-dot" />Live</span>
          </div>
          <div className="filter-row">
            {['all', 'pending', 'running', 'done'].map(f => (
              <button
                key={f}
                className={`filter-btn ${filter === f ? 'active' : ''}`}
                onClick={() => setFilter(f)}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
          <div className="feed-scroll">
            {filtered.length === 0 ? (
              <div className="feed-empty">
                <span style={{ fontSize: 36 }}>🚀</span>
                <span>No tasks yet.<br />Submit one to get started!</span>
              </div>
            ) : filtered.map(t => (
              <div className="task-item" key={t.id}>
                <span className={`task-dot ${t.status}`} />
                <span className="task-payload">#{t.id} &nbsp;{t.payload}</span>
                <span className={`task-tag ${t.status}`}>{t.status}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right column */}
        <div className="right-col">

          {/* Submit Task */}
          <div className="panel">
            <div className="panel-title">Submit Task</div>

            <div className="field">
              <label className="field-label">API Endpoint</label>
              <div className="endpoint-row">
                <input
                  className="tq-input"
                  value={endpoint}
                  onChange={e => setEndpoint(e.target.value)}
                />
                <button className={`btn-connect ${connected ? 'connected' : ''}`} onClick={connect}>
                  {connected ? 'Connected' : 'Connect'}
                </button>
              </div>
            </div>

            <div className="field">
              <label className="field-label">Payload (JSON)</label>
              <textarea
                className="tq-textarea"
                value={payload}
                onChange={e => setPayload(e.target.value)}
                rows={4}
              />
              {payloadErr && <p className="err-msg">{payloadErr}</p>}
            </div>

            <button className="btn-dispatch" onClick={dispatch}>
              ⚡ Dispatch Task
            </button>
          </div>

          {/* Activity Log */}
          <div className="panel">
            <div className="panel-title">Activity Log</div>
            <div className="activity-log">
              {log.map((line, i) => (
                <div key={i} className={`log-line ${
                  line.includes('✓') ? 'success' :
                  line.includes('error') || line.includes('failed') || line.includes('disconnected') ? 'error' :
                  line.includes('Connecting') || line.includes('→') || line.includes('Loaded') ? 'info' : ''
                }`}>{line}</div>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}