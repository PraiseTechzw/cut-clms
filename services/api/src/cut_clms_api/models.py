from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(StrEnum):
    INSTITUTION_ADMIN = "institution_admin"
    LAB_MANAGER = "lab_manager"
    TECHNICIAN = "technician"
    VIEWER = "viewer"


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint(
            "institution_id", "code", name="uq_department_institution_code"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)


class Laboratory(Base):
    __tablename__ = "laboratories"
    __table_args__ = (
        UniqueConstraint(
            "institution_id", "code", name="uq_laboratory_institution_code"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)


class InstitutionalUser(Base):
    __tablename__ = "institutional_users"
    __table_args__ = (
        UniqueConstraint("institution_id", "email", name="uq_user_institution_email"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    roles: Mapped[list[InstitutionalUserRole]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class InstitutionalUserRole(Base):
    __tablename__ = "institutional_user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role", name="uq_institutional_user_role"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("institutional_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            values_callable=lambda roles: [role.value for role in roles],
        ),
        nullable=False,
    )
    user: Mapped[InstitutionalUser] = relationship(back_populates="roles")


class ComputerAsset(Base):
    __tablename__ = "computer_assets"
    __table_args__ = (
        UniqueConstraint(
            "institution_id", "asset_tag", name="uq_asset_institution_tag"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    laboratory_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("laboratories.id", ondelete="SET NULL"), index=True
    )
    asset_tag: Mapped[str] = mapped_column(String(100), nullable=False)
    serial_number: Mapped[str | None] = mapped_column(String(200))


class EnrollmentToken(Base):
    __tablename__ = "enrollment_tokens"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EndpointDevice(Base):
    __tablename__ = "endpoint_devices"
    __table_args__ = (
        UniqueConstraint("device_id", name="uq_endpoint_device_identity"),
        Index("ix_endpoint_institution_last_seen", "institution_id", "last_seen_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("computer_assets.id", ondelete="SET NULL"), unique=True
    )
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    credential_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="online", nullable=False)
    agent_version: Mapped[str] = mapped_column(String(64), nullable=False)
    os_name: Mapped[str] = mapped_column(String(100), nullable=False)
    os_release: Mapped[str] = mapped_column(String(200), nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DeviceInventory(Base):
    __tablename__ = "device_inventories"
    __table_args__ = (
        Index("ix_inventory_endpoint_collected", "endpoint_id", "collected_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    endpoint_id: Mapped[UUID] = mapped_column(
        ForeignKey("endpoint_devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    operating_system: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    hardware: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    network_interfaces: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, nullable=False
    )
    storage_devices: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, nullable=False
    )


class InstalledSoftwareRecord(Base):
    __tablename__ = "installed_software"
    __table_args__ = (Index("ix_software_endpoint_name", "endpoint_id", "name"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    endpoint_id: Mapped[UUID] = mapped_column(
        ForeignKey("endpoint_devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inventory_id: Mapped[UUID] = mapped_column(
        ForeignKey("device_inventories.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[str | None] = mapped_column(String(200))
    publisher: Mapped[str | None] = mapped_column(String(300))


class DeviceTelemetry(Base):
    __tablename__ = "device_telemetry"
    __table_args__ = (
        Index("ix_telemetry_endpoint_received", "endpoint_id", "received_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    endpoint_id: Mapped[UUID] = mapped_column(
        ForeignKey("endpoint_devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    agent_reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    cpu_utilization_percent: Mapped[float | None]
    memory_utilization_percent: Mapped[float | None]
    uptime_seconds: Mapped[float | None]
    agent_status: Mapped[str] = mapped_column(String(32), nullable=False)
    disk_health: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_institution_created", "institution_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[UUID | None] = mapped_column(Uuid)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    endpoint_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("endpoint_devices.id", ondelete="SET NULL")
    )
    details: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
