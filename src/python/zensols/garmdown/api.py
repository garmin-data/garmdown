"""Taken from `garminexport <https://github.com/petergardfjall/garminexport>_`.
"""
__author__ = 'Peter Gardfjall'

import requests

import re
#from garmin_uploader import logger
import logging

logger = logging.getLogger(__name__)

URL_HOSTNAME = 'https://connect.garmin.com/modern/auth/hostname'
URL_LOGIN = 'https://sso.garmin.com/sso/login'
URL_POST_LOGIN = 'https://connect.garmin.com/modern/'
URL_PROFILE = 'https://connect.garmin.com/modern/currentuser-service/user/info'  # noqa
URL_HOST_SSO = 'sso.garmin.com'
URL_HOST_CONNECT = 'connect.garmin.com'
URL_SSO_SIGNIN = 'https://sso.garmin.com/sso/signin'
URL_UPLOAD = 'https://connect.garmin.com/modern/proxy/upload-service/upload'
URL_ACTIVITY_BASE = 'https://connect.garmin.com/modern/proxy/activity-service/activity'  # noqa
URL_ACTIVITY_TYPES = 'https://connect.garmin.com/modern/proxy/activity-service/activity/activityTypes' # noqa


class GarminAPIException(Exception):
    """
    An Exception occured in Garmin API
    """


