"""Download Garmin connect data application entry point.

"""
__author__ = '${user-name}'

from dataclasses import dataclass, field
import logging
#from pathlib import Path
from . import Manager, Fetcher

logger = logging.getLogger(__name__)


@dataclass
class InfoApplication(object):
    """Download Garmin connect data application.

    """
    #manager: Manager = field()
    fetcher: Fetcher

    def proto(self):
        #print(self.fetcher)
        for act in self.fetcher.get_activities():
            print(act)
