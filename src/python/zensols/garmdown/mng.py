from dataclasses import dataclass, field
import logging
import sys
from io import TextIOBase
from pathlib import Path
import shutil
from zensols.garmdown import Activity, Backuper, Persister, Fetcher

logger = logging.getLogger(__name__)


@dataclass
class Manager(object):
    """Manages downloading and database work.  This includes downloading data from
    the Garmin connect website and persisting status data in an SQLite
    database.

    """
    fetcher: Fetcher = field()
    """Fetches activities and downloads TCX files from Garmin."""

    persister: Persister = field()
    """Use to access backup tracking data."""

    backuper: Backuper = field()
    """Creates backups of the SQLite where activities are stored."""

    activities_dir: Path = field()
    """Location of activities (TCX) files"""

    import_dir: Path = field()
    """Where to copy to-be-imported files."""

    def sync_activities(self, limit: int = None, start_index: int = 0):
        """Download and add activities to the SQLite database.  Note that this does not
        download the TCX files.

        :param limit: the number of activities to download

        :param start_index: the 0 based activity index (not contiguous page
                            based)

        """
        # acts will be an iterable
        acts = self.fetcher.get_activities(limit, start_index)
        self.persister.insert_activities(acts)

    @staticmethod
    def _tcx_filename(activity):
        """Format a (non-directory) file name for ``activity``."""
        return f'{activity.start_date_str}_{activity.id}.tcx'

    def sync_tcx(self, limit: int = None):
        """Download TCX files and record each succesful download as such in the
        database.

        :param limit: the maximum number of TCX files to download, which
                      defaults to all

        """
        dl_dir = self.config.activities_dir
        persister = self.persister
        if not dl_dir.exists():
            logger.info(f'creating download directory {dl_dir}')
            dl_dir.mkdir(parents=True)
        acts = persister.get_missing_downloaded(limit)
        logger.info(f'downloading {len(acts)} tcx files')
        for act in acts:
            dl_path = Path(dl_dir, self._tcx_filename(act))
            if dl_path.exists():
                logger.warning(f'activity {act.id} is downloaded ' +
                               'but not marked--marking now')
            else:
                logger.debug(f'downloading {dl_path}')
                with open(dl_path, 'wb') as f:
                    self.fetcher.download_tcx(act, f)
                sr = dl_path.stat()
                logger.debug(f'{dl_path} has size {sr.st_size}')
                if sr.st_size < self.download.min_size:
                    m = f'downloaded file {dl_path} has size ' + \
                        f'{sr.st_size} < {self.download.min_size}'
                    raise ValueError(m)
            persister.mark_downloaded(act)

    def import_tcx(self, limit: int = None):
        """Download TCX files and record each succesful download as such in the
        database.

        :param limit: the maximum number of TCX files to download, which
            defaults to all

        """
        persister = self.persister
        dl_dir = self.config.activities_dir
        import_dir = self.config.import_dir
        if not import_dir.exists():
            logger.info(f'creating imported directory {import_dir}')
            import_dir.mkdir(parents=True)
        acts = persister.get_missing_imported(limit)
        logger.info(f'importing {len(acts)} activities')
        for act in acts:
            fname = self._tcx_filename(act)
            dl_path = Path(dl_dir, fname)
            import_path = Path(import_dir, fname)
            if import_path.exists():
                logger.warning(f'activity {act.id} is imported ' +
                               'but not marked--marking now')
            else:
                logger.info(f'copying {dl_path} -> {import_path}')
                shutil.copy(dl_path, import_path)
            persister.mark_imported(act)

    def sync(self, limit=None):
        """Sync activitives and TCX files.

        :param limit: the number of activities to download and import, which
            defaults to the configuration values

        """
        self.sync_activities(limit)
        self.sync_tcx(limit)
        self.import_tcx()

    def clean_imported(self, limit=None):
        """Delete all TCX files from the import directory.  This is useful so that
        programs like GoldenCheetah that imports them don't have to re-import
        them each time.

        """
        import_dir = self.config.import_dir
        logger.info(f'removing import files from {import_dir}')
        if import_dir.exists():
            for path in import_dir.iterdir():
                logger.info(f'removing {path}')
                path.unlink()

    def write_not_downloaded(self, detail: bool = False, limit: int = None,
                             writer: TextIOBase = sys.stdout):
        """Write human readable formatted data of all activities not yet downloaded.

        :param detail: whether or to give full information about the activity

        :param limit: the number of activities to report on

        :param writer: the stream to output, which defaults to stdout

        """
        act: Activity
        for act in self.persister.get_missing_downloaded(limit):
            act.write(writer, detail=detail)

    def write_not_imported(self, detail=False, limit=None, writer=sys.stdout):
        """Write human readable formatted data of all activities not yet imported.

        :param detail: whether or to give full information about the activity
        :param limit: the number of activities to report on
        :param writer: the stream to output, which defaults to stdout

        """
        act: Activity
        for act in self.persister.get_missing_imported(limit):
            act.write(writer, detail=detail)
