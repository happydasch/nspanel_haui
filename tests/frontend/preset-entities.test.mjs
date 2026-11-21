import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  areaOptions,
  areaSensor,
  domainEntities,
  entitiesInArea,
  hasEntities,
  lookupEntities,
} from '../../custom_components/nspanel_haui/frontend/preset-entities.js';
import { registryWorld } from './support/hass.mjs';

/** Two areas, one entity in the kitchen through its device, one hidden, one config entry. */
function world() {
  return {
    ...registryWorld({
      areas: [
        { area_id: 'bedroom', name: 'Bedroom' },
        {
          area_id: 'kitchen',
          name: 'Kitchen',
          temperature_entity_id: 'sensor.kitchen_temperature',
        },
      ],
      devices: [{ id: 'dev_clock', area_id: 'kitchen' }],
      entities: [
        { entity_id: 'light.kitchen', area_id: 'kitchen', name: 'Kitchen lamp' },
        { entity_id: 'light.hall', device_id: 'dev_clock' },
        { entity_id: 'light.bedroom', area_id: 'bedroom' },
        { entity_id: 'light.hidden', area_id: 'kitchen', hidden: true },
        { entity_id: 'light.diagnostic', area_id: 'kitchen', entity_category: 'diagnostic' },
        { entity_id: 'light.disabled', area_id: 'kitchen', disabled_by: 'user' },
        { entity_id: 'switch.kettle', area_id: 'kitchen' },
        { entity_id: 'sensor.kitchen_temperature', area_id: 'kitchen' },
        { entity_id: 'sensor.humidity', area_id: 'kitchen', name: 'Humidity' },
        { entity_id: 'weather.home' },
      ],
    }),
    states: {
      'light.kitchen': { state: 'on' },
      'light.hall': { state: 'unavailable' },
      'light.bedroom': { state: 'off' },
      'switch.kettle': { state: 'on' },
      'sensor.kitchen_temperature': { state: '21.5' },
      'sensor.humidity': {
        state: '48',
        attributes: { device_class: 'humidity' },
      },
      'weather.home': { state: 'sunny' },
    },
  };
}

test('the areas are listed by name', () => {
  assert.deepEqual(areaOptions(world()), [
    { area_id: 'bedroom', name: 'Bedroom' },
    { area_id: 'kitchen', name: 'Kitchen' },
  ]);
  assert.deepEqual(areaOptions({}), []);
  assert.deepEqual(areaOptions(null), []);
});

test('an entity is in an area through its own area or through its device', () => {
  const hass = world();
  assert.deepEqual(entitiesInArea(hass, 'kitchen', ['light']).sort(),
    ['light.hall', 'light.kitchen']);
  assert.deepEqual(entitiesInArea(hass, 'bedroom', ['light']), ['light.bedroom']);
  // An entity without an area of its own is in no area.
  assert.deepEqual(entitiesInArea(hass, 'kitchen', ['weather']), []);
});

test('hidden, configuration and disabled entities are never offered', () => {
  const ids = entitiesInArea(world(), 'kitchen', ['light']);
  for (const skipped of ['light.hidden', 'light.diagnostic', 'light.disabled']) {
    assert.ok(!ids.includes(skipped), skipped);
  }
});

test('entities in a usable state come first, then by name', () => {
  // The unavailable one is offered last even though it sorts first by id.
  assert.deepEqual(entitiesInArea(world(), 'kitchen', ['light']), ['light.kitchen', 'light.hall']);
  const hass = world();
  hass.states['light.kitchen'] = { state: 'unavailable' };
  hass.entities['light.aaa'] = { area_id: 'kitchen', name: 'A lamp' };
  hass.states['light.aaa'] = { state: 'on' };
  assert.equal(entitiesInArea(hass, 'kitchen', ['light'])[0], 'light.aaa');
});

test('the whole installation is every offerable entity of the domains', () => {
  const hass = world();
  assert.deepEqual(domainEntities(hass, ['weather']), ['weather.home']);
  assert.ok(domainEntities(hass, ['light']).length >= 2);
  assert.equal(hasEntities(hass, ['vacuum']), false);
  assert.equal(hasEntities(hass, ['switch']), true);
  assert.equal(hasEntities(hass, ['switch'], 'bedroom'), false);
});

test('an area prefers the sensor it registers, then one that measures it', () => {
  const hass = world();
  assert.equal(areaSensor(hass, 'kitchen', 'temperature'), 'sensor.kitchen_temperature');
  assert.equal(areaSensor(hass, 'kitchen', 'humidity'), 'sensor.humidity');
  // Without an area or without a matching sensor there is none.
  assert.equal(areaSensor(hass, '', 'temperature'), '');
  assert.equal(areaSensor(hass, 'bedroom', 'temperature'), '');
});

test('a lookup is memoised per registry snapshot, not per state', () => {
  const hass = world();
  const first = lookupEntities(hass, 'kitchen', ['light']);
  // The same registry record answers with the same list, even after a state moved on.
  const next = { ...hass, states: { ...hass.states } };
  assert.equal(lookupEntities(next, 'kitchen', ['light']), first);
  // A new registry record is a new lookup.
  const renamed = { ...hass, entities: { ...hass.entities } };
  assert.notEqual(lookupEntities(renamed, 'kitchen', ['light']), first);
  assert.deepEqual(lookupEntities(renamed, 'kitchen', ['light']), first);
  // The devices record decides area membership, so a new one recomputes.
  const moved = { ...hass, devices: { dev_clock: { area_id: 'bedroom' } } };
  assert.deepEqual(lookupEntities(moved, 'kitchen', ['light']), ['light.kitchen']);
});

test('an empty or missing registry offers nothing', () => {
  assert.deepEqual(lookupEntities({}, 'kitchen', ['light']), []);
  assert.deepEqual(domainEntities(null, ['light']), []);
  assert.equal(hasEntities(null, ['light']), false);
});
