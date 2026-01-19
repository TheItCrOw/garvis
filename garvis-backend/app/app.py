from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from app.api.health import router as health_router
from app.database.duckdb_data_service import DataService
from app.schemas.post_schemas import PostCreate, PostResponse
from app.database.sqlite_data_service import Post, create_db_and_tables, get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import Select
from app.media.images import imagekit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
import shutil
import os
import uuid
import tempfile

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(title="Garvis Backend", version="0.1.0",lifespan=lifespan)

############################ From Kevin ##############################
#app.include_router(health_router, prefix="/api")
#ds = DataService()
#print("Total Patients", ds.count_patients())
#
#@app.get("/")
#def root():
#    return {"name": "garvis-backend", "status": "ok"}
######################################################################

@app.post("/upload")
async def upload_file(
    file: UploadFile=File(...)
    , caption:str=Form("")
    , session:AsyncSession = Depends(get_async_session)
):
    temp_file_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix = os.path.splitext(file.filename)[1]) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        upload_result = imagekit.upload_file(
            file=open(temp_file_path,"rb")
            , file_name=file.filename
            , options=UploadFileRequestOptions(
                use_unique_file_name=True
                , tags=["backend-upload"]
            )
        )
    
        if(upload_result.response_metadata.http_status_code==200):

            post = Post(
                caption=caption
                , url=upload_result.url
                , file_type = "video" if file.content_type.startswith("video/") else "iamge"
                , file_name = upload_result.name
            )


            session.add(post)

            await session.commit()
            await session.refresh(post)
            return post
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if(temp_file_path and os.path.exists(temp_file_path)):
            os.unlink(temp_file_path)
        file.file.close()


@app.delete("/posts/{post_id}")
async def delete_post(post_id:str, session: AsyncSession = Depends(get_async_session)):
    try:
        post_uuid = uuid.UUID(post_id)
        result = await session.execute(Select(Post).where(Post.id == post_uuid))
        post = result.scalars().first()

        if(not post):
            raise HTTPException(status_code=404, detail="Post not found")
        
        await session.delete(post)
        await session.commit()

        return {"success":True,"message": "Post deleted successful"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/feed")
async def get_feed(session:AsyncSession = Depends(get_async_session)):
    result = await session.execute(Select(Post).order_by(Post.created_at.desc()))
    posts = [row[0] for row in result.all()]

    posts_data = []

    for post in posts:
        posts_data.append(
            {
                "id": str(post.id)
                , "caption": post.caption
                , "url": post.url
                , "file_type": post.file_type
                , "file_name": post.file_name
                , "create_at": post.created_at.isoformat()
            }
        )

    return {"posts": posts_data}