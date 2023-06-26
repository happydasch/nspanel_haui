import datetime

from ..helper.datetime import get_time_localized, \
    get_date_localized
from ..config import HAUIConfigEntity

from . import HAUIPage


class WeatherPage(HAUIPage):

    # time and date display
    TXT_TIME, TXT_DATE = (4, 'tTime'), (5, 'tDate')
    # main weather icon
    ICO_MAIN, TXT_MAIN, TXT_SUB = (6, 'tMainIcon'), (7, 'tMainText'), (8, 'tSubText')
    # icons below main icon
    D1_ICO, D1_VAL = (9, 'd1Icon'), (10, 'd1Val')
    D2_ICO, D2_VAL = (11, 'd2Icon'), (12, 'd2Val')
    D3_ICO, D3_VAL = (13, 'd3Icon'), (14, 'd3Val')
    # bottom weather forecast row
    F1_NAME, F1_ICO, F1_VAL = (15, 'f1Name'), (16, 'f1Icon'), (17, 'f1Val')
    F2_NAME, F2_ICO, F2_VAL = (18, 'f2Name'), (19, 'f2Icon'), (20, 'f2Val')
    F3_NAME, F3_ICO, F3_VAL = (21, 'f3Name'), (22, 'f3Icon'), (23, 'f3Val')
    F4_NAME, F4_ICO, F4_VAL = (24, 'f4Name'), (25, 'f4Icon'), (26, 'f4Val')
    F5_NAME, F5_ICO, F5_VAL = (27, 'f5Name'), (28, 'f5Icon'), (29, 'f5Val')

    # page

    def start_page(self):
        # time update callback
        time = datetime.time(0, 0, 0)
        self._time_timer = self.app.run_minutely(
            self.callback_update_time, time)
        # setup date callback
        self._date_timer = self.app.run_hourly(
            self.callback_update_date, time)

    def stop_page(self):
        # cancel time and date timer
        if self._time_timer:
            self.app.cancel_timer(self._time_timer)
            self._time_timer = None
        if self._date_timer:
            self.app.cancel_timer(self._date_timer)
            self._date_timer = None

    # panel

    def start_panel(self, panel):
        # entities
        self._handles = []
        for entity in panel.get_entities():
            if entity.get_entity_type() == 'weather':
                self.add_entity_listener(
                    entity.get_entity_id(),
                    self.callback_weather)

    def render_panel(self, panel):
        # time display
        self.update_time()
        # date display
        self.update_date()
        # entities
        self.update_entities(panel.get_entities())

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
            for i in range(5):
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
        for i in range(5):
            if not len(entities):
                break
            forecast.append(entities.pop(0))
            if len(forecast) == 5:
                break
        for i in range(len(forecast)):
            self.update_forecast(forecast[i], i + 1)

        # next 3 are entities below main weather
        info = []
        for i in range(3):
            if not len(entities):
                break
            info.append(entities.pop(0))
            if len(info) == 3:
                break
        for i in range(len(info)):
            self.update_info(info[i], i)

    def update_main_weather(self, haui_entity):
        # set up main weather details
        icon = haui_entity.get_icon()
        color = haui_entity.get_color()
        msg = haui_entity.get_value()
        msg_sub = haui_entity.get_entity_attr('pressure', '')
        if msg_sub:
            pressure_unit = haui_entity.get_entity_attr('pressure_unit')
            msg_sub = f'{msg_sub}{pressure_unit}'
        self.set_component_text_color(self.ICO_MAIN, color)
        self.set_component_text(self.ICO_MAIN, icon)
        self.set_component_text(self.TXT_MAIN, msg)
        self.set_component_text(self.TXT_SUB, msg_sub)

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

    def update_info(self, haui_entity, idx):
        if idx < 1 or idx > 5:
            self.log("Weather Info uses index 1-3")
            return
        info_icon = getattr(self, f'D{idx}_ICO')
        info_val = getattr(self, f'D{idx}_VAL')
        self.set_component_text_color(info_icon, haui_entity.get_color())
        self.set_component_text(info_icon, haui_entity.get_icon())
        self.set_component_text(info_val, haui_entity.get_value())

    # callback

    def callback_update_time(self, cb_args):
        if self.app.device.sleeping:
            return
        self.update_time()

    def callback_update_date(self, cb_args):
        if self.app.device.sleeping:
            return
        self.update_date()

    def callback_weather(self, entity, attribute, old, new, kwargs):
        if self.app.device.sleeping:
            return
        self.refresh_panel()
