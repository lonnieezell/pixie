import assert from "node:assert/strict";
import { test } from "node:test";

import { parseOptions } from "../capture.mjs";

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

test("rejects bad options", () => {
  const cases = [
    [["--out", "/tmp/run"], /--url/],
    [["--url", "http://x/"], /--out/],
    [["--url", "http://x/", "--out", "/tmp/run", "--viewports", "1440"], /1280/],
    [["--url", "http://x/", "--out", "/tmp/run", "--states", '[{"name":"a","steps":[{"drag":"x"}]}]'], /drag/],
    [["--url", "http://x/", "--out", "/tmp/run", "--states", '[{"name":"Menu open"},{"name":"menu-open"}]'], /same file/],
    [["--url", "http://x/", "--out", "/tmp/run", "--states", '[{"name":"!!!"}]'], /name/],
    [["--url", "http://x/", "--out", "/tmp/run", "--states", '[{"steps":[]}]'], /name/],
  ];
  for (const [argv, message] of cases) {
    assert.throws(() => parseOptions(argv), message);
  }
});
