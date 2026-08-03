from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    project_code = Column(String(64), unique=True, nullable=False, index=True)
    project_name = Column(String(255), nullable=False)
    owner_name = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False, default="draft", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    sites = relationship("Site", back_populates="project", cascade="all, delete-orphan")


class Site(Base):
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True, index=True)
    site_code = Column(String(64), nullable=False, index=True)
    site_name = Column(String(255), nullable=False)
    address_text = Column(Text, default="")
    region = Column(String(128), default="")
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    project = relationship("Project", back_populates="sites")
    findings = relationship("Finding", back_populates="site", cascade="all, delete-orphan")


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    category = Column(String(128), nullable=False)
    description = Column(Text, default="")
    risk_level = Column(String(32), nullable=False, default="low")
    finding_status = Column(String(32), nullable=False, default="draft", index=True)
    reported_by = Column(String(128), default="")
    reported_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    site = relationship("Site", back_populates="findings")
    attachments = relationship("Attachment", back_populates="finding", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="finding", cascade="all, delete-orphan")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(128), default="")
    storage_note = Column(Text, default="")
    linked_finding_id = Column(Integer, ForeignKey("findings.id"), nullable=False, index=True)

    finding = relationship("Finding", back_populates="attachments")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(Integer, ForeignKey("findings.id"), nullable=False, index=True)
    reviewer_name = Column(String(128), nullable=False)
    conclusion = Column(String(32), nullable=False)
    comment = Column(Text, default="")
    reviewed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    finding = relationship("Finding", back_populates="reviews")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(64), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    action = Column(String(64), nullable=False)
    actor = Column(String(128), default="system")
    from_status = Column(String(32), default="")
    to_status = Column(String(32), default="")
    event_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SiteTemplate(Base):
    __tablename__ = "site_templates"

    id = Column(Integer, primary_key=True, index=True)
    template_name = Column(String(255), nullable=False)
    default_region = Column(String(128), default="")
    site_items = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
