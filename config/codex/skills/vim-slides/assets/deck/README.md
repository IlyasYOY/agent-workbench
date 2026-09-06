# __VIM_SLIDES_TITLE__

This presentation is stored as one Markdown file per slide under `slides/`.
Nested directories group related slides. Relative paths are sorted
lexicographically, so use numeric prefixes to control the order.

## Neovim

Project-local configuration requires `set exrc` in your Neovim configuration.
Before trusting this repository, open `.nvim.lua`, inspect it, and run `:trust`
from that buffer. Restart Neovim from the repository root afterward.

- `:next` — next slide
- `:prev` — previous slide
- `:SlidesRefresh` — rebuild the recursive slide list
- `<localleader>sp` or `:SlidesToggle` — toggle presentation view
- `:[range]SlidesFold [summary]` — wrap lines, or insert an empty fold when no
  range is given; omit `summary` to enter it in a prompt
- Visual `<localleader>sf` — prompt with the first non-empty selected line as
  the suggested summary, then wrap the selection
- Normal `<localleader>sf` — prompt for a summary, insert an empty fold, and
  start typing inside it

The project uses your existing `maplocalleader`; `.nvim.lua` does not replace
it.

## Folded details

Content between these HTML comments is folded whenever the slide is entered,
including when returning with `:prev` or `[a`. A manual opening lasts until you
leave the slide:

```markdown
<!-- slide-fold: Architecture details -->
Optional detail.
<!-- /slide-fold -->
```

When closed, this example is displayed as `Architecture details · 1 line`.
Legacy `<!-- slide-fold -->` markers remain supported and use `…` in place of
the summary. Both marker forms are invisible when Markdown is rendered, while
the content remains present in the shared document. Empty summaries and
summaries containing `-->` are rejected without changing the buffer.

## Sources

Use descriptive labels rather than numbers:

```markdown
Read the [project documentation] and the detailed note.[^implementation-note]

[project documentation]: https://example.com/docs
[^implementation-note]: A named footnote is easier to maintain than `[^1]`.
```

Labels only need to be unique within one slide. In the combined document the
assembler keeps globally unique labels unchanged and merges repeated identical
definitions. When one label has different definitions, the variants become
`label-1`, `label-2`, and so on.

## Build

From the repository root:

```bash
python3 tools/build-slides.py
```

The command writes `presentation.md`.
