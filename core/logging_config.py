# logging_config.py
import logging
from logging.config import dictConfig

def setup_logging(env: str = "development"):
    if env == "production":
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    # Formato JSON con información completa de trazabilidad
                    "format": '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "file": "%(pathname)s", "function": "%(funcName)s", "line": %(lineno)d, "message": "%(message)s"}'
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        }
    else:
        # Desarrollo - formato más legible con colores y trazabilidad completa
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "detailed": {
                    # Formato con información completa de trazabilidad
                    "format": "[%(asctime)s] %(levelname)-8s [%(name)s] [%(pathname)s:%(lineno)d - %(funcName)s()] %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
                "simple": {
                    # Formato compacto con archivo:línea - función
                    "format": "[%(asctime)s] %(levelname)-8s [%(filename)s:%(lineno)d - %(funcName)s] %(message)s",
                    "datefmt": "%H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "detailed",  # Usar 'detailed' para ver rutas completas
                },
            },
            "root": {
                "level": "DEBUG",
                "handlers": ["console"],
            },
            "loggers": {
                "pymongo": {
                    "level": "WARNING"
                },
                "uvicorn": {
                    "level": "INFO"
                },
                "uvicorn.access": {
                    "level": "WARNING"
                }
            }
        }

    dictConfig(config)