from sqlalchemy import Column, String, DateTime, Text, BigInteger
from sqlalchemy.sql import func
from database import Base

class AuditLog(Base):
    __tablename__ = "audit_log"

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    tabla           = Column(String(50), nullable=False)
    operacion       = Column(String(10), nullable=False)  # INSERT, UPDATE, DELETE
    registro_id     = Column(String(36), nullable=False)
    datos_anteriores = Column(Text)  # JSON como texto
    datos_nuevos    = Column(Text)   # JSON como texto
    usuario_app     = Column(String(150))
    ejecutado_en    = Column(DateTime, server_default=func.now())