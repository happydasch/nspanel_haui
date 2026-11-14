// Capture the editor of a running Home Assistant with one headless Chrome, over
// the DevTools protocol (Node 22+ for its built-in WebSocket; no npm packages).
//
// Usage: node capture_editor.mjs <chrome> <jobs.json>
//
// jobs.json is {base, tokens, width, height, shots: [{hash, scheme, path, click?}]},
// written by gen_editor_screenshots.py. Each scheme gets its own tab with
// prefers-color-scheme emulated (Home Assistant's default theme follows it), the
// login tokens in localStorage and the Home Assistant sidebar collapsed. A shot
// opens the editor at its hash, waits until every panel preview in view shows
// its render, clicks the button labelled `click` if it has one and saves a
// screenshot.
import { spawn } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { DevTools, browserUrl } from '../preview_gallery/capture.mjs';

const READY_TIMEOUT_MS = 60000;
// Pictures and fonts of a render that has just arrived are still decoding.
const SETTLE_MS = 1500;
const sleep = (ms) => new Promise((resolve) => { setTimeout(resolve, ms); });

// The editor and Home Assistant live in nested shadow roots.
const DEEP_QUERY = `
window.__hauiDeepAll = (selector) => {
  const found = [];
  const walk = (root) => {
    found.push(...root.querySelectorAll(selector));
    for (const el of root.querySelectorAll('*')) if (el.shadowRoot) walk(el.shadowRoot);
  };
  walk(document);
  return found;
};
window.__hauiInView = (el) => {
  const box = el.getBoundingClientRect();
  return box.width > 0 && box.height > 0 && box.bottom > 0 && box.top < innerHeight
    && box.right > 0 && box.left < innerWidth;
};`;

// The previews are the cards' simulator frames and the device's live preview
// stage. Off-screen previews may never be drawn, so only those in view must be ready.
const READY = `(() => {
  if (typeof __hauiDeepAll !== 'function') return { ready: false, state: 'no page script' };
  const frames = __hauiDeepAll('nspanel-simulator-frame, .haui-preview-stage').filter(__hauiInView);
  const loading = __hauiDeepAll('.haui-preview-sim-loading, .haui-preview-stage[aria-busy="true"]')
    .filter(__hauiInView);
  return {
    ready: frames.length > 0 && loading.length === 0,
    state: location.href + ': ' + frames.length + ' previews in view, ' + loading.length + ' loading',
  };
})()`;

const click = (label) => `(() => {
  const button = __hauiDeepAll('button[aria-label=${JSON.stringify(label)}]').find(__hauiInView);
  button?.click();
  return Boolean(button);
})()`;

async function evaluate(devtools, sessionId, expression) {
  const { result, exceptionDetails } = await devtools.send('Runtime.evaluate', {
    expression, returnByValue: true,
  }, sessionId);
  if (exceptionDetails) throw new Error(`${expression}: ${exceptionDetails.text}`);
  return result.value;
}

async function waitReady(devtools, sessionId, what) {
  const started = Date.now();
  for (;;) {
    const { ready, state } = await evaluate(devtools, sessionId, READY);
    if (ready) break;
    if (Date.now() - started > READY_TIMEOUT_MS) throw new Error(`${what}: not ready after 60 s (${state})`);
    await sleep(250);
  }
  await sleep(SETTLE_MS);
}

async function openTab(devtools, jobs, scheme) {
  const { targetId } = await devtools.send('Target.createTarget', { url: 'about:blank', newWindow: true });
  const { sessionId } = await devtools.send('Target.attachToTarget', { targetId, flatten: true });
  const send = (method, params) => devtools.send(method, params, sessionId);
  // Scripts for new documents only run while the Page domain is enabled.
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', {
    width: jobs.width, height: jobs.height, deviceScaleFactor: 1, mobile: false,
  });
  await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: scheme }] });
  const hassTokens = {
    ...jobs.tokens,
    hassUrl: jobs.base,
    clientId: `${jobs.base}/`,
    expires: Date.now() + jobs.tokens.expires_in * 1000,
  };
  await send('Page.addScriptToEvaluateOnNewDocument', {
    source: `
      ${DEEP_QUERY}
      if (location.origin === ${JSON.stringify(jobs.base)}) {
        localStorage.setItem('hassTokens', ${JSON.stringify(JSON.stringify(hassTokens))});
        localStorage.setItem('dockedSidebar', '"auto"');
      }`,
  });
  return sessionId;
}

async function capture(devtools, sessionId, jobs, shot) {
  const url = `${jobs.base}/nspanel-haui${shot.hash}`;
  // A hash change alone would not reload the editor from its start state.
  await devtools.send('Page.navigate', { url: 'about:blank' }, sessionId);
  await devtools.send('Page.navigate', { url }, sessionId);
  await waitReady(devtools, sessionId, url);
  if (shot.click) {
    if (!(await evaluate(devtools, sessionId, click(shot.click)))) {
      throw new Error(`${url}: no button labelled ${shot.click}`);
    }
    await waitReady(devtools, sessionId, `${url} after ${shot.click}`);
  }
  // No hover state on whatever the pointer last touched.
  await devtools.send('Input.dispatchMouseEvent', {
    type: 'mouseMoved', x: jobs.width - 1, y: jobs.height - 1,
  }, sessionId);
  await sleep(300);
  const { data } = await devtools.send('Page.captureScreenshot', { format: 'png' }, sessionId);
  mkdirSync(dirname(shot.path), { recursive: true });
  writeFileSync(shot.path, Buffer.from(data, 'base64'));
  console.log(shot.path);
}

async function main() {
  const [chrome, jobsPath] = process.argv.slice(2);
  const jobs = JSON.parse(readFileSync(jobsPath, 'utf8'));
  const profile = mkdtempSync(join(tmpdir(), 'haui-editor-'));
  const browser = spawn(chrome, [
    '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
    '--no-default-browser-check', '--force-color-profile=srgb', `--user-data-dir=${profile}`,
    '--remote-debugging-port=0', 'about:blank',
  ], { stdio: ['ignore', 'ignore', 'pipe'] });
  let stderr = '';
  browser.stderr.setEncoding('utf8');
  browser.stderr.on('data', (chunk) => { stderr = (stderr + chunk).slice(-8192); });
  const exited = new Promise((resolve) => {
    browser.once('close', (code, signal) => resolve({ code, signal }));
  });
  let failed = false;
  try {
    const devtools = new DevTools(await browserUrl(profile, exited, () => stderr.trim(), chrome));
    await devtools.opened();
    const tabs = new Map();
    for (const shot of jobs.shots) {
      if (!tabs.has(shot.scheme)) tabs.set(shot.scheme, await openTab(devtools, jobs, shot.scheme));
      await capture(devtools, tabs.get(shot.scheme), jobs, shot);
    }
    await devtools.send('Browser.close');
  } catch (err) {
    console.error(err.message);
    failed = true;
  } finally {
    browser.kill();
    await exited;
    rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
  }
  process.exitCode = failed ? 1 : 0;
}

main();
