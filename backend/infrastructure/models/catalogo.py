from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, SmallInteger,
    String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Torre(Base):
    __tablename__ = "torres"

    id:          Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre:      Mapped[str]      = mapped_column(String(120), nullable=False)
    nombre_norm: Mapped[str]      = mapped_column(String(120), nullable=False, unique=True)
    activa:      Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)
    creado_en:   Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    perfiles:        Mapped[list["Perfil"]]         = relationship(back_populates="torre", cascade="all, delete-orphan")
    consideraciones: Mapped[list["Consideracion"]]  = relationship(back_populates="torre")
    entregables:     Mapped[list["Entregable"]]     = relationship(back_populates="torre", cascade="all, delete-orphan")
    fuera_alcance:   Mapped[list["FueraDelAlcance"]] = relationship(back_populates="torre", cascade="all, delete-orphan")


class Perfil(Base):
    __tablename__ = "perfiles"

    id:          Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    torre_id:    Mapped[int]      = mapped_column(Integer, ForeignKey("torres.id", ondelete="CASCADE"), nullable=False)
    rol:         Mapped[str]      = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str]      = mapped_column(Text, nullable=False)
    activo:      Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)
    creado_en:   Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    torre: Mapped["Torre"] = relationship(back_populates="perfiles")


class Consideracion(Base):
    __tablename__ = "consideraciones"

    id:          Mapped[int]       = mapped_column(Integer, primary_key=True, autoincrement=True)
    torre_id:    Mapped[int | None] = mapped_column(Integer, ForeignKey("torres.id", ondelete="SET NULL"), nullable=True)
    texto:       Mapped[str]       = mapped_column(Text, nullable=False)
    es_general:  Mapped[bool]      = mapped_column(Boolean, nullable=False, default=False)
    activa:      Mapped[bool]      = mapped_column(Boolean, nullable=False, default=True)
    orden:       Mapped[int]       = mapped_column(SmallInteger, nullable=False, default=0)
    creado_en:   Mapped[datetime]  = mapped_column(DateTime, nullable=False, server_default=func.now())

    torre: Mapped["Torre | None"] = relationship(back_populates="consideraciones")


class Entregable(Base):
    __tablename__ = "entregables"

    id:        Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    torre_id:  Mapped[int]      = mapped_column(Integer, ForeignKey("torres.id", ondelete="CASCADE"), nullable=False)
    item:      Mapped[str]      = mapped_column(String(500), nullable=False)
    activo:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)
    orden:     Mapped[int]      = mapped_column(SmallInteger, nullable=False, default=0)
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    torre: Mapped["Torre"] = relationship(back_populates="entregables")


class FueraDelAlcance(Base):
    __tablename__ = "fuera_del_alcance"

    id:        Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    torre_id:  Mapped[int]      = mapped_column(Integer, ForeignKey("torres.id", ondelete="CASCADE"), nullable=False)
    item:      Mapped[str]      = mapped_column(String(600), nullable=False)
    activo:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)
    orden:     Mapped[int]      = mapped_column(SmallInteger, nullable=False, default=0)
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    torre: Mapped["Torre"] = relationship(back_populates="fuera_alcance")
