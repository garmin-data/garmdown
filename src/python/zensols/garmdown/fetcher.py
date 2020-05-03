import logging
import json
import re
import itertools as it
import urllib.parse as up
from robobrowser import RoboBrowser
from zensols.persist import persisted
from zensols.garmdown import ActivityFactory

logger = logging.getLogger(__name__)


class Fetcher(object):
    """Downloads Garmin TXC files and activities (metadata).

    """

    def __init__(self, config):
        """Initialize

        :param config: the application configuration
        """
        self.config = config
        self.web = self.config.web
        self.fetch_params = self.config.fetch
        self.login_state = 'loggedout'

    @property
    @persisted('_activity_factory')
    def activity_factory(self):
        return ActivityFactory(self.config)

    @property
    @persisted('_browser', cache_global=True)
    def browser(self):
        "The ``RoboBrowser`` instance."
        import requests
        start = requests.session()
        start.headers = {'origin': 'https://sso.garmin.com'}
        return RoboBrowser(
            history=True, parser='lxml', user_agent=self.web.agent, session=start)

    @property
    @persisted('_hostname_url', cache_global=True)
    def hostname_url(self):
        "The API host name."
        self.browser.open(self.web.gauth)
        return json.loads(self.browser.parsed.html.body.p.text)['host']

    # not sure why we need this (taken from Shannon's code)
    @property
    @persisted('_script_url', cache_global=True)
    def script_url(self):
        "Not used"
        self.browser.open(self.web.base_url)
        parsed = self.browser.parsed.decode()
        pattern = r"'\S+sso\.garmin\.com\S+'"
        return re.search(pattern, parsed).group()[1:-1]

    @property
    def login_request_data(self):
        """Return the data needed to log in to the garmin connect site.

        """
        wconf = self.web
        # Package the full login GET request...
        data = {'service': wconf.redirect,
                'webhost': self.hostname_url,
                'source': wconf.base_url,
                'redirectAfterAccountLoginUrl': wconf.redirect,
                'redirectAfterAccountCreationUrl': wconf.redirect,
                'gauthHost': wconf.sso,
                'locale': 'en_US',
                'id': 'gauth-widget',
                'cssUrl': wconf.css,
                'clientId': 'GarminConnect',
                'rememberMeShown': 'true',
                'rememberMeChecked': 'false',
                'createAccountShown': 'true',
                'openCreateAccount': 'false',
                'usernameShown': 'false',
                'displayNameShown': 'false',
                'consumeServiceTicket': 'false',
                'initialFocus': 'true',
                'embedWidget': 'false',
                'generateExtraServiceTicket': 'false'}
        return data

    def _get_last_login_state(self):
        """Return ``success`` if the login connection was successful, ``failed`` if
        failed or ``unknown`` if it returned a response we don't understand.

        """
        decoded = self.browser.parsed.decode()
        if decoded.find('SUCCESS') > 0:
            state = 'success'
        elif decoded.find('Invalid') > 0:
            state = 'failed'
        else:
            logger.warning(f'unknown login state: {decoded}')
            state = 'unknown'
        return state

    def _login(self):
        """Login in the garmin connect site with athlete credentials.
        """
        login = self.config.populate(section='login')
        url = self.web.login_url + up.urlencode(self.login_request_data)
        logger.info('logging in...')
        logger.debug(f'login url: {url}')
        self.browser.open(url)
        form = self.browser.get_form(self.web.login_form)
        form['username'] = login.username
        form['password'] = login.password
        logger.debug(f'submitting form: {form}')
        self.browser.submit_form(form)
        state = self._get_last_login_state()
        if state == 'failed':
            raise ValueError('login failed')
        elif state == 'unknown':
            raise ValueError('login status unknown')
        self.login_state = state

    def _assert_logged_in(self):
        """Log in if we're not and raise an error if we can't.

        """
        if self.login_state != 'success':
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
        activity_chunk_size = self.fetch_params.activity_chunk_size
        activity_num = self.fetch_params.activity_num
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
