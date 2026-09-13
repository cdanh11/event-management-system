from datetime import datetime, timedelta
from .db import Base, SessionLocal, engine
from .models import Event, Registration, StaffEventAssignment, Ticket, User
from .security import hash_password
def run():
    Base.metadata.create_all(engine); db=SessionLocal()
    if db.query(User).first(): print('Database already seeded'); return
    users=[User(name='Minh Nguyen',email='attendee@demo.com',role='ATTENDEE',avatar_url='MN',password_hash=hash_password('123456')),User(name='Linh Tran',email='linh@demo.com',role='ATTENDEE',avatar_url='LT',password_hash=hash_password('123456')),User(name='Huy Pham',email='huy@demo.com',role='ATTENDEE',avatar_url='HP',password_hash=hash_password('123456')),User(name='An Le',email='staff@demo.com',role='STAFF',avatar_url='AL',password_hash=hash_password('123456')),User(name='Khanh Do',email='khanh.staff@demo.com',role='STAFF',avatar_url='KD',password_hash=hash_password('123456')),User(name='Evently Team',email='organizer@demo.com',role='ORGANIZER',avatar_url='ET',password_hash=hash_password('123456'))]
    db.add_all(users); db.flush(); organizer=users[-1]; now=datetime.now()
    specs=[('Vietnam Tech Conference 2026','PUBLISHED',now+timedelta(days=30),300,184),('Design Systems Workshop','PUBLISHED',now+timedelta(days=15),50,47),('Career Fair: Future Makers','PUBLISHED',now+timedelta(days=22),150,150),('AI Product Meetup','ONGOING',now-timedelta(hours=1),80,63),('Startup Pitch Night','COMPLETED',now-timedelta(days=20),100,89),('Community Design Day','CANCELLED',now+timedelta(days=45),60,12)]
    events=[]
    for title,status,start,capacity,count in specs:
        events.append(Event(organizer_id=organizer.id,title=title,description=f'{title} for the Evently community.',location='Ho Chi Minh City',start_time=start,end_time=start+timedelta(hours=6),capacity=capacity,registered_count=count,status=status,category='Technology',banner_url='https://images.unsplash.com/photo-1505373877841-8d25f7d46678?auto=format&fit=crop&w=1200&q=80'))
    db.add_all(events); db.flush(); db.add_all([StaffEventAssignment(staff_id=users[3].id,event_id=events[3].id),StaffEventAssignment(staff_id=users[4].id,event_id=events[0].id)])
    r=Registration(event_id=events[3].id,attendee_id=users[0].id); db.add(r); db.flush(); db.add(Ticket(registration_id=r.id,ticket_code='AI-MEET-2026',qr_value='AI-MEET-2026')); db.commit(); print('Seeded Evently demo accounts and events')
if __name__=='__main__': run()
