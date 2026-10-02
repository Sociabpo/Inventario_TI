from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid


class TipoServidor(Base):
    __tablename__ = "tipos_servidor"

    id          = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre      = Column(String(100), nullable=False, unique=True)
    descripcion = Column(String(200), nullable=True)


class Ambiente(Base):
    __tablename__ = "ambientes"

    id     = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = Column(String(100), nullable=False, unique=True)
    color  = Column(String(7), nullable=True)


class Criticidad(Base):
    __tablename__ = "criticidades"

    id     = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = Column(String(50), nullable=False, unique=True)
    nivel  = Column(Integer, nullable=False)
    color  = Column(String(7), nullable=False)


class EstadoServidor(Base):
    __tablename__ = "estados_servidor"

    id     = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = Column(String(100), nullable=False, unique=True)
    color  = Column(String(7), nullable=True)


class Ubicacion(Base):
    __tablename__ = "ubicaciones"
    __table_args__ = (UniqueConstraint("empresa_id", "nombre", name="uq_ubicacion_empresa_nombre"),)

    id          = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id  = Column(String(36), ForeignKey("empresas.id"), nullable=False)
    nombre      = Column(String(150), nullable=False)
    ciudad      = Column(String(100), nullable=True)
    pais        = Column(String(100), nullable=True, default="Colombia")
    descripcion = Column(String(200), nullable=True)

    empresa = relationship("Empresa")


class SistemaOperativo(Base):
    __tablename__ = "sistemas_operativos"

    id             = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre         = Column(String(150), nullable=False, unique=True)
    familia        = Column(String(50), nullable=False)
    soporte_activo = Column(Boolean, nullable=False, default=True, server_default="1")


class Herramienta(Base):
    __tablename__ = "herramientas"

    id          = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre      = Column(String(100), nullable=False, unique=True)
    categoria   = Column(String(50), nullable=False)
    descripcion = Column(String(200), nullable=True)
    activo      = Column(Boolean, nullable=False, default=True, server_default="1")


class Servidor(Base):
    __tablename__ = "servidores"
    __table_args__ = (UniqueConstraint("empresa_id", "hostname", name="uq_servidor_empresa_hostname"),)

    id               = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id       = Column(String(36), ForeignKey("empresas.id"), nullable=False)
    nombre           = Column(String(150), nullable=False)
    hostname         = Column(String(150), nullable=False)
    id_servicio      = Column(String(100), nullable=True)
    kawak_id         = Column(String(100), nullable=True)
    glpi_id          = Column(String(100), nullable=True)
    tipo_servidor_id = Column(String(36), ForeignKey("tipos_servidor.id"), nullable=True)
    ambiente_id      = Column(String(36), ForeignKey("ambientes.id"), nullable=True)
    criticidad_id    = Column(String(36), ForeignKey("criticidades.id"), nullable=True)
    estado_id        = Column(String(36), ForeignKey("estados_servidor.id"), nullable=True)
    ubicacion_id     = Column(String(36), ForeignKey("ubicaciones.id"), nullable=True)   # inerte (modelo Ubicacion sin uso)
    # Hosting: ubicación de hosting del servidor (AWS / On-premise / Triara…).
    # Catálogo GLOBAL Catalogo categoria='hosting' — NO confundir con 'ubicacion' (activos, per-empresa).
    ubicacion_catalogo_id = Column(String(36), ForeignKey("catalogos.id"), nullable=True, index=True)
    so_id            = Column(String(36), ForeignKey("sistemas_operativos.id"), nullable=True)
    procesador       = Column(String(200), nullable=True)
    memoria_ram      = Column(String(50), nullable=True)
    disco            = Column(String(200), nullable=True)
    ip_lan           = Column(String(45), nullable=True)
    ip_salida        = Column(String(45), nullable=True)
    observaciones    = Column(Text, nullable=True)
    pendientes       = Column(Text, nullable=True)
    activo           = Column(Boolean, nullable=False, default=True, server_default="1")
    # Baja: activo=False = dado de baja (VM que ya no existe / no llegó a producción).
    # El registro se CONSERVA (no hard-delete). estado_id pasa a "Dado de baja".
    motivo_baja      = Column(Text, nullable=True)
    fecha_baja       = Column(DateTime, nullable=True)
    dado_baja_por    = Column(String(36), nullable=True)   # usuario_sistema.id
    # Aplicabilidad por empresa (ADITIVO sobre empresa_id, que sigue siendo la empresa
    # OWNER/creadora). aplica_todas=True => visible para todas; False => solo las empresas
    # de servidor_empresas. INVARIANTE: si aplica_todas=False, la owner (empresa_id)
    # siempre está en servidor_empresas (el dueño nunca pierde de vista su servidor).
    aplica_todas     = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at       = Column(DateTime, server_default=func.now())
    updated_at       = Column(DateTime, server_default=func.now(), onupdate=func.now())

    empresa      = relationship("Empresa")
    tipo         = relationship("TipoServidor")
    ambiente     = relationship("Ambiente")
    criticidad   = relationship("Criticidad")
    estado       = relationship("EstadoServidor")
    ubicacion    = relationship("Ubicacion")   # inerte
    hosting      = relationship("Catalogo", foreign_keys=[ubicacion_catalogo_id])
    so           = relationship("SistemaOperativo")
    herramientas = relationship("ServidorHerramienta", back_populates="servidor",
                                cascade="all, delete-orphan")
    servicios    = relationship("ServicioServidor", back_populates="servidor")
    historial    = relationship("HistorialServidor", back_populates="servidor")
    empresas_aplicables = relationship("ServidorEmpresa", back_populates="servidor",
                                       cascade="all, delete-orphan")


