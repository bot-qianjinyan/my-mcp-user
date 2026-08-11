from sqlalchemy.orm import Session, joinedload

from fastapi import HTTPException, status

from app.models import Bill, BillLike, BillShare, User
from app.schemas import BillCreate, BillOut, BillUpdate


def _to_bill_out(bill: Bill, current_user: User) -> BillOut:
    liked_by_me = any(like.user_id == current_user.id for like in bill.likes)
    shared_with = [share.shared_with.username for share in bill.shares if share.shared_with]
    return BillOut(
        id=bill.id,
        owner_id=bill.owner_id,
        owner_username=bill.owner.username if bill.owner else None,
        title=bill.title,
        amount=bill.amount,
        category=bill.category,
        note=bill.note,
        spent_at=bill.spent_at,
        like_count=len(bill.likes),
        liked_by_me=liked_by_me,
        shared_with=shared_with,
        created_at=bill.created_at,
        updated_at=bill.updated_at,
    )


def _bill_query(db: Session):
    return db.query(Bill).options(
        joinedload(Bill.owner),
        joinedload(Bill.likes),
        joinedload(Bill.shares).joinedload(BillShare.shared_with),
    )


def _get_bill_or_404(db: Session, bill_id: int) -> Bill:
    bill = _bill_query(db).filter(Bill.id == bill_id).first()
    if bill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return bill


def can_read_bill(bill: Bill, user: User) -> bool:
    if bill.owner_id == user.id:
        return True
    return any(share.shared_with_user_id == user.id for share in bill.shares)


def create_bill(db: Session, owner: User, payload: BillCreate) -> BillOut:
    bill = Bill(
        owner_id=owner.id,
        title=payload.title,
        amount=payload.amount,
        category=payload.category,
        note=payload.note,
        spent_at=payload.spent_at,
    )
    db.add(bill)
    db.commit()
    bill = _get_bill_or_404(db, bill.id)
    return _to_bill_out(bill, owner)


def list_my_bills(db: Session, owner: User) -> list[BillOut]:
    bills = (
        _bill_query(db)
        .filter(Bill.owner_id == owner.id)
        .order_by(Bill.id.desc())
        .all()
    )
    return [_to_bill_out(bill, owner) for bill in bills]


def list_shared_with_me(db: Session, user: User) -> list[BillOut]:
    bills = (
        _bill_query(db)
        .join(BillShare, BillShare.bill_id == Bill.id)
        .filter(BillShare.shared_with_user_id == user.id)
        .order_by(Bill.id.desc())
        .all()
    )
    return [_to_bill_out(bill, user) for bill in bills]


def get_bill(db: Session, user: User, bill_id: int) -> BillOut:
    bill = _get_bill_or_404(db, bill_id)
    if not can_read_bill(bill, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this bill")
    return _to_bill_out(bill, user)


def update_bill(db: Session, owner: User, bill_id: int, payload: BillUpdate) -> BillOut:
    bill = _get_bill_or_404(db, bill_id)
    if bill.owner_id != owner.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can update bill")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    for key, value in data.items():
        setattr(bill, key, value)

    db.add(bill)
    db.commit()
    bill = _get_bill_or_404(db, bill_id)
    return _to_bill_out(bill, owner)


def delete_bill(db: Session, owner: User, bill_id: int) -> None:
    bill = _get_bill_or_404(db, bill_id)
    if bill.owner_id != owner.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can delete bill")
    db.delete(bill)
    db.commit()


def share_bill(db: Session, owner: User, bill_id: int, username: str) -> BillOut:
    bill = _get_bill_or_404(db, bill_id)
    if bill.owner_id != owner.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can share bill")

    target = db.query(User).filter(User.username == username).first()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")
    if target.id == owner.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot share bill with yourself")

    exists = (
        db.query(BillShare)
        .filter(BillShare.bill_id == bill.id, BillShare.shared_with_user_id == target.id)
        .first()
    )
    if exists is None:
        db.add(BillShare(bill_id=bill.id, shared_with_user_id=target.id))
        db.commit()

    bill = _get_bill_or_404(db, bill_id)
    return _to_bill_out(bill, owner)


def unshare_bill(db: Session, owner: User, bill_id: int, username: str) -> BillOut:
    bill = _get_bill_or_404(db, bill_id)
    if bill.owner_id != owner.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can unshare bill")

    target = db.query(User).filter(User.username == username).first()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

    share = (
        db.query(BillShare)
        .filter(BillShare.bill_id == bill.id, BillShare.shared_with_user_id == target.id)
        .first()
    )
    if share is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found")

    db.delete(share)
    db.commit()
    bill = _get_bill_or_404(db, bill_id)
    return _to_bill_out(bill, owner)


def like_bill(db: Session, user: User, bill_id: int) -> BillOut:
    bill = _get_bill_or_404(db, bill_id)
    if not can_read_bill(bill, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this bill")

    exists = (
        db.query(BillLike)
        .filter(BillLike.bill_id == bill.id, BillLike.user_id == user.id)
        .first()
    )
    if exists is None:
        db.add(BillLike(bill_id=bill.id, user_id=user.id))
        db.commit()

    bill = _get_bill_or_404(db, bill_id)
    return _to_bill_out(bill, user)


def unlike_bill(db: Session, user: User, bill_id: int) -> BillOut:
    bill = _get_bill_or_404(db, bill_id)
    if not can_read_bill(bill, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this bill")

    like = (
        db.query(BillLike)
        .filter(BillLike.bill_id == bill.id, BillLike.user_id == user.id)
        .first()
    )
    if like is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Like not found")

    db.delete(like)
    db.commit()
    bill = _get_bill_or_404(db, bill_id)
    return _to_bill_out(bill, user)
