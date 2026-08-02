import { useEffect, useState } from 'react';
import { api, ApiError } from '../api/client.js';
import { nextStatuses, STATUS_LABELS } from '../state/statusMachine.js';
import { StatusBadge } from './Badge.jsx';
import Timeline from './Timeline.jsx';

// Side panel for reviewing a single finding: submit, record a review
// conclusion, drive raw status transitions (with a note captured to audit),
// register attachment metadata, and view the merged timeline.
export default function ReviewSidebar({ finding, onChanged }) {
  const [note, setNote] = useState('');
  const [reviewer, setReviewer] = useState('');
  const [error, setError] = useState('');
  const [timeline, setTimeline] = useState([]);
  const [attach, setAttach] = useState({ file_name: '', file_type: '' });

  async function loadTimeline() {
    if (!finding) return;
    try {
      const tl = await api.findingTimeline(finding.id);
      setTimeline(tl.events);
    } catch {
      setTimeline([]);
    }
  }

  useEffect(() => {
    setError('');
    setNote('');
    loadTimeline();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [finding && finding.id, finding && finding.finding_status]);

  if (!finding) {
    return (
      <aside className="card detail-side">
        <h3>复核</h3>
        <p className="muted">从表格中选择一个观察项进行复核。</p>
      </aside>
    );
  }

  async function run(fn) {
    setError('');
    try {
      await fn();
      onChanged && (await onChanged());
      await loadTimeline();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '操作失败');
    }
  }

  const submit = () =>
    run(() => api.submitFinding(finding.id, { note, actor_name: reviewer }));

  const review = (conclusion) =>
    run(() =>
      api.reviewFinding(finding.id, {
        reviewer_name: reviewer || '复核人',
        conclusion,
        review_note: note,
      }),
    );

  const transition = (target) =>
    run(() =>
      api.transitionFinding(finding.id, {
        target_status: target,
        actor_name: reviewer,
        note,
      }),
    );

  const addAttachment = () =>
    run(async () => {
      await api.createAttachment({
        ...attach,
        linked_finding_id: finding.id,
      });
      setAttach({ file_name: '', file_type: '' });
    });

  return (
    <aside className="card detail-side" data-testid="review-sidebar">
      <h3>复核 · 观察项 #{finding.id}</h3>
      <p>
        当前状态：<StatusBadge status={finding.finding_status} />
      </p>
      {error && <div className="form-error" role="alert">{error}</div>}

      <div className="field">
        <label>复核人 / 操作者</label>
        <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} />
      </div>
      <div className="field">
        <label>说明 / 流转备注（记入审计）</label>
        <textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
      </div>

      {finding.finding_status === 'draft' && (
        <button onClick={submit}>提交观察项</button>
      )}
      {['submitted', 'reviewing'].includes(finding.finding_status) && (
        <div className="row" style={{ gap: 8 }}>
          <button onClick={() => review('accept')}>采纳</button>
          <button className="secondary" onClick={() => review('reject')}>
            驳回
          </button>
          <button className="secondary" onClick={() => review('needs_more_info')}>
            补充信息
          </button>
        </div>
      )}

      <div className="field" style={{ marginTop: 16 }}>
        <label>状态流转</label>
        <div className="row" style={{ gap: 8 }}>
          {nextStatuses(finding.finding_status).map((s) => (
            <button key={s} className="secondary" onClick={() => transition(s)}>
              → {STATUS_LABELS[s]}
            </button>
          ))}
          {!nextStatuses(finding.finding_status).length && (
            <span className="muted">已到终态。</span>
          )}
        </div>
      </div>

      <div className="field" style={{ marginTop: 16 }}>
        <label>附件元数据登记</label>
        <input
          placeholder="文件名 file_name"
          value={attach.file_name}
          onChange={(e) => setAttach({ ...attach, file_name: e.target.value })}
        />
        <input
          style={{ marginTop: 6 }}
          placeholder="类型 file_type"
          value={attach.file_type}
          onChange={(e) => setAttach({ ...attach, file_type: e.target.value })}
        />
        <button
          className="secondary"
          style={{ marginTop: 6 }}
          onClick={addAttachment}
        >
          登记附件
        </button>
      </div>

      <h4>时间线</h4>
      <Timeline events={timeline} />
    </aside>
  );
}
