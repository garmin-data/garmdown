from dataclasses import dataclass, field
import logging
import json
import re
import itertools as it
from robobrowser import RoboBrowser
from zensols.persist import persisted
from zensols.config import Settings
from . import ActivityFactory
from garminexport.garminclient import GarminClient

logger = logging.getLogger(__name__)


@dataclass
class Fetcher(object):
    """Downloads Garmin TXC files and activities (metadata).

    """
    activity_factory: ActivityFactory
    login: Settings
    download: Settings
    web: Settings

    def __post_init__(self):
        """Initialize

        :param config: the application configuration
        """
        #self.config = config
        #self.web = self.config.web
        #self.fetch_params = self.config.fetch
        self._login_state = 'loggedout'

    # @property
    # @persisted('_activity_factory')
    # def activity_factory(self):
    #     return ActivityFactory(self.config)

    @property
    @persisted('_browser', cache_global=True)
    def browser(self):
        "The ``RoboBrowser`` instance."
        logger.debug('creating browser...')
        return RoboBrowser(
            history=True, parser='lxml',
            user_agent=self.web.agent,
            session=self.session)

    def _login(self):
        """Login in the garmin connect site with athlete credentials.
        """
        login = self.login
        logger.info(f'logging in with {login.username}')
        client = GarminClient(login.username, login.password)
        client.connect()
        self.session = client.session
        self._login_state = 'success'

    def _assert_logged_in(self):
        """Log in if we're not and raise an error if we can't.

        """
        if self._login_state != 'success':
            self._login()

        # the web site seems to need to have this URL touched, otherwise we get
        # errors when downloading activities
        if not hasattr(self, '_preempt'):
            logger.info('preepting login')
            self.browser.open(self.web.preempt_activities)
            self._preempt = True

    def _download_activities(self, index, chunk_size):
        """Use robobrowser to download activities, parse JSON and return them.

        :param index: the 0 based activity index (not contiguous page based)

        :param chunk_size: how large the batch for each invocation

        """
        self._assert_logged_in()
        params = {'index': index,
                  'activity_chunk_size': chunk_size}
        url = self.web.activities.format(**params)
        logger.info(f'downloading {chunk_size} activities at index {index}')
        self.browser.open(url)
        jobj = json.loads(self.browser.parsed.html.body.p.text)
        if isinstance(jobj, dict) and 'error' in jobj:
            raise ValueError('can not parse activities')
        return jobj

    def _iterate_activities(self, index, chunk_size):
        """Yield downloaded activities.

        :param index: the 0 based activity index (not contiguous page based)

        :param chunk_size: how large the batch for each invocation

        """
        self._assert_logged_in()
        afactory = self.activity_factory
        search = self._download_activities(index, chunk_size)
        for item in search:
            activity = afactory.create(item)
            logger.debug(f'activity: {activity}')
            yield activity

    def get_activities(self, limit=None, start_index=0):
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

    def download_tcx(self, activity, writer):
        """Download the TCX file for ``activity`` and dump the contents to ``writer``.

        """
        self._assert_logged_in()
        url = self.web.tcx.format(**{'activity': activity})
        logger.info(f'downloading TCX for {activity} at {url}')
        self.browser.open(url)
        writer.write(self.browser.response.content)

    def close(self):
        """Close the fetcher.  It appears robobrowser doesn't need to be closed so this
        is a no-op for now.

        """
        logger.debug('closing fetcher')

    def tmp(self):
        self._login()
