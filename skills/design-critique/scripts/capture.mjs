#!/usr/bin/env node
// Capture one route for /design-critique: a PNG per state and viewport, an axe report and a manifest.
// Playwright and axe-core load from Pixie's own cache, never from the target repo.
//
//   node capture.mjs --url URL --out DIR [--viewports 390,1280] [--states JSON|FILE] [--storage-state FILE]
//   node capture.mjs --url BASE --out DIR --matrix JSON|FILE [--viewports 390,1280] [--storage-state FILE]
//
// --matrix captures a preview harness's state matrix instead of one page; its paths resolve against BASE.
//
// Exit codes: 0 captured (per-state errors are in the manifest), 1 bad options or the page failed to load,
// 3 Playwright, axe-core or Chromium missing from the cache. PIXIE_PLAYWRIGHT_DIR points at another cache, for testing.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { homedir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const MAX_WIDTH = 1280;
const MAX_HEIGHT = 4000;
const STEP_TIMEOUT_MS = 10000;
const LOAD_TIMEOUT_MS = 60000;
const ACTIONS = ["click", "fill", "press", "hover", "waitFor"];
const REQUIRED_STATES = ["empty", "single", "typical", "overflow", "error", "loading"];
const CACHE =process.env.PIXIE_PLAYWRIGHT_DIR || join(homedir(), ".cache", "pixie", "playwright");

const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

// An option's JSON comes inline or from a file.
const readJson = (value) => JSON.parse(/^\s*[[{]/.test(value) ? value : readFileSync(value, "utf8"));

// States: [{ "name": "menu open", "steps": [{ "click": "SELECTOR" }] }].
function checkStates(states) {
  for (const s of states) {
    if (typeof s.name !== "string" || !slug(s.name)) {
      throw new Error(`every state needs a name with letters or digits: ${JSON.stringify(s)}`);
    }
    const unknown = (s.steps ?? []).map((step) => Object.keys(step)[0]).find((a) => !ACTIONS.includes(a));
    if (unknown) throw new Error(`state "${s.name}": unknown step ${unknown}; use ${ACTIONS.join(", ")}`);
  }
  return states;
}

// A preview's state matrix: { "states": { "empty": "/__preview/x?state=empty", ... }, "interactions": [
// { "name": "menu open", "from": "typical", "steps": [...], "viewports": [390] }] }. Every state is shot at
// the widest viewport, and typical and overflow at the others too. Any state beyond the six is shot as well.
// An interaction replays its steps on its base state's page, at the widest viewport unless it names others.
function planMatrix(value, base, widths) {
  const m = readJson(value);
  const missing = REQUIRED_STATES.filter((s) => !(typeof m.states?.[s] === "string" && m.states[s]));
  if (missing.length) throw new Error(`the preview is missing required states: ${missing.join(", ")}`);
  const names = [...REQUIRED_STATES, ...checkStates(Object.keys(m.states).filter((s) => !REQUIRED_STATES.includes(s))
    .map((name) => ({ name }))).map((s) => s.name)];
  const desktop = Math.max(...widths);
  const url = (name) => new URL(m.states[name], base).href;
  const interactions = checkStates(m.interactions ?? []);
  for (const i of interactions) {
    if (!names.includes(i.from)) throw new Error(`interaction "${i.name}" starts from unknown state "${i.from}"`);
    const other = (i.viewports ?? []).find((w) => !widths.includes(w));
    if (other !== undefined) throw new Error(`interaction "${i.name}": viewport ${other} isn't one of ${widths}`);
  }
  return [
    ...names.map((name) => ({
      name, url: url(name), steps: [], widths: ["typical", "overflow"].includes(name) ? widths : [desktop],
    })),
    ...interactions.map((i) => ({
      name: i.name, url: url(i.from), steps: i.steps ?? [], widths: i.viewports ?? [desktop],
    })),
  ];
}

export function parseOptions(argv) {
  const o = { viewports: "390,1280" };
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i].replace(/^--/, "").replace(/-(.)/g, (_, c) => c.toUpperCase());
    o[key] = argv[i + 1];
  }
  if (!o.url) throw new Error("--url is required");
  if (!o.out) throw new Error("--out is required");
  const widths = o.viewports.split(",").map(Number);
  for (const w of widths) {
    if (!(Number.isInteger(w) && w > 0 && w <= MAX_WIDTH)) {
      throw new Error(`viewport ${w} must be a whole number from 1 to ${MAX_WIDTH}`);
    }
  }
  if (o.matrix && o.states) throw new Error("use --matrix or --states, not both");
  const states = o.matrix
    ? planMatrix(o.matrix, o.url, widths)
    : checkStates(readJson(o.states ?? '[{"name":"default","steps":[]}]')).map((s) => ({ name: s.name, url: o.url, steps: s.steps ?? [], widths }));
  o.shots = states.flatMap((s) =>
    s.widths.map((width) => ({
      file: `shots/${slug(s.name)}-${width}.png`,
      state: s.name,
      url: s.url,
      steps: s.steps,
      viewport: { width, height: width <= 480 ? 844 : 800 },
    })),
  );
  const files = new Map();
  for (const shot of o.shots) {
    const other = files.get(shot.file);
    if (other) throw new Error(`"${other.state}" and "${shot.state}" at ${shot.viewport.width} would save to the same file`);
    files.set(shot.file, shot);
  }
  return o;
}

