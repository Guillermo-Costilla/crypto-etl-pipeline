import requests
import sys
from datetime import datetime
import pandas as pd
import pyodbc
from dotenv import load_dotenv
import os
    
load_dotenv()

servidor = os.getenv('DB_SERVER')
base = os.getenv('DB_DATABASE')
usuario = os.getenv('DB_UID')
contraseña = os.getenv('DB_PWD')

# Endpoint público de CoinGecko que devuelve datos de mercado de criptomonedas. No requiere API key para uso liviano dentro de los límites gratuitos.
url = "https://api.coingecko.com/api/v3/coins/markets"

# Función chica que registra un mensaje en un archivo de log, agregando la fecha y hora automáticamente
def registrar_log(mensaje):
    with open("log_pipeline.txt", "a") as archivo:
        archivo.write(f"{datetime.now()} - {mensaje}\n")

# --- Conexión a SQL Server ---
try:
    conexion = pyodbc.connect(
    'DRIVER={ODBC Driver 18 for SQL Server};'
    f'SERVER={servidor};'
    f'DATABASE={base};'
    f'UID={usuario};'
    f'PWD={contraseña};'
    'Encrypt=yes;'
    'TrustServerCertificate=no;'
    'Connection Timeout=30;'
    )
    cursor = conexion.cursor()
    registrar_log("Conexión a SQL Server (Azure) exitosa")
except Exception as error:
    registrar_log(f"ERROR de conexión: {error}")
    sys.exit(1)
    # si no hay conexión, no tiene sentido seguir con el resto del script


# ----------------------   PARTE 1 EXTRACT (Extraemos los datos de la API)    --------------------------------------------------------------------------------

# Parámetros de la consulta: moneda de referencia (USD), orden por capitalización, de mercado descendente, y las primeras 20 criptomonedas (página 1).
# sparkline=False porque no necesitamos el historial de precios de 7 días.

params = {
    "vs_currency": "usd",
    "order": "market_cap_desc",
    "per_page": 20,
    "page": 1,
    "sparkline": False
}

try:
    registrar_log("Inicio de extracción")
    response = requests.get(url, params=params) # Ejecutamos la petición GET a la API
    data = response.json() # y parseamos la respuesta como JSON
    df = pd.DataFrame(data) # Convertimos la respuesta (lista de diccionarios) en un DataFrame de pandas
    registrar_log(f"Se extrajeron {len(df)} filas de la API")
    df_final = df[['id', 'symbol', 'name', 'current_price', 'market_cap', 'total_volume',
                    'high_24h', 'low_24h', 'price_change_percentage_24h', 'market_cap_rank',
                    'market_cap_change_percentage_24h', 'ath', 'ath_change_percentage']].copy()
    df_final['fecha_captura'] = datetime.now()
    registrar_log(f"Se extrajeron las columnas relevantes: {df_final.columns.to_list()}")
except Exception as error:
    registrar_log(f"ERROR en la extracción: {error}")
    conexion.close()
    sys.exit(1) # si no hay datos, no tiene sentido seguir con el resto del script

# ----------------------   PARTE 2 LOAD (Carga de datos en SQL Server)    --------------------------------------------------------------------------------

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
try:
    for index, row in df_final.iterrows():
        cursor.execute(insert_query, (
            row['id'], row['symbol'], row['name'], row['current_price'],
            row['market_cap'], row['total_volume'], row['high_24h'], row['low_24h'],
            row['price_change_percentage_24h'], row['market_cap_rank'],
            row['market_cap_change_percentage_24h'], row['ath'],
            row['ath_change_percentage'], row['fecha_captura']
        ))
    registrar_log("Carga completada exitosamente")
    conexion.commit()  # confirma las 20 inserciones en la base

# --- Transform: mover los datos de staging al esquema estrella ---
    cursor.execute("EXEC TransformarStaging")
    conexion.commit()
    registrar_log("Transformacion a esquema estrella completada")
except Exception as error:
    registrar_log(f"ERROR en la carga: {error}")
    conexion.rollback()  # si hay error, deshace los cambios

conexion.close()