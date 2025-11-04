import io
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Query, Path, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone, time
from enum import Enum
import random
import uuid

# --- LIBRERÍAS DE SEGURIDAD ---
from passlib.context import CryptContext
from jose import JWTError, jwt

# --- IMPORTS DE BASE DE DATOS ---
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, ForeignKey, JSON, Table, Time, func
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.ext.declarative import declarative_base

# --- 1. CONFIGURACIÓN DE LA BASE DE DATOS ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./frio_natural.db" 

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 2. CONFIGURACIÓN DE SEGURIDAD ---
SECRET_KEY = "frio-natural-secret-key-muy-segura"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- 3. DEFINICIONES DE ENUMS ---
class EstadoPedido(str, Enum):
    pendiente = "pendiente"
    confirmado = "confirmado"
    en_preparacion = "en_preparacion"
    listo_para_retiro = "listo_para_retiro"
    en_camino = "en_camino"
    entregado = "entregado"
    cancelado = "cancelado"

class EstadoPago(str, Enum):
    pendiente = "pendiente"
    pagado = "pagado"
    rechazado = "rechazado"

class EstadoSeguimiento(str, Enum):
    iniciado = "iniciado"
    en_camino = "en_camino"
    entregado = "entregado"

# --- 4. TABLAS DE ASOCIACIÓN (Many-to-Many) ---

carrito_item_toppings_tabla = Table('carrito_item_toppings', Base.metadata,
    Column('carrito_item_id', Integer, ForeignKey('carrito_items.id'), primary_key=True),
    Column('topping_id', Integer, ForeignKey('toppings.id'), primary_key=True)
)

pedido_items_tabla = Table('pedido_items', Base.metadata,
    Column('pedido_id', Integer, ForeignKey('pedidos.id'), primary_key=True),
    Column('producto_id', Integer, ForeignKey('productos.id'), primary_key=True),
    Column('cantidad', Integer),
    Column('precio_en_el_momento', Float),
    Column('sabores_seleccionados', JSON),
    Column('toppings_seleccionados', JSON)
)


# --- 5. MODELOS DE BASE DE DATOS (SQLAlchemy) ---

class UsuarioDB(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    saboresFavoritos = Column(JSON, nullable=True) # B-01
    
    carrito = relationship("CarritoDB", back_populates="dueño", uselist=False, cascade="all, delete-orphan")
    suscripciones = relationship("SuscripcionDB", back_populates="dueño", cascade="all, delete-orphan")
    pedidos = relationship("PedidoDB", back_populates="dueño")
    comprobantes = relationship("ComprobanteDB", back_populates="dueño")

class ProductoDB(Base):
    __tablename__ = "productos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    descripcion = Column(String, nullable=True)     # B-04
    foto = Column(String, nullable=True)            # B-04
    alergenos = Column(JSON, nullable=True)         # B-04
    precio = Column(Float, nullable=True)           # B-05
    tipo = Column(String, nullable=True)            # B-05
    sabor = Column(String, nullable=True)           # B-05
    tamano = Column(String, nullable=True)          # B-05
    maxSabores = Column(Integer, default=1)         # B-10

    presentaciones = relationship("PresentacionDB", back_populates="producto", cascade="all, delete-orphan") # B-06

class PresentacionDB(Base):
    __tablename__ = "presentaciones"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    stock = Column(Integer)
    producto_id = Column(Integer, ForeignKey('productos.id'))
    producto = relationship("ProductoDB", back_populates="presentaciones")

class ToppingDB(Base):
    __tablename__ = "toppings"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    costo = Column(Float)
    alergenos = Column(JSON, nullable=True)
    stock = Column(Integer, default=99)

class PromocionDB(Base):
    __tablename__ = "promociones"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    vigencia = Column(DateTime(timezone=True))
    condiciones = Column(String)
    tipo = Column(String)
    etiquetas = Column(JSON)

class CarritoDB(Base):
    __tablename__ = "carritos"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), unique=True)
    subtotal = Column(Float, default=0.0)
    descuento = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    
    dueño = relationship("UsuarioDB", back_populates="carrito")
    items = relationship("CarritoItemDB", back_populates="carrito", cascade="all, delete-orphan")

