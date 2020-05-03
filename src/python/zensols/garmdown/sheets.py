import logging
from pathlib import Path
from datetime import datetime
import itertools as it
import httplib2 as hl
from oauth2client import file, client, tools
import googleapiclient.discovery as gd
from zensols.persist import persisted
from zensols.garmdown import Persister

logger = logging.getLogger(__name__)


class CompletedEntry(object):
    """Represents a row of training data (bike/swim/run) in the Google training
    spreadsheet.

    """
    def __init__(self, idx, row_offset, datestr,
                 swim=None, bike=None, run=None, strength=None):
        """Initialize.

        :param idx: the 0-based index of the entry
        :param row_offset: the number of rows where the first data entry starts
            not including any header(s)
        :param datestr: the date string in ``mm/dd/yyyy`` format
        """
        self.idx = idx
        self.row_offset = row_offset
        self.date = datetime.strptime(datestr, '%m/%d/%Y')
        self.exists = not (swim is None and bike is None and run is None)
        self.swim = 0 if (swim is None or len(swim) == 0) else float(swim)
        self.bike = 0 if (bike is None or len(bike) == 0) else float(bike)
        self.run = 0 if (run is None or len(run) == 0) else float(run)
        self.strength = 0 if (strength is None or len(strength) == 0) else float(strength)

    @property
    def rowidx(self):
        return self.idx + self.row_offset

    @property
    @persisted('_row')
    def row(self):
        row = (self.swim, self.bike, self.run, self.strength)
        row = tuple(map(lambda x: None if x == 0 else x, row))
        return row

    def update(self, activities, act_char_to_col_type):
        by_sport = {}
        for act in activities:
            key = act_char_to_col_type[act.type_short]
            logger.debug(f'act short: {act.type_short} => {key} for {act}')
            if key != '<skip>':
                if key not in by_sport:
                    by_sport[key] = []
                by_sport[key].append(act)
        for k, v in by_sport.items():
            act_secs = sum(map(lambda x: x.move_time_seconds, v))
            act_min = act_secs / 60
            logger.debug(f'setting {k} => {act_min}')
            setattr(self, k, act_min)

    def __str__(self):
        return (f'{self.rowidx}: date={self.date}: exist={self.exists}, ' +
                f's={self.swim},  b={self.bike}, r={self.run}, ' +
                f'w={self.strength}')

    def __repr__(self):
        return self.__str__()


class SheetUpdater(object):
    """Updates a Google Sheets spreadsheet with activity data from the activity
    database.

    """
    SECTION = 'google_sheets'

    def __init__(self, config):
        """Initialize.

        :param config: the application configuration
        """
        self.config = config
        config.populate(self, section=self.SECTION)
        self.params = config.sheet
        self.act_char_to_col_type = config.fetch_config.get_options(
            section='activity_sheet')

    @property
    def persister(self):
        "The DB DAO."
        return Persister(self.config)

    @property
    @persisted('_service', cache_global=True)
    def service(self):
        """The Google Sheets API wrapper service.

        """
        cred_path = Path(self.google_cred_file).expanduser()
        token_path = Path(self.token_file).expanduser()
        logger.info(f'getting last update with {cred_path} ' +
                    f'with file {token_path}')
        store = file.Storage(token_path)
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets(cred_path, self.params.scope)
            creds = tools.run_flow(flow, store)
        logger.info(f'logging in to Google sheets API')
        return gd.build(self.params.api, self.params.version,
                        http=creds.authorize(hl.Http()),
                        cache_discovery=False)

    @property
    def sheet(self):
        """The Google Sheets API wrapper instance.

        """
        return self.service.spreadsheets()

    def _get_completed_cell_range(self, start, end):
        "Return the completed cell range from rows ``start`` to ``end``."
        return self.completed_cell_range_format.format(start, end)

    @property
    def completed_cell_range(self):
        "The completed cell range per defaults in the settings."
        return self._get_completed_cell_range(self.row_offset, self.maxdays)

    def _get_data(self, range):
        "Get data in the spreadsheet via the Google API."
        sheet = self.sheet
        result = sheet.values().get(spreadsheetId=self.sheet_id,
                                    range=range).execute()
        return result.get('values', ())

    def _set_data(self, values, range):
        "Set data in the spreadsheet via the Google API."
        sheet = self.sheet
        body = {
            'values': values,
        }
        sheet.values().update(
            spreadsheetId=self.sheet_id,
            #valueInputOption='RAW',
            valueInputOption='USER_ENTERED',
            range=range,
            body=body).execute()

    @persisted('_completed_entries')
    def _get_completed_entries(self):
        "Return completed training entries from the spreadsheet."
        logger.info('getting existing completed workout data')
        dates = self._get_data(self.date_cell_range)
        completed = self._get_data(self.completed_cell_range)
        ldates = len(dates)
        lcompleted = len(completed)
        logger.debug(f'dates {ldates}, completed: {lcompleted}')
        if ldates > lcompleted:
            completed = it.chain(completed, ((),) * (ldates - lcompleted))
        data = enumerate(zip(dates, completed))
        return map(lambda x: CompletedEntry(
            x[0], self.row_offset, x[1][0][0], *x[1][1]), data)

    def _get_update_range_entries(self, last_idx=None, end_date=None):
        """Return an updated range.

        :param last_idx: the last completed work out entry index (0 based), or
            if ``None``, calculated from spreadsheet data

        :param end_date: the last date to constraint entry range
        :type end_date: datetime.datetime

        """
        entries = tuple(self._get_completed_entries())
        if last_idx is None:
            last_idx = -1
            for last in filter(lambda x: x.exists, entries):
                last_idx = last.idx
        logger.debug(f'last existing completed row: {last_idx}')
        if end_date is None:
            end_date = datetime.now()
        return filter(lambda x: x.idx > last_idx and x.date < end_date,
                      entries)

    def _sync_entries_with_db(self, entries, clobber=False):
        """Populate database data in to ``entries``.

        :param entries: the workout entries to populate
        :type entries: CompletedEntry

        :param clobber: if ``True`` populate data even if ``entry.exists`` is
           ``False``

        """
        logger.info(f'syncing {len(entries)} with activity database')
        for entry in entries:
            if clobber or not entry.exists:
                acts = self.persister.get_activities_by_date(entry.date)
                if logger.isEnabledFor(logging.DEBUG):
                    types = ', '.join(map(lambda x: x.type, acts))
                    logger.debug(f'found {types} activities for {entry}')
                entry.update(acts, self.act_char_to_col_type)
            logger.debug(f'updated: {entry}')

    def _upload_row_data(self, entries):
        """Upload workout data to Google.

        :param entries: the workout data to upload
        :type entries: iterable of of CompletedEntry

        """
        rows = tuple(map(lambda x: x.row, entries))
        range = self._get_completed_cell_range(
            entries[0].rowidx, entries[-1].rowidx)
        logger.info(f'updating {len(rows)} rows with range {range}')
        self._set_data(rows, range)

    def sync(self):
        entries = tuple(self._get_update_range_entries())
        if len(entries) > 0:
            self._sync_entries_with_db(entries)
            self._upload_row_data(entries)
