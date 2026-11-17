# How to design a feature

This guide shows you how to have Claude explore a few real design directions for one piece of UI, see each one rendered in your app, and pick one with screenshots and critiques in front of you. It works on React, Laravel Blade and CodeIgniter 4 apps. You use two skills:

- `design-setup` catalogues your design system: tokens, components and which ones are current. You run it once per repo, and again when it's stale.
- `design` explores the directions and records your pick.

Both only run when you type them.

## 1. Catalogue the design system (once)

```text
/pixie:design-setup
```

Claude scans the repo and writes `docs/agents/design-system.md`. Say yes to the **preview harness** offer: the winning direction's preview is kept there. Say yes to **Playwright** too: that's how screenshots are taken and accessibility is checked. Commit the inventory.

If you skip this step, `design` runs a quick version of it first.

## 2. Ask for directions

Name one component, section or page, and what it's for if that isn't obvious:

```text
/pixie:design the order list on the dashboard
```

Add `with a wildcard` to get one extra direction that deliberately breaks a house convention.

Claude asks what the code can't tell it (who uses the screen, for what), then prints a **brief**: the axes that matter for this screen, such as `Density: compact ↔ roomy`, and 2 directions for a component or 3 for a page, each placed on those axes. Each direction lists the catalogued components it's built from and a one-sentence trade-off.

Nothing is built yet. Change anything you like: an axis, a direction, a component it uses. Approve when the directions are the real alternatives you want to see.

## 3. Let it build, gate and critique

Claude builds each direction as a preview with every state (empty, single, typical, overflow, error, loading), captures them, and runs the gates. A direction with an accessibility violation, a raw colour value, or a new component that duplicates one you have, is fixed before it goes further.

Then a code-blind critic reviews each direction's screenshots, all at once. Claude fixes the serious findings within each direction, for 2 rounds at most.

If the app needs to be running and there's no verification skill, Claude asks for the launch command. Run `/pixie:create-verifier` once to skip that next time.

## 4. Pick or blend

Claude shows each direction's trade-off, gate results, remaining findings and the paths of its screenshots. Open them, then:

- **Pick one.**
- **Blend:** say what to take from which ("the table from dense-table, with card-stack's summary"). Claude builds the blend as one more direction and shows it to you.
- **None:** Claude goes back to the brief with what you said.

## 5. Commit the record

After the pick, Claude deletes the losing directions' code and writes `docs/design/decisions/YYYY-MM-DD-SLUG.md`: the axes, every direction with its trade-off, screenshots, and why the winner won. The first time, it asks whether to keep the screenshots out of git.

Commit the record, the screenshots (unless gitignored), and the winner's preview. The preview and the record are the spec for building the winner into production code, which is the next step.
