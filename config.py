import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

# === SOC ===
SOC_ENDPOINT = os.getenv("SOC_ENDPOINT")
SOC_USUARIO = os.getenv("SOC_USUARIO")
SOC_SENHA = os.getenv("SOC_SENHA")
SOC_CODIGO_EMPRESA_PRINCIPAL = os.getenv("SOC_CODIGO_EMPRESA_PRINCIPAL")
SOC_CODIGO_RESPONSAVEL = os.getenv("SOC_CODIGO_RESPONSAVEL")

# === TOTVS RM ===
RM_ENDPOINT = os.getenv("RM_ENDPOINT")
RM_USER = os.getenv("RM_USER")
RM_PASS = os.getenv("RM_PASS")
RM_AUTH = (RM_USER, RM_PASS)

NDIAS = int(os.getenv("DIAS_RETROATIVOS", "2"))
data_inicio = (datetime.now() - timedelta(days=NDIAS)).strftime("%d/%m/%Y")

# === SQL Server (log de processamento) ===
SQL_SERVER_CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={os.getenv('SQLSERVER_HOST')},{os.getenv('SQLSERVER_PORT', '1433')};"
    f"DATABASE={os.getenv('SQLSERVER_DATABASE')};"
    f"UID={os.getenv('SQLSERVER_USER')};"
    f"PWD={os.getenv('SQLSERVER_PASSWORD')};"
)

# === Mapeamentos de negócio SOC -> RM ===
MAPA_MOTIVO_AFAST = {
    "1": "32", "2": "24", "3": "06", "4": "16", "5": "32",
    "6": "24", "7": "31", "8": "28", "9": "34", "10": "24",
}

MAPA_CODTP_ATESTADO = {
    "1": "06", "2": "04", "3": "01", "4": "03",
    "5": "05", "6": "07", "7": "02", "8": "08",
}

# Mapa de empresas SOC -> coligadas RM (exemplo ilustrativo)
EMPRESA_CODCOLIGADA = {
    "SOC_EMPRESA_1": 1,
    "SOC_EMPRESA_2": 2,
    "SOC_EMPRESA_3": 3,
    "SOC_EMPRESA_4": 4,
    "SOC_EMPRESA_5": 7,
    "SOC_EMPRESA_6": 8,
}
