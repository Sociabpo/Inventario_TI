from sqlalchemy import Column, String, ForeignKey, PrimaryKeyConstraint
from database import Base

class RolPermiso(Base):
    __tablename__ = "rol_permisos"

    rol_id     = Column(String(36), ForeignKey("roles.id"),    nullable=False)
    permiso_id = Column(String(36), ForeignKey("permisos.id"), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("rol_id", "permiso_id"),
    )
