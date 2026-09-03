local source = debug.getinfo(1, "S").source
local config_path = source:sub(1, 1) == "@" and source:sub(2)
    or vim.fs.joinpath(vim.fn.getcwd(), ".nvim.lua")
local root = vim.fs.dirname(vim.fs.normalize(vim.fn.fnamemodify(config_path, ":p")))
local slides_dir = vim.fs.joinpath(root, "slides")
local fold_start_prefix = "<!-- slide-fold"
local fold_end = "<!-- /slide-fold -->"

local presentation_enabled = true
local saved_global = nil
local saved_windows = {}
local saved_buffers = {}
local active_windows = {}
local initialized_arglists = {}

local global_options = {
    laststatus = 0,
    showtabline = 0,
    cmdheight = 0,
    showmode = false,
    showcmd = false,
    ruler = false,
}

local window_options = {
    number = false,
    relativenumber = false,
    signcolumn = "no",
    foldcolumn = "0",
    colorcolumn = "",
    cursorline = false,
    list = false,
    spell = false,
    wrap = true,
    linebreak = true,
    breakindent = true,
    conceallevel = 2,
    concealcursor = "nc",
    winbar = "",
    fillchars = "eob: ",
    foldenable = true,
    foldlevel = 0,
    foldmethod = "marker",
    foldmarker = fold_start_prefix .. "," .. fold_end,
    foldtext = "v:lua.VimSlidesFoldText()",
}

local buffer_options = {
    textwidth = 0,
}

local function get_option(name, scope)
    return vim.api.nvim_get_option_value(name, scope)
end

local function set_option(name, value, scope)
    vim.api.nvim_set_option_value(name, value, scope)
end

local function capture_options(names, scope)
    local values = {}
    for name in pairs(names) do
        values[name] = get_option(name, scope)
    end
    return values
end

local function apply_options(values, scope)
    for name, value in pairs(values) do
        set_option(name, value, scope)
    end
end

