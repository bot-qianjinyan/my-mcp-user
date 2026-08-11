from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)


class UserLogin(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, max_length=100)
    bio: str | None = Field(default=None, max_length=500)
    password: str | None = Field(default=None, min_length=6, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    display_name: str | None = None
    bio: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class Message(BaseModel):
    message: str


# ---- Bills ----


class BillCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    category: str | None = Field(default=None, max_length=50)
    note: str | None = Field(default=None, max_length=500)
    spent_at: date | None = None


class BillUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    category: str | None = Field(default=None, max_length=50)
    note: str | None = Field(default=None, max_length=500)
    spent_at: date | None = None


class BillShareRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)


class BillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    owner_username: str | None = None
    title: str
    amount: Decimal
    category: str | None = None
    note: str | None = None
    spent_at: date | None = None
    like_count: int = 0
    liked_by_me: bool = False
    shared_with: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
