#!/bin/bash

mkdir -p ~/dev/others/base16/templates 
cd ~/dev/others/base16/templates

rm -rf fish-shell
git clone gh:tomyun/base16-fish.git fish-shell

rm -rf tmux
git clone gh:tinted-theming/base16-tmux.git tmux
