from enum import Enum

class ValidEquipId(int, Enum):
    one = '1',
    two = '2',
    three = '3',
    four = '4',

class ValidPswitchId(int, Enum):
    one = '1',
    two = '2',

class ValidCoordSystems(str, Enum):
    eq = 'eq',
    hor = 'hor',
    ha = 'ha',
    azalt = 'azalt'