#!/usr/bin/env bash
# ============================================================================
#  code.sh — lance Forge Code, installe les langages, exécute vos programmes
#  Dépendance : python3 (3.8 ou plus). Tout le reste s'installe en extensions.
# ============================================================================
set -Eeuo pipefail

readonly SCRIPT_VERSION="1.0.0"
SCRIPT_NAME="$(basename "$0")"; readonly SCRIPT_NAME
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"; readonly SCRIPT_DIR
readonly GUI="$SCRIPT_DIR/forge-code.py"
readonly WORKSPACE_DEFAULT="${FORGE_CODE_WORKSPACE:-$HOME/Code}"

# ---------------------------------------------------------------- Affichage
if [[ -t 1 && -z ${NO_COLOR:-} ]]; then
    C_RED=$'\e[31m'; C_GRN=$'\e[32m'; C_YEL=$'\e[33m'; C_BLU=$'\e[34m'
    C_DIM=$'\e[2m'; C_BLD=$'\e[1m'; C_RST=$'\e[0m'
else
    C_RED=""; C_GRN=""; C_YEL=""; C_BLU=""; C_DIM=""; C_BLD=""; C_RST=""
fi
info()    { printf '%s➜%s %s\n' "$C_BLU" "$C_RST" "$*"; }
ok()      { printf '%s✔%s %s\n' "$C_GRN" "$C_RST" "$*"; }
warn()    { printf '%s⚠%s %s\n' "$C_YEL" "$C_RST" "$*" >&2; }
fail()    { printf '%s✖%s %s\n' "$C_RED" "$C_RST" "$*" >&2; }
tip()     { printf '%s💡 %s%s\n' "$C_DIM" "$*" "$C_RST"; }
section() { printf '\n%s%s%s\n' "$C_BLD" "$*" "$C_RST"; }
die()     { fail "$*"; exit 1; }
has()     { command -v "$1" >/dev/null 2>&1; }

# ---------------------------------------------------------------- Python
PY=""
find_python() {
    local c
    for c in python3 python; do
        if has "$c" && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
            PY="$(command -v "$c")"; return 0
        fi
    done
    return 1
}
require_python() {
    find_python && return 0
    fail "Python 3.8 ou plus est introuvable : Forge Code en a besoin pour fonctionner."
    if has apt-get; then tip "sudo apt install python3"
    elif has dnf; then tip "sudo dnf install python3"
    elif has pacman; then tip "sudo pacman -S python"
    elif has brew; then tip "brew install python"; fi
    exit 1
}
[[ -f $GUI ]] || die "forge-code.py introuvable à côté de $SCRIPT_NAME ($SCRIPT_DIR)."

forge() { require_python; "$PY" "$GUI" "$@"; }

