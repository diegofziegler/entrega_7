import os
import logging
from logging.handlers import RotatingFileHandler
from entrega_7.config import settings

def setup_loggers():
    os.makedirs(settings.LOG_DIR, exist_ok=True)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
    )

    # Agentes Logger
    agentes_logger = logging.getLogger("agentes")
    agentes_logger.setLevel(logging.INFO)
    agentes_logger.propagate = False
    if not agentes_logger.handlers:
        agentes_handler = RotatingFileHandler(
            os.path.join(settings.LOG_DIR, "agentes.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        agentes_handler.setFormatter(formatter)
        agentes_logger.addHandler(agentes_handler)

        # Stream handler for console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        agentes_logger.addHandler(console_handler)

    # RAG Logger
    rag_logger = logging.getLogger("rag")
    rag_logger.setLevel(logging.INFO)
    rag_logger.propagate = False
    if not rag_logger.handlers:
        rag_handler = RotatingFileHandler(
            os.path.join(settings.LOG_DIR, "rag.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        rag_handler.setFormatter(formatter)
        rag_logger.addHandler(rag_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        rag_logger.addHandler(console_handler)

    return agentes_logger, rag_logger

agentes_logger, rag_logger = setup_loggers()
