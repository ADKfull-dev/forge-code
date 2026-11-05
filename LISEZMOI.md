# Forge Code — atelier de programmation multi-langages

Le petit frère de Forge (Arduino) : même interface, mêmes 12 modes d'apparence, mais pour écrire et exécuter du code dans **n'importe quel langage**. Chaque langage est une **extension** qu'on installe en un clic.

## Démarrer

```bash
chmod +x code.sh
./code.sh setup python javascript     # vérifie Python, ajoute « forge-code » au menu, installe des langages
./code.sh                             # ouvre l'interface (projets dans ~/Code)
```

Seule dépendance : **Python 3.8+** (bibliothèque standard uniquement). L'interface s'ouvre dans Chrome/Chromium en mode application, sinon dans le navigateur par défaut. Tout reste en local (127.0.0.1).

## Ce qu'on peut faire

- **Exécuter** (`Ctrl+Entrée` ou `F5`) : enregistre, compile si besoin, puis lance le programme dans un **vrai terminal** : couleurs, saisie clavier (`input()`, `scanf`, `readLine`…), `Ctrl+C`, `Ctrl+D`. `Relancer` redémarre, `⇧F5` arrête.
- **Vérifier** (`Ctrl+R`) : compilation ou contrôle de syntaxe sans exécuter.
- **Vérification en direct** : pendant la frappe, le code (même non enregistré) est vérifié en arrière-plan avec le compilateur ou le contrôle de syntaxe du langage ; une erreur corrigée disparaît d'elle-même en une seconde environ. Désactivable depuis la palette (`Ctrl+K`). Non disponible pour Kotlin et C# (trop lents).
- **Erreurs dans l'éditeur** : ligne soulignée, pastille dans la marge et dans l'onglet, `F8` pour passer de l'une à l'autre, clic sur une ligne du terminal pour y aller. Reconnaît gcc/clang, rustc, go, javac, Python, Node, Ruby, PHP, Bash, Perl, C#, Zig…
- **Console interactive** (Python, Node, irb, php -a, ghci, jshell, R…) et **Shell** dans le dossier du projet.
- **Traceur** : chaque ligne `nom:valeur` écrite par le programme devient une courbe en direct (export CSV/PNG).
- **Web** : un projet HTML/CSS/JS s'ouvre en aperçu qui se **recharge à chaque Ctrl+S** ; les `console.log` de la page arrivent dans le terminal.
- **Paquets du projet** : pip (dans un `.venv` propre au projet), npm, Cargo, Go modules, RubyGems, Composer, LuaRocks, CRAN, NuGet.
- **Autocomplétion** : mots-clés, fonctions, mots du projet, membres (`std::`, `math.`, `console.`…), en-têtes après `#include <`. **Extraits** : tapez un déclencheur puis `Tab` (`cout` → `std::cout << … << std::endl;`, `cin`, `fori`, `forr`, `main`, `vec`, `inc`, `def`, `log`, `sout`, `pl`…), puis `Tab` / `⇧Tab` pour passer d'un champ à l'autre. `Alt+<` insère ` << ` (` >> ` sur une ligne `cin`), `Alt+>` insère ` >> `. Les `<>` se ferment tout seuls après `#include`, `template` et les types génériques (`vector<`, `List<`, `Vec<`…).
- **Académie** (`F9`, bouton dans la barre latérale) : une page dédiée au parcours du développeur, un grade par langage. **12 paliers, 13 grades** aux noms de métiers (🎒 Stagiaire → 📚 Alternant → ☕ Dev Junior → ⌨️ Développeur → 🔧 Dev Confirmé → 🧱 Dev Senior → 🧭 Tech Lead → 🧠 Staff Engineer → 🏛️ Architecte logiciel → ⚙️ Principal Engineer → 🛰️ Distinguished Engineer → 🚀 CTO → 👑 Légende du code). **120 défis** (9 mini-défis + 1 examen de promotion par palier) qui couvrent les bases, les boucles, les tableaux et chaînes, les fonctions et la récursivité, la robustesse et le débogage (code bogué à corriger), les structures de données, la recherche et le tri, la modélisation et la simulation, les graphes, la programmation dynamique, les bits, encodages et texte, et de vrais projets (parseur JSON, mini-SQL, tableur, machine virtuelle, interpréteur). Corrigés par des **tests cachés** (entrée → sortie, limite de temps, gros tests de performance) : le parcours marche dans tous les langages, avec des solutions de référence en **C, C++, Python, JavaScript et PHP**. Page Carrière (frise des échelons), Compétences (radar par domaine, carte d'activité, statistiques), Succès (24 succès, certificats PNG), cinématique de promotion. Un défi ouvert s'affiche dans l'onglet **🎯 Défi** de l'inspecteur, à côté du code : énoncé, exemples, chrono, indices, solutions, résultats test par test ; **`F6`** pour soumettre. Défis personnels en JSON dans `~/.config/forge-code/challenges/`, progression dans `~/.config/forge-code/progress.json`.
  - Le contenu vit dans le dossier `parcours/` (un fichier par palier). `python3 -m parcours.verifier` compile et exécute toutes les solutions de référence contre leurs tests (mêmes options que Forge Code) et régénère le cache des sorties attendues `parcours/attendus.json.gz`.
- **Formater** (`⇧Alt+F`) et **Analyser** (`⇧Alt+L`) avec les outils installés : Ruff, Black, Prettier, ESLint, clang-format, Cppcheck, gofmt, rustfmt, ShellCheck, shfmt, RuboCop, StyLua.
- **Structure** du fichier (fonctions, classes), **instantanés** git, **export/import .zip**, palette de commandes (`Ctrl+K`), aide (`?`).

## Extensions

Langages fournis : Python, JavaScript, TypeScript, Web, C, C++, Rust, Go, Java, Kotlin, C#, Ruby, PHP, Lua, Bash, Perl, R, Dart, Haskell, Julia, Zig. Outils : Git, Ruff, Black, Prettier, ESLint, clang-format, Cppcheck, gofmt, rustfmt, ShellCheck, shfmt, RuboCop, StyLua, pipx.

L'installation passe par le gestionnaire de paquets du système (APT, DNF, pacman, zypper, apk, Homebrew) ou par un installateur « utilisateur » sans droits administrateur (rustup, Kotlin, Zig, Dart, Julia, pipx, npm). Si le mot de passe administrateur est nécessaire et ne peut pas être demandé dans l'interface, Forge Code affiche la commande à lancer :

```bash
./code.sh list                 # état de toutes les extensions
./code.sh install rust go      # installe depuis le terminal (sudo si besoin)
```

**Votre propre langage** : onglet Extensions › *Extension personnelle…*, ou un fichier JSON dans `~/.config/forge-code/extensions/`. Exemple minimal :

```json
{
  "id": "awk", "name": "AWK", "exts": [".awk"], "main": "main.awk", "bins": ["awk"],
  "run": [{ "needs": ["awk"], "exec": ["awk", "-f", "{main}"] }],
  "comment": "#", "keywords": "BEGIN END print printf if else while for in next exit function",
  "templates": { "hello": "BEGIN { print \"Bonjour !\" }\n" },
  "snippets": { "pr": "print $1", "beg": "BEGIN {\n\t$0\n}" }
}
```

Emplacements disponibles dans les commandes : `{main}` `{stem}` `{out}` `{exe}` `{srcs:.c,.h}` `{bin}` `{python}` `{file}` `{home}` `{name}`.

## En ligne de commande

```bash
./code.sh new Jeu rust guess         # nouveau projet (modèles : hello, guess, plot, empty)
./code.sh run main.py -- --verbose   # exécute un fichier ici même
./code.sh export Jeu -o Jeu.zip      # puis ailleurs : ./code.sh import Jeu.zip
./code.sh snapshot Jeu -m "avant la refonte"
./code.sh doctor
source <(./code.sh completion)
```

## Fichiers

- `<projet>/.forge.json` : langage, fichier principal, arguments, entrée préremplie.
- `~/.config/forge-code/` : extensions désactivées et extensions personnelles.
- `~/.cache/forge-code/` : compilations (les projets restent propres).
