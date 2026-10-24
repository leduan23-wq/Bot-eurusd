import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def generar_grafico_estilo_trading(df, ticker, accion):
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.axis('off')
    
    # Coordenadas del lienzo esquemático
    y_min, y_max = 0, 100
    y_mid = 50
    
    # 1. Caja principal del rango (Líneas blancas brillantes para ALTO y BAJO)
    ax.plot([2, 12], [y_max, y_max], color='white', linewidth=2)  # Línea superior (ALTO)
    ax.plot([2, 12], [y_min, y_min], color='white', linewidth=2)  # Línea inferior (BAJO)
    ax.plot([12, 12], [y_min, y_max], color='white', linewidth=2) # Cierre derecho del rango
    
    # 2. Bloque "1D" a la izquierda (Caja blanca vertical sólida)
    caja_1d = patches.Rectangle((0.5, y_min), 1.2, y_max - y_min, facecolor='white', edgecolor='none')
    ax.add_patch(caja_1d)
    ax.text(1.1, y_mid, "1D", color='black', fontsize=13, fontweight='bold', rotation=90, va='center', ha='center')
    
    # Conector entre la caja 1D y el rango
    ax.plot([1.7, 2], [y_mid, y_mid], color='white', linewidth=1.5)
    
    # 3. Línea punteada del 50% (Equilibrio)
    ax.axhline(y_mid, color='white', linestyle='--', linewidth=1.2, alpha=0.9)
    ax.text(12.3, y_mid, "50%", color='white', fontsize=11, fontweight='bold', va='center')
    
    # 4. Zonas de color sólido (Rojo arriba / Verde abajo o viceversa según la acción)
    if "COMPRAR" in accion:
        zona_verde = patches.Rectangle((6, y_min), 6, y_mid - y_min, facecolor='green', alpha=0.35, edgecolor='none')
        zona_roja = patches.Rectangle((6, y_mid), 6, y_max - y_mid, facecolor='darkred', alpha=0.45, edgecolor='none')
        ax.add_patch(zona_verde)
        ax.add_patch(zona_roja)
    else:
        zona_verde = patches.Rectangle((6, y_mid), 6, y_max - y_mid, facecolor='green', alpha=0.35, edgecolor='none')
        zona_roja = patches.Rectangle((6, y_min), 6, y_mid - y_min, facecolor='darkred', alpha=0.45, edgecolor='none')
        ax.add_patch(zona_verde)
        ax.add_patch(zona_roja)

    # 5. Dibujar velas esquemáticas dentro del gráfico para simular la acción del precio
    np.random.seed(42)
    num_velas = 12
    x_vals = np.linspace(2.5, 11.5, num_velas)
    
    if "COMPRAR" in accion:
        tendencia = np.linspace(35, 25, num_velas) + np.sin(np.linspace(0, 3, num_velas)) * 8
    else:
        tendencia = np.linspace(65, 75, num_velas) + np.cos(np.linspace(0, 3, num_velas)) * 8
        
    for i, x in enumerate(x_vals):
        base_y = tendencia[i]
        # Mecha de la vela
        ax.plot([x, x], [base_y - 7, base_y + 7], color='white', linewidth=1)
        # Cuerpo de la vela
        cuerpo = patches.Rectangle((x - 0.3, base_y - 3.5), 0.6, 7, facecolor='white', edgecolor='white')
        ax.add_patch(cuerpo)

    # 6. Etiquetas de texto institucionales
    ax.text(12.3, y_max, "ALTO", color='white', fontsize=12, fontweight='bold', va='center')
    ax.text(12.3, y_min, "BAJO", color='white', fontsize=12, fontweight='bold', va='center')
    
    # Título limpio superior
    ax.set_title(f"Estructura Institucional ({ticker})", fontsize=13, color='cyan', pad=15, fontweight='bold')
    
    ax.set_xlim(-0.2, 14)
    ax.set_ylim(-10, 110)
    
    plt.tight_layout()
    ruta_imagen = 'analisis_tecnico.png'
    plt.savefig(ruta_imagen, dpi=300, facecolor=fig.get_facecolor())
    plt.close()
    return ruta_imagen
