"""Fetches activities and downloads TCX files from Garmin.

"""
__author__ = 'Paul Landes'

from dataclasses import dataclass, field
import logging
import itertools as it
from io import TextIOBase
from garminexport.garminclient import GarminClient
from zensols.persist import persisted
from zensols.config import Settings
from . import ActivityFactory

logger = logging.getLogger(__name__)


@dataclass
class Fetcher(object):
    """Downloads Garmin TXC files and activities (metadata).

    """
    activity_factory: ActivityFactory = field()
    """Create activity instances."""

    login: Settings = field()
    """The login creds for Garmin Connect."""

    download: Settings = field()
    """The download settings configuration."""

    retry_delay: int = field(default=1)
    """Initially, number of seconds to wait before retrying to contact Garmin
    Connect.  For each timeout, the number of seconds on each retry (see
    :obj:`retries`) grows exponentially.

    """

    max_retries: int = field(default=6)
    """The max number of retries when accessing Garmin Connect before failing.

    """
    @property
    @persisted('_client', cache_global=True)
    def client(self) -> GarminClient:
        """The client that manages the connection to the Garmin Connect server.
        """
        login = self.login
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'logging in with {login.username}')
        client = GarminClient(login.username, login.password,
                              retry_delay=self.retry_delay,
                              max_retries=self.max_retries)
        client.connect()
        return client

    def _iterate_activities(self, index: int, chunk_size: int):
        """Yield downloaded activities.

        :param index: the 0 based activity index (not contiguous page based)

        :param chunk_size: how large the batch for each invocation

        """
        afactory = self.activity_factory
        search = self.client.fetch_activities(index, chunk_size)
        for item in search:
            activity = afactory.create(item)
            logger.debug(f'activity: {activity}')
            yield activity

    def get_activities(self, limit: int = None, start_index: int = 0):
        """Download and return ``limit`` activities.

        :param limit: the number of activities to download
        :param start_index: the 0 based activity index (not contiguous page
            based)
        """
        activity_chunk_size = self.download.activity_chunk_size
        activity_num = self.download.activity_num
        if limit is None:
            limit = activity_chunk_size
        al = map(lambda x: self._iterate_activities(x, activity_chunk_size),
                 range(start_index, activity_num, activity_chunk_size))
        return it.islice(it.chain(*al), limit)

    def download_tcx(self, activity_id: int, writer: TextIOBase):
        """Download the TCX file for ``activity`` and dump the contents to ``writer``.

        """
        content: str = self.client.get_activity_tcx(activity_id)
        writer.write(content)