local function is_slide(buf)
    local path = vim.fs.normalize(vim.api.nvim_buf_get_name(buf))
    return path:sub(1, #slides_dir + 1) == slides_dir .. "/"
        and path:sub(-3) == ".md"
end

local function collect_slides()
    local slides = vim.fn.globpath(slides_dir, "**/*.md", false, true)
    for index, path in ipairs(slides) do
        slides[index] = vim.fs.normalize(path)
    end
    table.sort(slides)
    return slides
end

local function refresh_arglist(win)
    if not vim.api.nvim_win_is_valid(win) then
        return
    end

    vim.api.nvim_win_call(win, function()
        vim.cmd.arglocal()
        vim.cmd("%argdelete")
        for _, path in ipairs(collect_slides()) do
            vim.cmd("$argadd " .. vim.fn.fnameescape(path))
        end
    end)
    initialized_arglists[win] = true
end

local function restore_global_options()
    if saved_global then
        apply_options(saved_global, { scope = "global" })
        saved_global = nil
    end
end

local function restore_window(win)
    local values = saved_windows[win]
    if values and vim.api.nvim_win_is_valid(win) then
        apply_options(values, { win = win })
    end
    saved_windows[win] = nil
    active_windows[win] = nil
end

local function restore_buffer(buf)
    local values = saved_buffers[buf]
    if values and vim.api.nvim_buf_is_valid(buf) then
        apply_options(values, { buf = buf })
    end
    saved_buffers[buf] = nil
end

local function restore_presentation()
    for win in pairs(saved_windows) do
        restore_window(win)
    end
    for buf in pairs(saved_buffers) do
        restore_buffer(buf)
    end
    restore_global_options()
end

local function enable_presentation(win, buf)
    if not presentation_enabled or not is_slide(buf) then
        return
    end

    if not saved_global then
        saved_global = capture_options(global_options, { scope = "global" })
        apply_options(global_options, { scope = "global" })
    end
    if not saved_windows[win] then
        saved_windows[win] = capture_options(window_options, { win = win })
    end
    if not saved_buffers[buf] then
        saved_buffers[buf] = capture_options(buffer_options, { buf = buf })
    end

    apply_options(window_options, { win = win })
    apply_options(buffer_options, { buf = buf })
    active_windows[win] = buf
end

local function toggle_presentation()
    presentation_enabled = not presentation_enabled
    if not presentation_enabled then
        restore_presentation()
        return
    end

    for _, win in ipairs(vim.api.nvim_list_wins()) do
        local buf = vim.api.nvim_win_get_buf(win)
        if is_slide(buf) then
            enable_presentation(win, buf)
        end
    end
end

local function trim(value)
    return value:match("^%s*(.-)%s*$")
end

local function fold_start(summary)
    return fold_start_prefix .. ": " .. summary .. " -->"
end

local function fold_text()
    local marker = vim.fn.getline(vim.v.foldstart)
    local summary = marker:match("^%s*<!%-%- slide%-fold:%s*(.-)%s*%-%->%s*$")
    summary = summary and trim(summary) or ""
    if summary == "" then
        summary = "…"
    end

    local line_count = math.max(0, vim.v.foldend - vim.v.foldstart - 1)
    local unit = line_count == 1 and "line" or "lines"
    return string.format("%s · %d %s", summary, line_count, unit)
end

_G.VimSlidesFoldText = fold_text

local function validate_summary(summary)
    summary = trim(summary)
    if summary == "" then
        return nil
    end
    if summary:find("-->", 1, true) then
        vim.api.nvim_err_writeln("SlidesFold summary must not contain -->")
        return nil
    end
    return summary
end

local function wrap_fold(buf, first_line, last_line, summary)
    local lines = vim.api.nvim_buf_get_lines(buf, first_line - 1, last_line, false)
    local replacement = { fold_start(summary) }
    vim.list_extend(replacement, lines)
    table.insert(replacement, fold_end)
    vim.api.nvim_buf_set_lines(buf, first_line - 1, last_line, false, replacement)
    vim.api.nvim_win_set_cursor(0, { first_line + 1, 0 })
end

local function insert_empty_fold(buf, summary)
    local line = vim.api.nvim_win_get_cursor(0)[1]
    vim.api.nvim_buf_set_lines(buf, line, line, false, { fold_start(summary), "", fold_end })
    vim.api.nvim_win_set_cursor(0, { line + 2, 0 })
    vim.cmd("normal! zO")
end

local function default_summary(buf, first_line, last_line)
    for _, line in ipairs(vim.api.nvim_buf_get_lines(buf, first_line - 1, last_line, false)) do
        local candidate = trim(line)
        if candidate ~= "" then
            return candidate
        end
    end
    return ""
end

local function apply_fold(buf, first_line, last_line, has_range, summary, enter_insert)
    summary = validate_summary(summary)
    if not summary then
        return false
    end
    if has_range then
        wrap_fold(buf, first_line, last_line, summary)
    else
        insert_empty_fold(buf, summary)
    end
    if enter_insert then
        vim.schedule(function()
            if vim.api.nvim_buf_is_valid(buf) and vim.api.nvim_get_current_buf() == buf then
                vim.cmd.startinsert()
            end
        end)
    end
    return true
end

local function request_fold(buf, first_line, last_line, has_range, enter_insert)
    local default = has_range and default_summary(buf, first_line, last_line) or ""
    vim.ui.input({ prompt = "Fold summary: ", default = default }, function(input)
        if input ~= nil then
            apply_fold(buf, first_line, last_line, has_range, input, enter_insert)
        end
    end)
end

local function fold_command(args)
    local buf = vim.api.nvim_get_current_buf()
    if not is_slide(buf) then
        vim.api.nvim_err_writeln("SlidesFold is only available in slides/**/*.md")
        return false
    end
    local has_range = args.range > 0
    if args.args ~= "" then
        return apply_fold(buf, args.line1, args.line2, has_range, args.args, false)
    else
        request_fold(buf, args.line1, args.line2, has_range, false)
    end
    return true
end

local function configure_slide(win, buf)
    if not initialized_arglists[win] then
        refresh_arglist(win)
    end
    vim.keymap.set("n", "<localleader>sp", toggle_presentation, {
        buffer = buf,
        desc = "Toggle slide presentation view",
        silent = true,
    })
    vim.keymap.set("x", "<localleader>sf", ":<C-U>'<,'>SlidesFold<CR>", {
        buffer = buf,
        desc = "Wrap selection in a slide fold",
        silent = true,
    })
    vim.keymap.set("n", "<localleader>sf", function()
        local line = vim.api.nvim_win_get_cursor(0)[1]
        request_fold(buf, line, line, false, true)
    end, {
        buffer = buf,
        desc = "Insert an empty slide fold",
        silent = true,
    })
    enable_presentation(win, buf)
end

vim.api.nvim_create_user_command("SlidesRefresh", function()
    refresh_arglist(vim.api.nvim_get_current_win())
end, { desc = "Refresh the recursive slide argument list", force = true })

vim.api.nvim_create_user_command("SlidesToggle", toggle_presentation, {
    desc = "Toggle slide presentation view",
    force = true,
})

vim.api.nvim_create_user_command("SlidesFold", fold_command, {
    desc = "Wrap a range or insert an empty slide fold with a summary",
    range = true,
    nargs = "*",
    force = true,
})

local group = vim.api.nvim_create_augroup("vim_slides", { clear = true })

vim.api.nvim_create_autocmd({ "BufEnter", "BufWinEnter", "FileType" }, {
    group = group,
    pattern = "*",
    callback = function(args)
        local win = vim.api.nvim_get_current_win()
        vim.schedule(function()
            if not vim.api.nvim_win_is_valid(win)
                or not vim.api.nvim_buf_is_valid(args.buf)
                or vim.api.nvim_win_get_buf(win) ~= args.buf
            then
                return
            end
            if is_slide(args.buf) then
                configure_slide(win, args.buf)
            else
                local slide_buf = active_windows[win]
                restore_window(win)
                if slide_buf then
                    restore_buffer(slide_buf)
                end
                if next(active_windows) == nil then
                    for buf in pairs(saved_buffers) do
                        restore_buffer(buf)
                    end
                    restore_global_options()
                end
            end
        end)
    end,
})

vim.api.nvim_create_autocmd("WinClosed", {
    group = group,
    pattern = "*",
    callback = function(args)
        local win = tonumber(args.match)
        if win then
            saved_windows[win] = nil
            active_windows[win] = nil
            initialized_arglists[win] = nil
        end
        if next(active_windows) == nil then
            for buf in pairs(saved_buffers) do
                restore_buffer(buf)
            end
            restore_global_options()
        end
    end,
})

vim.api.nvim_create_autocmd("BufWritePost", {
    group = group,
    pattern = "*.md",
    callback = function(args)
        if is_slide(args.buf) then
            refresh_arglist(vim.api.nvim_get_current_win())
        end
    end,
})
