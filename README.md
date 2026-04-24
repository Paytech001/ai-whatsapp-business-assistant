# AI WhatsApp Business Assistant

This project is an AI-powered WhatsApp assistant for cafés and restaurants.

## Features
- English and Arabic support
- Dynamic menu system
- Order using text or numbers
- Quantity handling
- AI-powered order understanding and user Input
- Stores orders in database

## Demo
See attached video.

## Setup

1. Clone project
2. Install requirements:
   pip install -r requirements.txt

3. Get the required tokens and API in `.env`

4. Run server:
   uvicorn app.main:app --reload

## Note
This project uses WhatsApp Cloud API in test mode, which restricts messaging to approved numbers.