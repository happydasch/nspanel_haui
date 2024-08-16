import json
from typing import Union


class HAUIEvent:

    """ Event class for HAUI. All events use this class. """

    def __init__(self, name: str, value: Union[int, str, dict]):
        """Initializes the event.

        This class should be used for all events.

        The name and value of the event can be accessed using the as_* methods.

        The processed flag can be set to True to indicate that the event has been processed.
        This is used to prevent processing the same event multiple times.

        Args:
            name (str): The name of the event.
            value (): The value of the event.
        """
        self.name = name
        self.value = value
        self.processed = False

    def as_int(self) -> int:
        """Returns the value as an int.

        Returns:
            int: Value as int
        """
        return int(self.value)

    def as_str(self) -> str:
        """Returns the value as str.

        Returns:
            str: Value as str
        """
        return str(self.value)

    def as_json(self) -> dict:
        """Returns the value as a json.

        Returns:
            dict: Value as json
        """
        if not self.value:
            return {}
        return json.loads(self.value)
