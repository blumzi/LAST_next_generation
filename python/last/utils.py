from enum import Enum
import logging
import platform
import os
import datetime
import io

default_log_level = logging.DEBUG


class Equipment(Enum):
    Mount = 1,
    Camera = 2,
    Focuser = 3
    Test = 4


equipment_ids = {
    "e": [1, 2],
    "w": [3, 4],
}


class PathMaker:
    top_folder: str

    def __init__(self):
        #self.top_folder = config.get('global', 'TopFolder')
        self.top_folder = os.path.join('var', 'log')
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
        daily_folder = os.path.join(self.make_daily_log_folder_name())
        os.makedirs(daily_folder)
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
            top = '/var/log/last'
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
            encoding = io.text_encoding(encoding)
        logging.FileHandler.__init__(self, filename='', delay=True, mode=mode, encoding=encoding, errors=errors)


def init_log(logger: logging.Logger):
    logger.propagate = False
    logger.setLevel(default_log_level)
    handler = logging.StreamHandler()
    handler.setLevel(default_log_level)
    formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - {%(name)s:%(funcName)s:%(threadName)s:%(thread)s}' +
                                  ' -  %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # path_maker = SingletonFactory.get_instance(PathMaker)
    handler = DailyFileHandler(path=os.path.join(path_maker.make_daily_log_folder_name(), 'log.txt'), mode='a')
    handler.setLevel(default_log_level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)