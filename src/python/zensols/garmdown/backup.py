import logging
from pathlib import Path
from datetime import datetime
import shutil as su
from zensols.persist import persisted
from zensols.garmdown import (
    Backup,
    Persister,
)

logger = logging.getLogger(__name__)


class Backuper(object):
    """Backup the SQLite database on a periodic basis.

    """
    def __init__(self, config):
        """Initialize.

        :param config: the application configuration
        """
        self.config = config
        self.backup_params = self.config.populate(section='backup')

    @property
    @persisted('_persister')
    def persister(self):
        return Persister(self.config)

    @property
    @persisted('__backup_dir', cache_global=False)
    def _backup_dir(self):
        """Return the directory to where we back up."""
        backup_dir = self.config.db_backup_dir
        if not backup_dir.exists():
            logger.info(f'creating backup directory {backup_dir}')
            backup_dir.mkdir(parents=True)
        return backup_dir

    def _execute(self):
        """Execute the backup of the SQLite database."""
        persister = self.persister
        backup_dir = self._backup_dir
        src = persister.db_file
        dst = Path(backup_dir, f'{src.name}-{Backup.timestr_from_datetime()}')
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
                            f'backup every {self.backup_params.days} days')
                do_backup = diff_days >= self.backup_params.days
        logger.debug(f'backing up: {do_backup}')
        if do_backup:
            self._execute()
