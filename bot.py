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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

# Estados del flujo interactivo
ASK_DETAILS, ASK_PHOTO = range(2)

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
    ax.set_title(f'Niveles Óptimos ICT ({simbolo.upper()})', color='white', fontsize=12, pad=10)
    ax.legend(facecolor='#131722', edgecolor='#363c4e', labelcolor='white', loc='upper left')
    
    ruta_imagen = 'analisis_ia.png'
    plt.savefig(ruta_imagen, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    return ruta_imagen

# ---------------------------------------------------------
# MANEJADORES DEL FLUJO INTERACTIVO (CONVERSATION HANDLER)
# ---------------------------------------------------------
async def start(update: Update, context):
    user_name = update.effective_user.first_name
    keyboard = [[InlineKeyboardButton("📊 Analizar Gráfico TradingView", callback_data="start_analysis")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    bienvenida = (
        f"¡Hola, {user_name}! 🤖📊\n\n"
        "Tu bot autónomo con **Gemini IA** está listo.\n"
        "Presiona el botón de abajo para iniciar el análisis interactivo de tu captura de TradingView."
    )
    await update.message.reply_text(bienvenida, reply_markup=reply_markup, parse_mode="Markdown")
    return ConversationHandler.END

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "start_analysis":
        await query.message.reply_text(
            "1️⃣ **Paso 1:** Por favor, ingresa los **datos esenciales** antes de enviar la captura "
            "(Ejemplo: `BTC-USD, 1m, Busco Compra en Order Block`):",
            parse_mode="Markdown"
        )
        return ASK_DETAILS

async def receive_details(update: Update, context):
    context.user_data['trade_details'] = update.message.text
    await update.message.reply_text(
        "2️⃣ **Paso 2:** ¡Datos esenciales guardados!\n"
        "Ahora **envía la captura de pantalla de tu TradingView** para que la IA realice los cálculos finales.",
        parse_mode="Markdown"
    )
    return ASK_PHOTO

async def receive_photo_and_analyze(update: Update, context):
    try:
        details = context.user_data.get('trade_details', 'No especificado')
        await update.message.reply_text("🤖 Analizando la captura de pantalla, cruzando tus datos esenciales y calculando niveles ICT con precios reales...")
        
        foto_archivo = await update.message.photo[-1].get_file()
        foto_bytes = await foto_archivo.download_as_bytearray()
        
        imagen_part = {'mime_type': 'image/jpeg', 'data': bytes(foto_bytes)}
        
        prompt_vision = (
            f"Actúa como un trader institucional experto en metodología ICT. "
            f"El usuario proporcionó estos datos esenciales previos: '{details}'. "
            f"Analiza la captura de pantalla adjunta de TradingView basándote en el precio real visible y los datos indicados. "
            f"Calcula con precisión los niveles óptimos. "
            f"Debes incluir obligatoriamente al final de tu respuesta los valores numéricos exactos en este formato estricto:\n"
            f"ENTRADA: [número]\n"
            f"TP: [número]\n"
            f"SL: [número]"
        )
        
        respuesta = model.generate_content([prompt_vision, imagen_part], safety_settings=safety_settings)
        texto_respuesta = respuesta.text
        
        # Valores de respaldo predeterminados
        entrada, tp, sl = 80750.00, 80900.00, 80600.00
        
        match_ent = re.search(r"ENTRADA:\s*([\d\.]+)", texto_respuesta, re.IGNORECASE)
        match_tp = re.search(r"TP:\s*([\d\.]+)", texto_respuesta, re.IGNORECASE)
        match_sl = re.search(r"SL:\s*([\d\.]+)", texto_respuesta, re.IGNORECASE)
        
        if match_ent: entrada = float(match_ent.group(1))
        if match_tp: tp = float(match_tp.group(1))
        if match_sl: sl = float(match_sl.group(1))
        
        # Generar gráfico dinámico
        ruta_grafico = generar_grafico_posicion("TradingView Setup", entrada, tp, sl)
        
        # Enviar foto del gráfico
        with open(ruta_grafico, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption="📈 **Gráfico ICT con Niveles Calculados**",
                parse_mode="Markdown"
            )
            
        # Enviar análisis detallado y validación de datos
        await update.message.reply_text(
            f"📋 **Análisis y Validación de Datos Esenciales:**\n\n{texto_respuesta}",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error procesando análisis interactivo: {e}", exc_info=True)
        await update.message.reply_text(f"Ocurrió un error procesando tu solicitud: {str(e)}")
        
    return ConversationHandler.END

async def cancel(update: Update, context):
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END

# Configuración del ConversationHandler para el flujo paso a paso
conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(button_handler, pattern="^start_analysis$")],
    states={
        ASK_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_details)],
        ASK_PHOTO: [MessageHandler(filters.PHOTO, receive_photo_and_analyze)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

# Registrar comandos y manejadores en la app de Telegram
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(conv_handler)
# Mantener mensaje de texto libre por si acaso le escriben directamente el activo sin usar el botón
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_details))

# ---------------------------------------------------------
# CONFIGURACIÓN DEL BUCLE Y WEBHOOK
# ---------------------------------------------------------
loop = asyncio.new_event_loop()

def run_async_loop(l):
    asyncio.set_event_loop(l)
    l.run_forever()

threading.Thread(target=run_async_loop, args=(loop,), daemon=True).start()

async def setup_webhook():
    await telegram_app.initialize()
    webhook_endpoint = f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
    await telegram_app.bot.set_webhook(url=webhook_endpoint)
    logger.info(f"Webhook configurado en: {webhook_endpoint}")

asyncio.run_coroutine_threadsafe(setup_webhook(), loop)

# ---------------------------------------------------------
# RUTAS DEL SERVIDOR WEB (FLASK)
# ---------------------------------------------------------
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    json_update = request.get_json(force=True)
    update = Update.de_json(json_update, telegram_app.bot)
    asyncio.run_coroutine_threadsafe(telegram_app.process_update(update), loop)
    return "OK", 200

@app.route("/")
def index():
    return "Bot de Trading Autónomo Interactivo Activo", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
