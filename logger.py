import logging
import os
from datetime import datetime


def setup_logger():
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_filename = os.path.join(
        log_dir, datetime.now().strftime("scrape_%Y%m%d_%H%M%S.log")
    )
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    return logging.getLogger(__name__)
