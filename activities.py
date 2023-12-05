from enum import IntFlag

Idle = 0

class Activities:
    _activities: IntFlag

    def __init__(self) -> None:
        self._activities = Idle

    def start_activity(self, activities: IntFlag):
        self._activities |= activities

    def end_activity(self, activities: IntFlag):
        self._activities &= ~activities

    def is_active(self, activity: IntFlag):
        return self._activities & activity != Idle

    def is_idle(self):
        return self._activities == Idle
    
    def activities(self) -> IntFlag:
        return self._activities
        

class UnitActivities(IntFlag):
    StartingUp = (1 << 0)
    ShuttingDown = (1 << 1)
    Slewing = (1 << 2)
    Autofocusing = (1 << 3)
    Exposing = (1 << 4)
    Aborting = (1 << 5)

class MountActivities(IntFlag):
    StartingUp = (1 << 0)
    ShuttingDown = (1 << 1)
    Slewing = (1 << 2)
    Parking = (1 << 3)

class CameraActivities(IntFlag):
    StartingUp = (1 << 0)
    ShuttingDown = (1 << 1)
    CoolingDown = (1 << 2)
    WarmingUp = (1 << 3)
    Exposing = (1 << 4)

class FocuserActivities(IntFlag):
    Moving = (1 << 0)
