#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
seed_file="$root/candidate-seeds.tsv"
repo_root="$root/work/repos"
mkdir -p "$repo_root"

while IFS="$(printf '\t')" read -r repository provenance; do
    case "$repository" in
        ''|'#'*) continue ;;
    esac
    destination="$repo_root/$(printf '%s' "$repository" | tr '/' '__')"
    if [ -d "$destination/.git" ]; then
        printf 'EXISTS\t%s\t%s\n' "$repository" "$destination"
        continue
    fi
    if ! git clone --quiet --depth 1 --filter=blob:none --no-checkout \
        "https://github.com/$repository.git" "$destination"; then
        printf 'CLONE_FAILED\t%s\t%s\n' "$repository" "$provenance"
        continue
    fi
    if ! git -C "$destination" sparse-checkout set --no-cone \
        '/**/*.circom' '/**/*.sol' '/README*' '/**/README*' \
        '/package.json' '/**/package.json' '/foundry.toml' '/**/foundry.toml'; then
        printf 'SPARSE_FAILED\t%s\t%s\n' "$repository" "$provenance"
        continue
    fi
    if ! git -C "$destination" checkout --quiet; then
        printf 'CHECKOUT_FAILED\t%s\t%s\n' "$repository" "$provenance"
        continue
    fi
    printf 'FETCHED\t%s\t%s\n' "$repository" \
        "$(git -C "$destination" rev-parse HEAD)"
done < "$seed_file"

