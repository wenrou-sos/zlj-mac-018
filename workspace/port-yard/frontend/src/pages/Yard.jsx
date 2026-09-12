import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Yard() {
  const [block, setBlock] = useState('A')
  const [positions, setPositions] = useState([])
  const [summary, setSummary] = useState([])

  useEffect(() => {
    api.get(`/yard/positions?block=${block}`).then(setPositions).catch(alert)
  }, [block])
  useEffect(() => {
    api.get('/yard/summary').then(setSummary).catch(alert)
  }, [positions])

  // 按 排(bay) 分组渲染
  const bays = {}
  positions.forEach((p) => {
    ;(bays[p.bay] = bays[p.bay] || []).push(p)
  })

  return (
    <div>
      <h2>堆位图</h2>
      <div className="summary-bar">
        {summary.map((s) => (
          <button key={s.block} className={`block-btn ${block === s.block ? 'active' : ''}`}
            onClick={() => setBlock(s.block)}>
            {s.block} 区 <span className="muted">{s.occupied}/{s.total} ({s.rate}%)</span>
          </button>
        ))}
      </div>
      <div className="legend">
        <span className="cell free"></span> 空位
        <span className="cell used"></span> 占用
      </div>
      <div className="yard-grid">
        {Object.keys(bays).sort().map((bay) => (
          <div key={bay} className="bay">
            <div className="bay-title">排 {bay}</div>
            <div className="bay-cells">
              {bays[bay].map((p) => (
                <div key={p.id} className={`cell ${p.occupied ? 'used' : 'free'}`}
                  title={`${p.code}${p.container_no ? ' · ' + p.container_no : ' (空)'}`}>
                  {p.occupied ? p.container_no?.slice(-4) : ''}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
