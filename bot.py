import os
import logging
import matplotlib
matplotlib.use('Agg') # Obligatorio para servidores en la nube sin pantalla
import matplotlib.pyplot as plt
import numpy as np
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import google.generativeai as genai

# Configuración de logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Credenciales desde las variables de entorno de Render
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Inicializar Google Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

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
    
    # Líneas de gestión de riesgo
    ax.axhline(y=tp, color='#26a69a', linestyle='--', linewidth=1.5, label=f'TP: {tp}')
    ax.axhline(y=entrada, color='#2962FF', linestyle='-', linewidth=1.5, label=f'Entrada: {entrada}')
    ax.axhline(y=sl, color='#ef5350', linestyle='--', linewidth=1.5, label=f'SL: {sl}')
    
    # Zonas de beneficio y riesgo
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
# MANEJADORES DE MENSAJES Y COMANDOS
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    bienvenida = (
        f"¡Hola, {user_name}! 🤖📊\n\n"
        "Tu bot de trading ya está conectado con **Gemini IA**.\n"
        "Envía el nombre de un activo (ej: `BTC-USD`) o **una captura de pantalla** para calcular "
        "los niveles exactos de Entrada, TP y SL."
    )
    await update.message.reply_text(bienvenida, parse_mode="Markdown")

async def responder_con_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    
    prompt = (
        "Eres un trader experto en metodología ICT. "
        "Responde a la siguiente consulta de trading dando un análisis técnico detallado, "
        "sugerencia clara (Comprar/Vender/Esperar) y niveles estimados de Entrada, TP y SL: " + texto
    )
    
    try:
        respuesta = model.generate_content(prompt)
        await update.message.reply_text(respuesta.text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error con IA: {e}")
        await update.message.reply_text("Ocurrió un error procesando tu consulta con la IA.")

async def analizar_imagen_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        foto_archivo = await update.message.photo[-1].get_file()
        foto_bytes = await foto_archivo.download_as_bytearray()
        
        imagen_part = {
            'mime_type': 'image/jpeg',
            'data': bytes(foto_bytes)
        }
        
        prompt_vision = (
            "Analiza esta captura de gráfico de trading. "
            "Identifica la estructura y calcula numéricamente dónde poner el Precio de Entrada, "
            "el Take Profit (TP) y el Stop Loss (SL)."
        )
        
        respuesta = model.generate_content([prompt_vision, imagen_part])
        
        # Generar gráfico visual con niveles de ejemplo
        ruta_grafico = generar_grafico_posicion("BTC-USD", 80474.00, 80557.00, 80418.00)
        
        with open(ruta_grafico, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"📈 **Análisis de Gráfico por IA:**\n\n{respuesta.text}",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Error procesando imagen: {e}")
        await update.message.reply_text("No se pudo analizar la imagen. Inténtalo de nuevo.")

# ---------------------------------------------------------
# FUNCIÓN PRINCIPAL
# ---------------------------------------------------------
def main():
    if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
        logger.error("Faltan tokens de configuración.")
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Registro de manejadores
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_con_ia))
    application.add_handler(MessageHandler(filters.PHOTO, analizar_imagen_ia))

    logger.info("Bot con IA iniciado con éxito...")
    application.run_polling()

if __name__ == '__main__':
    main()
