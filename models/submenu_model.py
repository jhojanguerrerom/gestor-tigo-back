import enum
from sqlalchemy import Column, TEXT, Integer, String, Boolean
from app.db.base_model import Base

class EnumEstado(enum.Enum):
    Activo = "Activo"
    Inactivo = "Inactivo"

class SubMenuModel(Base):
    __tablename__ = "submenu"
    
    id = Column(Integer, primary_key=True, index=True)
    menu_id = Column(Integer, nullable=False, index=True)
    submenu_name = Column(TEXT, nullable=False)
    submenu_state = Column(Boolean, nullable=False, default=True)
    url = Column(TEXT, nullable=False)
    icon = Column(TEXT, nullable=False)

class SubMenuProfileModel(Base):
    __tablename__ = "submenu_profile"
    
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, nullable=False, index=True)
    submenu_id = Column(Integer, nullable=False, index=True)
    
    
