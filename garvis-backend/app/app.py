from fastapi import FastAPI, HTTPException
from app.api.health import router as health_router
from app.database.duckdb_data_service import DataService
from app.schemas.post_schemas import PostCreate, PostResponse
from app.database.sqlite_data_service import Post, create_db_and_tables, get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(title="Garvis Backend", version="0.1.0",lifespan=lifespan)
app.include_router(health_router, prefix="/api")

ds = DataService()
print("Total Patients", ds.count_patients())

######################################################################################
# PLAY GROUND


text_posts = {
  1: {
    "title": "Quiet Mornings and Focused Minds",
    "content": "Early mornings offer a rare mental clarity that is difficult to find later in the day. With fewer notifications, conversations, and distractions, the mind can focus deeply on complex problems. Many productive routines begin before sunrise because this time encourages reflection, planning, and deliberate action without the pressure of immediate external demands."
  },
  2: {
    "title": "Learning Through Failure",
    "content": "Failure is often misunderstood as a setback rather than a feedback mechanism. Each mistake reveals gaps in assumptions, process, or execution. When approached analytically, failure accelerates learning by forcing adjustments that success often hides. Over time, repeated small failures can build stronger intuition and resilience than uninterrupted success."
  },
  3: {
    "title": "Why Simplicity Scales",
    "content": "Systems that scale well are usually simple at their core. Simplicity reduces cognitive load, lowers maintenance costs, and minimizes unexpected interactions. Complex systems may appear powerful initially, but they often become brittle over time. Designing with simplicity encourages clearer reasoning, easier debugging, and smoother onboarding for new contributors."
  },
  4: {
    "title": "The Value of Deep Work",
    "content": "Deep work refers to uninterrupted periods of intense concentration on cognitively demanding tasks. This state allows individuals to produce higher-quality results in less time. Shallow multitasking fragments attention and degrades output. Cultivating deep work requires boundaries, intentional scheduling, and the discipline to resist constant digital interruptions."
  },
  5: {
    "title": "Technology as a Tool, Not a Crutch",
    "content": "Technology amplifies human capability, but it should not replace critical thinking. Overreliance on automated tools can weaken problem-solving skills and understanding. The most effective professionals treat technology as an assistant rather than an authority, verifying outputs and maintaining domain knowledge to make informed decisions when systems fail."
  },
  6: {
    "title": "Consistency Beats Intensity",
    "content": "Short bursts of effort feel productive, but consistent, moderate progress produces better long-term outcomes. Habits compound quietly, while intensity often leads to burnout. Whether learning a skill or building a product, showing up regularly creates momentum. Consistency also reduces friction, making progress feel natural rather than forced."
  },
  7: {
    "title": "Clear Communication Prevents Rework",
    "content": "Many project delays stem from unclear expectations rather than technical difficulty. Precise communication aligns assumptions early and reduces costly revisions. Writing things down, confirming understanding, and defining success criteria help teams move faster. Investing time in clarity upfront saves significantly more time during execution and review."
  },
  8: {
    "title": "Balancing Speed and Quality",
    "content": "Speed and quality are often framed as opposites, but they can reinforce each other. Fast feedback loops expose issues early, preventing large defects later. However, speed without standards leads to technical debt. The goal is controlled velocity: moving quickly while maintaining clear quality thresholds and accountability."
  },
  9: {
    "title": "The Power of Saying No",
    "content": "Saying no is an essential skill for protecting focus and priorities. Accepting too many commitments dilutes effort and reduces overall effectiveness. Thoughtful refusal allows resources to be directed toward meaningful work. Clear boundaries also set expectations, fostering respect and enabling better outcomes for the commitments you keep."
  },
  10: {
    "title": "Designing for Change",
    "content": "Change is inevitable in any long-lived system. Designing with flexibility reduces the cost of future modifications. Loose coupling, clear interfaces, and modular components allow parts to evolve independently. Systems that assume stability often break under new requirements, while adaptable designs absorb change with minimal disruption."
  }
}

@app.get("/hello-world")
def hello_word():
    return {"message": "Hello World from Team Bierbingka!"}

@app.get("/posts")
def get_all_posts(limit: int = None):
    if(limit):
        print(limit)
        limit = len(text_posts) if (limit > len(text_posts)) else limit
        return list(text_posts.values())[:3]
    return text_posts

@app.get("/posts/{id}")
def get_post(id:int)->PostCreate:
    if(id not in text_posts):
        raise HTTPException(status_code=404, detail="Id doesnt exist")

    return text_posts.get(id)

@app.post("/posts")
def create_post(post: PostCreate)->PostResponse:
    new_post = {"title": post.title, "content":post.content}
    text_posts[max(text_posts.keys()) + 1] = new_post
    return post

#######################################################################################



@app.get("/")
def root():
    return {"name": "garvis-backend", "status": "ok"}