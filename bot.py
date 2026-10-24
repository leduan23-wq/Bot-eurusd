import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- SERVIDOR WEB OBLIGATORIO PARA EL PLAN GRATIS DE RENDER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot ICT Activo 24/7 en Render Gratis!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"Servidor web escuchando en el puerto {port}...")
    server.serve_forever()

# Levantar el servidor web en segundo plano para cumplir con el puerto libre de Render
threading.Thread(target=run_web_server, daemon=True).start()
# -------------------------------------------------------------

def generar_grafico_estilo_trading(df, ticker, accion):
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axis('off')
    
    y_min, y_max = 0, 100
    y_mid = 50
    
    # Fondo oscuro estilo terminal de trading institucional
    ax.set_facecolor('#0b0e14')
    fig.patch.set_facecolor('#0b0e14')
    
    # Cuadrícula tenue
    for gx in np.linspace(2, 12, 5):
        ax.plot([gx, gx], [y_min, y_max], color='#22252a', linestyle='-', linewidth=0.8, zorder=0)
    for gy in np.linspace(0, 100, 5):
        ax.plot([2, 12], [gy, gy], color='#22252a', linestyle='-', linewidth=0.8, zorder=0)

    # Zonas sombreadas
    if "COMPRAR" in accion:
        zona_verde = patches.Rectangle((5.5, y_min), 6.5, y_mid - y_min, facecolor='#00875a', alpha=0.3, edgecolor='none', zorder=1)
        zona_roja = patches.Rectangle((5.5, y_mid), 6.5, y_max - y_mid, facecolor='#de350b', alpha=0.25, edgecolor='none', zorder=1)
    else:
        zona_verde = patches.Rectangle((5.5, y_mid), 6.5, y_max - y_mid, facecolor='#00875a', alpha=0.3, edgecolor='none', zorder=1)
        zona_roja = patches.Rectangle((5.5, y_min), 6.5, y_mid - y_min, facecolor='#de350b', alpha=0.25, edgecolor='none', zorder=1)
    
    ax.add_patch(zona_verde)
    ax.add_patch(zona_roja)

    # Caja principal del rango
    ax.plot([2, 12.5], [y_max, y_max], color='white', linewidth=2.2, zorder=3)
    ax.plot([2, 12.5], [y_min, y_min], color='white', linewidth=2.2, zorder=3)
    ax.plot([12.5, 12.5], [y_min, y_max], color='white', linewidth=2.2, zorder=3)

    # Bloque diario "1D"
    caja_1d = patches.Rectangle((0.4, y_min - 2), 1.2, (y_max - y_min) + 4, facecolor='white', edgecolor='none', zorder=3)
    ax.add_patch(caja_1d)
    ax.text(1.0, y_mid, "1D", color='black', fontsize=14, fontweight='bold', rotation=90, va='center', ha='center', zorder=4)
    ax.plot([1.6, 2], [y_mid, y_mid], color='white', linewidth=1.8, zorder=3)

    # Línea del 50%
    ax.axhline(y_mid, color='white', linestyle='--', linewidth=1.5, alpha=0.8, zorder=3)
    ax.text(12.8, y_mid, "50%", color='white', fontsize=11, fontweight='bold', va='center', zorder=4)

    # Velas esquemáticas
    np.random.seed(10)
    num_velas = 14
    x_vals = np.linspace(2.3, 11.8, num_velas)
    
    if "COMPRAR" in accion:
        alturas = [52, 55, 53, 56, 54, 42, 38, 45, 58, 68, 75, 82, 88, 92]
    else:
        alturas = [48, 45, 47, 44, 46, 58, 62, 55, 42, 32, 25, 18, 12, 8]

    for i, x in enumerate(x_vals):
        base_y = alturas[i]
        ax.plot([x, x], [base_y - 8, base_y + 8], color='white', linewidth=1.2, zorder=3)
        cuerpo = patches.Rectangle((x - 0.32, base_y - 4), 0.64, 8, facecolor='#ffffff', edgecolor='#ffffff', zorder=3)
        ax.add_patch(cuerpo)

    # Óvalo de manipulación
    circulo_sweep = patches.Ellipse((x_vals[6], alturas[6]), width=1.8, height=22, angle=15, 
                                    facecolor='none', edgecolor='white', linewidth=1.8, linestyle='-', zorder=5)
    ax.add_patch(circulo_sweep)

    # Etiqueta temporalidad "15 MIN"
    ax.plot([2.3, 2.3, 5.0, 5.0], [y_min + 8, y_min + 5, y_min + 5, y_min + 8], color='white', linewidth=1.2, zorder=3)
    ax.text(3.65, y_min + 12, "15 MIN", color='white', fontsize=10, fontweight='bold', ha='center', zorder=4)

    # Etiquetas principales
    ax.text(12.8, y_max, "ALTO", color='white', fontsize=13, fontweight='bold', va='center', zorder=4)
    ax.text(12.8, y_min, "BAJO", color='white', fontsize=13, fontweight='bold', va='center', zorder=4)
    
    ax.set_title(f"Estructura Institucional ICT: {ticker}", fontsize=14, color='#00d2ff', pad=15, fontweight='bold')
    
    ax.set_xlim(-0.5, 14.5)
    ax.set_ylim(-15, 115)
    
    plt.tight_layout()
    ruta_imagen = 'analisis_tecnico.png'
    plt.savefig(ruta_imagen, dpi=300, facecolor=fig.get_facecolor())
    plt.close()
    return ruta_imagen

async def start(command_update: Update, context: ContextTypes.DEFAULT_TYPE):
    await command_update.message.reply_text(
        "¡Hola! Soy tu bot institucional ICT 📊.\n"
        "Escribe el símbolo de cualquier activo (ejemplo: `BTC-USD`, `EURUSD=X`) para recibir tu análisis con gráfico técnico esquemático."
    )

async def responder_mercado(message_update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_usuario = message_update.message.text.strip().upper()
    await message_update.message.reply_text(f"🔍 Analizando estructura para `{texto_usuario}`...")
    
    try:
        datos = yf.Ticker(texto_usuario)
        hist = datos.history(period="5d")
        
        if not hist.empty:
            precio_actual = hist['Close'].iloc[-1]
            precio_anterior = hist['Close'].iloc[-2]
            cambio = ((precio_actual - precio_anterior) / precio_anterior) * 100
            
            accion = "📈 COMPRAR (Alcista)" if cambio > 0 else "📉 VENDER / ESPERAR (Bajista)"
            
            imagen_path = generar_grafico_estilo_trading(hist, texto_usuario, accion)
            
            respuesta = (
                f"📊 **Estructura ICT: {texto_usuario}**\n\n"
                f"• Precio actual: `{round(precio_actual, 4)}`\n"
                f"• Cambio: `{round(cambio, 2)}%`\n"
                f"• Sugerencia: *{accion}*"
            )
            
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

    print("🤖 Bot institucional ICT iniciado correctamente...")
    app.run_polling()

if __name__ == "__main__":
    main()
