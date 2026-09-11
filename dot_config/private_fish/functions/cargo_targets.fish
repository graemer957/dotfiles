function cargo_targets --description 'Find Rust target/ build directories under $HOME'
    argparse t/tsv -- $argv; or return

    # Trees whose target/ dirs are managed elsewhere — reported, never a
    # candidate.
    set -l excluded_trees ~/dev/work ~/dev/work.old

    set -l rust
    set -l other
    set -l excluded
    # Cargo projects gitignore target/, and fd honours .gitignore by default —
    # without --no-ignore the search finds nothing. --prune stops descent into
    # a match: target/ is huge, and build scripts can nest their own inside it.
    for dir in (fd --type directory --no-ignore --prune --glob target $HOME)
        # A target/ holding git-tracked files is source (a module named target),
        # never a build dir — it is not a candidate, so don't even size it.
        git -C $dir ls-files --error-unmatch . >/dev/null 2>&1; and continue

        # Bytes, not -h: --tsv wants sortable numbers; human mode formats at print.
        set -l bytes (du -s --block-size=1 $dir | cut -f1)
        # target/'s own mtime only moves when a direct child is added, so the
        # newest file inside is the honest "last built" signal.
        set -l newest (fd --type file --no-ignore . $dir --exec-batch stat -c %Y | sort -n | tail -1)
        set -l when -
        test -n "$newest"; and set when (date -d @$newest '+%Y-%m-%d %H:%M')
        set -l path (string replace $HOME '~' $dir)

        # target/ is also Maven's build dir; a sibling Cargo.toml is the Rust signal.
        set -l kind other
        test -f $dir/../Cargo.toml; and set kind rust
        for tree in $excluded_trees
            string match -q -- "$tree/*" $dir; and set kind excluded
        end

        # --tsv: one stream, tab-separated, raw bytes — for sort/fzf/parsing.
        # Tabs survive the spaces in paths that column-aligned output can't.
        if set -q _flag_tsv
            printf '%s\t%s\t%s\t%s\n' $kind $path $bytes $when
        else
            set -a $kind (printf '%s\t%s\t%s' $path $bytes $when)
        end
    end
    set -q _flag_tsv; and return

    for bucket in rust other excluded
        switch $bucket
            case rust
                echo 'Rust — candidates (Cargo.toml alongside)'
            case other
                echo 'Other target/ directories'
            case excluded
                echo 'Excluded trees — reported, not candidates'
        end
        # $$bucket: the rows list named by $bucket. Bytes ride in field 2 so the
        # total is summed from the rows themselves rather than tracked alongside.
        set -l rows $$bucket
        if test (count $rows) -eq 0
            echo '  (none)'
        else
            printf '%s\n' $rows | numfmt -d \t --field=2 --to=iec | column -t -s \t
            set -l total (math (string join + (string split -f2 \t $rows)))
            echo 'total: '(numfmt --to=iec $total)' across '(count $rows)' dirs'
        end
        echo
    end
end
