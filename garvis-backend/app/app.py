from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from app.api.health import router as health_router
from app.database.duckdb_data_service import DataService
from app.schemas.post_schemas import (
    PostCreate,
    PostResponse,
    UserRead,
    UserCreate,
    UserUpdate,
)
from app.database.sqlite_data_service import (
    Post,
    create_db_and_tables,
    get_async_session,
)
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import Select
import shutil
import os
import uuid
import tempfile
from app.users import auth_backend, current_active_user, fastapi_users
from app.database.sqlite_data_service import User
from app.api.speech_to_text import router as stt_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(title="Garvis Backend", version="0.1.0", lifespan=lifespan)
app.include_router(stt_router)

############################ From Kevin ##############################
# app.include_router(health_router, prefix="/api")
# ds = DataService()
# print("Total Patients", ds.count_patients())
#
# @app.get("/")
# def root():
#    return {"name": "garvis-backend", "status": "ok"}
######################################################################

# include all endpoints in the "fastapi_users.get_auth_router" router and prefix them with "/auth/jwt"
app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"]
)
app.include_router(
    fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"]
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)
