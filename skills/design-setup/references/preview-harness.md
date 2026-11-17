# Preview harness (React, Laravel Blade and CodeIgniter 4)

A preview renders one component (or, in Blade, a partial; in CodeIgniter, a view cell or partial) in every state of its **state matrix**, with fixture data, at a URL the capture script can load. `/design-critique` captures the whole matrix from it instead of only the states a live route happens to show.

`/pixie:design-setup` offers the harness once (step 7). The answer decides where previews live:

| Repo | Answer | Previews live in | Preview surface |
|---|---|---|---|
| Has Storybook | yes | Stories, kept and committed. No route is added. | `storybook (.storybook)` |
| No Storybook | yes | A dev-only `/__preview/<slug>?state=<name>` route, kept and committed | `harness (/__preview)` |
| Has Storybook | no | A stories file, created for one critique run and removed afterwards. Storybook is launched with the repo's `storybook` script. | `temporary` |
| No Storybook | no | The `/__preview` route, created for one critique run and removed afterwards | `temporary` |

A Laravel Blade or CodeIgniter 4 repo has no Storybook row: its previews always use the `/__preview` route, written in PHP (see [Laravel Blade](#laravel-blade) and [CodeIgniter 4](#codeigniter-4)). An Inertia-React app uses the React harness.

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

If the component has no way to show a state (no error prop, no loading prop), render it the way its parent would in that situation, and say so in a comment in the preview. Never leave a state out. A preview may add more states (`disabled`, `read-only`). They're captured too.

**The markers.** Every harness marks its page for `capture.mjs`, which waits for one of two markers before going on: `data-pixie-preview` wraps a rendered state, and `data-pixie-preview-error` marks an error (no such preview or state, missing required states, a failed render). Errors are served with a 200, so the capture fails the shot when it sees that marker, instead of capturing an error message as a state.

**Interaction states** are optional. Each one starts from a state's page and replays action steps before the screenshot, in the step format `/design-critique` uses (`click`, `fill`, `press`, `hover`, `waitFor`). For example, an open menu: `{"name": "menu open", "from": "typical", "steps": [{"click": "button[aria-label='Row actions']"}]}`. Use stable selectors: ARIA labels, `data-*` attributes, visible text. An interaction is captured at desktop width. One that only exists at another width, such as a mobile nav, names it: `"viewports": [390]`.

## Fixtures

- Use the app's own factories when it has them: JS builders in React (`test/factories`, `fishery`, `@faker-js/faker` builders, MSW handlers), model factories (`database/factories`) in Blade, and a model's `fake()` method through `Fabricator` in CodeIgniter, always with `make()`, which builds models in memory, never `create()`, which saves them. Seed any randomness, so screenshots compare across runs.
- Without factories, write the fixtures by hand, next to the preview. A seeder's made-up rows can be copied into the preview, but never run a seeder: it writes to the database.
- Shapes match what production passes: the component's prop types, a Blade component's `@props` or class constructor, a CodeIgniter view cell's public properties, the variables a partial uses, or the API resource the page fetches (a Laravel `JsonResource`, an OpenAPI schema, the TypeScript type of the fetch result). Read the type; don't guess field names.
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
// Not `Error`, which would shadow the global Error constructor in this file.
export const ErrorState: Story = { name: "Error", args: { orders: [], error: "We couldn't load your orders." } };
export const Loading: Story = { args: { orders: [], loading: true } };
```

The URL of a story is `/iframe.html?id=STORY_ID&viewMode=story`. Read the ids from the running Storybook's `/index.json`, rather than working them out from the title or export name. A wrong id still loads with a 200, showing Storybook's "Couldn't find story" error, so check every id is in the index before capturing. Storybook is launched with the repo's own script (usually `npm run storybook`, at `http://localhost:6006`).

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
import type { ReactElement } from "react";

export const previews: Record<string, () => Promise<{ states: Record<string, () => ReactElement> }>> = {
  "order-list": () => import("./previews/order-list.preview"),
};
```

**`PreviewPage.tsx`**, which renders one state and refuses an incomplete preview, with the two markers.

```tsx
import { type ReactNode, useEffect, useState } from "react";
import { previews } from "./registry";

const REQUIRED = ["empty", "single", "typical", "overflow", "error", "loading"];

const Problem = ({ children }: { children: ReactNode }) => (
  <p role="alert" data-pixie-preview-error="">{children}</p>
);

export default function PreviewPage({ slug, state }: { slug: string; state: string }) {
  const load = Object.hasOwn(previews, slug) ? previews[slug] : undefined;
  const [mod, setMod] = useState<Awaited<ReturnType<NonNullable<typeof load>>> | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  useEffect(() => { load?.().then(setMod, (e) => setFailed(String(e))); }, [load]);
  if (!load) return <Problem>No preview named {slug}</Problem>;
  if (failed) return <Problem>Preview {slug} failed to load: {failed}</Problem>;
  if (!mod) return null;
  const missing = REQUIRED.filter((s) => !mod.states[s]);
  if (missing.length) return <Problem>Preview {slug} is missing required states: {missing.join(", ")}</Problem>;
  const Render = Object.hasOwn(mod.states, state) ? mod.states[state] : undefined;
  if (!Render) return <Problem>Preview {slug} has no state {state}</Problem>;
  return <div data-pixie-preview=""><Render /></div>;
}
```

Wrap the page in the same providers the app's root uses (theme, router, query client, i18n), so a component renders as it does in the app. Then mount it so production never serves it:

| Setup | Mount | Production |
|---|---|---|
| Vite (React, Tauri) | In the entry file, before the normal render: `if (import.meta.env.DEV && location.pathname.startsWith("/__preview/")) { import("./__preview/PreviewPage").then(...render it...) } else { ...the existing render... }` | Vite replaces `import.meta.env.DEV` with `false` and drops the branch, so no preview code is built |
| Next (App Router) | `app/%5F%5Fpreview/[slug]/page.tsx` (a folder named `__preview` would be private and never routed). It calls `notFound()` first when `process.env.NODE_ENV === "production"`, then renders `PreviewPage` from a client component | Every preview URL returns 404. Next still compiles the preview code, but never serves it. |
| Next (Pages Router) | `pages/__preview/[slug].tsx`, whose `getServerSideProps` returns `{ notFound: true }` in production | Every preview URL returns 404. The code is compiled but never served. |
| Inertia (Laravel) | A route in `routes/web.php` inside `if (app()->environment('local')) { ... }` that renders the Inertia page `__preview` with the slug and `state` query. Keep that page out of `Pages/`, where the production glob would bundle it: put it at `__preview/InertiaPreview.tsx` and resolve it in the entry file's `resolve` with `import.meta.env.DEV && name === "__preview" ? import("./__preview/InertiaPreview") : resolvePageComponent(...)` | The route isn't registered outside `local`, so it returns 404, and Vite drops the `DEV` branch, so no preview code is built |

Each mount passes `slug` from the path and `state` from the `state` query.

**Prove the exclusion** after installing, before recording the answer:
- Vite: run the repo's production build, then `grep -rl "__preview" dist` (or the build's output folder) must find nothing.
- Next: `next build && next start`, then a preview URL must return 404.
- Inertia: `APP_ENV=production php artisan route:list --path=__preview` must list no routes, and after the production `vite build`, `grep -rl "__preview" public/build` must find nothing.

If the check fails, fix the mount and check again. Don't record `yes` until it passes.

## Laravel Blade

The same contract, served by Laravel: `/__preview/<slug>?state=<name>`, the six required states, [the markers](#the-state-matrix) and the same matrix file. A preview renders a Blade component (`<x-order-list>`) or a partial (`@include('orders._row')`) inside the app's own layout, so the page gets the app's real CSS and JS through `@vite` or `mix()`, whether that's Bootstrap or Tailwind. Those assets must be served too: run the repo's dev script (`composer run dev` in Laravel 11 and later, which starts the app and Vite together, or `npm run dev` alongside the app), or build them first. With neither, every state shows "Vite manifest not found".

Four pieces:

**`resources/previews/<slug>.php`**, one per component or partial. It returns the states as closures that render HTML, plus any interaction states:

```php
<?php

use App\Models\Order;
use Illuminate\Support\Facades\Blade;

$list = fn ($orders, array $extra = []) => Blade::render(
    '<x-order-list :orders="$orders" :error="$error" :loading="$loading" />',
    ['orders' => $orders, 'error' => null, 'loading' => false, ...$extra],
);

// Each request renders one state, so each state builds only its own data.
return [
    'states' => [
        'empty' => fn () => $list(collect()),
        'single' => fn () => $list(Order::factory()->count(1)->make()),
        'typical' => fn () => $list(Order::factory()->count(8)->make()),
        'overflow' => fn () => $list(Order::factory()->count(60)->make(['customer' => 'Maximiliana Featherstonehaugh-Wolfeschlegel'])),
        'error' => fn () => $list(collect(), ['error' => "We couldn't load your orders."]),
        'loading' => fn () => $list(collect(), ['loading' => true]),
    ],
    'interactions' => [
        ['name' => 'menu open', 'from' => 'typical', 'steps' => [['click' => "button[aria-label='Row actions']"]]],
    ],
];
```

A partial renders with `view('orders._row', ['order' => Order::factory()->make()])->render()`.

**`resources/views/__preview.blade.php`**, which puts the state inside the app's real layout. Use the layout the component's screens use, from the inventory's layout shells:

```blade
{{-- Pixie's preview harness: one state of a preview, inside the app's real layout. --}}
@extends('layouts.app')

@section('content')
    <div data-pixie-preview>{!! $render() !!}</div>
@endsection
```

For a component layout, wrap it instead: `<x-app-layout><div data-pixie-preview>{!! $render() !!}</div></x-app-layout>`.

**`routes/preview.php`**, which renders one state and refuses an incomplete preview:

```php
<?php

// Pixie's preview harness: renders one component or partial in one state of its matrix, for /design-critique.
// routes/web.php loads this file only in the local environment.

use App\Models\User;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Route;
use Illuminate\View\ViewException;

Route::get('/__preview/{slug}', function (string $slug) {
    $required = ['empty', 'single', 'typical', 'overflow', 'error', 'loading'];
    $state = request()->query('state', 'typical');
    $file = resource_path("previews/{$slug}.php");
    // Served bare, without the layout, so a broken layout can't hide it.
    $problem = fn (string $message) => response('<p role="alert" data-pixie-preview-error>'.e($message).'</p>');

    // Previews never read or write a database: any query on any connection while rendering fails and is
    // shown as a problem. Connections open lazily, so this opens none.
    $rendering = true;
    foreach (array_keys(config('database.connections')) as $name) {
        DB::connection($name)->beforeExecuting(function (string $query) use (&$rendering) {
            if ($rendering) {
                throw new RuntimeException("previews never query the database, but this ran: {$query}");
            }
        });
    }
    try {
        // Seeded, so factory data is the same on every load and screenshots compare across runs.
        fake()->seed(1);
        // A made-up user, never saved, for a layout that shows who's signed in.
        auth()->setUser(User::factory()->make(['name' => 'Preview User']));

        if (! is_file($file)) {
            return $problem("No preview named {$slug}");
        }
        // Required in its own scope, so the preview's variables can't overwrite the harness's.
        $states = (static fn () => require $file)()['states'];
        $missing = array_diff($required, array_keys($states));
        if ($missing) {
            return $problem("Preview {$slug} is missing required states: ".implode(', ', $missing));
        }
        if (! array_key_exists($state, $states)) {
            return $problem("Preview {$slug} has no state {$state}");
        }

        // Rendered here, inside the guard, so the layout can't query the database either. The view calls the
        // state while the layout renders, so the component's @push and @once reach the layout's @stack.
        return response(view('__preview', ['render' => $states[$state]])->render());
    } catch (Throwable $e) {
        // Blade wraps an error once per view it passes through; show the original.
        while ($e instanceof ViewException && $e->getPrevious()) {
            $e = $e->getPrevious();
        }

        return $problem("Preview {$slug} failed to render: {$e->getMessage()}");
    } finally {
        // The session and anything after the response may use the database again.
        $rendering = false;
    }
})->where('slug', '[a-z0-9-]+');
```

Drop the `auth()->setUser(...)` line if the layout doesn't show a signed-in user, and use the app's user model if it isn't `App\Models\User`. If the layout needs more (a team, a locale), set it up here the same way, with made-up values.

**`routes/web.php`**, which loads the route only in `local`:

```php
// Pixie's preview harness, for /design-critique. Never registered outside local.
if (app()->environment('local')) {
    require __DIR__.'/preview.php';
}
```

Writing Blade previews:
- **A query in a preview** shows as the error. The usual cause is a factory whose definition has a parent factory (`'user_id' => User::factory()`): `make()` still saves that parent. Use `->withoutParents()` (Laravel 12 and later) or pass the key yourself (`make(['user_id' => null])`), then attach a made parent with `->setRelation('user', User::factory()->make())`.
- **A query in the layout** (a view composer loading the nav's categories, a `Cache::remember` with the `database` cache store) fails every state. Don't loosen the guard. Use a layout that doesn't query, if the app has one. Otherwise stop and tell the user which query runs, and ask how to give the layout made-up data in previews, for example by having that composer skip `__preview/*` requests.
- **`loading`.** A Blade page has no pending state of its own. Render the placeholder the page shows while it waits (a skeleton, a disabled "Saving…" button, an `aria-busy` region), or follow the matrix rule for a state the component can't show.
- **Form errors.** For a form whose `error` state is validation messages, share an error bag in that state's closure: `view()->share('errors', (new \Illuminate\Support\ViewErrorBag)->put('default', new \Illuminate\Support\MessageBag(['email' => ['That email is already taken.']])))`. The component's own `@error` and `$errors` see it. An error summary in the layout doesn't, because the layout's data is gathered before the state renders. Say so in the critique if the page has one.

**Prove the exclusion** after installing, before recording the answer. Don't record `yes` until both pass:
- `php artisan route:list --path=__preview` lists the route, and `APP_ENV=production php artisan route:list --path=__preview` says the app has no matching routes. A cached config (`bootstrap/cache/config.php`) pins the environment, and cached routes (`bootstrap/cache/routes-v7.php`) are listed whatever the environment, so run both checks without either. If one exists, ask before running `php artisan config:clear` and `php artisan route:clear`, and tell the user to rebuild them afterwards if they keep them on purpose.
- Start the app (with the verifier's Launch section, or the launch command from step 5; if there's neither, ask the user for one, and confirm the command before running it). Load `/__preview/none` from the app's own URL: it shows the harness's "No preview named none" message, which also proves the database guard and the made-up user work. A Laravel error means the user model or its factory needs adapting in `routes/preview.php`. See the 404 note below for a 404. Stop the app afterwards.

**A 404 from the route** has three usual causes: the app isn't running with `APP_ENV=local`, a route cache (`bootstrap/cache/routes-v7.php`) from before the install, or a URL on Vite's dev server instead of the app's.

## CodeIgniter 4

The same contract, served by CodeIgniter: `/__preview/<slug>?state=<name>`, the six required states, [the markers](#the-state-matrix) and the same matrix file. A preview renders a view cell (`view_cell('OrderListCell', [...])`) or a partial (`view('orders/_row', [...])`) inside the app's own layout, so the page gets the stylesheets and scripts that layout links. A view that extends a layout itself is a whole screen: critique it as a live route, or preview the cells and partials it's made of.

**The gate.** CodeIgniter's `ENVIRONMENT` comes from `CI_ENVIRONMENT` (in `.env` or the server's environment) and is `production` when that's unset. `$routes->environment('development', ...)` registers routes only when it matches, so the route doesn't exist in production, or in `testing`, the environment PHPUnit runs in. The harness is a closure route, not a controller in `app/Controllers`, so auto-routing can't reach it either.

Four pieces:

**`app/Previews/<slug>.php`**, one per view cell or partial. It returns the states as closures that render HTML, plus any interaction states:

```php
<?php

use App\Models\OrderModel;
use CodeIgniter\Test\Fabricator;

$orders = static fn (int $count, array $overrides = []) => (new Fabricator(OrderModel::class))
    ->setOverrides($overrides)
    ->make($count);
$list = static fn (array $orders, array $extra = []) => view_cell('OrderListCell', ['orders' => $orders, ...$extra]);

// Each request renders one state, so each state builds only its own data.
return [
    'states' => [
        'empty'    => static fn () => $list([]),
        'single'   => static fn () => $list($orders(1)),
        'typical'  => static fn () => $list($orders(8)),
        'overflow' => static fn () => $list($orders(60, ['customer' => 'Maximiliana Featherstonehaugh-Wolfeschlegel'])),
        'error'    => static fn () => $list([], ['error' => "We couldn't load your orders."]),
        'loading'  => static fn () => $list([], ['loading' => true]),
    ],
    'interactions' => [
        ['name' => 'menu open', 'from' => 'typical', 'steps' => [['click' => "button[aria-label='Row actions']"]]],
    ],
];
```

`Fabricator` builds rows from the model's `fake()` method, or guesses from its fields if it has none. It needs `fakerphp/faker`, which a development install has. A partial renders with `view('orders/_row', ['order' => $orders(1)[0]])`.

**`app/Views/__preview.php`**, which puts the state inside the app's real layout. Use the layout the component's screens extend, from the inventory's layout shells:

```php
<?php // Pixie's preview harness: one state of a preview, inside the app's real layout. ?>
<?= $this->extend('layouts/main') ?>

<?= $this->section('content') ?>
<div data-pixie-preview><?= $render() ?></div>
<?= $this->endSection() ?>
```

Use the section name that layout renders with `renderSection()`.

**`app/Config/PreviewRoutes.php`**, which renders one state and refuses an incomplete preview:

```php
<?php

// Pixie's preview harness: renders one view, partial or view cell in one state of its matrix, for /design-critique.
// app/Config/Routes.php loads this file only in the development environment.

use CodeIgniter\Router\RouteCollection;
use Config\Database;
use Config\Toolbar;

/** @var RouteCollection $routes */
$routes->get('__preview/([a-z0-9-]+)', static function (string $slug) {
    $required = ['empty', 'single', 'typical', 'overflow', 'error', 'loading'];
    $state    = service('request')->getGet('state');
    $state    = is_string($state) ? $state : 'typical';
    $file     = APPPATH . "Previews/{$slug}.php";
    // Served bare, without the layout, so a broken layout can't hide it.
    $problem = static fn (string $message) => '<p role="alert" data-pixie-preview-error>' . esc($message) . '</p>';

    // Keeps the debug toolbar out of the screenshots: it skips any request with a header listed here.
    config(Toolbar::class)->disableOnHeaders['X-Pixie-Preview'] = null;
    service('request')->setHeader('X-Pixie-Preview', '1');

    // Previews never read or write a database: while one renders, every connection only pretends to run its
    // queries, and any query it was asked to run is shown as the problem. This opens no connection.
    $connections = [];
    foreach (get_object_vars(config(Database::class)) as $group => $settings) {
        if (is_array($settings) && isset($settings['DBDriver'])) {
            $db            = Database::connect($group);
            $connections[] = [$db, $db->getLastQuery()];
            $db->pretend();
        }
    }
    $queried = static function () use ($connections): ?string {
        foreach ($connections as [$db, $before]) {
            if ($db->getLastQuery() !== $before) {
                return "previews never query the database, but this ran: {$db->getLastQuery()}";
            }
        }

        return null;
    };
    $buffers = ob_get_level();

    try {
        // Seeded, so Faker data is the same on every load and screenshots compare across runs.
        mt_srand(1);

        if (! is_file($file)) {
            return $problem("No preview named {$slug}");
        }
        // Required in its own scope, so the preview's variables can't overwrite the harness's.
        $states  = (static fn () => require $file)()['states'];
        $missing = array_diff($required, array_keys($states));
        if ($missing !== []) {
            return $problem("Preview {$slug} is missing required states: " . implode(', ', $missing));
        }
        if (! array_key_exists($state, $states)) {
            return $problem("Preview {$slug} has no state {$state}");
        }

        // The view calls the state while it renders, inside the guard, so the layout can't query either.
        $html = view('__preview', ['render' => $states[$state]]);
        $sql  = $queried();

        return $sql === null ? $html : $problem("Preview {$slug} failed to render: {$sql}");
    } catch (Throwable $e) {
        // A view that throws leaves its output buffer open; drop its half-rendered HTML.
        while (ob_get_level() > $buffers) {
            ob_end_clean();
        }

        return $problem("Preview {$slug} failed to render: " . ($queried() ?? $e->getMessage()));
    } finally {
        foreach ($connections as [$db]) {
            $db->pretend(false);
        }
    }
});
```

If the layout needs more (a signed-in user, a locale), set it up in this route before rendering, with made-up values and nothing saved.

**`app/Config/Routes.php`**, which loads the route only in development:

```php
// Pixie's preview harness, for /design-critique. Never registered outside development.
$routes->environment('development', static function (RouteCollection $routes): void {
    require APPPATH . 'Config/PreviewRoutes.php';
});
```

Writing CodeIgniter previews:
- **A query in a preview** shows as the error, and never runs. The usual cause is `Fabricator::create()` or the `fake()` test helper, which both save: use `make()`. The guard covers the shared connection of every group in `app/Config/Database.php`. A connection the code opens itself (`db_connect($group, false)`) isn't covered, so never use one in a preview.
- **A query in the layout** (a view cell in the nav reading categories, sessions kept in the database) fails every state. Don't loosen the guard. Use a layout that doesn't query, if the app has one. Otherwise stop and tell the user which query runs, and ask how to give the layout made-up data in previews.
- **`loading`.** A CodeIgniter page has no pending state of its own. Render the placeholder the page shows while it waits (a skeleton, a disabled "Saving…" button, an `aria-busy` region), or follow the matrix rule for a state the component can't show.
- **Form errors.** For a form whose `error` state is validation messages, set them in that state's closure before rendering: `service('validation')->setError('email', 'That email is already taken.');`. `validation_show_error()`, `validation_list_errors()` and `validation_errors()` show them.
- **The debug toolbar** is kept off preview pages through `Config\Toolbar::$disableOnHeaders`. If `app/Config/Toolbar.php` lacks that property, each load logs a dynamic-property deprecation: suggest adding `public array $disableOnHeaders = [];`. If the toolbar still shows (an older framework), tell the user it will appear in the screenshots.

**Prove the exclusion** after installing, before recording the answer. Don't record `yes` until both pass:
- `CI_ENVIRONMENT=development php -d variables_order=EGPCS spark routes` lists `__preview/([a-z0-9-]+)`, and `CI_ENVIRONMENT=production php -d variables_order=EGPCS spark routes` doesn't. The `-d` flag matters: without it, `CI_ENVIRONMENT` from `.env` wins over the one on the command line, and both runs check the same environment. Don't run it for `testing`: `spark` can't start in PHPUnit's environment.
- Start the app (with the verifier's Launch section, or the launch command from step 5; if there's neither, ask the user for one, and confirm the command before running it). It must run in development: `CI_ENVIRONMENT = development` in `.env`. Load `/__preview/none` from the app's URL: it shows the harness's "No preview named none" message. A CodeIgniter error page means the harness needs adapting to the app (an older CodeIgniter, a renamed `Config\Database`). A 404 means the app isn't running in development. Stop the app afterwards.

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

Paths resolve against `--url`, the origin that serves the preview route (or Storybook). In a Laravel app that's the app's own URL (`php artisan serve`, Herd, Sail), not Vite's dev server. In CodeIgniter it's the app's URL (`php spark serve`, at `http://localhost:8080` by default). For Storybook, each path is the story's `/iframe.html?id=…&viewMode=story`. Every state is captured at the widest viewport (1280), and `typical` and `overflow` at mobile width (390) too. Interaction states are captured at 1280, or at the `viewports` they name. Don't pass `--states` with `--matrix`: the script refuses both together. Put the user's named states in `interactions` instead.

## Temporary mode

When the answer is `no`, `/design-critique` builds the same structure for one run and removes it afterwards: a stories file when a React repo has Storybook, otherwise the `/__preview` route.

1. Before creating anything, save `git status --porcelain --untracked-files=all` to `RUN/status-before.txt`. Any existing file the harness must edit (the Vite entry file, `routes/web.php`, `app/Config/Routes.php`) must be clean. If one isn't, stop and ask the user to commit it first.
2. Create the files, and write each path to `RUN/temp-harness.txt`, marked `created` or `edited`.
3. In cleanup, delete every `created` file and any folder the run made, and `git restore` every `edited` one.
4. Run the same `git status` again. Its output must match `RUN/status-before.txt`. If it doesn't, say which files differ and fix them before ending the run.
