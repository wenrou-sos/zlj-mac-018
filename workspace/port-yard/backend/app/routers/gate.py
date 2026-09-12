from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from ..database import get_db
from ..models import Container, GateRecord, Appointment, ContainerStatus
from ..schemas import GateInRequest, GateOutRequest, GateRecordOut
from .yard import allocate_position

router = APIRouter(prefix="/api/gate", tags=["闸口"])


def _record(db: Session, c: Container, direction: str, truck: str, driver: str,
            gate: str, result: str, remark: str = "") -> GateRecord:
    rec = GateRecord(container_id=c.id, direction=direction, truck_no=truck,
                     driver=driver, gate=gate, result=result, remark=remark)
    db.add(rec)
    return rec


@router.post("/in", response_model=GateRecordOut)
def gate_in(req: GateInRequest, db: Session = Depends(get_db)):
    """进场: 校验预约 -> 自动分配堆位 -> 记录进闸"""
    no = req.container_no.upper()
    c = db.query(Container).filter(Container.container_no == no).first()
    if not c:
        raise HTTPException(404, "箱号未登记，请先创建集装箱档案")
    if c.status == ContainerStatus.IN_YARD.value:
        raise HTTPException(400, "该箱已在场内")
    if c.status == ContainerStatus.OUT.value:
        raise HTTPException(400, "该箱已出场，如需再次进场请重新预约")

    # 预约校验
    appt = db.query(Appointment).filter(
        Appointment.container_no == no, Appointment.status == "PENDING"
    ).order_by(Appointment.planned_time).first()
    if not appt:
        _record(db, c, "IN", req.truck_no, req.driver, req.gate, "REJECTED", "无有效进场预约")
        db.commit()
        raise HTTPException(403, "进闸拒绝：无有效进场预约")

    # 自动分配堆位
    pos = allocate_position(db)
    if not pos:
        _record(db, c, "IN", req.truck_no, req.driver, req.gate, "REJECTED", "堆场已满")
        db.commit()
        raise HTTPException(409, "进闸拒绝：堆场已满")

    pos.occupied = True
    c.position_id = pos.id
    c.status = ContainerStatus.IN_YARD.value
    c.in_time = datetime.utcnow()
    appt.status = "COMPLETED"
    rec = _record(db, c, "IN", req.truck_no, req.driver, req.gate, "OK",
                  f"分配堆位 {pos.code}")
    db.commit()
    db.refresh(rec)
    return rec


@router.post("/out", response_model=GateRecordOut)
def gate_out(req: GateOutRequest, db: Session = Depends(get_db)):
    """出场(提箱)校验: 在场? 无扣箱? 提箱单号有效? -> 释放堆位 -> 记录出闸"""
    no = req.container_no.upper()
    c = db.query(Container).filter(Container.container_no == no).first()
    if not c:
        raise HTTPException(404, "箱号不存在")
    if c.status != ContainerStatus.IN_YARD.value:
        raise HTTPException(400, "该箱不在场内，无法提箱")

    # 提箱校验
    if c.has_hold:
        _record(db, c, "OUT", req.truck_no, req.driver, req.gate, "REJECTED", "海关/查验扣箱")
        db.commit()
        raise HTTPException(403, "出闸拒绝：该箱处于扣箱状态")
    if not req.pickup_no or len(req.pickup_no.strip()) < 6:
        _record(db, c, "OUT", req.truck_no, req.driver, req.gate, "REJECTED", "提箱单号无效")
        db.commit()
        raise HTTPException(403, "出闸拒绝：请提供有效提箱单号(至少6位)")

    # 释放堆位
    if c.position:
        c.position.occupied = False
    pos_code = c.position.code if c.position else ""
    c.position_id = None
    c.status = ContainerStatus.OUT.value
    c.out_time = datetime.utcnow()
    rec = _record(db, c, "OUT", req.truck_no, req.driver, req.gate, "OK",
                  f"提箱单 {req.pickup_no}，释放堆位 {pos_code}")
    db.commit()
    db.refresh(rec)
    return rec


@router.get("/records", response_model=List[GateRecordOut])
def list_records(limit: int = 100, db: Session = Depends(get_db)):
    recs = db.query(GateRecord).order_by(GateRecord.time.desc()).limit(limit).all()
    return [
        {**{c.name: getattr(r, c.name) for c in GateRecord.__table__.columns},
         "container_no": r.container.container_no if r.container else ""}
        for r in recs
    ]
