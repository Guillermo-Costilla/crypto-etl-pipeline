import pyodbc  # Para la conexión con SQL Server (carga de datos)
from datetime import datetime
from dotenv import load_dotenv
import os
import sys
    
load_dotenv()

servidor = os.getenv('DB_SERVER')
base = os.getenv('DB_DATABASE')
usuario = os.getenv('DB_UID')
contraseña = os.getenv('DB_PWD')

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
conexion.close()