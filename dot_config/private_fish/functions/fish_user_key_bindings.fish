function fish_user_key_bindings
    if command -v fzf > /dev/null
        fzf --fish | source
    end

    if command -v zoxide > /dev/null
        zoxide init fish | source
    end

    # Restore fish v3 behavior: Alt+Backspace deletes a word, not an entire argument
    bind alt-backspace backward-kill-word
end
