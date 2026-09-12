from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models import YardPosition, Container
from ..schemas import YardPositionOut

router = APIRouter(prefix="/api/yard", tags=["堆位"])


def to_out(p: YardPosition) -> dict:
    return {
        "id": p.id, "block": p.block, "bay": p.bay, "row": p.row, "tier": p.tier,
        "occupied": p.occupied, "code": p.code,
        "container_no": p.container.container_no if p.container else None,
    }


@router.get("/positions", response_model=List[YardPositionOut])
def list_positions(block: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(YardPosition)
    if block:
        q = q.filter(YardPosition.block == block.upper())
    return [to_out(p) for p in q.order_by(YardPosition.block, YardPosition.bay,
                                          YardPosition.row, YardPosition.tier).all()]


@router.get("/summary")
def yard_summary(db: Session = Depends(get_db)):
    """各区占用率"""
    rows = db.query(YardPosition).all()
    summary = {}
    for p in rows:
        s = summary.setdefault(p.block, {"block": p.block, "total": 0, "occupied": 0})
        s["total"] += 1
        s["occupied"] += 1 if p.occupied else 0
    for s in summary.values():
        s["rate"] = round(s["occupied"] / s["total"] * 100, 1) if s["total"] else 0
    return sorted(summary.values(), key=lambda x: x["block"])


def allocate_position(db: Session, prefer_block: Optional[str] = None) -> Optional[YardPosition]:
    """自动分配堆位: 优先指定区，按 区-排-列-层 顺序找第一个空位"""
    q = db.query(YardPosition).filter(YardPosition.occupied == False)  # noqa: E712
    if prefer_block:
        q = q.filter(YardPosition.block == prefer_block.upper())
    pos = q.order_by(YardPosition.block, YardPosition.bay,
                     YardPosition.row, YardPosition.tier).first()
    if not pos and prefer_block:  # 指定区满了则全场找
        pos = db.query(YardPosition).filter(YardPosition.occupied == False).order_by(
            YardPosition.block, YardPosition.bay, YardPosition.row, YardPosition.tier).first()
    return pos


@router.post("/allocate/{container_id}", response_model=YardPositionOut)
def manual_allocate(container_id: int, block: Optional[str] = None, db: Session = Depends(get_db)):
    c = db.get(Container, container_id)
    if not c:
        raise HTTPException(404, "集装箱不存在")
    if c.position_id:
        raise HTTPException(400, f"已分配堆位 {c.position.code}")
    pos = allocate_position(db, block)
    if not pos:
        raise HTTPException(409, "堆场已满，无可用堆位")
    pos.occupied = True
    c.position_id = pos.id
    db.commit()
    db.refresh(pos)
    return to_out(pos)
