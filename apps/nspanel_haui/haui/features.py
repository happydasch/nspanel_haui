class MediaPlayerFeatures:
    PAUSE = 1                  # (0x0001)
    SEEK = 2                   # (0x0002)
    VOLUME_SET = 4             # (0x0004)
    VOLUME_MUTE = 8            # (0x0008)
    PREVIOUS_TRACK = 16        # (0x0010)
    NEXT_TRACK = 32            # (0x0020)
    TURN_ON = 128              # (0x0080)
    TURN_OFF = 256             # (0x0100)
    PLAY_MEDIA = 512           # (0x0200)
    VOLUME_STEP = 1024         # (0x0400)
    SELECT_SOURCE = 2048       # (0x0800)
    STOP = 4096                # (0x1000)
    CLEAR_PLAYLIST = 8192      # (0x2000)
    PLAY = 16384               # (0x4000)
    SHUFFLE_SET = 32768        # (0x8000)
    SELECT_SOUND_MODE = 65536  # (0x00010000)
    BROWSE_MEDIA = 131072      # (0x00020000)
    REPEAT_SET = 262144        # (0x00040000)
    GROUPING = 524288          # (0x00080000)
    MEDIA_ENQUEUE = 2097152    # (0x00200000)


class VacuumFeatures:
    TURN_ON = 1  # Deprecated, not supported by StateVacuumEntity
    TURN_OFF = 2  # Deprecated, not supported by StateVacuumEntity
    PAUSE = 4
    STOP = 8
    RETURN_HOME = 16
    FAN_SPEED = 32
    BATTERY = 64
    STATUS = 128  # Deprecated, not supported by StateVacuumEntity
    SEND_COMMAND = 256
    LOCATE = 512
    CLEAN_SPOT = 1024
    MAP = 2048
    STATE = 4096  # Must be set by vacuum platforms derived from StateVacuumEntity
    START = 8192


class ClimateFeatures:
    TARGET_TEMPERATURE = 1
    TARGET_TEMPERATURE_RANGE = 2
    TARGET_HUMIDITY = 4
    FAN_MODE = 8
    PRESET_MODE = 16
    SWING_MODE = 32
    AUX_HEAT = 64
    TURN_OFF = 128
    TURN_ON = 256


class CoverFeatures:
    OPEN = 1
    CLOSE = 2
    SET_POSITION = 4
    STOP = 8
    OPEN_TILT = 16
    CLOSE_TILT = 32
    STOP_TILT = 64
    SET_TILT_POSITION = 128