class GarminAPI:
    """
    Low level Garmin Connect api connector
    """
    activity_types = None

    # This strange header is needed to get auth working
    common_headers = {
        'NK': 'NT',
    }

    def authenticate(self, username, password):
        """
        That's where the magic happens !
        Try to mimick a browser behavior trying to login
        on Garmin Connect as closely as possible
        Outputs a Requests session, loaded with precious cookies
        """
        # Use a valid Browser user agent
        # TODO: use several UA picked randomly
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:48.0) Gecko/20100101 Firefox/50.0',  # noqa
        })

        # Request sso hostname
        sso_hostname = None
        resp = session.get(URL_HOSTNAME)
        if not resp.ok:
            raise Exception('Invalid SSO first request status code {}'.format(resp.status_code))  # noqa
        sso_hostname = resp.json().get('host')

        # Load login page to get login ticket
        # Full parameters from Firebug, we have to maintain
        # Fuck this shit.
        # Who needs mandatory urls in a request parameters !
        params = [
            ('service', 'https://connect.garmin.com/modern/'),
            ('webhost', 'https://connect.garmin.com/modern/'),
            ('source', 'https://connect.garmin.com/signin/'),
            ('redirectAfterAccountLoginUrl', 'https://connect.garmin.com/modern/'),  # noqa
            ('redirectAfterAccountCreationUrl', 'https://connect.garmin.com/modern/'),  # noqa
            ('gauthHost', sso_hostname),
            ('locale', 'fr_FR'),
            ('id', 'gauth-widget'),
            ('cssUrl', 'https://connect.garmin.com/gauth-custom-v3.2-min.css'),
            ('privacyStatementUrl', 'https://www.garmin.com/fr-FR/privacy/connect/'),  # noqa
            ('clientId', 'GarminConnect'),
            ('rememberMeShown', 'true'),
            ('rememberMeChecked', 'false'),
            ('createAccountShown', 'true'),
            ('openCreateAccount', 'false'),
            ('displayNameShown', 'false'),
            ('consumeServiceTicket', 'false'),
            ('initialFocus', 'true'),
            ('embedWidget', 'false'),
            ('generateExtraServiceTicket', 'true'),
            ('generateTwoExtraServiceTickets', 'true'),
            ('generateNoServiceTicket', 'false'),
            ('globalOptInShown', 'true'),
            ('globalOptInChecked', 'false'),
            ('mobile', 'false'),
            ('connectLegalTerms', 'true'),
            ('showTermsOfUse', 'false'),
            ('showPrivacyPolicy', 'false'),
            ('showConnectLegalAge', 'false'),
            ('locationPromptShown', 'true'),
            ('showPassword', 'true'),
            ('useCustomHeader', 'false'),
            ('mfaRequired', 'false'),
            ('performMFACheck', 'false'),
            ('rememberMyBrowserShown', 'false'),
            ('rememberMyBrowserChecked', 'false'),
        ]
        res = session.get(URL_LOGIN, params=params)
        if res.status_code != 200:
            raise Exception('No login form')

        # Lookup for CSRF token
        csrf = re.search(r'<input type="hidden" name="_csrf" value="(\w+)" />', res.content.decode('utf-8'))  # noqa
        if csrf is None:
            raise Exception('No CSRF token')
        csrf_token = csrf.group(1)
        logger.debug('Found CSRF token {}'.format(csrf_token))

        # Login/Password with login ticket
        data = {
          'embed': 'false',
          'username': username,
          'password': password,
          '_csrf': csrf_token,
        }
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',  # noqa
            'Accept-Language': 'fr,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://sso.garmin.com',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': res.url,
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'iframe',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'TE': 'Trailers',
        }
        res = session.post(URL_LOGIN, params=params, data=data,
                           headers=headers)

        if not res.ok:
            if res.status_code == 429:
                raise Exception('Authentication failed due to too many requests (429). Retry later...')  # noqa
            raise Exception('Authentification failed.')

        # Check we have sso guid in cookies
        if 'GARMIN-SSO-GUID' not in session.cookies:
            raise Exception('Missing Garmin auth cookie')

        # Second auth step
        # Needs a service ticket from previous response
        headers = {
            'Host': URL_HOST_CONNECT,
        }
        res = session.get(URL_POST_LOGIN, params=params, headers=headers)
        if res.status_code != 200 and not res.history:
            raise Exception('Second auth step failed.')

        # Check login
        res = session.get(URL_PROFILE)
        if not res.ok:
            raise Exception("Login check failed.")
        garmin_user = res.json()
        logger.info('Logged in as {}'.format(garmin_user['username']))

        return session

    def upload_activity(self, session, activity):
        """
        Upload an activity on Garmin
        Support multiple formats
        """
        assert activity.id is None

        # Upload file as multipart form
        files = {
            "file": (activity.filename, activity.open()),
        }
        url = '{}/{}'.format(URL_UPLOAD, activity.extension)
        res = session.post(url, files=files, headers=self.common_headers)

        # HTTP Status can either be OK or Conflict
        if res.status_code not in (200, 201, 409):
            if res.status_code == 412:
                logger.error('You may have to give explicit consent for uploading files to Garmin')  # noqa
            raise GarminAPIException('Failed to upload {}'.format(activity))

        response = res.json()['detailedImportResult']
        if len(response["successes"]) == 0:
            if len(response["failures"]) > 0:
                if response["failures"][0]["messages"][0]['code'] == 202:
                    # Activity already exists
                    return response["failures"][0]["internalId"], False
                else:
                    raise GarminAPIException(response["failures"][0]["messages"])  # noqa
            else:
                raise GarminAPIException('Unknown error: {}'.format(response))
        else:
            # Upload was successsful
            return response["successes"][0]["internalId"], True

    def set_activity_name(self, session, activity):
        """
        Update the activity name
        """
        assert activity.id is not None
        assert activity.name is not None

        url = '{}/{}'.format(URL_ACTIVITY_BASE, activity.id)
        data = {
            'activityId': activity.id,
            'activityName': activity.name,
        }
        headers = dict(self.common_headers)  # clone
        headers['X-HTTP-Method-Override'] = 'PUT'  # weird. again.
        res = session.post(url, json=data, headers=headers)
        if not res.ok:
            raise GarminAPIException('Activity name not set: {}'.format(res.content))  # noqa

    def load_activity_types(self):
        """
        Fetch valid activity types from Garmin Connect
        """
        # Only fetch once
        if self.activity_types:
            return self.activity_types

        logger.debug('Fetching activity types')
        resp = requests.get(URL_ACTIVITY_TYPES, headers=self.common_headers)
        if not resp.ok:
            raise GarminAPIException('Failed to retrieve activity types')

        # Store as a clean dict, mapping keys and lower case common name
        types = resp.json()
        self.activity_types = {t['typeKey']: t for t in types}

        logger.debug('Fetched {} activity types'.format(len(self.activity_types)))  # noqa
        return self.activity_types

    def set_activity_type(self, session, activity):
        """
        Update the activity type
        """
        assert activity.id is not None
        assert activity.type is not None

        # Load the corresponding type key on Garmin Connect
        types = self.load_activity_types()
        type_key = types.get(activity.type)
        if type_key is None:
            logger.error("Activity type '{}' not valid".format(activity.type))
            return False

        url = '{}/{}'.format(URL_ACTIVITY_BASE, activity.id)
        data = {
            'activityId': activity.id,
            'activityTypeDTO': type_key
        }
        headers = dict(self.common_headers)  # clone
        headers['X-HTTP-Method-Override'] = 'PUT'  # weird. again.
        res = session.post(url, json=data, headers=headers)
        if not res.ok:
            raise GarminAPIException('Activity type not set: {}'.format(res.content))  # noqa
