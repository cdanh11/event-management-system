from datetime import datetime, timedelta
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import settings
from .db import get_db
from .deps import current_user, require
from .models import Checkin, Event, RefreshToken, Registration, StaffEventAssignment, Ticket, User
from .schemas import AssignmentIn, CheckinIn, CheckinOut, EventIn, EventOut, LoginIn, RegisterOut, RegistrationOut, TicketOut, TokenOut, TransitionIn, UserOut
from .security import access_token, digest, new_refresh, verify_password
router=APIRouter()
def api_error(status:int,code:str,message:str): raise HTTPException(status,detail={'code':code,'message':message})
def user_out(u:User)->dict:return {'id':u.id,'name':u.name,'email':u.email,'role':u.role,'avatar':u.avatar_url}
def event_out(e:Event)->dict:return {'id':e.id,'organizer_id':e.organizer_id,'title':e.title,'description':e.description,'location':e.location,'start_time':e.start_time,'end_time':e.end_time,'capacity':e.capacity,'registered_count':e.registered_count,'status':e.status,'category':e.category,'banner_image':e.banner_url,'created_at':e.created_at}
def reg_out(r:Registration)->dict:return {'id':r.id,'event_id':r.event_id,'attendee_id':r.attendee_id,'registered_at':r.registered_at,'status':r.status}
def ticket_out(t:Ticket)->dict:return {'id':t.id,'registration_id':t.registration_id,'ticket_code':t.ticket_code,'qr_value':t.qr_value,'status':t.status,'issued_at':t.issued_at}
def checkin_out(c:Checkin)->dict:return {'id':c.id,'ticket_id':c.ticket_id,'event_id':c.event_id,'attendee_id':c.attendee_id,'checked_in_by':c.checked_in_by,'checked_in_at':c.checked_in_at,'status':c.status}
def issue_refresh(response:Response,db:Session,user:User):
    raw=new_refresh(); db.add(RefreshToken(user_id=user.id,token_hash=digest(raw),expires_at=datetime.utcnow()+timedelta(days=settings.refresh_days))); db.flush(); response.set_cookie('evently_refresh',raw,httponly=True,secure=False,samesite='lax',max_age=settings.refresh_days*86400)
@router.post('/auth/login',response_model=TokenOut,tags=['auth'])
def login(payload:LoginIn,response:Response,db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.email==payload.email.lower()))
    if not user or not verify_password(payload.password,user.password_hash): api_error(401,'INVALID_CREDENTIALS','Email or password is incorrect')
    issue_refresh(response,db,user); db.commit(); return {'access_token':access_token(user.id,user.role),'user':user_out(user)}
@router.post('/auth/refresh',response_model=TokenOut,tags=['auth'])
def refresh(response:Response,evently_refresh:str|None=Cookie(None),db:Session=Depends(get_db)):
    if not evently_refresh: api_error(401,'UNAUTHORIZED','Refresh token missing')
    row=db.scalar(select(RefreshToken).where(RefreshToken.token_hash==digest(evently_refresh)))
    if not row or row.revoked_at or row.expires_at<datetime.utcnow(): api_error(401,'UNAUTHORIZED','Refresh token expired')
    user=db.get(User,row.user_id); row.revoked_at=datetime.utcnow(); issue_refresh(response,db,user); db.commit(); return {'access_token':access_token(user.id,user.role),'user':user_out(user)}
@router.post('/auth/logout',status_code=204,tags=['auth'])
def logout(response:Response,evently_refresh:str|None=Cookie(None),db:Session=Depends(get_db)):
    if evently_refresh:
        row=db.scalar(select(RefreshToken).where(RefreshToken.token_hash==digest(evently_refresh)))
        if row: row.revoked_at=datetime.utcnow(); db.commit()
    response.delete_cookie('evently_refresh')
@router.get('/auth/me',response_model=UserOut,tags=['auth'])
def me(user:User=Depends(current_user)): return user_out(user)
@router.get('/events',response_model=list[EventOut],tags=['events'])
def list_events(status:str|None=None,q:str|None=None,db:Session=Depends(get_db)):
    stmt=select(Event)
    if status: stmt=stmt.where(Event.status==status)
    if q: stmt=stmt.where(Event.title.ilike(f'%{q}%'))
    return [event_out(e) for e in db.scalars(stmt.order_by(Event.start_time)).all()]
