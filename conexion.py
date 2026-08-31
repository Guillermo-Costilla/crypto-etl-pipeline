# --- Librerías utilizadas ---
import requests   # Para hacer la petición HTTP a la API de CoinGecko
from datetime import datetime  # Para registrar el momento exacto de la extracción
import pandas as pd    # Para estructurar y transformar los datos en formato tabular
import pyodbc      # Para la conexión con SQL Server (carga de datos)

# --- Extracción (Extract) ---
# Endpoint público de CoinGecko que devuelve datos de mercado de criptomonedas.
# No requiere API key para uso liviano dentro de los límites gratuitos.
url = "https://api.coingecko.com/api/v3/coins/markets"

# Parámetros de la consulta: moneda de referencia (USD), orden por capitalización
# de mercado descendente, y las primeras 20 criptomonedas (página 1).
# sparkline=False porque no necesitamos el historial de precios de 7 días.
params = {
    "vs_currency": "usd",
    "order": "market_cap_desc",
    "per_page": 20,
    "page": 1,
    "sparkline": False
}

# Ejecutamos la petición GET a la API y parseamos la respuesta como JSON
response = requests.get(url, params=params)
data = response.json()

# Convertimos la respuesta (lista de diccionarios) en un DataFrame de pandas
df = pd.DataFrame(data)

# Verificación rápida: inspeccionamos las primeras filas y el listado de
# columnas disponibles antes de decidir con cuáles trabajar
print(df.head())
print(df.columns.to_list())

# --- Selección de columnas (Transform, parte 1) ---
# Me quedo solo con las columnas relevantes para el análisis de precios.
# Se descartan columnas como 'roi' (estructura anidada, muchos valores nulos)
# o 'image' (no aporta valor analítico).
# .copy() asegura que df_final sea un DataFrame independiente, evitando
# el warning de pandas por modificar una vista del DataFrame original.

df_final = df[['id', 'symbol', 'name', 'current_price', 'market_cap', 'total_volume',
               'high_24h', 'low_24h', 'price_change_percentage_24h', 'market_cap_rank',
               'market_cap_change_percentage_24h', 'ath', 'ath_change_percentage']].copy()

# Registramos la fecha y hora exacta de esta extracción. Usando datetime.now()
# en vez de la columna 'last_updated' de la API porque me interesa saber
# cuándo corrió el pipeline, no cuándo CoinGecko actualizó el dato.

df_final['fecha_captura'] = datetime.now()