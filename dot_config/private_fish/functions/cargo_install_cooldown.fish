# The cooldown + cargo-auditable install pipeline. The 7d window leaves time for a
# compromised release to be noticed and yanked; --locked holds every transitive
# dependency to the crate's tested lockfile, so that window covers the whole graph
# rather than the top-level crate alone. Building through cargo-auditable embeds
# the dependency tree, so `cargo audit bin` reads it exactly.
#
# nextest refuses to build without --locked (its locked-tripwire crate).
function cargo_install_cooldown --description 'cargo install with 7d cooldown, built auditable'
    cargo install-update -i --locked --cooldown 7d --install-cargo ~/.local/bin/cargo_auditable $argv
end
