from pydantic import BaseModel, Field

from shared.core.enums import UserType


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    user_type: UserType = UserType.user