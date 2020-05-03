import logging
from datetime import datetime
from zensols.cli import OneConfPerActionOptionsCliEnv
from zensols.garmdown import (
    Manager,
    Backuper,
    SheetUpdater,
    Reporter,
    AppConfig,
)


class InfoCli(object):
    def __init__(self, config, detail=False, limit=None):
        self.mng = Manager(config)
        self.detail = detail
        self.limit = limit

    def environment(self):
        self.mng.environment()

    def write_not_downloaded(self):
        self.mng.write_not_downloaded(self.detail, self.limit)

    def write_not_imported(self):
        self.mng.write_not_imported(self.detail, self.limit)


class DownloadCli(object):
    def __init__(self, config, limit=None):
        self.mng = Manager(config)
        self.config = config
        self.limit = limit

    def sync_activities(self):
        self.mng.sync_activities(self.limit)

    def sync_tcx(self):
        self.mng.sync_tcx(self.limit)

    def import_tcx(self):
        self.mng.import_tcx()

    def sync(self):
        self.mng.sync(self.limit)
        backuper = Backuper(self.config)
        backuper.backup()


class SheetCli(object):
    def __init__(self, config):
        self.config = config

    def sync(self):
        su = SheetUpdater(self.config)
        su.sync()


class BackupCli(object):
    def __init__(self, config):
        self.backer = Backuper(config)

    def backup(self):
        self.backer.backup(True)


class ReporterCli(object):
    FORMAT_TYPES = set('detail summary json'.split())

    def __init__(self, config, format, datestr=None):
        self.config = config
        self.format = format
        self.datestr = datestr
        if format not in self.FORMAT_TYPES:
            fopts = self.format_type_string()
            raise ValueError(
                f"unknown format type '{format}' not one of {fopts}")

    @classmethod
    def format_type_string(cls):
        return '|'.join(cls.FORMAT_TYPES)

    @property
    def date(self):
        if self.datestr is None:
            date = datetime.now()
        else:
            date = datetime.strptime(self.datestr, '%Y-%m-%d')
        return date

    def report(self):
        reporter = Reporter(self.config)
        getattr(reporter, f'write_{self.format}')(self.date)


class SyncCli(object):
    def __init__(self, config):
        self.config = config

    def sync(self):
        DownloadCli(self.config).sync()
        SheetCli(self.config).sync()


class ConfAppCommandLine(OneConfPerActionOptionsCliEnv):
    def __init__(self):
        detail_op = ['-d', '--detail', False,
                     {'dest': 'detail',
                      'action': 'store_true', 'default': False,
                      'help': 'report details of missing data'}]
        limit_op = ['-l', '--limit', False,
                    {'dest': 'limit', 'metavar': 'INTEGER',
                     'type': 'int',
                     'help': 'the limit'}]
        date_op = ['-a', '--date', False,
                   {'dest': 'datestr', 'metavar': 'mm/dd/yyyy',
                    'help': 'the date to report, which defaults to today'}]
        format_op = ['-f', '--format', False,
                     {'dest': 'format',
                      'default': 'detail',
                      'metavar': ReporterCli.format_type_string(),
                      'help': 'the format'}]
        cnf = {'executors':
               [{'name': 'info',
                 'executor': lambda params: InfoCli(**params),
                 'actions': [{'name': 'env',
                              'meth': 'environment',
                              'doc': 'print environment',
                              'opts': [detail_op]},
                             {'name': 'notdown',
                              'meth': 'write_not_downloaded',
                              'doc': 'print activities not downloaded',
                              'opts': [detail_op]},
                             {'name': 'notimport',
                              'meth': 'write_not_imported',
                              'doc': 'print activities not imported',
                              'opts': [detail_op]}]},
                {'name': 'down',
                 'executor': lambda params: DownloadCli(**params),
                 'actions': [{'name': 'activity',
                              'meth': 'sync_activities',
                              'doc': 'download outstanding activites',
                              'opts': [limit_op]},
                             {'name': 'tcx',
                              'meth': 'sync_tcx',
                              'doc': 'download outstanding TCX files',
                              'opts': [limit_op]},
                             {'name': 'import',
                              'meth': 'import_tcx',
                              'doc': 'import TCX file',
                              'opts': [limit_op]},
                             {'name': 'download',
                              'doc': 'download all outstanding data',
                              'opts': [limit_op]}]},
                {'name': 'backup',
                 'executor': lambda params: BackupCli(**params),
                 'actions': [{'name': 'backup',
                              'doc': 'backup (force) the activites database',
                              'opts': []}]},
                {'name': 'report',
                 'executor': lambda params: ReporterCli(**params),
                 'actions': [{'name': 'report',
                              'doc': 'report activities for a day',
                              'opts': [date_op, format_op]}]},
                {'name': 'sheet',
                 'executor': lambda params: SheetCli(**params),
                 'actions': [{'name': 'sheet',
                              'meth': 'sync',
                              'doc': 'update Google Docs training spreadsheet',
                              'opts': []}]},
                {'name': 'sync',
                 'executor': lambda params: SyncCli(**params),
                 'actions': [{'name': 'sync',
                              'doc': 'equivalent to actions download and sheet',
                              'opts': []}]}],
               'config_option': {'name': 'config',
                                 'expect': True,
                                 'opt': ['-c', '--config', False,
                                         {'dest': 'config',
                                          'metavar': 'FILE',
                                          'help': 'configuration file'}]},
               'whine': 0}
        super(ConfAppCommandLine, self).__init__(
            cnf, config_env_name='garmdownrc', pkg_dist='zensols.garmdown',
            config_type=AppConfig, default_action='sync')


def main():
    logging.basicConfig(format='%(module)s: %(message)s', level=logging.INFO)
    logging.getLogger('zensols.actioncli').setLevel(logging.WARNING)
    cl = ConfAppCommandLine()
    cl.invoke()
