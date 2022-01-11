"""Download Garmin connect data application entry point.

"""
__author__ = '${user-name}'

from dataclasses import dataclass, field
import logging
#from pathlib import Path
from . import Manager

logger = logging.getLogger(__name__)


@dataclass
class InfoApplication(object):
    """Download Garmin connect data application.

    """
    manager: Manager = field()

    def proto(self):
        self.manager.write_not_imported()
