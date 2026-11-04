// Capture gallery cards as PNG files with one headless Chrome, over the
// DevTools protocol (Node 22+ for its built-in WebSocket; no npm packages).
//
// Usage: node capture.mjs <chrome> <jobs.json>
//
// jobs.json is a list of {url, width, height, path}, written by
// gen_preview_gallery.py --png. Each tab is sized to the display, opens the
// card's single-card gallery URL, waits for the page's `data-ready` (the card
// drawn, its fonts and pictures loaded) and saves a screenshot.
import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';

const TABS = 4;
const [chrome, jobsPath] = process.argv.slice(2);
const jobs = JSON.parse(readFileSync(jobsPath, 'utf8'));
const sleep = (ms) => new Promise((resolve) => { setTimeout(resolve, ms); });

class DevTools {
  constructor(url) {
    this.socket = new WebSocket(url);
    this.nextId = 0;
    this.pending = new Map();
    this.socket.onmessage = ({ data }) => {
      const message = JSON.parse(data);
      const call = this.pending.get(message.id);
      if (!call) return;
      this.pending.delete(message.id);
      if (message.error) call.reject(new Error(`${call.method}: ${message.error.message}`));
      else call.resolve(message.result);
    };
  }

  opened() {
    return new Promise((resolve, reject) => {
      this.socket.onopen = resolve;
      this.socket.onerror = () => reject(new Error('cannot connect to Chrome'));
    });
  }

  send(method, params = {}, sessionId = undefined) {
    this.nextId += 1;
    const id = this.nextId;
    this.socket.send(JSON.stringify({ id, method, params, sessionId }));
    return new Promise((resolve, reject) => this.pending.set(id, { method, resolve, reject }));
  }
}

// Chrome writes the port it picked to DevToolsActivePort in its profile.
async function browserUrl(profile) {
  const file = join(profile, 'DevToolsActivePort');
  for (let attempt = 0; attempt < 300; attempt += 1) {
    if (existsSync(file)) {
      const [port, path] = readFileSync(file, 'utf8').split('\n');
      if (port && path) return `ws://127.0.0.1:${port}${path}`;
    }
    await sleep(50);
  }
  throw new Error(`${chrome} did not start`);
}

async function capture(devtools, sessionId, job) {
  await devtools.send('Emulation.setDeviceMetricsOverride', {
    width: job.width, height: job.height, deviceScaleFactor: 1, mobile: false,
  }, sessionId);
  await devtools.send('Page.navigate', { url: job.url }, sessionId);
  const started = Date.now();
  for (;;) {
    // Until the navigation commits, the tab still shows its previous card.
    const { result } = await devtools.send('Runtime.evaluate', {
      expression: '[location.href, document.body?.dataset.ready, document.body?.dataset.error]',
      returnByValue: true,
    }, sessionId);
    const [href, ready, error] = result.value || [];
    if (href !== job.url) {
      await sleep(50);
      continue;
    }
    if (ready === 'true') break;
    if (ready === 'error') throw new Error(`${job.url}: ${error}`);
    if (Date.now() - started > 30000) throw new Error(`${job.url}: not ready after 30 s`);
    await sleep(50);
  }
  const { data } = await devtools.send('Page.captureScreenshot', { format: 'png' }, sessionId);
  mkdirSync(dirname(job.path), { recursive: true });
  writeFileSync(job.path, Buffer.from(data, 'base64'));
  console.log(job.path);
}

const profile = mkdtempSync(join(tmpdir(), 'haui-gallery-'));
const browser = spawn(chrome, [
  '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
  '--no-default-browser-check', `--user-data-dir=${profile}`, '--remote-debugging-port=0',
  // The tabs run side by side: background tabs must not have their timers
  // and rendering throttled, or a card waits for its turn to be drawn.
  '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
  '--disable-backgrounding-occluded-windows',
  'about:blank',
], { stdio: 'ignore' });
const exited = new Promise((resolve) => { browser.once('exit', resolve); });
let failed = false;
try {
  const devtools = new DevTools(await browserUrl(profile));
  await devtools.opened();
  const queue = [...jobs];
  await Promise.all(Array.from({ length: Math.min(TABS, jobs.length) }, async () => {
    // A window per tab keeps every tab visible: a hidden page never decodes the
    // card's background pictures, so it would never be ready.
    const { targetId } = await devtools.send('Target.createTarget', {
      url: 'about:blank', newWindow: true,
    });
    const { sessionId } = await devtools.send('Target.attachToTarget', { targetId, flatten: true });
    while (queue.length) await capture(devtools, sessionId, queue.shift());
  }));
  await devtools.send('Browser.close');
} catch (err) {
  console.error(err.message);
  failed = true;
} finally {
  browser.kill();
  // Chrome writes to its profile until it has exited.
  await exited;
  rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}
process.exit(failed ? 1 : 0);
