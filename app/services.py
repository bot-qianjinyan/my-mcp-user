from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas import Token, UserLogin, UserOut, UserRegister, UserUpdate


def register_user(db: Session, payload: UserRegister) -> UserOut:
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        display_name=payload.display_name or payload.username,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


def login_user(db: Session, payload: UserLogin) -> Token:
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    token = create_access_token(user.username)
    return Token(access_token=token, user=UserOut.model_validate(user))


def update_user_profile(db: Session, user: User, payload: UserUpdate) -> UserOut:
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    if "email" in data and data["email"] != user.email:
        exists = db.query(User).filter(User.email == data["email"], User.id != user.id).first()
        if exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
        user.email = data["email"]

    if "display_name" in data:
        user.display_name = data["display_name"]

    if "bio" in data:
        user.bio = data["bio"]

    if "password" in data and data["password"]:
        user.hashed_password = hash_password(data["password"])

    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


def get_user_by_username(db: Session, username: str) -> UserOut | None:
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        return None
    return UserOut.model_validate(user)
