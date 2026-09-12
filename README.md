# Crypto ETL Pipeline

Pipeline de datos automatizado que extrae precios de criptomonedas en tiempo real, los transforma en un esquema estrella y los deja listos para análisis en Power BI — corriendo solo, en la nube, sin depender de que ninguna PC esté encendida.

## El problema original

Quería armar un proyecto de portfolio para analizar criptomonedas en Power BI. El primer enfoque hubiera sido simple: descargar un dataset de precios una sola vez y construir un dashboard estático sobre esa foto congelada en el tiempo.

Pero un dashboard de criptomonedas con datos de "una sola vez" pierde su sentido casi de inmediato — el mercado cripto se mueve minuto a minuto, y un análisis real necesita **historial**, no una captura aislada. La pregunta que definió el proyecto fue: *¿cómo logro que los datos se actualicen solos, de forma confiable, sin que yo tenga que ejecutar nada a mano cada vez?*

Esa pregunta llevó a un proyecto bastante más ambicioso de lo planeado: en el camino terminé construyendo un pipeline completo, aprendiendo Python más a fondo, SQL Server, arquitectura en la nube con Azure y automatización con GitHub Actions.

## Arquitectura: ELT, no ETL

El pipeline sigue el patrón **ELT** (Extract, Load, Transform) en vez del más tradicional ETL:

1. **Extract**: Python trae los datos crudos desde la API pública de [CoinGecko](https://www.coingecko.com/), sin modificarlos.
2. **Load**: esos datos crudos se cargan tal cual a una tabla de *staging* (`stg_CryptoPrecios`) en SQL Server.
3. **Transform**: un stored procedure en T-SQL toma esos datos crudos y los reparte en un esquema estrella, aprovechando el motor de la base de datos para el procesamiento en vez de hacerlo en Python.

La ventaja de este orden: si en algún momento la lógica de transformación tuviera un error, el dato original crudo sigue intacto en staging y se puede reprocesar sin volver a consultar la API.

## El esquema estrella

- **`DimCripto`** — datos estables de cada moneda (id, symbol, name).
- **`DimFecha`** — una fila por cada timestamp de captura, con columnas derivadas (hora, día, mes, año) para facilitar el análisis por franjas horarias en Power BI.
- **`FactPrecios`** — la tabla de hechos: una fila por cada combinación de criptomoneda + momento de captura, con las métricas numéricas (precio actual, máximos y mínimos de 24hs, capitalización de mercado, volumen, variaciones porcentuales).

## Stack técnico

- **Python** (`requests`, `pandas`, `pyodbc`, `python-dotenv`) para la extracción y carga
- **SQL Server / Azure SQL Database** para el almacenamiento y la transformación (T-SQL)
- **GitHub Actions** como orquestador, ejecutando el pipeline de forma periódica
- **Power BI** para el modelado final y la visualización

## Infraestructura en la nube

La base de datos vive en **Azure SQL Database**, en el nivel gratuito (*serverless*, con auto-pausado por inactividad). Esta decisión resolvió el problema original: como el pipeline corre en GitHub Actions y no en una PC local, la base de datos tampoco podía depender de una máquina personal encendida.

Un detalle de diseño no trivial: las bases *serverless* se pausan automáticamente tras un período de inactividad, y el primer intento de conexión después de una pausa puede tardar más que un timeout estándar. El script de extracción incluye lógica de reintento con espera entre intentos para manejar este comportamiento de forma resiliente.

## Automatización

Un workflow de GitHub Actions (`.github/workflows/extraccion.yml`) ejecuta el pipeline de forma periódica:

- Instala el driver ODBC de Microsoft para SQL Server en el runner de Linux
- Instala las dependencias de Python
- Ejecuta el script de extracción y carga, con las credenciales inyectadas de forma segura vía **GitHub Secrets** (nunca expuestas en el código)

> **Nota:** los triggers programados (`schedule`) de GitHub Actions funcionan bajo un esquema de "mejor esfuerzo", no garantizan puntualidad exacta — el intervalo real de ejecución puede variar respecto al configurado, según la carga de los servidores de GitHub en cada momento.

## Estructura del repositorio

```
crypto-etl-pipeline/
├── .github/workflows/
│   └── extraccion.yml       # Workflow de automatización
├── crear_tabla.py           # Crea la tabla de staging (se ejecuta una sola vez)
├── extraer_cargar.py        # Extract + Load + Transform (se ejecuta periódicamente)
├── .env                     # Credenciales locales (excluido del repositorio)
└── .gitignore
```

## Aprendizajes clave del proyecto

- Separar responsabilidades en archivos distintos según su ciclo de vida (setup único vs. ejecución recurrente)
- Manejo de errores por fase con `try/except`, logging y cortes controlados de ejecución (`sys.exit`)
- Diseño de tipos de datos en SQL pensando en el caso de uso real (por ejemplo, `DECIMAL` en vez de `FLOAT` para evitar errores de redondeo en precios financieros, `BIGINT` para magnitudes de capitalización de mercado)
- Manejo seguro de credenciales con variables de entorno y GitHub Secrets
- Diseño de un esquema estrella desde una fuente de datos en vivo, no desde un dataset estático
