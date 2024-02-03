# Seeded from https://github.com/jonhoo/configs/blob/master/shell/.config/fish/config.fish

abbr -a c cargo
abbr -a e nvim
abbr -a o open
abbr -a g gitq

if status is-interactive
	# Only apply base16 theme for fish if tmux is not running, due to escape sequences not working in later versions
	# See https://github.com/tomyun/base16-fish/issues/7#issuecomment-963376055
	if test -d ~/dev/others/base16/templates/fish-shell && test -z "$TMUX"
		set fish_function_path $fish_function_path ~/dev/others/base16/templates/fish-shell/functions
		builtin source ~/dev/others/base16/templates/fish-shell/conf.d/base16.fish
	end
end

# Fish git prompt
set __fish_git_prompt_showuntrackedfiles 'yes'
set __fish_git_prompt_showdirtystate 'yes'
set __fish_git_prompt_showstashstate ''
set __fish_git_prompt_showupstream 'none'
set -g fish_prompt_pwd_dir_length 3

function fish_prompt
	set_color brblack
	echo -n "["(date "+%H:%M")"] "
	set_color blue
	echo -n (hostname -s)
	if [ $PWD != $HOME ]
		set_color brblack
		echo -n ':'
		set_color yellow
		echo -n (basename $PWD)
	end
	set_color green
	printf '%s ' (__fish_git_prompt)
	set_color red
	echo -n '| '
	set_color normal
end
