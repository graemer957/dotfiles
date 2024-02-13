-- Seeded from https://github.com/jonhoo/configs/blob/master/editor/.config/nvim/init.lua

-- sweet sweet relative line numbers
vim.opt.relativenumber = true

-- and show the absolute line number for the current line
vim.opt.number = true

-- infinite undo!
-- NOTE: ends up in ~/.local/state/nvim/undo/
vim.opt.undofile = true
