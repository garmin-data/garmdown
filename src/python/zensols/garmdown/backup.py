"""Creates backups of the SQLite where activities are stored.

"""
__author__ = 'Paul Landes'

from dataclasses import dataclass, field
import logging
from pathlib import Path
from datetime import datetime
import shutil as su
from zensols.garmdown import Backup, Persister

logger = logging.getLogger(__name__)


@dataclass
class Backuper(object):
    """Backup the SQLite database on a periodic basis.

    """
    persister: Persister = field()
    """Use to access backup tracking data."""

    db_backup_dir: Path = field()
    """The directory to make SQLite file backups of the database."""

    days: int = field()
    """Number of days between backups of the activities SQLite database."""

    def _execute(self):
        """Execute the backup of the SQLite database."""
        persister = self.persister
        self.backup_dir.mkdir(parents=True, exists_ok=True)
        src = persister.db_file
        dst = self.backup_dir / f'{src.name}-{Backup.timestr_from_datetime()}'
        backup = Backup(dst)
        logger.info(f'backing up database {src} -> {dst}')
        su.copy(src, dst)
        persister.insert_backup(backup)

    def backup(self, force=False):
        """Backup the SQLite if the last backup time is older than what's specified in
        the configuration.

        :param force: if True, execute the backup regardless

        """
        backup = self.persister.get_last_backup()
        if force:
            do_backup = True
        else:
            if backup is None:
                logger.info('no recorded backup')
                do_backup = True
            else:
                logger.debug(f'last backup: {backup}')
                diff = datetime.now() - backup.time
                diff_days = diff.days
                logger.info(f'days since last backup: {diff_days} and we ' +
                            f'backup every {self.days} days')
                do_backup = diff_days >= self.days
        logger.debug(f'backing up: {do_backup}')
        if do_backup:
            self._execute()
