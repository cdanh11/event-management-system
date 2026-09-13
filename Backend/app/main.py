from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .config import settings
from .routers import router
app=FastAPI(title='Evently API',version='1.0.0',openapi_tags=[{'name':'auth'},{'name':'events'},{'name':'registrations'},{'name':'tickets'},{'name':'checkins'},{'name':'staff'},{'name':'assignments'}])
# Vite may select another local port when 5173 is occupied. Keep this flexible
# for development while production should provide a fixed public origin.
app.add_middleware(CORSMiddleware,allow_origins=[settings.frontend_origin],allow_origin_regex=r'^https?://(localhost|127\.0\.0\.1):\d+$',allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
@app.exception_handler(HTTPException)
async def errors(_:Request,exc:HTTPException):
    detail=exc.detail if isinstance(exc.detail,dict) else {'code':'HTTP_ERROR','message':str(exc.detail)}
    return JSONResponse(status_code=exc.status_code,content={'status':exc.status_code,**detail})
app.include_router(router)
@app.get('/health',tags=['system'])
def health(): return {'status':'ok'}
