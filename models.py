import uuid  # Импортируем модуль uuid для генерации UUID

from sqlalchemy import Column, Integer, String, ForeignKey  # Импортируем классы Column, Integer, String, ForeignKey из модуля sqlalchemy
from sqlalchemy.dialects.postgresql import UUID  # Импортируем класс UUID из модуля sqlalchemy.dialects.postgresql
from sqlalchemy.ext.declarative import declarative_base  # Импортируем функцию declarative_base из модуля sqlalchemy.ext.declarative


# Создаем базовый класс для всех моделей
Base = declarative_base()


class User(Base):
    __tablename__ = "users"  # Определяем имя таблицы в базе данных

    id = Column(Integer, primary_key=True, index=True)  # Определяем поле id с типом Integer, которое является первичным ключом и имеет индекс
    name = Column(String, unique=True)  # Определяем поле name с типом String, которое должно быть уникальным
    uuid_token = Column(String, unique=True)  # Определяем поле uuid_token с типом String, которое должно быть уникальным


class AudioRecord(Base):
    __tablename__ = "audiorecords"  # Определяем имя таблицы в базе данных

    id = Column(Integer, primary_key=True, index=True)   # Определяем поле id с типом Integer, которое является первичным ключом и имеет индекс
    user_id = Column(Integer, ForeignKey("users.id"))  # Определяем поле user_id с типом Integer, которое является внешним ключом и ссылается на поле id в таблице users
    audio_uuid = Column(UUID(as_uuid=True), unique=True, index=True, default=uuid.uuid4)  # Определяем поле audio_uuid с типом UUID, которое является уникальным и имеет индекс, инициализируем его значением, сгенерированным функцией uuid4
    audio_file = Column(String, unique=True, index=True)  # Определяем поле audio_file с типом String, которое должно быть уникальным
