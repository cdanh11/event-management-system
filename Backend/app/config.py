import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()
@dataclass(frozen=True)
class Settings:
    database_url:str=os.getenv('DATABASE_URL','postgresql+psycopg://evently:evently@localhost:5432/evently')
    jwt_secret:str=os.getenv('JWT_SECRET','development-only-change-me')
    access_minutes:int=int(os.getenv('ACCESS_TOKEN_MINUTES','15'))
    refresh_days:int=int(os.getenv('REFRESH_TOKEN_DAYS','7'))
    frontend_origin:str=os.getenv('FRONTEND_ORIGIN','http://localhost:5173')
settings=Settings()
