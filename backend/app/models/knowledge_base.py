from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.db.base import Base

class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"
    id = Column(Integer, primary_key=True, index=True)
    module = Column(String(32), index=True, comment="所属模块，如bazi、liuyao、xingming、tarot等")
    category = Column(String(32), index=True, comment="知识类别，如断语、吉凶、案例等")
    keyword = Column(String(64), index=True, comment="关键词/标签")
    content = Column(Text, nullable=False, comment="知识内容")
    source = Column(String(128), default="builtin", comment="来源/出处")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
