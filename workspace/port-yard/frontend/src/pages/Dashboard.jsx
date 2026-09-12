import { useEffect, useState } from 'react'
import { api } from '../api'

const fmt = (s) => (s ? new Date(s).toLocaleString('zh-CN', { hour12: false }) : '-')

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [overdue, setOverdue] = useState([])

  const load = () => {
    api.get('/dashboard').then(setStats).catch(alert)
    api.get('/containers/overdue').then(setOverdue).catch(alert)
  }
  useEffect(load, [])

  if (!stats) return <p>加载中…</p>
  const cards = [
    { label: '在场箱量', value: stats.in_yard, cls: 'blue' },
    { label: '超期箱', value: stats.overdue, cls: stats.overdue ? 'red' : '' },
    { label: '待进场预约', value: stats.pending_appointments, cls: 'orange' },
    { label: '在港船舶', value: stats.vessels_active, cls: 'blue' },
    { label: '堆场利用率', value: stats.yard_rate + '%', cls: stats.yard_rate > 85 ? 'red' : 'green' },
    { label: '今日进/出闸', value: `${stats.today_in} / ${stats.today_out}`, cls: '' },
  ]
  return (
    <div>
      <h2>运营看板</h2>
      <div className="cards">
        {cards.map((c) => (
          <div key={c.label} className={`card ${c.cls}`}>
            <div className="card-value">{c.value}</div>
            <div className="card-label">{c.label}</div>
          </div>
        ))}
      </div>

      <h3>⚠️ 超期箱提醒（在场超过免堆存期）</h3>
      {overdue.length === 0 ? <p className="muted">暂无超期箱</p> : (
        <table>
          <thead>
            <tr><th>箱号</th><th>尺寸/箱型</th><th>堆位</th><th>货主</th><th>进场时间</th><th>在场天数</th><th>免堆期</th></tr>
          </thead>
          <tbody>
            {overdue.map((c) => (
              <tr key={c.id} className="row-red">
                <td className="mono">{c.container_no}</td>
                <td>{c.size}'{c.ctype}</td>
                <td>{c.position_code || '-'}</td>
                <td>{c.consignee}</td>
                <td>{fmt(c.in_time)}</td>
                <td>{c.days_in_yard} 天</td>
                <td>{c.free_days} 天</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
