from datetime import datetime, timedelta, timezone
import hashlib, secrets, jwt
from pwdlib import PasswordHash
from .config import settings
pwd=PasswordHash.recommended()
def hash_password(value:str)->str:return pwd.hash(value)
def verify_password(value:str,hashed:str)->bool:return pwd.verify(value,hashed)
def access_token(user_id:str,role:str)->str:return jwt.encode({'sub':user_id,'role':role,'exp':datetime.now(timezone.utc)+timedelta(minutes=settings.access_minutes)},settings.jwt_secret,algorithm='HS256')
def decode_access(token:str)->dict:return jwt.decode(token,settings.jwt_secret,algorithms=['HS256'])
def new_refresh()->str:return secrets.token_urlsafe(48)
def digest(token:str)->str:return hashlib.sha256(token.encode()).hexdigest()
