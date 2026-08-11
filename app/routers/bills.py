from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import bill_services
from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import BillCreate, BillOut, BillShareRequest, BillUpdate, Message

router = APIRouter(prefix="/api/bills", tags=["bills"])


@router.post("", response_model=BillOut, status_code=201)
def create_bill(
    payload: BillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BillOut:
    """创建自己的账单。"""
    return bill_services.create_bill(db, current_user, payload)


@router.get("", response_model=list[BillOut])
def list_my_bills(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BillOut]:
    """读取自己的全部账单。"""
    return bill_services.list_my_bills(db, current_user)


@router.get("/shared-with-me", response_model=list[BillOut])
def list_shared_with_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BillOut]:
    """读取别人分享给自己的账单。"""
    return bill_services.list_shared_with_me(db, current_user)


@router.get("/{bill_id}", response_model=BillOut)
def get_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BillOut:
    """读取单条账单（自己的，或别人分享给自己的）。"""
    return bill_services.get_bill(db, current_user, bill_id)


@router.patch("/{bill_id}", response_model=BillOut)
def update_bill(
    bill_id: int,
    payload: BillUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BillOut:
    """更新自己的账单。"""
    return bill_services.update_bill(db, current_user, bill_id, payload)


@router.delete("/{bill_id}", response_model=Message)
def delete_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Message:
    """删除自己的账单。"""
    bill_services.delete_bill(db, current_user, bill_id)
    return Message(message="Bill deleted")


@router.post("/{bill_id}/share", response_model=BillOut)
def share_bill(
    bill_id: int,
    payload: BillShareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BillOut:
    """分享自己的账单给其他用户阅读。"""
    return bill_services.share_bill(db, current_user, bill_id, payload.username)


@router.delete("/{bill_id}/share/{username}", response_model=BillOut)
def unshare_bill(
    bill_id: int,
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BillOut:
    """取消分享。"""
    return bill_services.unshare_bill(db, current_user, bill_id, username)


@router.post("/{bill_id}/like", response_model=BillOut)
def like_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BillOut:
    """点赞账单（自己的或已分享给自己的）。"""
    return bill_services.like_bill(db, current_user, bill_id)


@router.delete("/{bill_id}/like", response_model=BillOut)
def unlike_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BillOut:
    """取消点赞。"""
    return bill_services.unlike_bill(db, current_user, bill_id)
