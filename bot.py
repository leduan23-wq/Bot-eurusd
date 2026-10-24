import os
import yfinance as yf
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Cargar el token desde las variables de entorno
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Comando /start o /help
async def start(command_update: Update, context: ContextTypes.DEFAULT_TYPE):
    await command_update.message.reply_text(
        "¡Hola! Soy tu bot de trading 📊.\n"
        "Escribe el símbolo de una moneda (por ejemplo: `BTC-USD` o `EURUSD=X`) para ver su precio y análisis al instante."
    )

# Función que responde cuando le escribes cualquier texto (como el nombre de un activo)
async def responder_mercado(message_update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_usuario = message_update.message.text.strip().upper()
    
    await message_update.message.reply_text(f"🔍 Consultando datos para `{texto_usuario}`...")
    
    try:
        # Consultar en Yahoo Finance lo que el usuario escribió
        datos = yf.Ticker(texto_usuario)
        hist = datos.history(period="2d")
        
        if not hist.empty:
            precio_actual = hist['Close'].iloc[-1]
            precio_anterior = hist['Close'].iloc[-2]
            cambio = ((precio_actual - precio_anterior) / precio_anterior) * 100
            
            accion = "📈 COMPRAR (Alcista)" if cambio > 0 else "📉 VENDER / ESPERAR (Bajista)"
            
            respuesta = (
                f"📊 **Reporte para {texto_usuario}**\n\n"
                f"• Precio actual: `{round(precio_actual, 4)}`\n"
                f"• Cambio: `{round(cambio, 2)}%`\n"
                f"• Sugerencia: *{accion}*"
            )
        else:
            respuesta = "❌ No encontré información para ese símbolo. Prueba con otro (ej: `BTC-USD`)."
            
    except Exception as e:
        respuesta = f"⚠️ Ocurrió un error al buscar el activo: {e}"

    await message_update.message.reply_text(respuesta, parse_mode="Markdown")

def main():
    # Construir la aplicación del bot enlazada al token
    app = ApplicationBuilder().token(TOKEN).build()

    # Registrar los manejadores de comandos y mensajes
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), responder_mercado))

    print("🤖 Bot iniciado y escuchando mensajes en tiempo real...")
    
    # Mantener el bot parándose y escuchando (Polling continuo)
    app.run_polling()

if __name__ == "__main__":
    main()
