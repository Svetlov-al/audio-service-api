from fastapi import FastAPI
from .routers import audio, users
from .database import engine
from .import models

models.Base.metadata.create_all(bind=engine)  # Создание таблиц в базе данных


# Инициализация приложения FastAPI
app = FastAPI(
    title="Wav2MP3"
)

app.include_router(users.router)
app.include_router(audio.router)


@app.get("/")
async def root():
    return {"message": "Welcome to SonicConverter! Breathe new life into your sound files by effortlessly transforming them from WAV to MP3. Let's make the magic happen!"}