# ---------------------------------------------------------------- Aide
show_usage() {
    cat <<EOF
${C_BLD}$SCRIPT_NAME v$SCRIPT_VERSION${C_RST} — Forge Code, atelier de programmation multi-langages

${C_BLD}Usage :${C_RST} $SCRIPT_NAME [commande] [arguments]
  (sans commande : ouvre l'interface, comme « $SCRIPT_NAME gui »)

${C_BLD}Démarrage${C_RST}
  setup [langages…]   Vérifie Python, ajoute Forge Code au menu des applications et à
                      ~/.local/bin, puis installe les langages demandés (ex. setup python rust)
  gui [dossier]       Ouvre l'interface (dossier des projets, défaut : $WORKSPACE_DEFAULT)
  doctor              Diagnostique l'installation (langages, droits, git…)

${C_BLD}Extensions (langages et outils)${C_RST}
  list                Liste les extensions et leur état
  install <id…>       Installe des extensions   (ex. install rust go ruff prettier)
  uninstall <id…>     Retire des outils installés pour votre utilisateur

${C_BLD}Projets${C_RST}
  new <nom> [langage] [modèle]
                      Crée un projet (modèles : hello, guess, plot, empty)
  run <fichier> [-- args…]
                      Exécute un fichier dans ce terminal (langage deviné par l'extension)
  export  <projet> [-o fichier.zip]
  import  <fichier.zip> [dossier]
  snapshot <projet> [-m "description"]
                      Instantané git du projet

${C_BLD}Divers${C_RST}
  completion          Autocomplétion bash : source <($SCRIPT_NAME completion)
  version             Affiche les versions

${C_BLD}Exemples${C_RST}
  $SCRIPT_NAME setup python javascript
  $SCRIPT_NAME new Bonjour python && $SCRIPT_NAME
  $SCRIPT_NAME install rust && $SCRIPT_NAME new Jeu rust guess
  $SCRIPT_NAME run ~/Code/Bonjour/main.py -- --verbose

${C_BLD}Fichiers${C_RST}
  <projet>/.forge.json                 langage, fichier principal, arguments du projet
  ~/.config/forge-code/extensions/     vos extensions personnelles (*.json)
  ~/.cache/forge-code/                 compilations (hors des projets)
EOF
}

# ---------------------------------------------------------------- Commandes
cmd_setup() {
    section "Python"
    require_python
    ok "$("$PY" --version) ($PY)"

    section "Raccourcis"
    mkdir -p "$HOME/.local/bin"
    ln -sf "$SCRIPT_DIR/$SCRIPT_NAME" "$HOME/.local/bin/forge-code"
    ok "Commande « forge-code » : $HOME/.local/bin/forge-code"
    case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) warn "$HOME/.local/bin n'est pas dans votre PATH (ajoutez-le à ~/.bashrc)";; esac
    if [[ $(uname -s) == Linux ]]; then
        local apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
        mkdir -p "$apps"
        cat >"$apps/forge-code.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Forge Code
Comment=Écrire et exécuter du code dans tous les langages
Exec="$SCRIPT_DIR/$SCRIPT_NAME" gui
Icon=utilities-terminal
Terminal=false
Categories=Development;IDE;
DESK
        ok "Menu des applications : Forge Code"
    fi
    has git || warn "git absent : pas d'instantanés (« $SCRIPT_NAME install git »)."
    if (($#)); then
        section "Langages"
        forge --install "$@" || true
    else
        tip "Installez des langages : $SCRIPT_NAME install python javascript rust …  (liste : $SCRIPT_NAME list)"
    fi
    section "Prêt"
    ok "Lancez : $SCRIPT_NAME   (ou « forge-code » depuis n'importe où)"
}

cmd_gui() {
    local ws="${1:-$WORKSPACE_DEFAULT}"
    mkdir -p "$ws"
    info "Forge Code — projets dans $ws"
    exec "$PY" "$GUI" "$ws"
}

cmd_new() {
    [[ -n ${1:-} ]] || die "Indiquez un nom : $SCRIPT_NAME new MonProjet [langage] [modèle]"
    forge "$WORKSPACE_DEFAULT" --new "$1" --lang "${2:-python}" --template "${3:-hello}"
}

cmd_run() {
    [[ -n ${1:-} ]] || die "Indiquez un fichier : $SCRIPT_NAME run main.py [-- args…]"
    local f="$1"; shift
    [[ ${1:-} == -- ]] && shift
    forge --run "$f" -- "$@"
}

cmd_version() {
    echo "$SCRIPT_NAME $SCRIPT_VERSION"
    find_python && "$PY" --version || echo "python3 : absent"
}

cmd_completion() {
    cat <<'COMP'
_forge_code_sh() {
    local cur=${COMP_WORDS[COMP_CWORD]} prev=${COMP_WORDS[COMP_CWORD-1]}
    local cmds="setup gui doctor list install uninstall new run export import snapshot completion version help"
    local exts="python javascript typescript web c cpp rust go java kotlin csharp ruby php lua bash perl r dart haskell julia zig git ruff black prettier eslint clang-format cppcheck gofmt rustfmt shellcheck shfmt rubocop stylua pipx"
    if ((COMP_CWORD == 1)); then COMPREPLY=($(compgen -W "$cmds" -- "$cur")); return; fi
    case ${COMP_WORDS[1]} in
        install|uninstall|setup) COMPREPLY=($(compgen -W "$exts" -- "$cur")) ;;
        new) ((COMP_CWORD == 3)) && COMPREPLY=($(compgen -W "$exts" -- "$cur")); ((COMP_CWORD == 4)) && COMPREPLY=($(compgen -W "hello guess plot empty" -- "$cur")) ;;
        run|import|gui) COMPREPLY=($(compgen -f -- "$cur")) ;;
    esac
}
complete -F _forge_code_sh code.sh forge-code
COMP
}

main() {
    local cmd="${1:-gui}"
    (($#)) && shift
    case $cmd in
        gui|ui|open)           require_python; cmd_gui "$@" ;;
        setup|init)            cmd_setup "$@" ;;
        doctor|diag)           forge "$WORKSPACE_DEFAULT" --doctor ;;
        list|ls|extensions)    forge --list ;;
        install|add)           (($#)) || die "Quelles extensions ? ex. $SCRIPT_NAME install rust go (liste : $SCRIPT_NAME list)"; forge --install "$@" ;;
        uninstall|remove)      (($#)) || die "Quelles extensions ?"; forge --uninstall "$@" ;;
        new)                   cmd_new "$@" ;;
        run)                   cmd_run "$@" ;;
        export)                forge "$WORKSPACE_DEFAULT" --export "$@" ;;
        import)                [[ -n ${1:-} ]] || die "Indiquez l'archive : $SCRIPT_NAME import projet.zip"; forge --import "$1" "${2:-$WORKSPACE_DEFAULT}" ;;
        snapshot|snap)         [[ -n ${1:-} ]] || die "Indiquez le projet"; forge "$WORKSPACE_DEFAULT" --snapshot "$@" ;;
        completion)            cmd_completion ;;
        version|-V|--version)  cmd_version ;;
        help|-h|--help)        show_usage ;;
        *)                     if [[ -d $cmd ]]; then require_python; cmd_gui "$cmd"; else fail "Commande inconnue : $cmd"; show_usage; exit 1; fi ;;
    esac
}
main "$@"
