---
name: vim-slides
description: Create, edit, navigate, and assemble Markdown slide decks presented in Neovim. Use for repositories whose slides live as individual Markdown files under slides/; do not use for PowerPoint, PDF, or browser-rendered decks.
---

# Vim Slides

Build presentations as small Markdown files that remain comfortable to present
directly in Neovim and easy to combine for sharing.

## Workflow

1. Choose the branch:
   - For a new deck, run `scripts/init_deck.py <target> [--title <title>]` from
     this skill. The target must be new or empty.
   - For an existing deck, inspect its `.nvim.lua`, `README.md`, and `slides/`
     before editing.

   Completion criterion: the target deck and allowed filesystem changes are
   explicit; initialization never overwrites a non-empty directory.

2. Author slides under `slides/`:
   - Keep one slide per `.md` file with one primary `#` heading.
   - Order slides by their relative POSIX paths. Use numeric prefixes on both
     directories and files when order matters.
   - Split content that does not fit a terminal viewport. Put optional detail
     between `<!-- slide-fold: Summary -->` and `<!-- /slide-fold -->` when it
     should be closed on entry. Legacy `<!-- slide-fold -->` markers remain
     supported.
   - Cite sources with descriptive Markdown reference labels such as `[spec]`
     or named footnotes such as `[^spec-details]`. Do not use numeric labels.
   - Preserve the deck's language, voice, and existing style.

   Completion criterion: every requested slide is a standalone Markdown file,
   nested groups remain ordered by path, and sourced claims use descriptive
   labels.

3. Build the shareable document from the deck root:

   ```bash
   python3 tools/build-slides.py
   ```

   The command recursively sorts `slides/**/*.md` and writes `presentation.md`.
   It keeps unique labels unchanged, merges repeated identical definitions, and
   numbers only conflicting definitions of the same label.

   Completion criterion: the command succeeds and the resulting document has
   the same slide order and content as the source files.

4. Verify Neovim behavior when `.nvim.lua` changes:
   - Confirm `:next` and `:prev` traverse the recursively sorted slide list.
   - Confirm fold markers are closed on every slide entry, including a
     first-slide → next-slide → first-slide round trip after manually opening
     them. Closed folds display `Summary · N lines`, counting only the content
     between the markers. Legacy markers display `… · N lines`.
   - Confirm `<localleader>sp` toggles the buffer-local presentation mapping
     without redefining `maplocalleader`, and restores prior options.
   - Confirm `:[range]SlidesFold [summary]` uses a supplied summary without a
     prompt. With no summary, Visual `<localleader>sf` suggests the first
     non-empty selected line, while Normal `<localleader>sf` prompts, inserts an
     empty fold, places the cursor inside it, and enters Insert mode.
   - Confirm cancelling the prompt, entering an empty summary, or using a
     summary containing `-->` leaves the buffer unchanged.

   Completion criterion: both the generated Markdown and the real Neovim
   workflow have been exercised; report any check that could not run.

## Boundaries

- Invoke this skill only when the user explicitly requests `$vim-slides`.
- Do not commit the generated repository unless the user explicitly asks.
- Do not trust `.nvim.lua` on the user's behalf. Tell the user to inspect it in
  Neovim and run `:trust`; project-local configuration also requires `exrc`.
- Do not add a manifest for ordering. The source of truth is recursive lexical
  order by relative path.

## Scripts

- `scripts/init_deck.py`: create a new Git-backed deck from the bundled assets.
- `scripts/build_slides.py`: canonical dependency-free assembler; the
  initializer copies it into each deck as `tools/build-slides.py`.
