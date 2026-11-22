function _claude_token --description "Print this machine's long-lived Claude token, if it has one"
    # ~/.claude/.token.1p holds a 1Password reference; without it, claude
    # uses the interactive sign-in.
    set -l ref_file ~/.claude/.token.1p
    test -r $ref_file; or return 0
    read -l ref <$ref_file
    # Give up on an unanswered unlock prompt rather than hang.
    timeout 60 op read $ref
    or echo '_claude_token: no token from 1Password; using the sign-in' >&2
end
