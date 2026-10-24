
import os
import asyncio

import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from telegram import Bot


TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")


async def generar_senial_y_enviar():
    # 1. Verificar las credenciales
    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise ValueError(
            "Faltan TELEGRAM_TOKEN o CHAT_ID en los Secrets de GitHub."
        )

    # 2. Descargar datos de EUR/USD
    data = yf.download(
        "EURUSD=X",
        period="5d",
        interval="15m",
        progress=False,
        auto_adjust=False
    )

    if data.empty or len(data) < 22:
        raise ValueError(
            "Yahoo Finance no devolvió suficientes datos de EUR/USD."
        )

    # 3. Normalizar columnas multinivel de yfinance
    if isinstance(data.columns, pd.MultiIndex):
        for level in range(data.columns.nlevels):
            column_names = data.columns.get_level_values(level)

            if "Close" in column_names:
                data.columns = column_names
                break

    # Comprobar que Close sea una serie, no un DataFrame
    if "Close" not in data.columns:
        raise ValueError(
            "No se encontró la columna Close en los datos descargados."
        )

    close = data["Close"]

    if isinstance(close, pd.DataFrame):
        if close.shape[1] != 1:
            raise ValueError(
                "La columna Close contiene varios activos inesperados."
            )
        close = close.iloc[:, 0]

    data["Close"] = pd.to_numeric(close, errors="coerce")
    data = data.dropna(subset=["Close"])

    if len(data) < 22:
        raise ValueError("No hay suficientes precios válidos para las EMA.")

    # 4. Calcular medias exponenciales
    data["EMA_fast"] = data["Close"].ewm(
        span=9, adjust=False
    ).mean()

    data["EMA_slow"] = data["Close"].ewm(
        span=21, adjust=False
    ).mean()

    # Extraer valores individuales para evitar el error de Series
    prev_fast = float(data["EMA_fast"].iloc[-2])
    prev_slow = float(data["EMA_slow"].iloc[-2])
    last_fast = float(data["EMA_fast"].iloc[-1])
    last_slow = float(data["EMA_slow"].iloc[-1])

    # 5. Detectar el cruce de medias
    signal = "NEUTRAL / ESPERAR"
    color = "gray"

    if prev_fast <= prev_slow and last_fast > last_slow:
        signal = "¡COMPRA (BUY) EUR/USD!"
        color = "green"

    elif prev_fast >= prev_slow and last_fast < last_slow:
        signal = "¡VENTA (SELL) EUR/USD!"
        color = "red"

    # 6. Crear gráfico
    fig, ax = plt.subplots(figsize=(10, 5))

    recent = data.iloc[-30:]

    ax.plot(
        recent.index, recent["Close"],
        label="Precio EUR/USD", color="black"
    )
    ax.plot(
        recent.index, recent["EMA_fast"],
        label="EMA 9", color="blue"
    )
    ax.plot(
        recent.index, recent["EMA_slow"],
        label="EMA 21", color="orange"
    )

    ax.set_title(
        f"Señal de Trading: {signal}",
        fontsize=14,
        color=color,
        fontweight="bold"
    )
    ax.set_xlabel("Hora")
    ax.set_ylabel("Precio")
    ax.legend()
    ax.grid(True)

    image_path = "eurusd_signal.png"

    try:
        fig.savefig(image_path, bbox_inches="tight")
    finally:
        plt.close(fig)

    # 7. Enviar análisis a Telegram
    precio_actual = float(data["Close"].iloc[-1])

    mensaje = (
        f"📊 **ANÁLISIS EUR/USD**\n"
        f"**Acción recomendada:** {signal}\n"
        f"**Precio Actual:** {precio_actual:.5f}\n\n"
        f"EMA 9: {last_fast:.5f}\n"
        f"EMA 21: {last_slow:.5f}\n\n"
        f"⚠️ *Gestiona tu riesgo correctamente.*"
    )

    try:
        async with Bot(token=TELEGRAM_TOKEN) as bot:
            with open(image_path, "rb") as photo:
                await bot.send_photo(
                    chat_id=CHAT_ID,
                    photo=photo,
                    caption=mensaje,
                    parse_mode="Markdown"
                )
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)


if __name__ == "__main__":
    asyncio.run(generar_senial_y_enviar())
