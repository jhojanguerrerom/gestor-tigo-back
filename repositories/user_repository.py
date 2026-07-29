import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.postgres import SessionLocalPG
from app.models.user_model import UserModel

logger = logging.getLogger("user_repository")


class UserRepository:
    """
    Repository para operaciones CRUD de usuarios.
    """
    
    def __init__(self, db: Session):
        """Inicializa el repository con la sesión de base de datos.
        
        Args:
            db: Sesión de SQLAlchemy inyectada por dependency
        """
        self.db = db
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[UserModel]:
        """
        Obtiene todos los usuarios con paginación.
        
        Args:
            skip: Número de registros a saltar
            limit: Número máximo de registros a retornar
        
        Returns:
            Lista de usuarios
        """
        return self.db.query(UserModel).offset(skip).limit(limit).all()
    
    def get_by_id(self, user_id: int) -> Optional[UserModel]:
        """
        Obtiene un usuario por ID.
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Usuario o None si no existe
        """
        return self.db.query(UserModel).filter(UserModel.id == user_id).first()
    
    def get_by_username(self, username: str) -> Optional[UserModel]:
        """
        Busca un usuario por login.
        
        Args:
            login: Login del usuario
        
        Returns:
            Usuario o None si no existe
        """
        return self.db.query(UserModel).filter(UserModel.login == username).first()
    
    def create(self, user_data: dict) -> UserModel:
        """
        Crea un nuevo usuario.
        
        Args:
            user_data: Diccionario con datos del usuario
        
        Returns:
            Usuario creado
        """
        try:
            user = UserModel(**user_data)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"Usuario creado: {user.id}")
            return user
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear usuario: {e}")
            raise
    
    def update(self, user_id: int, user_data: dict) -> Optional[UserModel]:
        """
        Actualiza un usuario existente.
        
        Args:
            user_id: ID del usuario
            user_data: Diccionario con datos a actualizar
        
        Returns:
            Usuario actualizado o None si no existe
        """
        try:
            user = self.get_by_id(user_id)
            if not user:
                return None
            
            for key, value in user_data.items():
                setattr(user, key, value)
            
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"Usuario actualizado: {user.id}")
            return user
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar usuario: {e}")
            raise
    
    def delete(self, user_id: int) -> bool:
        """
        Elimina un usuario (soft delete - marca como inactivo).
        
        Args:
            user_id: ID del usuario
        
        Returns:
            True si se eliminó, False si no existe
        """
        try:
            user = self.get_by_id(user_id)
            if not user:
                return False
            
            user.user_state = False
            self.db.commit()
            logger.info(f"Usuario eliminado (soft): {user.id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al eliminar usuario: {e}")
            raise
    
    def search(self, query: str) -> List[UserModel]:
        """
        Busca usuarios por nombre o email.
        
        Args:
            query: Texto a buscar
        
        Returns:
            Lista de usuarios que coinciden
        """
        search_pattern = f"%{query}%"
        return self.db.query(UserModel).filter(
            (UserModel.full_name.ilike(search_pattern)) |
            (UserModel.email.ilike(search_pattern))
        ).all()
    
    def count_all(self, active_only: bool = True, search: str = None) -> int:
        """
        Cuenta el total de usuarios.
        
        Args:
            active_only: Si True, solo cuenta usuarios activos
            search: Texto de búsqueda opcional
        
        Returns:
            Número total de usuarios
        """
        query = self.db.query(UserModel)
        
        if active_only:
            query = query.filter(UserModel.user_state == True)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (UserModel.full_name.ilike(search_pattern)) |
                (UserModel.email.ilike(search_pattern)) |
                (UserModel.login.ilike(search_pattern))
            )
        
        return query.count()
