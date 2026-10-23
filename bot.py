import yfinance as yf
import matplotlib.pyplot as plt
import asyncio
from telegram import Bot
import os

# Credenciales seguras desde la nube
TELEGRAM_TOKEN = os.environ.get(8460636135:AAF-Uw4qwrJ3ct7cJ0SyP9-Gty2-oVSLgic)
CHAT_ID = os.environ.get(5574325279)

async def generar_senial_y_enviar():
    # 1. Obtener datos de EUR/USD
    data = yf.download('EURUSD=X', period='5d', interval='15m')
    
    # 2. Calcular indicadores (Medias Móviles)
    data['EMA_fast'] = data['Close'].ewm(span=9, adjust=False).mean()
    data['EMA_slow'] = data['Close'].ewm(span=21, adjust=False).mean()
    
    last_row = data.iloc[-1]
    prev_row = data.iloc[-2]
    
    signal = "NEUTRAL / ESPERAR"
    color = "gray"
    
    # Evaluar cruce de medias
    if prev_row['EMA_fast'] <= prev_row['EMA_slow'] and last_row['EMA_fast'] > last_row['EMA_slow']:
        signal = "¡COMPRA (BUY) EUR/USD!"
        color = "green"
    elif prev_row['EMA_fast'] >= prev_row['EMA_slow'] and last_row['EMA_fast'] < last_row['EMA_slow']:
        signal = "¡VENTA (SELL) EUR/USD!"
        color = "red"

    # 3. Crear el gráfico explicativo
    plt.figure(figsize=(10, 5))
    plt.plot(data.index[-30:], data['Close'][-30:], label='Precio EUR/USD', color='black')
    plt.plot(data.index[-30:], data['EMA_fast'][-30:], label='EMA 9', color='blue')
    plt.plot(data.index[-30:], data['EMA_slow'][-30:], label='EMA 21', color='orange')
    
    plt.title(f"Señal de Trading: {signal}", fontsize=14, color=color, fontweight='bold')
    plt.xlabel('Hora')
    plt.ylabel('Precio')
    plt.legend()
    plt.grid(True)
    
    image_path = "eurusd_signal.png"
    plt.savefig(image_path)
    plt.close()

    # 4. Enviar a Telegram
    bot = Bot(token=TELEGRAM_TOKEN)
    precio_actual = float(data['Close'].iloc[-1])
    mensaje = (
        f"📊 **ANÁLISIS EUR/USD**\n"
        f"**Acción recomendada:** {signal}\n"
        f"**Precio Actual:** {precio_actual:.5f}\n\n"
        f"⚠️ *Gestiona tu riesgo correctamente.*"
    )
    
    with open(image_path, 'rb') as photo:
        await bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=mensaje, parse_mode='Markdown')

if __name__ == '__main__':
    asyncio.run(generar_senial_y_enviar())
