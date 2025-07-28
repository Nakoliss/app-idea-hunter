"""
JSON structured logging configuration using python-json-logger
"""
import logging
import logging.config
import sys
from typing import Dict, Any

import pythonjsonlogger.jsonlogger

from app.config import get_settings


class CustomJsonFormatter(pythonjsonlogger.jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # Add service name
        log_record['service'] = 'app-idea-hunter'
        
        # Add correlation ID if available
        if hasattr(record, 'correlation_id'):
            log_record['correlation_id'] = record.correlation_id
        
        # Add request ID if available
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id


def setup_logging() -> None:
    """Setup JSON structured logging"""
    settings = get_settings()
    
    # Logging configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': CustomJsonFormatter,
                'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
            },
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': settings.log_level,
                'formatter': 'json' if settings.environment == 'production' else 'standard',
                'stream': sys.stdout
            }
        },
        'loggers': {
            'app': {
                'level': settings.log_level,
                'handlers': ['console'],
                'propagate': False
            },
            'uvicorn': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False
            },
            'uvicorn.access': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False
            }
        },
        'root': {
            'level': settings.log_level,
            'handlers': ['console']
        }
    }
    
    logging.config.dictConfig(config)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            'log_level': settings.log_level,
            'environment': settings.environment
        }
    )