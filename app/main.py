from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.database import Base, engine, SessionLocal
from app.models import Business, Product, Order
from app.schemas import BusinessCreate, ProductCreate, OrderCreate
from fastapi import Request
from fastapi.responses import PlainTextResponse

# ENV
from dotenv import load_dotenv
import os
import json
import requests

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OPENAI
from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI()

Base.metadata.create_all(bind=engine)

user_sessions = {}

# ===== HELPER FUNCTIONS =====

def clean_message_text(text: str):
    arabic_digits = {
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
    }

    text = text.replace("\u200f", "").replace("\u200e", "").strip()

    for ar, en in arabic_digits.items():
        text = text.replace(ar, en)

    return text

@app.get("/")
def root():
    return {"message": "Backend is running successfully 🚀"}


@app.post("/businesses")
def create_business(business: BusinessCreate):
    db: Session = SessionLocal()

    new_business = Business(
        name=business.name,
        phone_number=business.phone_number,
        whatsapp_phone_number_id=business.whatsapp_phone_number_id
    )

    db.add(new_business)
    db.commit()
    db.refresh(new_business)
    db.close()

    return {
        "id": new_business.id,
        "name": new_business.name,
        "phone_number": new_business.phone_number,
        "is_active": new_business.is_active,
        "whatsapp_phone_number_id": new_business.whatsapp_phone_number_id
    }


@app.get("/businesses")
def get_businesses():
    db: Session = SessionLocal()

    businesses = db.query(Business).all()

    db.close()

    return businesses

