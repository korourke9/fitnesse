"""User Data Access Object."""
from sqlalchemy.orm import Session
from app.models.user import User


class UserDAO:
    """Data access object for User operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, user_id: str) -> User | None:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def create(self, user_id: str, email: str) -> User:
        """Create a new user."""
        user = User(id=user_id, email=email)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def get_or_create_temp_user(self) -> User:
        """Get or create the temporary user. TODO: Replace with auth."""
        temp_user_id = "temp-user-123"
        temp_user_email = "temp@fitnesse.local"
        
        user = self.get_by_id(temp_user_id)
        if not user:
            user = self.create(temp_user_id, temp_user_email)
        return user

