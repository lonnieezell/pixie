# Preview harness (React)

A preview renders one component in every state of its **state matrix**, with fixture data, at a URL the capture script can load. `/design-critique` captures the whole matrix from it instead of only the states a live route happens to show.

`/pixie:design-setup` offers the harness once (step 7). The answer decides where previews live:

| Repo | Answer | Previews live in | Preview surface |
|---|---|---|---|
| Has Storybook | yes | Stories, kept and committed. No route is added. | `storybook (.storybook)` |
| No Storybook | yes | A dev-only `/__preview/<slug>?state=<name>` route, kept and committed | `harness (/__preview)` |
| Either | no | The same structure, created for one critique run and removed afterwards | `temporary` |

React only. Blade and CodeIgniter screens are critiqued as live routes.

## The state matrix

Every preview declares all six of these. A preview that lacks any of them is rejected: `capture.mjs --matrix` refuses it, and the route shows an error instead of rendering.

| State | Shows |
|---|---|
| `empty` | No data: the empty state the user sees first |
| `single` | Exactly one item |
| `typical` | A realistic amount of realistic data |
| `overflow` | Too much: many items, long names, long unbroken words, large numbers |
| `error` | The failure the component shows when its data can't load or save |
| `loading` | The pending state, before data arrives |

If the component has no way to show a state (no error prop, no loading prop), render it the way its parent would in that situation, and say so in a comment in the preview. Never leave a state out.

**Interaction states** are optional. Each one starts from a required state's page and replays action steps before the screenshot, in the step format `/design-critique` uses (`click`, `fill`, `press`, `hover`, `waitFor`). For example, an open menu: `{"name": "menu open", "from": "typical", "steps": [{"click": "button[aria-label='Row actions']"}]}`. Use stable selectors: ARIA labels, `data-*` attributes, visible text.

## Fixtures

- Use the app's own JS factories when it has them (`test/factories`, `fishery`, `@faker-js/faker` builders, MSW handlers). Seed any randomness, so screenshots compare across runs.
- Otherwise write the fixtures by hand, next to the preview.
- Shapes match what production passes: the component's prop types, or the API resource the page fetches (a Laravel `JsonResource`, an OpenAPI schema, the TypeScript type of the fetch result). Read the type; don't guess field names.
- **Never real data.** Don't query a database, call a live API or copy rows from one. Made-up names and values only.

## Storybook

Write one stories file per component, where the repo keeps its stories, with one named story per required state. Put interaction states on the default export:

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { OrderList } from "./OrderList";
import { makeOrders } from "@/test/factories";

const meta = {
  title: "Orders/OrderList",
  component: OrderList,
  parameters: {
    pixie: { interactions: [{ name: "menu open", from: "typical", steps: [{ click: "button[aria-label='Row actions']" }] }] },
  },
} satisfies Meta<typeof OrderList>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Empty: Story = { args: { orders: [] } };
export const Single: Story = { args: { orders: makeOrders(1) } };
export const Typical: Story = { args: { orders: makeOrders(8) } };
export const Overflow: Story = { args: { orders: makeOrders(60, { customer: "Maximiliana Featherstonehaugh-Wolfeschlegel" }) } };
export const Error: Story = { args: { orders: [], error: "We couldn't load your orders." } };
export const Loading: Story = { args: { orders: [], loading: true } };
```

The URL of a story is `/iframe.html?id=STORY_ID&viewMode=story`. Read the ids from the running Storybook's `/index.json`, rather than working them out from the title. Storybook is launched with the repo's own script (usually `npm run storybook`, at `http://localhost:6006`).

## The `/__preview` route

Three pieces, under `src/__preview/` (or `resources/js/__preview/` for Inertia):

**`previews/<slug>.preview.tsx`**, one per component:

```tsx
import { OrderList } from "@/components/OrderList";
import { makeOrders } from "@/test/factories";

// Built once, so a re-render shows the same data.
const one = makeOrders(1);
const eight = makeOrders(8);
const many = makeOrders(60, { customer: "Maximiliana Featherstonehaugh-Wolfeschlegel" });

export const states = {
  empty: () => <OrderList orders={[]} />,
  single: () => <OrderList orders={one} />,
  typical: () => <OrderList orders={eight} />,
  overflow: () => <OrderList orders={many} />,
  error: () => <OrderList orders={[]} error="We couldn't load your orders." />,
  loading: () => <OrderList orders={[]} loading />,
};

export const interactions = [
  { name: "menu open", from: "typical", steps: [{ click: "button[aria-label='Row actions']" }] },
];
```

