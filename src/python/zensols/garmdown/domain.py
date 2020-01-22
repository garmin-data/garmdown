import sys
import itertools as it
from datetime import datetime


class Activity(object):
    def __init__(self, raw, type_char):
        self.id = str(raw['activityId'])
        self.raw = raw
        self.type_char = type_char

    @staticmethod
    def type_from_raw(raw):
        return raw['activityType']['typeKey']

    @staticmethod
    def common_attributes():
        return """
name location start_date_str duration move_time_seconds
heart_rate_average v02max stress_score calories
""".split()

    def _attr_names(self):
        return self.common_attributes()

    @property
    def start_time(self):
        if not hasattr(self, '_datestr'):
            datestr = self.raw['startTimeLocal']
            self._date = datetime.strptime(datestr, '%Y-%m-%d %H:%M:%S')
        return self._date

    @property
    def start_date_str(self):
        return datetime.strftime(self.start_time, '%Y-%m-%d')

    @property
    def start_year_str(self):
        return datetime.strftime(self.start_time, '%Y')

    @property
    def name(self):
        return self.raw['activityName']

    @property
    def type_raw(self):
        return self.type_from_raw(self.raw)

    @property
    def type(self):
        return self.factory.char_to_type[self.type_char]

    @property
    def type_short(self):
        return self.type_char

    @property
    def type_long(self):
        return self.factory.char_to_name[self.type_char]

    @property
    def location(self):
        return self.raw['locationName']

    @property
    def duration(self):
        no_move_sports = 'indoor_cycling treadmill_running strength_training'
        no_move_sports = set(no_move_sports.split())
        key = 'duration' if self.type in no_move_sports else 'movingDuration'
        return self.raw[key]

    @property
    def move_time_seconds(self):
        if self.type_short == 's':
            dur = self.raw['duration']
        else:
            dur = self.duration#self.raw['movingDuration']
        if dur is None:
            dur = self.raw['duration']
        if dur is None:
            raise ValueError(f'no such duration: {self}')
        return dur

    @property
    def heart_rate_average(self):
        return self.raw['averageHR']

    @property
    def v02max(self):
        return self.raw['vO2MaxValue']

    @property
    def stress_score(self):
        return self.raw['trainingStressScore']

    @property
    def calories(self):
        return self.raw['calories']

    def write_raw(self, writer=sys.stdout):
        from pprint import pprint
        pprint(self.raw, stream=writer)

    def write(self, writer=sys.stdout, detail=True):
        if detail:
            writer.write(f'{self.start_date_str}: {self.name}\n')
            writer.write(f'type: {self.type}\n')
            for attr in self._attr_names():
                name = attr.replace('_', ' ')
                aval = getattr(self, attr)
                writer.write(f'  {name}: {aval}\n')
        else:
            writer.write(
                f'{self.id}: start: {self.start_time}, type: {self.type}\n')

    def __str__(self):
        return f'{self.id}: date={self.start_date_str}, sport={self.type_long}'

    def __repr__(self):
        return self.__str__()


class CyclingActivity(Activity):
    @staticmethod
    def cycling_attributes():
        return """
cadence power_average power_norm power_max strokes
intensity
""".split()

    def _attr_names(self):
        pattrs = super(CyclingActivity, self)._attr_names()
        return it.chain(pattrs, self.cycling_attributes())

    @property
    def intensity(self):
        return self.raw['intensityFactor']

    @property
    def cadence(self):
        return self.raw['averageBikingCadenceInRevPerMinute']

    @property
    def power_average(self):
        return self.raw['avgPower']

    @property
    def power_norm(self):
        return self.raw['normPower']

    @property
    def power_max(self):
        return self.raw['maxPower']

    @property
    def strokes(self):
        return self.raw['strokes']


class RunningActivity(Activity):
    @staticmethod
    def running_attributes():
        return """
cadence_step_per_minute ground_contact_balance_average
ground_contact_time_average steps
""".split()

    def _attr_names(self):
        pattrs = super(RunningActivity, self)._attr_names()
        return it.chain(pattrs, self.running_attributes())

    @property
    def cadence_step_per_minute(self):
        return self.raw['averageRunningCadenceInStepsPerMinute']

    @property
    def stride_average(self):
        return self.raw['avgStrideLength']

    @property
    def ground_contact_balance_average(self):
        return self.raw['avgGroundContactBalance']

    @property
    def ground_contact_time_average(self):
        return self.raw['avgGroundContactTime']

    @property
    def steps(self):
        return self.raw['steps']


class ActivityFactory(object):
    def __init__(self, config):
        self.type_to_char = config.fetch_config.get_options(
            section='activity_type')
        self.char_to_name = config.fetch_config.get_options(
            section='activity_name')
        self.char_to_type = {v: k for k, v in self.type_to_char.items()}

    def create(self, raw):
        atype = Activity.type_from_raw(raw)
        type_char = self.type_to_char[atype]
        clsname = atype.capitalize() + 'Activity'
        if clsname not in globals():
            act = Activity(raw, type_char)
        else:
            act = globals()[clsname](raw, type_char)
        act.factory = self
        return act


class Backup(object):
    def __init__(self, path, time=None):
        self.path = path
        if time is None:
            self.time = datetime.now()
        else:
            self.time = time

    @property
    def datestr(self):
        return datetime.strftime(self.time, '%Y-%m-%d')

    @staticmethod
    def timestr_from_datetime(time=None):
        if time is None:
            time = datetime.now()
        return datetime.strftime(time, '%Y-%m-%d_%H-%M')

    @property
    def timestr(self):
        return self.timestr_from_datetime(self.time)

    def __str__(self):
        return f'{self.timestr}: {self.path}'
