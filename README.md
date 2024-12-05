# dotfiles

Collection of configuration files for Linux and macOS, managed by [chezmoi](https://chezmoi.io)

## TODO

- [x] `tmux`
- [x] `alacritty`
- [ ] `neovim`
- [x] Add mode into neovim table to disambiguate arrow key actions
- [x] `git`
- [ ] `dunst`
- [ ] `ulauncher`
- [ ] `yambar`
- [ ] `sway`
- [ ] Global keyboard shortcut [ideas](https://github.com/jonhoo/configs/blob/master/gui/.config/sxhkd/sxhkdrc)
- [ ] Take a look at `hypr` WM
- [ ] `mineapps.list`
- [ ] Lighter 'server' config?
- [ ] Enable clicking on URLs in Alacritty
- [ ] Check for useful fish functions for Linux setup

## Firefox

Version 128 has introduced a questionable new 'privacy preserving' Ad API developed alongside meta, see:
- [OSNews article](https://www.osnews.com/story/140247/i-told-you-so-mozilla-working-with-facebook-to-weaken-firefox-privacy-and-anti-tracking-features/)
- [privacyguides.org](https://blog.privacyguides.org/2024/07/14/mozilla-disappoints-us-yet-again-2/)

Disappointingly you are opted into this experimental API when installing the build. Suffice as to say, I am disabling this: Settings > Privacy & Security > Web Site Advertising Preferences > Disable "Allow web sites to perform privacy ad measurement".

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
| C-h | Switch to the previous session |
| C-l | Switch to the next session |
| h | Move focus left a pane |
| j | Move focus down a pane |
| k | Move focus up a pane |
| l | Move focus right a pane |

### neovim

`<leader>`: `<Space>`

| Mode | Description |
|------|-------------|
| i | Insert |
| n | Normal |

| Mode | Hotkey | Action |
|------|--------|--------|
| i | `<Down>` | nop (force my use of vi style keyboard navigation |
| i | `<Left>` | nop (force my use of vi style keyboard navigation |
| i | `<Right>` | nop (force my use of vi style keyboard navigation |
| i | `<Up>` | nop (force my use of vi style keyboard navigation |
| n | , | Toggle hidden characters |
| n | C-h | Stop searching |
| n | C-p | Open file |
| n | H | Beginning of line |
| n | L | Go to end of line |
| n | L-; | Search open buffers |
| n | L-L | Switch to last buffer |
| n | L-L+ | nop |
| n | L-c | Copy entire buffer into clipboard |
| n | L-e | Open LSP diagnostic |
| n | L-i | Toggle inlay hints |
| n | L-o | Open a new file adjacent to the current file |
| n | L-w | Write buffer |
| n | L-s-w | Enable word wrap |
| n | `<Left>` | Switch to left buffer |
| n | `<Right>` | Switch to right buffer |
