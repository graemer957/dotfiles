# Fresh-install a crate through the same cooldown + cargo-auditable pipeline
# the topgrade Cargo step uses, so a new tool never lands at HEAD unaudited.
function cargo_install_cooldown --description 'cargo install with 7d cooldown, built auditable'
    cargo install-update -i --cooldown 7d --install-cargo ~/.local/bin/cargo_auditable $argv
end
