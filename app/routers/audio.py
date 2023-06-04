from fastapi import APIRouter, HTTPException, Depends, status, Form, UploadFile, File
from fastapi.responses import FileResponse  # Импорт класса FileResponse из модуля fastapi.responses для возможности возвращения файлов в ответах API
from sqlalchemy.orm import Session
from pydub import AudioSegment  # Для преобразования аудиофайлов
from ..database import get_db
from uuid import uuid4  # Импортируем модуль uuid для генерации UUID
from .. import models
import os


router = APIRouter(
    prefix='/audio',
    tags=['Audio']
)


@router.post("/", status_code=status.HTTP_201_CREATED)  # Создание маршрута для загрузки аудио файла
async def upload_audio(user_id: int = Form(...),  # Получаем идентификатор пользователя из формы
                       token: str = Form(...),  # Получаем токен пользователя из формы
                       file: UploadFile = File(...),  # Получаем файл для загрузки из формы
                       db: Session = Depends(get_db)):  # Используем зависимость для получения сессии базы данных
    # Запрашиваем пользователя из базы данных по id и токену
    user = db.query(models.User).filter(models.User.id == user_id, models.User.uuid_token == token).first()
    # Если пользователь не найден, выдаем исключение
    if not user:
        raise HTTPException(status_code=400, detail="Invalid user ID or token")
    # Пытаемся прочитать данные из файла
    try:
        audio_data = await file.read()
    # В случае ошибки, возвращаем исключение с описанием ошибки
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(ex)}")
    # Генерируем уникальное имя для файла аудиозаписи
    audio_name = f"{str(uuid4())}.wav"
    # Формируем путь к файлу
    audio_path = os.path.join("audio_files", audio_name)
    # Создаем папку для файла, если она не существует
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
    # Пытаемся записать данные в файл
    try:
        with open(audio_path, "wb") as audio_file:
            audio_file.write(audio_data)
    # В случае ошибки, возвращаем исключение с описанием ошибки
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Error writing file: {str(ex)}")
    # Пытаемся преобразовать аудиофайл в mp3 формат
    try:
        audio = AudioSegment.from_wav(audio_path)
        audio.export(audio_path.replace(".wav", ".mp3"), format="mp3")
    # В случае ошибки, возвращаем исключение с описанием ошибки
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Error converting file to mp3: {str(ex)}")

    # os.remove(audio_path)  # Раскомментировать если необходимо удалять исходный файл

    new_audio_record = models.AudioRecord(
        user_id=user_id,
        audio_file=audio_path.replace(".wav", ".mp3")
    )
    # Добавляем запись в базу данных
    db.add(new_audio_record)
    db.commit()
    db.refresh(new_audio_record)
    # Возвращает ссылку где uuid = уникальный id трека, и user = user_id
    return {"download_url": f"http://localhost:8000/audio?uuid={new_audio_record.audio_uuid}&user={user_id}"}


@router.get("/")  # Создание маршрута для скачивания аудио файла по уникальному ID
async def download_record(uuid: str,  # Получаем идентификатор аудиозаписи из параметра запроса
                          user: int,  # Получаем идентификатор пользователя из параметра запроса
                          db: Session = Depends(get_db)):  # Используем зависимость для получения сессии базы данных
    # Проверка наличия пользователя
    db_user = db.query(models.User).filter(models.User.id == user).first()
    # Если пользователя не существует, возвращаем исключение
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Проверка наличия аудиозаписи
    db_audio_record = db.query(models.AudioRecord).filter(models.AudioRecord.audio_uuid == uuid).first()
    # Если аудиозапись не найдена или не принадлежит пользователю, возвращаем исключение
    if db_audio_record is None or db_audio_record.user_id != user:
        raise HTTPException(status_code=404, detail="Audio record not found")
    # Получаем путь к файлу аудиозаписи из базы данных
    audio_path = db_audio_record.audio_file
    # Возвращаем файловый ответ с аудиозаписью
    return FileResponse(audio_path, media_type="audio/mpeg", filename=f"{id}.mp3")


# Создание маршрута для удаления аудиозаписи
@router.delete("/{audio_uuid}")
def delete_audio(audio_uuid: str,
                 db: Session = Depends(get_db)):  # Функция принимает идентификатор аудиозаписи и сессию базы данных
    audio = db.query(models.AudioRecord).filter(
        models.AudioRecord.audio_uuid == audio_uuid).first()  # Получение аудиозаписи из базы данных по его идентификатору
    if not audio:
        raise HTTPException(status_code=404,
                            detail="Audio not found")  # Если аудиозапись не найдена, возвращаем ошибку 404

    db.delete(audio)  # Удаление аудиозаписи из сессии
    db.commit()  # Сохранение изменений
    return {"message": "Audio deleted successfully"}  # Возвращение сообщения об успешном удалении аудиозаписи
