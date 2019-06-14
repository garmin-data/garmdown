import logging
import importlib
from pathlib import Path
from zensols.garmdown import AppConfig

logger = logging.getLogger('zensols.garmdown.proto')


def create_config():
    #return AppConfig('test-resources/garmdown.conf')
    return AppConfig(Path('~/opt/etc/garmdown.conf').expanduser())


def fetch():
    import zensols.garmdown.fetcher
    importlib.reload(zensols.garmdown.fetcher)
    #logging.getLogger('zensols.actioncli').setLevel(logging.INFO)
    logging.getLogger('zensols.garmdown.fetcher').setLevel(logging.DEBUG)
    app = zensols.garmdown.fetcher.Fetcher(create_config())
    app.tmp()


def db():
    import zensols.garmdown.db
    importlib.reload(zensols.garmdown.db)
    logging.getLogger('zensols.garmdown.fetcher').setLevel(logging.INFO)
    logging.getLogger('zensols.garmdown.persist').setLevel(logging.INFO)
    app = zensols.garmdown.db.Persister(create_config())
    app.tmp()


def mng():
    import zensols.garmdown.mng
    importlib.reload(zensols.garmdown.mng)
    logging.getLogger('zensols.garmdown.fetcher').setLevel(logging.INFO)
    logging.getLogger('zensols.garmdown.persist').setLevel(logging.INFO)
    logging.getLogger('zensols.garmdown.mng').setLevel(logging.INFO)
    app = zensols.garmdown.mng.Manager(create_config())
    app.tmp()


def sheets():
    import zensols.garmdown.sheets
    importlib.reload(zensols.garmdown.sheets)
    logging.getLogger('zensols.garmdown.sheets').setLevel(logging.DEBUG)
    app = zensols.garmdown.sheets.SheetUpdater(create_config())
    app.tmp()


def reporter():
    import zensols.garmdown.reporter
    importlib.reload(zensols.garmdown.reporter)
    logging.getLogger('zensols.garmdown.reporter').setLevel(logging.DEBUG)
    app = zensols.garmdown.reporter.Reporter(create_config())
    app.tmp()


def main():
    logging.basicConfig(level=logging.WARNING)
    #logging.getLogger('googleapicliet.discovery_cache').setLevel(logging.ERROR)
    run = 1
    {1: fetch,
     2: db,
     3: mng,
     4: sheets,
     5: reporter,
     }[run]()


main()
