import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import yfinance as yf
import matplotlib.pyplot as plt
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# --- MINI SERVIDOR HTTP PARA RENDER (Background / Web Service compatible) ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot de Trading con graficos Activo 24/7!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()
# --------------------------------------------------------------------------

TOKEN = os.getenv("TELEGRAM_TOKEN")

# Función para generar la gráfica con el estilo de niveles (Alto, Bajo, 50%)
def generar_grafico_estilo_trading(df, ticker, accion):
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(8, 5))
    
    precios = df['Close'].values
    altos = df['High'].values
    bajos = df['Low'].values
    
    max_val = max(altos)
    min_val = min(bajos)
    mid_val = (max_val + min_val) / 2
    
    # Líneas de referencia principales (Estilo tus imágenes de referencia)
    ax.axhline(max_val, color='white', linestyle='-', linewidth=1.5, label='ALTO (Resistencia)')
    ax.axhline(min_val, color='white', linestyle='-', linewidth=1.5, label='BAJO (Soporte)')
    ax.axhline(mid_val, color='silver', linestyle='--', linewidth=1.2, alpha=0.8, label='50% (Equilibrio)')
    
    # Graficar la línea de precios
    ax.plot(range(len(precios)), precios, color='cyan', linewidth=2.5, label='Precio')
    
    # Zona sombreada de proyección según la acción sugerida
    if "COMPRAR" in accion:
        ax.fill_between(range(len(precios)), min_val, mid_val, color='green', alpha=0.25, label='Zona Alcista')
    else:
        ax.fill_between(range(len(precios)), mid_val, max_val, color='red', alpha=0.25, label='Zona Bajista')
        
    ax.set_title(f"Estructura de Mercado: {ticker}", fontsize=13, color='white', pad=10)
    ax.legend(loc='upper left', frameon=False, fontsize=9)
    ax.grid(color='gray', linestyle=':', alpha=0.3)
    
    plt.tight_layout()
    ruta_imagen = 'analisis_tecnico.png'
    plt.savefig(ruta_imagen, dpi=300, facecolor=fig.get_facecolor())
    plt.close()
    return ruta_imagen

# Comando /start
async def start(command_update: Update, context: ContextTypes.DEFAULT_TYPE):
    await command_update.message.reply_text(
        "¡Hola! Soy tu bot de trading profesional 📊.\n"
        "Escribe el símbolo de cualquier moneda (ejemplo: `BTC-USD`, `EURUSD=X`, `ETH-USD`) y te enviaré el análisis con su gráfica de niveles al instante."
    )

# Función que responde a tus peticiones con texto y la imagen técnica
async def responder_mercado(message_update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_usuario = message_update.message.text.strip().upper()
    
    await message_update.message.reply_text(f"🔍 Analizando estructura y niveles para `{texto_usuario}`...")
    
    try:
        datos = yf.Ticker(texto_usuario)
        hist = datos.history(period="5d") # Tomamos los últimos días para ver rangos
        
        if not hist.empty:
            precio_actual = hist['Close'].iloc[-1]
            precio_anterior = hist['Close'].iloc[-2]
            cambio = ((precio_actual - precio_anterior) / precio_anterior) * 100
            
            accion = "📈 COMPRAR (Alcista)" if cambio > 0 else "📉 VENDER / ESPERAR (Bajista)"
            
            # Generar la imagen personalizada con los niveles altos, bajos y 50%
            imagen_path = generar_grafico_estilo_trading(hist, texto_usuario, accion)
            
            respuesta = (
                f"📊 **Reporte Técnico para {texto_usuario}**\n\n"
                f"• Precio actual: `{round(precio_actual, 4)}`\n"
                f"• Cambio: `{round(cambio, 2)}%`\n"
                f"• Sugerencia: *{accion}*"
            )
            
            # Enviar la foto con la gráfica generada y el texto explicativo
            with open(imagen_path, 'rb') as foto:
                await message_update.message.reply_photo(
                    photo=foto,
                    caption=respuesta,
                    parse_mode="Markdown"
                )
        else:
            await message_update.message.reply_text("❌ No encontré información para ese símbolo. Prueba con otro (ej: `BTC-USD`).")
            
    except Exception as e:
        await message_update.message.reply_text(f"⚠️ Ocurrió un error al procesar el activo: {e}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), responder_mercado))

    print("🤖 Bot interactivo con gráficos técnicos iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
