from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
class UserOut(BaseModel): id:str; name:str; email:EmailStr; role:str; avatar:str
class LoginIn(BaseModel): email:EmailStr; password:str
class TokenOut(BaseModel): access_token:str; token_type:str='bearer'; user:UserOut
class EventIn(BaseModel): title:str=Field(min_length=1,max_length=200); description:str=Field(min_length=1); location:str; start_time:datetime; end_time:datetime; capacity:int=Field(gt=0); category:str; banner_image:str
class EventOut(EventIn): id:str; organizer_id:str; registered_count:int; status:str; created_at:datetime
class TransitionIn(BaseModel): status:str
class RegistrationOut(BaseModel): id:str; event_id:str; attendee_id:str; registered_at:datetime; status:str
class TicketOut(BaseModel): id:str; registration_id:str; ticket_code:str; qr_value:str; status:str; issued_at:datetime
class RegisterOut(BaseModel): registration:RegistrationOut; ticket:TicketOut
class CheckinIn(BaseModel): ticket_code:str
class CheckinOut(BaseModel): id:str; ticket_id:str; event_id:str; attendee_id:str; checked_in_by:str; checked_in_at:datetime; status:str
class AssignmentIn(BaseModel): staff_id:str
