import { useCallback, useEffect, useState } from 'react';
import {
  submitFinding,
  transitionFinding,
  reviewFinding,
  listFindingReviews,
  createAttachment,
  listAttachments,
  getFindingTimeline,
} from '../api/client.js';
import {
  availableTransitions,
  riskLabel,
  statusLabel,
} from '../stateMachine.js';
import Timeline from './Timeline.jsx';

const EMPTY_REVIEW = {
  reviewer_name: '',
  conclusion: 'accepted',
  comment: '',
};

const EMPTY_ATTACHMENT = {
  file_name: '',
  file_type: '',
  storage_note: '',
};

export default function ReviewSidebar({ finding, onClose, onChanged }) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [reviews, setReviews] = useState([]);
  const [attachments, setAttachments] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [reviewForm, setReviewForm] = useState(EMPTY_REVIEW);
  const [attachmentForm, setAttachmentForm] = useState(EMPTY_ATTACHMENT);
  const [transitionNote, setTransitionNote] = useState('');

  const findingId = finding.id;

  const loadSidebarData = useCallback(async () => {
    setError('');
    try {
      const [reviewList, attachmentList, timelineList] = await Promise.all([
        listFindingReviews(findingId),
        listAttachments({ linked_finding_id: findingId }),
        getFindingTimeline(findingId),
      ]);
      setReviews(reviewList || []);
      setAttachments(attachmentList || []);
      setTimeline(timelineList || []);
    } catch (err) {
      setError(err.message);
    }
  }, [findingId]);

  useEffect(() => {
    loadSidebarData();
  }, [loadSidebarData]);

  const runAction = async (action) => {
    setBusy(true);
    setError('');
    try {
      await action();
      await loadSidebarData();
      if (onChanged) await onChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const handleTransitionClick = (toStatus) => {
    if (finding.finding_status === 'draft' && toStatus === 'submitted') {
      return runAction(() => submitFinding(findingId));
    }
    const note = transitionNote.trim();
    return runAction(async () => {
      await transitionFinding(findingId, toStatus, note ? { note } : {});
      setTransitionNote('');
    });
  };

  const transitionButtonLabel = (toStatus) => {
    if (toStatus === 'submitted') return '提交';
    if (toStatus === 'reviewing') return '开始复核';
    if (toStatus === 'archived') return '归档';
    return `流转至${statusLabel(toStatus)}`;
  };

  const handleReviewSubmit = (event) => {
    event.preventDefault();
    runAction(async () => {
      await reviewFinding(findingId, {
        reviewer_name: reviewForm.reviewer_name.trim(),
        conclusion: reviewForm.conclusion,
        comment: reviewForm.comment.trim(),
      });
      setReviewForm(EMPTY_REVIEW);
    });
  };

  const handleAttachmentSubmit = (event) => {
    event.preventDefault();
    runAction(async () => {
      await createAttachment({
        file_name: attachmentForm.file_name.trim(),
        file_type: attachmentForm.file_type.trim(),
        storage_note: attachmentForm.storage_note.trim(),
        linked_finding_id: findingId,
      });
      setAttachmentForm(EMPTY_ATTACHMENT);
    });
  };

  const transitions = availableTransitions(finding.finding_status);
  // reviewing 状态的流转通过复核结论完成，不直接展示流转按钮
  const directTransitions = transitions.filter(
    (to) => !(finding.finding_status === 'reviewing' && (to === 'accepted' || to === 'rejected'))
  );

  return (
    <aside className="sidebar">
      <button className="btn btn-sm sidebar-close" onClick={onClose}>
        关闭
      </button>
      <h3>观察项复核</h3>
      {error && <div className="error-banner">{error}</div>}

      <div className="detail-grid">
        <div className="detail-item">
          <div className="detail-label">类别</div>
          <div className="detail-value">{finding.category}</div>
        </div>
        <div className="detail-item">
          <div className="detail-label">风险等级</div>
          <div className="detail-value">
            <span className={`badge badge-risk-${finding.risk_level}`}>
              {riskLabel(finding.risk_level)}
            </span>
          </div>
        </div>
        <div className="detail-item">
          <div className="detail-label">状态</div>
          <div className="detail-value">
            <span className={`badge badge-status-${finding.finding_status}`}>
              {statusLabel(finding.finding_status)}
            </span>
          </div>
        </div>
        <div className="detail-item">
          <div className="detail-label">填报人</div>
          <div className="detail-value">{finding.reported_by || '-'}</div>
        </div>
      </div>
      <div className="form-row" style={{ marginTop: 8 }}>
        <label>描述</label>
        <div className="meta-text">{finding.description}</div>
      </div>

      {directTransitions.length > 0 && (
        <div className="sidebar-section">
          <div className="form-row">
            <label>流转说明（可选，写入审计事件）</label>
            <textarea
              value={transitionNote}
              onChange={(e) => setTransitionNote(e.target.value)}
              placeholder="本次状态流转的说明"
            />
          </div>
          <div className="form-actions">
            {directTransitions.map((to) => (
              <button
                key={to}
                className="btn btn-primary"
                disabled={busy}
                onClick={() => handleTransitionClick(to)}
              >
                {transitionButtonLabel(to)}
              </button>
            ))}
          </div>
        </div>
      )}

      {finding.finding_status === 'reviewing' && (
        <div className="sidebar-section">
          <h3>复核结论</h3>
          <form onSubmit={handleReviewSubmit}>
            <div className="form-row">
              <label>复核人</label>
              <input
                value={reviewForm.reviewer_name}
                onChange={(e) =>
                  setReviewForm((prev) => ({
                    ...prev,
                    reviewer_name: e.target.value,
                  }))
                }
                required
              />
            </div>
            <div className="form-row">
              <label>结论</label>
              <select
                value={reviewForm.conclusion}
                onChange={(e) =>
                  setReviewForm((prev) => ({
                    ...prev,
                    conclusion: e.target.value,
                  }))
                }
              >
                <option value="accepted">通过</option>
                <option value="rejected">驳回</option>
              </select>
            </div>
            <div className="form-row">
              <label>复核意见</label>
              <textarea
                value={reviewForm.comment}
                onChange={(e) =>
                  setReviewForm((prev) => ({ ...prev, comment: e.target.value }))
                }
              />
            </div>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={busy}>
                提交复核结论
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="sidebar-section">
        <h3>复核记录</h3>
        {reviews.length === 0 ? (
          <div className="empty-state">暂无复核记录</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>复核人</th>
                <th>结论</th>
                <th>意见</th>
              </tr>
            </thead>
            <tbody>
              {reviews.map((review, index) => (
                <tr key={review.id ?? index}>
                  <td>{review.reviewer_name}</td>
                  <td>
                    <span
                      className={`badge badge-status-${review.conclusion}`}
                    >
                      {statusLabel(review.conclusion)}
                    </span>
                  </td>
                  <td>{review.comment || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="sidebar-section">
        <h3>附件登记</h3>
        <form onSubmit={handleAttachmentSubmit}>
          <div className="form-row">
            <label>文件名</label>
            <input
              value={attachmentForm.file_name}
              onChange={(e) =>
                setAttachmentForm((prev) => ({
                  ...prev,
                  file_name: e.target.value,
                }))
              }
              required
            />
          </div>
          <div className="form-row">
            <label>文件类型</label>
            <input
              value={attachmentForm.file_type}
              onChange={(e) =>
                setAttachmentForm((prev) => ({
                  ...prev,
                  file_type: e.target.value,
                }))
              }
              placeholder="如：photo / pdf / video"
              required
            />
          </div>
          <div className="form-row">
            <label>存储说明</label>
            <input
              value={attachmentForm.storage_note}
              onChange={(e) =>
                setAttachmentForm((prev) => ({
                  ...prev,
                  storage_note: e.target.value,
                }))
              }
              placeholder="存储位置或备注"
            />
          </div>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={busy}>
              登记附件
            </button>
          </div>
        </form>
        {attachments.length === 0 ? (
          <div className="empty-state" style={{ marginTop: 12 }}>
            暂无附件
          </div>
        ) : (
          <table className="data-table" style={{ marginTop: 12 }}>
            <thead>
              <tr>
                <th>文件名</th>
                <th>类型</th>
                <th>存储说明</th>
              </tr>
            </thead>
            <tbody>
              {attachments.map((attachment, index) => (
                <tr key={attachment.id ?? index}>
                  <td>{attachment.file_name}</td>
                  <td>{attachment.file_type}</td>
                  <td>{attachment.storage_note || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="sidebar-section">
        <h3>时间线</h3>
        <Timeline items={timeline} />
      </div>
    </aside>
  );
}
