from sqlalchemy import create_engine  # Для создания движка базы данных
from sqlalchemy.orm import sessionmaker  # Для создания сессии взаимодействия с базой данных
from sqlalchemy.ext.declarative import declarative_base  # Импортируем функцию declarative_base
from .config import settings

# Создаем подключение к базе данных
SQLALCHEMY_DATABASE_URL = (f'postgresql://{settings.database_username}:{settings.database_password}@'
                           f'{settings.database_hostname}:{settings.database_port}/{settings.database_name}')
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем базовый класс для всех моделей
Base = declarative_base()


# Зависимость для получения сессии базы данных
def get_db():
    db = SessionLocal()  # Создание новой сессии
    try:
        yield db  # Возврат сессии
    finally:
        db.close()  # Закрытие сессии
