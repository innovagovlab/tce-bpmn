"""Utilitários compartilhados de conexão com o banco de dados (SQL Server)."""

import os
import re
import sys
from pathlib import Path

import pyodbc
from dotenv import load_dotenv


class DbError(RuntimeError):
    pass


def _bundle_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


def _app_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


_BUNDLE_BASE_PATH = _bundle_base_path()
_APP_BASE_PATH = _app_base_path()


def load_env_files() -> None:
    candidates = [
        _APP_BASE_PATH / ".env",
        _BUNDLE_BASE_PATH / ".env",
        _BUNDLE_BASE_PATH / "_internal" / ".env",
    ]
    for env_path in candidates:
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)


def get_env(name: str, default: str | None = None, *aliases: str) -> str | None:
    for key in (name, *aliases):
        value = os.getenv(key)
        if value:
            return value
    return default


def get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise DbError(f"Valor inválido para {name}") from exc


def get_env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def validate_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise DbError("DB_NAME deve conter apenas letras, números ou underscore")
    return name


def build_conn_str(database: str) -> str:
    driver = get_env("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    server = get_env("DB_SERVER", "localhost,1433")
    user = get_env("DB_USER", "sa")
    password = get_env("DB_PASSWORD", None, "MSSQL_SA_PASSWORD")
    encrypt = get_env("DB_ENCRYPT", "yes")
    trust_cert = get_env("DB_TRUST_CERT", "yes")

    if not password:
        raise DbError("DB_PASSWORD (ou MSSQL_SA_PASSWORD) é obrigatório")

    return (
        f"Driver={{{driver}}};"
        f"Server={server};"
        f"Database={database};"
        f"UID={user};"
        f"PWD={password};"
        f"Encrypt={encrypt};"
        f"TrustServerCertificate={trust_cert};"
        "Connection Timeout=5;"
    )


def ensure_database() -> str:
    db_name = validate_identifier(get_env("DB_NAME", "tce_bpmn"))
    master_conn_str = build_conn_str("master")
    with pyodbc.connect(master_conn_str, autocommit=True) as conn:
        cursor = conn.cursor()
        cursor.execute(f"IF DB_ID(N'{db_name}') IS NULL CREATE DATABASE [{db_name}]")
    return db_name


def get_connection() -> pyodbc.Connection:
    db_name = validate_identifier(get_env("DB_NAME", "tce_bpmn"))
    return pyodbc.connect(build_conn_str(db_name))
