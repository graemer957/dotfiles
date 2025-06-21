function fish_user_key_bindings
    if command -v fzf > /dev/null
        fzf --fish | source
    end

    if command -v zoxide > /dev/null
        zoxide init fish | source
    end
end
