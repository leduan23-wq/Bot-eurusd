import os
import logging
import asyncio
import threading
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import google.generativeai as genai

# Configuración de logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Credenciales y variables de entorno
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")

# Inicializar Google Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Inicializar Flask y la App de Telegram
app = Flask(__name__)
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

# ---------------------------------------------------------
# FUNCIÓN DE GRÁFICO (Entrada, TP y SL)
# ---------------------------------------------------------
def generar_grafico_posicion(simbolo, entrada, tp, sl):
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor('#131722')
    ax.set_facecolor('#131722')
    
    x = np.arange(10)
    precios = np.linspace(entrada - 50, entrada + 20, 10)
    ax.plot(x, precios, color='#2962FF', linewidth=2, label='Precio')
    
    ax.axhline(y=tp, color='#26a69a', linestyle='--', linewidth=1.5, label=f'TP: {tp}')
    ax.axhline(y=entrada, color='#2962FF', linestyle='-', linewidth=1.5, label=f'Entrada: {entrada}')
    ax.axhline(y=sl, color='#ef5350', linestyle='--', linewidth=1.5, label=f'SL: {sl}')
    
    ax.axhspan(entrada, tp, color='#26a69a', alpha=0.15)
    ax.axhspan(sl, entrada, color='#ef5350', alpha=0.15)
    
    ax.tick_params(colors='white')
    for spine in ax.spines.values():
        spine.set_color('#363c4e')
    ax.set_title(f'Análisis ICT: {simbolo}', color='white', fontsize=12, pad=10)
    
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
        "Tu bot de trading ya está activo con **Gemini IA**.\n"
        "Envía un activo (ej: `BTC-USD`) o una captura de pantalla para calcular Entrada, TP y SL."
    )
    await update.message.reply_text(bienvenida, parse_mode="Markdown")

async def responder_con_ia(update: Update, context):
    texto = update.message.text
    prompt = (
        "Eres un trader experto en metodología ICT. "
        "Responde dando análisis técnico, sugerencia clara (Comprar/Vender/Esperar) y niveles estimados de Entrada, TP y SL: " + texto
    )
    try:
        respuesta = model.generate_content(prompt)
        await update.message.reply_text(respuesta.text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error con IA: {e}")
        await update.message.reply_text("Ocurrió un error procesando tu consulta con la IA.")

async def analizar_imagen_ia(update: Update, context):
    try:
        foto_archivo = await update.message.photo[-1].get_file()
        foto_bytes = await foto_archivo.download_as_bytearray()
        
        imagen_part = {'mime_type': 'image/jpeg', 'data': bytes(foto_bytes)}
        prompt_vision = "Analiza este gráfico de trading. Identifica la estructura y calcula numéricamente Entrada, TP y SL."
        
        respuesta = model.generate_content([prompt_vision, imagen_part])
        ruta_grafico = generar_grafico_posicion("BTC-USD", 80474.00, 80557.00, 80418.00)
        
        with open(ruta_grafico, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"📈 **Análisis de Gráfico por IA:**\n\n{respuesta.text}",
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Error procesando imagen: {e}")
        await update.message.reply_text("No se pudo analizar la imagen.")

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

# Iniciar el bucle de asyncio en un hilo separado de fondo
threading.Thread(target=run_async_loop, args=(loop,), daemon=True).start()

async def setup_webhook():
    await telegram_app.initialize()
    webhook_endpoint = f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
    await telegram_app.bot.set_webhook(url=webhook_endpoint)
    logger.info(f"Webhook configurado en: {webhook_endpoint}")

# Ejecutar la configuración inicial del webhook de forma segura en el bucle
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
    return "Bot de Trading con IA Activo", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
