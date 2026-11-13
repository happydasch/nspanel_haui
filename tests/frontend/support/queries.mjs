import { eventListeners } from './browser.mjs';

const roles = {
  button: 'button', link: 'a[href]', textbox: 'input:not([type=button]):not([type=submit]), textarea',
  checkbox: 'input[type=checkbox]', radio: 'input[type=radio]', combobox: 'select',
  heading: 'h1,h2,h3,h4,h5,h6', img: 'img,[role=img]', dialog: 'dialog,[role=dialog]',
};

export function byRole(root, role, { name, exact = true } = {}) {
  const selectors = [roles[role], '[role="' + role + '"]'].filter(Boolean).join(',');
  const candidates = [...root.querySelectorAll(selectors)];
  const named = name === undefined ? candidates : candidates.filter((element) => {
    const label = accessibleName(element);
    return exact ? label === name : label.includes(name);
  });
  return named[0] || null;
}

export function byLabel(root, label) {
  const explicit = [...root.querySelectorAll('label[for]')].find((node) => node.textContent.trim() === label);
  if (explicit) return root.querySelector('#' + CSS.escape(explicit.htmlFor));
  return [...root.querySelectorAll('label')].find((node) => node.textContent.trim() === label)?.querySelector('input,select,textarea') || null;
}

export function byClass(root, className) { return root.querySelector('.' + CSS.escape(className)); }
export function byText(root, text, { exact = true } = {}) {
  return [...root.querySelectorAll('*')].find((element) => {
    if ([...element.children].some((child) => child.textContent.trim() === text)) return false;
    const value = element.textContent.trim();
    return exact ? value === text : value.includes(text);
  }) || null;
}

export function accessibleName(element) {
  const labelledBy = element.getAttribute('aria-labelledby');
  if (labelledBy) return labelledBy.split(/\s+/).map((id) => element.ownerDocument.getElementById(id)?.textContent.trim() || '').join(' ').trim();
  if (element.getAttribute('aria-label')) return element.getAttribute('aria-label').trim();
  if (element.labels?.length) return [...element.labels].map((label) => label.textContent.trim()).join(' ').trim();
  if (element.getAttribute('alt')) return element.getAttribute('alt').trim();
  return element.textContent.trim();
}

/** Return listeners attached to an element; prefer dispatching real events in tests. */
export function handlers(element) {
  return Object.fromEntries([...eventListeners(element)].map(([type, callbacks]) => [type, [...callbacks]]));
}
