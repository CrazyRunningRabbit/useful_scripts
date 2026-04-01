# app/models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from .db import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r}>"


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    # 中文名称
    name = Column(String, index=True)
    # 当前价格
    price = Column(Float, default=0.0)

    # 缩略图（后台展示、机器人也可用作外链）
    image_url = Column(String, nullable=True)
    # Telegram file_id（若用机器人发送图片更稳）
    image_file_id = Column(String, nullable=True)

    # 分类
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    category = relationship("Category")

    # 其他信息
    series = Column(String, nullable=True)
    code = Column(String, nullable=True)
    rarity = Column(String, nullable=True)

    # 英文名称（按你的约定复用 lang 字段）
    lang = Column(String, nullable=True)

    # 库存或销售数量
    stock = Column(Integer, nullable=True)

    # 历史价格关联
    history = relationship(
        "PriceHistory",
        back_populates="card",
        cascade="all, delete-orphan",
        order_by="PriceHistory.ts.asc()",
    )

    def __repr__(self) -> str:
        return f"<Card id={self.id} name={self.name!r} price={self.price}>"


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(Integer, ForeignKey("cards.id"), index=True, nullable=False)
    # 记录时间（UTC）
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    # 当时价格
    price = Column(Float, nullable=False)

    card = relationship("Card", back_populates="history")

    def __repr__(self) -> str:
        return f"<PriceHistory card_id={self.card_id} ts={self.ts.isoformat()} price={self.price}>"
