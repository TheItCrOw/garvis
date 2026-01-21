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
from app.media.images import imagekit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
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


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    caption: str = Form(""),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    temp_file_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=os.path.splitext(file.filename)[1]
        ) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        upload_result = imagekit.upload_file(
            file=open(temp_file_path, "rb"),
            file_name=file.filename,
            options=UploadFileRequestOptions(
                use_unique_file_name=True, tags=["backend-upload"]
            ),
        )

        if upload_result.response_metadata.http_status_code == 200:

            post = Post(
                user_id=user.id,
                caption=caption,
                url=upload_result.url,
                file_type=(
                    "video" if file.content_type.startswith("video/") else "image"
                ),
                file_name=upload_result.name,
            )

            session.add(post)

            await session.commit()
            await session.refresh(post)
            return post
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        file.file.close()


@app.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    try:
        post_uuid = uuid.UUID(post_id)
        result = await session.execute(Select(Post).where(Post.id == post_uuid))
        post = result.scalars().first()

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        if post.user_id != user.id:
            raise HTTPException(
                status_code=403, detail="You dont have permission to delete this post"
            )

        await session.delete(post)
        await session.commit()

        return {"success": True, "message": "Post deleted successful"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/feed")
async def get_feed(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    result = await session.execute(Select(Post).order_by(Post.created_at.desc()))
    posts = [row[0] for row in result.all()]

    result = await session.execute(Select(User))
    users = [row[0] for row in result.all()]
    user_dict = {u.id: u.email for u in users}

    posts_data = []

    for post in posts:
        posts_data.append(
            {
                "id": str(post.id),
                "user_id": str(post.user_id),
                "caption": post.caption,
                "url": post.url,
                "file_type": post.file_type,
                "file_name": post.file_name,
                "created_at": post.created_at.isoformat(),
                "is_owner": post.user_id == user.id,
                "email": user_dict.get(post.user_id, "Unknown User"),
            }
        )

    return {"posts": posts_data}