@router.get('/events/{event_id}',response_model=EventOut,tags=['events'])
def get_event(event_id:str,db:Session=Depends(get_db)):
    e=db.get(Event,event_id)
    if not e: api_error(404,'EVENT_NOT_FOUND','Event not found')
    return event_out(e)
@router.post('/events',response_model=EventOut,status_code=201,tags=['events'])
def create_event(payload:EventIn,user:User=Depends(require('ORGANIZER')),db:Session=Depends(get_db)):
    if payload.start_time>=payload.end_time or payload.start_time<=datetime.now(payload.start_time.tzinfo): api_error(400,'INVALID_EVENT_TIME','Start time must be future and before end time')
    values=payload.model_dump(); values['banner_url']=values.pop('banner_image'); e=Event(organizer_id=user.id,**values); db.add(e); db.commit(); db.refresh(e); return event_out(e)
@router.post('/events/{event_id}/transition',response_model=EventOut,tags=['events'])
def transition(event_id:str,payload:TransitionIn,user:User=Depends(require('ORGANIZER')),db:Session=Depends(get_db)):
    e=db.get(Event,event_id)
    if not e: api_error(404,'EVENT_NOT_FOUND','Event not found')
    if e.organizer_id!=user.id: api_error(403,'FORBIDDEN','You do not own this event')
    valid={'DRAFT':{'PUBLISHED','CANCELLED'},'PUBLISHED':{'ONGOING','CANCELLED'},'ONGOING':{'COMPLETED'},'COMPLETED':set(),'CANCELLED':set()}
    if payload.status not in valid.get(e.status,set()): api_error(400,'INVALID_TRANSITION','This event transition is not allowed')
    e.status=payload.status; db.commit(); db.refresh(e); return event_out(e)
@router.post('/events/{event_id}/register',response_model=RegisterOut,status_code=201,tags=['registrations'])
def register(event_id:str,user:User=Depends(require('ATTENDEE')),db:Session=Depends(get_db)):
    try:
        # current_user already starts SQLAlchemy's implicit transaction. Keep all
        # writes in that transaction instead of opening a second one.
        e=db.scalar(select(Event).where(Event.id==event_id).with_for_update())
        if not e: api_error(404,'EVENT_NOT_FOUND','Event not found')
        if e.status!='PUBLISHED': api_error(400,'REGISTRATION_CLOSED','Registration is unavailable')
        existing=db.scalar(select(Registration).where(Registration.event_id==event_id,Registration.attendee_id==user.id))
        if existing: api_error(409,'ALREADY_REGISTERED','Already registered')
        if e.registered_count>=e.capacity: api_error(409,'EVENT_FULL','Event is full')
        r=Registration(event_id=e.id,attendee_id=user.id); db.add(r); db.flush(); code=f'EV-{r.id.replace("-","")[:8].upper()}'; t=Ticket(registration_id=r.id,ticket_code=code,qr_value=code); db.add(t); e.registered_count+=1; db.flush(); result={'registration':reg_out(r),'ticket':ticket_out(t)}
        db.commit()
        return result
    except IntegrityError: db.rollback(); api_error(409,'ALREADY_REGISTERED','Already registered')
