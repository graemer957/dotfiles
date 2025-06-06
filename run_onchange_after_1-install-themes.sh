#!/bin/bash

mkdir -p ~/dev/others/base16/templates
cd ~/dev/others/base16/templates || exit

if [ ! -d "fish-shell" ]; then
	(
		git clone https://github.com/tomyun/base16-fish.git fish-shell
		cd fish-shell || exit
		git checkout 2f6dd97
	)
fi

if [ ! -d "tmux" ]; then
	(
		git clone https://github.com/tinted-theming/base16-tmux.git tmux
		cd tmux || exit
		git checkout 49a493e
	)
fi
