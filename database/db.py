# database/db.py
# Conexión a la base de datos

import sqlite3
import os

RUTA_BD = os.path.join(os.path.dirname(__file__), '..', 'database', 'uv.db')

def get_connection():
    """Retorna una conexión a la base de datos SQLite"""
    try:
        conn = sqlite3.connect(RUTA_BD)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")
        raise