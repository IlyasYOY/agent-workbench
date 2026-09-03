from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "config" / "agent" / "skills" / "vim-slides"
INIT_SCRIPT = SKILL_ROOT / "scripts" / "init_deck.py"
BUILD_SCRIPT = SKILL_ROOT / "scripts" / "build_slides.py"


def load_build_module():
    spec = importlib.util.spec_from_file_location("vim_slides_build", BUILD_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Vim slides build script")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BUILD = load_build_module()


class VimSlidesTest(unittest.TestCase):
    def test_initializer_creates_git_deck_and_real_build_command_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "team-talk"
            subprocess.run(
                [sys.executable, str(INIT_SCRIPT), str(target), "--title", "Team Talk"],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertEqual((target / "slides" / "01-title.md").read_text(), "# Team Talk\n\nPresentation subtitle.\n")
            self.assertEqual(
                (target / ".nvim.lua").read_text(),
                (SKILL_ROOT / "assets" / "deck" / "nvim.lua").read_text(),
            )
            self.assertIn("<localleader>sp", (target / ".nvim.lua").read_text())
            self.assertIn("<localleader>sf", (target / ".nvim.lua").read_text())
            self.assertNotIn("maplocalleader =", (target / ".nvim.lua").read_text())
            self.assertTrue((target / "tools" / "build-slides.py").is_file())
            self.assertEqual(
                subprocess.run(
                    ["git", "-C", str(target), "rev-parse", "--is-inside-work-tree"],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip(),
                "true",
            )

            subprocess.run(
                [sys.executable, "tools/build-slides.py"],
                cwd=target,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual((target / "presentation.md").read_text(), "# Team Talk\n\nPresentation subtitle.\n")

    def test_neovim_fold_summary_prompt_mapping_and_foldtext(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = (Path(temporary) / "fold-talk").resolve()
            subprocess.run(
                [sys.executable, str(INIT_SCRIPT), str(target), "--title", "Fold Talk"],
                check=True,
                capture_output=True,
                text=True,
            )
            slide = target / "slides" / "01-title.md"
            result_file = target / "nvim-test-passed"
            script = target / "test-folds.lua"
            script.write_text(
                f'''local slide = {str(slide)!r}
local config = {str(target / ".nvim.lua")!r}
local result_file = {str(result_file)!r}

vim.o.swapfile = false
vim.cmd("edit " .. vim.fn.fnameescape(slide))
vim.cmd("luafile " .. vim.fn.fnameescape(config))
vim.cmd("doautocmd vim_slides BufEnter")
vim.wait(500, function()
    return vim.wo.foldmethod == "marker"
end)

local function assert_equal(actual, expected, label)
    if not vim.deep_equal(actual, expected) then
        error(string.format("%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)))
    end
end

vim.api.nvim_buf_set_lines(0, 0, -1, false, {{ "# Fold Talk", "one", "two" }})
vim.cmd("2,3SlidesFold Architecture details")
assert_equal(vim.api.nvim_buf_get_lines(0, 1, 5, false), {{
    "<!-- slide-fold: Architecture details -->",
    "one",
    "two",
    "<!-- /slide-fold -->",
}}, "range wrapping")
vim.cmd("normal! zM")
assert_equal(vim.wo.foldmethod, "marker", "fold method")
assert_equal(vim.fn.foldclosed(2), 2, "closed summary fold")
assert_equal(vim.fn.foldtextresult(2), "Architecture details · 2 lines", "summary foldtext")

vim.api.nvim_buf_set_lines(0, 0, -1, false, {{
    "<!-- slide-fold -->",
    "legacy detail",
    "<!-- /slide-fold -->",
}})
vim.cmd("normal! zM")
assert_equal(vim.fn.foldtextresult(1), "… · 1 line", "legacy foldtext")

vim.api.nvim_buf_set_lines(0, 0, -1, false, {{ "# Fold Talk", "", "  Suggested summary  ", "detail" }})
local unchanged = vim.api.nvim_buf_get_lines(0, 0, -1, false)
local prompt_options
vim.ui.input = function(options, callback)
    prompt_options = options
    callback(nil)
end
vim.cmd("2,4SlidesFold")
assert_equal(prompt_options.default, "Suggested summary", "visual default")
assert_equal(vim.api.nvim_buf_get_lines(0, 0, -1, false), unchanged, "cancelled prompt")

vim.ui.input = function(_, callback)
    callback("   ")
end
vim.cmd("2,4SlidesFold")
assert_equal(vim.api.nvim_buf_get_lines(0, 0, -1, false), unchanged, "empty prompt")

local valid_command = pcall(vim.cmd, "2,4SlidesFold invalid --> summary")
assert_equal(valid_command, false, "invalid summary command")
assert_equal(vim.api.nvim_buf_get_lines(0, 0, -1, false), unchanged, "invalid summary")

vim.api.nvim_win_set_cursor(0, {{ 1, 0 }})
vim.ui.input = function(_, callback)
    callback("Speaker notes")
end
local normal_mapping
for _, mapping in ipairs(vim.api.nvim_buf_get_keymap(0, "n")) do
    if mapping.desc == "Insert an empty slide fold" then
        normal_mapping = mapping
        break
    end
end
if not normal_mapping then
    error("normal fold mapping: mapping not found")
end
vim.api.nvim_feedkeys(normal_mapping.lhsraw, "xt", false)
assert_equal(vim.api.nvim_buf_get_lines(0, 1, 4, false), {{
    "<!-- slide-fold: Speaker notes -->",
    "",
    "<!-- /slide-fold -->",
}}, "normal mapping insertion")
assert_equal(vim.api.nvim_win_get_cursor(0), {{ 3, 0 }}, "normal mapping cursor")
assert_equal(vim.fn.foldclosed(2), -1, "normal mapping opens fold")

vim.fn.writefile({{ "passed" }}, result_file)
'''
            )

            completed = subprocess.run(
                [
                    "nvim",
                    "--headless",
                    "-u",
                    "NONE",
                    "-i",
                    "NONE",
                    "-c",
                    f"luafile {script}",
                    "-c",
                    "qa!",
                ],
                cwd=target,
                capture_output=True,
                text=True,
                timeout=10,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(result_file.is_file(), completed.stderr)

    def test_neovim_recloses_folds_after_navigation_and_restores_foldlevel(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = (Path(temporary) / "navigation-talk").resolve()
            subprocess.run(
                [sys.executable, str(INIT_SCRIPT), str(target), "--title", "Navigation Talk"],
                check=True,
                capture_output=True,
                text=True,
            )
            first_slide = target / "slides" / "01-title.md"
            first_slide.write_text(
                """# Navigation Talk

<!-- slide-fold: Sources -->
Hidden source.
<!-- /slide-fold -->
"""
            )
            second_slide = target / "slides" / "02-next.md"
            second_slide.write_text("# Next\n")
            result_file = target / "nvim-navigation-test-passed"
            script = target / "test-navigation.lua"
            script.write_text(
                f'''local first_slide = {str(first_slide)!r}
local config = {str(target / ".nvim.lua")!r}
local result_file = {str(result_file)!r}

vim.o.swapfile = false
vim.cmd("edit " .. vim.fn.fnameescape(first_slide))
vim.wo.foldlevel = 7
vim.cmd("luafile " .. vim.fn.fnameescape(config))
vim.cmd("doautocmd vim_slides BufEnter")
vim.wait(500, function()
    return vim.wo.foldmethod == "marker" and vim.wo.foldlevel == 0
end)

local function assert_equal(actual, expected, label)
    if not vim.deep_equal(actual, expected) then
        error(string.format("%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)))
    end
end

assert_equal(vim.fn.foldclosed(3), 3, "fold closed on first entry")
vim.cmd("normal! zR")
assert_equal(vim.fn.foldclosed(3), -1, "manual fold opening")

vim.cmd("next")
vim.wait(500, function()
    return vim.fn.expand("%:t") == "02-next.md" and vim.wo.foldlevel == 0
end)
assert_equal(vim.wo.foldlevel, 0, "next slide fold level")

vim.cmd("previous")
vim.wait(500, function()
    return vim.fn.expand("%:t") == "01-title.md" and vim.wo.foldlevel == 0
end)
assert_equal(vim.wo.foldlevel, 0, "returned slide fold level")
assert_equal(vim.fn.foldclosed(3), 3, "fold closed after return")

vim.cmd("SlidesToggle")
assert_equal(vim.wo.foldlevel, 7, "restored fold level")
vim.cmd("SlidesToggle")
assert_equal(vim.wo.foldlevel, 0, "reenabled presentation fold level")

vim.fn.writefile({{ "passed" }}, result_file)
'''
            )

            completed = subprocess.run(
                [
                    "nvim",
                    "--headless",
                    "-u",
                    "NONE",
                    "-i",
                    "NONE",
                    "-c",
                    f"luafile {script}",
                    "-c",
                    "qa!",
                ],
                cwd=target,
                capture_output=True,
                text=True,
                timeout=10,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(result_file.is_file(), completed.stderr)

    def test_skill_is_explicit_only(self) -> None:
        metadata = (SKILL_ROOT / "agents" / "openai.yaml").read_text()

        self.assertIn("policy:\n  allow_implicit_invocation: false\n", metadata)

    def test_initializer_refuses_non_empty_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "existing"
            target.mkdir()
            existing = target / "keep.txt"
            existing.write_text("keep\n")

            result = subprocess.run(
                [sys.executable, str(INIT_SCRIPT), str(target)],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("not empty", result.stderr)
            self.assertEqual(existing.read_text(), "keep\n")
            self.assertFalse((target / ".git").exists())

    def test_builder_orders_nested_slides_and_keeps_unique_labels(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            slides = root / "slides"
            nested = slides / "02-body"
            nested.mkdir(parents=True)
            (slides / "01-intro.md").write_text(
                """# Intro

Read [docs], [details][source], [source][], and note.[^note]
Do not alter [docs](https://inline.example) or `[docs]`.

```markdown
[docs]
[^note]
```

[docs]: https://docs.example
[source]: https://source.example
[^note]: Intro note.
"""
            )
            (nested / "01-detail.md").write_text(
                """# Detail

Read [nested-docs].[^nested-note]

<!-- slide-fold -->
Hidden initially.
<!-- /slide-fold -->

[nested-docs]: https://nested.example
[^nested-note]: Nested note.
"""
            )

            output = BUILD.build(root, Path("slides"), Path("presentation.md"))
            combined = output.read_text()

            self.assertLess(combined.index("# Intro"), combined.index("# Detail"))
            self.assertIn("Read [docs], [details][source], [source][], and note.[^note]", combined)
            self.assertIn("[nested-docs]: https://nested.example", combined)
            self.assertIn("[^nested-note]: Nested note.", combined)
            self.assertIn("[docs](https://inline.example)", combined)
            self.assertIn("`[docs]`", combined)
            self.assertIn("```markdown\n[docs]\n[^note]\n```", combined)
            self.assertIn("<!-- slide-fold -->", combined)
            self.assertEqual(combined.count("\n\n---\n\n"), 1)

    def test_builder_merges_identical_global_definitions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            slides = Path(temporary) / "slides"
            slides.mkdir()
            (slides / "01.md").write_text(
                """# One

Read [docs].[^details]

[docs]:
  https://example.com/docs
  "Documentation"
[^details]: Shared detail.
    Continued detail.
"""
            )
            second_slide = """# Two

Read [docs] again.[^details]

[docs]:
  https://example.com/docs__TRAILING__
  "Documentation"
[^details]: Shared detail.
    Continued detail.__TRAILING__
"""
            (slides / "02.md").write_text(
                second_slide.replace("__TRAILING__", "   ")
            )

            combined = BUILD.assemble(slides)

            self.assertNotIn("docs-1", combined)
            self.assertNotIn("details-1", combined)
            self.assertEqual(combined.count("[docs]:"), 1)
            self.assertEqual(combined.count("[^details]:"), 1)
            self.assertIn("Read [docs] again.[^details]", combined)

    def test_builder_numbers_distinct_definitions_and_reuses_each_number(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            slides = Path(temporary) / "slides"
            slides.mkdir()
            (slides / "01.md").write_text(
                """# One

Read [docs] and [reserved][docs-1].[^note]

[docs]:
  https://example.com/a
[docs-1]: https://example.com/reserved
[^note]: Variant A.
"""
            )
            (slides / "02.md").write_text(
                """# Two

Read [docs].[^note]

[docs]:
  https://example.com/b
[^note]: Variant B.
"""
            )
            (slides / "03.md").write_text(
                """# Three

Read [docs] again.[^note]

[docs]:
  https://example.com/a
[^note]: Variant A.
"""
            )

            combined = BUILD.assemble(slides)

            self.assertIn("Read [docs-2] and [reserved][docs-1].[^note-1]", combined)
            self.assertIn("Read [docs-3].[^note-2]", combined)
            self.assertIn("Read [docs-2] again.[^note-1]", combined)
            self.assertEqual(combined.count("[docs-2]:"), 1)
            self.assertEqual(combined.count("[docs-3]:"), 1)
            self.assertEqual(combined.count("[^note-1]:"), 1)
            self.assertEqual(combined.count("[^note-2]:"), 1)
            self.assertIn("[docs-1]: https://example.com/reserved", combined)

    def test_builder_rejects_duplicate_labels_and_output_under_slides(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            slides = root / "slides"
            slides.mkdir()
            (slides / "01.md").write_text("# Slide\n\n[docs]: one\n[DOCS]: two\n")

            with self.assertRaisesRegex(BUILD.BuildError, "duplicate reference label"):
                BUILD.assemble(slides)
            with self.assertRaisesRegex(BUILD.BuildError, "outside the slides directory"):
                BUILD.build(root, Path("slides"), Path("slides/presentation.md"))

    def test_builder_rejects_numeric_labels(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            slides = Path(temporary) / "slides"
            slides.mkdir()
            (slides / "01.md").write_text("# Slide\n\nSource.[^1]\n\n[^1]: Numeric source.\n")

            with self.assertRaisesRegex(BUILD.BuildError, "numeric footnote label"):
                BUILD.assemble(slides)


if __name__ == "__main__":
    unittest.main()
