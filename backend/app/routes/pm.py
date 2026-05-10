"""Project Management routes: tasks, daily logs, RFIs, punch list, submittals, meetings, photos."""
import os, uuid
from datetime import datetime
from typing import Optional, List, Tuple
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    User, Project, Task, TaskComment, DailyLog, RFI,
    PunchItem, Submittal, MeetingMinutes, PhotoLog,
)
from ..dependencies import get_current_user, get_current_org
from .audit import log as audit_log

router = APIRouter(prefix="/api/pm", tags=["pm"])

# ── Role helpers ──────────────────────────────────────────────────────────────

PM_WRITE_ROLES = {"owner", "admin", "pm_admin", "site_supervisor", "editor", "vendor_pm"}
PM_READ_ROLES  = PM_WRITE_ROLES | {"finance_admin", "pm_viewer", "finance_viewer", "viewer"}

def _pm_write(org_ctx: Tuple = Depends(get_current_org)):
    org, mem = org_ctx
    if mem.role not in PM_WRITE_ROLES:
        raise HTTPException(403, "PM write access required")
    return org, mem

def _pm_read(org_ctx: Tuple = Depends(get_current_org)):
    org, mem = org_ctx
    if mem.role not in PM_READ_ROLES:
        raise HTTPException(403, "PM read access required")
    return org, mem

def _proj(project_id: int, org_id: int, db: Session) -> Project:
    p = db.query(Project).filter(Project.id == project_id, Project.org_id == org_id).first()
    if not p:
        raise HTTPException(404, "Project not found")
    return p


# ══════════════════════════════════════════════════════════════════════════════
#  TASKS
# ══════════════════════════════════════════════════════════════════════════════

def _task_out(t: Task, db: Session) -> dict:
    subtask_count = db.query(Task).filter(Task.parent_id == t.id).count()
    comment_count = db.query(TaskComment).filter(TaskComment.task_id == t.id).count()
    return {
        "id": t.id, "project_id": t.project_id, "parent_id": t.parent_id,
        "title": t.title, "description": t.description, "task_type": t.task_type,
        "status": t.status, "priority": t.priority,
        "assigned_to": t.assigned_to,
        "assigned_to_name": t.assignee.username if t.assignee else None,
        "start_date": t.start_date, "end_date": t.end_date, "due_date": t.due_date,
        "percent_complete": t.percent_complete,
        "location": t.location, "tags": t.tags,
        "created_by": t.created_by,
        "created_by_name": t.creator.username if t.creator else None,
        "created_at": str(t.created_at), "updated_at": str(t.updated_at),
        "subtask_count": subtask_count, "comment_count": comment_count,
    }


