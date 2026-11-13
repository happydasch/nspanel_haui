/** Return a minimal response understood by the editor API client. */
export function jsonResponse(body, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

/** Build a Home Assistant facade with observable calls and controllable websocket subscriptions. */
export function makeHass(overrides = {}) {
  const calls = [];
  const subscriptions = [];
  const messages = [];
  const states = overrides.states || {};
  const connection = {
    async sendMessagePromise(message) {
      messages.push(message);
      return overrides.sendMessagePromise ? overrides.sendMessagePromise(message) : [];
    },
    subscribeMessage(callback, message, options) {
      const subscription = { callback, message, options, active: true };
      subscriptions.push(subscription);
      return () => { subscription.active = false; };
    },
    subscribeEvents(callback, eventType) {
      const subscription = { callback, eventType, active: true };
      subscriptions.push(subscription);
      return () => { subscription.active = false; };
    },
  };
  const hass = {
    ...overrides,
    language: overrides.language || 'en',
    locale: overrides.locale || { language: overrides.language || 'en' },
    states,
    connection: overrides.connection || connection,
    async fetchWithAuth(url, options = {}) {
      calls.push({ url, options });
      return overrides.fetchWithAuth
        ? overrides.fetchWithAuth(url, options)
        : { ok: true, status: 200, json: async () => ({}) };
    },
    async callWS(message) {
      messages.push(message);
      return overrides.callWS ? overrides.callWS(message) : [];
    },
    formatEntityState(entityId) { return states[entityId]?.state ?? ''; },
    calls,
    messages,
    subscriptions,
  };
  hass.publish = (subscription, value) => subscription.callback(value);
  return hass;
}
