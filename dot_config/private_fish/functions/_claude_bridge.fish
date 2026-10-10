function _claude_bridge --description 'Link new user-scope skills and rules into the work profile'
    # CLAUDE_CONFIG_DIR replaces user scope entirely: skills and rules under
    # ~/.claude are invisible to work sessions unless linked in. Prints each
    # new link relative to the work profile, one per line and nothing else,
    # so callers (claude.fish, graemlin's daemon) decide how to report it.
    set -l cfg "$HOME/dev/work/.claude"
    mkdir -p $cfg/rules $cfg/skills
    for src in ~/.claude/rules/*.md
        set -l dest $cfg/rules/(path basename $src)
        if not test -L $dest; and not test -e $dest
            ln -s $src $dest
            and echo rules/(path basename $src)
        end
    end
    for src in ~/.claude/skills/*/
        set -l dest $cfg/skills/(path basename $src)
        if not test -L $dest; and not test -e $dest
            ln -s (path resolve $src) $dest
            and echo skills/(path basename $src)
        end
    end
end
