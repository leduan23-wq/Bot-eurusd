import os
import logging
import asyncio
import threading
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Configuración de logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Credenciales y variables de entorno
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")

# Inicializar Google Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-3.8-flash')

# Configuración de seguridad para evitar bloqueos por términos financieros
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# Inicializar Flask y la App de Telegram
app = Flask(__name__)
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

# Estado de la conversación
ASK_PHOTO = range(1)

# ---------------------------------------------------------
# FUNCIÓN DE GRÁFICO DINÁMICO
# ---------------------------------------------------------
def generar_grafico_posicion(simbolo, entrada, tp, sl):
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor('#131722')
    ax.set_facecolor('#131722')
    
    rango_base = abs(tp - sl) if tp != sl else 100
    precios = np.linspace(sl - (rango_base * 0.5), tp + (rango_base * 0.5), 10)
    x = np.arange(10)
    
    ax.plot(x, precios, color='#2962FF', linewidth=2, label='Estructura')
    
    # Líneas clave ajustadas al precio real
    ax.axhline(y=tp, color='#26a69a', linestyle='--', linewidth=1.8, label=f'TP: {tp}')
    ax.axhline(y=entrada, color='#2962FF', linestyle='-', linewidth=1.8, label=f'Entrada: {entrada}')
    ax.axhline(y=sl, color='#ef5350', linestyle='--', linewidth=1.8, label=f'SL: {sl}')
    
    # Zonas visuales
    ax.axhspan(entrada, tp, color='#26a69a', alpha=0.15)
    ax.axhspan(sl, entrada, color='#ef5350', alpha=0.15)
    
    ax.tick_params(colors='white')
    for spine in ax.spines.values():
        spine.set_color('#363c4e')
    ax.set_title(f'Niveles Óptimos El Sensei Trading ({simbolo.upper()})', color='white', fontsize=12, pad=10)
    ax.legend(facecolor='#131722', edgecolor='#363c4e', labelcolor='white', loc='upper left')
    
    ruta_imagen = 'analisis_ia.png'
    plt.savefig(ruta_imagen, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    return ruta_imagen

# ---------------------------------------------------------
# MENÚ DE BOTONES INTERACTIVOS CON TODOS LOS ACTIVOS
# ---------------------------------------------------------
async def start(update: Update, context):
    user_name = update.effective_user.first_name if update.effective_user else "Trader"
    
    keyboard = [
        [InlineKeyboardButton("💱 EURUSD", callback_data="asset_EURUSD"), InlineKeyboardButton("💱 USDJPY", callback_data="asset_USDJPY")],
        [InlineKeyboardButton("🪙 BTCUSD", callback_data="asset_BTCUSD"), InlineKeyboardButton("🪙 BTCUSDT", callback_data="asset_BTCUSDT")],
        [InlineKeyboardButton("🪙 BTCUSDC", callback_data="asset_BTCUSDC"), InlineKeyboardButton("💱 USDCAD", callback_data="asset_USDCAD")],
        [InlineKeyboardButton("🥇 GOLD", callback_data="asset_GOLD"), InlineKeyboardButton("🥈 SILVER", callback_data="asset_SILVER")],
        [InlineKeyboardButton("📈 AAPL", callback_data="asset_AAPL"), InlineKeyboardButton("📊 META", callback_data="asset_META")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    bienvenida = (
        f"¡Hola, {user_name}! 🤖📊\n\n"
        "Bienvenido a tu asistente de trading
