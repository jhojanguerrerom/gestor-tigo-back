from sqlalchemy import Column, Integer, TEXT, Boolean
from app.db.base_model import Base

class MenuModel(Base):
    __tablename__ = "menu"

    id = Column(Integer, primary_key=True, index=True)
    menu_name = Column(TEXT, nullable=False)
    menu_state = Column(Boolean, nullable=False, default=True)

class MenuProfileModel(Base):
    __tablename__ = "menu_profile"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, nullable=False, index=True)
    menu_id = Column(Integer, nullable=False, index=True)