function loadTools() {
  process.env.PLAYWRIGHT_BROWSERS_PATH = join(CACHE, "browsers");
  const require = createRequire(join(CACHE, "noop.js"));
  try {
    return { chromium: require("playwright").chromium, axe: readFileSync(require.resolve("axe-core/axe.min.js"), "utf8") };
  } catch {
    return null;
  }
}

async function runStep(page, step) {
  const [action, arg] = Object.entries(step)[0];
  if (action === "fill") return page.fill(arg[0], arg[1]);
  if (action === "press") return page.keyboard.press(arg);
  if (action === "waitFor") return page.waitForSelector(arg);
  return page[action](arg);
}

export async function captureShot(browser, o, shot, axe) {
  const context = await browser.newContext({
    viewport: shot.viewport,
    deviceScaleFactor: 1,
    ...(o.storageState ? { storageState: o.storageState } : {}),
  });
  context.setDefaultTimeout(STEP_TIMEOUT_MS);
  try {
    const page = await context.newPage();
    // A dev server may compile the route on its first request, so loading gets longer than a step.
    const response = await page.goto(shot.url, { waitUntil: "load", timeout: LOAD_TIMEOUT_MS });
    if (response && response.status() >= 400) throw new Error(`HTTP ${response.status()} for ${shot.url}`);
    await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
    // The preview harness serves its errors (no such preview or state) with a 200, marked with this attribute.
    const previewError = await page.$("[data-pixie-preview-error]");
    if (previewError) throw new Error(`preview error: ${await previewError.textContent()}`);
    for (const step of shot.steps) await runStep(page, step);
    const height = Math.min(await page.evaluate(() => document.documentElement.scrollHeight), MAX_HEIGHT);
    await page.screenshot({ path: join(o.out, shot.file), fullPage: true, clip: { x: 0, y: 0, width: shot.viewport.width, height } });
    // Evaluated through the browser's debugging protocol, which the page's CSP doesn't apply to. A script tag
    // would be blocked by a strict CSP, and turning CSP off would change what the screenshots show.
    await page.evaluate(axe);
    const result = await page.evaluate(() => window.axe.run(document, { resultTypes: ["violations"] }));
    return result.violations.map((v) => ({
      id: v.id, impact: v.impact, help: v.help, helpUrl: v.helpUrl, nodes: v.nodes.map((n) => ({ target: n.target })),
    }));
  } finally {
    await context.close();
  }
}

async function main() {
  let o;
  try {
    o = parseOptions(process.argv.slice(2));
  } catch (e) {
    console.error(e.message);
    process.exit(1);
  }
  const tools = loadTools();
  if (!tools) {
    console.error(`Playwright or axe-core is missing from ${CACHE}. /pixie:design-setup offers to install them.`);
    process.exit(3);
  }
  mkdirSync(join(o.out, "shots"), { recursive: true });
  let browser;
  try {
    browser = await tools.chromium.launch();
  } catch (e) {
    // Only a missing browser is "cache not ready" (3). Anything else, such as missing system libraries, isn't
    // fixed by reinstalling.
    console.error(`Chromium won't start from ${CACHE}/browsers: ${e.message.split("\n")[0]}`);
    process.exit(/Executable doesn't exist/.test(e.message) ? 3 : 1);
  }
  const manifest = { url: o.url, capturedAt: new Date().toISOString(), shots: [], errors: [] };
  const axe = [];
  try {
    for (const shot of o.shots) {
      const entry = { file: shot.file, state: shot.state, viewport: shot.viewport.width, url: shot.url };
      try {
        const violations = await captureShot(browser, o, shot, tools.axe);
        manifest.shots.push(entry);
        axe.push({ ...entry, violations });
      } catch (e) {
        manifest.errors.push({ ...entry, error: e.message.split("\n")[0] });
      }
    }
  } finally {
    await browser.close();
  }
  writeFileSync(join(o.out, "manifest.json"), JSON.stringify(manifest, null, 2));
  writeFileSync(join(o.out, "axe.json"), JSON.stringify(axe, null, 2));
  console.log(`captured ${manifest.shots.length} of ${o.shots.length} shots, ${manifest.errors.length} errors -> ${o.out}`);
  if (manifest.shots.length === 0) process.exit(1);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) await main();
