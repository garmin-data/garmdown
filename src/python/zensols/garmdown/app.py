"""Download Garmin connect data application entry point.

"""
__author__ = '${user-name}'

from dataclasses import dataclass, field
from enum import Enum, auto
import logging
from datetime import datetime
from . import Manager, Backuper, Reporter

logger = logging.getLogger(__name__)


class ReportType(Enum):
    detail = auto()
    summary = auto()
    json = auto()


@dataclass
class InfoApplication(object):
    """Provide information about what has (not) been downloaded.

    """
    CLI_META = {'mnemonic_overrides': {'write_not_downloaded': 'notdown',
                                       'write_not_imported': 'notimport'}}

    manager: Manager = field()

    def write_not_downloaded(self):
        """Print activities not downloaded."""
        self.mng.write_not_downloaded(self.detail, self.limit)

    def write_not_imported(self):
        """Print activities not imported."""
        self.mng.write_not_imported(self.detail, self.limit)


@dataclass
class DownloadApplication(object):
    """Download Garmin connect data application.

    """
    CLI_META = {'option_excludes': set('manager backuper'.split()),
                'mnemonic_overrides':
                {'sync_activities': 'activity',
                 'sync_tcx': 'tcx',
                 'import_tcx': 'import',
                 'clean_imported': {'name': 'clean',
                                    'option_includes': set()}}}

    manager: Manager = field()
    """Manages downloading and database work."""

    backuper: Backuper = field()
    """Creates backups of the SQLite where activities are stored."""

    limit: int = field(default=10)
    """The activity limit."""

    def sync_activities(self):
        """Download outstanding activites."""
        self.mng.sync_activities(self.limit)

    def sync_tcx(self):
        """Download outstanding TCX files."""
        self.mng.sync_tcx(self.limit)

    def import_tcx(self):
        """Import TCX file."""
        self.mng.import_tcx()

    def clean_imported(self):
        """Remove all TCX files from the imported directory."""
        self.mng.clean_imported()


@dataclass
class BackupApplication(object):
    """Backup operations.

    """
    CLI_META = {'option_excludes': set('backuper'.split())}

    backuper: Backuper = field()
    """Creates backups of the SQLite where activities are stored."""

    def backup(self):
        self.backer.backup(True)


@dataclass
class ReporterApplication(object):
    """Report activities of a day.

    """
    CLI_META = {'option_excludes': set('reporter'.split())}

    reporter: Reporter = field()
    """Report activities of a day."""

    format: ReportType = field(default='summary')
    """The format to output."""

    date: str = field(default=None)
    """The date to report on, which defaults to today (%Y-%m-%d)."""

    def report(self):
        """Report activities for a day."""
        if self.date is None:
            date = datetime.now()
        else:
            date = datetime.strptime(self.date, '%Y-%m-%d')
        fmt = self.format.name
        getattr(self.reporter, f'write_{fmt}')(date)
