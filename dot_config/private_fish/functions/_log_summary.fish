function _log_summary --argument-names log focus --description 'Summarise a run log with claude -p'
    if not command -q claude
        echo '_log_summary: claude not on PATH; skipping summary' >&2
        return 0
    end

    # Profile by which credentials exist on this machine, not by cwd: the
    # log has no relationship to the directory the wrapper was run from.
    set -l work_cfg ~/dev/work/.claude
    set -l profile_env
    if test -r ~/.claude/.credentials.json
        # personal: default config dir
    else if test -r $work_cfg/.credentials.json
        set profile_env CLAUDE_CONFIG_DIR=$work_cfg
    else
        echo '_log_summary: no logged-in claude profile; skipping summary' >&2
        return 0
    end

    set -l prompt "Summarise the run log at $log. Open with a one-line verdict, \
then a Markdown table of what ran and its outcome, then anything worth a look. \
Focus on: $focus"

    # `env` resolves claude from PATH, bypassing the cwd-switching fish
    # wrapper. Read/Grep need no permission inside an --add-dir; no other
    # tools, so the model can only look at the log. The prompt goes first:
    # --tools and --add-dir are variadic and would swallow it.
    # mcat renders the Markdown when present; otherwise it's printed raw.
    set -l render cat
    if command -q mcat
        set render mcat -e md --silent
    else
        echo '_log_summary: mcat not on PATH; printing raw Markdown' >&2
    end
    # The exchange is appended to the log too, so a later reader sees what
    # was asked as well as what came back. Header and prompt land before the
    # call so a crashed run still records the attempt; the response is tee'd
    # raw and only rendered for the terminal.
    printf '\nSummarising log with Claude 🤖, please wait...\n\n' >&2
    printf '\nSummary from Claude 🤖\n\n```text\n%s\n```\n\n```markdown\n' $prompt >>$log
    env $profile_env claude -p $prompt --model opus --no-session-persistence \
        --tools Read,Grep --add-dir (path dirname $log) \
        | tee -a $log | $render
    set -l rc $pipestatus[1]
    printf '```\n' >>$log
    test $rc -eq 0; or echo "_log_summary: claude exited $rc" >&2
    return 0
end