class CarritoItemDB(Base):
    __tablename__ = "carrito_items"
    id = Column(Integer, primary_key=True, index=True)
    carrito_id = Column(Integer, ForeignKey('carritos.id'))
    producto_id = Column(Integer, ForeignKey('productos.id'))
    cantidad = Column(Integer)
    sabores = Column(JSON)
    
    producto = relationship("ProductoDB")
    carrito = relationship("CarritoDB", back_populates="items")
    toppings = relationship("ToppingDB", secondary=carrito_item_toppings_tabla)

class CuponDB(Base):
    __tablename__ = "cupones"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String, unique=True, index=True)
    porcentajeDescuento = Column(Float)
    expirado = Column(Boolean, default=False)
    fecha_expiracion = Column(DateTime(timezone=True), nullable=True)

class SuscripcionDB(Base):
    __tablename__ = "suscripciones"
    id = Column(Integer, primary_key=True, index=True)
    contacto = Column(String)
    via = Column(String)
    sabores = Column(JSON)
    confirmada = Column(Boolean, default=False)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True) 
    dueño = relationship("UsuarioDB", back_populates="suscripciones")

class PedidoDB(Base):
    __tablename__ = "pedidos"
    id = Column(Integer, primary_key=True, index=True)
    # ID público para el cliente
    public_id = Column(String, unique=True, index=True, default=lambda: f"FN-{uuid.uuid4().hex[:8].upper()}")
    usuario_id = Column(Integer, ForeignKey('usuarios.id'))
    estado = Column(String, default=EstadoPedido.pendiente)
    metodoPago = Column(String)
    horarioLimite = Column(Time, nullable=True)
    estadoPago = Column(String, default=EstadoPago.pendiente)
    
    notificacionCanal = Column(String, default="email")
    notificacionEstados = Column(JSON, nullable=True)
    notificacionNoMolestar = Column(Boolean, default=False)

    dueño = relationship("UsuarioDB", back_populates="pedidos")
    productos = relationship("ProductoDB", secondary=pedido_items_tabla)
    pago = relationship("PagoDB", back_populates="pedido", uselist=False)
    comprobante = relationship("ComprobanteDB", back_populates="pedido", uselist=False)
    seguimiento = relationship("SeguimientoDB", back_populates="pedido", uselist=False)

class PagoDB(Base):
    __tablename__ = "pagos"
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey('pedidos.id'))
    token = Column(String, nullable=True)
    estado = Column(String)
    medio_pago = Column(String)
    orderId = Column(String)
    
    pedido = relationship("PedidoDB", back_populates="pago")

class ComprobanteDB(Base):
    __tablename__ = "comprobantes"
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey('pedidos.id'))
    usuario_id = Column(Integer, ForeignKey('usuarios.id'))
    urlArchivo = Column(String)
    formato = Column(String)
    
    pedido = relationship("PedidoDB", back_populates="comprobante")
    dueño = relationship("UsuarioDB", back_populates="comprobantes")

class ZonaDespachoDB(Base):
    __tablename__ = "zonas_despacho"
    id = Column(Integer, primary_key=True, index=True)
    comuna = Column(String, unique=True)
    costo = Column(Float)
    tiempoEstimado = Column(String)

class SeguimientoDB(Base):
    __tablename__ = "seguimientos"
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey('pedidos.id'), unique=True)
    repartidorId = Column(String, nullable=True)
    estado = Column(String)
    horaEstimada = Column(Time, nullable=True)
    puntaje = Column(Integer, nullable=True)
    comentario = Column(String, nullable=True)
    
    pedido = relationship("PedidoDB", back_populates="seguimiento")


# --- 6. SCHEMAS (DTOs de Pydantic) ---

class ConfigORM:
    from_attributes = True

# --- Schemas de USUARIO ---
class UsuarioCreateInput(BaseModel):
    email: EmailStr
    contraseña: str = Field(min_length=6)
    saboresFavoritos: Optional[List[str]] = None

class LoginInput(BaseModel):
    email: EmailStr
    pass_field: str = Field(alias="pass") 
    recordarDevice: Optional[bool] = False

class EmailInput(BaseModel):
    email: EmailStr

