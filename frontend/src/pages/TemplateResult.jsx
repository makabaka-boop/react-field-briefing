import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api/client.js';

// Shown after "按模板创建项目". Reads the freshly generated project and its
// batch of sites from the backend (never from client-held arrays) so it
// reflects exactly what was committed in the transaction.
export default function TemplateResult() {
  const { projectId } = useParams();
  const [params] = useSearchParams();
  const templateName = params.get('template') || '';
  const [project, setProject] = useState(null);
  const [sites, setSites] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const p = await api.getProject(projectId);
        setProject(p);
        const res = await api.listSites({ project_id: projectId });
        setSites(res.items);
      } catch (err) {
        setError(err.message);
      }
    }
    load();
  }, [projectId]);

  if (error) return <div className="card"><div className="form-error">{error}</div></div>;
  if (!project) return <div className="card">加载中…</div>;

  return (
    <div>
      <div className="card" data-testid="template-result">
        <h2>创建结果</h2>
        <p className="muted">
          已按模板{templateName ? `「${templateName}」` : ''}在一个事务内创建项目并批量生成
          {sites.length} 个地点。
        </p>
        <p>
          项目：<strong>{project.project_name}</strong>（{project.project_code}）·
          负责人 {project.owner_name} · 状态 {project.status}
        </p>
        <Link to={`/projects/${project.id}`}>进入项目详情 →</Link>
      </div>

      <div className="card">
        <h3>已生成地点</h3>
        <table>
          <thead>
            <tr><th>编号</th><th>名称</th><th>区域</th><th>地址</th><th></th></tr>
          </thead>
          <tbody>
            {sites.map((s) => (
              <tr key={s.id}>
                <td>{s.site_code}</td>
                <td>{s.site_name}</td>
                <td>{s.region || '—'}</td>
                <td>{s.address_text || '—'}</td>
                <td><Link to={`/sites/${s.id}`}>进入</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
        {!sites.length && <p className="muted">未生成地点。</p>}
      </div>
    </div>
  );
}
