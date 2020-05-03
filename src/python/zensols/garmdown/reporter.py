import logging
import sys
import json
from zensols.garmdown import Persister

logger = logging.getLogger(__name__)


class Reporter(object):
    """Report that activities of a day.
    """

    def __init__(self, config):
        """Initialize

        :param config: the application configuration
        """
        self.config = config

    @property
    def persister(self):
        "The DB DAO."
        return Persister(self.config)

    def write_summary(self, date, writer=sys.stdout):
        """Write the summary of all activities for a day.

        :param date: the date of which to report the activities
        :type date: datetime.datetime
        :param writer: the writer object, which default to sys.stdout

        """
        logger.debug(f'summary on day {date}')
        for act in self.persister.get_activities_by_date(date):
            writer.write(f'{act}\n')

    def write_detail(self, date, writer=sys.stdout):
        """Write the detailed attributes of all activities for a day.

        :param date: the date of which to report the activities
        :type date: datetime.datetime
        :param writer: the writer object, which default to sys.stdout

        """
        logger.debug(f'detail on day {date}')
        for act in self.persister.get_activities_by_date(date):
            act.write(writer)

    def write_json(self, date, writer=sys.stdout):
        """Write the JSON, which contains all the data of all activities for a day.

        :param date: the date of which to report the activities
        :type date: datetime.datetime
        :param writer: the writer object, which default to sys.stdout

        """
        logger.debug(f'raw on day {date}')
        acts = tuple(map(lambda x: x.raw,
                         self.persister.get_activities_by_date(date)))
        json.dump(acts, writer, indent=4)
