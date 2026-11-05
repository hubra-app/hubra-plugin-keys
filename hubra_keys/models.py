"""Key and KeyHandover models (tenant schema)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hubra.core.extensions import db

KEY_KINDS = ("key", "card", "fob")
KEY_STATUSES = ("available", "issued", "lost", "retired")
HANDOVER_ACTIONS = ("issue", "return", "lost", "found", "retire")


class Key(db.Model):
    __tablename__ = "keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(db.String(120), nullable=False)
    # Engraved or printed number, unique per club when set.
    number: Mapped[str | None] = mapped_column(
        db.String(100), nullable=True, unique=True
    )
    kind: Mapped[str] = mapped_column(db.String(20), nullable=False, default="key")
    # Free text: which doors, lockers or rooms it opens.
    opens: Mapped[str | None] = mapped_column(db.String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        db.String(20), nullable=False, default="available"
    )
    holder_id: Mapped[int | None] = mapped_column(
        db.Integer, ForeignKey("members.id", ondelete="SET NULL"), nullable=True
    )
    deposit_chf: Mapped[float | None] = mapped_column(db.Numeric(10, 2), nullable=True)
    # A door code from the codes plugin, if that is installed. No foreign
    # key: Keys works without Codes; the id is checked when it is set.
    code_id: Mapped[int | None] = mapped_column(db.Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    holder: Mapped["Member | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Member", foreign_keys=[holder_id]
    )
    handovers: Mapped[list["KeyHandover"]] = relationship(
        "KeyHandover",
        back_populates="key",
        cascade="all, delete-orphan",
        order_by="KeyHandover.at.desc()",
    )

    def __repr__(self) -> str:
        return f"<Key id={self.id} label={self.label!r} status={self.status}>"


class KeyHandover(db.Model):
    """One entry in a key's history: issued, returned, lost, found, retired."""

    __tablename__ = "key_handovers"

    id: Mapped[int] = mapped_column(primary_key=True)
    key_id: Mapped[int] = mapped_column(
        db.Integer,
        ForeignKey("keys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(db.String(20), nullable=False)
    # Who received or gave back the key.
    member_id: Mapped[int | None] = mapped_column(
        db.Integer, ForeignKey("members.id", ondelete="SET NULL"), nullable=True
    )
    # Who recorded it.
    by_id: Mapped[int | None] = mapped_column(
        db.Integer, ForeignKey("members.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    key: Mapped["Key"] = relationship("Key", back_populates="handovers")
    member: Mapped["Member | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Member", foreign_keys=[member_id]
    )
    by: Mapped["Member | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Member", foreign_keys=[by_id]
    )


class MemberCard(db.Model):
    """A member's card: the secret behind the QR code in their app.

    One per member. Renewing it gives a new token, so a screenshot of the
    old code stops working.
    """

    __tablename__ = "member_cards"

    member_id: Mapped[int] = mapped_column(
        db.Integer, ForeignKey("members.id", ondelete="CASCADE"), primary_key=True
    )
    token: Mapped[str] = mapped_column(db.String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class CheckIn(db.Model):
    """A scanned card: who came, when, and to which event (if any)."""

    __tablename__ = "checkins"

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(
        db.Integer,
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[int | None] = mapped_column(
        db.Integer,
        ForeignKey("club_events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Where, when it is not an event: "Workshop door".
    place: Mapped[str | None] = mapped_column(db.String(120), nullable=True)
    by_id: Mapped[int | None] = mapped_column(
        db.Integer, ForeignKey("members.id", ondelete="SET NULL"), nullable=True
    )
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    member: Mapped["Member"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Member", foreign_keys=[member_id]
    )


class SmartLock(db.Model):
    """A Nuki smart lock the club opens to its members.

    Who may open it: members of ``group_id`` (everyone when unset) whose
    membership runs and who are not suspended. Each gets a keypad code of
    their own and, with ``app_open``, an Open button in the app.
    """

    __tablename__ = "smart_locks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(120), nullable=False)
    # Nuki's smartlockId (Nuki Web).
    smartlock_id: Mapped[int] = mapped_column(db.BigInteger, nullable=False)
    group_id: Mapped[int | None] = mapped_column(
        db.Integer, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True
    )
    keypad: Mapped[bool] = mapped_column(db.Boolean, default=True, nullable=False)
    app_open: Mapped[bool] = mapped_column(db.Boolean, default=True, nullable=False)
    synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    access: Mapped[list["LockAccess"]] = relationship(
        "LockAccess", back_populates="lock", cascade="all, delete-orphan"
    )


class LockAccess(db.Model):
    """One member's keypad code on one lock, as Nuki knows it.

    ``active`` once Nuki has it, ``failed`` when the last try did not work
    (the next sync tries again). The code is stored encrypted.
    """

    __tablename__ = "lock_access"
    __table_args__ = (
        db.UniqueConstraint("lock_id", "member_id", name="uq_lock_access"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lock_id: Mapped[int] = mapped_column(
        db.Integer, ForeignKey("smart_locks.id", ondelete="CASCADE"), nullable=False
    )
    member_id: Mapped[int] = mapped_column(
        db.Integer, ForeignKey("members.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth_id: Mapped[str | None] = mapped_column(db.String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        db.String(20), default="pending", nullable=False
    )
    error: Mapped[str | None] = mapped_column(db.String(300), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    lock: Mapped["SmartLock"] = relationship("SmartLock", back_populates="access")
