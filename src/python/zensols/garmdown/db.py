import logging
import sys
from pathlib import Path
from datetime import datetime
import json
import sqlite3
from zensols.persist import (
    persisted,
    resource
)
from zensols.garmdown import (
    ActivityFactory,
    Backup,
)

logger = logging.getLogger(__name__)


class connection(resource):
    def __init__(self):
        super(connection, self).__init__(
            '_create_connection', '_dispose_connection')


class Persister(object):
    """CRUDs activities in the SQLite database.

    """
    def __init__(self, config):
        """Initialize

        :param config: the application configuration
        """
        self.config = config
        self.sql = config.sql

    @property
    @persisted('_activity_factory')
    def activity_factory(self):
        return ActivityFactory(self.config)

    @property
    def db_file(self):
        return self.config.db_file

    def _create_connection(self):
        """Create a connection to the SQLite database (file).

        """
        logger.debug('creating connection')
        db_file = self.db_file
        created = False
        if not db_file.exists():
            if not db_file.parent.exists():
                logger.info(f'creating sql db directory {db_file.parent}')
                db_file.parent.mkdir(parents=True)
            logger.info(f'creating sqlite db file: {db_file}')
            created = True
        types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        conn = sqlite3.connect(str(db_file.absolute()), detect_types=types)
        if created:
            logger.info(f'initializing database...')
            for sql_key in self.config.db.init_sql:
                sql = getattr(self.sql, sql_key)
                logger.debug(f'invoking sql: {sql}')
                conn.execute(sql)
                conn.commit()
        return conn

    def _dispose_connection(self, conn):
        """Close the connection to the database."""
        logger.debug(f'closing connection {conn}')
        conn.close()

    def _activity_exists(self, conn, act):
        """"Return whether or not an activity already lives in the database."""
        cur = conn.cursor()
        exists = None
        try:
            cur.execute(self.sql.exists_act, (act.id,))
            exists = cur.fetchone() is not None
        finally:
            cur.close()
        return exists

    @connection()
    def insert_activities(self, conn, activities):
        """Insert an activity in the database.

        :param conn: the database connection (not provided on by the client of
            this class)

        :param activities the activities to add to the database

        """
        logger.info(f'persisting activities')
        logger.debug(f'connection: {conn}')
        for act in activities:
            if self._activity_exists(conn, act):
                logger.debug(f'already found in database: {act}--skipping')
            else:
                raw = json.dumps(act.raw)
                row = (act.id, act.start_time, act.type_short, raw,)
                logger.info(f'adding activity to db {act}')
                conn.execute(self.sql.insert_act, row)
        conn.commit()

    def _thaw_activity(self, conn, sql, *params):
        """Unpersist activities from the database.

        :param conn: the database connection
        :param sql: the string SQL used to query
        :param params: the parameters used in the SQL call

        """
        afactory = self.activity_factory
        for raw in map(lambda x: x[0], conn.execute(sql, params)):
            jobj = json.loads(raw)
            yield afactory.create(jobj)

    def _mark_state(self, conn, sql, action, act):
        """Mark something as downloaded or imported.

        :param conn: the database connection
        :param sql: the string SQL used to update
        :param action: what we're marking--only used for logging
        :param act: the activity to mark as updated for 'action' reason

        """
        now = datetime.now()
        logger.info(f'mark activity {act.id} to {action} {now}')
        logger.debug(f'update sql: {sql}')
        rc = conn.execute(sql, (now, act.id,)).rowcount
        logger.debug(f'updated {rc} row(s)')
        conn.commit()
        return rc

    @connection()
    def get_missing_downloaded(self, conn, limit=None):
        """Return activities that have not yet been downloaded.

        :param conn: the database connection (not provided on by the client of
            this class)

        :param limit: the number of actions to return that haven't been
            downloaded

        """
        if limit is None:
            limit = self.config.fetch.tcx_chunk_size
        return tuple(self._thaw_activity(
            conn, self.sql.missing_downloads, limit))

    @connection()
    def mark_downloaded(self, conn, activity):
        """Mark ``activity`` as having been downloaded

        :param conn: the database connection (not provided on by the client of
            this class)

        :param activity: the activity to mark as downloaded

        """
        update_sql = self.sql.update_downloaded
        self._mark_state(conn, update_sql, 'downloaded', activity)

    @connection()
    def get_missing_imported(self, conn, limit=None):
        """Return activities that have not yet been imported.

        :param conn: the database connection (not provided on by the client of
            this class)

        :param limit: the number of actions to return that haven't been
            imported

        """
        if limit is None:
            limit = sys.maxsize
        return tuple(self._thaw_activity(
            conn, self.sql.missing_imported, limit))

    @connection()
    def mark_imported(self, conn, activity):
        """Mark ``activity`` as having been imported

        :param conn: the database connection (not provided on by the client of
            this class)

        :param activity: the activity to mark as imported

        """
        update_sql = self.sql.update_imported
        self._mark_state(conn, update_sql, 'imported', activity)

    @connection()
    def insert_backup(self, conn, backup):
        row = (backup.time, str(backup.path.absolute()))
        logger.info(f'inserting backup {backup} to db')
        conn.execute(self.sql.insert_back, row)
        conn.commit()

    def _thaw_backup(self, conn, sql):
        for row in conn.execute(sql):
            time, filename = row
            yield Backup(Path(filename), time)

    @connection()
    def get_last_backup(self, conn):
        backups = tuple(self._thaw_backup(conn, self.sql.last_back))
        if len(backups) > 0:
            return backups[0]

    @connection()
    def get_activities_by_date(self, conn, datetime):
        datestr = datetime.strftime('%Y-%m-%d')
        return tuple(self._thaw_activity(
            conn, self.sql.activity_by_date, datestr))