@router.get("/tasks")
def list_tasks(
    project_id: int = Query(...),
    status: Optional[str] = None,
    assigned_to: Optional[int] = None,
    parent_id: Optional[int] = None,
    org_ctx: Tuple = Depends(_pm_read),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, mem = org_ctx
    _proj(project_id, org.id, db)
    q = db.query(Task).filter(Task.project_id == project_id, Task.org_id == org.id)
    if status:
        q = q.filter(Task.status == status)
    if assigned_to:
        q = q.filter(Task.assigned_to == assigned_to)

    # Vendors only see their own tasks
    if mem.role == "vendor_pm":
        q = q.filter(Task.assigned_to == current_user.id)

    if parent_id is not None:
        q = q.filter(Task.parent_id == (None if parent_id == 0 else parent_id))

    tasks = q.order_by(Task.due_date.nullslast(), Task.priority.desc(), Task.created_at).all()
    return [_task_out(t, db) for t in tasks]


@router.post("/tasks")
def create_task(
    body: dict,
    org_ctx: Tuple = Depends(_pm_write),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, mem = org_ctx
    project_id = body.get("project_id")
    if not project_id:
        raise HTTPException(400, "project_id required")
    _proj(project_id, org.id, db)

    task = Task(
        org_id=org.id, project_id=project_id,
        parent_id=body.get("parent_id"),
        title=(body.get("title") or "").strip() or "Untitled task",
        description=body.get("description"),
        task_type=body.get("task_type", "task"),
        status=body.get("status", "not_started"),
        priority=body.get("priority", "medium"),
        assigned_to=body.get("assigned_to"),
        start_date=body.get("start_date"),
        end_date=body.get("end_date"),
        due_date=body.get("due_date"),
        percent_complete=int(body.get("percent_complete", 0)),
        location=body.get("location"),
        tags=body.get("tags"),
        created_by=current_user.id,
    )
    db.add(task); db.commit(); db.refresh(task)
    audit_log(db, org.id, current_user, "create_task", "task", task.id,
              detail=f"Created task '{task.title}'")
    return _task_out(task, db)


@router.put("/tasks/{task_id}")
def update_task(
    task_id: int,
    body: dict,
    org_ctx: Tuple = Depends(_pm_write),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, mem = org_ctx
    task = db.query(Task).filter(Task.id == task_id, Task.org_id == org.id).first()
    if not task:
        raise HTTPException(404, "Task not found")

    # Vendor PM can only update status/percent on their own tasks
    if mem.role == "vendor_pm":
        if task.assigned_to != current_user.id:
            raise HTTPException(403, "Can only update your own tasks")
        allowed = {"status", "percent_complete", "description"}
        body = {k: v for k, v in body.items() if k in allowed}

    FIELDS = {"title","description","task_type","status","priority","assigned_to",
              "start_date","end_date","due_date","percent_complete","location","tags","parent_id"}
    for k, v in body.items():
        if k in FIELDS:
            setattr(task, k, v)
    task.updated_at = datetime.utcnow()
    db.commit(); db.refresh(task)
    audit_log(db, org.id, current_user, "update_task", "task", task.id,
              detail=f"Updated task '{task.title}' → status={task.status}")
    return _task_out(task, db)


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    org_ctx: Tuple = Depends(_pm_write),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, _ = org_ctx
    task = db.query(Task).filter(Task.id == task_id, Task.org_id == org.id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    title = task.title
    db.delete(task); db.commit()
    audit_log(db, org.id, current_user, "delete_task", "task", task_id,
              detail=f"Deleted task '{title}'")
    return {"message": "Task deleted"}


@router.get("/tasks/{task_id}/comments")
def list_comments(task_id: int, org_ctx: Tuple = Depends(_pm_read), db: Session = Depends(get_db)):
    org, _ = org_ctx
    task = db.query(Task).filter(Task.id == task_id, Task.org_id == org.id).first()
    if not task: raise HTTPException(404, "Task not found")
    comments = db.query(TaskComment).filter(TaskComment.task_id == task_id).order_by(TaskComment.created_at).all()
    return [{"id": c.id, "comment": c.comment, "user_id": c.user_id,
             "username": c.user.username if c.user else None, "created_at": str(c.created_at)}
            for c in comments]


@router.post("/tasks/{task_id}/comments")
def add_comment(
    task_id: int, body: dict,
    org_ctx: Tuple = Depends(_pm_read),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, _ = org_ctx
    task = db.query(Task).filter(Task.id == task_id, Task.org_id == org.id).first()
    if not task: raise HTTPException(404, "Task not found")
    c = TaskComment(task_id=task_id, user_id=current_user.id, comment=body.get("comment","").strip())
    db.add(c); db.commit(); db.refresh(c)
    return {"id": c.id, "comment": c.comment, "username": current_user.username, "created_at": str(c.created_at)}


# ══════════════════════════════════════════════════════════════════════════════
#  DAILY LOGS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/daily-logs")
def list_daily_logs(
    project_id: int = Query(...),
    org_ctx: Tuple = Depends(_pm_read),
    db: Session = Depends(get_db),
):
    org, _ = org_ctx
    _proj(project_id, org.id, db)
    logs = db.query(DailyLog).filter(DailyLog.project_id == project_id, DailyLog.org_id == org.id)\
             .order_by(DailyLog.log_date.desc()).all()
    return [{"id": l.id, "log_date": l.log_date, "weather": l.weather,
             "temperature": l.temperature, "crew_count": l.crew_count,
             "work_summary": l.work_summary, "issues": l.issues, "delays": l.delays,
             "visitors": l.visitors, "created_by": l.creator.username if l.creator else None,
             "created_at": str(l.created_at)} for l in logs]


@router.post("/daily-logs")
def create_daily_log(
    body: dict,
    org_ctx: Tuple = Depends(_pm_write),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, _ = org_ctx
    project_id = body.get("project_id")
    if not project_id: raise HTTPException(400, "project_id required")
    _proj(project_id, org.id, db)
    log = DailyLog(
        org_id=org.id, project_id=project_id,
        log_date=body.get("log_date", datetime.utcnow().strftime("%Y-%m-%d")),
        weather=body.get("weather"), temperature=body.get("temperature"),
        crew_count=int(body.get("crew_count", 0)),
        work_summary=body.get("work_summary"), issues=body.get("issues"),
        delays=body.get("delays"), visitors=body.get("visitors"),
        created_by=current_user.id,
    )
    db.add(log); db.commit(); db.refresh(log)
    audit_log(db, org.id, current_user, "create_daily_log", "daily_log", log.id,
              detail=f"Daily log for {log.log_date}")
    return {"id": log.id, "log_date": log.log_date, "message": "Daily log saved"}


@router.put("/daily-logs/{log_id}")
def update_daily_log(
    log_id: int, body: dict,
    org_ctx: Tuple = Depends(_pm_write),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, _ = org_ctx
    log = db.query(DailyLog).filter(DailyLog.id == log_id, DailyLog.org_id == org.id).first()
    if not log: raise HTTPException(404, "Log not found")
    for k in ("weather","temperature","crew_count","work_summary","issues","delays","visitors"):
        if k in body: setattr(log, k, body[k])
    db.commit()
    return {"message": "Updated"}


@router.delete("/daily-logs/{log_id}")
def delete_daily_log(log_id: int, org_ctx: Tuple = Depends(_pm_write), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org, _ = org_ctx
    log = db.query(DailyLog).filter(DailyLog.id == log_id, DailyLog.org_id == org.id).first()
    if not log: raise HTTPException(404)
    db.delete(log); db.commit()
    return {"message": "Deleted"}


# ══════════════════════════════════════════════════════════════════════════════
#  RFIs
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/rfis")
def list_rfis(project_id: int = Query(...), status: Optional[str] = None,
              org_ctx: Tuple = Depends(_pm_read), db: Session = Depends(get_db)):
    org, _ = org_ctx
    q = db.query(RFI).filter(RFI.project_id == project_id, RFI.org_id == org.id)
    if status: q = q.filter(RFI.status == status)
    items = q.order_by(RFI.created_at.desc()).all()
    return [{"id": r.id, "rfi_number": r.rfi_number, "subject": r.subject,
             "description": r.description, "status": r.status, "priority": r.priority,
             "assigned_to": r.assignee.username if r.assignee else None,
             "due_date": r.due_date, "response": r.response,
             "responded_by": r.responder.username if r.responder else None,
             "responded_at": str(r.responded_at) if r.responded_at else None,
             "created_by": r.creator.username if r.creator else None,
             "created_at": str(r.created_at)} for r in items]


@router.post("/rfis")
def create_rfi(body: dict, org_ctx: Tuple = Depends(_pm_write), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org, _ = org_ctx
    pid = body.get("project_id"); _proj(pid, org.id, db)
    count = db.query(RFI).filter(RFI.project_id == pid).count()
    rfi = RFI(org_id=org.id, project_id=pid,
              rfi_number=body.get("rfi_number") or f"RFI-{count+1:03d}",
              subject=body.get("subject","").strip(), description=body.get("description"),
              priority=body.get("priority","medium"), due_date=body.get("due_date"),
              assigned_to=body.get("assigned_to"), created_by=current_user.id)
    db.add(rfi); db.commit(); db.refresh(rfi)
    audit_log(db, org.id, current_user, "create_rfi", "rfi", rfi.id, detail=f"RFI {rfi.rfi_number}: {rfi.subject}")
    return {"id": rfi.id, "rfi_number": rfi.rfi_number}


@router.put("/rfis/{rfi_id}")
def update_rfi(rfi_id: int, body: dict, org_ctx: Tuple = Depends(_pm_write), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org, _ = org_ctx
    rfi = db.query(RFI).filter(RFI.id == rfi_id, RFI.org_id == org.id).first()
    if not rfi: raise HTTPException(404)
    for k in ("subject","description","status","priority","due_date","assigned_to","response"):
        if k in body: setattr(rfi, k, body[k])
    if body.get("response") and not rfi.responded_at:
        rfi.responded_by = current_user.id
        rfi.responded_at = datetime.utcnow()
        if rfi.status == "open": rfi.status = "answered"
    db.commit()
    return {"message": "Updated"}


@router.delete("/rfis/{rfi_id}")
def delete_rfi(rfi_id: int, org_ctx: Tuple = Depends(_pm_write), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org, _ = org_ctx
    rfi = db.query(RFI).filter(RFI.id == rfi_id, RFI.org_id == org.id).first()
    if not rfi: raise HTTPException(404)
    db.delete(rfi); db.commit()
    return {"message": "Deleted"}


# ══════════════════════════════════════════════════════════════════════════════
#  PUNCH LIST
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/punch-list")
def list_punch_items(project_id: int = Query(...), status: Optional[str] = None,
                     org_ctx: Tuple = Depends(_pm_read), db: Session = Depends(get_db)):
    org, _ = org_ctx
    q = db.query(PunchItem).filter(PunchItem.project_id == project_id, PunchItem.org_id == org.id)
    if status: q = q.filter(PunchItem.status == status)
    items = q.order_by(PunchItem.priority.desc(), PunchItem.created_at).all()
    return [{"id": p.id, "item_number": p.item_number, "title": p.title,
             "description": p.description, "location": p.location,
             "status": p.status, "priority": p.priority,
             "assigned_to": p.assignee.username if p.assignee else None,
             "due_date": p.due_date, "resolved_at": str(p.resolved_at) if p.resolved_at else None,
             "photo_path": p.photo_path,
             "created_by": p.creator.username if p.creator else None,
             "created_at": str(p.created_at)} for p in items]


@router.post("/punch-list")
def create_punch_item(body: dict, org_ctx: Tuple = Depends(_pm_write), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org, _ = org_ctx
    pid = body.get("project_id"); _proj(pid, org.id, db)
    count = db.query(PunchItem).filter(PunchItem.project_id == pid).count()
    item = PunchItem(
        org_id=org.id, project_id=pid,
        item_number=body.get("item_number") or f"PI-{count+1:03d}",
        title=body.get("title","").strip(), description=body.get("description"),
        location=body.get("location"), priority=body.get("priority","medium"),
        assigned_to=body.get("assigned_to"), due_date=body.get("due_date"),
        created_by=current_user.id,
    )
    db.add(item); db.commit(); db.refresh(item)
    audit_log(db, org.id, current_user, "create_punch_item", "punch_item", item.id, detail=f"{item.item_number}: {item.title}")
    return {"id": item.id, "item_number": item.item_number}


@router.put("/punch-list/{item_id}")
def update_punch_item(item_id: int, body: dict, org_ctx: Tuple = Depends(_pm_write), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org, _ = org_ctx
    item = db.query(PunchItem).filter(PunchItem.id == item_id, PunchItem.org_id == org.id).first()
    if not item: raise HTTPException(404)
    for k in ("title","description","location","status","priority","assigned_to","due_date","photo_path"):
        if k in body: setattr(item, k, body[k])
    if body.get("status") == "resolved" and not item.resolved_at:
        item.resolved_at = datetime.utcnow()
    db.commit()
    return {"message": "Updated"}


@router.delete("/punch-list/{item_id}")
def delete_punch_item(item_id: int, org_ctx: Tuple = Depends(_pm_write), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org, _ = org_ctx
    item = db.query(PunchItem).filter(PunchItem.id == item_id, PunchItem.org_id == org.id).first()
    if not item: raise HTTPException(404)
    db.delete(item); db.commit()
    return {"message": "Deleted"}


# ══════════════════════════════════════════════════════════════════════════════
#  SUBMITTALS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/submittals")
def list_submittals(project_id: int = Query(...), status: Optional[str] = None,
                    org_ctx: Tuple = Depends(_pm_read), db: Session = Depends(get_db)):
    org, _ = org_ctx
    q = db.query(Submittal).filter(Submittal.project_id == project_id, Submittal.org_id == org.id)
    if status: q = q.filter(Submittal.status == status)
    items = q.order_by(Submittal.created_at.desc()).all()
    return [{"id": s.id, "submittal_number": s.submittal_number, "title": s.title,
             "spec_section": s.spec_section, "status": s.status,
             "submitted_by": s.submitter.username if s.submitter else None,
             "submitted_date": s.submitted_date,
             "reviewer": s.reviewer_.username if s.reviewer_ else None,
             "review_date": s.review_date, "review_notes": s.review_notes,
             "created_at": str(s.created_at)} for s in items]


@router.post("/submittals")
def create_submittal(body: dict, org_ctx: Tuple = Depends(_pm_write), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org, _ = org_ctx
    pid = body.get("project_id"); _proj(pid, org.id, db)
    count = db.query(Submittal).filter(Submittal.project_id == pid).count()
    sub = Submittal(
        org_id=org.id, project_id=pid,
        submittal_number=body.get("submittal_number") or f"SUB-{count+1:03d}",
        title=body.get("title","").strip(), description=body.get("description"),
        spec_section=body.get("spec_section"), status=body.get("status","draft"),
        submitted_by=body.get("submitted_by"), submitted_date=body.get("submitted_date"),
        reviewer=body.get("reviewer"), created_by=current_user.id,
    )
    db.add(sub); db.commit(); db.refresh(sub)
    audit_log(db, org.id, current_user, "create_submittal", "submittal", sub.id, detail=f"{sub.submittal_number}: {sub.title}")
    return {"id": sub.id, "submittal_number": sub.submittal_number}


@router.put("/submittals/{sub_id}")
def update_submittal(sub_id: int, body: dict, org_ctx: Tuple = Depends(_pm_write), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org, _ = org_ctx
    sub = db.query(Submittal).filter(Submittal.id == sub_id, Submittal.org_id == org.id).first()
    if not sub: raise HTTPException(404)
    for k in ("title","description","spec_section","status","submitted_by","submitted_date","reviewer","review_date","review_notes"):
        if k in body: setattr(sub, k, body[k])
    db.commit()
    return {"message": "Updated"}


@router.delete("/submittals/{sub_id}")
def delete_submittal(sub_id: int, org_ctx: Tuple = Depends(_pm_write), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org, _ = org_ctx
    sub = db.query(Submittal).filter(Submittal.id == sub_id, Submittal.org_id == org.id).first()
    if not sub: raise HTTPException(404)
    db.delete(sub); db.commit()
    return {"message": "Deleted"}


# ══════════════════════════════════════════════════════════════════════════════
#  MEETING MINUTES
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/meetings")
def list_meetings(project_id: int = Query(...), org_ctx: Tuple = Depends(_pm_read), db: Session = Depends(get_db)):
    org, _ = org_ctx
    items = db.query(MeetingMinutes).filter(MeetingMinutes.project_id == project_id, MeetingMinutes.org_id == org.id)\
              .order_by(MeetingMinutes.meeting_date.desc()).all()
    return [{"id": m.id, "meeting_date": m.meeting_date, "title": m.title,
             "location": m.location, "attendees": m.attendees, "agenda": m.agenda,
             "minutes": m.minutes, "action_items": m.action_items,
             "next_meeting": m.next_meeting,
             "created_by": m.creator.username if m.creator else None,
             "created_at": str(m.created_at)} for m in items]


@router.post("/meetings")
def create_meeting(body: dict, org_ctx: Tuple = Depends(_pm_write), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org, _ = org_ctx
    pid = body.get("project_id"); _proj(pid, org.id, db)
    m = MeetingMinutes(
        org_id=org.id, project_id=pid,
        meeting_date=body.get("meeting_date", datetime.utcnow().strftime("%Y-%m-%d")),
        title=body.get("title","Meeting").strip(), location=body.get("location"),
        attendees=body.get("attendees"), agenda=body.get("agenda"),
        minutes=body.get("minutes"), action_items=body.get("action_items"),
        next_meeting=body.get("next_meeting"), created_by=current_user.id,
    )
    db.add(m); db.commit(); db.refresh(m)
    audit_log(db, org.id, current_user, "create_meeting", "meeting", m.id, detail=f"Meeting: {m.title} on {m.meeting_date}")
    return {"id": m.id, "meeting_date": m.meeting_date}


@router.put("/meetings/{meeting_id}")
def update_meeting(meeting_id: int, body: dict, org_ctx: Tuple = Depends(_pm_write), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org, _ = org_ctx
    m = db.query(MeetingMinutes).filter(MeetingMinutes.id == meeting_id, MeetingMinutes.org_id == org.id).first()
    if not m: raise HTTPException(404)
    for k in ("title","location","meeting_date","attendees","agenda","minutes","action_items","next_meeting"):
        if k in body: setattr(m, k, body[k])
    db.commit()
    return {"message": "Updated"}


@router.delete("/meetings/{meeting_id}")
def delete_meeting(meeting_id: int, org_ctx: Tuple = Depends(_pm_write), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org, _ = org_ctx
    m = db.query(MeetingMinutes).filter(MeetingMinutes.id == meeting_id, MeetingMinutes.org_id == org.id).first()
    if not m: raise HTTPException(404)
    db.delete(m); db.commit()
    return {"message": "Deleted"}


# ══════════════════════════════════════════════════════════════════════════════
#  PHOTO LOGS
# ══════════════════════════════════════════════════════════════════════════════

UPLOAD_DIR = os.getenv("UPLOAD_FOLDER", "./uploads")
PHOTO_DIR  = os.path.join(UPLOAD_DIR, "photos")
os.makedirs(PHOTO_DIR, exist_ok=True)

@router.get("/photos")
def list_photos(
    project_id: int = Query(...),
    category: Optional[str] = None,
    org_ctx: Tuple = Depends(_pm_read),
    db: Session = Depends(get_db),
):
    org, _ = org_ctx
    q = db.query(PhotoLog).filter(PhotoLog.project_id == project_id, PhotoLog.org_id == org.id)
    if category: q = q.filter(PhotoLog.category == category)
    photos = q.order_by(PhotoLog.taken_date.desc(), PhotoLog.created_at.desc()).all()
    return [{"id": p.id, "caption": p.caption, "location": p.location,
             "category": p.category, "taken_date": p.taken_date,
             "original_filename": p.original_filename,
             "url": f"/api/pm/photos/{p.id}/file",
             "task_id": p.task_id, "punch_item_id": p.punch_item_id,
             "created_by": p.creator.username if p.creator else None,
             "created_at": str(p.created_at)} for p in photos]


@router.post("/photos")
async def upload_photo(
    project_id: int,
    file: UploadFile = File(...),
    caption: Optional[str] = None,
    location: Optional[str] = None,
    category: str = "general",
    taken_date: Optional[str] = None,
    task_id: Optional[int] = None,
    org_ctx: Tuple = Depends(_pm_write),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, _ = org_ctx
    _proj(project_id, org.id, db)

    ext = os.path.splitext(file.filename or "photo.jpg")[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".heic"}:
        raise HTTPException(400, "Unsupported image format")

    fname = f"{uuid.uuid4().hex}{ext}"
    fpath = os.path.join(PHOTO_DIR, fname)
    content = await file.read()
    with open(fpath, "wb") as f:
        f.write(content)

    photo = PhotoLog(
        org_id=org.id, project_id=project_id,
        file_path=fpath, original_filename=file.filename,
        caption=caption, location=location, category=category,
        taken_date=taken_date or datetime.utcnow().strftime("%Y-%m-%d"),
        task_id=task_id, created_by=current_user.id,
    )
    db.add(photo); db.commit(); db.refresh(photo)
    return {"id": photo.id, "url": f"/api/pm/photos/{photo.id}/file"}


@router.get("/photos/{photo_id}/file")
def get_photo_file(photo_id: int, org_ctx: Tuple = Depends(_pm_read), db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse
    org, _ = org_ctx
    photo = db.query(PhotoLog).filter(PhotoLog.id == photo_id, PhotoLog.org_id == org.id).first()
    if not photo or not os.path.isfile(photo.file_path):
        raise HTTPException(404, "Photo not found")
    return FileResponse(photo.file_path)


@router.delete("/photos/{photo_id}")
def delete_photo(photo_id: int, org_ctx: Tuple = Depends(_pm_write), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org, _ = org_ctx
    photo = db.query(PhotoLog).filter(PhotoLog.id == photo_id, PhotoLog.org_id == org.id).first()
    if not photo: raise HTTPException(404)
    if os.path.isfile(photo.file_path):
        try: os.remove(photo.file_path)
        except: pass
    db.delete(photo); db.commit()
    return {"message": "Deleted"}


# ══════════════════════════════════════════════════════════════════════════════
#  PM DASHBOARD SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/summary")
def pm_summary(
    project_id: int = Query(...),
    org_ctx: Tuple = Depends(_pm_read),
    db: Session = Depends(get_db),
):
    org, _ = org_ctx
    _proj(project_id, org.id, db)
    pid, oid = project_id, org.id

    def task_counts():
        rows = db.query(Task.status, db.func.count(Task.id))\
                 .filter(Task.project_id == pid, Task.org_id == oid)\
                 .group_by(Task.status).all()
        return {r[0]: r[1] for r in rows}

    tc = task_counts()
    total_tasks     = sum(tc.values())
    completed_tasks = tc.get("completed", 0)
    blocked_tasks   = tc.get("blocked", 0)
    overdue_tasks   = db.query(Task).filter(
        Task.project_id == pid, Task.org_id == oid,
        Task.due_date < datetime.utcnow().strftime("%Y-%m-%d"),
        Task.status.notin_(["completed", "cancelled"])
    ).count()

    return {
        "tasks": {
            "total": total_tasks, "completed": completed_tasks,
            "blocked": blocked_tasks, "overdue": overdue_tasks,
            "by_status": tc,
        },
        "open_rfis":   db.query(RFI).filter(RFI.project_id==pid, RFI.org_id==oid, RFI.status=="open").count(),
        "open_punch":  db.query(PunchItem).filter(PunchItem.project_id==pid, PunchItem.org_id==oid, PunchItem.status.in_(["open","in_progress"])).count(),
        "pending_submittals": db.query(Submittal).filter(Submittal.project_id==pid, Submittal.org_id==oid, Submittal.status.in_(["submitted","under_review"])).count(),
        "photos":      db.query(PhotoLog).filter(PhotoLog.project_id==pid, PhotoLog.org_id==oid).count(),
        "last_daily_log": db.query(DailyLog.log_date).filter(DailyLog.project_id==pid, DailyLog.org_id==oid).order_by(DailyLog.log_date.desc()).scalar(),
    }
