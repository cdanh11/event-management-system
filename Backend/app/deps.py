from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .db import get_db
from .models import User
from .security import decode_access
bearer=HTTPBearer(auto_error=False)
def current_user(credentials:HTTPAuthorizationCredentials|None=Depends(bearer),db:Session=Depends(get_db))->User:
    if not credentials: raise HTTPException(401,detail={'code':'UNAUTHORIZED','message':'Authentication required'})
    try: claims=decode_access(credentials.credentials); user=db.get(User,claims['sub'])
    except Exception: user=None
    if not user: raise HTTPException(401,detail={'code':'UNAUTHORIZED','message':'Invalid or expired token'})
    return user
def require(*roles:str):
    def check(user:User=Depends(current_user))->User:
        if user.role not in roles: raise HTTPException(403,detail={'code':'FORBIDDEN','message':'Insufficient permission'})
        return user
    return check
