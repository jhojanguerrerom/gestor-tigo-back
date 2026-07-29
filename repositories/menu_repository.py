from sqlalchemy.orm import Session
from app.models.menu_model import MenuModel, MenuProfileModel
from app.models.submenu_model import SubMenuModel, SubMenuProfileModel

class MenuRepository:
    def __init__(self, db: Session):
        """Inicializa el repository con la sesión de base de datos.
        
        Args:
            db: Sesión de SQLAlchemy inyectada por dependency
        """
        self.db = db

    def get_menu_by_profile(self, profile: int):
        return self.db.query(MenuModel).join(
            MenuProfileModel, MenuModel.id == MenuProfileModel.menu_id
        ).filter(
            MenuProfileModel.profile_id == profile,
            MenuModel.menu_state == True,
        ).all()

    def get_submenu_by_menu_id(self, menu_id: int, profile: int):
        return self.db.query(SubMenuModel).join(
            SubMenuProfileModel, SubMenuModel.id == SubMenuProfileModel.submenu_id
        ).filter(
            SubMenuModel.menu_id == menu_id, 
            SubMenuProfileModel.profile_id == profile, 
            SubMenuModel.submenu_state == True
        ).order_by(SubMenuModel.submenu_name).all()
