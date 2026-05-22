import hashlib
import os
import re
import secrets
import smtplib
import ssl
import string
import sys
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

import bcrypt
import pyodbc
from dotenv import load_dotenv


class AuthError(RuntimeError):
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


def _load_env_files() -> None:
    candidates = [
        _APP_BASE_PATH / ".env",
        _BUNDLE_BASE_PATH / ".env",
        _BUNDLE_BASE_PATH / "_internal" / ".env",
    ]
    for env_path in candidates:
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)


def _get_env(name: str, default: str | None = None, *aliases: str) -> str | None:
    for key in (name, *aliases):
        value = os.getenv(key)
        if value:
            return value
    return default


def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise AuthError(f"Valor inválido para {name}") from exc


def _get_env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _is_allowed_email_domain(email: str) -> bool:
    domain = email.rsplit("@", 1)[-1]
    return domain == "tcepe.tc.br"


def _validate_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise AuthError("DB_NAME deve conter apenas letras, números ou underscore")
    return name


def _build_conn_str(database: str) -> str:
    driver = _get_env("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    server = _get_env("DB_SERVER", "localhost,1433")
    user = _get_env("DB_USER", "sa")
    password = _get_env("DB_PASSWORD", None, "MSSQL_SA_PASSWORD")
    encrypt = _get_env("DB_ENCRYPT", "yes")
    trust_cert = _get_env("DB_TRUST_CERT", "yes")

    if not password:
        raise AuthError("DB_PASSWORD (ou MSSQL_SA_PASSWORD) é obrigatório")

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


def _ensure_database() -> str:
    db_name = _validate_identifier(_get_env("DB_NAME", "tce_bpmn"))
    master_conn_str = _build_conn_str("master")
    with pyodbc.connect(master_conn_str, autocommit=True) as conn:
        cursor = conn.cursor()
        cursor.execute(f"IF DB_ID(N'{db_name}') IS NULL CREATE DATABASE [{db_name}]")
    return db_name


def _connect_db() -> pyodbc.Connection:
    db_name = _validate_identifier(_get_env("DB_NAME", "tce_bpmn"))
    return pyodbc.connect(_build_conn_str(db_name))


def _hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def _generate_temp_password(length: int) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _generate_otp() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def _send_email(to_email: str, subject: str, body: str) -> None:
    host = _get_env("SMTP_HOST")
    port = _get_env_int("SMTP_PORT", 587)
    user = _get_env("SMTP_USER")
    password = _get_env("SMTP_PASSWORD")
    from_addr = _get_env("SMTP_FROM", user)
    use_tls = _get_env_bool("SMTP_TLS", True)
    use_ssl = _get_env_bool("SMTP_SSL", False)

    if not host or not from_addr:
        raise AuthError("Configuração SMTP ausente")

    message = EmailMessage()
    message["From"] = from_addr
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    context = ssl.create_default_context()

    if use_ssl:
        with smtplib.SMTP_SSL(host, port, context=context) as server:
            if user and password:
                server.login(user, password)
            server.send_message(message)
        return

    with smtplib.SMTP(host, port) as server:
        if use_tls:
            server.starttls(context=context)
        if user and password:
            server.login(user, password)
        server.send_message(message)


class AuthService:
    def __init__(self) -> None:
        _load_env_files()

    def ensure_ready(self) -> None:
        _ensure_database()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with _connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                IF NOT EXISTS (
                    SELECT 1 FROM sys.objects
                    WHERE object_id = OBJECT_ID(N'dbo.users') AND type = N'U'
                )
                BEGIN
                    CREATE TABLE dbo.users (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        email NVARCHAR(320) NOT NULL UNIQUE,
                        password_hash NVARCHAR(200) NOT NULL,
                        must_change_password BIT NOT NULL DEFAULT 1,
                        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
                        updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
                    )
                END
                """)
            cursor.execute("""
                IF COL_LENGTH('dbo.users', 'must_change_password') IS NULL
                BEGIN
                    ALTER TABLE dbo.users
                    ADD must_change_password BIT NOT NULL
                        CONSTRAINT DF_users_must_change_password DEFAULT 1
                END
                """)
            cursor.execute("""
                IF NOT EXISTS (
                    SELECT 1 FROM sys.objects
                    WHERE object_id = OBJECT_ID(N'dbo.user_otps') AND type = N'U'
                )
                BEGIN
                    CREATE TABLE dbo.user_otps (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        user_id INT NOT NULL,
                        otp_hash CHAR(64) NOT NULL,
                        expires_at DATETIME2 NOT NULL,
                        used_at DATETIME2 NULL,
                        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
                        CONSTRAINT FK_user_otps_users FOREIGN KEY (user_id)
                            REFERENCES dbo.users(id)
                    )
                END
                """)
            conn.commit()

    def authenticate(self, email: str, password: str) -> bool:
        email = _normalize_email(email)
        with _connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT password_hash, must_change_password FROM dbo.users WHERE email = ?",
                email,
            )
            row = cursor.fetchone()
            if not row:
                return False
            if row[1]:
                raise AuthError("A senha inicial precisa ser alterada com a OTP.")
            return _verify_password(password, row[0])

    def register_user(self, email: str) -> None:
        email = _normalize_email(email)
        if not email:
            raise AuthError("Email é obrigatório")
        if not _is_allowed_email_domain(email):
            raise AuthError("Apenas email institucional @tcepe.tc.br é permitido")

        temp_length = _get_env_int("TEMP_PASSWORD_LENGTH", 16)
        otp_minutes = _get_env_int("OTP_EXPIRATION_MINUTES", 15)
        temp_password = _generate_temp_password(temp_length)
        password_hash = _hash_password(temp_password)
        otp = _generate_otp()
        otp_hash = _hash_otp(otp)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=otp_minutes)

        with _connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM dbo.users WHERE email = ?", email)
            if cursor.fetchone():
                raise AuthError("Usuário já existe")

            cursor.execute(
                """
                INSERT INTO dbo.users (email, password_hash, must_change_password)
                OUTPUT INSERTED.id
                VALUES (?, ?, 1)
                """,
                email,
                password_hash,
            )
            user_id = cursor.fetchone()[0]

            cursor.execute(
                "INSERT INTO dbo.user_otps (user_id, otp_hash, expires_at) VALUES (?, ?, ?)",
                user_id,
                otp_hash,
                expires_at,
            )
            conn.commit()

        app_name = _get_env("APP_NAME", "BPMN Generator")
        subject = f"{app_name} - Código OTP"
        body = (
            f"Olá,\n\n"
            f"Sua conta foi criada.\n"
            f"Código OTP: {otp}\n"
            f"A OTP expira em {otp_minutes} minutos.\n\n"
            f"Use a OTP para definir uma nova senha antes do login."
        )
        try:
            _send_email(email, subject, body)
        except Exception as exc:
            raise AuthError(
                "Usuário criado, mas falha no envio do email. Use a opção de reenviar OTP."
            ) from exc

    def issue_otp(self, email: str) -> None:
        email = _normalize_email(email)
        if not email:
            raise AuthError("Email é obrigatório")

        otp_minutes = _get_env_int("OTP_EXPIRATION_MINUTES", 15)
        otp = _generate_otp()
        otp_hash = _hash_otp(otp)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=otp_minutes)

        with _connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM dbo.users WHERE email = ?", email)
            row = cursor.fetchone()
            if not row:
                raise AuthError("Usuário não encontrado")

            user_id = row[0]
            cursor.execute(
                "INSERT INTO dbo.user_otps (user_id, otp_hash, expires_at) VALUES (?, ?, ?)",
                user_id,
                otp_hash,
                expires_at,
            )
            conn.commit()

        app_name = _get_env("APP_NAME", "BPMN Generator")
        subject = f"{app_name} - Código OTP"
        body = (
            f"Olá,\n\n" f"Código OTP: {otp}\n" f"A OTP expira em {otp_minutes} minutos."
        )
        try:
            _send_email(email, subject, body)
        except Exception as exc:
            raise AuthError(
                "Falha no envio do email. Tente novamente mais tarde."
            ) from exc

    def reset_password(self, email: str, otp: str, new_password: str) -> None:
        email = _normalize_email(email)
        if not email or not otp or not new_password:
            raise AuthError("Email, OTP e nova senha são obrigatórios")

        otp_hash = _hash_otp(otp)
        new_hash = _hash_password(new_password)

        with _connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT TOP 1 o.id
                FROM dbo.user_otps o
                INNER JOIN dbo.users u ON u.id = o.user_id
                WHERE u.email = ?
                  AND o.otp_hash = ?
                  AND o.used_at IS NULL
                  AND o.expires_at > SYSUTCDATETIME()
                ORDER BY o.created_at DESC
                """,
                email,
                otp_hash,
            )
            row = cursor.fetchone()
            if not row:
                raise AuthError("OTP inválida ou expirada")

            otp_id = row[0]
            cursor.execute(
                """
                UPDATE dbo.users
                SET password_hash = ?,
                    must_change_password = 0,
                    updated_at = SYSUTCDATETIME()
                WHERE email = ?
                """,
                new_hash,
                email,
            )
            cursor.execute(
                "UPDATE dbo.user_otps SET used_at = SYSUTCDATETIME() WHERE id = ?",
                otp_id,
            )
            conn.commit()