class UsuarioSchema(BaseModel):
    id: int
    email: EmailStr
    saboresFavoritos: Optional[List[str]] = None
    class Config(ConfigORM): pass

class TokenData(BaseModel):
    email: Optional[str] = None

# --- Schemas de PRODUCTO ---
class ProductoFilterInput(BaseModel):
    pagina: int = 1
    limite: int = 10
    sabor: Optional[str] = None
    tipo: Optional[List[str]] = None
    tamano: Optional[str] = None
    busqueda: Optional[str] = None

class PresentacionSchema(BaseModel):
    id: int
    nombre: str
    stock: int
    class Config(ConfigORM): pass

class ProductoSchema(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    foto: Optional[str] = None
    alergenos: Optional[List[str]] = None
    precio: Optional[float] = None
    tipo: Optional[str] = None
    sabor: Optional[str] = None
    tamano: Optional[str] = None
    maxSabores: Optional[int] = None
    presentaciones: List[PresentacionSchema] = []
    class Config(ConfigORM): pass

# --- Schemas de PROMOCION ---
class PromocionQueryInput(BaseModel):
    texto: Optional[str] = None
    tipo: Optional[str] = None
    etiquetas: Optional[List[str]] = None
    tamano: Optional[str] = None
    soloVigentes: bool = True

class PromocionSchema(BaseModel):
    id: int
    nombre: str
    vigencia: datetime
    condiciones: str
    tipo: str
    etiquetas: Optional[List[str]] = None
    class Config(ConfigORM): pass

# --- Schemas de CARRITO ---
class CarritoItemInput(BaseModel):
    productoId: int
    sabores: List[str]
    cantidad: int = Field(gt=0)
    toppingIds: List[int] = []

class CarritoItemUpdateInput(BaseModel):
    cantidad: int = Field(gt=0)
    sabores: List[str]
    toppingIds: List[int]

class ToppingsInput(BaseModel):
    toppingIds: List[int]

class CuponInput(BaseModel):
    codigo: str

class ToppingSchema(BaseModel):
    id: int
    nombre: str
    costo: float
    class Config(ConfigORM): pass

class CarritoItemSchema(BaseModel):
    id: int
    producto_id: int
    cantidad: int
    sabores: List[str]
    toppings: List[ToppingSchema] = []
    class Config(ConfigORM): pass

class CarritoSchema(BaseModel):
    id: int
    usuario_id: int
    subtotal: float
    descuento: float
    total: float
    items: List[CarritoItemSchema] = []
    class Config(ConfigORM): pass

# --- Schemas de SUSCRIPCION ---
class SuscripcionInput(BaseModel):
    contacto: str
    via: str
    sabores: Optional[List[str]] = None

class CancelarInput(BaseModel):
    contacto: str
    via: str

class SuscripcionSchema(BaseModel):
    id: int
    contacto: str
    via: str
    sabores: Optional[List[str]] = None
    confirmada: bool
    class Config(ConfigORM): pass

# --- Schemas de PEDIDO y PAGO ---
class ReservaInput(BaseModel):
    metodoPago: str

class PedidoSchema(BaseModel):
    id: int
    public_id: str
    usuario_id: int
    estado: str
    metodoPago: str
    horarioLimite: Optional[time] = None
    estadoPago: str
    class Config(ConfigORM): pass

class IniciarPagoInput(BaseModel):
    orderId: str
    medio: str

class CallbackInput(BaseModel):
    token: str
    estado: str

class ReintentarPagoInput(BaseModel):
    orderId: str

class PagoSchema(BaseModel):
    id: int
    pedido_id: int
    token: Optional[str] = None
    estado: str
    medio_pago: str
    class Config(ConfigORM): pass

# --- Schemas de COMPROBANTE ---
class EnviarComprobanteInput(BaseModel):
    pedidoId: str # Usamos el public_id
    email: EmailStr

class DescargarComprobanteInput(BaseModel):
    formato: str

class ComprobanteSchema(BaseModel):
    id: int
    pedido_id: int
    usuario_id: int
    urlArchivo: str
    formato: str
    class Config(ConfigORM): pass

# --- Schemas de ENVIO ---
class CalculoEnvioInput(BaseModel):
    direccion: str
    comuna: str
    tipoEntrega: str

class CostoEnvioSchema(BaseModel):
    comuna: str
    costo: float
    tiempoEstimado: str
    class Config(ConfigORM): pass

# --- Schemas de SEGUIMIENTO ---
class NotificacionLlegadaInput(BaseModel):
    canalNotificacion: str

class CalificacionInput(BaseModel):
    puntaje: int = Field(ge=1, le=5)
    comentario: Optional[str] = None

class SeguimientoSchema(BaseModel):
    id: int
    pedido_id: int
    repartidorId: Optional[str] = None
    estado: str
    horaEstimada: Optional[time] = None
    puntaje: Optional[int] = None
    comentario: Optional[str] = None
    class Config(ConfigORM): pass

# --- Schemas de NOTIFICACION PEDIDO ---
class ConfiguracionNotificacionInput(BaseModel):
    canal: str
    estados: List[str]
    noMolestar: bool

class CambioEstadoInput(BaseModel):
    estado: str
    mensaje: str

# --- Schema de RESPUESTA Genérica ---
class ResponseSchema(BaseModel):
    status: int
    body: Dict | List | str | Any


# --- 7. FUNCIONES HELPER DE SEGURIDAD ---
def verificar_contraseña(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hashear_contraseña(password: str) -> str:
    return pwd_context.hash(password)

def crear_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta: 
        expire = datetime.now(timezone.utc) + expires_delta
    else: 
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- 8. FUNCIONES DE AUTENTICACIÓN Y BBDD ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_usuario_by_email(db: Session, email: str) -> Optional[UsuarioDB]:
    return db.query(UsuarioDB).filter(UsuarioDB.email == email).first()

def get_producto_by_id(db: Session, producto_id: int) -> Optional[ProductoDB]:
    return db.query(ProductoDB).filter(ProductoDB.id == producto_id).first()

def get_topping_by_id(db: Session, topping_id: int) -> Optional[ToppingDB]:
    return db.query(ToppingDB).filter(ToppingDB.id == topping_id).first()
    
def get_pedido_by_public_id(db: Session, public_id: str) -> Optional[PedidoDB]:
    return db.query(PedidoDB).filter(PedidoDB.public_id == public_id).first()

def get_pedido_by_id(db: Session, id: int) -> Optional[PedidoDB]:
    return db.query(PedidoDB).filter(PedidoDB.id == id).first()

def get_cupon_by_codigo(db: Session, codigo: str) -> Optional[CuponDB]:
    return db.query(CuponDB).filter(CuponDB.codigo == codigo, CuponDB.expirado == False).first()

def get_carrito_item_by_id(db: Session, item_id: int, carrito_id: int) -> Optional[CarritoItemDB]:
    return db.query(CarritoItemDB).filter(CarritoItemDB.id == item_id, CarritoItemDB.carrito_id == carrito_id).first()

def get_or_create_carrito(db: Session, usuario_id: int) -> CarritoDB:
    carrito = db.query(CarritoDB).filter(CarritoDB.usuario_id == usuario_id).first()
    if not carrito:
        carrito = CarritoDB(usuario_id=usuario_id, subtotal=0, descuento=0, total=0)
        db.add(carrito)
        db.commit()
        db.refresh(carrito)
    return carrito

def autenticar_usuario(db: Session, email: str, contraseña: str) -> Optional[UsuarioDB]:
    usuario = get_usuario_by_email(db, email)
    if not usuario or not verificar_contraseña(contraseña, usuario.hashed_password):
        return None
    return usuario

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UsuarioDB:
    credentials_exception = HTTPException(
        status_code=401, 
        detail="Credenciales inválidas", 
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None: 
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    usuario = get_usuario_by_email(db, email=token_data.email)
    if usuario is None: 
        raise credentials_exception
    return usuario

# --- 9. CREA LA APP ---
app = FastAPI(
    title="Heladería Frio Natural API",
    description="API completa basada en los 18 diagramas de clases."
)

# ¡Esta línea crea el archivo 'frio_natural.db' y todas las tablas!
Base.metadata.create_all(bind=engine)

# --- 10. ENDPOINTS (API) ---

@app.get("/", summary="Endpoint raíz", include_in_schema=False)
def leer_root(): 
    return {"mensaje": "¡Bienvenido a la API de Heladería Frio Natural!"}

# --- ENDPOINTS DE USUARIO ---
@app.post("/api/usuario/registrar", response_model=UsuarioSchema, status_code=201, tags=["B-01: Usuario"])
def registrar_usuario(usuario_input: UsuarioCreateInput, db: Session = Depends(get_db)):
    if get_usuario_by_email(db, usuario_input.email):
        raise HTTPException(status_code=400, detail="El Email ya está en uso")
    
    hashed_password = hashear_contraseña(usuario_input.contraseña)
    nuevo_usuario_db = UsuarioDB(
        email=usuario_input.email, 
        hashed_password=hashed_password,
        saboresFavoritos=usuario_input.saboresFavoritos
    )
    db.add(nuevo_usuario_db)
    db.commit()
    db.refresh(nuevo_usuario_db)
    return nuevo_usuario_db

@app.post("/token", response_model=dict, tags=["B-02: Usuario"])
def login_para_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = autenticar_usuario(db, form_data.username, form_data.password)
    if not usuario:
        raise HTTPException(status_code=401, detail="Email o contraseña incorrecta", headers={"WWW-Authenticate": "Bearer"})
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = crear_access_token(
        data={"sub": usuario.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/usuario/solicitar-reset", response_model=ResponseSchema, tags=["B-03: Usuario"])
def solicitar_reset(input: EmailInput, db: Session = Depends(get_db)):
    usuario = get_usuario_by_email(db, input.email)
    if not usuario:
        return ResponseSchema(status=200, body={"mensaje": "Si el email existe, se enviará un enlace de reseteo."})
    print(f"Enviando email de reseteo a: {usuario.email}")
    return ResponseSchema(status=200, body={"mensaje": "Si el email existe, se enviará un enlace de reseteo."})

@app.get("/api/usuario/me", response_model=UsuarioSchema, tags=["Usuario"])
async def leer_mi_perfil(current_user: UsuarioDB = Depends(get_current_user)):
    return current_user

# --- ENDPOINTS DE CATÁLOGO ---
@app.get("/api/catalogo", response_model=List[ProductoSchema], tags=["B-04/B-05: Catálogo"])
def listar_productos(
    filtros: ProductoFilterInput = Depends(), 
    db: Session = Depends(get_db)
):
    query = db.query(ProductoDB)
    if filtros.busqueda:
        query = query.filter(ProductoDB.nombre.ilike(f"%{filtros.busqueda}%"))
    # ... (agregar más lógica de filtros) ...
    productos = query.offset((filtros.pagina - 1) * filtros.limite).limit(filtros.limite).all()
    return productos

@app.get("/api/catalogo/{id}", response_model=ProductoSchema, tags=["B-06: Catálogo"])
def ver_detalle_producto(
    id: int = Path(..., title="ID del Producto"), 
    db: Session = Depends(get_db)
):
    producto = get_producto_by_id(db, id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto

# --- ENDPOINTS DE PROMOCIONES ---
@app.get("/api/promociones", response_model=List[PromocionSchema], tags=["B-07: Promociones"])
def listar_promociones(
    params: PromocionQueryInput = Depends(), 
    db: Session = Depends(get_db)
):
    query = db.query(PromocionDB)
    if params.soloVigentes:
        query = query.filter(PromocionDB.vigencia > func.now())
    # ... (agregar más lógica de filtros) ...
    promociones = query.all()
    return promociones

# --- ENDPOINTS DE CARRITO ---
@app.post("/api/carrito/items", response_model=CarritoSchema, tags=["B-10: Carrito"])
def agregar_item_al_carrito(
    item_input: CarritoItemInput,
    current_user: UsuarioDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    producto = get_producto_by_id(db, item_input.productoId)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    if len(item_input.sabores) > producto.maxSabores:
        raise HTTPException(status_code=400, detail=f"Este producto solo permite {producto.maxSabores} sabores.")

    carrito = get_or_create_carrito(db, current_user.id)
    
    # (Lógica simplificada, no agrupa items idénticos)
    nuevo_item = CarritoItemDB(
        carrito_id=carrito.id,
        producto_id=item_input.productoId,
        sabores=item_input.sabores,
        cantidad=item_input.cantidad
    )
    db.add(nuevo_item)
    
    # Añadir toppings
    for topping_id in item_input.toppingIds:
        topping = get_topping_by_id(db, topping_id)
        if topping:
            nuevo_item.toppings.append(topping)
            
    # (Faltaría recalcular totales)
    db.commit()
    db.refresh(carrito)
    return carrito

@app.put("/api/carrito/items/{id}", response_model=CarritoSchema, tags=["B-12: Carrito"])
def actualizar_item_carrito(
    id: int,
    item_update: CarritoItemUpdateInput,
    current_user: UsuarioDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    carrito = get_or_create_carrito(db, current_user.id)
    item = get_carrito_item_by_id(db, id, carrito.id)
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado en el carrito")
        
    item.cantidad = item_update.cantidad
    item.sabores = item_update.sabores
    
    # Actualizar Toppings
    item.toppings.clear()
    for topping_id in item_update.toppingIds:
        topping = get_topping_by_id(db, topping_id)
        if topping:
            item.toppings.append(topping)

    # (Faltaría recalcular totales)
    db.commit()
    db.refresh(carrito)
    return carrito

@app.put("/api/carrito/me/aplicar-cupon", response_model=CarritoSchema, tags=["B-08: Carrito"])
def aplicar_cupon(
    cupon_input: CuponInput,
    current_user: UsuarioDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    carrito = get_or_create_carrito(db, current_user.id)
    cupon = get_cupon_by_codigo(db, cupon_input.codigo)
    
    if not cupon:
        raise HTTPException(status_code=404, detail="Cupón no válido o expirado")
        
    carrito.subtotal = 10000 
    carrito.descuento = carrito.subtotal * (cupon.porcentajeDescuento / 100)
    carrito.total = carrito.subtotal - carrito.descuento
    
    db.commit()
    db.refresh(carrito)
    return carrito

# --- ENDPOINTS DE SUSCRIPCIONES ---
@app.post("/api/suscripciones", response_model=SuscripcionSchema, status_code=201, tags=["B-09: Suscripciones"])
def suscribirse(
    input: SuscripcionInput, 
    db: Session = Depends(get_db)
):
    existente = db.query(SuscripcionDB).filter(SuscripcionDB.contacto == input.contacto).first()
    if existente:
        return existente

    nueva_suscripcion = SuscripcionDB(**input.model_dump(), confirmada=False)
    db.add(nueva_suscripcion)
    db.commit()
    db.refresh(nueva_suscripcion)
    
    print(f"Enviando confirmación a {input.contacto} por {input.via}")
    return nueva_suscripcion

@app.put("/api/suscripciones/confirmar/{token}", response_model=ResponseSchema, tags=["B-09: Suscripciones"])
def confirmar_suscripcion(token: str, db: Session = Depends(get_db)):
    # (Lógica simulada)
    suscripcion = db.query(SuscripcionDB).filter(SuscripcionDB.confirmada == False).first()
    if not suscripcion:
        raise HTTPException(status_code=404, detail="Token no válido")
        
    suscripcion.confirmada = True
    db.commit()
    return ResponseSchema(status=200, body={"mensaje": "Suscripción confirmada"})

@app.post("/api/suscripciones/cancelar", response_model=ResponseSchema, tags=["B-09: Suscripciones"])
def cancelar_suscripcion(input: CancelarInput, db: Session = Depends(get_db)):
    suscripcion = db.query(SuscripcionDB).filter(SuscripcionDB.contacto == input.contacto).first()
    if suscripcion:
        db.delete(suscripcion)
        db.commit()
    return ResponseSchema(status=200, body={"mensaje": "Suscripción cancelada"})

# --- ENDPOINTS DE PEDIDOS Y PAGOS ---
@app.post("/api/pedidos/reservar", response_model=PedidoSchema, tags=["B-15: Pedidos"])
def reservar_pedido(
    input: ReservaInput,
    current_user: UsuarioDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    carrito = get_or_create_carrito(db, current_user.id)
    if not carrito.items:
        raise HTTPException(status_code=400, detail="El carrito está vacío")
    
    nuevo_pedido = PedidoDB(
        usuario_id=current_user.id,
        estado=EstadoPedido.pendiente,
        metodoPago=input.metodoPago,
        estadoPago=EstadoPago.pendiente,
        horarioLimite= (datetime.now(timezone.utc) + timedelta(minutes=10)).time()
    )
    db.add(nuevo_pedido)
    
    # (Copiar items del carrito al pedido)
    
    # Vaciar carrito
    db.query(CarritoItemDB).filter(CarritoItemDB.carrito_id == carrito.id).delete()
    
    db.commit()
    db.refresh(nuevo_pedido)
    return nuevo_pedido

@app.post("/api/pagos/iniciar", response_model=ResponseSchema, tags=["B-13: Pagos"])
def iniciar_pago(input: IniciarPagoInput, db: Session = Depends(get_db)):
    pedido = get_pedido_by_public_id(db, input.orderId)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
        
    simulated_token = f"token_simulado_{uuid.uuid4().hex[:6]}"
    nuevo_pago = PagoDB(
        pedido_id=pedido.id,
        token=simulated_token,
        estado=EstadoPago.pendiente,
        medio_pago=input.medio,
        orderId=input.orderId
    )
    db.add(nuevo_pago)
    db.commit()
    
    return ResponseSchema(status=200, body={"redirect_url": f"/simulador/pago?token={simulated_token}"})

@app.post("/api/pagos/callback", response_model=ResponseSchema, tags=["B-13: Pagos"])
def notificar_callback_pago(input: CallbackInput, db: Session = Depends(get_db)):
    pago = db.query(PagoDB).filter(PagoDB.token == input.token).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Token de pago no válido")
    
    pedido = get_pedido_by_id(db, pago.pedido_id)
    if input.estado == "aprobado":
        pago.estado = EstadoPago.pagado
        pedido.estado = EstadoPedido.confirmado
        pedido.estadoPago = EstadoPago.pagado
    else:
        pago.estado = EstadoPago.rechazado
        pedido.estado = EstadoPedido.cancelado
        pedido.estadoPago = EstadoPago.rechazado
        
    db.commit()
    return ResponseSchema(status=200, body={"mensaje": "Callback recibido"})

@app.post("/api/pagos/reintentar", response_model=ResponseSchema, tags=["B-13: Pagos"])
def reintentar_pago(input: ReintentarPagoInput, db: Session = Depends(get_db)):
    # (Lógica similar a /iniciar)
    return ResponseSchema(status=501, body={"mensaje": "No implementado"})


# --- ENDPOINTS DE COMPROBANTES ---
@app.post("/api/comprobantes/enviar", response_model=ResponseSchema, tags=["B-14: Comprobantes"])
def enviar_comprobante(input: EnviarComprobanteInput, db: Session = Depends(get_db)):
    print(f"Enviando comprobante del pedido {input.pedidoId} a {input.email}")
    return ResponseSchema(status=200, body={"mensaje": "Comprobante enviado"})

@app.get("/api/comprobantes/{id}", response_model=ComprobanteSchema, tags=["B-14: Comprobantes"])
def ver_comprobante(id: int, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail="No implementado")

@app.get("/api/comprobantes/{id}/descargar", response_class=StreamingResponse, tags=["B-14: Comprobantes"])
def descargar_comprobante(id: int, input: DescargarComprobanteInput = Depends(), db: Session = Depends(get_db)):
    output = io.StringIO()
    output.write(f"Comprobante Ficticio ID={id}, Formato={input.formato}")
    file_content = output.getvalue()
    output.close()
    return StreamingResponse(
        io.BytesIO(file_content.encode("utf-8")),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=comprobante_{id}.txt"}
    )

@app.get("/api/usuarios/{id}/comprobantes", response_model=List[ComprobanteSchema], tags=["B-14: Comprobantes"])
def listar_comprobantes_usuario(id: int, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail="No implementado")

# --- ENDPOINTS DE ENVÍO ---
@app.post("/api/envios/calcular", response_model=CostoEnvioSchema, tags=["B-16: Envíos"])
def calcular_envio(input: CalculoEnvioInput, db: Session = Depends(get_db)):
    zona = db.query(ZonaDespachoDB).filter(ZonaDespachoDB.comuna == input.comuna).first()
    if not zona:
        raise HTTPException(status_code=404, detail="Comuna no disponible para despacho")
    
    return CostoEnvioSchema(
        comuna=zona.comuna,
        costo=zona.costo,
        tiempoEstimado=zona.tiempoEstimado
    )

# --- ENDPOINTS DE SEGUIMIENTO ---
@app.get("/api/seguimiento/{id}", response_model=SeguimientoSchema, tags=["B-17: Seguimiento"])
def obtener_seguimiento(
    id: int, # Asumimos que es el ID del Pedido
    current_user: UsuarioDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    seguimiento = db.query(SeguimientoDB).filter(SeguimientoDB.pedido_id == id).first()
    if not seguimiento:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
    
    # (Validar que el pedido pertenece al current_user)
    
    return seguimiento

@app.post("/api/seguimiento/{id}/notificar-llegada", response_model=ResponseSchema, tags=["B-17: Seguimiento"])
def notificar_llegada(id: int, input: NotificacionLlegadaInput, db: Session = Depends(get_db)):
    print(f"Notificando llegada de pedido {id} por canal {input.canalNotificacion}")
    return ResponseSchema(status=200, body={"mensaje": "Notificación enviada"})

@app.post("/api/seguimiento/{id}/calificar", response_model=SeguimientoSchema, tags=["B-17: Seguimiento"])
def calificar_entrega(
    id: int, 
    input: CalificacionInput, 
    current_user: UsuarioDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    seguimiento = db.query(SeguimientoDB).filter(SeguimientoDB.pedido_id == id).first()
    if not seguimiento:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
        
    seguimiento.puntaje = input.puntaje
    seguimiento.comentario = input.comentario
    db.commit()
    db.refresh(seguimiento)
    return seguimiento

# --- ENDPOINTS DE NOTIFICACIONES DE PEDIDO ---
@app.put("/api/pedidos/{id}/notificaciones", response_model=PedidoSchema, tags=["B-18: Notificaciones"])
def configurar_notificaciones(
    id: int, # ID del Pedido
    input: ConfiguracionNotificacionInput,
    current_user: UsuarioDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pedido = get_pedido_by_id(db, id)
    if not pedido or pedido.usuario_id != current_user.id:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
        
    pedido.notificacionCanal = input.canal
    pedido.notificacionEstados = input.estados
    pedido.notificacionNoMolestar = input.noMolestar
    db.commit()
    db.refresh(pedido)
    return pedido

@app.post("/api/pedidos/{id}/notificaciones/silenciar", response_model=ResponseSchema, tags=["B-18: Notificaciones"])
def silenciar_notificaciones(id: int, db: Session = Depends(get_db)):
    pedido = get_pedido_by_id(db, id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    pedido.notificacionNoMolestar = True
    db.commit()
    return ResponseSchema(status=200, body={"mensaje": "Notificaciones silenciadas"})

@app.post("/api/pedidos/{id}/notificaciones/reactivar", response_model=ResponseSchema, tags=["B-18: Notificaciones"])
def reactivar_notificaciones(id: int, db: Session = Depends(get_db)):
    pedido = get_pedido_by_id(db, id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    pedido.notificacionNoMolestar = False
    db.commit()
    return ResponseSchema(status=200, body={"mensaje": "Notificaciones reactivadas"})

@app.post("/api/pedidos/{id}/notificar-cambio", response_model=ResponseSchema, tags=["B-18: Notificaciones"])
def notificar_cambio_estado(id: int, input: CambioEstadoInput, db: Session = Depends(get_db)):
    # (Lógica de Admin/Sistema para notificar al usuario)
    print(f"Notificando al usuario del Pedido {id}: {input.estado} - {input.mensaje}")
    return ResponseSchema(status=200, body={"mensaje": "Notificación enviada"})


# --- Punto de entrada para ejecutar la app ---
if __name__ == "__main__":
    print("Iniciando servidor FastAPI 'Frio Natural' en http://127.0.0.1:8000")
    print("Accede a la documentación de la API en http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000)