from sqlalchemy.exc import IntegrityError, NoResultFound  # Импорт класса ошибок для работы с базой данных
from fastapi import APIRouter, status, HTTPException, Depends
from sqlalchemy.orm import Session
from .. import schemas, models
from ..database import get_db
from uuid import uuid4  # Импортируем модуль uuid для генерации UUID

router = APIRouter(
    prefix='/users',
    tags=['Users']
)


@router.post("/", status_code=status.HTTP_201_CREATED)  # Создание маршрута для создания пользователя
def create_user(user_data: schemas.CreateUserRequest,
                db: Session = Depends(get_db)):  # Функция принимает имя пользователя и сессию базы данных
    uuid_token = str(uuid4())  # Генерация UUID токена
    new_user = models.User(  # Создание нового пользователя
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


# Создание маршрута для удаления пользователя
@router.delete("/{user_id}")
def delete_user(user_id: int,
                db: Session = Depends(get_db)):  # Функция принимает идентификатор пользователя и сессию базы данных
    try:
        user = db.query(models.User).filter(
            models.User.id == user_id).one()  # Получение пользователя из базы данных по его идентификатору
    except NoResultFound:
        raise HTTPException(status_code=404,
                            detail="User not found")  # Если пользователь не найден, возвращаем ошибку 404

    # Удаление связанных записей из таблицы "audiorecords"
    db.query(models.AudioRecord).filter(models.AudioRecord.user_id == user.id).delete()
    db.delete(user)  # Удаление пользователя из сессии
    db.commit()  # Сохранение изменений
    return {"message": "User deleted successfully"}

