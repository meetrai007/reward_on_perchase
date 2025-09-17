import os
from logging.handlers import TimedRotatingFileHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'verbose': {
            'format': "[{asctime}] {levelname} [{name}:{lineno}] {message}",
            'style': '{',
        },
        'simple': {
            'format': "{levelname} {message}",
            'style': '{',
        },
    },

    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'when': 'midnight',
            'interval': 1,
            'backupCount': 7,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'error.log'),
            'when': 'midnight',
            'interval': 1,
            'backupCount': 14,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },

    'root': {
        'handlers': ['file', 'error_file', 'console'],
        'level': 'INFO',
    },

    'loggers': {
        'django': {
            'handlers': ['file', 'error_file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'common_file': {
            'handlers': ['file', 'error_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Custom apps
        'apis': {
            'handlers': ['file', 'error_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'rewards': {
            'handlers': ['file', 'error_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}