class ServidorEmpresa(Base):
    """Empresas específicas a las que aplica un servidor (cuando aplica_todas=False).
       Aditivo: NO reemplaza servidor.empresa_id (owner); lo complementa."""
    __tablename__ = "servidor_empresas"
    __table_args__ = (UniqueConstraint("servidor_id", "empresa_id",
                                       name="uq_servidor_empresa_aplica"),)

    id          = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    servidor_id = Column(String(36), ForeignKey("servidores.id"), nullable=False, index=True)
    empresa_id  = Column(String(36), ForeignKey("empresas.id"), nullable=False, index=True)

    servidor = relationship("Servidor", back_populates="empresas_aplicables")
    empresa  = relationship("Empresa")


class ServidorHerramienta(Base):
    __tablename__ = "servidor_herramientas"
    __table_args__ = (UniqueConstraint("servidor_id", "herramienta_id",
                                       name="uq_servidor_herramienta"),)

    id                   = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    servidor_id          = Column(String(36), ForeignKey("servidores.id"), nullable=False)
    herramienta_id       = Column(String(36), ForeignKey("herramientas.id"), nullable=False)
    estado               = Column(String(20), nullable=False, default="pendiente")
    version              = Column(String(50), nullable=True)
    fecha_instalacion    = Column(Date, nullable=True)
    ultima_actualizacion = Column(Date, nullable=True)
    notas                = Column(String(300), nullable=True)
    created_at           = Column(DateTime, server_default=func.now())

    servidor    = relationship("Servidor", back_populates="herramientas")
    herramienta = relationship("Herramienta")


class ServicioServidor(Base):
    __tablename__ = "servicios_servidor"

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    servidor_id     = Column(String(36), ForeignKey("servidores.id"), nullable=False)
    nombre_servicio = Column(String(150), nullable=False)
    descripcion     = Column(String(300), nullable=True)
    puerto          = Column(Integer, nullable=True)
    protocolo       = Column(String(10), nullable=True)
    activo          = Column(Boolean, nullable=False, default=True, server_default="1")

    servidor = relationship("Servidor", back_populates="servicios")


class HistorialServidor(Base):
    __tablename__ = "historial_servidores"

    id                 = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    servidor_id        = Column(String(36), ForeignKey("servidores.id"), nullable=False)
    usuario_sistema_id = Column(String(36), ForeignKey("usuarios_sistema.id"), nullable=False)
    tipo_cambio        = Column(String(50), nullable=False)
    campo_modificado   = Column(String(100), nullable=True)
    valor_anterior     = Column(Text, nullable=True)
    valor_nuevo        = Column(Text, nullable=True)
    observacion        = Column(String(300), nullable=True)
    created_at         = Column(DateTime, server_default=func.now())

    servidor        = relationship("Servidor", back_populates="historial")
    usuario_sistema = relationship("UsuarioSistema")