@app.post("/products")
def create_product(product: ProductCreate):
    db: Session = SessionLocal()

    new_product = Product(
        name_en=product.name_en,
        name_ar=product.name_ar,
        price=product.price,
        business_id=product.business_id
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    db.close()

    return {
        "id": new_product.id,
        "name_en": new_product.name_en,
        "name_ar": new_product.name_ar,
        "price": new_product.price,
        "business_id": new_product.business_id
    }

@app.get("/products/{business_id}")
def get_products(business_id: int):
    db: Session = SessionLocal()

    products = db.query(Product).filter(Product.business_id == business_id).all()
    business = db.query(Business).filter(Business.id == business_id).first()

    db.close()

    if not business:
        return {"message": "Business not found"}

    if not products:
        return {"message": "No products found"}

    menu_text = f"Welcome to {business.name} ☕\n\n"

    for i, product in enumerate(products, start=1):
        menu_text += f"{i}. {product.name} - {product.price} SAR\n"

    return {"menu": menu_text}

@app.post("/orders")
def create_order(order: OrderCreate):
    db: Session = SessionLocal()

    new_order = Order(
        customer_name=order.customer_name,
        item_name=order.item_name,
        quantity=order.quantity,
        business_id=order.business_id
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    db.close()

    return {
        "message": "Order placed successfully ✅",
        "order_id": new_order.id
    }

@app.get("/orders/{business_id}")
def get_orders(business_id: int):
    db: Session = SessionLocal()

    orders = db.query(Order).filter(Order.business_id == business_id).all()

    db.close()

    if not orders:
        return {"message": "No orders yet"}

    order_list = []

    for order in orders:
        order_list.append({
            "customer": order.customer_name,
            "item": order.item_name,
            "quantity": order.quantity
        })

    return {"orders": order_list}

@app.post("/chat")
def chat(message: str, business_id: int, customer_name: str):
    db: Session = SessionLocal()

    products = db.query(Product).filter(Product.business_id == business_id).all()
    business = db.query(Business).filter(Business.id == business_id).first()

    if not business:
        db.close()
        return {"message": "Business not found"}

    if not products:
        db.close()
        return {"message": "No products found for this business"}

    business_name = business.name

    menu_list = [product.name for product in products]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a smart cafe ordering assistant. "
                    "The customer may make spelling mistakes. "
                    "From the user's message, detect the intended menu item and quantity. "
                    "Only choose from this menu: " + ", ".join(menu_list) + ". "
                    "Return only valid JSON in this format: "
                    '{"item_name": "Latte", "quantity": 2}'
                )
            },
            {
                "role": "user",
                "content": message
            }
        ]
    )

    ai_reply = response.choices[0].message.content.strip()

    try:
        parsed = json.loads(ai_reply)
        item_name = parsed["item_name"]
        quantity = parsed["quantity"]
    except Exception:
        db.close()
        return {
            "message": "AI response could not be parsed",
            "raw_ai_response": ai_reply
        }

    matched_product = db.query(Product).filter(
        Product.business_id == business_id,
        Product.name == item_name
    ).first()

    if not matched_product:
        db.close()
        return {
            "message": "Matched product not found in database",
            "ai_detected_item": item_name
        }
    product_name = matched_product.name

    new_order = Order(
        customer_name=customer_name,
        item_name=product_name,
        quantity=quantity,
        business_id=business_id
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    db.close()

    return {
        "message": "Order placed successfully ✅",
        "business": business_name,
        "customer_name": customer_name,
        "item_name": product_name,
        "quantity": quantity,
        "order_id": new_order.id
    }

WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

def send_whatsapp_text(to_phone: str, text: str):
    url = f"https://graph.facebook.com/v25.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {
            "body": text
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    print("SEND RESPONSE:", response.status_code, response.text)


def detect_language(text: str):
    for ch in text:
        if '\u0600' <= ch <= '\u06FF':
            return "ar"
    return "en"
    

def process_ai_order(message: str, business_id: int, customer_name: str, language: str = "en"):
    db: Session = SessionLocal()

    products = db.query(Product).filter(Product.business_id == business_id).all()
    business = db.query(Business).filter(Business.id == business_id).first()
    business_name = business.name if business else "Unknown"
    business_name = business_name

    if not business:
        db.close()
        return {"message": "Business not found"}

    if not products:
        db.close()
        return {"message": "No products found for this business"}

    business_name = business_name
    menu_list = [product.name_en for product in products]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """
            You are a smart restaurant assistant.

            Your job is to extract an order from a message.

            The message may be in English, Arabic, or mixed.

            Examples:
            - "I want 2 latte"
            - "2 latte please"
            - "ابغى 2 لاتيه"
            - "عايز لاتيه"
            - "latte 2"

            You must extract:
            - product name
            - quantity

            Return ONLY in this JSON format:
            {
            "product_name": "latte",
            "quantity": 2
            }

            Rules:
            - If quantity is missing, assume 1
            - Normalize product names to lowercase English if possible
            - If unclear, still try your best guess
            """
            },
            {
                "role": "user",
                "content": message
            }
        ]
    )

    ai_reply = response.choices[0].message.content.strip()
    print("AI REPLY:", ai_reply)

    try:
        parsed = json.loads(ai_reply)
        item_name = parsed["product_name"]
        quantity = parsed["quantity"]
    except Exception:
        db.close()
        return {
            "message": "Sorry, I could not understand your order."
        }

    matched_product = db.query(Product).filter(
        Product.business_id == business_id,
        Product.name_en.ilike(item_name)
    ).first()

    if not matched_product:
        db.close()
        return {
            "message": f"Sorry, I could not find {item_name} on the menu."
        }

    product_name_en = matched_product.name_en
    product_name_ar = matched_product.name_ar

    new_order = Order(
        customer_name=customer_name,
        item_name=product_name_en,
        quantity=quantity,
        business_id=business_id
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    order_id = new_order.id
    db.close()

    if language == "ar":
        message_text = (
            "تم تنفيذ الطلب بنجاح ✅\n"
            f"المتجر: {business_name}\n"
            f"الصنف: {product_name_ar}\n"
            f"الكمية: {quantity}\n"
            f"رقم الطلب: {new_order.id}"
        )
    else:
        message_text = (
            "Order placed successfully ✅\n"
            f"Business: {business_name}\n"
            f"Item: {product_name_en}\n"
            f"Quantity: {quantity}\n"
            f"Order ID: {new_order.id}"
        )

    return {
        "message": message_text
    }

@app.post("/webhook")
async def receive_webhook(request: Request):
    body = await request.json()
    print("WEBHOOK RECEIVED:", body)

    try:
        entry = body["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        if "messages" in value:
            message = value["messages"][0]
            from_phone = message["from"]

            if message["type"] == "text":
                incoming_text = message["text"]["body"]
                incoming_text = clean_message_text(incoming_text)
                language = detect_language(incoming_text)
                

                incoming_phone_number_id = value["metadata"]["phone_number_id"]

                db = SessionLocal()
                business = db.query(Business).filter(
                    Business.whatsapp_phone_number_id == incoming_phone_number_id
                ).first()
                db.close()

                if not business:
                    send_whatsapp_text(
                        to_phone=from_phone,
                        text="Business not found for this WhatsApp number."
                    )
                    return {"status": "received"}
                text_lower = incoming_text.lower()

                text = incoming_text.strip()

                if from_phone in user_sessions:
                    parts = text.split()

                    # Case 1: user sends "1" → ask for quantity
                    # Case 1: user sends menu number → ask for quantity
                    if len(parts) == 1 and parts[0].isdigit() and "pending_item" not in user_sessions[from_phone]:
                        selected_index = int(parts[0]) - 1
                        menu_items = user_sessions[from_phone]["menu_items"]
                        language = user_sessions[from_phone]["language"]

                        if 0 <= selected_index < len(menu_items):
                            selected_item = menu_items[selected_index]

                            # save pending selection
                            user_sessions[from_phone]["pending_item"] = selected_item

                            if language == "ar":
                                send_whatsapp_text(
                                    to_phone=from_phone,
                                    text=f"كم عدد {selected_item}؟"
                                )
                            else:
                                send_whatsapp_text(
                                    to_phone=from_phone,
                                    text=f"How many {selected_item} would you like?"
                                )

                            return {"status": "awaiting_quantity"}

                    # Case 2: user sends "1 3" → order directly
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        selected_index = int(parts[0]) - 1
                        quantity = int(parts[1])
                        menu_items = user_sessions[from_phone]["menu_items"]

                        if 0 <= selected_index < len(menu_items):
                            selected_item = menu_items[selected_index]

                            result = process_ai_order(
                                message=f"I want {quantity} {selected_item}",
                                business_id=business.id,
                                customer_name="WhatsApp Customer"
                            )

                            send_whatsapp_text(
                                to_phone=from_phone,
                                text=result["message"]
                            )

                            return {"status": "number_quantity_order"}
                        
                # Case 3: user previously selected item and now sends quantity
                if from_phone in user_sessions and "pending_item" in user_sessions[from_phone]:
                    if incoming_text.strip().isdigit():
                        quantity = int(incoming_text.strip())
                        selected_item = user_sessions[from_phone]["pending_item"]

                        language = user_sessions[from_phone]["language"]
                        result = process_ai_order(
                            message=f"I want {quantity} {selected_item}",
                            business_id=business.id,
                            customer_name="WhatsApp Customer",
                            language=language
                        )

                        # clear pending item
                        del user_sessions[from_phone]["pending_item"]

                        send_whatsapp_text(
                            to_phone=from_phone,
                            text=result["message"]
                        )

                        return {"status": "quantity_completed"}

                if (
                    any(word in text_lower for word in ["hi", "hello", "hey", "menu", "start"])
                    or any(word in incoming_text for word in ["مرحبا", "اهلا", "القائمة", "ابدأ"])
                ):
                    db = SessionLocal()
                    products = db.query(Product).filter(
                        Product.business_id == business.id
                    ).all()
                    db.close()
                    user_sessions[from_phone] = {
                        "language": language,
                        "menu_items": [p.name_en for p in products]
                    }

                    if not products:
                        if language == "ar":
                            menu_text = "القائمة فارغة حالياً."
                        else:
                            menu_text = "Menu is currently empty."
                    else:
                        if language == "ar":
                            menu_text = "☕ القائمة:\n\n"
                        else:
                            menu_text = "☕ Menu:\n\n"

                        for i, p in enumerate(products, start=1):
                            if language == "ar":
                                menu_text += f"{i}. {p.name_ar} - {p.price} ريال\n"
                            else:
                                menu_text += f"{i}. {p.name_en} - {p.price} SAR\n"

                    if language == "ar":
                        menu_text += "\n👉 يمكنك الطلب مثل:\nأبغى 2 لاتيه"
                    else:
                        menu_text += "\n👉 You can order like:\nI want 2 latte"

                    send_whatsapp_text(
                        to_phone=from_phone,
                        text=menu_text
                    )

                    return {"status": "menu_sent"}

                result = process_ai_order(
                    message=incoming_text,
                    business_id=business.id,
                    customer_name="WhatsApp Customer"
                )

                send_whatsapp_text(
                    to_phone=from_phone,
                    text=result["message"]
                )

    except Exception as e:
        print("WEBHOOK ERROR:", str(e))

    return {"status": "received"}