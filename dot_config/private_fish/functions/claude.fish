function claude --description 'Claude Code, with work profile under ~/dev/work'
    set -l work_root "$HOME/dev/work"

    if test "$PWD" = "$work_root"; or string match -q "$work_root/*" -- $PWD
        # CLAUDE_CONFIG_DIR replaces user scope entirely: skills and rules
        # under ~/.claude are invisible to work sessions unless linked in.
        set -l cfg "$work_root/.claude"
        set -l linked
        mkdir -p $cfg/rules $cfg/skills
        for src in ~/.claude/rules/*.md
            set -l dest $cfg/rules/(path basename $src)
            if not test -L $dest; and not test -e $dest
                ln -s $src $dest
                set -a linked rules/(path basename $src)
            end
        end
        for src in ~/.claude/skills/*/
            set -l dest $cfg/skills/(path basename $src)
            if not test -L $dest; and not test -e $dest
                ln -s (path resolve $src) $dest
                set -a linked skills/(path basename $src)
            end
        end
        if set -q linked[1]
            echo "claude: bridged new user-scope items into $cfg:"
            printf '  %s\n' $linked
            # Pause only at an interactive prompt; scripts and pipes launch on.
            if isatty stdin
                read -l -P 'Enter to launch claude (Ctrl-C to abort) ' _reply
            end
        end
        CLAUDE_CONFIG_DIR="$cfg" command claude $argv
    else
        command claude $argv
    end
end
