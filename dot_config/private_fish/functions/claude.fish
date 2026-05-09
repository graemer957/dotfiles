function claude --description 'Claude Code, with work profile under ~/dev/work'
    set -l work_root "$HOME/dev/work"

    if test "$PWD" = "$work_root"; or string match -q "$work_root/*" -- $PWD
        CLAUDE_CONFIG_DIR="$work_root/.claude" command claude $argv
    else
        command claude $argv
    end
end
