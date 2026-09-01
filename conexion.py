# --- Librerías utilizadas ---
import requests   # Para hacer la petición HTTP a la API de CoinGecko
from datetime import datetime  # Para registrar el momento exacto de la extracción
import pandas as pd    # Para estructurar y transformar los datos en formato tabular
import pyodbc      # Para la conexión con SQL Server (carga de datos)

# Conexión a SQL SERVER (carga de datos)

conexion = pyodbc.connect(
    'DRIVER={ODBC Driver 18 for SQL Server};'
    'SERVER=localhost;'
    'DATABASE=CryptoETL;'
    'Trusted_Connection=yes;'
    'TrustServerCertificate=yes;'
)

# Prueba de conexión: verifico que la conexión esté activa y que pueda ejecutar una consulta simple.

cursor = conexion.cursor()
cursor.execute("SELECT @@VERSION")
resultado = cursor.fetchall()
print(resultado)

# --- Extracción (Extract) ---
# Endpoint público de CoinGecko que devuelve datos de mercado de criptomonedas. No requiere API key para uso liviano dentro de los límites gratuitos.

url = "https://api.coingecko.com/api/v3/coins/markets"

# Parámetros de la consulta: moneda de referencia (USD), orden por capitalización, de mercado descendente, y las primeras 20 criptomonedas (página 1).
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

# Verificación rápida: inspeccionamos las primeras filas y el listado de columnas disponibles antes de decidir con cuáles trabajar

print(df.head())
print(df.columns.to_list())

# ----------------------   PARTE 1 TRANSFORM (Transformación de datos)    ------------------------------------------------------------------------------
# Me quedo solo con las columnas relevantes para el análisis de precios. Se descartan columnas como 'roi' (estructura anidada, muchos valores nulos)
# .copy() asegura que df_final sea un DataFrame independiente

df_final = df[['id', 'symbol', 'name', 'current_price', 'market_cap', 'total_volume',
'high_24h', 'low_24h', 'price_change_percentage_24h', 'market_cap_rank',
'market_cap_change_percentage_24h', 'ath', 'ath_change_percentage']].copy()

# Registro la fecha y hora exacta de esta extracción. Usando datetime.now(), en vez de la columna 'last_updated' de la API porque me interesa saber
# cuándo corrió el pipeline, no cuándo CoinGecko actualizó el dato.

df_final['fecha_captura'] = datetime.now()

# ----------------------   PARTE 2 LOAD (Carga de datos en SQL Server)    --------------------------------------------------------------------------------

# Ahora creo la tabla de staging en SQL SERVER para almacenar los datos crudos.

staging = """
CREATE TABLE stg_CryptoPrecios (
ID_Captura INT IDENTITY(1,1) PRIMARY KEY,
id VARCHAR(100) NOT NULL,
symbol VARCHAR(100) NOT NULL,
name VARCHAR(100) NOT NULL,
current_price DECIMAL(15,8) NOT NULL,
market_cap BIGINT NOT NULL,
total_volume BIGINT NOT NULL,
high_24h DECIMAL(15,8) NOT NULL,
low_24h DECIMAL(15,8) NOT NULL,
price_change_percentage_24h DECIMAL(6,2),
market_cap_rank INT,
market_cap_change_percentage_24h DECIMAL(6,2),
ath DECIMAL(15,8),
ath_change_percentage DECIMAL(6,2),
fecha_captura DATETIME2 NOT NULL
)
"""

cursor.execute(staging) # Ejecuto la consulta para crear la tabla de staging en SQL Server.
conexion.commit()  # Confirmo la creación de la tabla en SQL Server

# Ahora inserto los datos del DataFrame en la tabla de staging. Uso un INSERT parametrizado para evitar inyecciones SQL y problemas con tipos de datos.
insert_query = """
INSERT INTO stg_CryptoPrecios (
    id, symbol, name, current_price, market_cap, total_volume,
    high_24h, low_24h, price_change_percentage_24h, market_cap_rank,
    market_cap_change_percentage_24h, ath, ath_change_percentage, fecha_captura
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

# Itero sobre cada fila del DataFrame y ejecuto el INSERT parametrizado para cada registro.
for index, row in df_final.iterrows():
    cursor.execute(insert_query, (
        row['id'], row['symbol'], row['name'], row['current_price'],
        row['market_cap'], row['total_volume'], row['high_24h'], row['low_24h'],
        row['price_change_percentage_24h'], row['market_cap_rank'],
        row['market_cap_change_percentage_24h'], row['ath'],
        row['ath_change_percentage'], row['fecha_captura']
    ))

conexion.commit()  # confirma las 20 inserciones en la base