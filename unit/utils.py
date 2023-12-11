from enum import Enum
import logging
import platform
import os
import datetime
import json
from typing import Any
from threading import Timer, Event

from json import JSONEncoder, JSONDecoder
from starlette.responses import Response
import fastapi.responses

default_log_level = logging.DEBUG
default_encoding = "utf-8"
default_port = 8000

class Equipment(Enum):
    Mount = 1,
    Camera = 2,
    Focuser = 3
    Pswitch = 4
    Test = 5
    Undefined = 6


equipment_ids = {
    "e": [1, 2],
    "w": [3, 4],
}

class ValidEquipId(int, Enum):
    one = '1',
    two = '2',
    three = '3',
    four = '4',

class ValidPswitchId(int, Enum):
    one = '1',
    two = '2',

class ValidCoordType(str, Enum):
    eq = 'eq',
    hor = 'hor',
    ha = 'ha',
    azalt = 'azalt'

class PathMaker:
    top_folder: str

    def __init__(self):
        self.top_folder = os.path.join('/var', 'log', 'last')
        pass

    @staticmethod
    def make_seq(path: str):
        seq_file = os.path.join(path, '.seq')

        os.makedirs(os.path.dirname(seq_file), exist_ok=True)
        if os.path.exists(seq_file):
            with open(seq_file) as f:
                seq = int(f.readline())
        else:
            seq = 0
        seq += 1
        with open(seq_file, 'w') as file:
            file.write(f'{seq}\n')

        return seq

    def make_daily_log_folder_name(self):
        dir = os.path.join(self.top_folder, datetime.datetime.now().strftime('%Y-%m-%d'))
        os.makedirs(dir, exist_ok=True)
        return dir
    #
    # def make_exposure_file_name(self):
    #     exposures_folder = os.path.join(self.make_daily_folder_name(), 'Exposures')
    #     os.makedirs(exposures_folder, exist_ok=True)
    #     return os.path.join(exposures_folder, f'exposure-{path_maker.make_seq(exposures_folder):04d}')
    #
    # def make_acquisition_folder_name(self):
    #     acquisitions_folder = os.path.join(self.make_daily_folder_name(), 'Acquisitions')
    #     os.makedirs(acquisitions_folder, exist_ok=True)
    #     return os.path.join(acquisitions_folder, f'acquisition-{PathMaker.make_seq(acquisitions_folder)}')
    #
    # def make_guiding_folder_name(self):
    #     guiding_folder = os.path.join(self.make_daily_folder_name(), 'Guidings')
    #     os.makedirs(guiding_folder, exist_ok=True)
    #     return os.path.join(guiding_folder, f'guiding-{PathMaker.make_seq(guiding_folder)}')

    def make_logfile_name(self):
        daily_folder = self.make_daily_log_folder_name()
        return os.path.join(daily_folder, 'log.txt')


path_maker = PathMaker()


class DailyFileHandler(logging.FileHandler):

    filename: str = ''
    path: str

    def make_file_name(self):
        """
        Produces file names for the DailyFileHandler, which rotates them daily at noon (UT).
        The filename has the format <top><daily><bottom> and includes:
        * A top section (either /var/log/mast on Linux or %LOCALAPPDATA%/mast on Windows
        * The daily section (current date as %Y-%m-%d)
        * The bottom path, supplied by the user
        Examples:
        * /var/log/mast/2022-02-17/server/app.log
        * c:\\User\\User\\LocalAppData\\mast\\2022-02-17\\main.log
        :return:
        """
        top = ''
        if platform.platform() == 'Linux':
            top = os.path.join('var', 'log', 'last')
        elif platform.platform().startswith('Windows'):
            top = os.path.join(os.path.expandvars('%LOCALAPPDATA%'), 'mast')
        now = datetime.datetime.now()
        if now.hour < 12:
            now = now - datetime.timedelta(days=1)
        return os.path.join(top, f'{now:%Y-%m-%d}', self.path)

    def emit(self, record: logging.LogRecord):
        """
        Overrides the logging.FileHandler's emit method.  It is called every time a log record is to be emitted.
        This function checks whether the handler's filename includes the current date segment.
        If not:
        * A new file name is produced
        * The handler's stream is closed
        * A new stream is opened for the new file
        The record is emitted.
        :param record:
        :return:
        """
        filename = self.make_file_name()
        if not filename == self.filename:
            if self.stream is not None:
                # we have an open file handle, clean it up
                self.stream.flush()
                self.stream.close()
                self.stream = None  # See Issue #21742: _open () might fail.

            self.baseFilename = filename
            os.makedirs(os.path.dirname(self.baseFilename), exist_ok=True)
            self.stream = self._open()
        logging.StreamHandler.emit(self, record=record)

    def __init__(self, path: str, mode='a', encoding=None, delay=False, errors=None):
        self.path = path
        if "b" not in mode:
            encoding = default_encoding # io.text_encoding(encoding) # python3.10
        logging.FileHandler.__init__(self, filename='', delay=True, mode=mode, encoding=encoding)


def init_log(logger: logging.Logger):
    logger.propagate = False
    logger.setLevel(default_log_level)
    handler = logging.StreamHandler()
    handler.setLevel(default_log_level)
    formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - {%(name)s:%(funcName)s:%(process)d:%(threadName)s:%(thread)s}' +
                                  ' -  %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    handler = DailyFileHandler(path=path_maker.make_logfile_name(), mode='a')
    handler.setLevel(default_log_level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class DateTimeEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        # Let the base class default method raise the TypeError
        return JSONEncoder.default(self, obj)

def datetime_decoder(dct):
    for key, value in dct.items():
        if isinstance(value, str):
            try:
                dct[key] = datetime.datetime.fromisoformat(value)
            except ValueError:
                pass  # Not a datetime string, so we leave it unchanged
    return dct
    
LAST_API_ROOT = '/last/api/v1/'

class PrettyJSONResponse(Response):
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=4,
            separators=(", ", ": "),
        ).encode(default_encoding)
    
class ResponseDict(dict):
    """
    Defines a Response dictionary which MUST have at least the keys:
    - Response: The actual response, relevant ONLY when 'Error' is None
    - Error: Optional error string
    - ErrorReport: Optional stack trace
    """
    def __init__(self, response: dict, error=None, error_report=None):
        d = dict()
        if error is not None:
            d['Response'] = None
            d['Error'] = error
            d['ErrorReport'] = error_report
        else:
            d['Response'] = response
            d['Error'] = None
            d['ErrorReport'] = None

        super.__init__(Response=d['Response'], Error=d['Error'], ErrorReport=d['ErrorReport'])


class RepeatTimer(Timer):
    def __init__(self, interval, function):
        super(RepeatTimer, self).__init__(interval=interval, function=function)
        self.interval = interval
        self.function = function
        self.stopped = Event()

    def run(self):
        while not self.stopped.wait(self.interval):
            self.function(*self.args, **self.kwargs)

    def stop(self):
        self.stopped.set()


def jsonResponse(obj: object) -> str:
    pretty_json = json.dumps(obj, indent=2, default=str)
    return fastapi.responses.JSONResponse(content=json.loads(pretty_json), media_type="aplication/json")