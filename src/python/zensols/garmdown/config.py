import logging
from zensols.config import ExtendedInterpolationConfig

logger = logging.getLogger(__name__)


class AppConfig(ExtendedInterpolationConfig):
    """Application context simplifies some of the configuration.

    """

    @property
    def fetch_config(self):
        if not hasattr(self, '_fetch_conf'):
            path = self.resource_filename('resources/fetch.conf')
            logger.debug(f'loading web configuration from {path}')
            conf = ExtendedInterpolationConfig(path)
            self._web = conf.populate(section='web')
            self._sql = conf.populate(section='sql')
            self._db = conf.populate(section='db')
            self._download = conf.populate(section='download')
            self._sheet = conf.populate(section='sheet')
            self._fetch_conf = conf
        return self._fetch_conf

    def _assert_fetch_conf(self):
        self.fetch_config

    @property
    def db_file(self):
        """Return the SQLite DB file."""
        return self.get_option_path('db_file').expanduser()

    @property
    def activities_dir(self):
        """Return the directory where TCX files live.
        TODO: fix BAD name.  This name should be ``tcx_dir``.

        """
        return self.get_option_path('activities_dir').expanduser()

    @property
    def import_dir(self):
        """Return the directory where the imported TCX files live."""
        return self.get_option_path('import_dir').expanduser()

    @property
    def db_backup_dir(self):
        """Return the directory of the stored SQLite backup files."""
        return self.get_option_path('db_backup_dir').expanduser()

    @property
    def web(self):
        """Return the web configuration used by the robot."""
        self._assert_fetch_conf()
        return self._web

    @property
    def sql(self):
        """Return the SQL statements object."""
        self._assert_fetch_conf()
        return self._sql

    @property
    def db(self):
        """Return the database configuration parameter object."""
        self._assert_fetch_conf()
        return self._db

    @property
    def download(self):
        """Return the download configuration parameter object."""
        self._assert_fetch_conf()
        return self._download

    @property
    def sheet(self):
        """Return the Google Sheets configuration parameter object."""
        self._assert_fetch_conf()
        return self._sheet

    @property
    def fetch(self):
        """Return the fetch (download) parameter object."""
        if not hasattr(self, '_fetch'):
            self._fetch = self.populate(section='download')
        return self._fetch
