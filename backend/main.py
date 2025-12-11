from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
import sqlite3
import requests
import json
import re
import random
from typing import List, Optional

app = FastAPI(title="🤡 Шапиро ИИ API")

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==== КОНФИГУРАЦИЯ (твои настройки) ====
JAN_API_URL = "http://localhost:1337/v1/chat/completions"  # ← ИЗМЕНИ НА СВОЙ!
JAN_AUTH_TOKEN = "bombom123"  # ← ИЗМЕНИ!
MODEL_NAME = "Llama-3_2-1B-Instruct_IQ4_XS"
TEST_PROMO_CODE = "TEST123"
STARTING_PRICE = 50
LORD_APPEALS = [
    "Мой повелитель", "Ваше величество", "Мой господин", "Ваше сиятельство",
    "О великий", "Мой властелин", "Ваша светлость", "О мудрый правитель"
]
SYSTEM_PROMPT = """Ты — полезный ассистент. Ты отвечаешь только на русском языке.
Твои ответы должны быть короткими, точными и фактическими.
Запрещено использовать английские слова."""

# ==== МОДЕЛИ ====
class ChatRequest(BaseModel):
    user_id: int
    message: str

class ChatResponse(BaseModel):
    answer: str
    lord_appeal: Optional[str] = None

class AuctionResponse(BaseModel):
    lord_id: Optional[int]
    lord_username: Optional[str]
    price: int
    time_left: str

# ==== БАЗА ДАННЫХ (твоя логика) ====
def init_db():
    conn = sqlite3.connect('shapiro.db')
    cursor = conn.cursor()
    
    # Твои таблицы (упрощенные)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS auction_state (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        current_lord_id INTEGER,
        current_lord_username TEXT,
        current_price INTEGER DEFAULT 50,
        lord_until TIMESTAMP
    )
    ''')
    cursor.execute('INSERT OR IGNORE INTO auction_state (id) VALUES (1)')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS message_history (
        user_id INTEGER,
        role TEXT,
        content TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bot_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        question TEXT,
        answer TEXT,
        usage_count INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# ==== ТВОИ ФУНКЦИИ (перенесены) ====
def get_auction_state():
    conn = sqlite3.connect('shapiro.db')
    cursor = conn.cursor()
    cursor.execute('SELECT current_lord_id, current_lord_username, current_price, lord_until FROM auction_state WHERE id = 1')
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'lord_id': result[0],
            'lord_username': result[1],
            'price': result[2],
            'lord_until': datetime.fromisoformat(result[3]) if result[3] else None
        }
    return {'lord_id': None, 'lord_username': None, 'price': STARTING_PRICE, 'lord_until': None}

def update_auction_state(lord_id, lord_username, price):
    lord_until = datetime.now() + timedelta(hours=24)
    conn = sqlite3.connect('shapiro.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE auction_state 
        SET current_lord_id = ?, current_lord_username = ?, current_price = ?, lord_until = ?
        WHERE id = 1
    ''', (lord_id, lord_username, price, lord_until.isoformat()))
    conn.commit()
    conn.close()

def get_stupid_answer(user_id: int, question: str) -> str:
    try:
        # Поиск в памяти (упрощенный)
        conn = sqlite3.connect('shapiro.db')
        cursor = conn.cursor()
        cursor.execute('SELECT answer FROM bot_memory WHERE user_id = ? AND question LIKE ? LIMIT 1',
                      (user_id, f'%{question[:20]}%'))
        memory = cursor.fetchone()
        conn.close()
        
        if memory:
            return memory[0]
        
        # Запрос к JAN AI
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": question}]
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 100
        }
        
        headers = {"Authorization": f"Bearer {JAN_AUTH_TOKEN}", "Content-Type": "application/json"}
        response = requests.post(JAN_API_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            answer = response.json()["choices"][0]["message"]["content"].strip()
            # Сохраняем в память
            conn = sqlite3.connect('shapiro.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO bot_memory (user_id, question, answer) VALUES (?, ?, ?)',
                          (user_id, question, answer))
            conn.commit()
            conn.close()
            return answer
        else:
            return "🤡 Мой мозг перегрелся! Спроси по-другому!"
            
    except Exception as e:
        return f"😵 Ошибка: {str(e)}"

# ==== API ENDPOINTS ====
@app.get("/")
def root():
    return {"message": "🤡 Шапиро ИИ API работает!"}

@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    answer = get_stupid_answer(request.user_id, request.message)
    
    # Проверяем повелителя
    auction = get_auction_state()
    lord_appeal = None
    if auction['lord_id'] == request.user_id:
        lord_appeal = random.choice(LORD_APPEALS)
        answer = f"{lord_appeal}! {answer}"
    
    return ChatResponse(answer=answer, lord_appeal=lord_appeal)

@app.get("/api/auction", response_model=AuctionResponse)
def auction():
    state = get_auction_state()
    time_left = "Трон пустует!"
    if state['lord_until'] and datetime.now() < state['lord_until']:
        delta = state['lord_until'] - datetime.now()
        hours = int(delta.total_seconds() // 3600)
        mins = int((delta.total_seconds() % 3600) // 60)
        time_left = f"{hours}ч {mins}м"
    
    return AuctionResponse(
        lord_id=state['lord_id'],
        lord_username=state['lord_username'],
        price=state['price'],
        time_left=time_left
    )

@app.post("/api/buy")
def buy_lord(user_id: int, username: str):
    state = get_auction_state()
    update_auction_state(user_id, username, state['price'] + 50)
    return {"success": True, "message": f"👑 @{username} — новый ПОВЕЛИТЕЛЬ!"}

@app.get("/api/profile/{user_id}")
def profile(user_id: int):
    conn = sqlite3.connect('shapiro.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM bot_memory WHERE user_id = ?', (user_id,))
    memories = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM message_history WHERE user_id = ?', (user_id,))
    messages = cursor.fetchone()[0]
    conn.close()
    return {"memories": memories, "messages": messages}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
