import { useEffect, useState } from 'react'
import { api } from '../api'

const fmt = (s) => (s ? new Date(s).toLocaleString('zh-CN', { hour12: false }) : '-')
const STATUS = { PENDING: '待进场', COMPLETED: '已完成', CANCELLED: '已取消' }

export default function Appointments() {
  const [list, setList] = useState([])
  const [vessels, setVessels] = useState([])
  const [form, setForm] = useState({ container_no: '', vessel_id: '', planned_time: '', truck_no: '' })
  const [msg, setMsg] = useState('')

  const load = () => api.get('/appointments').then(setList).catch((e) => setMsg(e.message))
  useEffect(load, [])
  useEffect(() => { api.get('/vessels').then(setVessels) }, [])

  const submit = async (e) => {
    e.preventDefault()
    setMsg('')
    try {
      await api.post('/appointments', {
        ...form,
        vessel_id: form.vessel_id ? Number(form.vessel_id) : null,
      })
      setForm({ container_no: '', vessel_id: '', planned_time: '', truck_no: '' })
      setMsg('✅ 预约已创建（若箱号未登记已自动建档）')
      load()
    } catch (err) { setMsg('❌ ' + err.message) }
  }

  const cancel = async (a) => {
    try { await api.patch(`/appointments/${a.id}/cancel`); load() }
    catch (e) { alert(e.message) }
  }

  return (
    <div>
      <h2>进场预约</h2>
      <form className="panel form-row" onSubmit={submit}>
        <input placeholder="箱号 (如 MSKU1234567)" value={form.container_no} required maxLength={11}
          onChange={(e) => setForm({ ...form, container_no: e.target.value.toUpperCase() })} />
        <select value={form.vessel_id} onChange={(e) => setForm({ ...form, vessel_id: e.target.value })}>
          <option value="">关联船期(可选)</option>
          {vessels.map((v) => <option key={v.id} value={v.id}>{v.vessel_name} / {v.voyage}</option>)}
        </select>
        <label>计划进场 <input type="datetime-local" value={form.planned_time} required
          onChange={(e) => setForm({ ...form, planned_time: e.target.value })} /></label>
        <input placeholder="车牌号" value={form.truck_no}
          onChange={(e) => setForm({ ...form, truck_no: e.target.value })} />
        <button type="submit">创建预约</button>
      </form>
      {msg && <p className="msg">{msg}</p>}

      <table>
        <thead>
          <tr><th>箱号</th><th>计划进场时间</th><th>车牌</th><th>状态</th><th>创建时间</th><th>操作</th></tr>
        </thead>
        <tbody>
          {list.map((a) => (
            <tr key={a.id}>
              <td className="mono">{a.container_no}</td>
              <td>{fmt(a.planned_time)}</td>
              <td>{a.truck_no}</td>
              <td><span className={`tag a-${a.status}`}>{STATUS[a.status]}</span></td>
              <td>{fmt(a.created_at)}</td>
              <td>
                {a.status === 'PENDING' &&
                  <button className="btn-sm" onClick={() => cancel(a)}>取消</button>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
