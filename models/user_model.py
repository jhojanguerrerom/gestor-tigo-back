from datetime import datetime
import uuid
from sqlalchemy import Column, Integer, Boolean, TIMESTAMP, BIGINT, UUID, TEXT
from app.db.base_model import Base
from app.db.timezone_types import get_bogota_now

class UserModel(Base):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4())
    login = Column(TEXT, nullable=False, index=True)
    user_identify = Column(BIGINT, nullable=True, index=True)
    full_name = Column(TEXT, nullable=True)
    profile_id = Column(Integer, nullable=True)
    create_user_login = Column(TEXT, nullable=True)
    user_state = Column(Boolean, nullable=True, default=True)
    email = Column(TEXT, nullable=True)
    create_at = Column(TIMESTAMP, nullable=True, default=get_bogota_now()) # datetime.now())
    last_access_date = Column(TIMESTAMP, nullable=True, default=None)

