import datetime

from ..mapping.background import BACKGROUNDS
from ..helper.datetime import get_time_localized, \
    get_date_localized
from ..config import HAUIConfigEntity

from . import HAUIPage


class ClockPage(HAUIPage):

    # main components
    TXT_TIME, TXT_DATE = (2, 'tTime'), (3, 'tDate')
    ICO_MAIN, TXT_MAIN = (4, 'tMainIcon'), (5, 'tMainText')

    # bottom weather forecast row
    F1_NAME, F2_NAME, F3_NAME, F4_NAME = (6, 'f1Name'), (7, 'f2Name'), (8, 'f3Name'), (9, 'f4Name')
    F1_ICO, F2_ICO, F3_ICO, F4_ICO = (10, 'f1Icon'), (11, 'f2Icon'), (12, 'f3Icon'), (13, 'f4Icon')
    F1_VAL, F2_VAL, F3_VAL, F4_VAL = (14, 'f1Val'), (15, 'f2Val'), (16, 'f3Val'), (17, 'f4Val')
    F1_SUBVAL, F2_SUBVAL, F3_SUBVAL, F4_SUBVAL = (18, 'f1SubVal'), (19, 'f2SubVal'), (20, 'f3SubVal'), (21, 'f4SubVal')

    # panel

    def create_panel(self, panel):
        # setting: background
        background = panel.get('background', 'default')
        background = self.render_template(background, False)
        if background in BACKGROUNDS:
            self.send_cmd(f'clock.background.val={BACKGROUNDS[background]}')

    def start_panel(self, panel):
        # time update callback
        time = datetime.time(0, 0, 0)
        self._time_timer = self.app.run_minutely(
            self.callback_update_time, time)
        # date update callback
        self._date_timer = self.app.run_hourly(
            self.callback_update_date, time)
        # entity listeners
        for entity in panel.get_entities():
            if entity.get_entity_type() == 'weather':
                self.add_entity_listener(
                    entity.get_entity_id(), self.callback_weather)
        # setting: show_weather
        if not panel.get('show_weather', True):
            self.hide_component(self.ICO_MAIN)
        # setting: show_temp
        if not panel.get('show_temp', True):
            self.hide_component(self.TXT_MAIN)

    def render_panel(self, panel):
        # time display
        self.update_time()
        # date display
        self.update_date()
        # entities
        self.update_entities(panel.get_entities())

    def stop_panel(self, panel):
        # cancel time and date timer
        if self._time_timer:
            self.app.cancel_timer(self._time_timer)
            self._time_timer = None
        if self._date_timer:
            self.app.cancel_timer(self._date_timer)
            self._date_timer = None

    # misc

    def update_time(self):
        timeformat = self.app.config.get('time_format')
        time = get_time_localized(timeformat)
        self.set_component_text(self.TXT_TIME, time)

    def update_date(self):
        strftime_format = self.app.config.get('date_format')
        babel_format = self.app.config.get('date_format_babel')
        locale = self.app.device.get_locale()
        date = get_date_localized(strftime_format, babel_format, locale)
        self.set_component_text(self.TXT_DATE, date)

    def update_entities(self, entities):
        # if only one entry, create new entities which will be used for
        # forecast
        if len(entities) == 1:
            for i in range(4):
                config = {
                    'entity': entities[0].get('entity'),
                    'forecast_index': i
                }
                entities.append(
                    HAUIConfigEntity(self.app, config))

        # first entity is main weather entity
        main = None
        if len(entities):
            main = entities.pop(0)
        if main is not None:
            self.update_main_weather(main)

        # next 5 are weather forecast entities
        forecast = []
        for i in range(4):
            if not len(entities):
                break
            forecast.append(entities.pop(0))
            if len(forecast) == 4:
                break
        for i in range(len(forecast)):
            self.update_forecast(forecast[i], i + 1)

    def update_main_weather(self, haui_entity):
        # set up main weather details
        icon = haui_entity.get_icon()
        color = haui_entity.get_color()
        msg = haui_entity.get_value()
        self.set_component_text_color(self.ICO_MAIN, color)
        self.set_component_text(self.ICO_MAIN, icon)
        self.set_component_text(self.TXT_MAIN, msg)

    def update_forecast(self, haui_entity, idx):
        if idx < 1 or idx > 5:
            self.log("Weather Forecast uses index 1-5")
            return
        forecast_name = getattr(self, f'F{idx}_NAME')
        forecast_icon = getattr(self, f'F{idx}_ICO')
        forecast_val = getattr(self, f'F{idx}_VAL')
        self.set_component_text_color(forecast_icon, haui_entity.get_color())
        self.set_component_text(forecast_icon, haui_entity.get_icon())
        self.set_component_text(forecast_name, haui_entity.get_name())
        self.set_component_text(forecast_val, haui_entity.get_value())

    # callback

    def callback_update_time(self, cb_args):
        self.log(f'Got update time callback: {cb_args}')
        if self.app.device.sleeping:
            return
        self.update_time()

    def callback_update_date(self, cb_args):
        self.log(f'Got update date callback: {cb_args}')
        if self.app.device.sleeping:
            return
        self.update_date()

    def callback_weather(self, entity, attribute, old, new, kwargs):
        self.log(f'Got weather callback: {entity}.{attribute}:{new}')
        if self.app.device.sleeping:
            return
        self.refresh_panel()
