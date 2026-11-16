#!/usr/bin/env node
// Capture one route for /design-critique: a PNG per state and viewport, an axe report and a manifest.
// Playwright and axe-core load from Pixie's own cache, never from the target repo.
//
//   node capture.mjs --url URL --out DIR [--viewports 390,1280] [--states JSON|FILE] [--storage-state FILE]
//
// Exit codes: 0 captured (per-state errors are in the manifest), 1 bad options or the page failed to load,
// 3 Playwright or axe-core missing from the cache.
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { homedir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const MAX_WIDTH = 1280;
const MAX_HEIGHT = 4000;
const ACTIONS = ["click", "fill", "press", "hover", "waitFor"];
export const CACHE = process.env.PIXIE_PLAYWRIGHT_DIR || join(homedir(), ".cache", "pixie", "playwright");

const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

// States come inline as JSON or from a file: [{ "name": "menu open", "steps": [{ "click": "SELECTOR" }] }].
function parseStates(value) {
  const states = JSON.parse(value.trim().startsWith("[") ? value : readFileSync(value, "utf8"));
  for (const s of states) {
    const unknown = (s.steps ?? []).map((step) => Object.keys(step)[0]).find((a) => !ACTIONS.includes(a));
    if (unknown) throw new Error(`state "${s.name}": unknown step ${unknown}; use ${ACTIONS.join(", ")}`);
  }
  return states;
}

export function parseOptions(argv) {
  const o = { viewports: "390,1280", states: '[{"name":"default","steps":[]}]' };
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i].replace(/^--/, "").replace(/-(.)/g, (_, c) => c.toUpperCase());
    o[key] = argv[i + 1];
  }
  if (!o.url) throw new Error("--url is required");
  if (!o.out) throw new Error("--out is required");
  const widths = o.viewports.split(",").map(Number);
  for (const w of widths) {
    if (!(w > 0 && w <= MAX_WIDTH)) throw new Error(`viewport ${w} must be between 1 and ${MAX_WIDTH} wide`);
  }
  o.shots = parseStates(o.states).flatMap((s) =>
    widths.map((width) => ({
      file: `shots/${slug(s.name)}-${width}.png`,
      state: s.name,
      steps: s.steps ?? [],
      viewport: { width, height: width <= 480 ? 844 : 800 },
    })),
  );
  return o;
}

function loadTools() {
  process.env.PLAYWRIGHT_BROWSERS_PATH = join(CACHE, "browsers");
  const require = createRequire(join(CACHE, "noop.js"));
  try {
    return { chromium: require("playwright").chromium, axePath: require.resolve("axe-core/axe.min.js") };
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

async function captureShot(browser, o, shot, axePath) {
  const context = await browser.newContext({
    viewport: shot.viewport,
    deviceScaleFactor: 1,
    ...(o.storageState ? { storageState: o.storageState } : {}),
  });
  try {
    const page = await context.newPage();
    const response = await page.goto(o.url, { waitUntil: "load" });
    if (response && response.status() >= 400) throw new Error(`HTTP ${response.status()} for ${o.url}`);
    await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
    for (const step of shot.steps) await runStep(page, step);
    const height = Math.min(await page.evaluate(() => document.documentElement.scrollHeight), MAX_HEIGHT);
    await page.screenshot({ path: join(o.out, shot.file), fullPage: true, clip: { x: 0, y: 0, width: shot.viewport.width, height } });
    await page.addScriptTag({ path: axePath });
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
    console.error(`Playwright or axe-core is missing from ${CACHE}. See the skill's Prerequisites to install them.`);
    process.exit(3);
  }
  mkdirSync(join(o.out, "shots"), { recursive: true });
  const browser = await tools.chromium.launch();
  const manifest = { url: o.url, capturedAt: new Date().toISOString(), shots: [], errors: [] };
  const axe = [];
  try {
    for (const shot of o.shots) {
      const entry = { file: shot.file, state: shot.state, viewport: shot.viewport.width };
      try {
        const violations = await captureShot(browser, o, shot, tools.axePath);
        manifest.shots.push(entry);
        axe.push({ screenshot: shot.file, state: shot.state, viewport: shot.viewport.width, violations });
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
