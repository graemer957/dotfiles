function _log_summary --argument-names log focus label --description 'Summarise a run log with claude -p'
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
    set -l session (uuidgen)
    set -l name "$label run on "(date +%d/%m/%Y)

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
    env $profile_env claude -p $prompt --model opus --session-id $session \
        --name $name --tools Read,Grep --add-dir (path dirname $log) \
        | tee -a $log | $render
    set -l rc $pipestatus[1]
    printf '```\n' >>$log
    test $rc -eq 0; or echo "_log_summary: claude exited $rc" >&2

    # The summary session is saved under a readable name, so it can also be
    # picked up later from /resume. Resuming launches with claude's full tool
    # set (--tools binds only the launch that passes it). Asked only at an
    # interactive prompt, and never after a failed summary.
    if test $rc -eq 0; and isatty stdin
        read -l -P 'Talk to Claude about this? [y/N] ' reply
        if string match -qir '^y(es)?$' -- $reply
            env $profile_env claude -r $session
        end
    end
    return 0
end
