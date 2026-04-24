from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone_number = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    whatsapp_phone_number_id = Column(String, unique=True, nullable=True)



class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name_en = Column(String, nullable=False)
    name_ar = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    business_id = Column(Integer, ForeignKey("businesses.id"))  

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, nullable=False)
    item_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    business_id = Column(Integer, ForeignKey("businesses.id"))    