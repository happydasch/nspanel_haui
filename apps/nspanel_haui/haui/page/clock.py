import datetime

from ..helper.datetime import get_time_localized, \
    get_date_localized
from ..config import HAUIConfigEntity

from . import HAUIPage


class ClockPage(HAUIPage):

    # time and date display
    TXT_TIME, TXT_DATE = (4, 'tTime'), (5, 'tDate')
    # main weather icon
    ICO_MAIN = (6, 'tMainIcon')
    TXT_MAIN = (7, 'tMainText')
    TXT_SUB = (8, 'tSubText')
    # bottom weather forecast row
    F1_NAME, F1_ICO, F1_VAL = (9, 'f1Name'), (10, 'f1Icon'), (11, 'f1Val')
    F2_NAME, F2_ICO, F2_VAL = (12, 'f2Name'), (13, 'f2Icon'), (14, 'f2Val')
    F3_NAME, F3_ICO, F3_VAL = (15, 'f3Name'), (16, 'f3Icon'), (17, 'f3Val')
    F4_NAME, F4_ICO, F4_VAL = (18, 'f4Name'), (19, 'f4Icon'), (20, 'f4Val')

    # page

    def start_page(self):
        # time update callback
        time = datetime.time(0, 0, 0)
        self._time_timer = self.app.run_minutely(
            self.callback_update_time, time)
        # Setup date callback
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
        for entity in panel.get_entities():
            if entity.get_entity_type() == 'weather':
                self.add_entity_listener(
                    entity.get_entity_id(), self.callback_weather)

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
