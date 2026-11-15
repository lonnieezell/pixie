# Seed expectation checklists

Starting checklists for common component archetypes. Use the ones that match the section. For any other archetype, derive a list the same way: *"What would a regular user of [reference app] try first, by reflex, and be surprised not to find?"*

**Tree view:** Up/Down moves, Right expands/enters, Left collapses/goes to parent; Home/End; type-ahead to jump; Enter/F2 renames (per platform), Esc cancels rename, blur commits; rename selects the name without the extension; Shift/Cmd(Ctrl)-click multi-select; drag to move with clear drop target and auto-expand on hover; disallow dropping into itself; context menu on right-click *and* keyboard; delete with confirmation or undo; new item appears in rename mode in the right folder; expanded state and selection persist; active item revealed and scrolled into view; sort order is predictable (folders first, natural sort so `file2` < `file10`); collapse-all; large trees stay fast.

**Data grid / spreadsheet-like manager:** arrow-key cell navigation, Tab/Shift-Tab, Enter to edit/commit, Esc to cancel, typing starts editing; copy/paste single and multi-cell, including to/from a real spreadsheet; fill-down; column sort (with visible indicator, stable sort), resize, reorder, hide — and persistence of those; sticky header; row selection with Shift range and Cmd toggle, select-all; bulk actions on selection; filters clearly indicated when active and easy to clear; search highlights matches; undo for edits and deletes; inline validation errors; empty, loading, and no-results states distinct; column widths sensible for content; large datasets virtualized.

**List with selection / file manager:** same selection model as the platform's file manager; double-click/Enter opens; Space previews (macOS); drag out/in where it makes sense; consistent ordering; counts and selection totals visible.

**Forms & dialogs:** focus lands in the first field; Enter submits, Esc cancels; validation on blur and on submit, messages next to the field; no data loss on accidental close (confirm or preserve draft); disabled submit explains why; destructive buttons clearly marked and not the default.

**Drag and drop:** visible drag preview; valid/invalid targets distinguished; auto-scroll near edges; Esc cancels; keyboard alternative exists.
