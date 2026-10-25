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
# FUNCIÓN DE GRÁFICO DETALLADO ESTILO EL SENSEI TRADING
# ---------------------------------------------------------
def generar_grafico_posicion(simbolo, entrada, tp, sl):
    fig, ax = plt.subplots(figsize=(9, 6))
    fig.patch.set_facecolor('#131722')
    ax.set_facecolor('#131722')
    
    # Simular estructura de mercado realista (ondas de swing / price action)
    x = np.linspace(0, 10, 100)
    base_tendencia = np.linspace(sl + (entrada - sl) * 0.4, entrada, 50)
    impulso_tp = np.linspace(entrada, tp, 50)
    precios_base = np.concatenate([base_tendencia, impulso_tp])
    ruido = np.sin(x * 5) * (abs(tp - sl) * 0.04)
    precios = precios_base + ruido
    
    ax.plot(x, precios, color='#2962FF', linewidth=2, label='Estructura (Price Action)')
    
    # Zonas institucionales (Pisos, Techos y Order Blocks)
    ax.axhspan(entrada - (abs(tp - sl) * 0.08), entrada + (abs(tp - sl) * 0.08), color='#2962FF', alpha=0.25, label='Zona de Entrada / OB')
    ax.axhspan(tp - (abs(tp - sl) * 0.04), tp + (abs(tp - sl) * 0.04), color='#26a69a', alpha=0.3, label='Take Profit (Techo / Obj)')
    ax.axhspan(sl - (abs(tp - sl) * 0.04), sl + (abs(tp - sl) * 0.04), color='#ef5350', alpha=0.3, label='Stop Loss (Piso / Riesgo)')

    # Líneas clave horizontales institucionales
    ax.axhline(y=tp, color='#26a69a', linestyle='--', linewidth=1.8, label=f'TP: {tp}')
    ax.axhline(y=entrada, color='#2962FF', linestyle='-', linewidth=2.0, label=f'Entrada: {entrada}')
    ax.axhline(y=sl, color='#ef5350', linestyle='--', linewidth=1.8, label=f'SL: {sl}')
    
    # Anotaciones visuales explicativas en el gráfico
    ax.text(0.5, entrada, ' ENTRADA INSTITUCIONAL', color='#ffffff', fontsize=8, fontweight='bold', va='center', backgroundcolor='#2962FF')
    ax.text(0.5, tp, ' TAKE PROFIT (OBJETIVO 1:2+)', color='#ffffff', fontsize=8, fontweight='bold', va='center', backgroundcolor='#26a69a')
    ax.text(0.5, sl, ' STOP LOSS (LÍMITE SEGURO)', color='#ffffff', fontsize=8, fontweight='bold', va='center', backgroundcolor='#ef5350')

    # Estética estilo TradingView / Tema Oscuro
    ax.tick_params(colors='white', labelsize=9)
    ax.grid(True, color='#2a2e39', linestyle=':', alpha=0.5)
    for spine in ax.spines.values():
        spine.set_color('#363c4e')
        
    ax.set_title(f'Estrategia Institucional - El Sensei Trading | {simbolo.upper()}', color='white', fontsize=12, pad=12, fontweight='bold')
    ax.legend(facecolor='#131722', edgecolor='#363c4e', labelcolor='white', loc='upper left', fontsize=8)
    
    ruta_imagen = 'analisis_ia.png'
    plt.savefig(ruta_imagen, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight', dpi=150)
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
        "Bienvenido a tu asistente de trading entrenado con la metodología avanzada de **El Sensei Trading** (@senseiprofe).\n\n"
        "Selecciona abajo el activo que deseas analizar:"
    )
    
    if update.message:
        await update.message.reply_text(bienvenida, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(bienvenida, reply_markup=reply_markup, parse_mode="Markdown")
        
    return ConversationHandler.END

async def asset_chosen(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    asset = query.data.replace("asset_", "")
    context.user_data['selected_asset'] = asset
    
    await query.message.edit_text(
        f"✅ Has seleccionado: **{asset}**\n\n"
        "📸 **Envía ahora la captura de pantalla de tu TradingView** para este activo. La IA aplicará rigurosamente el análisis institucional del Sensei (pisos/techos, confluencias, estructura y gestión de riesgo 1:2).",
        parse_mode="Markdown"
    )
    return ASK_PHOTO

async def receive_photo_and_analyze(update: Update, context):
    try:
        asset = context.user_data.get('selected_asset', 'BTC-USD')
        await update.message.reply_text(f"🤖 Estudiando captura de pantalla para **{asset}** bajo los criterios y cursos de **El Sensei Trading**...")
        
        foto_archivo = await update.message.photo[-1].get_file()
        foto_bytes = await foto_archivo.download_as_bytearray()
        
        imagen_part = {'mime_type': 'image/jpeg', 'data': bytes(foto_bytes)}
        
        prompt_vision = (
            f"Actúa como un trader institucional experto que ha dominado por completo todos los cursos avanzados y metodologías del canal de YouTube 'El Sensei Trading' (@senseiprofe). "
            f"El activo seleccionado es: '{asset}'. "
            f"Analiza la captura de pantalla adjunta de TradingView aplicando estrictamente sus enseñanzas clave:\n"
            f"1. **Soportes y Resistencias (Pisos y Techos):** Identifica las zonas institucionales donde el precio ha rebotado múltiples veces (mínimo 3 toques).\n"
            f"2. **Estructura y Tendencia:** Evalúa los puntos altos y bajos (máximos y mínimos crecientes o decrecientes) para definir si estamos en tendencia alcista o bajista ('La tendencia es tu amiga').\n"
            f"3. **Confirmaciones por Velas (Velas Envolventes y Mechas de Rechazo):** Busca patrones de velas japonesas concluyentes en las zonas operativas.\n"
            f"4. **Gestión de Riesgo y R/R Profesional:** Diseña la operación asegurando una relación beneficio-riesgo mínima de 1:2 (el Take Profit debe duplicar la distancia del Stop Loss).\n"
            f"Basándote estrictamente en el precio real actual visible en la imagen, calcula con precisión matemática los niveles óptimos.\n"
            f"Debes incluir obligatoriamente al final de tu respuesta los valores numéricos exactos en este formato estricto:\n"
            f"ENTRADA: [número]\n"
            f"TP: [número]\n"
            f"SL: [número]"
        )
        
        # Reintento automático para mitigar saturación de cuota (429)
        respuesta = None
        max_intentos = 3
        for intento in range(max_intentos):
            try:
                respuesta = model.generate_content([prompt_vision, imagen_part], safety_settings=safety_settings)
                break
            except Exception as api_err:
                if "429" in str(api_err) or "ResourceExhausted" in str(api_err):
                    if intento < max_intentos - 1:
                        await asyncio.sleep(5)
                        continue
                raise api_err

        texto_respuesta = respuesta.text
        
        # Valores de respaldo predeterminados
        entrada, tp, sl = 80750.00, 80900.00, 80600.00
        
        match_ent = re.search(r"ENTRADA:\s*([\d\.]+)", texto_respuesta, re.IGNORECASE)
        match_tp = re.search(r"TP:\s*([\d\.]+)", texto_respuesta, re.IGNORECASE)
        match_sl = re.search(r"SL:\s*([\d\.]+)", texto_respuesta, re.IGNORECASE)
        
        if match_ent: entrada = float(match_ent.group(1))
        if match_tp: tp = float(match_tp.group(1))
        if match_sl: sl = float(match_sl.group(1))
        
        # Generar gráfico detallado con los niveles calculados
        ruta_grafico = generar_grafico_posicion(asset, entrada, tp, sl)
        
        # Enviar foto del gráfico generado
        with open(ruta_grafico, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"📈 Gráfico Institucional El Sensei Trading ({asset})"
            )
            
        # Enviar análisis detallado en texto plano
        await update.message.reply_text(
            f"📋 Análisis Técnico Estilo El Sensei Trading:\n\n{texto_respuesta}"
        )
        
        # Volver a mostrar el menú de botones
        await start(update, context)
        
    except Exception as e:
        logger.error(f"Error procesando análisis: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Se ha alcanzado temporalmente el límite de peticiones gratuitas de la IA (Error 429). "
            "Por favor, espera unos segundos e inténtalo de nuevo."
        )
        
    return ConversationHandler.END

async def cancel(update: Update, context):
    await update.message.reply_text("Operación cancelada. Escribe /start para volver al menú.")
    return ConversationHandler.END

# Configuración del ConversationHandler
conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(asset_chosen, pattern="^asset_")],
    states={
        ASK_PHOTO: [MessageHandler(filters.PHOTO, receive_photo_and_analyze)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

# Registrar manejadores
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(conv_handler)
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))

# ---------------------------------------------------------
# CONFIGURACIÓN DEL BUCLE Y WEBHOOK CON BOTÓN DE MENÚ PERSISTENTE
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
    
    # Configurar el botón de menú persistente para /start
    await telegram_app.bot.set_my_commands([
        BotCommand("start", "Menú principal y selección de activos")
    ])
    
    logger.info(f"Webhook configurado y menú de comandos establecido en: {webhook_endpoint}")

asyncio.run_coroutine_threadsafe(setup_webhook(), loop)

# ---------------------------------------------------------
# RUTAS DEL WEBHOOK (FLASK)
# ---------------------------------------------------------
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    json_update = request.get_json(force=True)
    update = Update.de_json(json_update, telegram_app.bot)
    asyncio.run_coroutine_threadsafe(telegram_app.process_update(update), loop)
    return "OK", 200

@app.route("/")
def index():
    return "Bot de Trading El Sensei Activo", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
