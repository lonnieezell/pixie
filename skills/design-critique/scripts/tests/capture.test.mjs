import assert from "node:assert/strict";
import { test } from "node:test";

import { captureShot, parseOptions } from "../capture.mjs";

test("defaults to a default state at 390 and 1280 wide", () => {
  const o = parseOptions(["--url", "http://localhost:8080/orders", "--out", "/tmp/run"]);
  assert.deepEqual(
    o.shots.map((s) => [s.file, s.state, s.viewport.width]),
    [
      ["shots/default-390.png", "default", 390],
      ["shots/default-1280.png", "default", 1280],
    ],
  );
});

test("plans one shot per state and viewport, with safe file names", () => {
  const states = JSON.stringify([
    { name: "default", steps: [] },
    { name: "Menu open", steps: [{ click: "button[aria-label=Menu]" }] },
  ]);
  const o = parseOptions(["--url", "http://x/", "--out", "/tmp/run", "--viewports", "768", "--states", states]);
  assert.deepEqual(
    o.shots.map((s) => [s.file, s.state, s.steps.length]),
    [
      ["shots/default-768.png", "default", 0],
      ["shots/menu-open-768.png", "Menu open", 1],
    ],
  );
});

const MATRIX = {
  states: Object.fromEntries(
    ["empty", "single", "typical", "overflow", "error", "loading"].map((s) => [s, `/__preview/order-list?state=${s}`]),
  ),
  interactions: [{ name: "menu open", from: "typical", steps: [{ click: "button[aria-label=Menu]" }] }],
};
// A preview may declare states beyond the six, and an interaction may name the widths it exists at.
const FULL_MATRIX = {
  states: { ...MATRIX.states, disabled: "/__preview/order-list?state=disabled" },
  interactions: [
    ...MATRIX.interactions,
    { name: "nav open", from: "typical", viewports: [390], steps: [{ click: "button[aria-label='Open menu']" }] },
  ],
};
const matrixArgs = (m, base = "http://x/") => ["--url", base, "--out", "/tmp/run", "--matrix", JSON.stringify(m)];

test("plans every matrix state at desktop, plus typical and overflow at mobile, each at its own URL", () => {
  const o = parseOptions(matrixArgs(FULL_MATRIX, "http://localhost:5173"));
  assert.deepEqual(
    o.shots.map((s) => [s.file, s.url, s.steps.length]),
    [
      ["shots/empty-1280.png", "http://localhost:5173/__preview/order-list?state=empty", 0],
      ["shots/single-1280.png", "http://localhost:5173/__preview/order-list?state=single", 0],
      ["shots/typical-390.png", "http://localhost:5173/__preview/order-list?state=typical", 0],
      ["shots/typical-1280.png", "http://localhost:5173/__preview/order-list?state=typical", 0],
      ["shots/overflow-390.png", "http://localhost:5173/__preview/order-list?state=overflow", 0],
      ["shots/overflow-1280.png", "http://localhost:5173/__preview/order-list?state=overflow", 0],
      ["shots/error-1280.png", "http://localhost:5173/__preview/order-list?state=error", 0],
      ["shots/loading-1280.png", "http://localhost:5173/__preview/order-list?state=loading", 0],
      ["shots/disabled-1280.png", "http://localhost:5173/__preview/order-list?state=disabled", 0],
      ["shots/menu-open-1280.png", "http://localhost:5173/__preview/order-list?state=typical", 1],
      ["shots/nav-open-390.png", "http://localhost:5173/__preview/order-list?state=typical", 1],
    ],
  );
});

// Stands in for Playwright's browser and records what the page was asked to do. The page's evaluate calls
// answer in order: the page height, loading axe, then axe's result.
function fakeBrowser(calls, previewError = null) {
  const answers = [900, undefined, { violations: [] }];
  const page = {
    $: async () => previewError && { textContent: async () => previewError },
    goto: async (url) => (calls.push(["goto", url]), { status: () => 200 }),
    waitForLoadState: async () => {},
    click: async (selector) => calls.push(["click", selector]),
    screenshot: async ({ path }) => calls.push(["screenshot", path]),
    evaluate: async () => answers.shift(),
  };
  return { newContext: async () => ({ setDefaultTimeout() {}, newPage: async () => page, close: async () => {} }) };
}

test("replays an interaction's steps on its base state's page before the screenshot", async () => {
  const o = parseOptions(matrixArgs(MATRIX, "http://localhost:5173"));
  const calls = [];
  await captureShot(fakeBrowser(calls), o, o.shots.find((s) => s.state === "menu open"), "");
  assert.deepEqual(calls, [
    ["goto", "http://localhost:5173/__preview/order-list?state=typical"],
    ["click", "button[aria-label=Menu]"],
    ["screenshot", "/tmp/run/shots/menu-open-1280.png"],
  ]);
});

test("fails a shot whose page is a preview error, served with a 200, instead of capturing it", async () => {
  const o = parseOptions(matrixArgs(MATRIX));
  const calls = [];
  await assert.rejects(
    captureShot(fakeBrowser(calls, "No preview named order-list"), o, o.shots[0], ""),
    /No preview named order-list/,
  );
  assert.ok(!calls.some(([call]) => call === "screenshot"));
});

test("rejects bad options", () => {
  const cases = [
    [["--out", "/tmp/run"], /--url/],
    [["--url", "http://x/"], /--out/],
    [["--url", "http://x/", "--out", "/tmp/run", "--viewports", "1440"], /1280/],
    [["--url", "http://x/", "--out", "/tmp/run", "--states", '[{"name":"a","steps":[{"drag":"x"}]}]'], /drag/],
    [["--url", "http://x/", "--out", "/tmp/run", "--states", '[{"name":"Menu open"},{"name":"menu-open"}]'], /same file/],
    [["--url", "http://x/", "--out", "/tmp/run", "--states", '[{"name":"!!!"}]'], /name/],
    [["--url", "http://x/", "--out", "/tmp/run", "--states", '[{"steps":[]}]'], /name/],
    [["--url", "http://x/", "--out", "/tmp/run", "--states", '[{"name":1}]'], /name/],
    [["--url", "http://x/", "--out", "/tmp/run", "--viewports", "390,390"], /same file/],
    [["--url", "http://x/", "--out", "/tmp/run", "--viewports", "390.5"], /whole number/],
    [matrixArgs({ ...MATRIX, states: { ...MATRIX.states, error: undefined, loading: "" } }), /missing.*error, loading/],
    [matrixArgs({ ...MATRIX, interactions: [{ name: "menu open", from: "busy", steps: [] }] }), /busy/],
    [matrixArgs({ ...MATRIX, interactions: [{ name: "typical", from: "typical", steps: [] }] }), /same file/],
    [matrixArgs({ ...MATRIX, interactions: [{ name: "a", from: "typical", viewports: [768], steps: [] }] }), /768/],
    [[...matrixArgs(MATRIX), "--states", '[{"name":"default"}]'], /--states/],
  ];
  for (const [argv, message] of cases) {
    assert.throws(() => parseOptions(argv), message);
  }
});
