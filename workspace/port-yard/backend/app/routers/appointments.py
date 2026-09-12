from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Appointment, Container, Vessel
from ..schemas import AppointmentIn, AppointmentOut, valid_container_no

router = APIRouter(prefix="/api/appointments", tags=["预约"])


@router.get("", response_model=List[AppointmentOut])
def list_appointments(status: str = None, db: Session = Depends(get_db)):
    q = db.query(Appointment)
    if status:
        q = q.filter(Appointment.status == status)
    return q.order_by(Appointment.planned_time).all()


@router.post("", response_model=AppointmentOut)
def create_appointment(data: AppointmentIn, db: Session = Depends(get_db)):
    no = data.container_no.upper()
    if not valid_container_no(no):
        raise HTTPException(400, "箱号格式错误")
    # 已有待处理预约则拒绝
    dup = db.query(Appointment).filter(
        Appointment.container_no == no, Appointment.status == "PENDING").first()
    if dup:
        raise HTTPException(409, "该箱已有待进场预约")
    if data.vessel_id and not db.get(Vessel, data.vessel_id):
        raise HTTPException(404, "船期不存在")
    # 若箱档案不存在则自动建档(预约即登记)
    c = db.query(Container).filter(Container.container_no == no).first()
    if not c:
        c = Container(container_no=no, vessel_id=data.vessel_id)
        db.add(c)
    elif data.vessel_id and not c.vessel_id:
        c.vessel_id = data.vessel_id
    appt = Appointment(**{**data.model_dump(), "container_no": no})
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt


@router.patch("/{appt_id}/cancel", response_model=AppointmentOut)
def cancel_appointment(appt_id: int, db: Session = Depends(get_db)):
    a = db.get(Appointment, appt_id)
    if not a:
        raise HTTPException(404, "预约不存在")
    if a.status != "PENDING":
        raise HTTPException(400, "仅待处理预约可取消")
    a.status = "CANCELLED"
    db.commit()
    db.refresh(a)
    return a
