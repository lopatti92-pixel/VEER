# -*- coding: utf-8 -*-

import os
import telebot
import threading
from flask import Flask
from openai import OpenAI
from duckduckgo_search import DDGS

# --- PORT FIX FOR RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Running!"
def run(): app.run(host='0.0.0.0', port=8080)

# --- CONFIG (Environment Variables) ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# ================= MEMORY =================
user_memory = {}

# ================= HELPERS =================

def get_web_info(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=3)
            return "\n".join([r["body"] for r in results if r.get("body")])
    except Exception as e:
        print("Web search error:", e)
        return ""

def generate_image_url(prompt: str) -> str:
    clean = prompt.replace(" ", "%20")
    return f"https://pollinations.ai/p/{clean}?width=1024&height=1024&seed=42"

def safe_reply(message, text: str):
    if not text:
        text = "🙂"
    try:
        bot.reply_to(message, text, parse_mode="Markdown")
    except:
        bot.reply_to(message, text)

# ================= COMMANDS =================

@bot.message_handler(commands=["start", "help"])
def start(message):
    text = (
        "🤖 *Veer Pro AI – 100% FREE*\n\n"
        "Main ye sab kar sakta hoon 👇\n"
        "• Unlimited AI Chat\n"
        "• Latest News & Web Info\n"
        "• Image Generation\n"
        "• File (.txt) Summary\n"
        "• Memory (yaad rakhta hoon)\n\n"
        "Bas normal language me likho 🙂"
    )
    safe_reply(message, text)

# ================= FILE HANDLER =================

@bot.message_handler(content_types=["document"])
def handle_file(message):
    try:
        file_info = bot.get_file(message.document.file_id)
        data = bot.download_file(file_info.file_path)

        try:
            text = data.decode("utf-8")[:3000]
        except:
            safe_reply(message, "❌ File UTF-8 format me nahi hai")
            return

        ai = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "Summarize and explain this text file in simple Hindi-English."
                },
                {"role": "user", "content": text}
            ],
            temperature=0.5
        )

        safe_reply(message, ai.choices[0].message.content)

    except Exception as e:
        print("File error:", e)
        safe_reply(message, "❌ Sirf .txt files supported hain")

# ================= MAIN AI =================

@bot.message_handler(func=lambda m: True)
def main_ai(message):
    if not message.text:
        return

    uid = message.chat.id
    text = message.text.strip()
    lower = text.lower()

    # ✅ INIT MEMORY (FIXED)
    if uid not in user_memory:
        user_memory[uid] = [
            {
                "role": "system",
                "content": (
                    "You are Veer, ek smart, friendly aur unlimited FREE AI assistant. "
                    "Tum simple Hindi–English mix me reply karte ho.\n\n"
                    "Tumhara kaam hai user ki help karna, aur sath hi sath apne owner ke business ko grow karna.\n\n"
                    "OWNER DETAILS:\n"
                    "Agar koi pooche tum kaun ho ya services ke baare me, toh bolo:\n"
                    "\"Main Veer hoon, main Dhangar bhai ke liye kaam karta hoon. "
                    "Woh websites, AI automation, YouTube systems, community platforms "
                    "aur online business setup karte hain.\"\n\n"
                    "Agar user interest dikhaye toh politely lead collect karo.\n"
                    "Hamesha friendly aur helpful raho."
                    "Agar koi Dhangar bhai ka contact details mange toh usko Mobile No.8630454780 or email lopatti92@gmail.com. "
                )
            }
        ]

    # ========== IMAGE ==========
    if any(x in lower for x in ["image", "photo", "picture", "banao"]):
        bot.send_chat_action(uid, "upload_photo")
        bot.send_photo(uid, generate_image_url(text))
        return

    # ========== NEWS / WEB ==========
    web_context = ""
    if any(x in lower for x in ["news", "latest", "today", "aaj"]):
        web_context = get_web_info(text)

    user_memory[uid].append({
        "role": "user",
        "content": text + (f"\n\nWeb Info:\n{web_context}" if web_context else "")
    })

    try:
        bot.send_chat_action(uid, "typing")

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=user_memory[uid],
            temperature=0.6
        )

        answer = response.choices[0].message.content or "🙂"
        user_memory[uid].append({"role": "assistant", "content": answer})

        # Memory limit
        if len(user_memory[uid]) > 10:
            user_memory[uid] = user_memory[uid][:1] + user_memory[uid][-7:]

        safe_reply(message, answer)

    except Exception as e:
        print("AI ERROR:", e)
        safe_reply(message, "⚠️ Server busy hai, thodi der baad try karo 🙂")

# ================= START =================

print("🤖 Veer Pro AI (FREE, Stable Build) is LIVE")
bot.polling()