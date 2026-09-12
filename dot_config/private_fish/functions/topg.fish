function topg --description 'Run topgrade, logging the session to ~/Documents/system_updates'
    set -l log_dir ~/Documents/system_updates
    mkdir -p $log_dir; or return

    # One log per day; a rerun would silently truncate the earlier one.
    set -l log $log_dir/(date +%Y%m%d).txt
    if test -e $log
        read -l -P "$log exists — overwrite? [y/N] " answer
        string match -qi y $answer; or return 1
    end

    # topgrade resolves `sudo` on PATH (no config for an arbitrary path), so
    # a throwaway dir puts sudo-rs ahead of the system sudo for this run only.
    set -l shim (mktemp -d)
    if command -q sudo-rs
        ln -s (command -v sudo-rs) $shim/sudo
    else
        echo 'topg: sudo-rs not on PATH; falling back to sudo' >&2
    end
    set -lx PATH $shim $PATH

    # damp: print each command before running it, so the log records what was
    # invoked, not just what it printed. Extra args pass through (e.g. --dry-run).
    topgrade -r damp $argv &| tee $log
    rm -r $shim
end
