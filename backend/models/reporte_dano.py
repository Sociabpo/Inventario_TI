from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid
import json


class ReporteDano(Base):
    """Reporte de daño de una impresora enviado al proveedor por correo (Fase 3).

    Registro de trazabilidad (append-only). Las IMÁGENES NO se almacenan: solo el
    conteo (num_imagenes). destinatarios/cc se guardan como JSON list (mismo idioma
    que empresas.sedes / proveedor.modulos).
    """
    __tablename__ = "reportes_dano_impresora"

    id                 = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    impresora_id       = Column(String(36), ForeignKey("impresoras.id"), nullable=False, index=True)
    empresa_id         = Column(String(36), ForeignKey("empresas.id"), nullable=False, index=True)  # heredada de la impresora
    descripcion_dano   = Column(Text, nullable=True)
    asunto             = Column(String(300), nullable=True)   # asunto realmente enviado
    cuerpo             = Column(Text, nullable=True)          # cuerpo realmente enviado (html)
    destinatarios      = Column(Text, nullable=True)          # JSON list de correos "para"
    cc                 = Column(Text, nullable=True)          # JSON list de correos en copia
    num_imagenes       = Column(Integer, nullable=False, default=0, server_default="0")  # solo conteo; sin storage
    generado_por       = Column(String(36), nullable=True)   # usuario_sistema.id
    generado_por_email = Column(String(150), nullable=True)  # denormalizado para mostrar
    created_at         = Column(DateTime, server_default=func.now())

    impresora = relationship("Impresora")
    empresa   = relationship("Empresa")

    def _as_list(self, raw) -> list:
        if not raw:
            return []
        try:
            v = json.loads(raw)
            return [str(x) for x in v] if isinstance(v, list) else []
        except (ValueError, TypeError):
            return []

    @property
    def destinatarios_list(self) -> list:
        return self._as_list(self.destinatarios)

    @property
    def cc_list(self) -> list:
        return self._as_list(self.cc)
