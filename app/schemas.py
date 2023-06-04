from pydantic import BaseModel


# Описываем модель запроса
class CreateUserRequest(BaseModel):
    name: str
