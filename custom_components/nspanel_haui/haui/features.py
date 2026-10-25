class MediaPlayerFeatures:
    PAUSE = 1  # (0x0001)
    VOLUME_SET = 4  # (0x0004)
    PREVIOUS_TRACK = 16  # (0x0010)
    NEXT_TRACK = 32  # (0x0020)
    TURN_ON = 128  # (0x0080)
    SELECT_SOURCE = 2048  # (0x0800)
    PLAY = 16384  # (0x4000)
    SHUFFLE_SET = 32768  # (0x8000)
    REPEAT_SET = 262144  # (0x00040000)
    GROUPING = 524288  # (0x00080000)


class VacuumFeatures:
    PAUSE = 4
    STATE = 4096  # Must be set by vacuum platforms derived from StateVacuumEntity
    STOP = 8
    RETURN_HOME = 16
    FAN_SPEED = 32
    BATTERY = 64
    LOCATE = 512
    START = 8192


class ClimateFeatures:
    TARGET_TEMPERATURE = 1
    TARGET_TEMPERATURE_RANGE = 2
    FAN_MODE = 8
    PRESET_MODE = 16
    SWING_MODE = 32


class CoverFeatures:
    OPEN = 1
    CLOSE = 2
    SET_POSITION = 4
    STOP = 8
