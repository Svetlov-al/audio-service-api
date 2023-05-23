from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, status  # Импорт основных классов FastAPI
from fastapi.responses import FileResponse  # Импорт класса FileResponse из модуля fastapi.responses для возможности возвращения файлов в ответах API
from sqlalchemy.orm import Session  # Импорт сессии для работы с базой данных
from sqlalchemy.exc import IntegrityError, NoResultFound  # Импорт класса ошибок для работы с базой данных
from sqlalchemy import create_engine  # Для создания движка базы данных
from models import User, Base, AudioRecord  # Импорт модели пользователя и базового класса
from sqlalchemy.orm import sessionmaker  # Для создания сессии взаимодействия с базой данных
from uuid import uuid4  # Импорт функции генерации UUID
from pydub import AudioSegment  # Для преобразования аудиофайлов
from pydantic import BaseModel
import os

# Создаем подключение к базе данных
DATABASE_URL = "postgresql://root:root@audio_container:5432/postgres"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)  # Создание таблиц в базе данных

app = FastAPI()  # Инициализация приложения FastAPI


# Описываем модель запроса
class CreateUserRequest(BaseModel):
    name: str


# Зависимость для получения сессии базы данных
def get_db():
    db = SessionLocal()  # Создание новой сессии
    try:
        yield db  # Возврат сессии
    finally:
        db.close()  # Закрытие сессии


@app.post("/create_user", status_code=status.HTTP_201_CREATED)  # Создание маршрута для создания пользователя
def create_user(user_data: CreateUserRequest, db: Session = Depends(get_db)):  # Функция принимает имя пользователя и сессию базы данных
    uuid_token = str(uuid4())  # Генерация UUID токена
    new_user = User(  # Создание нового пользователя
        name=user_data.name,
        uuid_token=uuid_token
    )
    try:
        db.add(new_user)  # Добавление пользователя в сессию
        db.commit()  # Сохранение изменений
        db.refresh(new_user)  # Обновление данных пользователя
    except IntegrityError:  # Перехват ошибки при дублировании имени пользователя
        raise HTTPException(status_code=400, detail="Username already exists")  # Возврат ошибку клиенту
    return {"user_id": new_user.id, "uuid_token": new_user.uuid_token}  # Возвращение данных пользователя клиенту


@app.post("/upload_audio", status_code=status.HTTP_201_CREATED)  # Создание маршрута для загрузки аудио файла
async def upload_audio(user_id: int = Form(...),  # Получаем идентификатор пользователя из формы
                       token: str = Form(...),  # Получаем токен пользователя из формы
                       file: UploadFile = File(...),  # Получаем файл для загрузки из формы
                       db: Session = Depends(get_db)):  # Используем зависимость для получения сессии базы данных
    # Запрашиваем пользователя из базы данных по id и токену
    user = db.query(User).filter(User.id == user_id, User.uuid_token == token).first()
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

    new_audio_record = AudioRecord(
        user_id=user_id,
        audio_file=audio_path.replace(".wav", ".mp3")
    )
    # Добавляем запись в базу данных
    db.add(new_audio_record)
    db.commit()
    db.refresh(new_audio_record)
    # Возвращает ссылку где id = уникальный id трека, и user = user_id
    return {"download_url": f"http://localhost:8000/record?id={new_audio_record.audio_uuid}&user={user_id}"}


@app.get("/record")  # Создание маршрута для скачивания аудио файла по уникальному ID
async def download_record(uuid: str,  # Получаем идентификатор аудиозаписи из параметра запроса
                          user: int,  # Получаем идентификатор пользователя из параметра запроса
                          db: Session = Depends(get_db)):  # Используем зависимость для получения сессии базы данных
    # Проверка наличия пользователя
    db_user = db.query(User).filter(User.id == user).first()
    # Если пользователя не существует, возвращаем исключение
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Проверка наличия аудиозаписи
    db_audio_record = db.query(AudioRecord).filter(AudioRecord.audio_uuid == uuid).first()
    # Если аудиозапись не найдена или не принадлежит пользователю, возвращаем исключение
    if db_audio_record is None or db_audio_record.user_id != user:
        raise HTTPException(status_code=404, detail="Audio record not found")
    # Получаем путь к файлу аудиозаписи из базы данных
    audio_path = db_audio_record.audio_file
    # Возвращаем файловый ответ с аудиозаписью
    return FileResponse(audio_path, media_type="audio/mpeg", filename=f"{id}.mp3")


# Создание маршрута для удаления пользователя
@app.delete("/delete_user/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):  # Функция принимает идентификатор пользователя и сессию базы данных
    try:
        user = db.query(User).filter(User.id == user_id).one()  # Получение пользователя из базы данных по его идентификатору
    except NoResultFound:
        raise HTTPException(status_code=404, detail="User not found")  # Если пользователь не найден, возвращаем ошибку 404

    # Удаление связанных записей из таблицы "audiorecords"
    db.query(AudioRecord).filter(AudioRecord.user_id == user.id).delete()

    db.delete(user)  # Удаление пользователя из сессии
    db.commit()  # Сохранение изменений
    return {"message": "User deleted successfully"}


# Создание маршрута для удаления аудиозаписи
@app.delete("/delete_audio/{audio_uuid}")
def delete_audio(audio_uuid: str, db: Session = Depends(get_db)):  # Функция принимает идентификатор аудиозаписи и сессию базы данных
    audio = db.query(AudioRecord).filter(AudioRecord.audio_uuid == audio_uuid).one()  # Получение аудиозаписи из базы данных по его идентификатору
    if not audio:
        raise HTTPException(status_code=404, detail="Audio not found")  # Если аудиозапись не найдена, возвращаем ошибку 404

    db.delete(audio)  # Удаление аудиозаписи из сессии
    db.commit()  # Сохранение изменений
    return {"message": "Audio deleted successfully"}  # Возвращение сообщения об успешном удалении аудиозаписи
