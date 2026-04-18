from datetime import datetime
from sqlalchemy import ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(unique=True)

class Name(Base):
    __tablename__ = "names"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(unique=True)
    available_na_char: Mapped[int | None]
    available_na_family: Mapped[int | None]
    available_eu_char: Mapped[int | None]
    available_eu_family: Mapped[int | None]
    last_checked: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    name_categories: Mapped[list["NameCategory"]] = relationship(
        "NameCategory", back_populates="name", passive_deletes=True
    )


class NameCategory(Base):
    __tablename__ = "name_categories"
    __table_args__ = (UniqueConstraint("name_id", "category_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name_id: Mapped[int] = mapped_column(ForeignKey("names.id", ondelete="CASCADE"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    name: Mapped["Name"] = relationship("Name", back_populates="name_categories")
