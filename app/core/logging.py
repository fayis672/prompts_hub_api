import logging
import sys
from typing import Any

from app.core.config import settings

def setup_logging() -> None:
    """
    Configure logging for the application.
    """
    log_level = settings.LOG_LEVEL.upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # set up root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # set up uvicorn logger
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.error").handlers = []
    
    # ensure everything uses our format
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    for handler in logger.handlers:
        handler.setFormatter(formatter)