**`registry.ts`**, one line per preview, so a preview is loaded only when asked for:

```ts
export const previews: Record<string, () => Promise<{ states: Record<string, () => JSX.Element> }>> = {
  "order-list": () => import("./previews/order-list.preview"),
};
```

**`PreviewPage.tsx`**, which renders one state and refuses an incomplete preview:

```tsx
import { useEffect, useState } from "react";
import { previews } from "./registry";

const REQUIRED = ["empty", "single", "typical", "overflow", "error", "loading"];

export default function PreviewPage({ slug, state }: { slug: string; state: string }) {
  const [mod, setMod] = useState<Awaited<ReturnType<(typeof previews)[string]>> | null>(null);
  useEffect(() => { previews[slug]?.().then(setMod); }, [slug]);
  if (!previews[slug]) return <p role="alert">No preview named {slug}</p>;
  if (!mod) return null;
  const missing = REQUIRED.filter((s) => !mod.states[s]);
  if (missing.length) return <p role="alert">Preview {slug} is missing required states: {missing.join(", ")}</p>;
  const Render = mod.states[state];
  return Render ? <Render /> : <p role="alert">Preview {slug} has no state {state}</p>;
}
```

Wrap the page in the same providers the app's root uses (theme, router, query client, i18n), so a component renders as it does in the app. Then mount it so production never serves it:

| Setup | Mount | Production |
|---|---|---|
| Vite (React, Tauri) | In the entry file, before the normal render: `if (import.meta.env.DEV && location.pathname.startsWith("/__preview/")) { import("./__preview/PreviewPage").then(...render it...) } else { ...the existing render... }` | Vite replaces `import.meta.env.DEV` with `false` and drops the branch, so no preview code is built |
| Next (App Router) | `app/%5F%5Fpreview/[slug]/page.tsx` (a folder named `__preview` would be private and never routed). It calls `notFound()` first when `process.env.NODE_ENV === "production"`, then renders `PreviewPage` from a client component | Every preview URL returns 404 |
| Next (Pages Router) | `pages/__preview/[slug].tsx`, whose `getServerSideProps` returns `{ notFound: true }` in production | Every preview URL returns 404 |
| Inertia (Laravel) | A route in `routes/web.php` inside `if (app()->environment('local')) { ... }` that renders an Inertia page wrapping `PreviewPage` with the slug and `state` query | The route isn't registered outside `local`, so it returns 404 |

Each mount passes `slug` from the path and `state` from the `state` query.

**Prove the exclusion** after installing, before recording the answer:
- Vite: run the repo's production build, then `grep -rl "__preview" dist` (or the build's output folder) must find nothing.
- Next: `next build && next start`, then a preview URL must return 404.
- Inertia: `APP_ENV=production php artisan route:list --path=__preview` must list no routes.

If the check fails, fix the mount and check again. Don't record `yes` until it passes.

## The matrix file

`/design-critique` captures a preview by writing `RUN/matrix.json` from it and passing it to `capture.mjs --matrix`:

```json
{
  "states": {
    "empty": "/__preview/order-list?state=empty",
    "single": "/__preview/order-list?state=single",
    "typical": "/__preview/order-list?state=typical",
    "overflow": "/__preview/order-list?state=overflow",
    "error": "/__preview/order-list?state=error",
    "loading": "/__preview/order-list?state=loading"
  },
  "interactions": [{"name": "menu open", "from": "typical", "steps": [{"click": "button[aria-label='Row actions']"}]}]
}
```

Paths resolve against `--url`, the dev server's (or Storybook's) origin. For Storybook, each path is the story's `/iframe.html?id=…&viewMode=story`. Every state is captured at the widest viewport (1280), and `typical` and `overflow` at mobile width (390) too. Interaction states are captured at 1280.

## Temporary mode

When the answer is `no`, `/design-critique` builds the same structure for one run and removes it afterwards:

1. Before creating anything, save `git status --porcelain --untracked-files=all` to `RUN/status-before.txt`. Any existing file the harness must edit (the Vite entry file, `routes/web.php`) must be clean. If one isn't, stop and ask the user to commit it first.
2. Create the files, and write each path to `RUN/temp-harness.txt`, marked `created` or `edited`.
3. In cleanup, delete every `created` file and any folder the run made, and `git restore` every `edited` one.
4. Run the same `git status` again. Its output must match `RUN/status-before.txt`. If it doesn't, say which files differ and fix them before ending the run.
