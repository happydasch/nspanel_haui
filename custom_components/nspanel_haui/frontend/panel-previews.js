/**
 * NSPanel HAUI - Editor - Panel preview renderers.
 *
 * Registry for custom panel previews shown in the grid view card body.
 * Each panel type can register a renderer; if none is registered the
 * default fallback (icon only) is used.
 *
 * This module provides reusable visual primitives (simScreen, simHeader,
 * simTile, simSlider, etc.) and per-panel-type renderers that compose them
 * to give a meaningful visual hint of the panel layout and config.
 */
import { registerPanelPreview, renderPanelPreview } from './previews/registry.js';
import { renderGridPreview } from './previews/grid.js';
import { renderRowPreview } from './previews/row.js';
import { renderLightPreview } from './previews/light.js';
import { renderClimatePreview } from './previews/climate.js';
import { renderMediaPreview } from './previews/media.js';
import { renderCoverPreview } from './previews/cover.js';
import { renderVacuumPreview } from './previews/vacuum.js';
import { renderTimerPreview } from './previews/timer.js';
import { renderAlarmPreview, renderUnlockPreview } from './previews/alarm.js';
import { renderClockPreview, renderClockTwoPreview } from './previews/clock.js';
import { renderWeatherPreview } from './previews/weather.js';
import { renderQRPreview } from './previews/qr.js';
import { renderNotifyPreview } from './previews/notify.js';
import { renderSelectPreview } from './previews/select.js';
import { renderSettingsPreview } from './previews/settings.js';
import { renderAboutPreview } from './previews/about.js';
import { renderSystemPreview } from './previews/system.js';
import { renderBlankPreview } from './previews/blank.js';

export { registerPanelPreview, renderPanelPreview };

/* ── Register all preview renderers ────────────────────────────── */
registerPanelPreview('grid', renderGridPreview);
registerPanelPreview('row', renderRowPreview);
registerPanelPreview('light', renderLightPreview);
registerPanelPreview('climate', renderClimatePreview);
registerPanelPreview('media', renderMediaPreview);
registerPanelPreview('cover', renderCoverPreview);
registerPanelPreview('vacuum', renderVacuumPreview);
registerPanelPreview('timer', renderTimerPreview);
registerPanelPreview('alarm', renderAlarmPreview);
registerPanelPreview('clock', renderClockPreview);
registerPanelPreview('clocktwo', renderClockTwoPreview);
registerPanelPreview('weather', renderWeatherPreview);
registerPanelPreview('qr', renderQRPreview);
registerPanelPreview('notify', renderNotifyPreview);
registerPanelPreview('notifs', renderNotifyPreview);
registerPanelPreview('select', renderSelectPreview);
registerPanelPreview('system_settings', renderSettingsPreview);
registerPanelPreview('system_about', renderAboutPreview);
registerPanelPreview('system', renderSystemPreview);
registerPanelPreview('blank', renderBlankPreview);
// Popup aliases share renderers with their base types (handled via panel.type)
registerPanelPreview('popup_unlock', renderUnlockPreview);
registerPanelPreview('popup_notify', renderNotifyPreview);
registerPanelPreview('popup_notifs', renderNotifyPreview);
registerPanelPreview('popup_select', renderSelectPreview);
registerPanelPreview('popup_light', renderLightPreview);
registerPanelPreview('popup_media_player', renderMediaPreview);
registerPanelPreview('popup_vacuum', renderVacuumPreview);
registerPanelPreview('popup_climate', renderClimatePreview);
registerPanelPreview('popup_timer', renderTimerPreview);
registerPanelPreview('popup_cover', renderCoverPreview);
