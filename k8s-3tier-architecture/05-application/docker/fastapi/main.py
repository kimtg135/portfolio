"""
Shop API - FastAPI 쇼핑몰 백엔드

API 구조:
  /health                    - 헬스체크
  /api/auth/register         - 회원가입
  /api/auth/login            - 로그인 (JWT 발급)
  /api/products              - 상품 목록 (검색, 카테고리 필터)
  /api/products/{id}         - 상품 상세
  /api/orders                - 주문 생성 / 주문 내역 조회
  /api/admin/products        - [Admin] 상품 등록
  /api/admin/products/{id}   - [Admin] 상품 수정/삭제
  /api/admin/orders          - [Admin] 주문 현황 조회
  /api/admin/orders/{id}     - [Admin] 주문 상태 변경 (취소 포함)
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, BigInteger, String, Text, Numeric, Integer, Boolean, Enum, ForeignKey, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from passlib.context import CryptContext
from jose import jwt
from pydantic import BaseModel, EmailStr
import redis

# ─── 설정 ───────────────────────────────────────────────
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "shop_db")
DB_USER = os.getenv("DB_USER", "shop_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Shop_Pass_456")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-key")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost").split(",")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"])
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# ─── Models ─────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(Enum("user", "admin"), default="user")
    created_at = Column(DateTime, default=func.now())
    orders = relationship("Order", back_populates="user")

class Product(Base):
    __tablename__ = "products"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    stock = Column(Integer, default=0)
    category = Column(String(100))
    image_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

class Order(Base):
    __tablename__ = "orders"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    status = Column(Enum("pending", "confirmed", "shipping", "delivered", "cancelled"), default="pending")
    total_amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=func.now())
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_id = Column(BigInteger, ForeignKey("orders.id"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    order = relationship("Order", back_populates="items")
    product = relationship("Product")

# ─── Schemas ────────────────────────────────────────────
class UserRegister(BaseModel):
    email: str
    password: str
    name: str

class UserLogin(BaseModel):
    email: str
    password: str

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock: int
    category: Optional[str] = None
    image_url: Optional[str] = None

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int

class OrderCreate(BaseModel):
    items: list[OrderItemCreate]

class OrderStatusUpdate(BaseModel):
    status: str

# ─── App ────────────────────────────────────────────────
app = FastAPI(title="Shop API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_token(user_id: int, role: str) -> str:
    payload = {"sub": str(user_id), "role": role, "exp": datetime.utcnow() + timedelta(hours=24)}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def get_current_user(token: str = Depends(), db: Session = Depends(get_db)):
    """Authorization 헤더에서 JWT를 검증하고 유저 반환"""
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    # 이 함수는 아래 의존성에서 오버라이드됨
    pass

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        user = db.query(User).filter(User.id == int(payload["sub"])).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# ─── Health ─────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}

# ─── Auth ───────────────────────────────────────────────
@app.post("/api/auth/register")
def register(data: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=data.email, password_hash=pwd_context.hash(data.password), name=data.name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "name": user.name}

@app.post("/api/auth/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not pwd_context.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user.id, user.role)
    return {"access_token": token, "token_type": "bearer", "role": user.role}

# ─── Products (User) ───────────────────────────────────
@app.get("/api/products")
def list_products(
    search: Optional[str] = None,
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Product).filter(Product.is_active == True)
    if search:
        query = query.filter(Product.name.contains(search))
    if category:
        query = query.filter(Product.category == category)
    total = query.count()
    products = query.offset((page - 1) * size).limit(size).all()
    return {
        "total": total,
        "page": page,
        "items": [{"id": p.id, "name": p.name, "price": float(p.price), "stock": p.stock, "category": p.category, "image_url": p.image_url} for p in products]
    }

@app.get("/api/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    # Redis 캐시 조회
    cached = redis_client.get(f"product:{product_id}")
    if cached:
        import json
        return json.loads(cached)

    product = db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    result = {"id": product.id, "name": product.name, "description": product.description, "price": float(product.price), "stock": product.stock, "category": product.category, "image_url": product.image_url}

    # Redis 캐시 저장 (5분)
    import json
    redis_client.setex(f"product:{product_id}", 300, json.dumps(result))
    return result

# ─── Orders (User) ─────────────────────────────────────
@app.post("/api/orders")
def create_order(data: OrderCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total = 0
    order_items = []
    for item in data.items:
        product = db.query(Product).filter(Product.id == item.product_id, Product.is_active == True).first()
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} not found")
        if product.stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {product.name}")
        product.stock -= item.quantity
        total += float(product.price) * item.quantity
        order_items.append(OrderItem(product_id=item.product_id, quantity=item.quantity, price=product.price))

    order = Order(user_id=user.id, total_amount=total, items=order_items)
    db.add(order)
    db.commit()
    db.refresh(order)
    return {"id": order.id, "total_amount": float(order.total_amount), "status": order.status}

@app.get("/api/orders")
def my_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.user_id == user.id).order_by(Order.created_at.desc()).all()
    return [{"id": o.id, "status": o.status, "total_amount": float(o.total_amount), "created_at": str(o.created_at), "items": [{"product_id": i.product_id, "quantity": i.quantity, "price": float(i.price)} for i in o.items]} for o in orders]

# ─── Admin: Products ───────────────────────────────────
@app.post("/api/admin/products")
def admin_create_product(data: ProductCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return {"id": product.id, "name": product.name}

@app.put("/api/admin/products/{product_id}")
def admin_update_product(product_id: int, data: ProductCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for key, value in data.model_dump().items():
        setattr(product, key, value)
    db.commit()
    redis_client.delete(f"product:{product_id}")
    return {"id": product.id, "name": product.name}

@app.delete("/api/admin/products/{product_id}")
def admin_delete_product(product_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_active = False
    db.commit()
    redis_client.delete(f"product:{product_id}")
    return {"message": "Product deactivated"}

# ─── Admin: Orders ─────────────────────────────────────
@app.get("/api/admin/orders")
def admin_list_orders(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)
    total = query.count()
    orders = query.order_by(Order.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "total": total,
        "page": page,
        "items": [{"id": o.id, "user_id": o.user_id, "status": o.status, "total_amount": float(o.total_amount), "created_at": str(o.created_at)} for o in orders]
    }

@app.patch("/api/admin/orders/{order_id}")
def admin_update_order_status(order_id: int, data: OrderStatusUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    valid_statuses = ["pending", "confirmed", "shipping", "delivered", "cancelled"]
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    # 취소 시 재고 복구
    if data.status == "cancelled" and order.status != "cancelled":
        for item in order.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.stock += item.quantity
    order.status = data.status
    db.commit()
    return {"id": order.id, "status": order.status}
