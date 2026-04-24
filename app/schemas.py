from pydantic import BaseModel


class BusinessCreate(BaseModel):
    name: str
    phone_number: str
    whatsapp_phone_number_id: str

class ProductCreate(BaseModel):
    name_en: str
    name_ar: str
    price: int
    business_id: int  

class OrderCreate(BaseModel):
    customer_name: str
    item_name: str
    quantity: int
    business_id: int    