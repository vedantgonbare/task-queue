import { useEffect, useState } from 'react';
import './TaskModal.css';

const API = 'http://localhost:8000';

function fmt(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString() + '\n' + d.toTimeString().slice(0, 8);
}

function duration(start, end) {
  if (!start || !end) return null;
  const ms = new Date(end) - new Date(start);
  return (ms / 1000).toFixed(1) + 's';
}

function prettyJson(str) {
  try { return JSON.stringify(JSON.parse(str), null, 2); }
  catch { return str; }
}

export default function TaskModal({ taskId, onClose, onRetry }) {
  const [task, setTask]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  useEffect(() => {
    if (!taskId) return;
    setLoading(true);
    setError('');
    fetch(`${API}/tasks/${taskId}`)
      .then(r => { if (!r.ok) throw new Error('Not found'); return r.json(); })
      .then(data => { setTask(data); setLoading(false); })
      .catch(e  => { setError(e.message); setLoading(false); });
  }, [taskId]);

  // Close on backdrop click
  const onBackdrop = (e) => { if (e.target === e.currentTarget) onClose(); };

  // Close on Escape key
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const statusColor = {
    pending: 'amber',
    running: 'blue',
    done:    'green',
    failed:  'red',
  }[task?.status] || 'gray';

  const dur = task ? duration(task.started_at, task.completed_at) : null;

  // Timeline step states
  const steps = [
    { label: 'Created', time: task?.created_at,   active: true },
    { label: 'Running', time: task?.started_at,   active: !!task?.started_at },
    { label: 'Done',    time: task?.completed_at,  active: !!task?.completed_at },
  ];

  return (
    <div className="modal-backdrop" onClick={onBackdrop}>
      <div className="modal-card">

        {/* Header */}
        <div className="modal-header">
          <div>
            <div className="modal-title-row">
              <span className="modal-title">Task Detail</span>
              {task && (
                <span className={`modal-status-badge ${statusColor}`}>
                  {task.status.toUpperCase()}
                </span>
              )}
            </div>
            <span className="modal-id">
              #{taskId?.slice(0, 22)}…
            </span>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {loading && (
          <div className="modal-loading">Loading task…</div>
        )}

        {error && (
          <div className="modal-error">Could not load task: {error}</div>
        )}

        {task && !loading && (
          <>
            {/* Timeline */}
            <div className="modal-timeline">
              <div className="timeline-track">
                {steps.map((step, i) => (
                  <div className="timeline-step" key={step.label}>
                    <div className={`timeline-dot ${step.active ? 'active' : ''}`} />
                    <span className="timeline-label">{step.label}</span>
                    {i < steps.length - 1 && (
                      <div className={`timeline-line ${steps[i + 1].active ? 'active' : ''}`} />
                    )}
                  </div>
                ))}
              </div>
              <div className="timeline-times">
                <span>{task.created_at   ? new Date(task.created_at).toTimeString().slice(0,8)   : '—'}</span>
                {dur && <span className="timeline-dur">⏱ {dur}</span>}
                <span>{task.completed_at ? new Date(task.completed_at).toTimeString().slice(0,8) : '—'}</span>
              </div>
            </div>

            {/* Body */}
            <div className="modal-body">

              {/* Payload */}
              <div className="modal-field">
                <label className="field-label">Payload</label>
                <pre className="payload-box">{prettyJson(task.payload)}</pre>
              </div>

              {/* Timestamps */}
              <div className="modal-two-col">
                <div className="modal-field">
                  <label className="field-label">Created at</label>
                  <span className="mono-val">{fmt(task.created_at)}</span>
                </div>
                <div className="modal-field">
                  <label className="field-label">Completed at</label>
                  <span className="mono-val">{fmt(task.completed_at)}</span>
                </div>
              </div>

              {/* Metric cards */}
              <div className="modal-two-col">
                <div className={`metric-card ${dur ? 'green' : 'gray'}`}>
                  <span className="metric-label">Duration</span>
                  <span className="metric-val">{dur || '—'}</span>
                </div>
                <div className="metric-card purple">
                  <span className="metric-label">Task ID</span>
                  <span className="metric-id">{taskId?.slice(0, 8)}</span>
                </div>
              </div>

            </div>

            {/* Footer */}
            <div className="modal-footer">
              <button className="btn-close-modal" onClick={onClose}>Close</button>
              <button
                className="btn-retry"
                onClick={() => { onRetry(task.payload); onClose(); }}
              >
                ↺ Retry Task
              </button>
            </div>
          </>
        )}

      </div>
    </div>
  );
}