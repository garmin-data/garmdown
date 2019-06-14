from pathlib import Path
from zensols.pybuild import SetupUtil

SetupUtil(
    setup_path=Path(__file__).parent.absolute(),
    name="zensols.garmdown",
    package_names=['zensols', 'resources'],
    package_data={'': ['*.conf']},
    description='Download Garmin Connect data',
    user='plandes',
    project='garmdown',
    keywords=['garmin data'],
).setup()
