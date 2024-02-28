# dotfiles

Collection of configuration files for Linux and macOS, managed by [chezmoi](https://chezmoi.io)

## TODO

- [x] `tmux`
- [x] `alacritty`
- [ ] `neovim`

## Keyboard shortcuts

Key bindings configured that are **different** to the default or custom ones added.

**NOTE**: Unless otherwise specified, case does matter!

| Abbreviation | Key |
|--------------|-----|
| A | Alt |
| C | Ctrl |
| L | Leader |
| S | Super (Cmd on macOS) |

### tmux

Prefix: C-a

| Key | Action |
|-----|--------|
| C-a | Switch to last window |
| C-h | Increase size of pane leftwards |
| C-j | Increase size of pane downwards |
| C-k | Increase size of pane upwards |
| C-l | Increase size of pane rightwards |
| h | Move focus left a pane |
| j | Move focus down a pane |
| k | Move focus up a pane |
| l | Move focus right a pane |

### neovim

`<leader>`: `<Space>`

| Hotkey | Action |
|--------|--------|
| C-h | Stop searching |
| C-p | Open file |
| H | Beginning of line |
| L | Go to end of line |
| L-; | Search open buffers |
| L-L | Switch to last buffer |
| L-L+ | nop |
| L-e | Open LSP diagnostic |
| L-w | Write buffer |
| `<Down>` | nop (force my use of vi style keyboard navigation when editing |
| `<Left>` | Switch to left buffer when not editing |
| `<Left>` | nop (force my use of vi style keyboard navigation when editing |
| `<Right>` | Switch to right buffer when not editing |
| `<Right>` | nop (force my use of vi style keyboard navigation when editing |
| `<Up>` | nop (force my use of vi style keyboard navigation when editing |
