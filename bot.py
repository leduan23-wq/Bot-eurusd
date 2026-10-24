import os
import yfinance as yf
import matplotlib.pyplot as plt
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# Cargar las credenciales desde las variables de entorno de GitHub Secrets
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=TOKEN)

def analizar_mercados():
    # Lista de activos o mercados que deseas consultar
    simbolos = {
        "EUR/USD": "EURUSD=X",
        "Bitcoin": "BTC-USD",
        "Oro": "GC=F",
        "S&P 500": "^GSPC"
    }
    
    resultados = []
    
    # Recopilar la información completa de cada tabla/activo
    for nombre, ticker in simbolos.items():
        try:
            datos = yf.Ticker(ticker)
            hist = datos.history(period="5d")
            
            if not hist.empty:
                precio_actual = hist['Close'].iloc[-1]
                precio_anterior = hist['Close'].iloc[-2]
                cambio_porcentaje = ((precio_actual - precio_anterior) / precio_anterior) * 100
                
                # Definir una acción básica de ejemplo basada en el comportamiento
                if cambio_porcentaje > 0:
                    accion = "📈 COMPRAR (Alcista)"
                else:
                    accion = "📉 VENDER / ESPERAR (Bajista)"
                
                resultados.append({
                    "nombre": nombre,
                    "precio": round(precio_actual, 4),
                    "cambio": round(cambio_porcentaje, 2),
                    "accion": accion
                })
        except Exception as e:
            print(f"Error al obtener datos de {nombre}: {e}")

    return resultados

def generar_grafico_ejemplo(resultados):
    # Crear un gráfico de ejemplo rápido para enviarlo con el mensaje
    nombres = [r['nombre'] for r in resultados]
    cambios = [r['cambio'] for r in resultados]
    
    plt.figure(figsize=(8, 4))
    colores = ['green' if c >= 0 else 'red' for c in cambios]
    plt.barh(nombres, cambios, color=colores)
    plt.xlabel('Variación en %')
    plt.title('Resumen de Mercados - Bot')
    plt.axvline(0, color='grey', linestyle='--', linewidth=0.8)
    plt.tight_layout()
    
    ruta_imagen = 'resumen_mercado.png'
    plt.savefig(ruta_imagen)
    plt.close()
    return ruta_imagen

async def enviar_reporte():
    datos_mercado = analizar_mercados()
    
    if not datos_mercado:
        print("No se pudieron obtener datos de los mercados.")
        return

    # Construir el texto con la información completa en formato de tabla/lista
    mensaje = "📊 **REPORTE GENERAL DE MERCADOS Y ACCIONES** 📊\n\n"
    
    for item in datos_mercado:
        mensaje += f"🔹 **{item['nombre']}**\n"
        mensaje += f"   • Precio: `{item['precio']}`\n"
        mensaje += f"   • Cambio: `{item['cambio']}%`\n"
        mensaje += f"   • Acción sugerida: *{item['accion']}*\n\n"

    # Generar la imagen de ejemplo
    imagen_path = generar_grafico_ejemplo(datos_mercado)

    # Crear botones interactivos para cada plataforma o mercado
    teclado = [
        [
            InlineKeyboardButton("📈 Ver en TradingView", url="https://www.tradingview.com"),
            InlineKeyboardButton("📉 Ver en MetaTrader", url="https://www.metatrader5.com")
        ],
        [
            InlineKeyboardButton("🔄 Actualizar Datos", callback_data="actualizar")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(teclado)

    # Enviar la imagen junto con la información y los botones a Telegram
    async with bot:
        with open(imagen_path, 'rb') as foto:
            await bot.send_photo(
                chat_id=CHAT_ID,
                photo=foto,
                caption=mensaje,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

if __name__ == "__main__":
    import asyncio
    asyncio.run(enviar_reporte())
