"""Download Garmin connect data application entry point.

"""
__author__ = '${user-name}'

from dataclasses import dataclass, field
from enum import Enum, auto
import logging
from datetime import datetime
from . import Manager, Backuper, Reporter, SheetUpdater

logger = logging.getLogger(__name__)


class ReportType(Enum):
    detail = auto()
    summary = auto()
    json = auto()


@dataclass
class InfoApplication(object):
    """Provide information about what has (not) been downloaded.

    """
    CLI_META = {'option_excludes': {'manager'},
                'mnemonic_overrides': {'write_not_downloaded': 'notdown',
                                       'write_not_imported': 'notimport'}}

    manager: Manager = field()
    """Manages downloading and database work."""

    detail: bool = field(default=False)
    """Whether or not to include detail."""

    limit: int = field(default=None)
    """The activity limit, which defaults config.

    """
    def write_not_downloaded(self):
        """Print activities not downloaded."""
        self.manager.write_not_downloaded(self.detail, self.limit)

    def write_not_imported(self):
        """Print activities not imported."""
        self.manager.write_not_imported(self.detail, self.limit)


@dataclass
class DateBasedApplication(object):
    def _get_date(self) -> datetime:
        if self.date is None:
            date = datetime.now()
        else:
            date = datetime.strptime(self.date, '%Y-%m-%d')
        return date


@dataclass
class ReporterApplication(DateBasedApplication):
    """Report activities of a day.

    """
    CLI_META = {'option_excludes': set('reporter'.split())}

    reporter: Reporter = field()
    """Report activities of a day."""

    format: ReportType = field(default='summary')
    """The format to output."""

    date: str = field(default=None)
    """The date to report on, which defaults to today (yyyy-mm-dd)."""

    def report(self):
        """Report activities for a day."""
        date = self._get_date()
        fmt = self.format.name
        getattr(self.reporter, f'write_{fmt}')(date)


@dataclass
class DownloadApplication(DateBasedApplication):
    """Download Garmin connect data application.

    """
    CLI_META = {'option_excludes': set('manager backuper'.split()),
                'mnemonic_overrides':
                {'sync_activities': 'activity',
                 'sync_tcx': 'tcx',
                 'import_tcx': 'import',
                 'import_tcx_from_date': 'importafter',
                 'clean_imported': {'name': 'clean',
                                    'option_includes': set()}}}

    manager: Manager = field()
    """Manages downloading and database work."""

    backuper: Backuper = field()
    """Creates backups of the SQLite where activities are stored."""

    limit: int = field(default=None)
    """The activity limit, which defaults config.

    """
    def sync_activities(self):
        """Download outstanding activites."""
        self.manager.sync_activities(self.limit)

    def sync_tcx(self):
        """Download outstanding TCX files."""
        self.manager.sync_tcx(self.limit)

    def import_tcx(self):
        """Import TCX file."""
        self.manager.import_tcx()

    def clean_imported(self):
        """Remove all TCX files from the imported directory."""
        self.manager.clean_imported()

    def _import_tcx_from_date(self, date: str):
        """Import TCX files from the database starting on or after a date.

        :param date: the date to report on, which defaults to today
                     (yyyy-mm-dd)

        """
        self.date = date
        date: datetime = self._get_date()
        self.manager.import_tcx_from_date(date)


@dataclass
class BackupApplication(object):
    """Backup operations.

    """
    CLI_META = {'option_excludes': set('backuper'.split())}

    backuper: Backuper = field()
    """Creates backups of the SQLite where activities are stored."""

    def backup(self):
        self.backuper.backup(True)


@dataclass
class SheetApplication(object):
    """Updates a Google Sheets activity data.

    """
    CLI_META = {'option_excludes': set('sheet_updater'.split()),
                'mnemonic_overrides': {'sync': 'sheet'}}

    sheet_updater: SheetUpdater = field()
    """Updates a Google Sheets spreadsheet with activity data from the activity
    database.

    """

    def sync(self):
        """Update Google Docs training spreadsheet."""
        self.sheet_updater.sync()


@dataclass
class SyncApplication(object):
    """Download Garmin activities and sync with Google sheets.

    """
    CLI_META = {'option_excludes': set('manager sheet_updater'.split())}

    manager: Manager = field()
    """Manages downloading and database work."""

    backuper: Backuper = field()
    """Creates backups of the SQLite where activities are stored."""

    sheet_updater: SheetUpdater = field()
    """Updates a Google Sheets spreadsheet with activity data from the activity
    database.

    """
    def sync(self):
        self.manager.sync()
        self.backuper.backup()
        self.sheet_updater.sync()
