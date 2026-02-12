from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from miniorm.session import Session
from models import Procedure
from deps import get_session

router = APIRouter()

class ProcedureCreate(BaseModel):
    name: str
    description: str = ""
    price: float = 0

class ProcedureUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None

def _apply_procedure_filters(procs, name, description, price_min, price_max):
    if name:
        procs = [p for p in procs if name.lower() in (p.name or "").lower()]
    if description:
        procs = [p for p in procs if description.lower() in (p.description or "").lower()]
    if price_min is not None:
        try:
            pm = float(price_min)
            procs = [p for p in procs if p.price is not None and p.price >= pm]
        except (ValueError, TypeError):
            pass
    if price_max is not None:
        try:
            px = float(price_max)
            procs = [p for p in procs if p.price is not None and p.price <= px]
        except (ValueError, TypeError):
            pass
    return procs

@router.get("/api/procedures")
def get_procedures(
    session: Session = Depends(get_session),
    name: str = Query(None),
    description: str = Query(None),
    price_min: float = Query(None),
    price_max: float = Query(None),
):
    procs = session.query(Procedure).all()
    procs = _apply_procedure_filters(procs, name, description, price_min, price_max)
    return [
        {"procedure_id": p.procedure_id, "name": p.name, "description": p.description, "price": p.price}
        for p in procs
    ]

@router.post("/api/procedures")
def add_procedure(proc: ProcedureCreate, session: Session = Depends(get_session)):
    new_proc = Procedure(name=proc.name, description=proc.description, price=proc.price)
    session.add(new_proc)
    session.commit()
    return {
        "procedure_id": new_proc.procedure_id,
        "name": new_proc.name,
        "description": new_proc.description,
        "price": new_proc.price,
        "message": "Procedure added successfully"
    }

@router.put("/api/procedures/{procedure_id}")
def update_procedure(procedure_id: int, proc: ProcedureUpdate, session: Session = Depends(get_session)):
    existing = session.get(Procedure, procedure_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Procedure not found")
    if proc.name is not None:
        setattr(existing, "name", proc.name)
    if proc.description is not None:
        setattr(existing, "description", proc.description)
    if proc.price is not None:
        setattr(existing, "price", proc.price)
    session.update(existing)
    session.commit()
    return {
        "procedure_id": existing.procedure_id,
        "name": existing.name,
        "description": existing.description,
        "price": existing.price,
        "message": "Procedure updated"
    }

@router.delete("/api/procedures/{procedure_id}")
def delete_procedure(procedure_id: int, session: Session = Depends(get_session)):
    existing = session.get(Procedure, procedure_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Procedure not found")
    session.delete(existing)
    session.commit()
    return {"message": "Procedure deleted"}