@router.get('/registrations/me',response_model=list[RegistrationOut],tags=['registrations'])
def my_registrations(user:User=Depends(require('ATTENDEE')),db:Session=Depends(get_db)): return [reg_out(r) for r in db.scalars(select(Registration).where(Registration.attendee_id==user.id).order_by(Registration.registered_at.desc())).all()]
@router.get('/registrations/{registration_id}',response_model=RegistrationOut,tags=['registrations'])
def get_registration(registration_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=db.get(Registration,registration_id)
    if not r: api_error(404,'REGISTRATION_NOT_FOUND','Registration not found')
    if user.role=='ATTENDEE' and r.attendee_id!=user.id: api_error(403,'FORBIDDEN','Not your registration')
    return reg_out(r)
@router.post('/registrations/{registration_id}/cancel',response_model=RegistrationOut,tags=['registrations'])
def cancel_registration(registration_id:str,user:User=Depends(require('ATTENDEE')),db:Session=Depends(get_db)):
    r=db.scalar(select(Registration).where(Registration.id==registration_id).with_for_update())
    if not r: api_error(404,'REGISTRATION_NOT_FOUND','Registration not found')
    if r.attendee_id!=user.id: api_error(403,'FORBIDDEN','Not your registration')
    if r.status=='CANCELLED': return reg_out(r)
    r.status='CANCELLED'; t=db.scalar(select(Ticket).where(Ticket.registration_id==r.id));
    if t: t.status='CANCELLED'
    e=db.scalar(select(Event).where(Event.id==r.event_id).with_for_update()); e.registered_count=max(0,e.registered_count-1)
    db.commit(); return reg_out(r)
@router.get('/tickets/{ticket_id}',response_model=TicketOut,tags=['tickets'])
def get_ticket(ticket_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    t=db.get(Ticket,ticket_id)
    if not t: api_error(404,'TICKET_NOT_FOUND','Ticket not found')
    r=db.get(Registration,t.registration_id)
    if user.role=='ATTENDEE' and r.attendee_id!=user.id: api_error(403,'FORBIDDEN','Not your ticket')
    return ticket_out(t)
@router.get('/registrations/{registration_id}/ticket',response_model=TicketOut,tags=['tickets'])
def ticket_for_registration(registration_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=db.get(Registration,registration_id)
    if not r: api_error(404,'REGISTRATION_NOT_FOUND','Registration not found')
    if user.role=='ATTENDEE' and r.attendee_id!=user.id: api_error(403,'FORBIDDEN','Not your registration')
    t=db.scalar(select(Ticket).where(Ticket.registration_id==registration_id)); return ticket_out(t)
@router.post('/checkins',response_model=CheckinOut,status_code=201,tags=['checkins'])
def checkin(payload:CheckinIn,user:User=Depends(require('STAFF')),db:Session=Depends(get_db)):
    t=db.scalar(select(Ticket).where(Ticket.ticket_code==payload.ticket_code.strip().upper()).with_for_update())
    if not t: api_error(404,'INVALID_TICKET','Invalid ticket')
    if t.status=='CANCELLED': api_error(400,'TICKET_CANCELLED','Ticket cancelled')
    if t.status=='USED': api_error(409,'TICKET_ALREADY_USED','Ticket already checked in')
    r=db.get(Registration,t.registration_id); e=db.get(Event,r.event_id)
    if e.status!='ONGOING': api_error(400,'CHECKIN_CLOSED','Check-in is only available for ongoing events')
    assigned=db.scalar(select(StaffEventAssignment).where(StaffEventAssignment.staff_id==user.id,StaffEventAssignment.event_id==e.id))
    if not assigned: api_error(403,'FORBIDDEN','You are not assigned to this event')
    c=Checkin(ticket_id=t.id,event_id=e.id,attendee_id=r.attendee_id,checked_in_by=user.id); t.status='USED'; db.add(c); db.commit(); db.refresh(c); return checkin_out(c)
@router.get('/staff/events',response_model=list[EventOut],tags=['staff'])
def staff_events(user:User=Depends(require('STAFF')),db:Session=Depends(get_db)):
    return [event_out(e) for e in db.scalars(select(Event).join(StaffEventAssignment,StaffEventAssignment.event_id==Event.id).where(StaffEventAssignment.staff_id==user.id)).all()]
@router.get('/organizer/dashboard',tags=['organizer'])
def organizer_dashboard(user:User=Depends(require('ORGANIZER')),db:Session=Depends(get_db)):
    events=db.scalars(select(Event).where(Event.organizer_id==user.id).order_by(Event.start_time)).all(); ids=[e.id for e in events]
    registrations=[] if not ids else db.scalars(select(Registration).where(Registration.event_id.in_(ids))).all()
    checkins=[] if not ids else db.scalars(select(Checkin).where(Checkin.event_id.in_(ids))).all()
    return {'events':[event_out(e) for e in events],'total_registrations':len([r for r in registrations if r.status=='REGISTERED']),'total_checkins':len(checkins)}
@router.post('/events/{event_id}/staff',status_code=201,tags=['assignments'])
def assign_staff(event_id:str,payload:AssignmentIn,user:User=Depends(require('ORGANIZER')),db:Session=Depends(get_db)):
    e=db.get(Event,event_id); staff=db.get(User,payload.staff_id)
    if not e: api_error(404,'EVENT_NOT_FOUND','Event not found')
    if e.organizer_id!=user.id: api_error(403,'FORBIDDEN','You do not own this event')
    if not staff or staff.role!='STAFF': api_error(400,'INVALID_STAFF','User must be staff')
    db.add(StaffEventAssignment(event_id=e.id,staff_id=staff.id))
    try: db.commit()
    except IntegrityError: db.rollback(); api_error(409,'ALREADY_ASSIGNED','Staff is already assigned')
    return {'event_id':e.id,'staff_id':staff.id}
