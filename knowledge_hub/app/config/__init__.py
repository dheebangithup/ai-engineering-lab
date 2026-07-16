import logging

from .app_settings import AppSettings

app_settings = AppSettings()
app_logger = logging.getLogger("app")


__all__ = ['app_settings', 'app_logger']

