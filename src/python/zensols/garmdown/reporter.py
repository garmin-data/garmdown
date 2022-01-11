"""Report activities of a day.

"""
__author__ = 'Paul Landes'

from dataclasses import dataclass, field
import logging
import sys
from io import TextIOBase
import json
from zensols.garmdown import Persister

logger = logging.getLogger(__name__)


@dataclass
class Reporter(object):
    """Report activities of a day.

    """
    persister: Persister = field()
    """Use to access backup tracking data."""

    def write_summary(self, date, writer: TextIOBase = sys.stdout):
        """Write the summary of all activities for a day.

        :param date: the date of which to report the activities

        :param writer: the writer object, which default to sys.stdout

        """
        logger.debug(f'summary on day {date}')
        for act in self.persister.get_activities_by_date(date):
            writer.write(f'{act}\n')

    def write_detail(self, date, writer: TextIOBase = sys.stdout):
        """Write the detailed attributes of all activities for a day.

        :param date: the date of which to report the activities

        :param writer: the writer object, which default to sys.stdout

        """
        logger.debug(f'detail on day {date}')
        for act in self.persister.get_activities_by_date(date):
            act.write(writer)

    def write_json(self, date, writer: TextIOBase = sys.stdout):
        """Write the JSON, which contains all the data of all activities for a day.

        :param date: the date of which to report the activities

        :param writer: the writer object, which default to sys.stdout

        """
        logger.debug(f'raw on day {date}')
        acts = tuple(map(lambda x: x.raw,
                         self.persister.get_activities_by_date(date)))
        json.dump(acts, writer, indent=4)
