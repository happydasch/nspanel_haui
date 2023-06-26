from . import HAUIPage


class MediaPage(HAUIPage):

    # common components
    BTN_NAV_LEFT, BTN_NAV_RIGHT = (4, 'bNavLeft'), (5, 'bNavRight')
    TXT_TITLE = (6, 'tTitle')
    # entities
    B1_ENTITY, B2_ENTITY, B3_ENTITY = (7, 'bEntity1'), (8, 'bEntity2'), (9, 'bEntity3')
    B4_ENTITY, B5_ENTITY, B6_ENTITY = (10, 'bEntity4'), (10, 'bEntity5'), (12, 'bEntity6')
    # basic info
    TXT_NAME, TXT_INTERPRET = (13, 'tName'), (14, 'tInterpret')
    # control
    TXT_SHUFFLE, TXT_PREV, TXT_PLAY_PAUSE = (15, 'tShuffle'), (16, 'tPrev'), (17, 'tPlayPause')
    TXT_NEXT, TXT_STOP, TXT_VOL_DOWN = (18, 'tNext'), (19, 'tStop'), (20, 'tVolDown')
    SLIDER_VOLUME, TXT_VOL_UP = (21, 'hVolume'), (22, 'tVolUp')

    # panel

    def start_panel(self, panel):
        self.set_prev_next_nav_buttons(self.BTN_NAV_LEFT, self.BTN_NAV_RIGHT)

    def render_panel(self, panel):
        self.set_component_text(self.TXT_TITLE, panel.get_title())
