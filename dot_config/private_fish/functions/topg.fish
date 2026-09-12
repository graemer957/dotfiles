function topg --description 'Run topgrade, logging the session to ~/Documents/system_updates'
    set -l log_dir ~/Documents/system_updates
    mkdir -p $log_dir; or return

    # One log per day; a rerun would silently truncate the earlier one.
    set -l log $log_dir/(date +%Y%m%d).txt
    if test -e $log
        read -l -P "$log exists — overwrite? [y/N] " answer
        string match -qi y $answer; or return 1
    end

    # damp: print each command before running it, so the log records what was
    # invoked, not just what it printed. Extra args pass through (e.g. --dry-run).
    topgrade -r damp $argv &| tee $log
end
