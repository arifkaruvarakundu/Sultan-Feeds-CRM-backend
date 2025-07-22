from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, ForeignKey, DateTime, Index, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    user_type = Column(String, default="admin")  # or "user"

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, index=True, nullable=True)
    phone = Column(String, unique=True, index=True)
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")
    address = relationship("Address", back_populates="customer", uselist=False, cascade="all, delete-orphan")

class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)

    company = Column(String)
    address_1 = Column(String)
    address_2 = Column(String)
    city = Column(String)
    state = Column(String)
    postcode = Column(String)
    country = Column(String)

    customer = relationship("Customer", back_populates="address")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)  # internal DB id
    external_id = Column(BigInteger, unique=True, index=True, nullable=True)  # WooCommerce ID (previously `order_id`)
    order_key = Column(String, unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"))
    status = Column(String, nullable=False)
    total_amount = Column(Float, nullable=False)
    created_at = Column(DateTime, index=True, nullable=False)
    payment_method = Column(String, nullable=True)

    attribution_referrer = Column(String, nullable=True)
    session_pages = Column(Integer, nullable=True)
    session_count = Column(Integer, nullable=True)
    device_type = Column(String, nullable=True)

    customer = relationship("Customer", back_populates="orders", passive_deletes=True)
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(BigInteger, unique=True, index=True, nullable=True)
    name = Column(String, nullable=False)
    short_description = Column(Text, nullable=True)
    regular_price = Column(Float, nullable=True)
    sales_price = Column(Float, nullable=True)
    total_sales = Column(Integer, nullable=True)
    categories = Column(String, nullable=True)  # stringified list or JSON
    stock_status = Column(String, nullable=True)
    weight = Column(Float, nullable=True)

    date_created = Column(DateTime, nullable=True)
    date_modified = Column(DateTime, nullable=True)

    # ✅ Relationship back to OrderItem
    order_items = relationship("OrderItem", back_populates="product")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    product_id = Column(Integer, ForeignKey("products.external_id", ondelete="SET NULL"))  # ✅ This is essential
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items", passive_deletes=True)
    
    # ✅ Relationship to Product
    product = relationship("Product", back_populates="order_items")

class SyncState(Base):
    __tablename__ = "sync_state"
    key = Column(String, primary_key=True)
    value = Column(String)