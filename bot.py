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
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
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

# ---------------------------------------------------------
# FUNCIÓN DE GRÁFICO DINÁMICO
# ---------------------------------------------------------
def generar_grafico_posicion(simbolo, entrada, tp, sl):
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor('#131722')
    ax.set_facecolor('#131722')
    
    rango_base = abs(tp - sl) if tp != sl else 100
    precios = np.linspace(sl - (rango_base * 0.2), tp + (rango_base * 0.2), 10)
    x = np.arange(10)
    
    ax.plot(x, precios, color='#2962FF', linewidth=2, label='Estructura')
    
    # Líneas clave de gestión de riesgo
    ax.axhline(y=tp, color='#26a69a', linestyle='--', linewidth=1.8, label=f'TP: {tp}')
    ax.axhline(y=entrada, color='#2962FF', linestyle='-', linewidth=1.8, label=f'Entrada: {entrada}')
    ax.axhline(y=sl, color='#ef5350', linestyle='--', linewidth=1.8, label=f'SL: {sl}')
    
    # Zonas visuales
    ax.axhspan(entrada, tp, color='#26a69a', alpha=0.15)
    ax.axhspan(sl, entrada, color='#ef5350', alpha=0.15)
    
    ax.tick_params(colors='white')
    for spine in ax.spines.values():
        spine.set_color('#363c4e')
    ax.set_title(f'Niveles Óptimos ICT: {simbolo.upper()}', color='white', fontsize=12, pad=10)
    ax.legend(facecolor='#131722', edgecolor='#363c4e', labelcolor='white', loc='upper left')
    
    ruta_imagen = 'analisis_ia.png'
    plt.savefig(ruta_imagen, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    return ruta_imagen

# ---------------------------------------------------------
# MANEJADORES DE TELEGRAM
# ---------------------------------------------------------
async def start(update: Update, context):
    user_name = update.effective_user.first_name
    bienvenida = (
        f"¡Hola, {user_name}! 🤖📊\n\n"
        "Tu bot autónomo con **Gemini IA** está listo.\n"
        "Solo escribe el nombre de un activo (ej: `BTC`, `EURUSD`, `ETH`) y el bot calculará los niveles y **generará la imagen del gráfico automáticamente**."
    )
    await update.message.reply_text(bienvenida, parse_mode="Markdown")

async def responder_con_ia(update: Update, context):
    texto = update.message.text
    try:
        await update.message.reply_text("🤖 Analizando mercado, calculando niveles ICT y generando gráfico...")
        
        prompt = (
            f"Actúa como un trader experto en metodología ICT. "
            f"Para el activo o consulta solicitada: '{texto}', calcula un escenario de trading profesional con precios estimados de mercado actuales. "
            f"Debes incluir obligatoriamente al final de tu respuesta los valores numéricos exactos en este formato estricto:\n"
            f"ENTRADA: [número]\n"
            f"TP: [número]\n"
            f"SL: [número]"
        )
        
        respuesta = model.generate_content(prompt, safety_settings=safety_settings)
        texto_respuesta = respuesta.text
        
        # Valores por defecto de respaldo
        entrada, tp, sl = 80474.00, 80557.00, 80418.00
        
        match_ent = re.search(r"ENTRADA:\s*([\d\.]+)", texto_respuesta, re.IGNORECASE)
        match_tp = re.search(r"TP:\s*([\d\.]+)", texto_respuesta, re.IGNORECASE)
        match_sl = re.search(r"SL:\s*([\d\.]+)", texto_respuesta, re.IGNORECASE)
        
        if match_ent: entrada = float(match_ent.group(1))
        if match_tp: tp = float(match_tp.group(1))
        if match_sl: sl = float(match_sl.group(1))
        
        # Generar la imagen del gráfico
        ruta_grafico = generar_grafico_posicion(texto, entrada, tp, sl)
        
        # 1. Enviar la foto con un título corto (para evitar el límite de Telegram)
        with open(ruta_grafico, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"📈 **Gráfico ICT generado para: {texto.upper()}**",
                parse_mode="Markdown"
            )
            
        # 2. Enviar el análisis completo en un mensaje de texto separado
        await update.message.reply_text(
            f"📋 **Análisis Técnico Detallado:**\n\n{texto_respuesta}",
            parse_mode="Markdown"
        )
            
    except Exception as e:
        logger.error(f"Error generando análisis autónomo: {e}", exc_info=True)
        await update.message.reply_text(f"Ocurrió un error procesando tu solicitud: {str(e)}")

async def analizar_imagen_ia(update: Update, context):
    try:
        await update.message.reply_text("🔍 Analizando imagen y calculando niveles ICT...")
        foto_archivo = await update.message.photo[-1].get_file()
        foto_bytes = await foto_archivo.download_as_bytearray()
        
        imagen_part = {'mime_type': 'image/jpeg', 'data': bytes(foto_bytes)}
        prompt_vision = (
            "Analiza este gráfico bajo metodología ICT. Calcula numéricamente los niveles clave. "
            "Formato obligatorio al final:\nENTRADA: [número]\nTP: [número]\nSL: [número]"
        )
        
        respuesta = model.generate_content([prompt_vision, imagen_part], safety_settings=safety_settings)
        texto_respuesta = respuesta.text
        
        entrada, tp, sl = 80474.00, 80557.00, 80418.00
        match_ent = re.search(r"ENTRADA:\s*([\d\.]+)", texto_respuesta, re.IGNORECASE)
        match_tp = re.search(r"TP:\s*([\d\.]+)", texto_respuesta, re.IGNORECASE)
        match_sl = re.search(r"SL:\s*([\d\.]+)", texto_respuesta, re.IGNORECASE)
        
        if match_ent: entrada = float(match_ent.group(1))
        if match_tp: tp = float(match_tp.group(1))
        if match_sl: sl = float(match_sl.group(1))
        
        ruta_grafico = generar_grafico_posicion("Gráfico Analizado", entrada, tp, sl)
        
        with open(ruta_grafico, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption="📈 **Gráfico Analizado por IA**",
                parse_mode="Markdown"
            )
            
        await update.message.reply_text(
            f"📋 **Análisis Detallado de la Captura:**\n\n{texto_respuesta}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error procesando imagen: {e}", exc_info=True)
        await update.message.reply_text("No se pudo procesar la imagen.")

# Registrar manejadores
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_con_ia))
telegram_app.add_handler(MessageHandler(filters.PHOTO, analizar_imagen_ia))

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
    return "Bot de Trading Autónomo Activo", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
