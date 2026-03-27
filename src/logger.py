import logging
import os


def configure_logging(log_file=None):
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        handlers=[
            # logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(),
        ]
    )


def get_logger():
    return logging.getLogger('voice_assistant')
