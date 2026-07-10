"""Serviço de log de atividades da aplicação.

Registra ações do usuário (quem fez, o que fez, se deu certo ou não e
informações adicionais relevantes) na tabela `dbo.activity_logs`.

Quando a ação for a geração de um BPMN com sucesso, o conteúdo gerado
(blob) é salvo na tabela `dbo.bpmn_outputs`, referenciando o log
correspondente através de uma chave estrangeira (`log_id`).
"""

import json

from utils.db import ensure_database, get_connection, load_env_files

STATUS_SUCCESS = "success"
STATUS_ERROR = "error"


class LogError(RuntimeError):
    pass


class LogService:
    def __init__(self) -> None:
        load_env_files()

    def ensure_ready(self) -> None:
        ensure_database()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                IF NOT EXISTS (
                    SELECT 1 FROM sys.objects
                    WHERE object_id = OBJECT_ID(N'dbo.activity_logs') AND type = N'U'
                )
                BEGIN
                    CREATE TABLE dbo.activity_logs (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        user_email NVARCHAR(320) NULL,
                        action NVARCHAR(100) NOT NULL,
                        status NVARCHAR(20) NOT NULL,
                        message NVARCHAR(MAX) NULL,
                        details NVARCHAR(MAX) NULL,
                        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
                    )
                END
                """)
            cursor.execute("""
                IF NOT EXISTS (
                    SELECT 1 FROM sys.objects
                    WHERE object_id = OBJECT_ID(N'dbo.bpmn_outputs') AND type = N'U'
                )
                BEGIN
                    CREATE TABLE dbo.bpmn_outputs (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        log_id INT NOT NULL,
                        file_name NVARCHAR(260) NULL,
                        content VARBINARY(MAX) NOT NULL,
                        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
                        CONSTRAINT FK_bpmn_outputs_logs FOREIGN KEY (log_id)
                            REFERENCES dbo.activity_logs(id)
                    )
                END
                """)
            conn.commit()

    def log_action(
        self,
        user_email: str | None,
        action: str,
        status: str,
        message: str | None = None,
        details: dict | None = None,
    ) -> int:
        """Registra uma ação e retorna o id do log gerado."""
        details_json = json.dumps(details, ensure_ascii=False) if details else None
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO dbo.activity_logs (user_email, action, status, message, details)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, ?, ?)
                """,
                user_email,
                action,
                status,
                message,
                details_json,
            )
            log_id = cursor.fetchone()[0]
            conn.commit()
            return log_id

    def save_bpmn_output(
        self, log_id: int, content: bytes, file_name: str | None = None
    ) -> None:
        """Salva o blob do BPMN gerado, referenciando o log através de FK."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO dbo.bpmn_outputs (log_id, file_name, content)
                VALUES (?, ?, ?)
                """,
                log_id,
                file_name,
                content,
            )
            conn.commit()
