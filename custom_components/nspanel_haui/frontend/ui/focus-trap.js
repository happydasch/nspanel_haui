// @ts-check

// summary: the sidebar forms fold their sections into <details>, whose headings are tab stops.
const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])';

/** Whether Tab can reach the element: not hidden, and not inside a closed section. */
function reachable(element) {
  return !element.hasAttribute?.('hidden') && element.getAttribute?.('aria-hidden') !== 'true'
    && element.checkVisibility?.() !== false;
}

/**
 * The controls Tab stops at, in document order. The sidebar's form lives in the
 * shadow root of an element that takes no focus itself, so every shadow root
 * is searched, not only those of focusable hosts.
 */
function descendants(root, result = []) {
  if (!root?.querySelectorAll) return result;
  for (const element of root.querySelectorAll('*')) {
    if (element.matches?.(FOCUSABLE) && reachable(element)) result.push(element);
    if (element.shadowRoot) descendants(element.shadowRoot, result);
  }
  return result;
}

function deepActiveElement(root) {
  const scope = root?.getRootNode?.();
  let active = scope?.activeElement || root?.ownerDocument?.activeElement;
  while (active?.shadowRoot?.activeElement) active = active.shadowRoot.activeElement;
  return active;
}

/** Keep Tab navigation within a modal dashboard sidebar. */
export function trapTab(event, root) {
  if (event.key !== 'Tab') return false;
  const focusable = descendants(root);
  if (!focusable.length) {
    event.preventDefault();
    root.focus?.();
    return true;
  }
  const active = deepActiveElement(root);
  const index = focusable.indexOf(active);
  const first = focusable[0];
  const last = focusable.at(-1);
  if (event.shiftKey && (index <= 0 || active === root)) {
    event.preventDefault();
    last.focus();
    return true;
  }
  if (!event.shiftKey && (index === focusable.length - 1 || active === root)) {
    event.preventDefault();
    first.focus();
    return true;
  }
  return false;
}
