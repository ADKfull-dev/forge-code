#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Forge Code — atelier de programmation multi-langages.

    python3 forge-code.py [dossier_des_projets] [--port 8724] [--no-browser]

Sans interface (utilisé par « code.sh ») :
    python3 forge-code.py --list                       extensions et leur état
    python3 forge-code.py --install ID [ID…]           installe des extensions (langages, outils)
    python3 forge-code.py --run FICHIER [-- args…]     exécute un fichier dans le terminal
    python3 forge-code.py --export PROJET [-o fichier.zip]
    python3 forge-code.py --import fichier.zip [dossier_des_projets]
    python3 forge-code.py --snapshot PROJET [-m "description"]

Serveur local (127.0.0.1 uniquement), bibliothèque standard Python 3.8+,
aucune dépendance. L'interface s'ouvre dans le navigateur.
"""
import argparse
import codecs
import fcntl
import io
import json
import os
import platform
import pty
import queue
import re
import secrets
import select
import shlex
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
import webbrowser
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

VERSION = "1.0.0"
HOME = Path.home()
TOKEN = secrets.token_urlsafe(24)
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "forge-code"
CACHE = Path(os.environ.get("XDG_CACHE_HOME", HOME / ".cache")) / "forge-code"
META_FILE = CACHE / "meta.json"
EXT_STATE = CONFIG / "extensions.json"       # extensions désactivées
EXT_DIR = CONFIG / "extensions"              # extensions personnelles (*.json)
CONF_FILE = ".forge.json"                    # réglages d'un projet : langage, fichier principal, exécution, instantanés
CONF_SECTIONS = {"lang", "main", "run", "snapshots"}
IGNORED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "target", "build", "dist", "bin", "obj",
                ".idea", ".vscode", ".mypy_cache", ".pytest_cache", ".ruff_cache", "zig-cache", ".zig-cache", ".dart_tool", ".gradle"}
MAX_FILES = 800
MAX_EDIT = 2 * 1024 * 1024

# outils installés « pour l'utilisateur » : rendus visibles même si le PATH de la session ne les contient pas
for extra in (HOME / ".local/bin", HOME / ".cargo/bin", HOME / "go/bin", HOME / ".deno/bin", HOME / ".bun/bin",
              HOME / ".dotnet", HOME / ".dotnet/tools", HOME / ".juliaup/bin", HOME / ".ghcup/bin", HOME / ".luarocks/bin",
              Path("/usr/local/go/bin"), Path("/snap/bin")):
    if str(extra) not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + str(extra)
try:                                          # gemmes installées avec --user-install
    for d in (HOME / ".local/share/gem/ruby").glob("*/bin"):
        os.environ["PATH"] += os.pathsep + str(d)
except OSError:
    pass
GIT = shutil.which("git")

# --------------------------------------------------------------------------- catalogue des extensions
# Une extension « lang » apporte un langage : comment l'exécuter, le vérifier, ouvrir sa console
# interactive (REPL), l'installer, et des modèles de départ. Une extension « tool » ajoute un outil
# (formateur, analyseur…) à un ou plusieurs langages.
#
# Emplacements dans les commandes :
#   {main}  fichier à exécuter (relatif au projet)     {stem}  son nom sans extension
#   {out}   dossier de compilation (hors du projet)    {exe}   {out}/{stem}
#   {srcs:.c,.h}  tous les fichiers du projet ayant ces extensions
#   {bin}   premier exécutable trouvé parmi « bins »   {python}  .venv/bin/python du projet, sinon python3
#   {file}  fichier ouvert (formateurs, analyseurs)     {home}  dossier personnel      {name}  nom du projet
# « needs » : exécutables requis (« a|b » = l'un ou l'autre ; « node@22.6 » = version minimale).
# « when »  : fichier qui doit exister dans le projet pour que cette variante s'applique.

PM_NAMES = {"apt": "APT (Debian, Ubuntu)", "dnf": "DNF (Fedora)", "pacman": "pacman (Arch)",
            "zypper": "zypper (openSUSE)", "apk": "apk (Alpine)", "brew": "Homebrew"}

T_PLOT_NOTE = "Traceur : chaque ligne « nom:valeur » devient une courbe (onglet Traceur)."

CATALOG = [
    # ================================================================== langages
    {
        "id": "python", "kind": "lang", "name": "Python", "abbr": "PY", "color": 4,
        "desc": "Scripts, données, automatisation. Paquets pip dans un .venv propre au projet.",
        "exts": [".py", ".pyw"], "main": "main.py", "bins": ["python3", "python"],
        "version": ["{bin}", "--version"],
        "run": [{"needs": ["python3|python"], "exec": ["{python}", "{main}"]}],
        "check": [{"needs": ["python3|python"], "build": [["{python}", "-m", "py_compile", "{main}"]]}],
        "repl": [{"needs": ["python3|python"], "exec": ["{python}", "-q"]}],
        "install": [{"pm": {"apt": ["python3", "python3-venv", "python3-pip"], "dnf": ["python3", "python3-pip"], "pacman": ["python", "python-pip"],
                            "zypper": ["python3", "python3-pip"], "apk": ["python3", "py3-pip"], "brew": ["python"]}}],
        "pkg": "pip", "comment": "#", "indent": 4,
        "templates": {
            "hello": '''# {name}
# Un premier programme : il pose une question et répond.

def saluer(nom: str) -> str:
    return f"Bonjour {nom} !"


if __name__ == "__main__":
    nom = input("Comment vous appelez-vous ? ")
    print(saluer(nom or "inconnu"))
    for i in range(1, 4):
        print(f"{i} × 7 = {i * 7}")
''',
            "plot": '''# {name}
# Envoie des mesures « nom:valeur » : ouvrez l'onglet Traceur.
import math
import random
import time

t = 0.0
for _ in range(400):
    sinus = math.sin(t) * 100
    cosinus = math.cos(t * 0.5) * 60
    bruit = random.uniform(-20, 20)
    print(f"sinus:{sinus:.2f},cosinus:{cosinus:.2f},bruit:{bruit:.2f}")
    t += 0.08
    time.sleep(0.03)
''',
            "guess": '''# {name}
# Jeu : devinez le nombre (1 à 100). Tapez vos réponses dans le terminal.
import random

secret = random.randint(1, 100)
essais = 0
print("J'ai choisi un nombre entre 1 et 100.")
while True:
    texte = input("Votre proposition : ")
    if not texte.strip().isdigit():
        print("Un nombre, s'il vous plaît.")
        continue
    n = int(texte)
    essais += 1
    if n < secret:
        print("C'est plus !")
    elif n > secret:
        print("C'est moins !")
    else:
        print(f"Bravo, trouvé en {essais} essai(s) !")
        break
''',
            "empty": "# {name}\n\n",
        },
    },
    {
        "id": "javascript", "kind": "lang", "name": "JavaScript", "abbr": "JS", "color": 7,
        "desc": "Node.js : scripts, serveurs, outils. Paquets npm dans le projet.",
        "exts": [".js", ".mjs", ".cjs"], "main": "main.js", "bins": ["node", "nodejs"],
        "version": ["{bin}", "--version"],
        "run": [{"needs": ["node|nodejs"], "exec": ["{bin}", "{main}"]}],
        "check": [{"needs": ["node|nodejs"], "build": [["{bin}", "--check", "{main}"]]}],
        "repl": [{"needs": ["node|nodejs"], "exec": ["{bin}"], "env": {"NODE_NO_READLINE": "1"}}],
        "install": [{"pm": {"apt": ["nodejs", "npm"], "dnf": ["nodejs", "npm"], "pacman": ["nodejs", "npm"], "zypper": ["nodejs", "npm"], "apk": ["nodejs", "npm"], "brew": ["node"]}}],
        "pkg": "npm", "comment": "//", "indent": 2,
        "templates": {
            "hello": '''// {name}
// Un premier programme : il pose une question et répond.
const readline = require("node:readline/promises");

async function main() {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const nom = await rl.question("Comment vous appelez-vous ? ");
  console.log(`Bonjour ${nom || "inconnu"} !`);
  for (let i = 1; i <= 3; i++) console.log(`${i} × 7 = ${i * 7}`);
  rl.close();
}

main();
''',
            "plot": '''// {name}
// Envoie des mesures « nom:valeur » : ouvrez l'onglet Traceur.
let t = 0, n = 0;
const timer = setInterval(() => {
  const sinus = Math.sin(t) * 100;
  const cosinus = Math.cos(t * 0.5) * 60;
  const bruit = Math.random() * 40 - 20;
  console.log(`sinus:${sinus.toFixed(2)},cosinus:${cosinus.toFixed(2)},bruit:${bruit.toFixed(2)}`);
  t += 0.08;
  if (++n >= 400) clearInterval(timer);
}, 30);
''',
            "guess": '''// {name}
// Jeu : devinez le nombre (1 à 100).
const readline = require("node:readline");

const secret = 1 + Math.floor(Math.random() * 100);
let essais = 0;
const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
console.log("J'ai choisi un nombre entre 1 et 100.");
rl.setPrompt("Votre proposition : ");
rl.prompt();
rl.on("line", ligne => {
  const n = parseInt(ligne, 10);
  if (Number.isNaN(n)) console.log("Un nombre, s'il vous plaît.");
  else if (++essais && n < secret) console.log("C'est plus !");
  else if (n > secret) console.log("C'est moins !");
  else { console.log(`Bravo, trouvé en ${essais} essai(s) !`); return rl.close(); }
  rl.prompt();
});
''',
            "empty": "// {name}\n\n",
        },
    },
    {
        "id": "typescript", "kind": "lang", "name": "TypeScript", "abbr": "TS", "color": 4,
        "desc": "JavaScript typé. Exécuté par Deno, tsx, Bun ou Node 22.6+ (types retirés à la volée).",
        "exts": [".ts", ".mts", ".cts"], "main": "main.ts", "bins": ["deno", "tsx", "bun", "node"],
        "version": ["{bin}", "--version"],
        "run": [{"needs": ["deno"], "exec": ["deno", "run", "-A", "{main}"]},
                {"needs": ["tsx"], "exec": ["tsx", "{main}"]},
                {"needs": ["bun"], "exec": ["bun", "run", "{main}"]},
                {"needs": ["node@22.6"], "exec": ["node", "--experimental-strip-types", "--no-warnings", "{main}"]}],
        "check": [{"needs": ["tsc"], "build": [["tsc", "--noEmit", "--strict", "--target", "es2022", "--module", "nodenext", "--skipLibCheck", "{main}"]]},
                  {"needs": ["deno"], "build": [["deno", "check", "{main}"]]}],
        "repl": [{"needs": ["deno"], "exec": ["deno"]}, {"needs": ["tsx"], "exec": ["tsx"]}],
        "install": [{"needs": ["npm"], "cmd": ["npm", "install", "-g", "--prefix", "{home}/.local", "tsx", "typescript"],
                     "remove": ["npm", "uninstall", "-g", "--prefix", "{home}/.local", "tsx", "typescript"]},
                    {"needs": ["curl"], "sh": "curl -fsSL https://deno.land/install.sh | sh -s -- -y"}],
        "pkg": "npm", "comment": "//", "indent": 2,
        "templates": {
            "hello": '''// {name}
// Un premier programme typé.
interface Personne {
  nom: string;
  age: number;
}

function presenter(p: Personne): string {
  return `${p.nom} a ${p.age} ans`;
}

const gens: Personne[] = [{ nom: "Ada", age: 36 }, { nom: "Alan", age: 41 }];
gens.forEach(p => console.log(presenter(p)));
''',
            "plot": '''// {name}
// Envoie des mesures « nom:valeur » : ouvrez l'onglet Traceur.
let t: number = 0;
let n: number = 0;
const timer = setInterval(() => {
  const sinus: number = Math.sin(t) * 100;
  const cosinus: number = Math.cos(t * 0.5) * 60;
  console.log(`sinus:${sinus.toFixed(2)},cosinus:${cosinus.toFixed(2)}`);
  t += 0.08;
  if (++n >= 400) clearInterval(timer);
}, 30);
''',
            "empty": "// {name}\n\n",
        },
    },
    {
        "id": "web", "kind": "lang", "name": "Web (HTML/CSS/JS)", "abbr": "WEB", "color": 8,
        "desc": "Page web avec aperçu en direct : la page se recharge à chaque enregistrement.",
        "exts": [".html", ".htm", ".css"], "main": "index.html", "bins": [],
        "run": [{"needs": [], "preview": True}], "check": [], "repl": [],
        "install": [], "comment": "<!--", "indent": 2, "builtin": True,
        "templates": {
            "hello": {
                "index.html": '''<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{name}</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <main>
    <h1>{name}</h1>
    <p>Modifiez <code>index.html</code>, <code>style.css</code> ou <code>script.js</code> puis enregistrez : l'aperçu se recharge tout seul.</p>
    <button id="btn">Cliquez-moi</button>
    <p id="out"></p>
  </main>
  <script src="script.js"></script>
</body>
</html>
''',
                "style.css": '''body {
  font-family: system-ui, sans-serif;
  display: grid;
  place-items: center;
  min-height: 100vh;
  margin: 0;
  background: linear-gradient(135deg, #0f766e, #4338ca);
  color: #fff;
}

main {
  max-width: 520px;
  padding: 32px;
  border-radius: 18px;
  background: rgba(255, 255, 255, .12);
}

button {
  font: inherit;
  padding: 10px 18px;
  border: 0;
  border-radius: 10px;
  cursor: pointer;
}
''',
                "script.js": '''let clics = 0;
document.getElementById("btn").addEventListener("click", () => {
  clics++;
  document.getElementById("out").textContent = `Cliqué ${clics} fois`;
  console.log("clic", clics);
});
''',
            },
            "empty": {"index.html": "<!doctype html>\n<html lang=\"fr\">\n<head>\n  <meta charset=\"utf-8\">\n  <title>{name}</title>\n</head>\n<body>\n\n</body>\n</html>\n"},
        },
    },
    {
        "id": "c", "kind": "lang", "name": "C", "abbr": "C", "color": 1,
        "desc": "Compilé avec gcc ou clang (tous les .c du projet), avertissements activés.",
        "exts": [".c", ".h"], "main": "main.c", "bins": ["gcc", "clang", "cc"],
        "version": ["{bin}", "--version"],
        "run": [{"needs": ["gcc|clang|cc"], "build": [["{bin}", "-std=c17", "-Wall", "-Wextra", "-g", "{srcs:.c}", "-o", "{exe}", "-lm"]], "exec": ["{exe}"]}],
        "check": [{"needs": ["gcc|clang|cc"], "build": [["{bin}", "-std=c17", "-Wall", "-Wextra", "-fsyntax-only", "{srcs:.c}"]]}],
        "repl": [],
        "install": [{"pm": {"apt": ["build-essential", "gdb"], "dnf": ["gcc", "make", "gdb"], "pacman": ["base-devel", "gdb"], "zypper": ["gcc", "make", "gdb"], "apk": ["build-base"], "brew": ["gcc"]}}],
        "comment": "//", "indent": 4,
        "templates": {
            "hello": '''// {name}
#include <stdio.h>
#include <string.h>

int main(void) {
    char nom[64] = "";
    printf("Comment vous appelez-vous ? ");
    fflush(stdout);
    if (fgets(nom, sizeof nom, stdin)) nom[strcspn(nom, "\\n")] = '\\0';
    printf("Bonjour %s !\\n", nom[0] ? nom : "inconnu");
    for (int i = 1; i <= 3; i++) printf("%d x 7 = %d\\n", i, i * 7);
    return 0;
}
''',
            "plot": '''// {name}
// Envoie des mesures « nom:valeur » : ouvrez l'onglet Traceur.
#include <math.h>
#include <stdio.h>
#include <time.h>

int main(void) {
    struct timespec pause = {0, 30 * 1000000L};
    double t = 0;
    for (int i = 0; i < 400; i++) {
        printf("sinus:%.2f,cosinus:%.2f\\n", sin(t) * 100, cos(t * 0.5) * 60);
        fflush(stdout);
        t += 0.08;
        nanosleep(&pause, NULL);
    }
    return 0;
}
''',
            "guess": '''// {name}
// Jeu : devinez le nombre (1 à 100).
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

int main(void) {
    srand((unsigned) time(NULL));
    int secret = rand() % 100 + 1, essais = 0, n;
    puts("J'ai choisi un nombre entre 1 et 100.");
    for (;;) {
        printf("Votre proposition : ");
        fflush(stdout);
        if (scanf("%d", &n) != 1) {
            int c;
            while ((c = getchar()) != '\\n' && c != EOF) {}
            if (c == EOF) return 0;
            puts("Un nombre, s'il vous plaît.");
            continue;
        }
        essais++;
        if (n < secret) puts("C'est plus !");
        else if (n > secret) puts("C'est moins !");
        else { printf("Bravo, trouvé en %d essai(s) !\\n", essais); return 0; }
    }
}
''',
            "empty": "// {name}\n#include <stdio.h>\n\nint main(void) {\n    return 0;\n}\n",
        },
    },
    {
        "id": "cpp", "kind": "lang", "name": "C++", "abbr": "C++", "color": 3,
        "desc": "Compilé avec g++ ou clang++ en C++20 (tous les .cpp du projet).",
        "exts": [".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"], "main": "main.cpp", "bins": ["g++", "clang++", "c++"],
        "version": ["{bin}", "--version"],
        "run": [{"needs": ["g++|clang++|c++"], "build": [["{bin}", "-std=c++20", "-Wall", "-Wextra", "-g", "{srcs:.cpp,.cc,.cxx}", "-o", "{exe}"]], "exec": ["{exe}"]}],
        "check": [{"needs": ["g++|clang++|c++"], "build": [["{bin}", "-std=c++20", "-Wall", "-Wextra", "-fsyntax-only", "{srcs:.cpp,.cc,.cxx}"]]}],
        "repl": [],
        "install": [{"pm": {"apt": ["build-essential", "gdb"], "dnf": ["gcc-c++", "make", "gdb"], "pacman": ["base-devel", "gdb"], "zypper": ["gcc-c++", "make"], "apk": ["build-base"], "brew": ["gcc"]}}],
        "comment": "//", "indent": 4,
        "templates": {
            "hello": '''// {name}
#include <iostream>
#include <string>
#include <vector>

int main() {
    std::string nom;
    std::cout << "Comment vous appelez-vous ? " << std::flush;
    std::getline(std::cin, nom);
    std::cout << "Bonjour " << (nom.empty() ? "inconnu" : nom) << " !\\n";

    std::vector<int> nombres{3, 1, 4, 1, 5, 9, 2, 6};
    int somme = 0;
    for (int n : nombres) somme += n;
    std::cout << "Somme : " << somme << "\\n";
    return 0;
}
''',
            "plot": '''// {name}
// Envoie des mesures « nom:valeur » : ouvrez l'onglet Traceur.
#include <chrono>
#include <cmath>
#include <iostream>
#include <thread>

int main() {
    double t = 0;
    for (int i = 0; i < 400; ++i) {
        std::cout << "sinus:" << std::sin(t) * 100 << ",cosinus:" << std::cos(t * 0.5) * 60 << std::endl;
        t += 0.08;
        std::this_thread::sleep_for(std::chrono::milliseconds(30));
    }
}
''',
            "guess": '''// {name}
// Jeu : devinez le nombre (1 à 100).
#include <iostream>
#include <random>

int main() {
    std::mt19937 gen{std::random_device{}()};
    int secret = std::uniform_int_distribution<>(1, 100)(gen), essais = 0, n;
    std::cout << "J'ai choisi un nombre entre 1 et 100.\\n";
    while (std::cout << "Votre proposition : " << std::flush && std::cin >> n) {
        ++essais;
        if (n < secret) std::cout << "C'est plus !\\n";
        else if (n > secret) std::cout << "C'est moins !\\n";
        else { std::cout << "Bravo, trouvé en " << essais << " essai(s) !\\n"; break; }
    }
}
''',
            "empty": "// {name}\n#include <iostream>\n\nint main() {\n    return 0;\n}\n",
        },
    },
    {
        "id": "rust", "kind": "lang", "name": "Rust", "abbr": "RS", "color": 8,
        "desc": "rustc pour un fichier seul, Cargo dès qu'il y a un Cargo.toml (paquets crates.io).",
        "exts": [".rs"], "main": "main.rs", "bins": ["rustc", "cargo"],
        "version": ["rustc", "--version"],
        "run": [{"needs": ["cargo"], "when": "Cargo.toml", "exec": ["cargo", "run", "-q"], "env": {"CARGO_TARGET_DIR": "{out}/cargo"}},
                {"needs": ["rustc"], "build": [["rustc", "--edition", "2021", "-g", "{main}", "-o", "{exe}"]], "exec": ["{exe}"]}],
        "check": [{"needs": ["cargo"], "when": "Cargo.toml", "build": [["cargo", "check", "-q"]], "env": {"CARGO_TARGET_DIR": "{out}/cargo"}},
                  {"needs": ["rustc"], "build": [["rustc", "--edition", "2021", "--emit=metadata", "-o", "{out}/check.rmeta", "{main}"]]}],
        "repl": [{"needs": ["evcxr"], "exec": ["evcxr"]}],
        "install": [{"needs": ["curl"], "sh": "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal -c rustfmt"},
                    {"pm": {"apt": ["rustc", "cargo"], "dnf": ["rust", "cargo"], "pacman": ["rust"], "zypper": ["rust", "cargo"], "apk": ["rust", "cargo"], "brew": ["rust"]}}],
        "pkg": "cargo", "comment": "//", "indent": 4,
        "templates": {
            "hello": '''// {name}
use std::io::{self, Write};

fn saluer(nom: &str) -> String {
    format!("Bonjour {} !", nom)
}

fn main() {
    print!("Comment vous appelez-vous ? ");
    io::stdout().flush().unwrap();
    let mut nom = String::new();
    io::stdin().read_line(&mut nom).unwrap();
    let nom = nom.trim();
    println!("{}", saluer(if nom.is_empty() { "inconnu" } else { nom }));
    for i in 1..=3 {
        println!("{} × 7 = {}", i, i * 7);
    }
}
''',
            "plot": '''// {name}
// Envoie des mesures « nom:valeur » : ouvrez l'onglet Traceur.
use std::{thread, time::Duration};

fn main() {
    let mut t: f64 = 0.0;
    for _ in 0..400 {
        println!("sinus:{:.2},cosinus:{:.2}", t.sin() * 100.0, (t * 0.5).cos() * 60.0);
        t += 0.08;
        thread::sleep(Duration::from_millis(30));
    }
}
''',
            "guess": '''// {name}
// Jeu : devinez le nombre (1 à 100).
use std::io::{self, BufRead, Write};
use std::time::{SystemTime, UNIX_EPOCH};

fn main() {
    let graine = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().subsec_nanos();
    let secret = graine % 100 + 1;
    let mut essais = 0;
    println!("J'ai choisi un nombre entre 1 et 100.");
    let stdin = io::stdin();
    loop {
        print!("Votre proposition : ");
        io::stdout().flush().unwrap();
        let mut ligne = String::new();
        if stdin.lock().read_line(&mut ligne).unwrap() == 0 { break; }
        let n: u32 = match ligne.trim().parse() {
            Ok(n) => n,
            Err(_) => { println!("Un nombre, s'il vous plaît."); continue; }
        };
        essais += 1;
        if n < secret { println!("C'est plus !"); }
        else if n > secret { println!("C'est moins !"); }
        else { println!("Bravo, trouvé en {} essai(s) !", essais); break; }
    }
}
''',
            "empty": "// {name}\n\nfn main() {\n}\n",
        },
    },
    {
        "id": "go", "kind": "lang", "name": "Go", "abbr": "GO", "color": 0,
        "desc": "go run sur les fichiers du projet ; go.mod créé à l'ajout du premier paquet.",
        "exts": [".go"], "main": "main.go", "bins": ["go"],
        "version": ["go", "version"],
        "run": [{"needs": ["go"], "when": "go.mod", "exec": ["go", "run", "."]},
                {"needs": ["go"], "exec": ["go", "run", "{srcs:.go}"]}],
        "check": [{"needs": ["go"], "when": "go.mod", "build": [["go", "vet", "."]]},
                  {"needs": ["go"], "build": [["go", "vet", "{srcs:.go}"]]}],
        "repl": [],
        "install": [{"pm": {"apt": ["golang-go"], "dnf": ["golang"], "pacman": ["go"], "zypper": ["go"], "apk": ["go"], "brew": ["go"]}}],
        "pkg": "go", "comment": "//", "indent": 4,
        "templates": {
            "hello": '''// {name}
package main

import (
	"bufio"
	"fmt"
	"os"
	"strings"
)

func main() {
	fmt.Print("Comment vous appelez-vous ? ")
	nom, _ := bufio.NewReader(os.Stdin).ReadString('\\n')
	nom = strings.TrimSpace(nom)
	if nom == "" {
		nom = "inconnu"
	}
	fmt.Printf("Bonjour %s !\\n", nom)
	for i := 1; i <= 3; i++ {
		fmt.Printf("%d × 7 = %d\\n", i, i*7)
	}
}
''',
            "plot": '''// {name}
// Envoie des mesures « nom:valeur » : ouvrez l'onglet Traceur.
package main

import (
	"fmt"
	"math"
	"time"
)

func main() {
	t := 0.0
	for i := 0; i < 400; i++ {
		fmt.Printf("sinus:%.2f,cosinus:%.2f\\n", math.Sin(t)*100, math.Cos(t*0.5)*60)
		t += 0.08
		time.Sleep(30 * time.Millisecond)
	}
}
''',
            "guess": '''// {name}
// Jeu : devinez le nombre (1 à 100).
package main

import (
	"bufio"
	"fmt"
	"math/rand"
	"os"
	"strconv"
	"strings"
)

func main() {
	secret, essais := rand.Intn(100)+1, 0
	sc := bufio.NewScanner(os.Stdin)
	fmt.Println("J'ai choisi un nombre entre 1 et 100.")
	for fmt.Print("Votre proposition : "); sc.Scan(); fmt.Print("Votre proposition : ") {
		n, err := strconv.Atoi(strings.TrimSpace(sc.Text()))
		if err != nil {
			fmt.Println("Un nombre, s'il vous plaît.")
			continue
		}
		essais++
		switch {
		case n < secret:
			fmt.Println("C'est plus !")
		case n > secret:
			fmt.Println("C'est moins !")
		default:
			fmt.Printf("Bravo, trouvé en %d essai(s) !\\n", essais)
			return
		}
	}
}
''',
            "empty": "// {name}\npackage main\n\nfunc main() {\n}\n",
        },
    },
    {
        "id": "java", "kind": "lang", "name": "Java", "abbr": "JAVA", "color": 2,
        "desc": "javac puis java ; la classe principale porte le nom du fichier principal.",
        "exts": [".java"], "main": "Main.java", "bins": ["javac", "java"],
        "version": ["javac", "-version"],
        "run": [{"needs": ["javac", "java"], "build": [["javac", "-encoding", "UTF-8", "-Xlint:all", "-d", "{out}/classes", "{srcs:.java}"]],
                 "exec": ["java", "-Dfile.encoding=UTF-8", "-cp", "{out}/classes", "{stem}"]}],
        "check": [{"needs": ["javac"], "build": [["javac", "-encoding", "UTF-8", "-Xlint:all", "-d", "{out}/classes", "{srcs:.java}"]]}],
        "repl": [{"needs": ["jshell"], "exec": ["jshell"]}],
        "install": [{"pm": {"apt": ["default-jdk"], "dnf": ["java-latest-openjdk-devel"], "pacman": ["jdk-openjdk"], "zypper": ["java-21-openjdk-devel"], "apk": ["openjdk21"], "brew": ["openjdk"]}}],
        "comment": "//", "indent": 4,
        "templates": {
            "hello": '''// {name}
import java.util.Scanner;

public class Main {
    static String saluer(String nom) {
        return "Bonjour " + nom + " !";
    }

    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        System.out.print("Comment vous appelez-vous ? ");
        String nom = in.hasNextLine() ? in.nextLine().trim() : "";
        System.out.println(saluer(nom.isEmpty() ? "inconnu" : nom));
        for (int i = 1; i <= 3; i++) {
            System.out.printf("%d × 7 = %d%n", i, i * 7);
        }
    }
}
''',
            "plot": '''// {name}
// Envoie des mesures « nom:valeur » : ouvrez l'onglet Traceur.
public class Main {
    public static void main(String[] args) throws InterruptedException {
        double t = 0;
        for (int i = 0; i < 400; i++) {
            System.out.printf(java.util.Locale.ROOT, "sinus:%.2f,cosinus:%.2f%n", Math.sin(t) * 100, Math.cos(t * 0.5) * 60);
            t += 0.08;
            Thread.sleep(30);
        }
    }
}
''',
            "guess": '''// {name}
// Jeu : devinez le nombre (1 à 100).
import java.util.Random;
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        int secret = new Random().nextInt(100) + 1, essais = 0;
        Scanner in = new Scanner(System.in);
        System.out.println("J'ai choisi un nombre entre 1 et 100.");
        while (true) {
            System.out.print("Votre proposition : ");
            if (!in.hasNextLine()) return;
            int n;
            try { n = Integer.parseInt(in.nextLine().trim()); }
            catch (NumberFormatException e) { System.out.println("Un nombre, s'il vous plaît."); continue; }
            essais++;
            if (n < secret) System.out.println("C'est plus !");
            else if (n > secret) System.out.println("C'est moins !");
            else { System.out.println("Bravo, trouvé en " + essais + " essai(s) !"); return; }
        }
    }
}
''',
            "empty": "// {name}\npublic class Main {\n    public static void main(String[] args) {\n    }\n}\n",
        },
    },
    {
        "id": "kotlin", "kind": "lang", "name": "Kotlin", "abbr": "KT", "color": 1,
        "desc": "kotlinc produit un .jar autonome, lancé par java.",
        "exts": [".kt", ".kts"], "main": "Main.kt", "bins": ["kotlinc"],
        "version": ["kotlinc", "-version"],
        "run": [{"needs": ["kotlinc", "java"], "build": [["kotlinc", "{srcs:.kt}", "-include-runtime", "-d", "{out}/app.jar"]], "exec": ["java", "-jar", "{out}/app.jar"]}],
        "check": [{"needs": ["kotlinc"], "build": [["kotlinc", "{srcs:.kt}", "-d", "{out}/check"]]}],
        "repl": [],
        "install": [{"pm": {"pacman": ["kotlin"], "brew": ["kotlin"], "apk": ["kotlin"]}},
                    {"needs": ["curl", "unzip", "java"], "sh": "V=2.1.20 && curl -fSL --progress-bar -o /tmp/kotlinc.zip https://github.com/JetBrains/kotlin/releases/download/v$V/kotlin-compiler-$V.zip && mkdir -p \"$HOME/.local/share\" \"$HOME/.local/bin\" && rm -rf \"$HOME/.local/share/kotlinc\" && unzip -q /tmp/kotlinc.zip -d \"$HOME/.local/share\" && rm /tmp/kotlinc.zip && ln -sf \"$HOME/.local/share/kotlinc/bin/kotlinc\" \"$HOME/.local/share/kotlinc/bin/kotlin\" \"$HOME/.local/bin/\""},
                    {"needs": ["sdk"], "cmd": ["sdk", "install", "kotlin"]},
                    {"needs": ["snap"], "root": True, "cmd": ["snap", "install", "--classic", "kotlin"]}],
        "comment": "//", "indent": 4,
        "templates": {
            "hello": '''// {name}
fun saluer(nom: String) = "Bonjour $nom !"

fun main() {
    print("Comment vous appelez-vous ? ")
    val nom = readlnOrNull()?.trim().orEmpty()
    println(saluer(nom.ifEmpty { "inconnu" }))
    (1..3).forEach { println("$it × 7 = ${it * 7}") }
}
''',
            "empty": "// {name}\nfun main() {\n}\n",
        },
    },
    {
        "id": "csharp", "kind": "lang", "name": "C#", "abbr": "C#", "color": 5,
        "desc": "SDK .NET : dotnet run sur le projet (.csproj créé avec le modèle).",
        "exts": [".cs", ".csproj"], "main": "Program.cs", "bins": ["dotnet"],
        "version": ["dotnet", "--version"],
        "run": [{"needs": ["dotnet"], "exec": ["dotnet", "run", "--nologo", "-v", "q"], "env": {"DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"}}],
        "check": [{"needs": ["dotnet"], "build": [["dotnet", "build", "--nologo", "-v", "q", "-clp:NoSummary"]], "env": {"DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"}}],
        "repl": [{"needs": ["csharprepl"], "exec": ["csharprepl"]}],
        "install": [{"pm": {"apt": ["dotnet-sdk-8.0"], "dnf": ["dotnet-sdk-8.0"], "pacman": ["dotnet-sdk"], "brew": ["dotnet"]}},
                    {"needs": ["curl"], "sh": "curl -fsSL https://dot.net/v1/dotnet-install.sh | bash -s -- --channel LTS --install-dir \"$HOME/.dotnet\" && mkdir -p \"$HOME/.local/bin\" && ln -sf \"$HOME/.dotnet/dotnet\" \"$HOME/.local/bin/dotnet\""}],
        "pkg": "dotnet", "comment": "//", "indent": 4,
        "templates": {
            "hello": {
                "Program.cs": '''// {name}
Console.Write("Comment vous appelez-vous ? ");
var nom = Console.ReadLine()?.Trim();
Console.WriteLine($"Bonjour {(string.IsNullOrEmpty(nom) ? "inconnu" : nom)} !");
for (var i = 1; i <= 3; i++)
    Console.WriteLine($"{i} × 7 = {i * 7}");
''',
                "{name}.csproj": '''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>
</Project>
''',
            },
        },
    },
    {
        "id": "ruby", "kind": "lang", "name": "Ruby", "abbr": "RB", "color": 3,
        "desc": "Scripts Ruby ; console interactive irb ; gemmes installées pour l'utilisateur.",
        "exts": [".rb"], "main": "main.rb", "bins": ["ruby"],
        "version": ["ruby", "--version"],
        "run": [{"needs": ["ruby"], "exec": ["ruby", "{main}"]}],
        "check": [{"needs": ["ruby"], "build": [["ruby", "-wc", "{main}"]]}],
        "repl": [{"needs": ["irb"], "exec": ["irb", "--simple-prompt", "--nocolorize", "--noreadline"]}],
        "install": [{"pm": {"apt": ["ruby-full"], "dnf": ["ruby", "ruby-devel"], "pacman": ["ruby"], "zypper": ["ruby"], "apk": ["ruby"], "brew": ["ruby"]}}],
        "pkg": "gem", "comment": "#", "indent": 2,
        "templates": {
            "hello": '''# {name}
def saluer(nom)
  "Bonjour #{nom} !"
end

print "Comment vous appelez-vous ? "
nom = ($stdin.gets || "").strip
puts saluer(nom.empty? ? "inconnu" : nom)
(1..3).each { |i| puts "#{i} × 7 = #{i * 7}" }
''',
            "plot": '''# {name}
# Envoie des mesures « nom:valeur » : ouvrez l'onglet Traceur.
$stdout.sync = true
t = 0.0
400.times do
  puts format("sinus:%.2f,cosinus:%.2f", Math.sin(t) * 100, Math.cos(t * 0.5) * 60)
  t += 0.08
  sleep 0.03
end
''',
            "empty": "# {name}\n\n",
        },
    },
    {
        "id": "php", "kind": "lang", "name": "PHP", "abbr": "PHP", "color": 5,
        "desc": "PHP en ligne de commande ; console php -a ; paquets Composer.",
        "exts": [".php"], "main": "main.php", "bins": ["php"],
        "version": ["php", "--version"],
        "run": [{"needs": ["php"], "exec": ["php", "{main}"]}],
        "check": [{"needs": ["php"], "build": [["php", "-l", "{main}"]]}],
        "repl": [{"needs": ["php"], "exec": ["php", "-a"]}],
        "install": [{"pm": {"apt": ["php-cli"], "dnf": ["php-cli"], "pacman": ["php"], "zypper": ["php8"], "apk": ["php"], "brew": ["php"]}}],
        "pkg": "composer", "comment": "//", "indent": 4,
        "templates": {
            "hello": '''<?php
// {name}

function saluer(string $nom): string {
    return "Bonjour $nom !";
}

echo "Comment vous appelez-vous ? ";
$nom = trim(fgets(STDIN) ?: "");
echo saluer($nom !== "" ? $nom : "inconnu"), PHP_EOL;
foreach (range(1, 3) as $i) {
    echo "$i × 7 = ", $i * 7, PHP_EOL;
}
''',
            "empty": "<?php\n// {name}\n\n",
        },
    },
    {
        "id": "lua", "kind": "lang", "name": "Lua", "abbr": "LUA", "color": 4,
        "desc": "Langage léger (Lua 5.x ou LuaJIT), console lua -i.",
        "exts": [".lua"], "main": "main.lua", "bins": ["lua", "lua5.4", "lua5.3", "luajit"],
        "version": ["{bin}", "-v"],
        "run": [{"needs": ["lua|lua5.4|lua5.3|luajit"], "exec": ["{bin}", "{main}"]}],
        "check": [{"needs": ["luac|luac5.4|luac5.3"], "build": [["{luac}", "-p", "{main}"]]}],
        "repl": [{"needs": ["lua|lua5.4|lua5.3|luajit"], "exec": ["{bin}", "-i"]}],
        "install": [{"pm": {"apt": ["lua5.4"], "dnf": ["lua"], "pacman": ["lua"], "zypper": ["lua54"], "apk": ["lua5.4"], "brew": ["lua"]}}],
        "pkg": "luarocks", "comment": "--", "indent": 2,
        "templates": {
            "hello": '''-- {name}
local function saluer(nom)
  return "Bonjour " .. nom .. " !"
end

io.write("Comment vous appelez-vous ? ")
io.flush()
local nom = (io.read("l") or ""):match("^%s*(.-)%s*$")
print(saluer(nom ~= "" and nom or "inconnu"))
for i = 1, 3 do
  print(i .. " × 7 = " .. i * 7)
end
''',
            "empty": "-- {name}\n\n",
        },
    },
    {
        "id": "bash", "kind": "lang", "name": "Bash", "abbr": "SH", "color": 5,
        "desc": "Scripts shell ; bash -n pour la vérification ; ShellCheck en extension.",
        "exts": [".sh", ".bash"], "main": "main.sh", "bins": ["bash"],
        "version": ["bash", "--version"],
        "run": [{"needs": ["bash"], "exec": ["bash", "{main}"]}],
        "check": [{"needs": ["bash"], "build": [["bash", "-n", "{main}"]]}],
        "repl": [{"needs": ["bash"], "exec": ["bash", "--norc", "--noprofile", "-i"], "env": {"PS1": "\\W $ "}}],
        "install": [{"pm": {"apt": ["bash"], "dnf": ["bash"], "pacman": ["bash"], "zypper": ["bash"], "apk": ["bash"], "brew": ["bash"]}}],
        "comment": "#", "indent": 2, "builtin": True,
        "templates": {
            "hello": '''#!/usr/bin/env bash
# {name}
set -euo pipefail

read -r -p "Comment vous appelez-vous ? " nom
echo "Bonjour ${nom:-inconnu} !"
for i in 1 2 3; do
  echo "$i × 7 = $((i * 7))"
done
''',
            "plot": '''#!/usr/bin/env bash
# {name}
# Envoie des mesures « nom:valeur » : ouvrez l'onglet Traceur.
for i in $(seq 0 200); do
  echo "carre:$(( (i % 40) < 20 ? 50 : -50 )),dent:$(( i % 40 * 5 - 100 ))"
  sleep 0.03
done
''',
            "empty": "#!/usr/bin/env bash\n# {name}\nset -euo pipefail\n\n",
        },
    },
    {
        "id": "perl", "kind": "lang", "name": "Perl", "abbr": "PL", "color": 1,
        "desc": "Scripts Perl 5, avertissements activés (perl -w).",
        "exts": [".pl", ".pm"], "main": "main.pl", "bins": ["perl"],
        "version": ["perl", "-e", "print \"Perl $^V\\n\""],
        "run": [{"needs": ["perl"], "exec": ["perl", "-w", "{main}"]}],
        "check": [{"needs": ["perl"], "build": [["perl", "-wc", "{main}"]]}],
        "repl": [],
        "install": [{"pm": {"apt": ["perl"], "dnf": ["perl"], "pacman": ["perl"], "zypper": ["perl"], "apk": ["perl"], "brew": ["perl"]}}],
        "comment": "#", "indent": 4,
        "templates": {
            "hello": '''#!/usr/bin/env perl
# {name}
use strict;
use warnings;
use utf8;
binmode STDOUT, ':encoding(UTF-8)';
$| = 1;

print "Comment vous appelez-vous ? ";
my $nom = <STDIN> // "";
chomp $nom;
print "Bonjour ", ($nom eq "" ? "inconnu" : $nom), " !\\n";
printf "%d × 7 = %d\\n", $_, $_ * 7 for 1 .. 3;
''',
            "empty": "#!/usr/bin/env perl\n# {name}\nuse strict;\nuse warnings;\n\n",
        },
    },
    {
        "id": "r", "kind": "lang", "name": "R", "abbr": "R", "color": 4,
        "desc": "Statistiques et données : Rscript, console R.",
        "exts": [".R", ".r"], "main": "main.R", "bins": ["Rscript"],
        "version": ["Rscript", "--version"],
        "run": [{"needs": ["Rscript"], "exec": ["Rscript", "{main}"]}],
        "check": [{"needs": ["Rscript"], "build": [["Rscript", "-e", "invisible(parse(file='{main}'))"]]}],
        "repl": [{"needs": ["R"], "exec": ["R", "--quiet", "--no-save"]}],
        "install": [{"pm": {"apt": ["r-base"], "dnf": ["R"], "pacman": ["r"], "zypper": ["R-base"], "apk": ["R"], "brew": ["r"]}}],
        "pkg": "cran", "comment": "#", "indent": 2,
        "templates": {
            "hello": '''# {name}
notes <- c(12, 15, 9, 17, 14)
cat("Moyenne :", mean(notes), "\\n")
cat("Écart-type :", round(sd(notes), 2), "\\n")
print(summary(notes))
''',
            "empty": "# {name}\n\n",
        },
    },
    {
        "id": "dart", "kind": "lang", "name": "Dart", "abbr": "DART", "color": 0,
        "desc": "SDK Dart : dart run, dart analyze.",
        "exts": [".dart"], "main": "main.dart", "bins": ["dart"],
        "version": ["dart", "--version"],
        "run": [{"needs": ["dart"], "exec": ["dart", "run", "{main}"]}],
        "check": [{"needs": ["dart"], "build": [["dart", "analyze", "{main}"]]}],
        "repl": [],
        "install": [{"pm": {"pacman": ["dart"], "brew": ["dart-sdk"]}},
                    {"needs": ["curl", "unzip"], "sh": "A=$(uname -m | sed 's/x86_64/x64/;s/aarch64/arm64/') && curl -fSL --progress-bar -o /tmp/dart.zip https://storage.googleapis.com/dart-archive/channels/stable/release/latest/sdk/dartsdk-linux-$A-release.zip && mkdir -p \"$HOME/.local/share\" \"$HOME/.local/bin\" && rm -rf \"$HOME/.local/share/dart-sdk\" && unzip -q /tmp/dart.zip -d \"$HOME/.local/share\" && rm /tmp/dart.zip && ln -sf \"$HOME/.local/share/dart-sdk/bin/dart\" \"$HOME/.local/bin/dart\""},
                    {"needs": ["snap"], "root": True, "cmd": ["snap", "install", "dart", "--classic"]}],
        "comment": "//", "indent": 2,
        "templates": {
            "hello": '''// {name}
import 'dart:io';

String saluer(String nom) => 'Bonjour $nom !';

void main() {
  stdout.write('Comment vous appelez-vous ? ');
  final nom = stdin.readLineSync()?.trim() ?? '';
  print(saluer(nom.isEmpty ? 'inconnu' : nom));
  for (var i = 1; i <= 3; i++) {
    print('$i × 7 = ${i * 7}');
  }
}
''',
            "empty": "// {name}\nvoid main() {\n}\n",
        },
    },
    {
        "id": "haskell", "kind": "lang", "name": "Haskell", "abbr": "HS", "color": 1,
        "desc": "GHC : runghc pour exécuter, ghci en console interactive.",
        "exts": [".hs"], "main": "Main.hs", "bins": ["runghc", "ghc"],
        "version": ["ghc", "--version"],
        "run": [{"needs": ["runghc"], "exec": ["runghc", "{main}"]}],
        "check": [{"needs": ["ghc"], "build": [["ghc", "-fno-code", "-Wall", "{main}"]]}],
        "repl": [{"needs": ["ghci"], "exec": ["ghci"]}],
        "install": [{"pm": {"apt": ["ghc"], "dnf": ["ghc"], "pacman": ["ghc"], "zypper": ["ghc"], "apk": ["ghc"], "brew": ["ghc"]}}],
        "comment": "--", "indent": 2,
        "templates": {
            "hello": '''-- {name}
module Main where

saluer :: String -> String
saluer nom = "Bonjour " ++ nom ++ " !"

main :: IO ()
main = do
  putStrLn "Comment vous appelez-vous ?"
  nom <- getLine
  putStrLn (saluer (if null nom then "inconnu" else nom))
  mapM_ (\\i -> putStrLn (show i ++ " × 7 = " ++ show (i * 7))) [1 .. 3 :: Int]
''',
            "empty": "-- {name}\nmodule Main where\n\nmain :: IO ()\nmain = return ()\n",
        },
    },
    {
        "id": "julia", "kind": "lang", "name": "Julia", "abbr": "JL", "color": 6,
        "desc": "Calcul scientifique rapide ; console julia.",
        "exts": [".jl"], "main": "main.jl", "bins": ["julia"],
        "version": ["julia", "--version"],
        "run": [{"needs": ["julia"], "exec": ["julia", "--color=yes", "{main}"]}],
        "check": [], "repl": [{"needs": ["julia"], "exec": ["julia", "--banner=no", "--color=no"]}],
        "install": [{"needs": ["curl"], "sh": "curl -fsSL https://install.julialang.org | sh -s -- -y"},
                    {"pm": {"pacman": ["julia"], "brew": ["julia"]}}],
        "comment": "#", "indent": 4,
        "templates": {
            "hello": '''# {name}
saluer(nom) = "Bonjour $nom !"

print("Comment vous appelez-vous ? ")
nom = strip(readline())
println(saluer(isempty(nom) ? "inconnu" : nom))
for i in 1:3
    println("$i × 7 = $(i * 7)")
end
''',
            "empty": "# {name}\n\n",
        },
    },
    {
        "id": "zig", "kind": "lang", "name": "Zig", "abbr": "ZIG", "color": 2,
        "desc": "zig run : compile et lance en une commande.",
        "exts": [".zig"], "main": "main.zig", "bins": ["zig"],
        "version": ["zig", "version"],
        "run": [{"needs": ["zig"], "exec": ["zig", "run", "{main}"], "env": {"ZIG_LOCAL_CACHE_DIR": "{out}/zig-cache"}}],
        "check": [{"needs": ["zig"], "build": [["zig", "ast-check", "{main}"]]}],
        "repl": [],
        "install": [{"pm": {"pacman": ["zig"], "brew": ["zig"], "apk": ["zig"], "dnf": ["zig"]}},
                    {"needs": ["curl", "tar"], "sh": "V=0.13.0 A=$(uname -m) && mkdir -p \"$HOME/.local/share\" \"$HOME/.local/bin\" && curl -fSL --progress-bar https://ziglang.org/download/$V/zig-linux-$A-$V.tar.xz | tar -xJ -C \"$HOME/.local/share\" && ln -sf \"$HOME/.local/share/zig-linux-$A-$V/zig\" \"$HOME/.local/bin/zig\""},
                    {"needs": ["snap"], "root": True, "cmd": ["snap", "install", "zig", "--classic", "--beta"]}],
        "comment": "//", "indent": 4,
        "templates": {
            "hello": '''// {name}
const std = @import("std");

pub fn main() void {
    std.debug.print("Bonjour depuis Zig !\\n", .{});
    var i: u32 = 1;
    while (i <= 3) : (i += 1) {
        std.debug.print("{d} x 7 = {d}\\n", .{ i, i * 7 });
    }
}
''',
            "empty": "// {name}\nconst std = @import(\"std\");\n\npub fn main() void {\n}\n",
        },
    },

    # ================================================================== outils
    {"id": "git", "kind": "tool", "name": "Git", "abbr": "GIT", "color": 8, "desc": "Nécessaire aux instantanés (historique du projet).",
     "bins": ["git"], "version": ["git", "--version"], "langs": ["*"],
     "install": [{"pm": {"apt": ["git"], "dnf": ["git"], "pacman": ["git"], "zypper": ["git"], "apk": ["git"], "brew": ["git"]}}]},
    {"id": "ruff", "kind": "tool", "name": "Ruff", "abbr": "RUFF", "color": 2, "desc": "Formateur et analyseur Python ultra-rapide (remplace Black, Flake8, isort).",
     "bins": ["ruff"], "version": ["ruff", "--version"], "langs": ["python"],
     "format": ["ruff", "format", "-q", "{file}"], "lint": ["ruff", "check", "--output-format=concise", "--no-fix", "{file}"],
     "install": [{"needs": ["pipx"], "cmd": ["pipx", "install", "ruff"], "remove": ["pipx", "uninstall", "ruff"]},
                 {"needs": ["python3"], "cmd": ["python3", "-m", "pip", "install", "--user", "--break-system-packages", "ruff"], "remove": ["python3", "-m", "pip", "uninstall", "-y", "--break-system-packages", "ruff"]}]},
    {"id": "black", "kind": "tool", "name": "Black", "abbr": "BLK", "color": 9, "desc": "Le formateur Python « sans compromis ».",
     "bins": ["black"], "version": ["black", "--version"], "langs": ["python"], "format": ["black", "-q", "{file}"],
     "install": [{"needs": ["pipx"], "cmd": ["pipx", "install", "black"], "remove": ["pipx", "uninstall", "black"]},
                 {"needs": ["python3"], "cmd": ["python3", "-m", "pip", "install", "--user", "--break-system-packages", "black"], "remove": ["python3", "-m", "pip", "uninstall", "-y", "--break-system-packages", "black"]}]},
    {"id": "prettier", "kind": "tool", "name": "Prettier", "abbr": "PRT", "color": 6, "desc": "Formateur JavaScript, TypeScript, HTML, CSS, JSON, Markdown.",
     "bins": ["prettier"], "version": ["prettier", "--version"], "langs": ["javascript", "typescript", "web"],
     "format_exts": [".js", ".mjs", ".cjs", ".ts", ".mts", ".jsx", ".tsx", ".html", ".htm", ".css", ".scss", ".json", ".md", ".yaml", ".yml"],
     "format": ["prettier", "--write", "--log-level", "warn", "{file}"],
     "install": [{"needs": ["npm"], "cmd": ["npm", "install", "-g", "--prefix", "{home}/.local", "prettier"], "remove": ["npm", "uninstall", "-g", "--prefix", "{home}/.local", "prettier"]}]},
    {"id": "eslint", "kind": "tool", "name": "ESLint", "abbr": "ESL", "color": 1, "desc": "Analyseur JavaScript : erreurs probables et variables inutilisées.",
     "bins": ["eslint"], "version": ["eslint", "--version"], "langs": ["javascript"],
     "lint": ["eslint", "--no-config-lookup", "--rule", "{\"no-unused-vars\":\"warn\",\"no-undef\":\"off\"}", "-f", "unix", "{file}"],
     "install": [{"needs": ["npm"], "cmd": ["npm", "install", "-g", "--prefix", "{home}/.local", "eslint"], "remove": ["npm", "uninstall", "-g", "--prefix", "{home}/.local", "eslint"]}]},
    {"id": "clang-format", "kind": "tool", "name": "clang-format", "abbr": "CLF", "color": 3, "desc": "Formateur C, C++, Java.",
     "bins": ["clang-format"], "version": ["clang-format", "--version"], "langs": ["c", "cpp", "java"],
     "format": ["clang-format", "-i", "--style={BasedOnStyle: Google, IndentWidth: 4, ColumnLimit: 110}", "{file}"],
     "install": [{"pm": {"apt": ["clang-format"], "dnf": ["clang-tools-extra"], "pacman": ["clang"], "zypper": ["clang-tools"], "apk": ["clang-extra-tools"], "brew": ["clang-format"]}},
                 {"needs": ["pipx"], "cmd": ["pipx", "install", "clang-format"], "remove": ["pipx", "uninstall", "clang-format"]}]},
    {"id": "cppcheck", "kind": "tool", "name": "Cppcheck", "abbr": "CPC", "color": 0, "desc": "Analyse statique C/C++ : fuites, débordements, code mort.",
     "bins": ["cppcheck"], "version": ["cppcheck", "--version"], "langs": ["c", "cpp"],
     "lint": ["cppcheck", "--enable=warning,style,performance", "--template=gcc", "--quiet", "{file}"],
     "install": [{"pm": {"apt": ["cppcheck"], "dnf": ["cppcheck"], "pacman": ["cppcheck"], "zypper": ["cppcheck"], "apk": ["cppcheck"], "brew": ["cppcheck"]}}]},
    {"id": "gofmt", "kind": "tool", "name": "gofmt", "abbr": "GOF", "color": 0, "desc": "Formateur officiel de Go (fourni avec Go).",
     "bins": ["gofmt"], "langs": ["go"], "format": ["gofmt", "-w", "{file}"], "install": [], "bundled": "go"},
    {"id": "rustfmt", "kind": "tool", "name": "rustfmt", "abbr": "RFM", "color": 8, "desc": "Formateur officiel de Rust.",
     "bins": ["rustfmt"], "version": ["rustfmt", "--version"], "langs": ["rust"], "format": ["rustfmt", "--edition", "2021", "{file}"],
     "install": [{"needs": ["rustup"], "cmd": ["rustup", "component", "add", "rustfmt"], "remove": ["rustup", "component", "remove", "rustfmt"]},
                 {"pm": {"apt": ["rustfmt"], "dnf": ["rustfmt"], "pacman": ["rust"], "brew": ["rustfmt"]}}]},
    {"id": "shellcheck", "kind": "tool", "name": "ShellCheck", "abbr": "SHC", "color": 2, "desc": "Trouve les pièges des scripts shell (guillemets, variables…).",
     "bins": ["shellcheck"], "version": ["shellcheck", "--version"], "langs": ["bash"], "lint": ["shellcheck", "-f", "gcc", "{file}"],
     "install": [{"pm": {"apt": ["shellcheck"], "dnf": ["ShellCheck"], "pacman": ["shellcheck"], "zypper": ["ShellCheck"], "apk": ["shellcheck"], "brew": ["shellcheck"]}}]},
    {"id": "shfmt", "kind": "tool", "name": "shfmt", "abbr": "SHF", "color": 5, "desc": "Formateur de scripts shell.",
     "bins": ["shfmt"], "version": ["shfmt", "--version"], "langs": ["bash"], "format": ["shfmt", "-w", "-i", "2", "{file}"],
     "install": [{"pm": {"apt": ["shfmt"], "dnf": ["shfmt"], "pacman": ["shfmt"], "apk": ["shfmt"], "brew": ["shfmt"]}},
                 {"needs": ["go"], "cmd": ["go", "install", "mvdan.cc/sh/v3/cmd/shfmt@latest"]}]},
    {"id": "rubocop", "kind": "tool", "name": "RuboCop", "abbr": "RBC", "color": 3, "desc": "Analyseur et formateur Ruby.",
     "bins": ["rubocop"], "version": ["rubocop", "--version"], "langs": ["ruby"],
     "lint": ["rubocop", "--format", "emacs", "--no-color", "{file}"], "format": ["rubocop", "-a", "--format", "quiet", "{file}"],
     "install": [{"needs": ["gem"], "cmd": ["gem", "install", "--user-install", "rubocop"], "remove": ["gem", "uninstall", "--user-install", "-x", "rubocop"]}]},
    {"id": "stylua", "kind": "tool", "name": "StyLua", "abbr": "STY", "color": 4, "desc": "Formateur Lua.",
     "bins": ["stylua"], "version": ["stylua", "--version"], "langs": ["lua"], "format": ["stylua", "{file}"],
     "install": [{"needs": ["cargo"], "cmd": ["cargo", "install", "stylua"], "remove": ["cargo", "uninstall", "stylua"]}]},
    {"id": "pipx", "kind": "tool", "name": "pipx", "abbr": "PIPX", "color": 4, "desc": "Installe des outils Python isolés (utilisé par Ruff, Black…).",
     "bins": ["pipx"], "version": ["pipx", "--version"], "langs": ["python"],
     "install": [{"pm": {"apt": ["pipx"], "dnf": ["pipx"], "pacman": ["python-pipx"], "zypper": ["python3-pipx"], "apk": ["pipx"], "brew": ["pipx"]}}]},
]



# --------------------------------------------------------------------------- utilitaires
def valid_name(name):
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,62}", name or ""))


def valid_relpath(rel):
    """Chemin relatif sûr : segments « lettres, chiffres, _ . - », pas de « .. », 6 niveaux au plus."""
    parts = (rel or "").replace("\\", "/").split("/")
    return 0 < len(parts) <= 6 and all(re.fullmatch(r"[A-Za-z0-9_.@+-][A-Za-z0-9_.@+ -]{0,99}", p) and p not in (".", "..") for p in parts)


def run_quiet(cmd, timeout=8, cwd=None):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, errors="replace", cwd=cwd,
                           stdin=subprocess.DEVNULL)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.SubprocessError):
        return None, ""


def version_tuple(text):
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text or "")
    return tuple(int(x or 0) for x in m.groups()) if m else ()


_which_cache = {}
_ver_cache = {}


def which(name):
    """which() mis en cache ; « node@22.6 » : node en version 22.6 au moins."""
    if name in _which_cache:
        return _which_cache[name]
    bin_, _, minv = name.partition("@")
    path = shutil.which(bin_)
    if path and minv:
        code, out = run_quiet([path, "--version"], 6)
        if not version_tuple(out) or version_tuple(out) < version_tuple(minv):
            path = None
    _which_cache[name] = path
    return path


def forget_which():
    _which_cache.clear()
    _ver_cache.clear()


def pkg_manager():
    for pm, exe in (("apt", "apt-get"), ("dnf", "dnf"), ("pacman", "pacman"), ("zypper", "zypper"), ("apk", "apk"), ("brew", "brew")):
        if shutil.which(exe):
            return pm
    return None


def pm_command(pm, pkgs, remove=False):
    q = " ".join(shlex.quote(p) for p in pkgs)
    if pm == "apt":
        return (f"DEBIAN_FRONTEND=noninteractive apt-get remove -y {q}" if remove else
                f"(apt-get update -qq || true) && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends {q}")
    return {
        "dnf": f"dnf {'remove' if remove else 'install'} -y {q}",
        "pacman": f"pacman {'-R' if remove else '-S --needed'} --noconfirm {q}",
        "zypper": f"zypper --non-interactive {'remove' if remove else 'install'} {q}",
        "apk": f"apk {'del' if remove else 'add'} {q}",
        "brew": f"brew {'uninstall' if remove else 'install'} {q}",
    }[pm]


def root_prefix():
    """Préfixe pour les commandes administrateur : [] (déjà root), sudo sans mot de passe, pkexec (fenêtre), ou None."""
    if os.geteuid() == 0:
        return []
    if shutil.which("sudo") and run_quiet(["sudo", "-n", "true"], 5)[0] == 0:
        return ["sudo", "-n"]
    if shutil.which("pkexec") and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return ["pkexec"]
    return None


def expand_home(s):
    return s.replace("{home}", str(HOME))


# --------------------------------------------------------------------------- extensions
class Extensions:
    def __init__(self):
        self.lock = threading.Lock()
        self.custom_errors = []
        self.load()

    def load(self):
        items, self.custom_errors = [dict(x, source="builtin") for x in CATALOG], []
        ids = {x["id"] for x in items}
        if EXT_DIR.is_dir():
            for f in sorted(EXT_DIR.glob("*.json")):
                try:
                    x = self.validate(json.loads(f.read_text()))
                except (OSError, ValueError) as e:
                    self.custom_errors.append(f"{f.name} : {e}")
                    continue
                x["source"] = "custom"
                if x["id"] in ids:
                    items = [y for y in items if y["id"] != x["id"]]     # une extension personnelle remplace celle du catalogue
                items.append(x)
                ids.add(x["id"])
        self.items = {x["id"]: x for x in items}

    @staticmethod
    def validate(x):
        if not isinstance(x, dict):
            raise ValueError("objet JSON attendu")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", str(x.get("id", ""))):
            raise ValueError("« id » : minuscules, chiffres, - et _ (32 max)")
        x.setdefault("kind", "lang")
        if x["kind"] not in ("lang", "tool"):
            raise ValueError("« kind » vaut « lang » ou « tool »")
        x["name"] = str(x.get("name") or x["id"])[:40]
        x["abbr"] = str(x.get("abbr") or x["id"][:3]).upper()[:4]
        x["desc"] = str(x.get("desc", ""))[:200]
        x["color"] = int(x.get("color", 9)) % 10
        x["bins"] = [str(b) for b in x.get("bins", [])][:8]
        if x["kind"] == "lang":
            exts = x.get("exts")
            if not exts or not all(isinstance(e, str) and e.startswith(".") for e in exts):
                raise ValueError("« exts » : liste d'extensions, ex. [\".nim\"]")
            x["main"] = str(x.get("main") or "main" + exts[0])
            if not valid_relpath(x["main"]):
                raise ValueError("« main » : nom de fichier invalide")
            for key in ("run", "check", "repl"):
                v = x.get(key, [])
                if isinstance(v, dict):
                    v = [v]
                if not isinstance(v, list):
                    raise ValueError(f"« {key} » : liste de variantes")
                for var in v:
                    if not isinstance(var, dict) or not all(isinstance(c, list) and all(isinstance(a, str) for a in c)
                                                            for c in var.get("build", []) + ([var["exec"]] if "exec" in var else [])):
                        raise ValueError(f"« {key} » : chaque commande est une liste de chaînes")
                    var.setdefault("needs", x["bins"][:1])
                x[key] = v
            if not x["run"]:
                raise ValueError("« run » : au moins une façon d'exécuter")
            tpl = x.get("templates") or {}
            x["templates"] = {k: v for k, v in tpl.items() if isinstance(v, (str, dict))} or {"empty": ""}
            x.setdefault("comment", "#")
            x["indent"] = int(x.get("indent", 4))
            sn = x.get("snippets") or {}
            x["snippets"] = {k: v for k, v in sn.items() if isinstance(k, str) and isinstance(v, str)} if isinstance(sn, dict) else {}
        inst = x.get("install", [])
        x["install"] = inst if isinstance(inst, list) else [inst]
        return x

    def disabled(self):
        try:
            return set(json.loads(EXT_STATE.read_text()).get("disabled", []))
        except (OSError, ValueError, AttributeError):
            return set()

    def set_enabled(self, ext_id, on):
        if ext_id not in self.items:
            raise ValueError("Extension inconnue")
        with self.lock:
            d = self.disabled()
            (d.discard if on else d.add)(ext_id)
            CONFIG.mkdir(parents=True, exist_ok=True)
            EXT_STATE.write_text(json.dumps({"disabled": sorted(d)}, indent=1))

    def add_custom(self, data):
        x = self.validate(json.loads(json.dumps(data)))
        EXT_DIR.mkdir(parents=True, exist_ok=True)
        clean = {k: v for k, v in data.items() if k != "source"}
        (EXT_DIR / f"{x['id']}.json").write_text(json.dumps(clean, ensure_ascii=False, indent=2) + "\n")
        self.load()
        return x["id"]

    def delete_custom(self, ext_id):
        f = EXT_DIR / f"{ext_id}.json"
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", ext_id or "") or not f.is_file():
            raise ValueError("Extension personnelle introuvable")
        f.unlink()
        self.load()

    def get(self, ext_id):
        x = self.items.get(ext_id)
        if not x:
            raise ValueError(f"Extension inconnue : {ext_id}")
        return x

    def langs(self):
        return [x for x in self.items.values() if x["kind"] == "lang"]

    # ---- état : installée ? version ?
    @staticmethod
    def needs_ok(needs):
        bind = {}
        for n in needs:
            found = None
            for alt in n.split("|"):
                p = which(alt)
                if p:
                    found = (alt.split("@")[0], p)
                    break
            if not found:
                return None
            bind[n.split("|")[0].split("@")[0]] = found[0]
        return bind

    def installed(self, x):
        if x.get("builtin") and not x.get("bins"):
            return True
        if x["kind"] == "lang":
            return any(self.needs_ok(v.get("needs", [])) is not None for v in x.get("run", []))
        return any(which(b) for b in x.get("bins", []))

    def version(self, x):
        if x["id"] in _ver_cache:
            return _ver_cache[x["id"]]
        cmd = x.get("version")
        out = ""
        if cmd:
            b = next((bb for bb in x.get("bins", []) if which(bb)), None)
            cmd = [c.replace("{bin}", b or "") for c in cmd]
            if which(cmd[0]):
                _, text = run_quiet(cmd, 12)
                lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not re.match(r"(Picked up|WARNING|warning:|NOTE:)", ln.strip())]
                line = next((ln for ln in lines if re.search(r"\d+\.\d+", ln)), lines[0] if lines else "")
                m = re.search(r"\d+\.\d+(?:\.\d+)?(?:[-+.\w]*)?", line)
                out = m.group(0) if m else line[:40]
        _ver_cache[x["id"]] = out
        return out

    def install_plan(self, x, remove=False):
        """Première recette applicable : (description, commande shell ou liste, besoin root) ou (None, raison, None)."""
        pm = pkg_manager()
        reasons = []
        for r in x.get("install", []):
            if "pm" in r:
                if not pm or pm not in r["pm"]:
                    reasons.append("aucun paquet pour " + (PM_NAMES.get(pm, "ce système") if pm else "ce système"))
                    continue
                pkgs = r["pm"][pm]
                return (f"{PM_NAMES[pm]} : {' '.join(pkgs)}", pm_command(pm, pkgs, remove), pm != "brew")
            need = r.get("needs", [])
            if any(not which(n) for n in need):
                reasons.append("nécessite " + " + ".join(need))
                continue
            if remove:
                if "remove" not in r:
                    continue
                return ("désinstallation", [expand_home(a) for a in r["remove"]], bool(r.get("root")))
            if "sh" in r:
                return (r["sh"].split("|")[0].strip()[:80], r["sh"], bool(r.get("root")))
            return (" ".join(r["cmd"][:4]), [expand_home(a) for a in r["cmd"]], bool(r.get("root")))
        if remove:
            return (None, "Pas de désinstallation automatique pour cette extension (désactivez-la plutôt).", None)
        return (None, "; ".join(dict.fromkeys(reasons)) or "Aucune méthode d'installation connue.", None)

    def describe(self, x, with_version=True):
        inst = self.installed(x)
        plan = self.install_plan(x)
        out = {k: x.get(k) for k in ("id", "kind", "name", "abbr", "desc", "color", "exts", "main", "langs", "source", "comment",
                                       "indent", "keywords", "types", "builtins", "snippets", "bundled", "pkg")}
        out.update({
            "installed": inst, "enabled": x["id"] not in self.disabled(),
            "version": self.version(x) if (inst and with_version) else "",
            "path": next((which(b) for b in x.get("bins", []) if which(b)), ""),
            "plan": plan[0], "why": plan[1] if not plan[0] else "", "root": bool(plan[2]),
            "removable": bool(self.install_plan(x, remove=True)[0]) and x["kind"] == "tool",
            "templates": sorted(x.get("templates", {}).keys(), key=lambda t: (["hello", "guess", "plot", "empty"] + [t]).index(t)) if x["kind"] == "lang" else [],
            "repl": bool(x.get("repl")), "check": bool(x.get("check")),
            "format": bool(x.get("format")), "lint": bool(x.get("lint")),
        })
        return out


EXT = None


# --------------------------------------------------------------------------- bus d'événements (SSE)
class Bus:
    def __init__(self):
        self.subs = set()
        self.lock = threading.Lock()

    def subscribe(self):
        q = queue.Queue(maxsize=20000)
        with self.lock:
            self.subs.add(q)
        return q

    def unsubscribe(self, q):
        with self.lock:
            self.subs.discard(q)

    def emit(self, _event, **data):
        msg = json.dumps({"type": _event, **data}, ensure_ascii=False)
        with self.lock:
            subs = list(self.subs)
        for q in subs:
            try:
                q.put_nowait(msg)
            except queue.Full:
                pass


BUS = Bus()


def term(text, kind="sys"):
    """Ligne produite par Forge Code (et non par le programme) dans le terminal."""
    BUS.emit("term", text=text + "\n", kind=kind)


def toast(text, kind="info"):
    BUS.emit("toast", text=text, kind=kind)


# --------------------------------------------------------------------------- diagnostics
RX_LOC = re.compile(r"(?P<file>(?:[A-Za-z]:)?[\w./\\@+-]*[\w@+-]\.[A-Za-z0-9]{1,6})(?::(?P<line>\d+)(?::(?P<col>\d+))?|\((?P<l2>\d+),(?P<c2>\d+)\))")
RX_SEV_W = re.compile(r"\b(warning|avertissement|note|style|performance|convention)\b|^\s*[CWR]:", re.I)


class Diag:
    """Relève erreurs et avertissements (fichier, ligne, colonne, message) dans la sortie des compilateurs et des programmes."""

    def __init__(self, root, files):
        self.root = Path(root).resolve()
        self.files = set(files)
        self.items = []
        self.pending = None        # (fichier, ligne, col) en attente d'un message (traces Python, Node)
        self.last_exc = None       # message d'exception en attente d'un emplacement (traces Java, Go)
        self.rust_msg = None

    def rel(self, f):
        f = f.strip().strip("'\"").replace("\\", "/")
        if f.startswith("./"):
            f = f[2:]
        if f in self.files:
            return f
        try:
            p = Path(f)
            p = p.resolve() if p.is_absolute() else (self.root / p).resolve()
            r = p.relative_to(self.root).as_posix()
            return r if r in self.files else None
        except (ValueError, OSError):
            return None

    def add(self, f, line, col, msg, sev="error"):
        msg = " ".join(str(msg).split())[:400]
        if not msg or len(self.items) >= 300:
            return
        d = {"file": f, "line": max(1, int(line)), "col": max(1, int(col or 1)), "message": msg, "severity": sev}
        if d not in self.items:
            self.items.append(d)

    def frame(self, f, ln, col):
        """Ligne d'une pile d'appels : complète une exception déjà lue, sinon attend son message."""
        if self.last_exc:
            self.add(f, ln, col, self.last_exc)
            self.last_exc = None
        elif not self.pending:
            self.pending = (f, ln, col)

    def feed(self, line):
        line = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", line).rstrip()
        if not line.strip():
            return
        s = line.strip()
        # --- traces : on retient l'endroit, le message arrive plus loin
        m = re.match(r'\s*File "(.+?)", line (\d+)', line)                              # Python
        if m:
            f = self.rel(m.group(1))
            if f:
                self.pending = (f, int(m.group(2)), 1)
            return
        m = re.match(r"\s+at .*?\(?((?:file://)?/[^\s():]+|[\w./-]+\.\w+):(\d+):(\d+)\)?$", line)   # Node / Deno
        if m:
            f = self.rel(m.group(1).replace("file://", ""))
            if f:
                self.frame(f, int(m.group(2)), int(m.group(3)))
            return
        m = re.match(r"\s+at [\w.$<>]+\(([\w.-]+\.(?:java|kt)):(\d+)\)", line)            # Java / Kotlin
        if m:
            f = self.rel(m.group(1)) or next((x for x in self.files if x.endswith("/" + m.group(1))), None)
            if f:
                self.frame(f, int(m.group(2)), 1)
            return
        m = re.match(r"^panic: (.+)$", s)                                                   # Go
        if m:
            self.last_exc = "panic: " + m.group(1)
            return
        m = re.match(r"^(error|warning)(\[\w+\])?: (.+)$", s)                              # Rust : message puis « --> fichier:ligne:col »
        if m:
            self.rust_msg = ("warning" if m.group(1) == "warning" else "error", m.group(3))
            return
        m = re.match(r"^-->\s+(.+?):(\d+):(\d+)$", s)
        if m and self.rust_msg:
            f = self.rel(m.group(1))
            if f:
                self.add(f, m.group(2), m.group(3), self.rust_msg[1], self.rust_msg[0])
            self.rust_msg = None
            return
        m = re.match(r"^(?:Uncaught |Exception in thread \"\w+\" )?([\w.$]*(?:Error|Exception|Interrupt|Exit|Panic)[\w.$]*)(?::\s*(.*))?$", s)
        if m and not re.match(r"^\w+\.\w+:\d", s):                                        # « XxxError: message »
            msg = f"{m.group(1).split('.')[-1]}: {m.group(2)}" if m.group(2) else m.group(1)
            if self.pending:
                f, ln, col = self.pending
                self.add(f, ln, col, msg)
                self.pending = None
            else:
                self.last_exc = msg
            return
        # --- PHP : « … in /chemin/fichier.php on line 3 »
        m = re.search(r"(?:PHP )?(Parse error|Fatal error|Warning|Notice|Deprecated)[^:]*:\s*(.+?) in (\S+?\.php)(?::(\d+))? on line (\d+)", s)
        if m:
            f = self.rel(m.group(3))
            if f:
                self.add(f, m.group(5), 1, m.group(2), "warning" if m.group(1) in ("Warning", "Notice", "Deprecated") else "error")
            return
        # --- Bash : « main.sh: line 3: … »  ;  Perl : « … at main.pl line 3. »
        m = re.match(r"^(.+?): (?:line|ligne) (\d+): (.+)$", s)
        if m and self.rel(m.group(1)):
            self.add(self.rel(m.group(1)), m.group(2), 1, m.group(3))
            return
        m = re.search(r"^(.*) at (\S+) line (\d+)[.,]", s)
        if m and self.rel(m.group(2)):
            self.add(self.rel(m.group(2)), m.group(3), 1, m.group(1), "warning" if re.search(r"\bwarn|deprecated|used only once", s, re.I) else "error")
            return
        # --- forme générale : fichier:ligne[:col][:] message  (gcc, clang, go, javac, ruff, shellcheck, lua, ruby, zig, dart, C#…)
        for m in RX_LOC.finditer(line):
            f = self.rel(m.group("file"))
            if not f:
                continue
            ln = m.group("line") or m.group("l2")
            col = m.group("col") or m.group("c2") or 1
            rest = line[m.end():].lstrip(" :")
            rest = re.sub(r"^(fatal error|error|erreur|warning|avertissement|note)\s*(\[[^\]]*\])?\s*:?\s*", lambda k: "", rest, flags=re.I) if rest else rest
            head = line[m.end():]
            sev = "warning" if RX_SEV_W.search(head[:40]) or re.match(r"\s*:\s*\d+:\s*[A-Z]\d{3,4}\b", head) else "error"
            if re.search(r"\bnote\b", head[:20], re.I):
                return
            if re.match(r"^in [`'‘]", rest):                      # Ruby : « main.rb:3:in 'x': message (NameError) »
                if ":" not in rest:
                    return                                         # simple ligne de pile d'appels
                rest = rest.split(":", 1)[1].strip()
            if re.match(r"^in (main chunk|function|upvalue|local|method|field|\?)", rest):
                return                                             # pile d'appels Lua
            if re.search(r"\b(warning|info|hint)\b", line[:m.start()], re.I):
                sev = "warning"
            if not rest.strip() or re.fullmatch(r"\+0x[0-9a-f]+", rest.strip()):
                if self.last_exc:                                  # Go : « /chemin/main.go:8 +0x1d » après « panic: … »
                    self.add(f, ln, col, self.last_exc)
                    self.last_exc = None
                elif not rest.strip() and not self.pending:        # Node : « /chemin/main.js:3 » puis le message plus bas
                    self.pending = (f, int(ln), int(col))
                return
            rest = re.sub(r"^-\s+", "", rest)
            self.add(f, ln, col, rest, sev)
            return


class LiveDiag(Diag):
    """Diagnostics d'une vérification faite dans le miroir du projet : les chemins du miroir sont ramenés au projet."""

    def __init__(self, mirror, root, files):
        super().__init__(root, files)
        self.mirror = str(mirror).replace("\\", "/")

    def rel(self, f):
        f = f.strip().strip("'\"").replace("\\", "/")
        if f.startswith(self.mirror + "/"):
            f = f[len(self.mirror) + 1:]
        return super().rel(f)


# --------------------------------------------------------------------------- terminal (PTY)
class Session:
    """Un processus relié à un pseudo-terminal : programme, console interactive (REPL) ou shell."""

    def __init__(self):
        self.proc = None
        self.master = None
        self.kind = None
        self.lock = threading.Lock()
        self.size = (32, 120)
        self.t0 = 0
        self.capture = None
        self.on_exit = None
        self.stopping = False

    @property
    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self, cmd, cwd, env, kind, on_exit=None, capture=False, label=None):
        self.stop()
        master, slave = pty.openpty()
        rows, cols = self.size
        try:
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        except OSError:
            pass

        def child_setup():                     # le pseudo-terminal devient le terminal de contrôle : Ctrl+C fonctionne
            try:
                fcntl.ioctl(0, termios.TIOCSCTTY, 0)
            except OSError:
                pass
        try:
            proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=slave, stdout=slave, stderr=slave,
                                    start_new_session=True, close_fds=True, preexec_fn=child_setup)
        except OSError as e:
            os.close(master)
            os.close(slave)
            raise RuntimeError(f"Impossible de lancer {cmd[0]} : {e.strerror or e}")
        os.close(slave)
        fcntl.fcntl(master, fcntl.F_SETFL, fcntl.fcntl(master, fcntl.F_GETFL) | os.O_NONBLOCK)
        with self.lock:
            self.proc, self.master, self.kind, self.t0 = proc, master, kind, time.time()
            self.capture = [] if capture else None
            self.on_exit, self.stopping = on_exit, False
        BUS.emit("session", state="open", kind=kind, cmd=label or " ".join(shlex.quote(c) for c in cmd), pid=proc.pid)
        threading.Thread(target=self._reader, args=(proc, master), daemon=True).start()

    def _reader(self, proc, master):
        dec = codecs.getincrementaldecoder("utf-8")("replace")
        size = 0
        while True:
            try:
                r, _, _ = select.select([master], [], [], 0.25)
            except (OSError, ValueError):
                break
            if r:
                try:
                    chunk = os.read(master, 65536)
                except BlockingIOError:
                    continue
                except OSError:                 # EIO : plus aucun processus relié au terminal
                    break
                if not chunk:
                    break
            elif proc.poll() is not None:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    break
                if not chunk:
                    break
            else:
                continue
            text = dec.decode(chunk)
            if text:
                BUS.emit("term", text=text, kind="pty")
                if self.capture is not None and size < 400_000:
                    self.capture.append(text)
                    size += len(text)
            time.sleep(0.01)
        code = proc.wait()
        try:
            os.close(master)
        except OSError:
            pass
        secs = round(time.time() - self.t0, 2)
        with self.lock:
            mine = proc is self.proc
            cb, cap, stopping = self.on_exit, self.capture, self.stopping
            if mine:
                self.proc = self.master = None
        if mine:
            BUS.emit("session", state="closed", kind=self.kind, code=code, seconds=secs, stopped=stopping)
            if cb:
                try:
                    cb(code, "".join(cap or []), secs, stopping)
                except Exception as e:  # noqa: BLE001
                    term(f"Erreur interne : {e}", "error")

    def write(self, text):
        if not self.running or self.master is None:
            raise RuntimeError("Aucun programme en cours : lancez-le d'abord (Ctrl+Entrée).")
        os.write(self.master, text.encode())

    def signal(self, what):
        if not self.running:
            return
        if what == "eof":
            os.write(self.master, b"\x04")
            return
        if what == "int":
            try:                                  # comme au clavier : le terminal prévient le groupe au premier plan
                os.write(self.master, b"\x03")
                return
            except OSError:
                pass
        sig = {"int": signal.SIGINT, "term": signal.SIGTERM, "kill": signal.SIGKILL}.get(what, signal.SIGINT)
        try:
            os.killpg(self.proc.pid, sig)
        except OSError:
            pass

    def resize(self, rows, cols):
        self.size = (max(5, min(300, int(rows))), max(20, min(500, int(cols))))
        if self.master is not None:
            try:
                fcntl.ioctl(self.master, termios.TIOCSWINSZ, struct.pack("HHHH", self.size[0], self.size[1], 0, 0))
                os.killpg(self.proc.pid, signal.SIGWINCH)
            except OSError:
                pass

    def stop(self):
        with self.lock:
            proc = self.proc
            self.stopping = True
        if proc and proc.poll() is None:
            for sig, wait in ((signal.SIGTERM, 1.2), (signal.SIGKILL, 2)):
                try:
                    os.killpg(proc.pid, sig)
                except OSError:
                    break
                try:
                    proc.wait(wait)
                    break
                except subprocess.TimeoutExpired:
                    continue
        # le lecteur signale lui-même la fin (événement « session »)
        deadline = time.time() + 2
        while self.proc is proc and proc is not None and time.time() < deadline:
            time.sleep(0.05)


# --------------------------------------------------------------------------- studio
class Studio:
    def __init__(self, workspace):
        self.workspace = Path(workspace).expanduser().resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.job_lock = threading.Lock()
        self.job = None
        self.proc = None
        self.cancelled = False
        self.run_cancelled = False
        self.bproc = None
        self.session = Session()
        self.meta_lock = threading.Lock()
        self.conf_lock = threading.Lock()
        self.snap_lock = threading.Lock()
        self.run_lock = threading.Lock()
        self.live_locks = {}
        self.run_id = 0
        self._git_ident = None
        self.preview_ver = {}

    # ----------------------------------------------------------------- projets
    def project_dir(self, name):
        if not valid_name(name):
            raise ValueError("Nom de projet invalide")
        path = (self.workspace / name).resolve()
        if path.parent != self.workspace or not path.is_dir():
            raise ValueError(f"Projet introuvable : {name}")
        return path

    def walk(self, root):
        """Fichiers du projet (chemins relatifs), sans les dossiers générés (.git, node_modules, .venv, target…)."""
        out = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in IGNORED_DIRS and not d.startswith(".") or d in (".github",))
            rel = Path(dirpath).relative_to(root)
            for f in sorted(filenames):
                if f in (CONF_FILE, CONF_FILE + ".tmp") or f.endswith((".pyc", ".class", ".o")):
                    continue
                out.append((rel / f).as_posix())
                if len(out) >= MAX_FILES:
                    return out
        return out

    def detect_lang(self, root, files=None):
        files = files if files is not None else self.walk(root)
        score = {}
        for lang in EXT.langs():
            s = 0
            for f in files:
                if f == lang.get("main"):
                    s += 5
                if Path(f).suffix in lang.get("exts", []):
                    s += 2 if "/" not in f else 1
            if s:
                score[lang["id"]] = s
        if "web" in score and any(Path(f).suffix in (".js", ".ts") for f in files) and "index.html" not in files:
            score.pop("web")
        return max(score, key=score.get) if score else ""

    def lang_of(self, root, conf=None):
        conf = conf if conf is not None else self.conf_dir(root)
        lang = conf.get("lang") if isinstance(conf.get("lang"), str) else ""
        return lang if lang in EXT.items else self.detect_lang(root)

    def main_of(self, root, lang, files, conf=None):
        conf = conf if conf is not None else self.conf_dir(root)
        m = conf.get("main")
        if isinstance(m, str) and m in files:
            return m
        x = EXT.items.get(lang)
        if x:
            if x.get("main") in files:
                return x["main"]
            cand = [f for f in files if Path(f).suffix in x.get("exts", [])]
            for pref in ("main", "Main", "index", "app", "Program"):
                hit = next((f for f in cand if Path(f).stem == pref), None)
                if hit:
                    return hit
            if cand:
                return cand[0]
        return files[0] if files else ""

    def projects(self):
        out = []
        for d in sorted(self.workspace.iterdir(), key=lambda p: p.name.lower()):
            if not d.is_dir() or d.name.startswith(".") or not valid_name(d.name):
                continue
            try:
                conf = self.conf_dir(d)
                lang = self.lang_of(d, conf)
                mtime = max([d.stat().st_mtime] + [f.stat().st_mtime for f in list(d.iterdir())[:60] if f.is_file()])
            except OSError:
                continue
            out.append({"name": d.name, "lang": lang, "modified": mtime})
        return out

    def project(self, name):
        root = self.project_dir(name)
        files = self.walk(root)
        conf = self.conf_dir(root)
        lang = self.lang_of(root, conf)
        return {"name": name, "path": str(root), "files": files, "lang": lang,
                "main": self.main_of(root, lang, files, conf), "conf": conf,
                "truncated": len(files) >= MAX_FILES}

    def file_path(self, project, rel, must_exist=True):
        root = self.project_dir(project)
        if not valid_relpath(rel):
            raise ValueError("Nom de fichier non autorisé")
        p = (root / rel).resolve()
        if root not in p.parents or ".git" in p.relative_to(root).parts:
            raise ValueError("Fichier non autorisé")
        if must_exist and not p.is_file():
            raise ValueError(f"Fichier introuvable : {rel}")
        return p

    def read_file(self, project, rel):
        p = self.file_path(project, rel)
        size = p.stat().st_size
        if size > MAX_EDIT:
            raise ValueError(f"Fichier trop volumineux pour l'éditeur ({size // 1024} Ko)")
        data = p.read_bytes()
        if b"\0" in data[:8192]:
            raise ValueError("Fichier binaire : il ne peut pas être ouvert dans l'éditeur")
        return {"content": data.decode("utf-8", "replace"), "mtime": p.stat().st_mtime}

    def write_file(self, project, rel, content):
        p = self.file_path(project, rel, must_exist=False)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        self.bump_preview(project)
        return {"ok": True, "mtime": p.stat().st_mtime}

    def new_file(self, project, rel, content=None):
        p = self.file_path(project, rel, must_exist=False)
        if p.exists():
            raise ValueError(f"« {rel} » existe déjà.")
        p.parent.mkdir(parents=True, exist_ok=True)
        if content is None:
            content = self.file_stub(project, rel)
        p.write_text(content)
        return {"file": rel, **self.project(project)}

    def file_stub(self, project, rel):
        suffix = Path(rel).suffix
        stem = Path(rel).stem
        for x in EXT.langs():
            if suffix in x.get("exts", []):
                c = x.get("comment", "#")
                if suffix in (".h", ".hpp", ".hh"):
                    return f"#pragma once\n\n// {stem}\n"
                if suffix == ".java":
                    return f"public class {stem} {{\n}}\n"
                if suffix == ".go":
                    return "package main\n\n"
                if suffix == ".php":
                    return "<?php\n\n"
                if suffix in (".html", ".htm"):
                    return f"<!doctype html>\n<html lang=\"fr\">\n<head>\n  <meta charset=\"utf-8\">\n  <title>{stem}</title>\n</head>\n<body>\n\n</body>\n</html>\n"
                if suffix == ".css":
                    return f"/* {stem} */\n"
                return f"{c} {stem}\n" + ("-->\n" if c == "<!--" else "")
        return ""

    def rename_file(self, project, rel, new):
        src = self.file_path(project, rel)
        dst = self.file_path(project, new, must_exist=False)
        if dst.exists() and dst.resolve() != src.resolve():
            raise ValueError(f"« {new} » existe déjà.")
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        conf = self.conf(project)
        if conf.get("main") == rel:
            self.set_conf(project, "main", new)
        return {"file": new, **self.project(project)}

    def delete_file(self, project, rel):
        self.file_path(project, rel).unlink()
        return self.project(project)

    # ----------------------------------------------------------------- épinglés et dates d'ouverture
    def meta(self):
        try:
            data = json.loads(META_FILE.read_text())
        except (OSError, ValueError):
            data = {}
        m = data.get(str(self.workspace), {}) if isinstance(data, dict) else {}
        pinned = [n for n in m.get("pinned", []) if isinstance(n, str)]
        opened = {k: float(v) for k, v in (m.get("opened") or {}).items() if isinstance(k, str) and isinstance(v, (int, float))}
        return {"pinned": pinned, "opened": opened}

    def set_meta(self, pinned=None, opened=None):
        with self.meta_lock:
            try:
                data = json.loads(META_FILE.read_text())
            except (OSError, ValueError):
                data = {}
            cur = self.meta()
            if isinstance(pinned, list):
                cur["pinned"] = [n for n in pinned if isinstance(n, str)][:500]
            if isinstance(opened, dict):
                cur["opened"].update({k: float(v) for k, v in opened.items() if isinstance(k, str) and isinstance(v, (int, float))})
                cur["opened"] = dict(sorted(cur["opened"].items(), key=lambda kv: -kv[1])[:500])
            data[str(self.workspace)] = cur
            CACHE.mkdir(parents=True, exist_ok=True)
            tmp = META_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False))
            tmp.replace(META_FILE)
            return cur

    # ----------------------------------------------------------------- réglages du projet (.forge.json)
    @staticmethod
    def conf_dir(root):
        try:
            data = json.loads((Path(root) / CONF_FILE).read_text())
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def conf(self, project):
        return self.conf_dir(self.project_dir(project))

    def set_conf(self, project, section, value):
        if section not in CONF_SECTIONS:
            raise ValueError("Section de configuration inconnue")
        if len(json.dumps(value)) > 100_000:
            raise ValueError("Configuration trop volumineuse")
        root = self.project_dir(project)
        with self.conf_lock:
            data = self.conf_dir(root)
            data[section] = value
            tmp = root / (CONF_FILE + ".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
            tmp.replace(root / CONF_FILE)
        return data

    def new_project(self, name, lang_id, template):
        if not valid_name(name):
            raise ValueError("Nom invalide : lettres, chiffres, _ . - sans espace (63 max).")
        x = EXT.get(lang_id)
        if x["kind"] != "lang":
            raise ValueError("Ce n'est pas un langage")
        d = self.workspace / name
        if d.exists():
            raise ValueError(f"« {name} » existe déjà.")
        tpls = x.get("templates") or {}
        tpl = tpls.get(template) or tpls.get("hello") or tpls.get("empty") or ""
        files = tpl if isinstance(tpl, dict) else {x["main"]: tpl}
        d.mkdir()
        try:
            for rel, body in files.items():
                rel = rel.replace("{name}", name)
                if not valid_relpath(rel):
                    raise ValueError(f"Nom de fichier invalide dans le modèle : {rel}")
                p = d / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(body.replace("{name}", name))
                if p.suffix in (".sh", ".bash", ".pl", ".py") and body.startswith("#!"):
                    p.chmod(0o755)
            (d / CONF_FILE).write_text(json.dumps({"lang": lang_id}, indent=1) + "\n")
            (d / ".gitignore").write_text("build/\n.venv/\nnode_modules/\ntarget/\n__pycache__/\n")
        except Exception:
            shutil.rmtree(d, ignore_errors=True)
            raise
        return self.project(name)

    def set_lang(self, project, lang_id):
        EXT.get(lang_id)
        self.set_conf(project, "lang", lang_id)
        return self.project(project)

    # ----------------------------------------------------------------- exécution
    def build_dir(self, root):
        import hashlib
        d = CACHE / "build" / f"{root.name}-{hashlib.sha1(str(root).encode()).hexdigest()[:8]}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def env_for(self, extra=None, colors=True):
        env = dict(os.environ)
        env.update({"PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8", "LANG": env.get("LANG") or "C.UTF-8",
                    "COLUMNS": str(self.session.size[1]), "LINES": str(self.session.size[0])})
        if colors:
            env.update({"TERM": "xterm-256color", "FORCE_COLOR": "1", "CLICOLOR_FORCE": "1"})
        else:
            env.update({"TERM": "dumb", "NO_COLOR": "1", "PYTHON_BASIC_REPL": "1"})
        for k, v in (extra or {}).items():
            env[k] = v
        return env

    def resolve(self, x, key, root, files, main):
        """Choisit la variante (run, check, repl) applicable et remplit les emplacements. Renvoie (variante, liaisons) ou lève une erreur claire."""
        variants = x.get(key) or []
        if not variants:
            return None, None
        missing = []
        for v in variants:
            if v.get("when") and not (root / v["when"]).exists():
                continue
            bind = EXT.needs_ok(v.get("needs", []))
            if bind is None:
                missing.append(" ou ".join(n.replace("|", " / ") for n in v.get("needs", [])))
                continue
            return v, bind
        need = missing[0] if missing else "?"
        raise RuntimeError(f"{x['name']} n'est pas installé sur cet ordinateur (il faut : {need}). "
                           f"Installez l'extension « {x['name']} » (onglet Extensions).")

    def fill(self, args, root, files, main, bind, out):
        stem = Path(main).stem
        venv_py = root / ".venv" / "bin" / "python"
        subst = {"{main}": main, "{stem}": stem, "{out}": str(out), "{exe}": str(out / stem), "{home}": str(HOME),
                 "{name}": root.name, "{python}": str(venv_py) if venv_py.exists() else (which("python3") or "python3")}
        for k, v in bind.items():
            subst["{" + k + "}"] = v
        if bind:
            subst["{bin}"] = next(iter(bind.values()))
        res = []
        for a in args:
            m = re.fullmatch(r"\{srcs:([^}]+)\}", a)
            if m:
                exts = tuple(e.strip() for e in m.group(1).split(","))
                srcs = [f for f in files if f.endswith(exts)]
                res += srcs or [main]
                continue
            for k, v in subst.items():
                a = a.replace(k, v)
            res.append(a)
        return res

    def prepare(self, project, target, key):
        root = self.project_dir(project)
        info = self.project(project)
        lang = info["lang"]
        if not lang:
            raise RuntimeError("Langage du projet inconnu : choisissez-le dans la barre d'outils.")
        x = EXT.get(lang)
        files = info["files"]
        main = info["main"]
        if target and target in files and target != main:
            suf = Path(target).suffix
            if suf in x.get("exts", []):
                main = target
            elif x["id"] != "web":
                # fichier ouvert d'un autre langage (ex. un .py dans un projet C) : on prend le langage de ce fichier
                other = next((l for l in EXT.langs() if suf in l.get("exts", []) and l["id"] != "web"), None)
                if other:
                    x, main = other, target
        v, bind = self.resolve(x, key, root, files, main)
        return root, x, files, main, v, bind

    def run(self, project, target="", args="", stdin="", mode="run"):
        """Vérifie (mode check) ou compile puis exécute dans le terminal (mode run)."""
        key = "check" if mode == "check" else "run"
        root, x, files, main, v, bind = self.prepare(project, target, key)
        if v is None:
            if key == "check":
                raise RuntimeError(f"Pas de vérification disponible pour {x['name']} : utilisez Exécuter (Ctrl+Entrée).")
            raise RuntimeError(f"{x['name']} ne sait pas encore exécuter ce projet.")
        if v.get("preview"):
            url = f"/preview/{TOKEN}/{project}/{main}"
            term(f"Aperçu web : {main} (se recharge à chaque enregistrement)", "info")
            BUS.emit("preview", url=url, project=project)
            BUS.emit("run", state="done", ok=True, code=0, seconds=0, preview=True, mode=mode)
            return {"ok": True, "preview": url}
        if not self.run_lock.acquire(blocking=False):
            raise RuntimeError("Une exécution est déjà en préparation.")
        self.session.stop()
        self.run_id += 1
        rid = self.run_id
        out = self.build_dir(root)
        env = self.env_for({k: self.fill([val], root, files, main, bind, out)[0] for k, val in (v.get("env") or {}).items()})
        steps = [self.fill(c, root, files, main, bind, out) for c in v.get("build", [])]
        exe = self.fill(v["exec"], root, files, main, bind, out) + (shlex.split(args) if args and mode == "run" else []) if v.get("exec") and mode == "run" else None
        self.run_cancelled = False

        def worker():
            diag = Diag(root, files)
            t0 = time.time()
            try:
                BUS.emit("run", state="start", mode=mode, lang=x["id"], main=main, steps=len(steps), exec=bool(exe))
                for i, cmd in enumerate(steps):
                    BUS.emit("run", state="step", step="build", i=i, n=len(steps))
                    code = self.stream(cmd, root, env, diag, slot="bproc")
                    BUS.emit("diagnostics", items=diag.items)
                    if code != 0 or self.run_cancelled:
                        n = sum(1 for d in diag.items if d["severity"] == "error")
                        BUS.emit("run", state="done", ok=False, stage="build", code=code, errors=n, mode=mode,
                                 cancelled=self.run_cancelled, seconds=round(time.time() - t0, 2))
                        return
                if not exe:
                    BUS.emit("diagnostics", items=diag.items)
                    BUS.emit("run", state="done", ok=True, stage="build", code=0, mode=mode, seconds=round(time.time() - t0, 2),
                             warnings=len(diag.items))
                    return
                BUS.emit("run", state="step", step="exec")
                if not steps:
                    BUS.emit("diagnostics", items=[])
                def show(i, a):
                    if a.startswith(str(out)):
                        return "…build" + a[len(str(out)):]
                    if i == 0 and os.path.isabs(a):
                        return os.path.relpath(a, root) if str(root) in a else os.path.basename(a)
                    return shlex.quote(a)
                label = " ".join(show(i, a) for i, a in enumerate(exe))
                term("$ " + label, "cmd")

                def done(code, text, secs, stopped):
                    if rid != self.run_id:
                        return
                    items = list(diag.items)
                    if code != 0 and not stopped:
                        d2 = Diag(root, files)
                        for ln in text.splitlines():
                            d2.feed(ln)
                        items += [dict(d, runtime=True) for d in d2.items if d not in items]
                    BUS.emit("diagnostics", items=items, runtime=True)
                    BUS.emit("run", state="done", ok=code == 0, stage="exec", code=code, seconds=secs, stopped=stopped, mode=mode,
                             errors=sum(1 for d in items if d["severity"] == "error"))
                self.session.start(exe, str(root), env, "run", on_exit=done, capture=True, label=label)
                if stdin:
                    time.sleep(0.15)
                    self.session.write(stdin if stdin.endswith("\n") else stdin + "\n")
            except Exception as e:  # noqa: BLE001
                term(str(e), "error")
                BUS.emit("run", state="done", ok=False, stage="start", code=-1, mode=mode, seconds=0)
            finally:
                self.run_lock.release()
        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True}

    LIVE_SKIP = {"kotlin", "csharp"}            # vérifications trop lentes pour tourner à chaque frappe
    LIVE_LINKS = ("node_modules", ".venv", "venv")

    def live_check(self, project, target, docs):
        """Vérification silencieuse (pas de terminal) du projet avec le texte non enregistré de l'éditeur."""
        import hashlib
        root, x, files, main, v, bind = self.prepare(project, target, "check")
        if v is None or v.get("preview") or x["id"] in self.LIVE_SKIP:
            return {"ok": True, "supported": False, "items": []}
        key = hashlib.sha1(str(root).encode()).hexdigest()[:10]
        mirror = CACHE / "live" / key
        with self.live_locks.setdefault(key, threading.Lock()):
            if mirror.exists():
                shutil.rmtree(mirror, ignore_errors=True)
            mirror.mkdir(parents=True, exist_ok=True)
            docs = {f: t for f, t in (docs or {}).items() if isinstance(f, str) and isinstance(t, str) and f in files}
            for f in files:                       # fichiers modifiés : copie ; les autres : lien vers l'original
                dst = mirror / f
                dst.parent.mkdir(parents=True, exist_ok=True)
                if f in docs:
                    dst.write_text(docs[f], encoding="utf-8")
                else:
                    try:
                        dst.symlink_to(root / f)
                    except OSError:
                        pass
            for d in self.LIVE_LINKS:
                if (root / d).is_dir() and not (mirror / d).exists():
                    (mirror / d).symlink_to(root / d)
            out = self.build_dir(root) / "live"
            out.mkdir(parents=True, exist_ok=True)
            env = self.env_for({k: self.fill([val], root, files, main, bind, out)[0] for k, val in (v.get("env") or {}).items()}, colors=False)
            diag = LiveDiag(mirror, root, files)
            ok = True
            for c in v.get("build", []):
                cmd = self.fill(c, root, files, main, bind, out)
                try:
                    r = subprocess.run(cmd, cwd=str(mirror), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       stdin=subprocess.DEVNULL, text=True, errors="replace", timeout=30)
                except subprocess.TimeoutExpired:
                    return {"ok": False, "supported": True, "items": diag.items, "timeout": True}
                except OSError as e:
                    return {"ok": False, "supported": False, "items": [], "error": str(e)}
                for ln in r.stdout.splitlines():
                    diag.feed(ln)
                if r.returncode != 0:
                    ok = False
                    break
            return {"ok": ok, "supported": True, "items": diag.items, "lang": x["id"], "files": files}

    def stream(self, cmd, cwd, env, diag=None, timeout=900, slot="proc"):
        """Commande non interactive (compilation, installation) : sortie diffusée ligne par ligne dans le terminal."""
        flag = "cancelled" if slot == "proc" else "run_cancelled"
        if getattr(self, flag):
            return 130
        term("$ " + " ".join(shlex.quote(a) for a in cmd) if isinstance(cmd, list) else "$ " + cmd, "cmd")
        env = dict(env, NO_COLOR="1", TERM="dumb")
        env.pop("FORCE_COLOR", None)
        env.pop("CLICOLOR_FORCE", None)
        try:
            proc = subprocess.Popen(cmd, cwd=str(cwd), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                    text=True, bufsize=1, errors="replace", shell=isinstance(cmd, str), start_new_session=True)
        except OSError as e:
            term(f"Impossible de lancer {cmd[0] if isinstance(cmd, list) else cmd} : {e.strerror or e}", "error")
            return 127
        setattr(self, slot, proc)
        t0 = last_prog = time.time()
        for raw in proc.stdout:
            for line in raw.rstrip("\n").split("\r"):
                if not line.strip():
                    continue
                if re.search(r"\d+(?:[.,]\d+)?\s?%\s*$", line) and not line.strip().startswith("100"):
                    if time.time() - last_prog < 0.8 and not re.search(r"100(?:[.,]0)?\s?%\s*$", line):
                        continue                    # barre de progression : une mise à jour par seconde environ suffit
                    last_prog = time.time()
                    line = re.sub(r"^[#=\-O\s>]{20,}", lambda m: "#" * min(40, len(m.group(0)) // 4) + " ", line)
                low = line.lower()
                kind = "out"
                if re.search(r"\berror\b|\berreur\b|fatal|failed|échec|e: ", low):
                    kind = "error"
                elif re.search(r"\bwarning\b|avertissement|\bwarn\b", low):
                    kind = "warn"
                BUS.emit("term", text=line + "\n", kind=kind)
                if diag:
                    diag.feed(line)
            if time.time() - t0 > timeout:
                proc.kill()
        code = proc.wait()
        setattr(self, slot, None)
        return 130 if getattr(self, flag) else code

    def interactive(self, project, what):
        """Console interactive du langage (repl) ou shell dans le dossier du projet."""
        root = self.project_dir(project)
        if what == "shell":
            sh = os.environ.get("SHELL") or "/bin/bash"
            cmd = [sh, "--norc", "--noprofile", "-i"] if sh.endswith("bash") else [sh, "-i"]
            self.session.stop()
            self.session.start(cmd, str(root), self.env_for({"PS1": "\\W $ "}, colors=False), "shell")
            return {"ok": True}
        info = self.project(project)
        x = EXT.get(info["lang"]) if info["lang"] else None
        if not x:
            raise RuntimeError("Langage du projet inconnu.")
        v, bind = self.resolve(x, "repl", root, info["files"], info["main"])
        if v is None:
            raise RuntimeError(f"Pas de console interactive pour {x['name']}. Utilisez le shell (bouton Shell) ou Exécuter.")
        out = self.build_dir(root)
        cmd = self.fill(v["exec"], root, info["files"], info["main"], bind, out)
        self.session.stop()
        self.session.start(cmd, str(root), self.env_for(v.get("env"), colors=False), "repl")
        return {"ok": True}

    # ----------------------------------------------------------------- formateurs et analyseurs
    def tool_for(self, lang, action, rel):
        suffix = Path(rel).suffix
        disabled = EXT.disabled()
        cands = []
        for t in EXT.items.values():
            if t["kind"] != "tool" or not t.get(action) or t["id"] in disabled:
                continue
            fx = t.get("format_exts")
            if lang in t.get("langs", []) or (fx and suffix in fx):
                cands.append(t)
        inst = [t for t in cands if EXT.installed(t)]
        return (inst[0] if inst else None), cands

    def format_file(self, project, rel, lang):
        p = self.file_path(project, rel)
        t, cands = self.tool_for(lang, "format", rel)
        if not t:
            names = ", ".join(c["name"] for c in cands) or "aucun formateur connu"
            raise RuntimeError(f"Aucun formateur installé pour ce fichier. Extensions possibles : {names}.")
        cmd = [a.replace("{file}", str(p)) for a in t["format"]]
        before = p.read_text(errors="replace")
        code, out = run_quiet(cmd, 30, cwd=str(p.parent))
        after = p.read_text(errors="replace")
        if code != 0:
            raise RuntimeError(f"{t['name']} : " + (out.strip().splitlines() or ["échec"])[-1][:300])
        self.bump_preview(project)
        return {"content": after, "changed": after != before, "tool": t["name"]}

    def lint_file(self, project, rel, lang):
        root = self.project_dir(project)
        p = self.file_path(project, rel)
        t, cands = self.tool_for(lang, "lint", rel)
        if not t:
            names = ", ".join(c["name"] for c in cands) or "aucun analyseur connu"
            raise RuntimeError(f"Aucun analyseur installé pour ce fichier. Extensions possibles : {names}.")
        cmd = [a.replace("{file}", rel) for a in t["lint"]]
        _, out = run_quiet(cmd, 60, cwd=str(root))
        d = Diag(root, self.walk(root))
        for ln in out.splitlines():
            d.feed(ln)
        for it in d.items:
            if t["id"] in ("ruff", "eslint", "shellcheck", "rubocop") and it["severity"] == "error" and not re.search(r"syntax|E9\d\d|parse", it["message"], re.I):
                it["severity"] = "warning"
        return {"items": d.items, "tool": t["name"], "raw": out[-4000:]}

    # ----------------------------------------------------------------- tâches (installations, paquets)
    def start_job(self, kind, target, *args, label=""):
        if not self.job_lock.acquire(blocking=False):
            raise RuntimeError("Une installation est déjà en cours.")
        self.job = {"kind": kind, "label": label, "started": time.time()}
        self.cancelled = False
        BUS.emit("job", state="running", kind=kind, label=label)

        def runner():
            ok = False
            try:
                ok = bool(target(*args))
            except Exception as e:  # noqa: BLE001
                term(f"Erreur : {e}", "error")
            finally:
                self.job = None
                self.proc = None
                self.job_lock.release()
                BUS.emit("job", state="idle", kind=kind, label=label, ok=ok)
        threading.Thread(target=runner, daemon=True).start()

    def cancel(self):
        self.cancelled = True
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGTERM)
            except OSError:
                self.proc.terminate()

    def stop_run(self):
        self.run_cancelled = True
        b = self.bproc
        if b and b.poll() is None:
            try:
                os.killpg(b.pid, signal.SIGTERM)
            except OSError:
                b.terminate()
        self.session.stop()

    def shell_cmd(self, cmd, root_needed):
        """Commande d'installation prête à lancer (liste pour subprocess), ou lève une erreur si les droits manquent."""
        if isinstance(cmd, str):
            cmd = ["sh", "-c", cmd]
        if root_needed:
            pre = root_prefix()
            if pre is None:
                raise PermissionError(" ".join(shlex.quote(c) for c in cmd))
            cmd = pre + cmd
        return cmd

    def ext_install(self, ext_id, remove=False):
        x = EXT.get(ext_id)
        if x.get("bundled") and not remove:
            host = EXT.items.get(x["bundled"])
            if host and not EXT.installed(host):
                return self.ext_install(host["id"])
        label, cmd, root_needed = EXT.install_plan(x, remove=remove)
        if not label:
            term(cmd, "error")
            toast(cmd, "error")
            return False
        term(f"{'Désinstallation' if remove else 'Installation'} de {x['name']} — {label}", "info")
        try:
            full = self.shell_cmd(cmd, root_needed)
        except PermissionError as e:
            line = f"sudo {e}"
            term("Droits administrateur nécessaires, et aucun moyen de les demander ici (ni sudo sans mot de passe, ni pkexec).", "error")
            term(f"Dans un terminal : ./code.sh install {ext_id}    (ou : {line})", "info")
            BUS.emit("need_root", ext=ext_id, name=x["name"], cmd=line)
            return False
        if full and full[0] == "pkexec":
            term("Une fenêtre va demander votre mot de passe administrateur.", "info")
        code = self.stream(full, HOME, self.env_for(colors=False), timeout=3600)
        forget_which()
        ok = code == 0 and (remove or EXT.installed(x))
        if ok:
            term(f"✔ {x['name']} {'désinstallé' if remove else 'installé'}" + (f" ({EXT.version(x)})" if not remove else ""), "ok")
            toast(f"{x['name']} {'désinstallé' if remove else 'installé'}", "ok")
            if not remove:
                EXT.set_enabled(ext_id, True)
        else:
            why = "installation terminée mais l'outil reste introuvable (ouvrez un nouveau terminal ou vérifiez le PATH)" if code == 0 else f"code {code}"
            term(f"✖ Échec : {why}", "error")
            toast(f"{x['name']} : échec ({why})", "error")
        BUS.emit("exts_changed")
        return ok

    # ----------------------------------------------------------------- paquets du projet
    def pkg_kind(self, project):
        info = self.project(project)
        x = EXT.items.get(info["lang"]) or {}
        return info, x.get("pkg")

    def pkgs(self, project):
        info, kind = self.pkg_kind(project)
        root = Path(info["path"])
        out = {"kind": kind, "items": [], "note": "", "ready": True}
        if kind == "pip":
            py = root / ".venv" / "bin" / "python"
            if not py.exists():
                out.update(ready=False, note="Aucun environnement virtuel : il sera créé (.venv) au premier paquet.")
                return out
            code, text = run_quiet([str(py), "-m", "pip", "list", "--format=json", "--disable-pip-version-check"], 30)
            try:
                items = json.loads(text[text.index("["):]) if code == 0 else []
            except ValueError:
                items = []
            out["items"] = [{"name": i["name"], "version": i["version"]} for i in items if i["name"] not in ("pip", "setuptools", "wheel")]
            out["note"] = "Paquets du .venv du projet (utilisé automatiquement à l'exécution)."
        elif kind == "npm":
            try:
                pj = json.loads((root / "package.json").read_text())
            except (OSError, ValueError):
                pj = {}
            deps = {**(pj.get("dependencies") or {}), **(pj.get("devDependencies") or {})}
            out["items"] = [{"name": k, "version": str(v).lstrip("^~")} for k, v in sorted(deps.items())]
            out["note"] = "Dépendances de package.json (node_modules dans le projet)."
        elif kind == "cargo":
            if not (root / "Cargo.toml").exists():
                out.update(ready=False, note="Le projet sera converti en projet Cargo (Cargo.toml) au premier paquet.")
                return out
            txt = (root / "Cargo.toml").read_text(errors="replace")
            m = re.search(r"^\[dependencies\]\s*$(.*?)(?=^\[|\Z)", txt, re.M | re.S)
            for ln in (m.group(1) if m else "").splitlines():
                k = re.match(r'^\s*([\w-]+)\s*=\s*(?:"([^"]*)"|\{.*?version\s*=\s*"([^"]*)")?', ln)
                if k:
                    out["items"].append({"name": k.group(1), "version": k.group(2) or k.group(3) or ""})
            out["note"] = "Dépendances de Cargo.toml (crates.io)."
        elif kind == "go":
            if not (root / "go.mod").exists():
                out.update(ready=False, note="go.mod sera créé au premier paquet.")
                return out
            txt = (root / "go.mod").read_text(errors="replace")
            for m in re.finditer(r"^\s*(?:require\s+)?([\w.\-/]+\.[\w.\-/]+)\s+(v[\w.\-+]+)", txt, re.M):
                out["items"].append({"name": m.group(1), "version": m.group(2)})
            out["note"] = "Modules de go.mod."
        elif kind in ("gem", "composer", "luarocks", "cran", "dotnet"):
            out["note"] = {"gem": "Gemmes installées pour votre utilisateur (gem install --user-install).",
                           "composer": "Paquets Composer du projet (composer.json).",
                           "luarocks": "Modules LuaRocks installés pour votre utilisateur (--local).",
                           "cran": "Paquets R installés dans votre bibliothèque personnelle.",
                           "dotnet": "Paquets NuGet ajoutés au .csproj."}[kind]
            if kind == "composer":
                try:
                    req = json.loads((root / "composer.json").read_text()).get("require") or {}
                    out["items"] = [{"name": k, "version": v} for k, v in req.items()]
                except (OSError, ValueError):
                    pass
        else:
            out.update(ready=False, note="Pas de gestionnaire de paquets pour ce langage.")
        return out

    def pkg_cmds(self, project, name, remove=False):
        info, kind = self.pkg_kind(project)
        root = Path(info["path"])
        if not re.fullmatch(r"[A-Za-z0-9@][\w.\-/@:=<>~^!*+ ,\[\]]{0,120}", name or ""):
            raise ValueError("Nom de paquet invalide")
        spec = shlex.split(name)
        cmds = []
        py3 = which("python3") or "python3"
        if kind == "pip":
            venv = root / ".venv"
            if not (venv / "bin" / "python").exists():
                if remove:
                    raise ValueError("Aucun environnement virtuel")
                cmds.append([py3, "-m", "venv", str(venv)])
            cmds.append([str(venv / "bin" / "python"), "-m", "pip", "uninstall" if remove else "install", *(["-y"] if remove else ["--disable-pip-version-check"]), *spec])
        elif kind == "npm":
            if not which("npm"):
                raise RuntimeError("npm est introuvable : installez l'extension JavaScript.")
            if not (root / "package.json").exists():
                (root / "package.json").write_text(json.dumps({"name": root.name.lower(), "version": "1.0.0", "private": True}, indent=2) + "\n")
            cmds.append(["npm", "uninstall" if remove else "install", "--no-fund", "--no-audit", *spec])
        elif kind == "cargo":
            if not which("cargo"):
                raise RuntimeError("cargo est introuvable : installez l'extension Rust.")
            if not (root / "Cargo.toml").exists():
                if remove:
                    raise ValueError("Pas de Cargo.toml")
                main = info["main"] or "main.rs"
                crate = re.sub(r"[^a-z0-9_]", "_", root.name.lower()).strip("_") or "app"
                (root / "Cargo.toml").write_text(f'[package]\nname = "{crate}"\nversion = "0.1.0"\nedition = "2021"\n\n[[bin]]\nname = "{crate}"\npath = "{main}"\n\n[dependencies]\n')
                term("Cargo.toml créé : le projet est maintenant un projet Cargo.", "info")
            cmds.append(["cargo", "remove" if remove else "add", *spec])
        elif kind == "go":
            if not (root / "go.mod").exists():
                cmds.append(["go", "mod", "init", re.sub(r"[^a-z0-9_.-]", "", root.name.lower()) or "app"])
            cmds.append(["go", "get", *(f"{s}@none" for s in spec)] if remove else ["go", "get", *spec])
            cmds.append(["go", "mod", "tidy"])
        elif kind == "gem":
            cmds.append(["gem", "uninstall", "--user-install", "-x", *spec] if remove else ["gem", "install", "--user-install", *spec])
        elif kind == "composer":
            if not which("composer"):
                raise RuntimeError("composer est introuvable (https://getcomposer.org).")
            cmds.append(["composer", "remove" if remove else "require", *spec])
        elif kind == "luarocks":
            if not which("luarocks"):
                raise RuntimeError("luarocks est introuvable (paquet « luarocks » de votre système).")
            cmds.append(["luarocks", "--local", "remove" if remove else "install", *spec])
        elif kind == "cran":
            lib = HOME / "R" / "library"
            lib.mkdir(parents=True, exist_ok=True)
            fn = "remove.packages" if remove else "install.packages"
            extra = "" if remove else ", repos='https://cloud.r-project.org'"
            cmds.append(["Rscript", "-e", f".libPaths('{lib}'); {fn}(c({', '.join(repr(s) for s in spec)}), lib='{lib}'{extra})"])
        elif kind == "dotnet":
            cmds.append(["dotnet", "remove" if remove else "add", "package", *spec])
        else:
            raise RuntimeError("Pas de gestionnaire de paquets pour ce langage.")
        return root, cmds

    def pkg_job(self, project, name, remove=False):
        root, cmds = self.pkg_cmds(project, name, remove)

        def go():
            term(f"{'Retrait' if remove else 'Ajout'} du paquet « {name} »…", "info")
            code = 0
            for c in cmds:
                code = self.stream(c, root, self.env_for(colors=False), timeout=1800)
                if code != 0:
                    break
            term("✔ Paquets à jour" if code == 0 else f"✖ Échec (code {code})", "ok" if code == 0 else "error")
            BUS.emit("pkgs_changed", project=project)
            return code == 0
        self.start_job("pkg", go, label=name)

    # ----------------------------------------------------------------- instantanés (git dans le dossier du projet)
    def git(self, root, *args, check=True, env=None):
        if not GIT and not which("git"):
            raise RuntimeError("git n'est pas installé : les instantanés sont indisponibles (extension Git).")
        g = GIT or which("git")
        e = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C", **(env or {}))
        if self._git_ident is None:
            self._git_ident = bool(subprocess.run([g, "config", "user.email"], capture_output=True, text=True, cwd=root).stdout.strip())
        if not self._git_ident:
            e.update(GIT_AUTHOR_NAME="Forge Code", GIT_AUTHOR_EMAIL="forge@localhost", GIT_COMMITTER_NAME="Forge Code", GIT_COMMITTER_EMAIL="forge@localhost")
        r = subprocess.run([g, "-c", f"core.hooksPath={os.devnull}", "-c", "core.quotepath=off", "-c", "commit.gpgsign=false",
                            "-c", "advice.defaultBranchName=false", "-C", str(root), *args],
                           capture_output=True, text=True, errors="replace", env=e, timeout=60)
        if check and r.returncode != 0:
            raise RuntimeError(r.stderr.strip() or "échec de git")
        return r

    def snap_repo(self, root, create=False):
        if (root / ".git").exists():
            return True
        if not create:
            return False
        self.git(root, "init", "-q")
        if not (root / ".gitignore").exists():
            (root / ".gitignore").write_text("build/\n.venv/\nnode_modules/\ntarget/\n__pycache__/\n")
        term("Dépôt git créé dans le dossier du projet (instantanés).", "info")
        return True

    def snap_head(self, root):
        r = self.git(root, "rev-parse", "--verify", "-q", "HEAD", check=False)
        return r.stdout.strip() if r.returncode == 0 else ""

    def snap_dirty(self, root):
        return bool(self.git(root, "status", "--porcelain").stdout.strip())

    def snap_tree(self, root):
        with tempfile.TemporaryDirectory() as d:
            env = {"GIT_INDEX_FILE": os.path.join(d, "index")}
            self.git(root, "add", "-A", env=env)
            return self.git(root, "write-tree", env=env).stdout.strip()

    def snap_rev(self, root, rev):
        if not re.fullmatch(r"[0-9a-f]{7,40}", rev or ""):
            raise ValueError("Instantané invalide")
        r = self.git(root, "rev-parse", "--verify", "-q", rev + "^{commit}", check=False)
        if r.returncode != 0:
            raise ValueError("Instantané introuvable")
        return r.stdout.strip()

    def snapshot(self, project, label="", auto=False):
        root = self.project_dir(project)
        with self.snap_lock:
            self.snap_repo(root, create=True)
            self.git(root, "add", "-A")
            if self.snap_head(root) and not self.snap_dirty(root):
                return {"created": False}
            label = " ".join(str(label or "").split())[:120] or time.strftime("Instantané du %d/%m/%Y à %H:%M")
            self.git(root, "commit", "-q", "--no-verify", "--allow-empty", "-m", ("[auto] " if auto else "") + label)
            h = self.snap_head(root)
        BUS.emit("snapshot", project=project, hash=h[:7], auto=auto)
        return {"created": True, "hash": h[:7]}

    def snapshots(self, project):
        root = self.project_dir(project)
        conf = self.conf(project).get("snapshots") or {}
        out = {"git": bool(GIT or which("git")), "repo": False, "items": [], "dirty": False, "auto": conf.get("auto", False) is True}
        if not out["git"] or not self.snap_repo(root):
            return out
        out["repo"] = True
        if self.snap_head(root):
            for line in self.git(root, "log", "-n", "100", "--format=%H%x1f%h%x1f%ct%x1f%s").stdout.splitlines():
                full, short, ts, subject = (line.split("\x1f") + ["", "", "", ""])[:4]
                auto = subject.startswith("[auto] ")
                out["items"].append({"rev": short, "time": int(ts or 0), "label": subject[7:] if auto else subject, "auto": auto})
        out["dirty"] = self.snap_dirty(root) if out["items"] else True
        return out

    def snap_changes(self, root, rev):
        tree = self.snap_tree(root)
        raw = self.git(root, "diff", "--name-status", "--no-renames", "--no-ext-diff", "-z", rev, tree).stdout.split("\0")
        return tree, [(raw[i], raw[i + 1]) for i in range(0, len(raw) - 1, 2) if raw[i]]

    def snap_diff(self, project, rev):
        root = self.project_dir(project)
        rev = self.snap_rev(root, rev)
        tree, changes = self.snap_changes(root, rev)
        patch = self.git(root, "diff", "--no-color", "--no-renames", "--no-ext-diff", "--no-textconv", "-U3", rev, tree).stdout
        return {"files": [{"status": st, "file": f} for st, f in changes], "patch": patch[:400_000], "truncated": len(patch) > 400_000}

    def snap_restore(self, project, rev):
        root = self.project_dir(project)
        rev = self.snap_rev(root, rev)
        safety = None
        if self.snap_dirty(root) or self.snap_changes(root, rev)[1]:
            safety = self.snapshot(project, f"Avant restauration de {rev[:7]}", auto=True).get("hash")
        _, changes = self.snap_changes(root, rev)
        back = [f for st, f in changes if st in ("M", "D", "T")]
        gone = [f for st, f in changes if st == "A"]
        base = root.resolve()
        for i in range(0, len(back), 40):
            self.git(root, "checkout", rev, "--", *back[i:i + 40])
        for rel in gone:
            target = (root / rel).resolve()
            if base in target.parents and ".git" not in target.relative_to(base).parts and target.is_file():
                target.unlink()
                for parent in target.parents:
                    if parent == base or any(parent.iterdir()):
                        break
                    parent.rmdir()
        BUS.emit("snapshot", project=project, hash=rev[:7], auto=False, restored=True)
        return {"restored": len(back), "deleted": len(gone), "safety": safety}

    # ----------------------------------------------------------------- export / import (.zip)
    def export_zip(self, project):
        root = self.project_dir(project)
        buf = io.BytesIO()
        count = 0
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = sorted(d for d in dirnames if d not in IGNORED_DIRS)
                for fn in sorted(filenames):
                    f = Path(dirpath) / fn
                    rel = f.relative_to(root)
                    if f.is_symlink() or rel.as_posix() in (CONF_FILE + ".tmp",) or f.stat().st_size > 50 * 1024 * 1024:
                        continue
                    z.write(f, f"{project}/{rel.as_posix()}")
                    count += 1
        return {"data": buf.getvalue(), "name": f"{project}.zip", "files": count}

    def import_zip(self, data):
        try:
            z = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            raise ValueError("Ce fichier n'est pas une archive .zip valide.")
        files = {}
        for info in z.infolist():
            name = info.filename.replace("\\", "/")
            parts = [x for x in name.split("/") if x not in ("", ".")]
            if info.is_dir() or not parts:
                continue
            if name.startswith("/") or ".." in parts or re.match(r"^[A-Za-z]:", parts[0]):
                raise ValueError(f"Chemin dangereux dans l'archive : {info.filename}")
            if ".git" in parts or "__MACOSX" in parts or parts[-1] == ".DS_Store" or any(p in IGNORED_DIRS for p in parts[:-1]):
                continue
            files[tuple(parts)] = info
        if not files:
            raise ValueError("L'archive est vide.")
        if len(files) > 3000 or sum(i.file_size for i in files.values()) > 300 * 1024 * 1024:
            raise ValueError("Archive trop volumineuse.")
        tops = {p[0] for p in files}
        root_dir = len(tops) == 1 and all(len(p) > 1 for p in files)
        stem = next(iter(tops)) if root_dir else "Importe"
        base = stem if valid_name(stem) else (re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("_.-")[:60] or "Importe")
        if not base[0].isalnum():
            base = "P_" + base
        name, n = base, 2
        while (self.workspace / name).exists():
            name, n = f"{base}_{n}", n + 1
        dest = self.workspace / name
        dest.mkdir()
        try:
            for parts, info in files.items():
                rel = parts[1:] if root_dir else parts
                target = dest.joinpath(*rel)
                if dest.resolve() not in target.resolve().parents:
                    raise ValueError("Chemin dangereux dans l'archive.")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(info))
        except Exception:
            shutil.rmtree(dest, ignore_errors=True)
            raise
        return {**self.project(name), "renamed": name != stem}

    # ----------------------------------------------------------------- aperçu web
    def bump_preview(self, project):
        self.preview_ver[project] = self.preview_ver.get(project, 0) + 1

    # ----------------------------------------------------------------- diagnostic
    def doctor(self):
        checks = []
        add = lambda status, title, detail, fix="": checks.append({"status": status, "title": title, "detail": detail, "fix": fix})  # noqa: E731
        add("ok", f"Python {platform.python_version()}", f"{sys.executable} · {platform.system()} {platform.release()}")
        pm = pkg_manager()
        add("ok" if pm else "warn", "Gestionnaire de paquets", PM_NAMES.get(pm, "") if pm else "Aucun reconnu : les langages s'installent à la main.")
        pre = root_prefix()
        if pre is None:
            add("warn", "Droits administrateur", "Ni sudo sans mot de passe ni pkexec : les installations système se font depuis un terminal.",
                "./code.sh install python")
        else:
            add("ok", "Droits administrateur", {0: "session root"}.get(len(pre), "via " + pre[0]) if pre else "session root")
        add("ok" if which("git") else "warn", "Git", EXT.version(EXT.items["git"]) if which("git") else "Absent : pas d'instantanés.",
            "" if which("git") else "./code.sh install git")
        langs = [x for x in EXT.langs()]
        have = [x for x in langs if EXT.installed(x)]
        add("ok" if have else "fail", f"{len(have)} langage(s) prêt(s) sur {len(langs)}", ", ".join(x["name"] for x in have) or "aucun")
        for x in have:
            v = EXT.version(x)
            add("ok", x["name"], f"{v} · {next((which(b) for b in x.get('bins', []) if which(b)), '') or 'intégré'}")
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)
        loc = str(HOME / ".local/bin")
        add("ok" if loc in path_dirs else "warn", "Outils utilisateur", f"{loc} est ajouté au PATH de Forge Code.")
        for e in EXT.custom_errors:
            add("fail", "Extension personnelle invalide", e)
        try:
            m, s = pty.openpty()
            os.close(m)
            os.close(s)
            add("ok", "Terminal (pseudo-terminal)", "Disponible : programmes interactifs, couleurs, Ctrl+C.")
        except OSError as e:
            add("fail", "Terminal (pseudo-terminal)", str(e))
        return checks

    def status(self):
        return {"version": VERSION, "workspace": str(self.workspace), "projects": self.projects(), "meta": self.meta(),
                "session": {"running": self.session.running, "kind": self.session.kind},
                "job": self.job, "pm": pkg_manager(), "system": f"{platform.system()} {platform.machine()}"}


# --------------------------------------------------------------------------- parcours : grades et défis
# Le contenu (deux filières, « dev » et « math », de 12 paliers et 13 grades, avec solutions en C, C++, Python,
# JavaScript et PHP) vit dans le paquet « parcours » à côté de ce fichier. Les tests passant par l'entrée/sortie
# standard, le parcours fonctionne dans tous les langages ; chaque langage a son propre grade dans chaque filière.
# Vérification : python3 -m parcours.verifier
sys.path.insert(0, str(Path(__file__).resolve().parent))
import parcours  # noqa: E402
from parcours import CH_BY_ID, CHALLENGES, LEVELS, SOL_LANGS, STAGES, STAGE_THEMES, TRACKS  # noqa: E402,F401

PROG_FILE = CONFIG / "progress.json"
CH_DIR = CONFIG / "challenges"                # défis personnels (*.json)
EXAM_COOLDOWN = 10 * 60                        # après un examen raté : 10 minutes avant de retenter
ACHIEVEMENTS = [
    ("premier", "🎉", "Hello, world!", "Réussir un premier défi."),
    ("dupremier", "🎯", "Du premier coup", "Réussir un défi à la première soumission."),
    ("autonome", "🧠", "Autodidacte", "Réussir 10 défis sans indice."),
    ("orfevre", "🥇", "Orfèvre", "Obtenir 5 médailles d'or."),
    ("apprenti", "☕", "Premier contrat", "Devenir Dev Junior dans un langage."),
    ("forgeron", "🧱", "Senior", "Devenir Dev Senior dans un langage."),
    ("architecte", "🏛️", "Architecte", "Devenir Architecte logiciel dans un langage."),
    ("cto", "🚀", "Aux commandes", "Devenir CTO dans un langage."),
    ("legende", "👑", "Légende vivante", "Devenir Légende du code dans un langage."),
    ("bilingue", "🌍", "Bilingue", "Devenir Développeur dans deux langages."),
    ("polyglotte", "🗺️", "Polyglotte", "Devenir Développeur dans trois langages."),
    ("fullstack", "🧩", "Couteau suisse", "Réussir un même défi en C, C++, Python, JavaScript et PHP."),
    ("centurion", "💯", "Centurion", "Réussir 100 défis (tous langages confondus)."),
    ("debogueur", "🐛", "Chasseur de bugs", "Réussir tous les défis de débogage dans un langage."),
    ("perfection", "💎", "Perfectionniste", "Obtenir l'or sur tous les défis d'un palier."),
    ("assidu", "📅", "Assidu", "Série de 3 jours."),
    ("inarretable", "⚡", "Inarrêtable", "Série de 7 jours."),
    ("marathon", "🏃", "Marathonien", "Série de 30 jours."),
    ("rdv", "☀️", "Rendez-vous", "Réussir un défi du jour."),
    ("eclair", "🏎️", "Éclair", "Réussir un examen en moins de la moitié du temps prévu."),
    ("tenace", "🪨", "Tenace", "Réussir un défi après au moins 5 échecs."),
    ("memoire", "🐘", "Mémoire d'éléphant", "Refaire un défi en mode révision."),
    ("nuit", "🦉", "Oiseau de nuit", "Réussir un défi entre minuit et 5 h."),
    ("createur", "🛠️", "Créateur", "Ajouter un défi personnel."),
    ("theoreme", "✏️", "Premier théorème", "Devenir Taupin dans un langage (filière Mathématicien)."),
    ("agrege", "🎓", "Reçu à l'agrégation", "Devenir Agrégé dans un langage (filière Mathématicien)."),
    ("docteur", "📜", "Thèse soutenue", "Devenir Docteur dans un langage (filière Mathématicien)."),
    ("fields", "🏅", "Médaille Fields", "Obtenir la médaille Fields dans un langage."),
    ("infini", "♾️", "Vers l'infini", "Devenir Légende des mathématiques dans un langage."),
    ("double", "🔀", "Double cursus", "Atteindre l'échelon 3 dans les deux filières, dans un même langage."),
]
MEDALS = {1: "bronze", 2: "argent", 3: "or"}


def _norm_out(t):
    return "\n".join(ln.rstrip() for ln in t.replace("\r\n", "\n").split("\n")).rstrip("\n")


class Progress:
    """Parcours de progression : grades par langage, défis corrigés par des tests, XP, médailles, succès."""

    def __init__(self, studio):
        self.studio = studio
        self.lock = threading.Lock()

    # ---------------------------------------------------------------- données
    def load(self):
        try:
            d = json.loads(PROG_FILE.read_text())
        except (OSError, ValueError):
            d = {}
        for k, v in (("xp", 0), ("langs", {}), ("done", {}), ("tries", {}), ("hints", {}), ("sol_seen", []), ("started", {}),
                     ("locks", {}), ("history", []), ("days", []), ("achievements", {}), ("reviews", {})):
            d.setdefault(k, v)
        return d

    def save(self, d):
        CONFIG.mkdir(parents=True, exist_ok=True)
        d["history"] = d["history"][-600:]
        tmp = PROG_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1))
        tmp.replace(PROG_FILE)

    def custom(self):
        out = []
        for f in sorted(CH_DIR.glob("*.json")) if CH_DIR.is_dir() else []:
            try:
                out.append(self.validate_custom(json.loads(f.read_text())))
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return out

    @staticmethod
    def validate_custom(c):
        if not isinstance(c, dict):
            raise ValueError("Un défi est un objet JSON.")
        cid = str(c.get("id", ""))
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,40}", cid):
            raise ValueError("« id » : minuscules, chiffres et tirets (ex. « mon-defi »).")
        tests = c.get("tests")
        if not isinstance(tests, list) or not tests or not all(isinstance(t, dict) and isinstance(t.get("in", ""), str) and isinstance(t.get("out"), str) for t in tests):
            raise ValueError("« tests » : liste de {\"in\": \"entrée\", \"out\": \"sortie attendue\", \"hidden\": false}.")
        lim = c.get("limits") if isinstance(c.get("limits"), dict) else {}
        kind = "exam" if c.get("kind") == "exam" else "mini"
        return {"id": "perso-" + cid, "stage": -1, "kind": kind, "title": str(c.get("title") or cid)[:80], "tag": "", "starter": {},
                "theme": str(c.get("theme") or "personnel")[:30], "desc": str(c.get("desc") or "")[:4000],
                "tests": [{"in": t.get("in", ""), "out": t["out"], "hidden": bool(t.get("hidden")), "gen": None, "auto": False} for t in tests[:60]],
                "hints": [str(h) for h in (c.get("hints") or [])][:5], "langs": c.get("langs") or [],
                "sol": {k: v for k, v in (c.get("solutions") or {}).items() if isinstance(v, str)},
                "xp": max(5, min(1000, int(c.get("xp") or 30))),
                "limits": {"time": float(lim.get("time", 2)), "minutes": int(lim.get("minutes", 0)), "max_lines": int(lim.get("max_lines", 0)),
                           "banned": lim.get("banned") if isinstance(lim.get("banned"), dict) else {}}}

    def add_custom(self, data):
        c = self.validate_custom(data)
        CH_DIR.mkdir(parents=True, exist_ok=True)
        (CH_DIR / (c["id"][6:] + ".json")).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        with self.lock:
            d = self.load()
            d["achievements"].setdefault("createur", time.time())
            self.save(d)
        return {"ok": True, "id": c["id"]}

    def delete_custom(self, cid):
        f = CH_DIR / (str(cid).replace("perso-", "", 1) + ".json")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,40}", f.stem) or not f.is_file():
            raise ValueError("Défi personnel introuvable")
        f.unlink()
        return {"ok": True}

    def get(self, cid):
        c = CH_BY_ID.get(cid) or next((x for x in self.custom() if x["id"] == cid), None)
        if not c:
            raise ValueError("Défi inconnu")
        return c

    @staticmethod
    def track_langs():
        return [x for x in EXT.langs() if x["id"] != "web" and x.get("run")]

    # ---------------------------------------------------------------- règles
    @staticmethod
    def gkey(track):
        """Clé du grade dans progress.json : « grade » pour la filière dev (compatibilité), « grade_math »…"""
        return "grade" if track == "dev" else f"grade_{track}"

    def grade(self, d, lang, track="dev"):
        return int(d["langs"].get(lang, {}).get(self.gkey(track), 0))

    @staticmethod
    def track_of(c):
        return c.get("track") or "dev"

    def status(self, d, lang, c):
        key = f"{lang}/{c['id']}"
        if key in d["done"]:
            return "done"
        if c["stage"] < 0 or c["stage"] <= self.grade(d, lang, self.track_of(c)):
            return "open"
        return "locked"

    @staticmethod
    def streak(d):
        days = set(d["days"])
        day = time.strftime("%Y-%m-%d")
        t = time.time()
        if day not in days:
            t -= 86400
        n = 0
        while time.strftime("%Y-%m-%d", time.localtime(t)) in days:
            n += 1
            t -= 86400
        return n

    def daily(self, d, lang, track="dev"):
        """Défi du jour du langage et de la filière : tiré (toujours le même pour la journée) parmi les défis ouverts et pas encore en or."""
        cands = []
        for x in self.track_langs():
            if x["id"] != lang:
                continue
            for c in CHALLENGES:
                if c["track"] != track:
                    continue
                k = f"{x['id']}/{c['id']}"
                if self.status(d, x["id"], c) != "locked" and d["done"].get(k, {}).get("medal", 0) < 3:
                    cands.append((x["id"], c["id"]))
        if not cands:
            return None
        import hashlib
        i = int(hashlib.sha1((time.strftime("%Y-%m-%d") + lang + ("" if track == "dev" else track)).encode()).hexdigest(), 16) % len(cands)
        return {"lang": cands[i][0], "id": cands[i][1], "title": CH_BY_ID[cands[i][1]]["title"]}

    # ---------------------------------------------------------------- vue d'ensemble
    def overview(self, lang, track="dev"):
        track = track if track in TRACKS else "dev"
        tname, ticon, tsub, levels, tstages, domains = TRACKS[track]
        chs = [c for c in CHALLENGES if c["track"] == track]
        ids = {c["id"] for c in chs}
        d = self.load()
        def used(l):
            p = l + "/"
            return d["langs"].get(l, {}).get("seen") or any(k.startswith(p) for k in list(d["done"]) + list(d["tries"]) + list(d["started"]))
        def mine(k, l):
            return k.startswith(l + "/") and k.split("/", 1)[1] in ids
        langs = [{"id": x["id"], "name": x["name"], "installed": EXT.installed(x), "grade": self.grade(d, x["id"], track),
                  "started": used(x["id"]) or self.grade(d, x["id"], track) > 0,
                  "xp": sum(v.get("xp", 0) for k, v in d["done"].items() if mine(k, x["id"])),
                  "done": sum(1 for k in d["done"] if mine(k, x["id"]))} for x in self.track_langs()]
        if not lang:
            lang = max(langs, key=lambda l: (l["started"], l["grade"], l["installed"]))["id"] if langs else "python"
        now = time.time()

        def item(c):
            k = f"{lang}/{c['id']}"
            dn = d["done"].get(k)
            return {"id": c["id"], "title": c["title"], "theme": c["theme"], "kind": c["kind"], "xp": c["xp"], "stage": c["stage"], "tag": c.get("tag", ""),
                    "status": self.status(d, lang, c), "medal": dn["medal"] if dn else 0, "tries": d["tries"].get(k, 0),
                    "lock": max(0, int(d["locks"].get(k, 0) - now)), "review": bool(dn and now - dn["date"] > 7 * 86400),
                    "active": k in d["started"] and not dn}
        stages = [{"index": s, "name": levels[s + 1][0], "icon": levels[s + 1][1], "theme": tstages[s][0], "domain": tstages[s][1], "about": tstages[s][2],
                   "items": [item(c) for c in chs if c["stage"] == s]} for s in range(len(tstages))]
        custom = [item(c) for c in self.custom() if not c["langs"] or lang in c["langs"]] if track == "dev" else []
        # compétences : par thème, défis réussis et échecs
        skills = {}
        for c in chs:
            s = skills.setdefault(c["theme"], {"theme": c["theme"], "total": 0, "done": 0, "fails": 0})
            s["total"] += 1
            s["done"] += f"{lang}/{c['id']}" in d["done"]
        for h in d["history"]:
            if mine(h["key"], lang) and not h["ok"]:
                c = CH_BY_ID.get(h["key"].split("/", 1)[1])
                if c:
                    skills[c["theme"]]["fails"] += 1
        sk = sorted(skills.values(), key=lambda s: s["theme"])
        weak = min((s for s in sk if s["done"] < s["total"]), key=lambda s: (s["done"] / s["total"], -s["fails"]), default=None)
        suggestion = None
        if weak:
            c = next((c for c in chs if c["theme"] == weak["theme"] and self.status(d, lang, c) == "open"), None)
            if c:
                suggestion = {"id": c["id"], "title": c["title"], "theme": weak["theme"]}
        hist = [h for h in d["history"] if mine(h["key"], lang)]
        reasons = {}
        for h in hist:
            if not h["ok"]:
                reasons[h.get("why", "wrong")] = reasons.get(h.get("why", "wrong"), 0) + 1
        oks = [h for h in hist if h["ok"] and h.get("secs")]
        stats = {"attempts": len(hist), "success": sum(1 for h in hist if h["ok"]), "reasons": reasons,
                 "avg_secs": round(sum(h["secs"] for h in oks) / len(oks)) if oks else 0,
                 "golds": sum(1 for k, v in d["done"].items() if mine(k, lang) and v["medal"] == 3),
                 "done": sum(1 for k in d["done"] if mine(k, lang))}
        # activité des 26 dernières semaines (tous langages) : jour → nombre de défis réussis
        heat = {}
        for h in d["history"]:
            if h["ok"]:
                day = time.strftime("%Y-%m-%d", time.localtime(h["t"]))
                heat[day] = heat.get(day, 0) + 1
        g = self.grade(d, lang, track)
        tracks = [{"id": t, "name": v[0], "icon": v[1], "sub": v[2], "grade": self.grade(d, lang, t), "level": v[3][self.grade(d, lang, t)][0],
                   "glyph": v[3][self.grade(d, lang, t)][1]} for t, v in TRACKS.items()]
        return {"lang": lang, "track": track, "tracks": tracks, "track_name": tname, "track_sub": tsub, "domains": domains,
                "langs": langs, "grade": g, "level": levels[g][0], "icon": levels[g][1], "levels": levels, "heat": heat,
                "today": time.strftime("%Y-%m-%d"), "sol_langs": list(SOL_LANGS), "all_done": len(d["done"]),
                "xp": d["xp"], "lxp": next((l["xp"] for l in langs if l["id"] == lang), 0), "total": len(chs),
                "streak": self.streak(d), "daily": self.daily(d, lang, track), "stages": stages, "custom": custom,
                "skills": sk, "suggestion": suggestion, "stats": stats, "recent": hist[-12:][::-1],
                "achievements": [{"id": a, "icon": i, "name": n, "desc": ds, "got": d["achievements"].get(a)} for a, i, n, ds in ACHIEVEMENTS]}

    def detail(self, lang, cid):
        d = self.load()
        c = parcours.remplir(self.get(cid), visibles=True)
        k = f"{lang}/{cid}"
        n = d["hints"].get(k, 0)
        dn = d["done"].get(k)
        tr = self.track_of(c)
        return {"id": cid, "lang": lang, "title": c["title"], "theme": c["theme"], "kind": c["kind"], "desc": c["desc"], "xp": c["xp"],
                "stage": c["stage"], "track": tr, "status": self.status(d, lang, c), "limits": c["limits"],
                "examples": [{"in": t["in"], "out": t["out"]} for t in c["tests"] if not t["hidden"]], "ntests": len(c["tests"]), "tag": c.get("tag", ""),
                "has_starter": lang in c.get("starter", {}), "sol_langs": sorted(c["sol"]),
                "hints": c["hints"][:n], "nhints": len(c["hints"]), "tries": d["tries"].get(k, 0), "medal": dn["medal"] if dn else 0,
                "started": d["started"].get(k), "active": k in d["started"] and not dn, "lock": max(0, int(d["locks"].get(k, 0) - time.time())),
                "has_solution": bool(c["sol"]), "sol_free": bool(dn), "sol_seen": k in d["sol_seen"],
                "project": self.project_name(lang, cid)}

    @staticmethod
    def project_name(lang, cid):
        return f"Defi-{lang}-{cid}"

    # ---------------------------------------------------------------- actions
    def starter(self, x, c):
        parcours.remplir(c, visibles=True)
        com = x.get("comment") or "#"
        main = x["main"]
        lines = [f"Défi « {c['title']} » ({'examen' if c['kind'] == 'exam' else 'mini-défi'} · {c['theme']})", ""]
        words, cur = c["desc"].split(), ""
        for w in words:
            if len(cur) + len(w) > 90:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        lines.append(cur)
        for i, t in enumerate(t for t in c["tests"] if not t["hidden"]):
            lines += ["", f"Exemple {i + 1} — entrée :"] + [f"    {ln}" for ln in t["in"].split("\n")[:8]]
            lines += ["sortie attendue :"] + [f"    {ln}" for ln in t["out"].split("\n")[:8]]
        lines += ["", "Soumettez avec « Soumettre » dans le panneau Défi, à droite (ou F6) : tests cachés en plus des exemples."]
        if x["id"] in ("web",) or com in ("<!--",):
            head = ""
        else:
            head = "\n".join((com + " " + ln).rstrip() for ln in lines) + "\n\n"
        skel = {
            "cpp": "#include <iostream>\n#include <string>\n\nint main() {\n    // À vous !\n    return 0;\n}\n",
            "c": "#include <stdio.h>\n\nint main(void) {\n    // À vous !\n    return 0;\n}\n",
            "python": "# À vous !\n",
            "javascript": "const lignes = require(\"fs\").readFileSync(0, \"utf8\").split(\"\\n\");\n// À vous !\n",
            "java": f"import java.util.*;\n\npublic class {Path(main).stem} {{\n    public static void main(String[] args) {{\n        Scanner sc = new Scanner(System.in);\n        // À vous !\n    }}\n}}\n",
            "rust": "use std::io::{self, Read};\n\nfn main() {\n    let mut entree = String::new();\n    io::stdin().read_to_string(&mut entree).unwrap();\n    // À vous !\n}\n",
            "go": "package main\n\nimport (\n\t\"bufio\"\n\t\"fmt\"\n\t\"os\"\n)\n\nfunc main() {\n\tr := bufio.NewReader(os.Stdin)\n\t_ = r\n\tfmt.Println() // À vous !\n}\n",
            "php": "<?php\n$ligne = trim(fgets(STDIN));\n// À vous !\n",
        }.get(x["id"], "")
        body = c.get("starter", {}).get(x["id"], skel)    # défi de débogage : le code à corriger est fourni
        if body.startswith("<?php"):                        # en PHP, tout ce qui précède <?php serait affiché
            return main, "<?php\n" + head + body[len("<?php"):].lstrip("\n")
        return main, head + body

    def start(self, lang, cid):
        x = EXT.get(lang)
        c = self.get(cid)
        with self.lock:
            d = self.load()
            if self.status(d, lang, c) == "locked":
                raise ValueError(f"Ce défi se débloque au grade {TRACKS[self.track_of(c)][3][c['stage']][0]} en {x['name']}.")
            k = f"{lang}/{cid}"
            d["started"].setdefault(k, time.time())
            d["langs"].setdefault(lang, {})["seen"] = True
            if k in d["done"] and time.time() - d["done"][k]["date"] > 7 * 86400:
                d["reviews"][k] = time.time()          # mode révision
            self.save(d)
        name = self.project_name(lang, cid)
        root = self.studio.workspace / name
        if not root.exists():
            main, body = self.starter(x, c)
            root.mkdir(parents=True)
            (root / main).write_text(body)
            (root / CONF_FILE).write_text(json.dumps({"lang": lang, "challenge": {"lang": lang, "id": cid}}, indent=1) + "\n")
            (root / ".gitignore").write_text("build/\n__pycache__/\ntarget/\n")
        return {"ok": True, "project": name}

    def abandon(self, lang, cid, reset=False):
        """Arrête un défi en cours : le chrono est remis à zéro ; « reset » efface aussi le projet du défi."""
        self.get(cid)
        k = f"{lang}/{cid}"
        with self.lock:
            d = self.load()
            d["started"].pop(k, None)
            d["reviews"].pop(k, None)
            self.save(d)
        name = self.project_name(lang, cid)
        root = self.studio.workspace / name
        if reset and root.is_dir():
            try:
                conf = json.loads((root / CONF_FILE).read_text())
            except (OSError, ValueError):
                conf = {}
            if conf.get("challenge") != {"lang": lang, "id": cid}:
                raise ValueError("Ce dossier n'est pas un projet de défi : il n'a pas été effacé.")
            shutil.rmtree(root, ignore_errors=True)
        return {"ok": True, "project": name, "deleted": bool(reset)}

    def hint(self, lang, cid):
        c = self.get(cid)
        with self.lock:
            d = self.load()
            k = f"{lang}/{cid}"
            n = min(len(c["hints"]), d["hints"].get(k, 0) + 1)
            d["hints"][k] = n
            self.save(d)
        return {"hints": c["hints"][:n], "nhints": len(c["hints"])}

    def solution(self, lang, cid):
        c = self.get(cid)
        with self.lock:
            d = self.load()
            k = f"{lang}/{cid}"
            if k not in d["done"] and d["tries"].get(k, 0) < 3:
                raise ValueError("La solution se débloque après la réussite, ou après 3 tentatives.")
            if k not in d["done"] and k not in d["sol_seen"]:
                d["sol_seen"].append(k)
                self.save(d)
        code_lang = lang if lang in c["sol"] else ("python" if "python" in c["sol"] else next(iter(c["sol"]), None))
        if not code_lang:
            raise ValueError("Pas de solution de référence pour ce défi.")
        return {"lang": code_lang, "code": c["sol"][code_lang], "all": c["sol"]}

    def judge(self, project, c, lang):
        """Compile une fois, puis exécute chaque test avec son entrée ; compare la sortie (espaces de fin ignorés)."""
        st = self.studio
        parcours.remplir(c)
        root, x, files, main, v, bind = st.prepare(project, "", "run")
        if x["id"] != lang:
            raise ValueError("Le projet n'est pas dans le langage du défi.")
        if v is None or not v.get("exec"):
            raise ValueError(f"{x['name']} ne sait pas exécuter ce projet.")
        src = (root / main).read_text(errors="replace")
        lim = c["limits"]
        code_lines = [ln for ln in src.split("\n") if ln.strip() and not ln.strip().startswith(x.get("comment") or "#")]
        if lim.get("max_lines") and len(code_lines) > lim["max_lines"]:
            return {"ok": False, "why": "constraint", "message": f"Contrainte : {len(code_lines)} lignes de code, {lim['max_lines']} au plus (commentaires et lignes vides non comptés)."}
        for rx in (lim.get("banned") or {}).get("*", []) + (lim.get("banned") or {}).get(lang, []):
            m = re.search(rx, src)
            if m:
                return {"ok": False, "why": "constraint", "message": f"Contrainte : « {m.group(0).strip()} » est interdit dans ce défi."}
        out = st.build_dir(root) / "judge"
        out.mkdir(parents=True, exist_ok=True)
        env = st.env_for({k: st.fill([val], root, files, main, bind, out)[0] for k, val in (v.get("env") or {}).items()}, colors=False)
        for cmd in v.get("build", []):
            try:
                r = subprocess.run(st.fill(cmd, root, files, main, bind, out), cwd=str(root), env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True, errors="replace", timeout=120)
            except subprocess.TimeoutExpired:
                return {"ok": False, "why": "compile", "message": "La compilation a pris plus de 2 minutes."}
            if r.returncode != 0:
                return {"ok": False, "why": "compile", "message": "Le programme ne compile pas.", "output": "\n".join(r.stdout.splitlines()[:40])}
        exe = st.fill(v["exec"], root, files, main, bind, out)
        results, why = [], None
        for t in c["tests"]:
            t0 = time.time()
            try:
                r = subprocess.run(exe, cwd=str(root), env=env, input=t["in"] + "\n", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, errors="replace", timeout=lim.get("time", 2) + 0.5)
                secs = time.time() - t0
                got, err = r.stdout, r.stderr
                if secs > lim.get("time", 2):
                    status = "timeout"
                elif r.returncode != 0 and _norm_out(got) != _norm_out(t["out"]):
                    status = "crash"
                else:
                    status = "ok" if _norm_out(got) == _norm_out(t["out"]) else "wrong"
            except subprocess.TimeoutExpired:
                secs, got, err, status = lim.get("time", 2), "", "", "timeout"
            res = {"status": status, "hidden": t["hidden"], "secs": round(secs, 3)}
            if not t["hidden"]:
                res.update({"input": t["in"][:2000], "expected": t["out"][:2000], "got": got[:2000], "stderr": err[-1500:]})
            elif status == "crash":
                res["stderr"] = err[-600:]
            results.append(res)
            if status != "ok" and not why:
                why = status
        passed = sum(1 for r in results if r["status"] == "ok")
        return {"ok": passed == len(results), "why": why, "passed": passed, "total": len(results), "results": results}

    def submit(self, lang, cid, project, pastes=0):
        c = self.get(cid)
        k = f"{lang}/{cid}"
        d = self.load()
        if self.status(d, lang, c) == "locked":
            raise ValueError("Ce défi n'est pas encore débloqué.")
        lock = d["locks"].get(k, 0) - time.time()
        if lock > 0:
            raise ValueError(f"Examen raté récemment : nouvel essai possible dans {int(lock // 60) + 1} min.")
        res = self.judge(project, c, lang)
        with self.lock:
            d = self.load()
            now = time.time()
            prev = d["done"].get(k)
            d["tries"][k] = d["tries"].get(k, 0) + 1
            secs = round(now - d["started"].get(k, now))
            d["history"].append({"t": now, "key": k, "ok": res["ok"], "why": None if res["ok"] else res.get("why") or "wrong",
                                 "passed": res.get("passed", 0), "total": res.get("total", len(c["tests"])), "secs": secs, "pastes": pastes})
            gained, new_ach, grade_up = 0, [], None
            if not res["ok"]:
                if c["kind"] == "exam" and res.get("why") != "compile":
                    d["locks"][k] = now + EXAM_COOLDOWN
            else:
                day = time.strftime("%Y-%m-%d")
                if day not in d["days"]:
                    d["days"].append(day)
                hints = d["hints"].get(k, 0)
                fails = sum(1 for h in d["history"] if h["key"] == k and not h["ok"])
                in_time = not c["limits"].get("minutes") or secs <= c["limits"]["minutes"] * 60
                medal = 1 if (hints or k in d["sol_seen"]) else 3 if (fails == 0 and in_time) else 2
                mult = {3: 1.5, 2: 1.2, 1: max(0.4, 1 - 0.15 * hints - (0.5 if k in d["sol_seen"] else 0))}[medal]
                full = round(c["xp"] * mult)
                daily = self.daily(d, lang, self.track_of(c))
                is_daily = bool(daily and daily["lang"] == lang and daily["id"] == cid)
                if is_daily:
                    full *= 2
                if prev:
                    review = k in d["reviews"]
                    gained = max(0, full - prev.get("xp", 0)) if medal > prev["medal"] else 0
                    if review:
                        gained += round(c["xp"] * 0.3)
                        d["reviews"].pop(k, None)
                        d["achievements"].setdefault("memoire", now)
                    prev.update({"medal": max(prev["medal"], medal), "date": now, "xp": prev.get("xp", 0) + gained})
                else:
                    gained = full
                    d["done"][k] = {"medal": medal, "date": now, "first": now, "attempts": d["tries"][k], "secs": secs, "hints": hints, "xp": full}
                d["xp"] += gained
                d["started"].pop(k, None)
                tr = self.track_of(c)
                if c["kind"] == "exam" and c["stage"] >= 0 and self.grade(d, lang, tr) == c["stage"]:
                    lv = TRACKS[tr][3]
                    d["langs"].setdefault(lang, {})[self.gkey(tr)] = c["stage"] + 1
                    grade_up = {"grade": c["stage"] + 1, "name": lv[c["stage"] + 1][0], "icon": lv[c["stage"] + 1][1], "lang": lang, "track": tr}
                # succès
                A = d["achievements"]
                done = d["done"].values()
                grades = [int(v.get("grade", 0)) for v in d["langs"].values()]
                mgrades = [int(v.get("grade_math", 0)) for v in d["langs"].values()]
                checks = {
                    "premier": True, "dupremier": fails == 0,
                    "autonome": sum(1 for v in done if not v.get("hints")) >= 10,
                    "orfevre": sum(1 for v in done if v["medal"] == 3) >= 5,
                    "apprenti": max(grades, default=0) >= 2, "forgeron": max(grades, default=0) >= 5, "architecte": max(grades, default=0) >= 8,
                    "cto": max(grades, default=0) >= 11, "legende": max(grades, default=0) >= len(STAGES),
                    "bilingue": sum(g >= 3 for g in grades) >= 2, "polyglotte": sum(g >= 3 for g in grades) >= 3,
                    "fullstack": all(f"{l}/{cid}" in d["done"] for l in SOL_LANGS),
                    "centurion": len(d["done"]) >= 100,
                    "debogueur": all(f"{lang}/{x['id']}" in d["done"] for x in CHALLENGES if x.get("tag") == "debug"),
                    "perfection": c["stage"] >= 0 and all(d["done"].get(f"{lang}/{x['id']}", {}).get("medal") == 3 for x in CHALLENGES
                                                          if x["stage"] == c["stage"] and x["track"] == tr),
                    "theoreme": max(mgrades, default=0) >= 2, "agrege": max(mgrades, default=0) >= 4, "docteur": max(mgrades, default=0) >= 6,
                    "fields": max(mgrades, default=0) >= 11, "infini": max(mgrades, default=0) >= len(TRACKS["math"][4]),
                    "double": any(int(v.get("grade", 0)) >= 3 and int(v.get("grade_math", 0)) >= 3 for v in d["langs"].values()),
                    "assidu": self.streak(d) >= 3, "inarretable": self.streak(d) >= 7, "marathon": self.streak(d) >= 30, "rdv": is_daily,
                    "eclair": c["kind"] == "exam" and c["limits"].get("minutes") and secs <= c["limits"]["minutes"] * 30,
                    "tenace": fails >= 5, "nuit": time.localtime(now).tm_hour < 5,
                }
                for a, ok in checks.items():
                    if ok and a not in A:
                        A[a] = now
                        new_ach.append(next({"id": a, "icon": i, "name": n, "desc": ds} for aa, i, n, ds in ACHIEVEMENTS if aa == a))
                res["medal"] = d["done"][k]["medal"]
                res["daily"] = is_daily
            self.save(d)
        res.update({"gained": gained, "achievements": new_ach, "grade_up": grade_up, "xp": d["xp"], "tries": d["tries"][k],
                    "lock": max(0, int(d["locks"].get(k, 0) - time.time()))})
        return res


STUDIO = None
PROG = None


# --------------------------------------------------------------------------- aperçu web (sert les fichiers du projet)
PREVIEW_JS = """<script>(function(){var B=%s,v=null;
function send(k,a){try{fetch(B+"__log",{method:"POST",body:JSON.stringify({k:k,t:[].map.call(a,function(x){try{return typeof x==="string"?x:JSON.stringify(x)}catch(e){return String(x)}}).join(" ")})})}catch(e){}}
["log","info","warn","error"].forEach(function(k){var o=console[k];console[k]=function(){send(k,arguments);return o.apply(console,arguments)}});
addEventListener("error",function(e){send("error",[(e.message||"Erreur")+(e.filename?" ("+e.filename.split("/").pop()+":"+e.lineno+")":"")])});
setInterval(function(){fetch(B+"__v?"+Date.now()).then(function(r){return r.text()}).then(function(t){if(v!==null&&t!==v)location.reload();v=t}).catch(function(){})},700);
})();</script>"""


# --------------------------------------------------------------------------- serveur HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "ForgeCode/" + VERSION
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(self, data, ctype, extra=None):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def authorized(self, qs):
        return secrets.compare_digest(self.headers.get("X-Token", "") or qs.get("token", [""])[0], TOKEN)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def preview(self, path, method="GET"):
        import mimetypes
        parts = path.split("/", 4)          # ["", "preview", token, project, rest]
        if len(parts) < 4 or not secrets.compare_digest(parts[2], TOKEN):
            return self.send_json({"error": "non autorisé"}, 403)
        project, rest = parts[3], unquote(parts[4]) if len(parts) > 4 else ""
        base = f"/preview/{TOKEN}/{project}/"
        if rest == "__v":
            return self.send_bytes(str(STUDIO.preview_ver.get(project, 0)).encode(), "text/plain")
        if rest == "__log" and method == "POST":
            try:
                b = self.body()
                kind = {"warn": "warn", "error": "error"}.get(b.get("k"), "web")
                BUS.emit("term", text="[page] " + str(b.get("t", ""))[:2000] + "\n", kind=kind)
            except (ValueError, OSError):
                pass
            return self.send_json({"ok": True})
        try:
            root = STUDIO.project_dir(project)
            rest = rest or "index.html"
            p = (root / rest).resolve()
            if p.is_dir():
                p = p / "index.html"
            if root not in p.parents or ".git" in p.relative_to(root).parts or not p.is_file():
                raise ValueError
        except ValueError:
            return self.send_bytes(b"<h1>404</h1><p>Fichier introuvable.</p>", "text/html; charset=utf-8")
        ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        data = p.read_bytes()
        if ctype == "text/html":
            txt = data.decode("utf-8", "replace")
            inj = PREVIEW_JS % json.dumps(base)
            txt = re.sub(r"(<head[^>]*>)", lambda m: m.group(1) + inj, txt, count=1, flags=re.I) if re.search(r"<head[^>]*>", txt, re.I) else inj + txt
            data = txt.encode()
            ctype += "; charset=utf-8"
        elif ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        self.send_bytes(data, ctype)

    def do_GET(self):
        url = urlparse(self.path)
        qs = parse_qs(url.query)
        if url.path == "/":
            page = HTML.replace("__TOKEN__", TOKEN).encode()
            return self.send_bytes(page, "text/html; charset=utf-8")
        if url.path.startswith("/preview/"):
            return self.preview(url.path)
        if not self.authorized(qs):
            return self.send_json({"error": "non autorisé"}, 403)
        q = lambda k, d="": qs.get(k, [d])[0]  # noqa: E731
        try:
            p = url.path
            if p == "/api/events":
                return self.events()
            if p == "/api/status":
                return self.send_json(STUDIO.status())
            if p == "/api/projects":
                return self.send_json(STUDIO.projects())
            if p == "/api/prog":
                return self.send_json(PROG.overview(q("lang"), q("track") or "dev"))
            if p == "/api/prog/detail":
                return self.send_json(PROG.detail(q("lang"), q("id")))
            if p == "/api/project":
                return self.send_json(STUDIO.project(q("name")))
            if p == "/api/file":
                return self.send_json(STUDIO.read_file(q("project"), q("file")))
            if p == "/api/exts":
                if q("refresh") == "1":
                    forget_which()
                    EXT.load()
                return self.send_json({"items": [EXT.describe(x) for x in EXT.items.values()], "pm": pkg_manager(),
                                       "pmName": PM_NAMES.get(pkg_manager() or "", ""), "root": root_prefix() is not None,
                                       "errors": EXT.custom_errors, "dir": str(EXT_DIR)})
            if p == "/api/ext":
                x = EXT.get(q("id"))
                return self.send_json({k: v for k, v in x.items() if k != "source"})
            if p == "/api/pkgs":
                return self.send_json(STUDIO.pkgs(q("project")))
            if p == "/api/export":
                made = STUDIO.export_zip(q("project"))
                return self.send_bytes(made["data"], "application/zip", {"Content-Disposition": f'attachment; filename="{made["name"]}"'})
            if p == "/api/snapshots":
                return self.send_json(STUDIO.snapshots(q("project")))
            if p == "/api/snapshots/diff":
                return self.send_json(STUDIO.snap_diff(q("project"), q("rev")))
            if p == "/api/doctor":
                return self.send_json(STUDIO.doctor())
            if p == "/api/template":
                x = EXT.get(q("lang"))
                t = (x.get("templates") or {}).get(q("name"))
                if t is None:
                    raise ValueError("Modèle introuvable")
                files = t if isinstance(t, dict) else {x["main"]: t}
                return self.send_json({"files": {k: v for k, v in files.items()}})
        except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as e:
            return self.send_json({"error": str(e)}, 400)
        self.send_json({"error": "introuvable"}, 404)

    def do_POST(self):
        url = urlparse(self.path)
        if url.path.startswith("/preview/"):
            return self.preview(url.path, "POST")
        if not self.authorized(parse_qs(url.query)):
            return self.send_json({"error": "non autorisé"}, 403)
        try:
            p = url.path
            if p == "/api/import":
                n = int(self.headers.get("Content-Length") or 0)
                if n > 120 * 1024 * 1024:
                    raise ValueError("Archive trop volumineuse (120 Mo maximum).")
                return self.send_json(STUDIO.import_zip(self.rfile.read(n)))
            b = self.body()
            if p == "/api/file":
                return self.send_json(STUDIO.write_file(b["project"], b["file"], b["content"]))
            if p == "/api/file/new":
                return self.send_json(STUDIO.new_file(b["project"], b["file"], b.get("content")))
            if p == "/api/file/rename":
                return self.send_json(STUDIO.rename_file(b["project"], b["file"], b["to"]))
            if p == "/api/file/delete":
                return self.send_json(STUDIO.delete_file(b["project"], b["file"]))
            if p == "/api/conf":
                return self.send_json(STUDIO.set_conf(b["project"], b["section"], b["data"]))
            if p == "/api/meta":
                return self.send_json(STUDIO.set_meta(b.get("pinned"), b.get("opened")))
            if p == "/api/project/new":
                return self.send_json(STUDIO.new_project(b.get("name", ""), b.get("lang", "python"), b.get("template", "hello")))
            if p == "/api/project/lang":
                return self.send_json(STUDIO.set_lang(b["project"], b["lang"]))
            if p == "/api/run":
                if b.get("rows"):
                    STUDIO.session.resize(b["rows"], b.get("cols", 120))
                return self.send_json(STUDIO.run(b["project"], b.get("target", ""), b.get("args", ""), b.get("stdin", ""), b.get("mode", "run")))
            if p == "/api/stop":
                STUDIO.stop_run()
                return self.send_json({"ok": True})
            if p == "/api/stdin":
                STUDIO.session.write(str(b.get("text", "")))
                return self.send_json({"ok": True})
            if p == "/api/signal":
                STUDIO.session.signal(b.get("sig", "int"))
                return self.send_json({"ok": True})
            if p == "/api/resize":
                STUDIO.session.resize(b.get("rows", 32), b.get("cols", 120))
                return self.send_json({"ok": True})
            if p == "/api/interactive":
                if b.get("rows"):
                    STUDIO.session.resize(b["rows"], b.get("cols", 120))
                return self.send_json(STUDIO.interactive(b["project"], b.get("what", "repl")))
            if p == "/api/format":
                return self.send_json(STUDIO.format_file(b["project"], b["file"], b.get("lang", "")))
            if p == "/api/prog/start":
                return self.send_json(PROG.start(b["lang"], b["id"]))
            if p == "/api/prog/submit":
                return self.send_json(PROG.submit(b["lang"], b["id"], b["project"], int(b.get("pastes") or 0)))
            if p == "/api/prog/abandon":
                return self.send_json(PROG.abandon(b["lang"], b["id"], bool(b.get("reset"))))
            if p == "/api/prog/hint":
                return self.send_json(PROG.hint(b["lang"], b["id"]))
            if p == "/api/prog/solution":
                return self.send_json(PROG.solution(b["lang"], b["id"]))
            if p == "/api/prog/custom":
                return self.send_json(PROG.add_custom(b.get("data")))
            if p == "/api/prog/custom/delete":
                return self.send_json(PROG.delete_custom(b.get("id")))
            if p == "/api/live":
                return self.send_json(STUDIO.live_check(b["project"], b.get("file", ""), b.get("docs") or {}))
            if p == "/api/lint":
                return self.send_json(STUDIO.lint_file(b["project"], b["file"], b.get("lang", "")))
            if p == "/api/ext/install":
                x = EXT.get(b["id"])
                STUDIO.start_job("install", STUDIO.ext_install, b["id"], label=x["name"])
                return self.send_json({"ok": True})
            if p == "/api/ext/remove":
                x = EXT.get(b["id"])
                STUDIO.start_job("install", STUDIO.ext_install, b["id"], True, label=x["name"])
                return self.send_json({"ok": True})
            if p == "/api/ext/toggle":
                EXT.set_enabled(b["id"], bool(b.get("enabled")))
                BUS.emit("exts_changed")
                return self.send_json({"ok": True})
            if p == "/api/ext/custom":
                new_id = EXT.add_custom(b["ext"])
                forget_which()
                BUS.emit("exts_changed")
                return self.send_json({"ok": True, "id": new_id})
            if p == "/api/ext/custom/delete":
                EXT.delete_custom(b["id"])
                BUS.emit("exts_changed")
                return self.send_json({"ok": True})
            if p == "/api/pkgs/install":
                STUDIO.pkg_job(b["project"], b["name"])
                return self.send_json({"ok": True})
            if p == "/api/pkgs/remove":
                STUDIO.pkg_job(b["project"], b["name"], remove=True)
                return self.send_json({"ok": True})
            if p == "/api/cancel":
                STUDIO.cancel()
                return self.send_json({"ok": True})
            if p == "/api/snapshots/create":
                return self.send_json(STUDIO.snapshot(b["project"], b.get("label", ""), auto=bool(b.get("auto"))))
            if p == "/api/snapshots/restore":
                return self.send_json(STUDIO.snap_restore(b["project"], b["rev"]))
        except (ValueError, KeyError, OSError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError) as e:
            return self.send_json({"error": str(e)}, 400)
        self.send_json({"error": "introuvable"}, 404)

    def events(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        q = BUS.subscribe()
        try:
            self.wfile.write(b"retry: 1500\n\n")
            self.wfile.flush()
            while True:
                try:
                    msg = q.get(timeout=15)
                    self.wfile.write(f"data: {msg}\n\n".encode())
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            BUS.unsubscribe(q)
            self.close_connection = True


def free_port(preferred):
    for port in [preferred, *range(preferred + 1, preferred + 50)]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return 0


def open_window(url):
    """Fenêtre « application » (sans barre d'adresse) si Chrome/Chromium/Edge est présent."""
    for b in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "brave-browser"):
        exe = shutil.which(b)
        if exe:
            subprocess.Popen([exe, f"--app={url}", "--window-size=1440,900"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            return
    webbrowser.open(url)


# --------------------------------------------------------------------------- commandes sans interface
def cli_list():
    rows = []
    for x in EXT.items.values():
        d = EXT.describe(x)
        state = "✔ installé " if d["installed"] else "· absent   "
        if not d["enabled"]:
            state = "⊘ désactivé"
        rows.append((x["kind"], x["id"], state, d["version"] or "", d["plan"] or d["why"]))
    for kind, title in (("lang", "Langages"), ("tool", "Outils")):
        print(f"\n{title}")
        for k, i, st, v, how in rows:
            if k == kind:
                print(f"  {i:<13} {st}  {v:<16.16} {'' if st.startswith('✔') else how}")
    print()


def cli_install(ids, remove=False):
    code = 0
    for ext_id in ids:
        try:
            x = EXT.get(ext_id)
        except ValueError as e:
            print(f"✖ {e}", file=sys.stderr)
            code = 1
            continue
        if not remove and EXT.installed(x):
            print(f"✔ {x['name']} est déjà installé ({EXT.version(x)})")
            continue
        label, cmd, root_needed = EXT.install_plan(x, remove=remove)
        if not label:
            print(f"✖ {x['name']} : {cmd}", file=sys.stderr)
            code = 1
            continue
        full = ["sh", "-c", cmd] if isinstance(cmd, str) else cmd
        if root_needed and os.geteuid() != 0:
            full = ["sudo"] + full if shutil.which("sudo") else ["su", "-c", " ".join(shlex.quote(c) for c in full)]
        print(f"➜ {'Désinstallation' if remove else 'Installation'} de {x['name']} — {label}")
        print("  $ " + " ".join(shlex.quote(c) for c in full))
        r = subprocess.run(full, cwd=str(HOME))
        forget_which()
        if r.returncode == 0 and (remove or EXT.installed(x)):
            print(f"✔ {x['name']} {'désinstallé' if remove else 'installé'} {EXT.version(x) if not remove else ''}")
            if not remove:
                EXT.set_enabled(ext_id, True)
        else:
            print(f"✖ Échec pour {x['name']} (code {r.returncode})", file=sys.stderr)
            code = 1
    return code


def cli_run(path, args):
    f = Path(path).expanduser().resolve()
    if not f.is_file():
        print(f"✖ Fichier introuvable : {path}", file=sys.stderr)
        return 1
    x = next((l for l in EXT.langs() if f.suffix in l.get("exts", []) and l["id"] != "web"), None)
    if not x:
        print(f"✖ Aucun langage installé ne gère les fichiers {f.suffix}", file=sys.stderr)
        return 1
    root = f.parent
    files = [p.name for p in sorted(root.iterdir()) if p.is_file()]
    st = Studio.__new__(Studio)
    st.session = Session()
    try:
        v, bind = st.resolve(x, "run", root, files, f.name)
    except RuntimeError as e:
        print(f"✖ {e}", file=sys.stderr)
        return 1
    out = CACHE / "build" / "cli"
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, **{k: st.fill([val], root, files, f.name, bind, out)[0] for k, val in (v.get("env") or {}).items()})
    for c in v.get("build", []):
        cmd = st.fill(c, root, files, f.name, bind, out)
        r = subprocess.run(cmd, cwd=str(root), env=env)
        if r.returncode != 0:
            return r.returncode
    cmd = st.fill(v["exec"], root, files, f.name, bind, out) + list(args)
    try:
        return subprocess.run(cmd, cwd=str(root), env=env).returncode
    except KeyboardInterrupt:
        return 130


def run_tool(a, ws):
    def project(arg):
        d = Path(arg).expanduser().resolve()
        if d.is_dir():
            return Studio(d.parent), d.name
        return Studio(ws), arg
    try:
        if a.export:
            st, name = project(a.export)
            made = st.export_zip(name)
            out = Path(a.output or made["name"]).expanduser()
            if out.is_dir():
                out = out / made["name"]
            out.write_bytes(made["data"])
            print(f"✔ Exporté : {out.resolve()} ({made['files']} fichiers)")
        elif a.import_file:
            src = Path(a.import_file).expanduser()
            if not src.is_file():
                raise ValueError(f"Fichier introuvable : {src}")
            st = Studio(ws)
            made = st.import_zip(src.read_bytes())
            print(f"✔ Projet « {made['name']} » importé dans {st.workspace / made['name']}" + (" (le nom d'origine existait déjà)" if made["renamed"] else ""))
        elif a.snapshot:
            st, name = project(a.snapshot)
            made = st.snapshot(name, a.message or "")
            print(f"✔ Instantané enregistré ({made['hash']})" if made["created"] else "➜ Rien de nouveau depuis le dernier instantané.")
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as e:
        print(f"✖ {e}", file=sys.stderr)
        return 1
    return 0


def main():
    global STUDIO, EXT, PROG
    if "--run" in sys.argv[1:]:                  # « --run fichier [--] args… » : les arguments vont au programme
        i = sys.argv.index("--run")
        if i + 1 >= len(sys.argv):
            sys.exit("✖ --run : indiquez un fichier")
        rest = sys.argv[i + 2:]
        EXT = Extensions()
        sys.exit(cli_run(sys.argv[i + 1], rest[1:] if rest[:1] == ["--"] else rest))
    ap = argparse.ArgumentParser(description="Forge Code — atelier de programmation multi-langages")
    ap.add_argument("workspace", nargs="?", default=None, help="dossier des projets (défaut : ~/Code)")
    ap.add_argument("--port", type=int, default=8724)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--list", action="store_true", help="liste les extensions (langages, outils) et leur état")
    ap.add_argument("--install", nargs="+", metavar="ID", help="installe des extensions, ex. --install python rust")
    ap.add_argument("--uninstall", nargs="+", metavar="ID", help="désinstalle des outils installés pour l'utilisateur")
    ap.add_argument("--run", metavar="FICHIER", help="exécute un fichier (langage deviné par l'extension)")
    ap.add_argument("--export", metavar="PROJET", help="exporte un projet en .zip puis quitte")
    ap.add_argument("--import", dest="import_file", metavar="FICHIER.zip", help="importe un projet depuis un .zip")
    ap.add_argument("--snapshot", metavar="PROJET", help="enregistre un instantané git du projet")
    ap.add_argument("--new", metavar="NOM", help="crée un projet (avec --lang et --template)")
    ap.add_argument("--lang", default="python", help="avec --new : langage (voir --list)")
    ap.add_argument("--template", default="hello", help="avec --new : hello, guess, plot ou empty")
    ap.add_argument("--doctor", action="store_true", help="diagnostique l'installation")
    ap.add_argument("-o", "--output", metavar="FICHIER", help="avec --export : fichier ou dossier de destination")
    ap.add_argument("-m", "--message", metavar="TEXTE", help="avec --snapshot : description")
    a, rest = ap.parse_known_args()
    if rest and not a.run:
        ap.error("arguments inconnus : " + " ".join(rest))

    EXT = Extensions()
    ws = Path(a.workspace or os.environ.get("FORGE_CODE_WORKSPACE") or HOME / "Code").expanduser()
    if a.list:
        cli_list()
        return
    if a.install or a.uninstall:
        sys.exit(cli_install(a.install or a.uninstall, remove=bool(a.uninstall)))
    if a.run:
        sys.exit(cli_run(a.run, [x for x in rest if x != "--"]))
    if a.export or a.import_file or a.snapshot:
        sys.exit(run_tool(a, ws))
    if a.new or a.doctor:
        st = Studio(ws)
        if a.doctor:
            for c in st.doctor():
                mark = {"ok": "✔", "warn": "⚠", "fail": "✖"}[c["status"]]
                print(f"{mark} {c['title']} — {c['detail']}" + (f"\n    ➜ {c['fix']}" if c.get("fix") else ""))
            return
        try:
            made = st.new_project(a.new, a.lang, a.template)
        except (ValueError, OSError) as e:
            print(f"✖ {e}", file=sys.stderr)
            sys.exit(1)
        x = EXT.get(a.lang)
        print(f"✔ Projet « {a.new} » ({x['name']}) créé dans {made['path']}")
        print(f"  Fichier principal : {made['main']}" + ("" if EXT.installed(x) else f"\n⚠ {x['name']} n'est pas installé : ./code.sh install {a.lang}"))
        return
    STUDIO = Studio(ws)
    PROG = Progress(STUDIO)

    port = free_port(a.port)
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.daemon_threads = True
    url = f"http://127.0.0.1:{port}/"
    threading.Thread(target=lambda: [EXT.describe(x) for x in list(EXT.items.values())], daemon=True).start()  # versions en cache

    print(f"\n  ⚡ Forge Code {VERSION}  →  {url}")
    print(f"     Projets : {STUDIO.workspace}")
    print("     Ctrl+C pour quitter\n")
    if not a.no_browser:
        threading.Timer(0.6, open_window, args=(url,)).start()

    def bye(*_):
        STUDIO.session.stop()
        print("\n  À bientôt !")
        os._exit(0)
    signal.signal(signal.SIGINT, bye)
    signal.signal(signal.SIGTERM, bye)
    srv.serve_forever()


HTML = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light">
<script>
/* Registre des modes : id, nom, famille (animations/illustrations), variantes (d = sombre, l = clair). */
const FORGE_MODES = [
  {"id": "tech", "name": "Tech", "desc": "Verre dépoli, turquoise et violet — précis", "fam": "tech", "v": "dl"},
  {"id": "hacker", "name": "Hacker · Phosphore", "desc": "Noir profond, vert phosphore, terminal CRT", "fam": "hacker", "v": "d"},
  {"id": "hacker2", "name": "Hacker · Cyberpunk", "desc": "Marine nuit, vert acide et magenta, cadres à équerres", "fam": "hacker", "v": "d"},
  {"id": "fleur", "name": "Fleur · Herbier", "desc": "Crème, vert sauge, rose poudré, terracotta, empattements", "fam": "fleur", "v": "l"},
  {"id": "fleur2", "name": "Fleur · Jardin de nuit", "desc": "Vert forêt, crème, rose et terracotta — version nocturne", "fam": "fleur", "v": "d"},
  {"id": "kawaii", "name": "Kawaii · Bonbon", "desc": "Rose, lavande, menthe, ciel — très arrondi", "fam": "kawaii", "v": "ld"},
  {"id": "kawaii2", "name": "Kawaii · Nuage", "desc": "Nuages lavande, bulles et boutons ronds", "fam": "kawaii", "v": "l"},
  {"id": "synthwave", "name": "Synthwave", "desc": "Magenta et cyan néon, grille et soleil couchant", "fam": "synth", "v": "d"},
  {"id": "papier", "name": "Papier", "desc": "Clair sobre, cahier quadrillé, plein jour", "fam": "papier", "v": "l"},
  {"id": "contraste", "name": "Contraste élevé", "desc": "WCAG AAA, bordures épaisses, sans transparence", "fam": "contraste", "v": "dl"}
];
function forgeTheme(p, m) {
  var w = p.theme === "light" || p.theme === "dark" ? p.theme : (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  return m.v.indexOf(w[0]) >= 0 ? w : (m.v[0] === "d" ? "dark" : "light");
}
function forgeApply(p) {
  var R = document.documentElement, m = FORGE_MODES.find(function (x) { return x.id === p.mode; }) || FORGE_MODES[0], t = forgeTheme(p, m);
  R.dataset.mode = m.id; R.dataset.theme = t;
  R.dataset.fx = p.fx === false ? "off" : "on";
  R.dataset.motion = (p.reduced === true || (p.reduced === undefined && matchMedia("(prefers-reduced-motion: reduce)").matches)) ? "reduced" : "full";
  R.dataset.dens = p.dens || "normal";
  if (m.id === "tech") R.removeAttribute("data-art"); else R.dataset.art = "1";
  return t;
}
try { forgeApply(JSON.parse(localStorage.getItem("forgecode.prefs")) || {}); } catch (e) { forgeApply({}); }
</script>
<title>Forge Code</title>
<meta name="theme-color" content="#070a0f" id="themeColor"><link id="fav" rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop offset='0' stop-color='%2319c3b3'/%3E%3Cstop offset='1' stop-color='%237c5cff'/%3E%3C/linearGradient%3E%3C/defs%3E%3Cpath d='M12 1.5 21.5 7v10L12 22.5 2.5 17V7z' fill='url(%23g)'/%3E%3Cpath d='m9.6 8.2-3.4 3.8 3.4 3.8M14.4 8.2l3.4 3.8-3.4 3.8' fill='none' stroke='white' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Fraunces:wght@500;700&family=Nunito:wght@400;600;700;800&family=Nunito+Sans:wght@400;600;700&family=Quicksand:wght@500;600;700&family=Orbitron:wght@600;800&family=Caveat:wght@600;700&display=swap" rel="stylesheet">
<style>
:root,[data-mode="tech"]{
  color-scheme:dark;
  --bg:#070a0f; --bg2:#0b1017; --panel:rgba(var(--panel-rgb),.72); --panel-solid:#111821; --panel2:rgba(var(--fg),.035);
  --line:rgba(var(--fg),.07); --line2:rgba(var(--fg),.12);
  --text:#e7edf4; --muted:#9aa7b8; --dim:#8b99ab;
  --accent:#19c3b3; --accent2:#7c5cff; --accent3:#35a6ff;
  --accent-rgb:25,195,179; --accent2-rgb:124,92,255; --accent3-rgb:53,166,255;
  --ok:#3ddc97; --warn:#ffb547; --err:#ff5c7a; --ok-rgb:61,220,151; --warn-rgb:255,181,71; --err-rgb:255,92,122;
  --on-accent:#04201d; --on-err:#26050d; --on-warn:#2a1a00; --on-ok:#06140e; --warn-text:#ffd08a;
  --grad:linear-gradient(135deg,var(--accent) 0%,var(--accent3) 50%,var(--accent2) 100%);
  --grad-btn:linear-gradient(135deg,#0b8378 0%,#1b64c4 55%,#5a3fd0 100%);
  --fg:255,255,255; --field:rgba(0,0,0,.25); --field2:rgba(0,0,0,.12);
  --panel-rgb:17,24,33; --scrim-rgb:3,6,10; --blob:.33;
  --radius:14px; --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --sans:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --panel-h:340px; --fs:13.5px; --lh:21px;
  --shadow:0 10px 40px -10px rgba(0,0,0,.6);
  --code:#cdd6e2; --caret:#5ff2e2; --sel:rgba(var(--accent3-rgb),.30);
  --tk-c:#7d8da1; --tk-s:#b5e48c; --tk-n:#ff9e64; --tk-k:#c792ea; --tk-t:#82aaff; --tk-f:#2de0cf; --tk-p:#ff7eb6; --tk-o:#89ddff; --tk-call:#e8c872; --ext-h:#a995ff; --info:#b9a8ff;
  --p0:#19c3b3;--p1:#8f7bff;--p2:#ffb547;--p3:#ff5c7a;--p4:#35a6ff;--p5:#7ddc5d;--p6:#ff7eb6;--p7:#e8c872;--p8:#ff8a4c;--p9:#c9d4e2;
  --plot-bg:#111821;--plot-grid:rgba(var(--fg),.06);--plot-zero:rgba(var(--fg),.2);--plot-text:#e7edf4;--plot-text2:#93a0b1;
  --blob1:#0e8f86; --blob2:#4b2fd0; --blob3:#1566b8; --on-grad:#fff; --knob:#fff; --pin-gnd:#5b6675; --sheen-rgb:255,255,255; --shade-rgb:0,0,0;
  --logo1:#19c3b3; --logo2:#7c5cff; --logo-bolt:#fff;   --dots:radial-gradient(rgba(var(--fg),.045) 1px,transparent 1px); --deco-img:none; --deco-size:auto; --deco-pos:0 0; --deco-rep:no-repeat; --deco-op:1; --overlay:none; --bw:1px; --dens:1;
  --art-welcome:none; --art-empty:none; --art-ok:none; --art-err:none;
  --rr:1; --glass-blur:22px; --glass-sat:140%; --spd:1; --font-head:var(--sans); --deco:1; --ink:#0b1017; --paper:#ffffff;
  --plat0:#19c3b3; --plat1:#ff5c7a; --plat2:#ffb547; --plat3:#ff7eb6; --plat4:#35a6ff; --plat5:#6b4cf5; --plat6:#3ddc97; --plat-x:#8a97a8;
  --burst1:#19c3b3; --burst2:#35a6ff; --burst3:#7c5cff; --burst4:#3ddc97; --burst5:#ffffff; --burst6:#ffb547;
  --d-find:rgba(var(--warn-rgb),.30); --d-cur:rgba(var(--accent-rgb),.55); --d-word:rgba(var(--accent2-rgb),.30); --d-br:rgba(var(--accent-rgb),.38);
}
:root[data-theme="light"],[data-mode="tech"][data-theme="light"]{
  color-scheme:light;
  --bg:#eaf0f6; --bg2:#f5f8fb; --panel:rgba(255,255,255,.74); --panel-solid:#ffffff; --panel2:rgba(15,23,42,.045);
  --line:rgba(15,23,42,.11); --line2:rgba(15,23,42,.18);
  --text:#0f1b2d; --muted:#475569; --dim:#526175;
  --accent:#08736a; --accent2:#5b3fd6; --accent3:#1a63b8;
  --accent-rgb:8,115,106; --accent2-rgb:91,63,214; --accent3-rgb:26,99,184;
  --ok:#157347; --warn:#9a5a00; --err:#c4193f; --ok-rgb:21,115,71; --warn-rgb:154,90,0; --err-rgb:196,25,63;
  --on-accent:#ffffff; --on-err:#ffffff; --on-warn:#ffffff; --on-ok:#ffffff; --warn-text:#7a4700;
  --grad:linear-gradient(135deg,#0a8f83 0%,#2a6fcf 50%,#6446dc 100%);
  --grad-btn:linear-gradient(135deg,#08736a 0%,#1a63b8 55%,#5b3fd6 100%);
  --fg:15,23,42; --field:rgba(255,255,255,.85); --field2:rgba(15,23,42,.05);
  --panel-rgb:255,255,255; --scrim-rgb:15,23,42; --blob:.16;
  --shadow:0 10px 34px -12px rgba(15,23,42,.28);
  --code:#1c2b3f; --caret:#08736a; --sel:rgba(26,99,184,.22);
  --tk-c:#5b6a7d; --tk-s:#2f7a16; --tk-n:#b4470b; --tk-k:#7b3fb8; --tk-t:#1e56b8; --tk-f:#08736a; --tk-p:#b0246e; --tk-o:#26647a; --tk-call:#8a5a00; --ext-h:#5b3fd6; --info:#5b3fd6;
  --p0:#08736a;--p1:#5b3fd6;--p2:#9a5a00;--p3:#c4193f;--p4:#1a63b8;--p5:#2f7a16;--p6:#b0246e;--p7:#7a6400;--p8:#b4470b;--p9:#475569;
  --plot-bg:#ffffff;--plot-grid:rgba(15,23,42,.08);--plot-zero:rgba(15,23,42,.28);--plot-text:#0f1b2d;--plot-text2:#526174;
  --d-find:rgba(154,90,0,.28); --d-cur:rgba(8,115,106,.38); --d-word:rgba(91,63,214,.22); --d-br:rgba(8,115,106,.28);
}
/* ================= MODES D'APPARENCE =================
   Chaque bloc ci-dessous définit TOUTES les variables d'un mode (sombre / clair).
   Pour ajouter un mode : copiez un bloc, changez data-mode et les valeurs, puis déclarez-le dans FORGE_MODES (en tête de page). */
/* ---- Hacker · Phosphore (sombre) ---- */
[data-mode="hacker"][data-theme="dark"]{
  color-scheme:dark;
  --bg:#030503;
  --bg2:#050b06;
  --panel-rgb:4,12,6;
  --panel:rgba(var(--panel-rgb),.9);
  --panel-solid:#050d06;
  --fg:51,255,102;
  --panel2:rgba(var(--fg),.05);
  --line:rgba(var(--fg),.30);
  --line2:rgba(var(--fg),.55);
  --text:#3dff72;
  --muted:#2fd05c;
  --dim:#25b04d;
  --accent:#33ff66;
  --accent2:#ffb547;
  --accent3:#00e5ff;
  --accent-rgb:51,255,102;
  --accent2-rgb:255,181,71;
  --accent3-rgb:0,229,255;
  --ok:#33ff66;
  --warn:#ffb547;
  --err:#ff5555;
  --ok-rgb:51,255,102;
  --warn-rgb:255,181,71;
  --err-rgb:255,85,85;
  --on-accent:#021a08;
  --on-err:#1f0000;
  --on-warn:#1a1000;
  --on-ok:#021a08;
  --warn-text:#ffc76b;
  --grad:linear-gradient(90deg,#33ff66,#00e5ff);
  --grad-btn:linear-gradient(#0c3a1a,#0c3a1a);
  --on-grad:#33ff66;
  --field:rgba(0,0,0,.6);
  --field2:rgba(0,0,0,.35);
  --scrim-rgb:0,6,2;
  --blob:0;
  --blob1:#000;
  --blob2:#000;
  --blob3:#000;
  --radius:0px;
  --rr:0;
  --sans:"JetBrains Mono","IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --font-head:var(--mono);
  --shadow:none;
  --glass-blur:0px;
  --glass-sat:100%;
  --spd:.8;
  --bw:1px;
  --code:#7dff9b;
  --caret:#33ff66;
  --sel:rgba(51,255,102,.28);
  --tk-c:#4fa868;
  --tk-s:#e6e64a;
  --tk-n:#ff9e4a;
  --tk-k:#33ff66;
  --tk-t:#00e5ff;
  --tk-f:#9dffb0;
  --tk-p:#ff7ab8;
  --tk-o:#7be7c1;
  --tk-call:#c9ff5a;
  --ext-h:#00e5ff;
  --info:#00e5ff;
  --p0:#33ff66;
  --p1:#00e5ff;
  --p2:#ffb547;
  --p3:#ff5566;
  --p4:#7ea0ff;
  --p5:#c8ff3a;
  --p6:#ff7ab8;
  --p7:#e8d44d;
  --p8:#ff8a4c;
  --p9:#b7ffce;
  --plot-bg:#030503;
  --plot-grid:rgba(var(--fg),.10);
  --plot-zero:rgba(var(--fg),.35);
  --plot-text:#3dff72;
  --plot-text2:#2fd05c;
  --d-find:rgba(var(--warn-rgb),.30);
  --d-cur:rgba(var(--accent-rgb),.55);
  --d-word:rgba(var(--accent2-rgb),.30);
  --d-br:rgba(var(--accent-rgb),.38);
  --logo1:#33ff66;
  --logo2:#00e5ff;
  --logo-bolt:#030503;
  --knob:#33ff66;
  --pin-gnd:#2fd05c;
  --sheen-rgb:51,255,102;
  --shade-rgb:0,0,0;
  --ink:#021a08;
  --paper:#33ff66;
  --dots:none;
  --deco-img:radial-gradient(ellipse at 50% 0%,rgba(51,255,102,.10),transparent 60%),url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20240%20240'%3E%3Ctext%20x='38'%20y='46'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.1'%3E%5B%3C/text%3E%3Ctext%20x='38'%20y='62'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.091'%3E1%3C/text%3E%3Ctext%20x='38'%20y='78'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.082'%3E%5C%3C/text%3E%3Ctext%20x='38'%20y='94'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.073'%3E%2A%3C/text%3E%3Ctext%20x='119'%20y='40'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.1'%3E/%3C/text%3E%3Ctext%20x='119'%20y='56'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.091'%3E%2A%3C/text%3E%3Ctext%20x='119'%20y='72'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.082'%3E%7D%3C/text%3E%3Ctext%20x='119'%20y='88'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.073'%3E1%3C/text%3E%3Ctext%20x='119'%20y='104'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.064'%3E%5C%3C/text%3E%3Ctext%20x='119'%20y='120'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.055'%3E0%3C/text%3E%3Ctext%20x='119'%20y='136'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.046'%3E/%3C/text%3E%3Ctext%20x='119'%20y='152'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.037'%3E/%3C/text%3E%3Ctext%20x='119'%20y='168'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.028'%3E%3E%3C/text%3E%3Ctext%20x='199'%20y='59'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.1'%3E%2B%3C/text%3E%3Ctext%20x='199'%20y='75'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.091'%3E%5C%3C/text%3E%3Ctext%20x='199'%20y='91'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.082'%3E%5B%3C/text%3E%3Ctext%20x='199'%20y='107'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.073'%3E%2B%3C/text%3E%3Ctext%20x='209'%20y='24'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.1'%3E1%3C/text%3E%3Ctext%20x='209'%20y='40'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.091'%3E%5D%3C/text%3E%3Ctext%20x='209'%20y='56'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.082'%3E0%3C/text%3E%3Ctext%20x='209'%20y='72'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.073'%3E0%3C/text%3E%3Ctext%20x='209'%20y='88'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.064'%3E0%3C/text%3E%3Ctext%20x='209'%20y='104'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.055'%3E=%3C/text%3E%3Ctext%20x='209'%20y='120'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.046'%3E%3C%3C/text%3E%3Ctext%20x='209'%20y='136'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.037'%3E0%3C/text%3E%3Ctext%20x='229'%20y='34'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.1'%3E%7D%3C/text%3E%3Ctext%20x='229'%20y='50'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.091'%3E/%3C/text%3E%3Ctext%20x='229'%20y='66'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.082'%3E%2B%3C/text%3E%3Ctext%20x='229'%20y='82'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.073'%3E0%3C/text%3E%3Ctext%20x='229'%20y='98'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.064'%3E%3C%3C/text%3E%3Ctext%20x='229'%20y='114'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.055'%3E%7D%3C/text%3E%3Ctext%20x='229'%20y='130'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.046'%3E%2A%3C/text%3E%3Ctext%20x='229'%20y='146'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.037'%3E%5C%3C/text%3E%3Ctext%20x='229'%20y='162'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.028'%3E%5C%3C/text%3E%3Ctext%20x='145'%20y='24'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.1'%3E%7D%3C/text%3E%3Ctext%20x='145'%20y='40'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.091'%3E=%3C/text%3E%3Ctext%20x='145'%20y='56'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.082'%3E%7D%3C/text%3E%3Ctext%20x='145'%20y='72'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.073'%3E%2A%3C/text%3E%3Ctext%20x='145'%20y='88'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.064'%3E%5C%3C/text%3E%3Ctext%20x='145'%20y='104'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.055'%3E%5B%3C/text%3E%3Ctext%20x='9'%20y='36'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.1'%3E=%3C/text%3E%3Ctext%20x='9'%20y='52'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.091'%3E1%3C/text%3E%3Ctext%20x='9'%20y='68'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.082'%3E%7B%3C/text%3E%3Ctext%20x='9'%20y='84'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.073'%3E=%3C/text%3E%3Ctext%20x='9'%20y='100'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.064'%3E%2B%3C/text%3E%3Ctext%20x='9'%20y='116'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.055'%3E%5B%3C/text%3E%3Ctext%20x='9'%20y='132'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.046'%3E1%3C/text%3E%3Ctext%20x='9'%20y='148'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.037'%3E%2B%3C/text%3E%3Ctext%20x='89'%20y='56'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.1'%3E%3C%3C/text%3E%3Ctext%20x='89'%20y='72'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.091'%3E/%3C/text%3E%3Ctext%20x='89'%20y='88'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.082'%3E%3C%3C/text%3E%3Ctext%20x='89'%20y='104'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.073'%3E=%3C/text%3E%3Ctext%20x='89'%20y='120'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.064'%3E%7D%3C/text%3E%3Ctext%20x='89'%20y='136'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.055'%3E%5B%3C/text%3E%3Ctext%20x='89'%20y='152'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.046'%3E%5B%3C/text%3E%3Ctext%20x='89'%20y='168'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.037'%3E%3E%3C/text%3E%3Ctext%20x='89'%20y='184'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.028'%3E%5C%3C/text%3E%3Ctext%20x='220'%20y='42'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.1'%3E%3E%3C/text%3E%3Ctext%20x='220'%20y='58'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.091'%3E0%3C/text%3E%3Ctext%20x='220'%20y='74'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.082'%3E%5C%3C/text%3E%3Ctext%20x='220'%20y='90'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.073'%3E%7D%3C/text%3E%3Ctext%20x='220'%20y='106'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.064'%3E%2B%3C/text%3E%3Ctext%20x='220'%20y='122'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.055'%3E%2A%3C/text%3E%3Ctext%20x='220'%20y='138'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.046'%3E/%3C/text%3E%3Ctext%20x='110'%20y='52'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.1'%3E%5D%3C/text%3E%3Ctext%20x='110'%20y='68'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.091'%3E%3C%3C/text%3E%3Ctext%20x='110'%20y='84'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.082'%3E%2B%3C/text%3E%3Ctext%20x='110'%20y='100'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.073'%3E%2A%3C/text%3E%3Ctext%20x='110'%20y='116'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.064'%3E=%3C/text%3E%3Ctext%20x='192'%20y='33'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.1'%3E%5C%3C/text%3E%3Ctext%20x='192'%20y='49'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.091'%3E=%3C/text%3E%3Ctext%20x='192'%20y='65'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.082'%3E%3C%3C/text%3E%3Ctext%20x='192'%20y='81'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.073'%3E1%3C/text%3E%3Ctext%20x='203'%20y='20'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.1'%3E/%3C/text%3E%3Ctext%20x='203'%20y='36'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.091'%3E%5D%3C/text%3E%3Ctext%20x='203'%20y='52'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.082'%3E%5C%3C/text%3E%3Ctext%20x='203'%20y='68'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.073'%3E%2B%3C/text%3E%3Ctext%20x='203'%20y='84'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.064'%3E0%3C/text%3E%3Ctext%20x='203'%20y='100'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.055'%3E%5C%3C/text%3E%3Ctext%20x='203'%20y='116'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.046'%3E0%3C/text%3E%3Ctext%20x='203'%20y='132'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.037'%3E%5B%3C/text%3E%3Ctext%20x='184'%20y='49'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.1'%3E%3E%3C/text%3E%3Ctext%20x='184'%20y='65'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.091'%3E/%3C/text%3E%3Ctext%20x='184'%20y='81'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.082'%3E=%3C/text%3E%3Ctext%20x='184'%20y='97'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.073'%3E%7B%3C/text%3E%3Ctext%20x='184'%20y='113'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.064'%3E%7B%3C/text%3E%3Ctext%20x='184'%20y='129'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.055'%3E%3C%3C/text%3E%3Ctext%20x='184'%20y='145'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.046'%3E%7D%3C/text%3E%3Ctext%20x='184'%20y='161'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.037'%3E0%3C/text%3E%3Ctext%20x='201'%20y='22'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.1'%3E%3C%3C/text%3E%3Ctext%20x='201'%20y='38'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.091'%3E%7D%3C/text%3E%3Ctext%20x='201'%20y='54'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.082'%3E/%3C/text%3E%3Ctext%20x='201'%20y='70'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.073'%3E%3C%3C/text%3E%3Ctext%20x='201'%20y='86'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.064'%3E%5D%3C/text%3E%3Ctext%20x='201'%20y='102'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.055'%3E%3E%3C/text%3E%3Ctext%20x='201'%20y='118'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.046'%3E%5D%3C/text%3E%3Ctext%20x='201'%20y='134'%20font-family='monospace'%20font-size='12'%20fill='%2333ff66'%20opacity='0.037'%3E%5C%3C/text%3E%3C/svg%3E");
  --deco-size:auto,240px 240px;
  --deco-pos:0 0;
  --deco-rep:no-repeat,repeat;
  --deco-op:1;
  --overlay:repeating-linear-gradient(0deg,rgba(0,0,0,.26) 0,rgba(0,0,0,.26) 1px,transparent 1px,transparent 3px);
  --burst1:#33ff66;
  --burst2:#00e5ff;
  --burst3:#ffb547;
  --burst4:#c8ff3a;
  --burst5:#ffffff;
  --burst6:#33ff66;
  --plat0:#33ff66;
  --plat1:#ff5566;
  --plat2:#ffb547;
  --plat3:#ff7ab8;
  --plat4:#00e5ff;
  --plat5:#c8ff3a;
  --plat6:#7dff9b;
  --plat-x:#2fd05c;
  --art-welcome:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20290%20150'%3E%3Ctext%20x='8'%20y='22'%20font-family='JetBrains%20Mono%2Cui-monospace%2CConsolas%2Cmonospace'%20font-size='17'%20fill='%2333ff66'%20xml:space='preserve'%3E%20_____%20___%20%20____%20%20%20____%20_____%3C/text%3E%3Ctext%20x='8'%20y='42'%20font-family='JetBrains%20Mono%2Cui-monospace%2CConsolas%2Cmonospace'%20font-size='17'%20fill='%2333ff66'%20xml:space='preserve'%3E%7C%20%20___/%20_%20%5C%7C%20%20_%20%5C%20/%20___%7C%20____%7C%3C/text%3E%3Ctext%20x='8'%20y='62'%20font-family='JetBrains%20Mono%2Cui-monospace%2CConsolas%2Cmonospace'%20font-size='17'%20fill='%2333ff66'%20xml:space='preserve'%3E%7C%20%7C_%20%7C%20%7C%20%7C%20%7C%20%7C_%29%20%7C%20%7C%20%20_%7C%20%20_%7C%3C/text%3E%3Ctext%20x='8'%20y='82'%20font-family='JetBrains%20Mono%2Cui-monospace%2CConsolas%2Cmonospace'%20font-size='17'%20fill='%2333ff66'%20xml:space='preserve'%3E%7C%20%20_%7C%7C%20%7C_%7C%20%7C%20%20_%20%26lt%3B%7C%20%7C_%7C%20%7C%20%7C___%3C/text%3E%3Ctext%20x='8'%20y='102'%20font-family='JetBrains%20Mono%2Cui-monospace%2CConsolas%2Cmonospace'%20font-size='17'%20fill='%2333ff66'%20xml:space='preserve'%3E%7C_%7C%20%20%20%5C___/%7C_%7C%20%5C_%5C%5C____%7C_____%7C%3C/text%3E%3Ctext%20x='8'%20y='128'%20font-family='JetBrains%20Mono%2Cui-monospace%2CConsolas%2Cmonospace'%20font-size='14'%20fill='%23ffb547'%3E%26gt%3B%20atelier%20multi-langages_%3C/text%3E%3C/svg%3E");
  --art-empty:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2090%2030'%3E%3Ctext%20x='4'%20y='20'%20font-family='monospace'%20font-size='15'%20fill='%232fd05c'%3E%26gt%3B%20_%20vide%3C/text%3E%3C/svg%3E");
  --art-ok:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Ctext%20x='24'%20y='31'%20text-anchor='middle'%20font-family='monospace'%20font-size='24'%20font-weight='700'%20fill='%2333ff66'%3EOK%3C/text%3E%3C/svg%3E");
  --art-err:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Ctext%20x='24'%20y='31'%20text-anchor='middle'%20font-family='monospace'%20font-size='20'%20font-weight='700'%20fill='%23ff5555'%3EERR%3C/text%3E%3C/svg%3E");
}
/* ---- Hacker · Cyberpunk (sombre) ---- */
[data-mode="hacker2"][data-theme="dark"]{
  color-scheme:dark;
  --bg:#020611;
  --bg2:#050b1b;
  --panel-rgb:4,10,23;
  --panel:rgba(var(--panel-rgb),.88);
  --panel-solid:#050c1a;
  --fg:138,227,178;
  --panel2:rgba(var(--fg),.05);
  --line:rgba(var(--fg),.16);
  --line2:rgba(var(--fg),.30);
  --text:#9bebc0;
  --muted:#6fc79a;
  --dim:#5fb488;
  --accent:#39ff14;
  --accent2:#ff2bd6;
  --accent3:#00e5ff;
  --accent-rgb:57,255,20;
  --accent2-rgb:255,43,214;
  --accent3-rgb:0,229,255;
  --ok:#39ff14;
  --warn:#ffb547;
  --err:#ff4d80;
  --ok-rgb:57,255,20;
  --warn-rgb:255,181,71;
  --err-rgb:255,77,128;
  --on-accent:#04140a;
  --on-err:#20040c;
  --on-warn:#1a1000;
  --on-ok:#04140a;
  --warn-text:#ffc76b;
  --grad:linear-gradient(90deg,#39ff14,#ff2bd6);
  --grad-btn:linear-gradient(135deg,#0d4d0a 0%,#5e0a56 100%);
  --on-grad:#eaffe0;
  --field:rgba(0,0,0,.5);
  --field2:rgba(0,0,0,.3);
  --scrim-rgb:2,4,14;
  --blob:.18;
  --blob1:#0a5a1c;
  --blob2:#7a0a6e;
  --blob3:#063a5a;
  --radius:0px;
  --rr:0;
  --sans:"JetBrains Mono","IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --font-head:var(--mono);
  --shadow:0 0 0 1px rgba(57,255,20,.12), 0 0 28px -12px rgba(57,255,20,.35);
  --glass-blur:4px;
  --glass-sat:110%;
  --spd:.9;
  --bw:1px;
  --code:#b8f5d3;
  --caret:#39ff14;
  --sel:rgba(255,43,214,.28);
  --tk-c:#6fa88a;
  --tk-s:#ffe45c;
  --tk-n:#ff9e64;
  --tk-k:#ff5ce6;
  --tk-t:#00e5ff;
  --tk-f:#39ff14;
  --tk-p:#ff7ab8;
  --tk-o:#7be7ff;
  --tk-call:#c9ff5a;
  --ext-h:#ff7ae8;
  --info:#7be7ff;
  --p0:#39ff14;
  --p1:#ff2bd6;
  --p2:#00e5ff;
  --p3:#ffb547;
  --p4:#7ea0ff;
  --p5:#c8ff3a;
  --p6:#ff7ab8;
  --p7:#ffe45c;
  --p8:#ff8a4c;
  --p9:#cfe9dc;
  --plot-bg:#040a17;
  --plot-grid:rgba(var(--fg),.10);
  --plot-zero:rgba(var(--fg),.32);
  --plot-text:#9bebc0;
  --plot-text2:#6fc79a;
  --d-find:rgba(var(--warn-rgb),.30);
  --d-cur:rgba(var(--accent-rgb),.55);
  --d-word:rgba(var(--accent2-rgb),.30);
  --d-br:rgba(var(--accent-rgb),.38);
  --logo1:#39ff14;
  --logo2:#ff2bd6;
  --logo-bolt:#020611;
  --knob:#39ff14;
  --pin-gnd:#6fc79a;
  --sheen-rgb:57,255,20;
  --shade-rgb:0,0,0;
  --ink:#04140a;
  --paper:#eaffe0;
  --dots:none;
  --deco-img:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20240%20240'%3E%3Ctext%20x='86'%20y='19'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.09'%3E=%3C/text%3E%3Ctext%20x='86'%20y='35'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.082'%3E0%3C/text%3E%3Ctext%20x='86'%20y='51'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.074'%3E1%3C/text%3E%3Ctext%20x='86'%20y='67'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.066'%3E%3C%3C/text%3E%3Ctext%20x='86'%20y='83'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.058'%3E1%3C/text%3E%3Ctext%20x='86'%20y='99'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.05'%3E%5D%3C/text%3E%3Ctext%20x='86'%20y='115'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.041'%3E%3E%3C/text%3E%3Ctext%20x='18'%20y='42'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.09'%3E0%3C/text%3E%3Ctext%20x='18'%20y='58'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.082'%3E1%3C/text%3E%3Ctext%20x='18'%20y='74'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.074'%3E/%3C/text%3E%3Ctext%20x='18'%20y='90'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.066'%3E/%3C/text%3E%3Ctext%20x='18'%20y='106'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.058'%3E1%3C/text%3E%3Ctext%20x='65'%20y='15'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.09'%3E/%3C/text%3E%3Ctext%20x='65'%20y='31'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.082'%3E0%3C/text%3E%3Ctext%20x='65'%20y='47'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.074'%3E%3E%3C/text%3E%3Ctext%20x='65'%20y='63'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.066'%3E1%3C/text%3E%3Ctext%20x='65'%20y='79'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.058'%3E%7D%3C/text%3E%3Ctext%20x='65'%20y='95'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.05'%3E=%3C/text%3E%3Ctext%20x='65'%20y='111'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.041'%3E=%3C/text%3E%3Ctext%20x='65'%20y='127'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.033'%3E%3E%3C/text%3E%3Ctext%20x='19'%20y='46'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.09'%3E/%3C/text%3E%3Ctext%20x='19'%20y='62'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.082'%3E0%3C/text%3E%3Ctext%20x='19'%20y='78'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.074'%3E%7D%3C/text%3E%3Ctext%20x='19'%20y='94'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.066'%3E0%3C/text%3E%3Ctext%20x='19'%20y='110'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.058'%3E%3C%3C/text%3E%3Ctext%20x='19'%20y='126'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.05'%3E%7B%3C/text%3E%3Ctext%20x='19'%20y='142'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.041'%3E%5B%3C/text%3E%3Ctext%20x='19'%20y='158'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.033'%3E/%3C/text%3E%3Ctext%20x='40'%20y='44'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.09'%3E%3E%3C/text%3E%3Ctext%20x='40'%20y='60'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.082'%3E%5B%3C/text%3E%3Ctext%20x='40'%20y='76'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.074'%3E%3C%3C/text%3E%3Ctext%20x='40'%20y='92'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.066'%3E=%3C/text%3E%3Ctext%20x='50'%20y='16'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.09'%3E%3E%3C/text%3E%3Ctext%20x='50'%20y='32'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.082'%3E=%3C/text%3E%3Ctext%20x='50'%20y='48'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.074'%3E%7D%3C/text%3E%3Ctext%20x='50'%20y='64'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.066'%3E%5D%3C/text%3E%3Ctext%20x='50'%20y='80'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.058'%3E1%3C/text%3E%3Ctext%20x='50'%20y='96'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.05'%3E%3C%3C/text%3E%3Ctext%20x='50'%20y='112'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.041'%3E%2B%3C/text%3E%3Ctext%20x='50'%20y='128'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.033'%3E1%3C/text%3E%3Ctext%20x='148'%20y='13'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.09'%3E%7D%3C/text%3E%3Ctext%20x='148'%20y='29'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.082'%3E%5C%3C/text%3E%3Ctext%20x='148'%20y='45'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.074'%3E=%3C/text%3E%3Ctext%20x='148'%20y='61'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.066'%3E%3C%3C/text%3E%3Ctext%20x='148'%20y='77'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.058'%3E/%3C/text%3E%3Ctext%20x='148'%20y='93'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.05'%3E%2A%3C/text%3E%3Ctext%20x='148'%20y='109'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.041'%3E%5D%3C/text%3E%3Ctext%20x='148'%20y='125'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.033'%3E%5C%3C/text%3E%3Ctext%20x='153'%20y='39'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.09'%3E%5B%3C/text%3E%3Ctext%20x='153'%20y='55'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.082'%3E%7D%3C/text%3E%3Ctext%20x='153'%20y='71'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.074'%3E%2A%3C/text%3E%3Ctext%20x='153'%20y='87'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.066'%3E%7B%3C/text%3E%3Ctext%20x='153'%20y='103'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.058'%3E%2B%3C/text%3E%3Ctext%20x='153'%20y='119'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.05'%3E%2A%3C/text%3E%3Ctext%20x='66'%20y='15'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.09'%3E%5B%3C/text%3E%3Ctext%20x='66'%20y='31'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.082'%3E%3C%3C/text%3E%3Ctext%20x='66'%20y='47'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.074'%3E%5C%3C/text%3E%3Ctext%20x='66'%20y='63'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.066'%3E%5D%3C/text%3E%3Ctext%20x='66'%20y='79'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.058'%3E%2B%3C/text%3E%3Ctext%20x='66'%20y='95'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.05'%3E%5C%3C/text%3E%3Ctext%20x='66'%20y='111'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.041'%3E%5B%3C/text%3E%3Ctext%20x='66'%20y='127'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.033'%3E%3E%3C/text%3E%3Ctext%20x='22'%20y='17'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.09'%3E/%3C/text%3E%3Ctext%20x='22'%20y='33'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.082'%3E%7B%3C/text%3E%3Ctext%20x='22'%20y='49'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.074'%3E%2A%3C/text%3E%3Ctext%20x='22'%20y='65'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.066'%3E%5D%3C/text%3E%3Ctext%20x='22'%20y='81'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.058'%3E%7B%3C/text%3E%3Ctext%20x='22'%20y='97'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.05'%3E%5C%3C/text%3E%3Ctext%20x='22'%20y='113'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.041'%3E/%3C/text%3E%3Ctext%20x='22'%20y='129'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.033'%3E0%3C/text%3E%3Ctext%20x='175'%20y='14'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.09'%3E%3E%3C/text%3E%3Ctext%20x='175'%20y='30'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.082'%3E%2A%3C/text%3E%3Ctext%20x='175'%20y='46'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.074'%3E%5D%3C/text%3E%3Ctext%20x='175'%20y='62'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.066'%3E%5D%3C/text%3E%3Ctext%20x='175'%20y='78'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.058'%3E%2B%3C/text%3E%3Ctext%20x='175'%20y='94'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.05'%3E%5D%3C/text%3E%3Ctext%20x='175'%20y='110'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.041'%3E%3E%3C/text%3E%3Ctext%20x='175'%20y='126'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.033'%3E%5C%3C/text%3E%3Ctext%20x='152'%20y='39'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.09'%3E1%3C/text%3E%3Ctext%20x='152'%20y='55'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.082'%3E%5B%3C/text%3E%3Ctext%20x='152'%20y='71'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.074'%3E%5C%3C/text%3E%3Ctext%20x='152'%20y='87'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.066'%3E%2B%3C/text%3E%3Ctext%20x='174'%20y='14'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.09'%3E%2B%3C/text%3E%3Ctext%20x='174'%20y='30'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.082'%3E%2B%3C/text%3E%3Ctext%20x='174'%20y='46'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.074'%3E%5B%3C/text%3E%3Ctext%20x='174'%20y='62'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.066'%3E=%3C/text%3E%3Ctext%20x='151'%20y='53'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.09'%3E%5B%3C/text%3E%3Ctext%20x='151'%20y='69'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.082'%3E%2B%3C/text%3E%3Ctext%20x='151'%20y='85'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.074'%3E/%3C/text%3E%3Ctext%20x='151'%20y='101'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.066'%3E=%3C/text%3E%3Ctext%20x='151'%20y='117'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.058'%3E%5D%3C/text%3E%3Ctext%20x='151'%20y='133'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.05'%3E0%3C/text%3E%3Ctext%20x='151'%20y='149'%20font-family='monospace'%20font-size='12'%20fill='%2339ff14'%20opacity='0.041'%3E%5C%3C/text%3E%3C/svg%3E"),radial-gradient(ellipse at 100% 100%,rgba(255,43,214,.10),transparent 55%);
  --deco-size:240px 240px,auto;
  --deco-pos:0 0;
  --deco-rep:repeat,no-repeat;
  --deco-op:1;
  --overlay:repeating-linear-gradient(0deg,rgba(0,0,0,.18) 0,rgba(0,0,0,.18) 1px,transparent 1px,transparent 3px);
  --burst1:#39ff14;
  --burst2:#ff2bd6;
  --burst3:#00e5ff;
  --burst4:#ffe45c;
  --burst5:#ffffff;
  --burst6:#39ff14;
  --plat0:#39ff14;
  --plat1:#ff4d80;
  --plat2:#ffb547;
  --plat3:#ff2bd6;
  --plat4:#00e5ff;
  --plat5:#c8ff3a;
  --plat6:#7dff9b;
  --plat-x:#6fc79a;
  --art-welcome:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20290%20150'%3E%3Ctext%20x='8'%20y='22'%20font-family='JetBrains%20Mono%2Cui-monospace%2CConsolas%2Cmonospace'%20font-size='17'%20fill='%2339ff14'%20xml:space='preserve'%3E%20_____%20___%20%20____%20%20%20____%20_____%3C/text%3E%3Ctext%20x='8'%20y='42'%20font-family='JetBrains%20Mono%2Cui-monospace%2CConsolas%2Cmonospace'%20font-size='17'%20fill='%2339ff14'%20xml:space='preserve'%3E%7C%20%20___/%20_%20%5C%7C%20%20_%20%5C%20/%20___%7C%20____%7C%3C/text%3E%3Ctext%20x='8'%20y='62'%20font-family='JetBrains%20Mono%2Cui-monospace%2CConsolas%2Cmonospace'%20font-size='17'%20fill='%2339ff14'%20xml:space='preserve'%3E%7C%20%7C_%20%7C%20%7C%20%7C%20%7C%20%7C_%29%20%7C%20%7C%20%20_%7C%20%20_%7C%3C/text%3E%3Ctext%20x='8'%20y='82'%20font-family='JetBrains%20Mono%2Cui-monospace%2CConsolas%2Cmonospace'%20font-size='17'%20fill='%2339ff14'%20xml:space='preserve'%3E%7C%20%20_%7C%7C%20%7C_%7C%20%7C%20%20_%20%26lt%3B%7C%20%7C_%7C%20%7C%20%7C___%3C/text%3E%3Ctext%20x='8'%20y='102'%20font-family='JetBrains%20Mono%2Cui-monospace%2CConsolas%2Cmonospace'%20font-size='17'%20fill='%2339ff14'%20xml:space='preserve'%3E%7C_%7C%20%20%20%5C___/%7C_%7C%20%5C_%5C%5C____%7C_____%7C%3C/text%3E%3Ctext%20x='8'%20y='128'%20font-family='JetBrains%20Mono%2Cui-monospace%2CConsolas%2Cmonospace'%20font-size='14'%20fill='%23ff2bd6'%3E%26gt%3B%20atelier%20multi-langages_%3C/text%3E%3C/svg%3E");
  --art-empty:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2090%2030'%3E%3Ctext%20x='4'%20y='20'%20font-family='monospace'%20font-size='15'%20fill='%236fc79a'%3E%26gt%3B%20null_%3C/text%3E%3C/svg%3E");
  --art-ok:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Ctext%20x='24'%20y='31'%20text-anchor='middle'%20font-family='monospace'%20font-size='24'%20font-weight='700'%20fill='%2339ff14'%3EOK%3C/text%3E%3C/svg%3E");
  --art-err:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Ctext%20x='24'%20y='31'%20text-anchor='middle'%20font-family='monospace'%20font-size='20'%20font-weight='700'%20fill='%23ff4d80'%3EERR%3C/text%3E%3C/svg%3E");
}
/* ---- Fleur · Herbier (clair) ---- */
[data-mode="fleur"][data-theme="light"]{
  color-scheme:light;
  --bg:#f4ecdf;
  --bg2:#faf4e9;
  --panel-rgb:255,251,243;
  --panel:rgba(var(--panel-rgb),.74);
  --panel-solid:#fffaf1;
  --fg:44,54,45;
  --panel2:rgba(var(--fg),.045);
  --line:rgba(var(--fg),.13);
  --line2:rgba(var(--fg),.22);
  --text:#2c362d;
  --muted:#4f5f4c;
  --dim:#5d6c59;
  --accent:#436340;
  --accent2:#a03a51;
  --accent3:#9a4326;
  --accent-rgb:67,99,64;
  --accent2-rgb:160,58,81;
  --accent3-rgb:154,67,38;
  --ok:#3f6e3a;
  --warn:#96540f;
  --err:#a83a26;
  --ok-rgb:63,110,58;
  --warn-rgb:150,84,15;
  --err-rgb:168,58,38;
  --on-accent:#ffffff;
  --on-err:#ffffff;
  --on-warn:#ffffff;
  --on-ok:#ffffff;
  --warn-text:#6f3d05;
  --grad:linear-gradient(135deg,#436340,#b2495f 60%,#9a4326);
  --grad-btn:linear-gradient(135deg,#9a4326 0%,#a94661 100%);
  --on-grad:#ffffff;
  --field:rgba(255,255,255,.75);
  --field2:rgba(44,54,45,.05);
  --scrim-rgb:44,54,45;
  --blob:.22;
  --blob1:#c5d4b8;
  --blob2:#f0c9cc;
  --blob3:#f0d5b8;
  --radius:18px;
  --rr:1.35;
  --sans:"Nunito Sans",Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --font-head:Fraunces,"Playfair Display",Georgia,"Times New Roman",serif;
  --shadow:0 10px 30px -12px rgba(76,111,69,.28);
  --glass-blur:12px;
  --glass-sat:115%;
  --spd:1.3;
  --bw:1px;
  --code:#2c362d;
  --caret:#9a4326;
  --sel:rgba(178,73,95,.20);
  --tk-c:#5b6a55;
  --tk-s:#3b6b2e;
  --tk-n:#9a4b16;
  --tk-k:#9a3f6a;
  --tk-t:#2b5f8a;
  --tk-f:#2f6b57;
  --tk-p:#a8412e;
  --tk-o:#4a6a78;
  --tk-call:#7a5a12;
  --ext-h:#9a3f6a;
  --info:#9a3f6a;
  --p0:#436340;
  --p1:#a03a51;
  --p2:#9a4326;
  --p3:#2b5f8a;
  --p4:#7a5a12;
  --p5:#6b4a8a;
  --p6:#2f6b57;
  --p7:#9a7a20;
  --p8:#c06a2a;
  --p9:#5d6c59;
  --plot-bg:#fffaf1;
  --plot-grid:rgba(var(--fg),.09);
  --plot-zero:rgba(var(--fg),.30);
  --plot-text:#2c362d;
  --plot-text2:#5d6c59;
  --d-find:rgba(var(--warn-rgb),.30);
  --d-cur:rgba(var(--accent-rgb),.55);
  --d-word:rgba(var(--accent2-rgb),.30);
  --d-br:rgba(var(--accent-rgb),.38);
  --logo1:#7f9e76;
  --logo2:#d98a95;
  --logo-bolt:#fffaf1;
  --knob:#fffaf1;
  --pin-gnd:#6b7a66;
  --sheen-rgb:255,255,255;
  --shade-rgb:44,54,45;
  --ink:#2c362d;
  --paper:#fffaf1;
  --dots:none;
  --deco-img:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20200%20300'%3E%3Cg%20opacity='0.34'%3E%3Cpath%20d='M100%20290%20C96%20220%20112%20170%20100%2096'%20fill='none'%20stroke='%237f9e76'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cpath%20d='M0%200%20C13.799999999999999%20-16.56%2034.5%20-13.799999999999999%2046%200%20C34.5%2013.799999999999999%2013.799999999999999%2016.56%200%200Z'%20fill='%23a9c2a0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='translate%28100%20250%29%20rotate%28-30%29'/%3E%3Cpath%20d='M0%200%20C12.9%20-15.479999999999999%2032.25%20-12.9%2043%200%20C32.25%2012.9%2012.9%2015.479999999999999%200%200Z'%20fill='%23a9c2a0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='translate%28100%20215%29%20rotate%28210%29'/%3E%3Cpath%20d='M0%200%20C12.0%20-14.399999999999999%2030.0%20-12.0%2040%200%20C30.0%2012.0%2012.0%2014.399999999999999%200%200Z'%20fill='%23a9c2a0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='translate%28100%20182%29%20rotate%28-30%29'/%3E%3Cpath%20d='M0%200%20C11.1%20-13.32%2027.75%20-11.1%2037%200%20C27.75%2011.1%2011.1%2013.32%200%200Z'%20fill='%23a9c2a0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='translate%28100%20150%29%20rotate%28210%29'/%3E%3Cpath%20d='M0%200%20C10.2%20-12.24%2025.5%20-10.2%2034%200%20C25.5%2010.2%2010.2%2012.24%200%200Z'%20fill='%23a9c2a0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='translate%28100%20122%29%20rotate%28-30%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%280.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%2872.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%28144.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%28216.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%28288.0%20100%2078%29'/%3E%3Ccircle%20cx='100'%20cy='78'%20r='9.520000000000001'%20fill='%23e0a24a'/%3E%3C/g%3E%3C/svg%3E"),url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20200%20300'%3E%3Cg%20opacity='0.28'%3E%3Cpath%20d='M100%20290%20C96%20220%20112%20170%20100%2096'%20fill='none'%20stroke='%237f9e76'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cpath%20d='M0%200%20C13.799999999999999%20-16.56%2034.5%20-13.799999999999999%2046%200%20C34.5%2013.799999999999999%2013.799999999999999%2016.56%200%200Z'%20fill='%23a9c2a0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='translate%28100%20250%29%20rotate%28-30%29'/%3E%3Cpath%20d='M0%200%20C12.9%20-15.479999999999999%2032.25%20-12.9%2043%200%20C32.25%2012.9%2012.9%2015.479999999999999%200%200Z'%20fill='%23a9c2a0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='translate%28100%20215%29%20rotate%28210%29'/%3E%3Cpath%20d='M0%200%20C12.0%20-14.399999999999999%2030.0%20-12.0%2040%200%20C30.0%2012.0%2012.0%2014.399999999999999%200%200Z'%20fill='%23a9c2a0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='translate%28100%20182%29%20rotate%28-30%29'/%3E%3Cpath%20d='M0%200%20C11.1%20-13.32%2027.75%20-11.1%2037%200%20C27.75%2011.1%2011.1%2013.32%200%200Z'%20fill='%23a9c2a0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='translate%28100%20150%29%20rotate%28210%29'/%3E%3Cpath%20d='M0%200%20C10.2%20-12.24%2025.5%20-10.2%2034%200%20C25.5%2010.2%2010.2%2012.24%200%200Z'%20fill='%23a9c2a0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='translate%28100%20122%29%20rotate%28-30%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a9b0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%280.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a9b0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%2872.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a9b0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%28144.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a9b0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%28216.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a9b0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%28288.0%20100%2078%29'/%3E%3Ccircle%20cx='100'%20cy='78'%20r='9.520000000000001'%20fill='%23e0a24a'/%3E%3C/g%3E%3C/svg%3E");
  --deco-size:250px auto,210px auto;
  --deco-pos:left 1.5% bottom -30px,right 2% top -40px;
  --deco-rep:no-repeat;
  --deco-op:1;
  --overlay:none;
  --burst1:#d98a95;
  --burst2:#7f9e76;
  --burst3:#c8683f;
  --burst4:#f0c9cc;
  --burst5:#ffffff;
  --burst6:#e8b4b8;
  --plat0:#436340;
  --plat1:#a8412e;
  --plat2:#96540f;
  --plat3:#b2495f;
  --plat4:#2b5f8a;
  --plat5:#6b4a8a;
  --plat6:#3f6e3a;
  --plat-x:#5d6c59;
  --art-welcome:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20220%20190'%3E%3Cpath%20d='M60%2083.4%20C52%20130%2090%20115%20100%20150'%20fill='none'%20stroke='%237f9e76'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cpath%20d='M118%2070.6%20C118%20110%20100%20115%20100%20150'%20fill='none'%20stroke='%237f9e76'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cpath%20d='M170%2089.6%20C178%20138%20110%20115%20100%20150'%20fill='none'%20stroke='%237f9e76'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cpath%20d='M0%200%20C12.6%20-15.12%2031.5%20-12.6%2042%200%20C31.5%2012.6%2012.6%2015.12%200%200Z'%20fill='%23a9c2a0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='translate%28100%20132%29%20rotate%28-35%29'/%3E%3Cpath%20d='M0%200%20C12.0%20-14.399999999999999%2030.0%20-12.0%2040%200%20C30.0%2012.0%2012.0%2014.399999999999999%200%200Z'%20fill='%23a9c2a0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='translate%28100%20120%29%20rotate%28215%29'/%3E%3Cpath%20d='M0%200%20C9.6%20-11.52%2024.0%20-9.6%2032%200%20C24.0%209.6%209.6%2011.52%200%200Z'%20fill='%23a9c2a0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='translate%28100%20100%29%20rotate%28-20%29'/%3E%3Cellipse%20cx='60'%20cy='43.879999999999995'%20rx='9.36'%20ry='16.12'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%280.0%2060%2060%29'/%3E%3Cellipse%20cx='60'%20cy='43.879999999999995'%20rx='9.36'%20ry='16.12'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%2872.0%2060%2060%29'/%3E%3Cellipse%20cx='60'%20cy='43.879999999999995'%20rx='9.36'%20ry='16.12'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%28144.0%2060%2060%29'/%3E%3Cellipse%20cx='60'%20cy='43.879999999999995'%20rx='9.36'%20ry='16.12'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%28216.0%2060%2060%29'/%3E%3Cellipse%20cx='60'%20cy='43.879999999999995'%20rx='9.36'%20ry='16.12'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%28288.0%2060%2060%29'/%3E%3Ccircle%20cx='60'%20cy='60'%20r='7.280000000000001'%20fill='%23e0a24a'/%3E%3Cellipse%20cx='118'%20cy='18.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a9b0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%280.0%20118%2040%29'/%3E%3Cellipse%20cx='118'%20cy='18.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a9b0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%2872.0%20118%2040%29'/%3E%3Cellipse%20cx='118'%20cy='18.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a9b0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%28144.0%20118%2040%29'/%3E%3Cellipse%20cx='118'%20cy='18.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a9b0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%28216.0%20118%2040%29'/%3E%3Cellipse%20cx='118'%20cy='18.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a9b0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%28288.0%20118%2040%29'/%3E%3Ccircle%20cx='118'%20cy='40'%20r='9.520000000000001'%20fill='%23e0a24a'/%3E%3Cellipse%20cx='170'%20cy='53.120000000000005'%20rx='8.64'%20ry='14.879999999999999'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%280.0%20170%2068%29'/%3E%3Cellipse%20cx='170'%20cy='53.120000000000005'%20rx='8.64'%20ry='14.879999999999999'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%2872.0%20170%2068%29'/%3E%3Cellipse%20cx='170'%20cy='53.120000000000005'%20rx='8.64'%20ry='14.879999999999999'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%28144.0%20170%2068%29'/%3E%3Cellipse%20cx='170'%20cy='53.120000000000005'%20rx='8.64'%20ry='14.879999999999999'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%28216.0%20170%2068%29'/%3E%3Cellipse%20cx='170'%20cy='53.120000000000005'%20rx='8.64'%20ry='14.879999999999999'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%28288.0%20170%2068%29'/%3E%3Ccircle%20cx='170'%20cy='68'%20r='6.720000000000001'%20fill='%23e0a24a'/%3E%3Cpath%20d='M78%20150%20Q100%20175%20122%20150%20L116%20168%20Q100%20180%2084%20168Z'%20fill='%237f9e76'%20opacity='.55'/%3E%3C/svg%3E");
  --art-empty:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20200%20300'%3E%3Cg%20opacity='1'%3E%3Cpath%20d='M100%20290%20C96%20220%20112%20170%20100%2096'%20fill='none'%20stroke='%237f9e76'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cpath%20d='M0%200%20C13.799999999999999%20-16.56%2034.5%20-13.799999999999999%2046%200%20C34.5%2013.799999999999999%2013.799999999999999%2016.56%200%200Z'%20fill='%23a9c2a0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='translate%28100%20250%29%20rotate%28-30%29'/%3E%3Cpath%20d='M0%200%20C12.9%20-15.479999999999999%2032.25%20-12.9%2043%200%20C32.25%2012.9%2012.9%2015.479999999999999%200%200Z'%20fill='%23a9c2a0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='translate%28100%20215%29%20rotate%28210%29'/%3E%3Cpath%20d='M0%200%20C12.0%20-14.399999999999999%2030.0%20-12.0%2040%200%20C30.0%2012.0%2012.0%2014.399999999999999%200%200Z'%20fill='%23a9c2a0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='translate%28100%20182%29%20rotate%28-30%29'/%3E%3Cpath%20d='M0%200%20C11.1%20-13.32%2027.75%20-11.1%2037%200%20C27.75%2011.1%2011.1%2013.32%200%200Z'%20fill='%23a9c2a0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='translate%28100%20150%29%20rotate%28210%29'/%3E%3Cpath%20d='M0%200%20C10.2%20-12.24%2025.5%20-10.2%2034%200%20C25.5%2010.2%2010.2%2012.24%200%200Z'%20fill='%23a9c2a0'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='translate%28100%20122%29%20rotate%28-30%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%280.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%2872.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%28144.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%28216.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23f0c2c8'%20stroke='%235d7a55'%20stroke-width='1.6'%20transform='rotate%28288.0%20100%2078%29'/%3E%3Ccircle%20cx='100'%20cy='78'%20r='9.520000000000001'%20fill='%23e0a24a'/%3E%3C/g%3E%3C/svg%3E");
  --art-ok:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Cellipse%20cx='24'%20cy='14.7'%20rx='5.3999999999999995'%20ry='9.3'%20fill='%23436340'%20transform='rotate%280.0%2024%2024%29'/%3E%3Cellipse%20cx='24'%20cy='14.7'%20rx='5.3999999999999995'%20ry='9.3'%20fill='%23436340'%20transform='rotate%2872.0%2024%2024%29'/%3E%3Cellipse%20cx='24'%20cy='14.7'%20rx='5.3999999999999995'%20ry='9.3'%20fill='%23436340'%20transform='rotate%28144.0%2024%2024%29'/%3E%3Cellipse%20cx='24'%20cy='14.7'%20rx='5.3999999999999995'%20ry='9.3'%20fill='%23436340'%20transform='rotate%28216.0%2024%2024%29'/%3E%3Cellipse%20cx='24'%20cy='14.7'%20rx='5.3999999999999995'%20ry='9.3'%20fill='%23436340'%20transform='rotate%28288.0%2024%2024%29'/%3E%3Ccircle%20cx='24'%20cy='24'%20r='4.2'%20fill='%23fffaf1'/%3E%3C/svg%3E");
  --art-err:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Cpath%20d='M24%2044%20C24%2034%2026%2030%2030%2024'%20fill='none'%20stroke='%239a4326'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cellipse%20cx='32'%20cy='13.18'%20rx='3.96'%20ry='6.82'%20fill='%23fffaf1'%20stroke='%239a4326'%20stroke-width='2.4'%20transform='rotate%280.0%2032%2020%29'/%3E%3Cellipse%20cx='32'%20cy='13.18'%20rx='3.96'%20ry='6.82'%20fill='%23fffaf1'%20stroke='%239a4326'%20stroke-width='2.4'%20transform='rotate%2872.0%2032%2020%29'/%3E%3Cellipse%20cx='32'%20cy='13.18'%20rx='3.96'%20ry='6.82'%20fill='%23fffaf1'%20stroke='%239a4326'%20stroke-width='2.4'%20transform='rotate%28144.0%2032%2020%29'/%3E%3Cellipse%20cx='32'%20cy='13.18'%20rx='3.96'%20ry='6.82'%20fill='%23fffaf1'%20stroke='%239a4326'%20stroke-width='2.4'%20transform='rotate%28216.0%2032%2020%29'/%3E%3Cellipse%20cx='32'%20cy='13.18'%20rx='3.96'%20ry='6.82'%20fill='%23fffaf1'%20stroke='%239a4326'%20stroke-width='2.4'%20transform='rotate%28288.0%2032%2020%29'/%3E%3Ccircle%20cx='32'%20cy='20'%20r='3.08'%20fill='%239a4326'/%3E%3C/svg%3E");
}
/* ---- Fleur · Jardin de nuit (sombre) ---- */
[data-mode="fleur2"][data-theme="dark"]{
  color-scheme:dark;
  --bg:#101b15;
  --bg2:#15241c;
  --panel-rgb:26,41,33;
  --panel:rgba(var(--panel-rgb),.80);
  --panel-solid:#1a2a21;
  --fg:230,219,208;
  --panel2:rgba(var(--fg),.04);
  --line:rgba(var(--fg),.10);
  --line2:rgba(var(--fg),.18);
  --text:#eadfd3;
  --muted:#b7b0a5;
  --dim:#a19a8f;
  --accent:#e8a39d;
  --accent2:#e29677;
  --accent3:#9fbb99;
  --accent-rgb:232,163,157;
  --accent2-rgb:226,150,119;
  --accent3-rgb:159,187,153;
  --ok:#9fbb99;
  --warn:#e0b07f;
  --err:#ee9a9a;
  --ok-rgb:159,187,153;
  --warn-rgb:224,176,127;
  --err-rgb:238,154,154;
  --on-accent:#2a1512;
  --on-err:#2a0d0d;
  --on-warn:#2a1a08;
  --on-ok:#0f1d12;
  --warn-text:#f0cda1;
  --grad:linear-gradient(135deg,#e8a39d,#e29677 60%,#9fbb99);
  --grad-btn:linear-gradient(135deg,#b35c3d 0%,#a5524f 100%);
  --on-grad:#ffffff;
  --field:rgba(0,0,0,.28);
  --field2:rgba(0,0,0,.15);
  --scrim-rgb:6,12,9;
  --blob:.30;
  --blob1:#2e5a41;
  --blob2:#6b3a4a;
  --blob3:#5a4a2a;
  --radius:22px;
  --rr:1.6;
  --sans:"Nunito Sans",Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --font-head:Fraunces,"Playfair Display",Georgia,"Times New Roman",serif;
  --shadow:0 16px 44px -14px rgba(0,0,0,.55);
  --glass-blur:16px;
  --glass-sat:120%;
  --spd:1.4;
  --bw:1px;
  --code:#e6dbd0;
  --caret:#e8a39d;
  --sel:rgba(232,163,157,.25);
  --tk-c:#93a08e;
  --tk-s:#b5d59a;
  --tk-n:#f0b27a;
  --tk-k:#e8a3c0;
  --tk-t:#8fbfe0;
  --tk-f:#8fd4b8;
  --tk-p:#f08a8a;
  --tk-o:#a8c8d0;
  --tk-call:#e8d08a;
  --ext-h:#e8a3c0;
  --info:#e8a3c0;
  --p0:#e8a39d;
  --p1:#9fbb99;
  --p2:#e0b07f;
  --p3:#8fbfe0;
  --p4:#e29677;
  --p5:#b5d59a;
  --p6:#e8a3c0;
  --p7:#e8d08a;
  --p8:#f0b27a;
  --p9:#cfc6ba;
  --plot-bg:#1a2a21;
  --plot-grid:rgba(var(--fg),.08);
  --plot-zero:rgba(var(--fg),.28);
  --plot-text:#eadfd3;
  --plot-text2:#b7b0a5;
  --d-find:rgba(var(--warn-rgb),.30);
  --d-cur:rgba(var(--accent-rgb),.55);
  --d-word:rgba(var(--accent2-rgb),.30);
  --d-br:rgba(var(--accent-rgb),.38);
  --logo1:#9fbb99;
  --logo2:#e8a39d;
  --logo-bolt:#14211a;
  --knob:#eadfd3;
  --pin-gnd:#8b8f86;
  --sheen-rgb:255,255,255;
  --shade-rgb:0,0,0;
  --ink:#14211a;
  --paper:#f3eadf;
  --dots:none;
  --deco-img:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20200%20300'%3E%3Cg%20opacity='0.34'%3E%3Cpath%20d='M100%20290%20C96%20220%20112%20170%20100%2096'%20fill='none'%20stroke='%235c8a6a'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cpath%20d='M0%200%20C13.799999999999999%20-16.56%2034.5%20-13.799999999999999%2046%200%20C34.5%2013.799999999999999%2013.799999999999999%2016.56%200%200Z'%20fill='%233f6b52'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='translate%28100%20250%29%20rotate%28-30%29'/%3E%3Cpath%20d='M0%200%20C12.9%20-15.479999999999999%2032.25%20-12.9%2043%200%20C32.25%2012.9%2012.9%2015.479999999999999%200%200Z'%20fill='%233f6b52'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='translate%28100%20215%29%20rotate%28210%29'/%3E%3Cpath%20d='M0%200%20C12.0%20-14.399999999999999%2030.0%20-12.0%2040%200%20C30.0%2012.0%2012.0%2014.399999999999999%200%200Z'%20fill='%233f6b52'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='translate%28100%20182%29%20rotate%28-30%29'/%3E%3Cpath%20d='M0%200%20C11.1%20-13.32%2027.75%20-11.1%2037%200%20C27.75%2011.1%2011.1%2013.32%200%200Z'%20fill='%233f6b52'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='translate%28100%20150%29%20rotate%28210%29'/%3E%3Cpath%20d='M0%200%20C10.2%20-12.24%2025.5%20-10.2%2034%200%20C25.5%2010.2%2010.2%2012.24%200%200Z'%20fill='%233f6b52'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='translate%28100%20122%29%20rotate%28-30%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%280.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%2872.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%28144.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%28216.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%28288.0%20100%2078%29'/%3E%3Ccircle%20cx='100'%20cy='78'%20r='9.520000000000001'%20fill='%23e0b07f'/%3E%3C/g%3E%3C/svg%3E"),url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20200%20300'%3E%3Cg%20opacity='0.28'%3E%3Cpath%20d='M100%20290%20C96%20220%20112%20170%20100%2096'%20fill='none'%20stroke='%235c8a6a'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cpath%20d='M0%200%20C13.799999999999999%20-16.56%2034.5%20-13.799999999999999%2046%200%20C34.5%2013.799999999999999%2013.799999999999999%2016.56%200%200Z'%20fill='%233f6b52'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='translate%28100%20250%29%20rotate%28-30%29'/%3E%3Cpath%20d='M0%200%20C12.9%20-15.479999999999999%2032.25%20-12.9%2043%200%20C32.25%2012.9%2012.9%2015.479999999999999%200%200Z'%20fill='%233f6b52'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='translate%28100%20215%29%20rotate%28210%29'/%3E%3Cpath%20d='M0%200%20C12.0%20-14.399999999999999%2030.0%20-12.0%2040%200%20C30.0%2012.0%2012.0%2014.399999999999999%200%200Z'%20fill='%233f6b52'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='translate%28100%20182%29%20rotate%28-30%29'/%3E%3Cpath%20d='M0%200%20C11.1%20-13.32%2027.75%20-11.1%2037%200%20C27.75%2011.1%2011.1%2013.32%200%200Z'%20fill='%233f6b52'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='translate%28100%20150%29%20rotate%28210%29'/%3E%3Cpath%20d='M0%200%20C10.2%20-12.24%2025.5%20-10.2%2034%200%20C25.5%2010.2%2010.2%2012.24%200%200Z'%20fill='%233f6b52'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='translate%28100%20122%29%20rotate%28-30%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e29677'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%280.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e29677'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%2872.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e29677'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%28144.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e29677'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%28216.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e29677'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%28288.0%20100%2078%29'/%3E%3Ccircle%20cx='100'%20cy='78'%20r='9.520000000000001'%20fill='%23e0b07f'/%3E%3C/g%3E%3C/svg%3E");
  --deco-size:250px auto,210px auto;
  --deco-pos:left 1.5% bottom -30px,right 2% top -40px;
  --deco-rep:no-repeat;
  --deco-op:1;
  --overlay:none;
  --burst1:#e8a39d;
  --burst2:#9fbb99;
  --burst3:#e29677;
  --burst4:#f0c9cc;
  --burst5:#ffffff;
  --burst6:#e0b07f;
  --plat0:#9fbb99;
  --plat1:#ee9a9a;
  --plat2:#e0b07f;
  --plat3:#e8a39d;
  --plat4:#8fbfe0;
  --plat5:#e29677;
  --plat6:#b5d59a;
  --plat-x:#a19a8f;
  --art-welcome:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20220%20190'%3E%3Cpath%20d='M60%2083.4%20C52%20130%2090%20115%20100%20150'%20fill='none'%20stroke='%235c8a6a'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cpath%20d='M118%2070.6%20C118%20110%20100%20115%20100%20150'%20fill='none'%20stroke='%235c8a6a'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cpath%20d='M170%2089.6%20C178%20138%20110%20115%20100%20150'%20fill='none'%20stroke='%235c8a6a'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cpath%20d='M0%200%20C12.6%20-15.12%2031.5%20-12.6%2042%200%20C31.5%2012.6%2012.6%2015.12%200%200Z'%20fill='%233f6b52'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='translate%28100%20132%29%20rotate%28-35%29'/%3E%3Cpath%20d='M0%200%20C12.0%20-14.399999999999999%2030.0%20-12.0%2040%200%20C30.0%2012.0%2012.0%2014.399999999999999%200%200Z'%20fill='%233f6b52'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='translate%28100%20120%29%20rotate%28215%29'/%3E%3Cpath%20d='M0%200%20C9.6%20-11.52%2024.0%20-9.6%2032%200%20C24.0%209.6%209.6%2011.52%200%200Z'%20fill='%233f6b52'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='translate%28100%20100%29%20rotate%28-20%29'/%3E%3Cellipse%20cx='60'%20cy='43.879999999999995'%20rx='9.36'%20ry='16.12'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%280.0%2060%2060%29'/%3E%3Cellipse%20cx='60'%20cy='43.879999999999995'%20rx='9.36'%20ry='16.12'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%2872.0%2060%2060%29'/%3E%3Cellipse%20cx='60'%20cy='43.879999999999995'%20rx='9.36'%20ry='16.12'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%28144.0%2060%2060%29'/%3E%3Cellipse%20cx='60'%20cy='43.879999999999995'%20rx='9.36'%20ry='16.12'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%28216.0%2060%2060%29'/%3E%3Cellipse%20cx='60'%20cy='43.879999999999995'%20rx='9.36'%20ry='16.12'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%28288.0%2060%2060%29'/%3E%3Ccircle%20cx='60'%20cy='60'%20r='7.280000000000001'%20fill='%23e0b07f'/%3E%3Cellipse%20cx='118'%20cy='18.92'%20rx='12.24'%20ry='21.08'%20fill='%23e29677'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%280.0%20118%2040%29'/%3E%3Cellipse%20cx='118'%20cy='18.92'%20rx='12.24'%20ry='21.08'%20fill='%23e29677'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%2872.0%20118%2040%29'/%3E%3Cellipse%20cx='118'%20cy='18.92'%20rx='12.24'%20ry='21.08'%20fill='%23e29677'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%28144.0%20118%2040%29'/%3E%3Cellipse%20cx='118'%20cy='18.92'%20rx='12.24'%20ry='21.08'%20fill='%23e29677'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%28216.0%20118%2040%29'/%3E%3Cellipse%20cx='118'%20cy='18.92'%20rx='12.24'%20ry='21.08'%20fill='%23e29677'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%28288.0%20118%2040%29'/%3E%3Ccircle%20cx='118'%20cy='40'%20r='9.520000000000001'%20fill='%23e0b07f'/%3E%3Cellipse%20cx='170'%20cy='53.120000000000005'%20rx='8.64'%20ry='14.879999999999999'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%280.0%20170%2068%29'/%3E%3Cellipse%20cx='170'%20cy='53.120000000000005'%20rx='8.64'%20ry='14.879999999999999'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%2872.0%20170%2068%29'/%3E%3Cellipse%20cx='170'%20cy='53.120000000000005'%20rx='8.64'%20ry='14.879999999999999'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%28144.0%20170%2068%29'/%3E%3Cellipse%20cx='170'%20cy='53.120000000000005'%20rx='8.64'%20ry='14.879999999999999'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%28216.0%20170%2068%29'/%3E%3Cellipse%20cx='170'%20cy='53.120000000000005'%20rx='8.64'%20ry='14.879999999999999'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%28288.0%20170%2068%29'/%3E%3Ccircle%20cx='170'%20cy='68'%20r='6.720000000000001'%20fill='%23e0b07f'/%3E%3Cpath%20d='M78%20150%20Q100%20175%20122%20150%20L116%20168%20Q100%20180%2084%20168Z'%20fill='%235c8a6a'%20opacity='.55'/%3E%3C/svg%3E");
  --art-empty:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20200%20300'%3E%3Cg%20opacity='1'%3E%3Cpath%20d='M100%20290%20C96%20220%20112%20170%20100%2096'%20fill='none'%20stroke='%235c8a6a'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cpath%20d='M0%200%20C13.799999999999999%20-16.56%2034.5%20-13.799999999999999%2046%200%20C34.5%2013.799999999999999%2013.799999999999999%2016.56%200%200Z'%20fill='%233f6b52'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='translate%28100%20250%29%20rotate%28-30%29'/%3E%3Cpath%20d='M0%200%20C12.9%20-15.479999999999999%2032.25%20-12.9%2043%200%20C32.25%2012.9%2012.9%2015.479999999999999%200%200Z'%20fill='%233f6b52'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='translate%28100%20215%29%20rotate%28210%29'/%3E%3Cpath%20d='M0%200%20C12.0%20-14.399999999999999%2030.0%20-12.0%2040%200%20C30.0%2012.0%2012.0%2014.399999999999999%200%200Z'%20fill='%233f6b52'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='translate%28100%20182%29%20rotate%28-30%29'/%3E%3Cpath%20d='M0%200%20C11.1%20-13.32%2027.75%20-11.1%2037%200%20C27.75%2011.1%2011.1%2013.32%200%200Z'%20fill='%233f6b52'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='translate%28100%20150%29%20rotate%28210%29'/%3E%3Cpath%20d='M0%200%20C10.2%20-12.24%2025.5%20-10.2%2034%200%20C25.5%2010.2%2010.2%2012.24%200%200Z'%20fill='%233f6b52'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='translate%28100%20122%29%20rotate%28-30%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%280.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%2872.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%28144.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%28216.0%20100%2078%29'/%3E%3Cellipse%20cx='100'%20cy='56.92'%20rx='12.24'%20ry='21.08'%20fill='%23e8a39d'%20stroke='%239fbb99'%20stroke-width='1.6'%20transform='rotate%28288.0%20100%2078%29'/%3E%3Ccircle%20cx='100'%20cy='78'%20r='9.520000000000001'%20fill='%23e0b07f'/%3E%3C/g%3E%3C/svg%3E");
  --art-ok:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Cellipse%20cx='24'%20cy='14.7'%20rx='5.3999999999999995'%20ry='9.3'%20fill='%239fbb99'%20transform='rotate%280.0%2024%2024%29'/%3E%3Cellipse%20cx='24'%20cy='14.7'%20rx='5.3999999999999995'%20ry='9.3'%20fill='%239fbb99'%20transform='rotate%2872.0%2024%2024%29'/%3E%3Cellipse%20cx='24'%20cy='14.7'%20rx='5.3999999999999995'%20ry='9.3'%20fill='%239fbb99'%20transform='rotate%28144.0%2024%2024%29'/%3E%3Cellipse%20cx='24'%20cy='14.7'%20rx='5.3999999999999995'%20ry='9.3'%20fill='%239fbb99'%20transform='rotate%28216.0%2024%2024%29'/%3E%3Cellipse%20cx='24'%20cy='14.7'%20rx='5.3999999999999995'%20ry='9.3'%20fill='%239fbb99'%20transform='rotate%28288.0%2024%2024%29'/%3E%3Ccircle%20cx='24'%20cy='24'%20r='4.2'%20fill='%231a2a21'/%3E%3C/svg%3E");
  --art-err:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Cpath%20d='M24%2044%20C24%2034%2026%2030%2030%2024'%20fill='none'%20stroke='%23ee9a9a'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cellipse%20cx='32'%20cy='13.18'%20rx='3.96'%20ry='6.82'%20fill='%231a2a21'%20stroke='%23ee9a9a'%20stroke-width='2.4'%20transform='rotate%280.0%2032%2020%29'/%3E%3Cellipse%20cx='32'%20cy='13.18'%20rx='3.96'%20ry='6.82'%20fill='%231a2a21'%20stroke='%23ee9a9a'%20stroke-width='2.4'%20transform='rotate%2872.0%2032%2020%29'/%3E%3Cellipse%20cx='32'%20cy='13.18'%20rx='3.96'%20ry='6.82'%20fill='%231a2a21'%20stroke='%23ee9a9a'%20stroke-width='2.4'%20transform='rotate%28144.0%2032%2020%29'/%3E%3Cellipse%20cx='32'%20cy='13.18'%20rx='3.96'%20ry='6.82'%20fill='%231a2a21'%20stroke='%23ee9a9a'%20stroke-width='2.4'%20transform='rotate%28216.0%2032%2020%29'/%3E%3Cellipse%20cx='32'%20cy='13.18'%20rx='3.96'%20ry='6.82'%20fill='%231a2a21'%20stroke='%23ee9a9a'%20stroke-width='2.4'%20transform='rotate%28288.0%2032%2020%29'/%3E%3Ccircle%20cx='32'%20cy='20'%20r='3.08'%20fill='%23ee9a9a'/%3E%3C/svg%3E");
}
/* ---- Kawaii · Bonbon (clair) ---- */
[data-mode="kawaii"][data-theme="light"]{
  color-scheme:light;
  --bg:#fdeef6;
  --bg2:#fff5fa;
  --panel-rgb:255,255,255;
  --panel:rgba(var(--panel-rgb),.78);
  --panel-solid:#ffffff;
  --fg:91,74,114;
  --panel2:rgba(var(--fg),.045);
  --line:rgba(var(--fg),.13);
  --line2:rgba(var(--fg),.22);
  --text:#4f3d69;
  --muted:#6f5b8c;
  --dim:#6f5c8f;
  --accent:#ad2a6a;
  --accent2:#6b4bd6;
  --accent3:#17649c;
  --accent-rgb:173,42,106;
  --accent2-rgb:107,75,214;
  --accent3-rgb:23,100,156;
  --ok:#0f6e50;
  --warn:#9a5200;
  --err:#b52c48;
  --ok-rgb:15,110,80;
  --warn-rgb:154,82,0;
  --err-rgb:181,44,72;
  --on-accent:#ffffff;
  --on-err:#ffffff;
  --on-warn:#ffffff;
  --on-ok:#ffffff;
  --warn-text:#6e3a00;
  --grad:linear-gradient(135deg,#ff8ec0,#c4a6ff 55%,#7cc8ff);
  --grad-btn:linear-gradient(135deg,#ff9ecb 0%,#c9a6ff 55%,#8ad2ff 100%);
  --on-grad:#3b2a55;
  --field:rgba(255,255,255,.85);
  --field2:rgba(91,74,114,.05);
  --scrim-rgb:60,40,90;
  --blob:.45;
  --blob1:#ffb6d9;
  --blob2:#cdb6ff;
  --blob3:#a9e4ff;
  --radius:24px;
  --rr:1.75;
  --sans:Nunito,Quicksand,ui-rounded,"Segoe UI",system-ui,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --font-head:Quicksand,Nunito,ui-rounded,system-ui,sans-serif;
  --shadow:0 14px 34px -14px rgba(199,58,128,.30);
  --glass-blur:14px;
  --glass-sat:130%;
  --spd:1.2;
  --bw:1px;
  --code:#4f3d69;
  --caret:#c73a80;
  --sel:rgba(199,58,128,.20);
  --tk-c:#6e5f88;
  --tk-s:#0f7a5a;
  --tk-n:#b04a00;
  --tk-k:#a12a8a;
  --tk-t:#2b5fc4;
  --tk-f:#6b3fd0;
  --tk-p:#c02a6a;
  --tk-o:#2a6f8a;
  --tk-call:#8a5400;
  --ext-h:#6b4bd6;
  --info:#6b4bd6;
  --p0:#ad2a6a;
  --p1:#6b4bd6;
  --p2:#c47a00;
  --p3:#17649c;
  --p4:#0f6e50;
  --p5:#d0417a;
  --p6:#8a5400;
  --p7:#2a6f8a;
  --p8:#e0602a;
  --p9:#7c6a99;
  --plot-bg:#ffffff;
  --plot-grid:rgba(var(--fg),.10);
  --plot-zero:rgba(var(--fg),.30);
  --plot-text:#4f3d69;
  --plot-text2:#7c6a99;
  --d-find:rgba(var(--warn-rgb),.30);
  --d-cur:rgba(var(--accent-rgb),.55);
  --d-word:rgba(var(--accent2-rgb),.30);
  --d-br:rgba(var(--accent-rgb),.38);
  --logo1:#ff8ec0;
  --logo2:#9b7bff;
  --logo-bolt:#ffffff;
  --knob:#ffffff;
  --pin-gnd:#8a7aa5;
  --sheen-rgb:255,255,255;
  --shade-rgb:120,60,140;
  --ink:#3b2a55;
  --paper:#ffffff;
  --dots:none;
  --deco-img:linear-gradient(135deg,#ffe1ee 0%,#e6dcff 38%,#d6eeff 72%,#d3f6e8 100%),url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20260%20260'%3E%3Cpath%20d='M30%2044%20c-8%20-8%20-8%20-14%20-3%20-16%20c3%20-1%205%201%203%203%20c2%20-2%206%20-4%208%200%20c2%205%20-2%209%20-8%2013z'%20fill='%23ff9ecb'%20opacity='.8'/%3E%3Cpath%20d='M120%2011%20L122.52%2017.48%20L129%2020%20L122.52%2022.52%20L120%2029%20L117.48%2022.52%20L111%2020%20L117.48%2017.48Z'%20fill='%23c4a6ff'%20opacity='0.85'/%3E%3Cpath%20d='M210%2059%20L213.08%2066.92%20L221%2070%20L213.08%2073.08%20L210%2081%20L206.92%2073.08%20L199%2070%20L206.92%2066.92Z'%20fill='%237cc8ff'%20opacity='0.85'/%3E%3Cpath%20d='M70%20134%20c-8%20-8%20-8%20-14%20-3%20-16%20c3%20-1%205%201%203%203%20c2%20-2%206%20-4%208%200%20c2%205%20-2%209%20-8%2013z'%20fill='%23ffd27a'%20opacity='.8'/%3E%3Cpath%20d='M170%20141%20L172.52%20147.48%20L179%20150%20L172.52%20152.52%20L170%20159%20L167.48%20152.52%20L161%20150%20L167.48%20147.48Z'%20fill='%23ff9ecb'%20opacity='0.85'/%3E%3Cpath%20d='M240%20189%20L243.08%20196.92%20L251%20200%20L243.08%20203.08%20L240%20211%20L236.92%20203.08%20L229%20200%20L236.92%20196.92Z'%20fill='%23c4a6ff'%20opacity='0.85'/%3E%3Cpath%20d='M40%20224%20c-8%20-8%20-8%20-14%20-3%20-16%20c3%20-1%205%201%203%203%20c2%20-2%206%20-4%208%200%20c2%205%20-2%209%20-8%2013z'%20fill='%237cc8ff'%20opacity='.8'/%3E%3Cpath%20d='M130%20231%20L132.52%20237.48%20L139%20240%20L132.52%20242.52%20L130%20249%20L127.48%20242.52%20L121%20240%20L127.48%20237.48Z'%20fill='%23ffd27a'%20opacity='0.85'/%3E%3Cpath%20d='M200%209%20L203.08%2016.92%20L211%2020%20L203.08%2023.08%20L200%2031%20L196.92%2023.08%20L189%2020%20L196.92%2016.92Z'%20fill='%23ff9ecb'%20opacity='0.85'/%3E%3C/svg%3E");
  --deco-size:auto,260px 260px;
  --deco-pos:0 0;
  --deco-rep:no-repeat,repeat;
  --deco-op:1;
  --overlay:none;
  --burst1:#ff8ec0;
  --burst2:#c4a6ff;
  --burst3:#7cc8ff;
  --burst4:#7be0b8;
  --burst5:#ffe07a;
  --burst6:#ffffff;
  --plat0:#ad2a6a;
  --plat1:#b52c48;
  --plat2:#9a5200;
  --plat3:#d0417a;
  --plat4:#17649c;
  --plat5:#6b4bd6;
  --plat6:#0f6e50;
  --plat-x:#7c6a99;
  --art-welcome:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20164%20110'%3E%3Crect%20x='24'%20y='36'%20width='26'%20height='30'%20rx='3'%20fill='%23ffd6e7'%20stroke='%235b4a72'%20stroke-width='3'/%3E%3Crect%20x='14'%20y='14'%20width='136'%20height='82'%20rx='10'%20fill='%23fff7fb'%20stroke='%235b4a72'%20stroke-width='3'/%3E%3Crect%20x='92'%20y='34'%20width='38'%20height='38'%20rx='4'%20fill='%23ffd6e7'%20stroke='%235b4a72'%20stroke-width='2'/%3E%3Crect%20x='34'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='34'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='45'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='45'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='56'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='56'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='67'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='67'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='78'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='78'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='89'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='89'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='100'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='100'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='111'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='111'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Ccircle%20cx='66'%20cy='30'%20r='5'%20fill='%23ff6fa8'/%3E%3Ccircle%20cx='60'%20cy='76'%20r='7'%20fill='none'%20stroke='%23ff6fa8'%20stroke-width='2'/%3E%3Ccircle%20cx='78'%20cy='52'%20r='0'%20/%3E%3Cellipse%20cx='64'%20cy='52'%20rx='4'%20ry='5.5'%20fill='%235b4a72'/%3E%3Cellipse%20cx='92'%20cy='52'%20rx='4'%20ry='5.5'%20fill='%235b4a72'/%3E%3Cpath%20d='M70%2062%20Q78%2070%2086%2062'%20fill='none'%20stroke='%235b4a72'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cellipse%20cx='54'%20cy='62'%20rx='6'%20ry='3.5'%20fill='%23ff6fa8'%20opacity='.55'/%3E%3Cellipse%20cx='102'%20cy='62'%20rx='6'%20ry='3.5'%20fill='%23ff6fa8'%20opacity='.55'/%3E%3Cpath%20d='M14%204%20L16.240000000000002%209.76%20L22%2012%20L16.240000000000002%2014.24%20L14%2020%20L11.76%2014.24%20L6%2012%20L11.76%209.76Z'%20fill='%23ffb454'%20opacity='1'/%3E%3Cpath%20d='M150%2010%20L151.68%2014.32%20L156%2016%20L151.68%2017.68%20L150%2022%20L148.32%2017.68%20L144%2016%20L148.32%2014.32Z'%20fill='%23ff8ec0'%20opacity='1'/%3E%3Cpath%20d='M154%2085%20L155.96%2090.04%20L161%2092%20L155.96%2093.96%20L154%2099%20L152.04%2093.96%20L147%2092%20L152.04%2090.04Z'%20fill='%237cc8ff'%20opacity='1'/%3E%3C/svg%3E");
  --art-empty:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20164%20110'%3E%3Crect%20x='24'%20y='36'%20width='26'%20height='30'%20rx='3'%20fill='%23ffd6e7'%20stroke='%235b4a72'%20stroke-width='4'/%3E%3Crect%20x='14'%20y='14'%20width='136'%20height='82'%20rx='10'%20fill='%23fff7fb'%20stroke='%235b4a72'%20stroke-width='4'/%3E%3Crect%20x='92'%20y='34'%20width='38'%20height='38'%20rx='4'%20fill='%23ffd6e7'%20stroke='%235b4a72'%20stroke-width='3'/%3E%3Crect%20x='34'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='34'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='45'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='45'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='56'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='56'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='67'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='67'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='78'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='78'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='89'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='89'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='100'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='100'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='111'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='111'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Ccircle%20cx='66'%20cy='30'%20r='5'%20fill='%23ff6fa8'/%3E%3Ccircle%20cx='60'%20cy='76'%20r='7'%20fill='none'%20stroke='%23ff6fa8'%20stroke-width='3'/%3E%3Ccircle%20cx='78'%20cy='52'%20r='0'%20/%3E%3Cellipse%20cx='64'%20cy='52'%20rx='4'%20ry='5.5'%20fill='%235b4a72'/%3E%3Cellipse%20cx='92'%20cy='52'%20rx='4'%20ry='5.5'%20fill='%235b4a72'/%3E%3Cpath%20d='M70%2062%20Q78%2070%2086%2062'%20fill='none'%20stroke='%235b4a72'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cellipse%20cx='54'%20cy='62'%20rx='6'%20ry='3.5'%20fill='%23ff6fa8'%20opacity='.55'/%3E%3Cellipse%20cx='102'%20cy='62'%20rx='6'%20ry='3.5'%20fill='%23ff6fa8'%20opacity='.55'/%3E%3C/svg%3E");
  --art-ok:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Cpath%20d='M24%204%20L29.6%2018.4%20L44%2024%20L29.6%2029.6%20L24%2044%20L18.4%2029.6%20L4%2024%20L18.4%2018.4Z'%20fill='%230f6e50'%20opacity='1'/%3E%3Cpath%20d='M40%204%20L41.68%208.32%20L46%2010%20L41.68%2011.68%20L40%2016%20L38.32%2011.68%20L34%2010%20L38.32%208.32Z'%20fill='%230f6e50'%20opacity='1'/%3E%3Cpath%20d='M8%2033%20L9.4%2036.6%20L13%2038%20L9.4%2039.4%20L8%2043%20L6.6%2039.4%20L3%2038%20L6.6%2036.6Z'%20fill='%230f6e50'%20opacity='1'/%3E%3C/svg%3E");
  --art-err:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Ccircle%20cx='24'%20cy='24'%20r='19'%20fill='none'%20stroke='%23b52c48'%20stroke-width='4'/%3E%3Ccircle%20cx='17'%20cy='21'%20r='2.6'%20fill='%23b52c48'/%3E%3Ccircle%20cx='31'%20cy='21'%20r='2.6'%20fill='%23b52c48'/%3E%3Cpath%20d='M16%2034%20Q24%2026%2032%2034'%20fill='none'%20stroke='%23b52c48'%20stroke-width='3.4'%20stroke-linecap='round'/%3E%3C/svg%3E");
}
/* ---- Kawaii · Bonbon (sombre) ---- */
[data-mode="kawaii"][data-theme="dark"]{
  color-scheme:dark;
  --bg:#231a38;
  --bg2:#2b2145;
  --panel-rgb:46,34,72;
  --panel:rgba(var(--panel-rgb),.78);
  --panel-solid:#30244f;
  --fg:240,228,255;
  --panel2:rgba(var(--fg),.05);
  --line:rgba(var(--fg),.12);
  --line2:rgba(var(--fg),.22);
  --text:#f3eaff;
  --muted:#cbb8ea;
  --dim:#b39fd6;
  --accent:#ff8ec0;
  --accent2:#c4a6ff;
  --accent3:#7cc8ff;
  --accent-rgb:255,142,192;
  --accent2-rgb:196,166,255;
  --accent3-rgb:124,200,255;
  --ok:#7be0b8;
  --warn:#ffc98a;
  --err:#ff8fa6;
  --ok-rgb:123,224,184;
  --warn-rgb:255,201,138;
  --err-rgb:255,143,166;
  --on-accent:#3a1030;
  --on-err:#3a0a18;
  --on-warn:#3a2200;
  --on-ok:#062a1c;
  --warn-text:#ffdcab;
  --grad:linear-gradient(135deg,#ff8ec0,#c4a6ff 55%,#7cc8ff);
  --grad-btn:linear-gradient(135deg,#ff9ecb 0%,#c9a6ff 55%,#8ad2ff 100%);
  --on-grad:#2a1c45;
  --field:rgba(20,10,40,.4);
  --field2:rgba(20,10,40,.22);
  --scrim-rgb:20,10,40;
  --blob:.35;
  --blob1:#8a3f7a;
  --blob2:#4a3aa8;
  --blob3:#2f6a9a;
  --radius:24px;
  --rr:1.75;
  --sans:Nunito,Quicksand,ui-rounded,"Segoe UI",system-ui,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --font-head:Quicksand,Nunito,ui-rounded,system-ui,sans-serif;
  --shadow:0 14px 36px -14px rgba(0,0,0,.6);
  --glass-blur:14px;
  --glass-sat:130%;
  --spd:1.2;
  --bw:1px;
  --code:#f3eaff;
  --caret:#ff8ec0;
  --sel:rgba(255,142,192,.28);
  --tk-c:#a898c8;
  --tk-s:#9ff0c8;
  --tk-n:#ffc48a;
  --tk-k:#ff9ee0;
  --tk-t:#9ac4ff;
  --tk-f:#c4b0ff;
  --tk-p:#ff9ec4;
  --tk-o:#9adfff;
  --tk-call:#ffe08a;
  --ext-h:#c4b0ff;
  --info:#c4b0ff;
  --p0:#ff8ec0;
  --p1:#c4a6ff;
  --p2:#ffc98a;
  --p3:#7cc8ff;
  --p4:#7be0b8;
  --p5:#ff9ee0;
  --p6:#ffe08a;
  --p7:#9adfff;
  --p8:#ffa07a;
  --p9:#d9cdf0;
  --plot-bg:#30244f;
  --plot-grid:rgba(var(--fg),.09);
  --plot-zero:rgba(var(--fg),.30);
  --plot-text:#f3eaff;
  --plot-text2:#cbb8ea;
  --d-find:rgba(var(--warn-rgb),.30);
  --d-cur:rgba(var(--accent-rgb),.55);
  --d-word:rgba(var(--accent2-rgb),.30);
  --d-br:rgba(var(--accent-rgb),.38);
  --logo1:#ff8ec0;
  --logo2:#9b7bff;
  --logo-bolt:#ffffff;
  --knob:#f3eaff;
  --pin-gnd:#a898c8;
  --sheen-rgb:255,255,255;
  --shade-rgb:0,0,0;
  --ink:#2a1c45;
  --paper:#ffffff;
  --dots:none;
  --deco-img:linear-gradient(135deg,#2a1c45 0%,#241a3c 50%,#1c1a3c 100%),url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20260%20260'%3E%3Cpath%20d='M30%2044%20c-8%20-8%20-8%20-14%20-3%20-16%20c3%20-1%205%201%203%203%20c2%20-2%206%20-4%208%200%20c2%205%20-2%209%20-8%2013z'%20fill='%23ff8ec0'%20opacity='.8'/%3E%3Cpath%20d='M120%2011%20L122.52%2017.48%20L129%2020%20L122.52%2022.52%20L120%2029%20L117.48%2022.52%20L111%2020%20L117.48%2017.48Z'%20fill='%23c4a6ff'%20opacity='0.85'/%3E%3Cpath%20d='M210%2059%20L213.08%2066.92%20L221%2070%20L213.08%2073.08%20L210%2081%20L206.92%2073.08%20L199%2070%20L206.92%2066.92Z'%20fill='%237cc8ff'%20opacity='0.85'/%3E%3Cpath%20d='M70%20134%20c-8%20-8%20-8%20-14%20-3%20-16%20c3%20-1%205%201%203%203%20c2%20-2%206%20-4%208%200%20c2%205%20-2%209%20-8%2013z'%20fill='%23ffd27a'%20opacity='.8'/%3E%3Cpath%20d='M170%20141%20L172.52%20147.48%20L179%20150%20L172.52%20152.52%20L170%20159%20L167.48%20152.52%20L161%20150%20L167.48%20147.48Z'%20fill='%23ff8ec0'%20opacity='0.85'/%3E%3Cpath%20d='M240%20189%20L243.08%20196.92%20L251%20200%20L243.08%20203.08%20L240%20211%20L236.92%20203.08%20L229%20200%20L236.92%20196.92Z'%20fill='%23c4a6ff'%20opacity='0.85'/%3E%3Cpath%20d='M40%20224%20c-8%20-8%20-8%20-14%20-3%20-16%20c3%20-1%205%201%203%203%20c2%20-2%206%20-4%208%200%20c2%205%20-2%209%20-8%2013z'%20fill='%237cc8ff'%20opacity='.8'/%3E%3Cpath%20d='M130%20231%20L132.52%20237.48%20L139%20240%20L132.52%20242.52%20L130%20249%20L127.48%20242.52%20L121%20240%20L127.48%20237.48Z'%20fill='%23ffd27a'%20opacity='0.85'/%3E%3Cpath%20d='M200%209%20L203.08%2016.92%20L211%2020%20L203.08%2023.08%20L200%2031%20L196.92%2023.08%20L189%2020%20L196.92%2016.92Z'%20fill='%23ff8ec0'%20opacity='0.85'/%3E%3C/svg%3E");
  --deco-size:auto,260px 260px;
  --deco-pos:0 0;
  --deco-rep:no-repeat,repeat;
  --deco-op:1;
  --overlay:none;
  --burst1:#ff8ec0;
  --burst2:#c4a6ff;
  --burst3:#7cc8ff;
  --burst4:#7be0b8;
  --burst5:#ffe07a;
  --burst6:#ffffff;
  --plat0:#ff8ec0;
  --plat1:#ff8fa6;
  --plat2:#ffc98a;
  --plat3:#ff9ee0;
  --plat4:#7cc8ff;
  --plat5:#c4a6ff;
  --plat6:#7be0b8;
  --plat-x:#b39fd6;
  --art-welcome:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20164%20110'%3E%3Crect%20x='24'%20y='36'%20width='26'%20height='30'%20rx='3'%20fill='%235a3a72'%20stroke='%23f3eaff'%20stroke-width='3'/%3E%3Crect%20x='14'%20y='14'%20width='136'%20height='82'%20rx='10'%20fill='%233a2d5c'%20stroke='%23f3eaff'%20stroke-width='3'/%3E%3Crect%20x='92'%20y='34'%20width='38'%20height='38'%20rx='4'%20fill='%235a3a72'%20stroke='%23f3eaff'%20stroke-width='2'/%3E%3Crect%20x='34'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='34'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='45'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='45'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='56'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='56'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='67'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='67'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='78'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='78'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='89'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='89'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='100'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='100'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='111'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='111'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Ccircle%20cx='66'%20cy='30'%20r='5'%20fill='%23ff8ec0'/%3E%3Ccircle%20cx='60'%20cy='76'%20r='7'%20fill='none'%20stroke='%23ff8ec0'%20stroke-width='2'/%3E%3Ccircle%20cx='78'%20cy='52'%20r='0'%20/%3E%3Cellipse%20cx='64'%20cy='52'%20rx='4'%20ry='5.5'%20fill='%23f3eaff'/%3E%3Cellipse%20cx='92'%20cy='52'%20rx='4'%20ry='5.5'%20fill='%23f3eaff'/%3E%3Cpath%20d='M70%2062%20Q78%2070%2086%2062'%20fill='none'%20stroke='%23f3eaff'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cellipse%20cx='54'%20cy='62'%20rx='6'%20ry='3.5'%20fill='%23ff8ec0'%20opacity='.55'/%3E%3Cellipse%20cx='102'%20cy='62'%20rx='6'%20ry='3.5'%20fill='%23ff8ec0'%20opacity='.55'/%3E%3Cpath%20d='M14%204%20L16.240000000000002%209.76%20L22%2012%20L16.240000000000002%2014.24%20L14%2020%20L11.76%2014.24%20L6%2012%20L11.76%209.76Z'%20fill='%23ffe07a'%20opacity='1'/%3E%3Cpath%20d='M150%2010%20L151.68%2014.32%20L156%2016%20L151.68%2017.68%20L150%2022%20L148.32%2017.68%20L144%2016%20L148.32%2014.32Z'%20fill='%23ff8ec0'%20opacity='1'/%3E%3Cpath%20d='M154%2085%20L155.96%2090.04%20L161%2092%20L155.96%2093.96%20L154%2099%20L152.04%2093.96%20L147%2092%20L152.04%2090.04Z'%20fill='%237cc8ff'%20opacity='1'/%3E%3C/svg%3E");
  --art-empty:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20164%20110'%3E%3Crect%20x='24'%20y='36'%20width='26'%20height='30'%20rx='3'%20fill='%235a3a72'%20stroke='%23f3eaff'%20stroke-width='4'/%3E%3Crect%20x='14'%20y='14'%20width='136'%20height='82'%20rx='10'%20fill='%233a2d5c'%20stroke='%23f3eaff'%20stroke-width='4'/%3E%3Crect%20x='92'%20y='34'%20width='38'%20height='38'%20rx='4'%20fill='%235a3a72'%20stroke='%23f3eaff'%20stroke-width='3'/%3E%3Crect%20x='34'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='34'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='45'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='45'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='56'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='56'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='67'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='67'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='78'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='78'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='89'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='89'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='100'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='100'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='111'%20y='6'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Crect%20x='111'%20y='95'%20width='6'%20height='9'%20fill='%23c4a6ff'/%3E%3Ccircle%20cx='66'%20cy='30'%20r='5'%20fill='%23ff8ec0'/%3E%3Ccircle%20cx='60'%20cy='76'%20r='7'%20fill='none'%20stroke='%23ff8ec0'%20stroke-width='3'/%3E%3Ccircle%20cx='78'%20cy='52'%20r='0'%20/%3E%3Cellipse%20cx='64'%20cy='52'%20rx='4'%20ry='5.5'%20fill='%23f3eaff'/%3E%3Cellipse%20cx='92'%20cy='52'%20rx='4'%20ry='5.5'%20fill='%23f3eaff'/%3E%3Cpath%20d='M70%2062%20Q78%2070%2086%2062'%20fill='none'%20stroke='%23f3eaff'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cellipse%20cx='54'%20cy='62'%20rx='6'%20ry='3.5'%20fill='%23ff8ec0'%20opacity='.55'/%3E%3Cellipse%20cx='102'%20cy='62'%20rx='6'%20ry='3.5'%20fill='%23ff8ec0'%20opacity='.55'/%3E%3C/svg%3E");
  --art-ok:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Cpath%20d='M24%204%20L29.6%2018.4%20L44%2024%20L29.6%2029.6%20L24%2044%20L18.4%2029.6%20L4%2024%20L18.4%2018.4Z'%20fill='%237be0b8'%20opacity='1'/%3E%3Cpath%20d='M40%204%20L41.68%208.32%20L46%2010%20L41.68%2011.68%20L40%2016%20L38.32%2011.68%20L34%2010%20L38.32%208.32Z'%20fill='%237be0b8'%20opacity='1'/%3E%3Cpath%20d='M8%2033%20L9.4%2036.6%20L13%2038%20L9.4%2039.4%20L8%2043%20L6.6%2039.4%20L3%2038%20L6.6%2036.6Z'%20fill='%237be0b8'%20opacity='1'/%3E%3C/svg%3E");
  --art-err:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Ccircle%20cx='24'%20cy='24'%20r='19'%20fill='none'%20stroke='%23ff8fa6'%20stroke-width='4'/%3E%3Ccircle%20cx='17'%20cy='21'%20r='2.6'%20fill='%23ff8fa6'/%3E%3Ccircle%20cx='31'%20cy='21'%20r='2.6'%20fill='%23ff8fa6'/%3E%3Cpath%20d='M16%2034%20Q24%2026%2032%2034'%20fill='none'%20stroke='%23ff8fa6'%20stroke-width='3.4'%20stroke-linecap='round'/%3E%3C/svg%3E");
}
/* ---- Kawaii · Nuage (clair) ---- */
[data-mode="kawaii2"][data-theme="light"]{
  color-scheme:light;
  --bg:#f1ecff;
  --bg2:#f8f4ff;
  --panel-rgb:255,255,255;
  --panel:rgba(var(--panel-rgb),.82);
  --panel-solid:#ffffff;
  --fg:77,61,120;
  --panel2:rgba(var(--fg),.05);
  --line:rgba(var(--fg),.14);
  --line2:rgba(var(--fg),.24);
  --text:#463670;
  --muted:#66539a;
  --dim:#74629f;
  --accent:#a82878;
  --accent2:#6a45d8;
  --accent3:#0a6580;
  --accent-rgb:168,40,120;
  --accent2-rgb:106,69,216;
  --accent3-rgb:10,101,128;
  --ok:#0f6e4f;
  --warn:#93500a;
  --err:#b32a4d;
  --ok-rgb:15,110,79;
  --warn-rgb:147,80,10;
  --err-rgb:179,42,77;
  --on-accent:#ffffff;
  --on-err:#ffffff;
  --on-warn:#ffffff;
  --on-ok:#ffffff;
  --warn-text:#6b3a00;
  --grad:linear-gradient(135deg,#ffb6e6,#c9b6ff 55%,#b6e6ff);
  --grad-btn:linear-gradient(135deg,#ffbde8 0%,#cdbcff 55%,#bde8ff 100%);
  --on-grad:#3a2c66;
  --field:rgba(255,255,255,.9);
  --field2:rgba(77,61,120,.05);
  --scrim-rgb:60,40,110;
  --blob:.5;
  --blob1:#ffd0ee;
  --blob2:#d6c8ff;
  --blob3:#c8ecff;
  --radius:26px;
  --rr:2.1;
  --sans:Quicksand,Nunito,ui-rounded,"Segoe UI",system-ui,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --font-head:Quicksand,Nunito,ui-rounded,system-ui,sans-serif;
  --shadow:0 12px 34px -12px rgba(140,110,230,.35);
  --glass-blur:16px;
  --glass-sat:130%;
  --spd:1.3;
  --bw:1px;
  --code:#463670;
  --caret:#c2358f;
  --sel:rgba(106,69,216,.20);
  --tk-c:#6b5d92;
  --tk-s:#0f7a58;
  --tk-n:#a84a00;
  --tk-k:#9a2fa0;
  --tk-t:#2a5fc4;
  --tk-f:#6a45d8;
  --tk-p:#c02a70;
  --tk-o:#1f6f8a;
  --tk-call:#84520a;
  --ext-h:#6a45d8;
  --info:#6a45d8;
  --p0:#a82878;
  --p1:#6a45d8;
  --p2:#c47a00;
  --p3:#0a6580;
  --p4:#0f6e4f;
  --p5:#d0417a;
  --p6:#84520a;
  --p7:#2a5fc4;
  --p8:#e0602a;
  --p9:#74629f;
  --plot-bg:#ffffff;
  --plot-grid:rgba(var(--fg),.10);
  --plot-zero:rgba(var(--fg),.30);
  --plot-text:#463670;
  --plot-text2:#74629f;
  --d-find:rgba(var(--warn-rgb),.30);
  --d-cur:rgba(var(--accent-rgb),.55);
  --d-word:rgba(var(--accent2-rgb),.30);
  --d-br:rgba(var(--accent-rgb),.38);
  --logo1:#ffb6e6;
  --logo2:#b6a0ff;
  --logo-bolt:#ffffff;
  --knob:#ffffff;
  --pin-gnd:#8a7aa5;
  --sheen-rgb:255,255,255;
  --shade-rgb:110,80,190;
  --ink:#3a2c66;
  --paper:#ffffff;
  --dots:none;
  --deco-img:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20760%20200'%3E%3Cg%20fill='%23ffffff'%20transform='translate%2810%2030%29%20scale%281.3%29'%3E%3Cellipse%20cx='40'%20cy='40'%20rx='40'%20ry='22'/%3E%3Cellipse%20cx='75'%20cy='30'%20rx='30'%20ry='24'/%3E%3Cellipse%20cx='105'%20cy='42'%20rx='34'%20ry='20'/%3E%3Cellipse%20cx='58'%20cy='24'%20rx='24'%20ry='20'/%3E%3C/g%3E%3Cg%20fill='%23e9deff'%20transform='translate%28300%2090%29%20scale%281.0%29'%3E%3Cellipse%20cx='40'%20cy='40'%20rx='40'%20ry='22'/%3E%3Cellipse%20cx='75'%20cy='30'%20rx='30'%20ry='24'/%3E%3Cellipse%20cx='105'%20cy='42'%20rx='34'%20ry='20'/%3E%3Cellipse%20cx='58'%20cy='24'%20rx='24'%20ry='20'/%3E%3C/g%3E%3Cg%20fill='%23ffffff'%20transform='translate%28560%2020%29%20scale%281.5%29'%3E%3Cellipse%20cx='40'%20cy='40'%20rx='40'%20ry='22'/%3E%3Cellipse%20cx='75'%20cy='30'%20rx='30'%20ry='24'/%3E%3Cellipse%20cx='105'%20cy='42'%20rx='34'%20ry='20'/%3E%3Cellipse%20cx='58'%20cy='24'%20rx='24'%20ry='20'/%3E%3C/g%3E%3Cpath%20d='M250%2032%20L252.24%2037.76%20L258%2040%20L252.24%2042.24%20L250%2048%20L247.76%2042.24%20L242%2040%20L247.76%2037.76Z'%20fill='%23e9deff'%20opacity='1'/%3E%3Cpath%20d='M500%20114%20L501.68%20118.32%20L506%20120%20L501.68%20121.68%20L500%20126%20L498.32%20121.68%20L494%20120%20L498.32%20118.32Z'%20fill='%23e9deff'%20opacity='1'/%3E%3C/svg%3E"),url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20260%20260'%3E%3Cpath%20d='M30%2044%20c-8%20-8%20-8%20-14%20-3%20-16%20c3%20-1%205%201%203%203%20c2%20-2%206%20-4%208%200%20c2%205%20-2%209%20-8%2013z'%20fill='%23ffb6e6'%20opacity='.8'/%3E%3Cpath%20d='M120%2011%20L122.52%2017.48%20L129%2020%20L122.52%2022.52%20L120%2029%20L117.48%2022.52%20L111%2020%20L117.48%2017.48Z'%20fill='%23c9b6ff'%20opacity='0.85'/%3E%3Cpath%20d='M210%2059%20L213.08%2066.92%20L221%2070%20L213.08%2073.08%20L210%2081%20L206.92%2073.08%20L199%2070%20L206.92%2066.92Z'%20fill='%23a8dcf5'%20opacity='0.85'/%3E%3Cpath%20d='M70%20134%20c-8%20-8%20-8%20-14%20-3%20-16%20c3%20-1%205%201%203%203%20c2%20-2%206%20-4%208%200%20c2%205%20-2%209%20-8%2013z'%20fill='%23ffe08a'%20opacity='.8'/%3E%3Cpath%20d='M170%20141%20L172.52%20147.48%20L179%20150%20L172.52%20152.52%20L170%20159%20L167.48%20152.52%20L161%20150%20L167.48%20147.48Z'%20fill='%23ffb6e6'%20opacity='0.85'/%3E%3Cpath%20d='M240%20189%20L243.08%20196.92%20L251%20200%20L243.08%20203.08%20L240%20211%20L236.92%20203.08%20L229%20200%20L236.92%20196.92Z'%20fill='%23c9b6ff'%20opacity='0.85'/%3E%3Cpath%20d='M40%20224%20c-8%20-8%20-8%20-14%20-3%20-16%20c3%20-1%205%201%203%203%20c2%20-2%206%20-4%208%200%20c2%205%20-2%209%20-8%2013z'%20fill='%23a8dcf5'%20opacity='.8'/%3E%3Cpath%20d='M130%20231%20L132.52%20237.48%20L139%20240%20L132.52%20242.52%20L130%20249%20L127.48%20242.52%20L121%20240%20L127.48%20237.48Z'%20fill='%23ffe08a'%20opacity='0.85'/%3E%3Cpath%20d='M200%209%20L203.08%2016.92%20L211%2020%20L203.08%2023.08%20L200%2031%20L196.92%2023.08%20L189%2020%20L196.92%2016.92Z'%20fill='%23ffb6e6'%20opacity='0.85'/%3E%3C/svg%3E");
  --deco-size:100% auto,260px 260px;
  --deco-pos:center bottom,0 0;
  --deco-rep:no-repeat,repeat;
  --deco-op:1;
  --overlay:none;
  --burst1:#ffb6e6;
  --burst2:#c9b6ff;
  --burst3:#b6e6ff;
  --burst4:#a8f0d0;
  --burst5:#fff0a0;
  --burst6:#ffffff;
  --plat0:#a82878;
  --plat1:#b32a4d;
  --plat2:#93500a;
  --plat3:#d0417a;
  --plat4:#0a6580;
  --plat5:#6a45d8;
  --plat6:#0f6e4f;
  --plat-x:#74629f;
  --art-welcome:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20164%20110'%3E%3Crect%20x='24'%20y='36'%20width='26'%20height='30'%20rx='3'%20fill='%23e6dcff'%20stroke='%236a55a8'%20stroke-width='3'/%3E%3Crect%20x='14'%20y='14'%20width='136'%20height='82'%20rx='10'%20fill='%23ffffff'%20stroke='%236a55a8'%20stroke-width='3'/%3E%3Crect%20x='92'%20y='34'%20width='38'%20height='38'%20rx='4'%20fill='%23e6dcff'%20stroke='%236a55a8'%20stroke-width='2'/%3E%3Crect%20x='34'%20y='6'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='34'%20y='95'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='45'%20y='6'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='45'%20y='95'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='56'%20y='6'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='56'%20y='95'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='67'%20y='6'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='67'%20y='95'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='78'%20y='6'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='78'%20y='95'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='89'%20y='6'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='89'%20y='95'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='100'%20y='6'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='100'%20y='95'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='111'%20y='6'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='111'%20y='95'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Ccircle%20cx='66'%20cy='30'%20r='5'%20fill='%23ff8fc7'/%3E%3Ccircle%20cx='60'%20cy='76'%20r='7'%20fill='none'%20stroke='%23ff8fc7'%20stroke-width='2'/%3E%3Ccircle%20cx='78'%20cy='52'%20r='0'%20/%3E%3Cellipse%20cx='64'%20cy='52'%20rx='4'%20ry='5.5'%20fill='%236a55a8'/%3E%3Cellipse%20cx='92'%20cy='52'%20rx='4'%20ry='5.5'%20fill='%236a55a8'/%3E%3Cpath%20d='M70%2062%20Q78%2070%2086%2062'%20fill='none'%20stroke='%236a55a8'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cellipse%20cx='54'%20cy='62'%20rx='6'%20ry='3.5'%20fill='%23ff8fc7'%20opacity='.55'/%3E%3Cellipse%20cx='102'%20cy='62'%20rx='6'%20ry='3.5'%20fill='%23ff8fc7'%20opacity='.55'/%3E%3Cpath%20d='M14%204%20L16.240000000000002%209.76%20L22%2012%20L16.240000000000002%2014.24%20L14%2020%20L11.76%2014.24%20L6%2012%20L11.76%209.76Z'%20fill='%23ffd27a'%20opacity='1'/%3E%3Cpath%20d='M150%2010%20L151.68%2014.32%20L156%2016%20L151.68%2017.68%20L150%2022%20L148.32%2017.68%20L144%2016%20L148.32%2014.32Z'%20fill='%23ff8fc7'%20opacity='1'/%3E%3Cpath%20d='M154%2085%20L155.96%2090.04%20L161%2092%20L155.96%2093.96%20L154%2099%20L152.04%2093.96%20L147%2092%20L152.04%2090.04Z'%20fill='%238fd8ea'%20opacity='1'/%3E%3C/svg%3E");
  --art-empty:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20164%20110'%3E%3Crect%20x='24'%20y='36'%20width='26'%20height='30'%20rx='3'%20fill='%23e6dcff'%20stroke='%236a55a8'%20stroke-width='4'/%3E%3Crect%20x='14'%20y='14'%20width='136'%20height='82'%20rx='10'%20fill='%23ffffff'%20stroke='%236a55a8'%20stroke-width='4'/%3E%3Crect%20x='92'%20y='34'%20width='38'%20height='38'%20rx='4'%20fill='%23e6dcff'%20stroke='%236a55a8'%20stroke-width='3'/%3E%3Crect%20x='34'%20y='6'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='34'%20y='95'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='45'%20y='6'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='45'%20y='95'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='56'%20y='6'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='56'%20y='95'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='67'%20y='6'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='67'%20y='95'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='78'%20y='6'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='78'%20y='95'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='89'%20y='6'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='89'%20y='95'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='100'%20y='6'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='100'%20y='95'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='111'%20y='6'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Crect%20x='111'%20y='95'%20width='6'%20height='9'%20fill='%23b6a0ff'/%3E%3Ccircle%20cx='66'%20cy='30'%20r='5'%20fill='%23ff8fc7'/%3E%3Ccircle%20cx='60'%20cy='76'%20r='7'%20fill='none'%20stroke='%23ff8fc7'%20stroke-width='3'/%3E%3Ccircle%20cx='78'%20cy='52'%20r='0'%20/%3E%3Cellipse%20cx='64'%20cy='52'%20rx='4'%20ry='5.5'%20fill='%236a55a8'/%3E%3Cellipse%20cx='92'%20cy='52'%20rx='4'%20ry='5.5'%20fill='%236a55a8'/%3E%3Cpath%20d='M70%2062%20Q78%2070%2086%2062'%20fill='none'%20stroke='%236a55a8'%20stroke-width='3'%20stroke-linecap='round'/%3E%3Cellipse%20cx='54'%20cy='62'%20rx='6'%20ry='3.5'%20fill='%23ff8fc7'%20opacity='.55'/%3E%3Cellipse%20cx='102'%20cy='62'%20rx='6'%20ry='3.5'%20fill='%23ff8fc7'%20opacity='.55'/%3E%3C/svg%3E");
  --art-ok:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Cpath%20d='M24%204%20L29.6%2018.4%20L44%2024%20L29.6%2029.6%20L24%2044%20L18.4%2029.6%20L4%2024%20L18.4%2018.4Z'%20fill='%230f6e4f'%20opacity='1'/%3E%3Cpath%20d='M40%204%20L41.68%208.32%20L46%2010%20L41.68%2011.68%20L40%2016%20L38.32%2011.68%20L34%2010%20L38.32%208.32Z'%20fill='%230f6e4f'%20opacity='1'/%3E%3Cpath%20d='M8%2033%20L9.4%2036.6%20L13%2038%20L9.4%2039.4%20L8%2043%20L6.6%2039.4%20L3%2038%20L6.6%2036.6Z'%20fill='%230f6e4f'%20opacity='1'/%3E%3C/svg%3E");
  --art-err:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Ccircle%20cx='24'%20cy='24'%20r='19'%20fill='none'%20stroke='%23b32a4d'%20stroke-width='4'/%3E%3Ccircle%20cx='17'%20cy='21'%20r='2.6'%20fill='%23b32a4d'/%3E%3Ccircle%20cx='31'%20cy='21'%20r='2.6'%20fill='%23b32a4d'/%3E%3Cpath%20d='M16%2034%20Q24%2026%2032%2034'%20fill='none'%20stroke='%23b32a4d'%20stroke-width='3.4'%20stroke-linecap='round'/%3E%3C/svg%3E");
}
/* ---- Synthwave (sombre) ---- */
[data-mode="synthwave"][data-theme="dark"]{
  color-scheme:dark;
  --bg:#12002b;
  --bg2:#1a0538;
  --panel-rgb:30,8,58;
  --panel:rgba(var(--panel-rgb),.64);
  --panel-solid:#1c0a3a;
  --fg:255,190,245;
  --panel2:rgba(var(--fg),.05);
  --line:rgba(var(--fg),.14);
  --line2:rgba(var(--fg),.28);
  --text:#f6ecff;
  --muted:#d0b0ec;
  --dim:#b48ad6;
  --accent:#ff4fdc;
  --accent2:#00e5ff;
  --accent3:#a58bff;
  --accent-rgb:255,79,220;
  --accent2-rgb:0,229,255;
  --accent3-rgb:165,139,255;
  --ok:#00ffa2;
  --warn:#ffb547;
  --err:#ff6b8a;
  --ok-rgb:0,255,162;
  --warn-rgb:255,181,71;
  --err-rgb:255,107,138;
  --on-accent:#1a0030;
  --on-err:#2a0010;
  --on-warn:#2a1600;
  --on-ok:#00210f;
  --warn-text:#ffd08a;
  --grad:linear-gradient(135deg,#ff2bd6 0%,#7c5cff 55%,#00e5ff 100%);
  --grad-btn:linear-gradient(135deg,#ff2bd6 0%,#7c5cff 55%,#00e5ff 100%);
  --on-grad:#12002b;
  --field:rgba(10,0,30,.45);
  --field2:rgba(10,0,30,.25);
  --scrim-rgb:10,0,30;
  --blob:.34;
  --blob1:#a3178f;
  --blob2:#3a1ab5;
  --blob3:#0a6a9a;
  --radius:14px;
  --rr:1;
  --sans:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --font-head:Orbitron,Rajdhani,Inter,ui-sans-serif,system-ui,sans-serif;
  --shadow:0 0 40px -12px rgba(255,43,214,.45), 0 10px 40px -10px rgba(0,0,0,.75);
  --glass-blur:18px;
  --glass-sat:150%;
  --spd:.9;
  --bw:1px;
  --code:#efe3ff;
  --caret:#00e5ff;
  --sel:rgba(255,43,214,.30);
  --tk-c:#a48ac6;
  --tk-s:#8dffd0;
  --tk-n:#ffb86b;
  --tk-k:#ff6ee6;
  --tk-t:#5ee9ff;
  --tk-f:#c4a8ff;
  --tk-p:#ff8ec0;
  --tk-o:#7be7ff;
  --tk-call:#ffe07a;
  --ext-h:#c4a8ff;
  --info:#7be7ff;
  --p0:#ff4fdc;
  --p1:#00e5ff;
  --p2:#ffb547;
  --p3:#00ffa2;
  --p4:#a58bff;
  --p5:#ffe07a;
  --p6:#ff8ec0;
  --p7:#7be7ff;
  --p8:#ff8a4c;
  --p9:#e0d0f5;
  --plot-bg:#1a0538;
  --plot-grid:rgba(var(--fg),.10);
  --plot-zero:rgba(var(--fg),.35);
  --plot-text:#f6ecff;
  --plot-text2:#c0a0e0;
  --d-find:rgba(var(--warn-rgb),.30);
  --d-cur:rgba(var(--accent-rgb),.55);
  --d-word:rgba(var(--accent2-rgb),.30);
  --d-br:rgba(var(--accent-rgb),.38);
  --logo1:#ff2bd6;
  --logo2:#00e5ff;
  --logo-bolt:#ffffff;
  --knob:#ffffff;
  --pin-gnd:#a48ac6;
  --sheen-rgb:255,255,255;
  --shade-rgb:0,0,0;
  --ink:#12002b;
  --paper:#ffffff;
  --dots:none;
  --deco-img:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%201600%20560'%3E%3Cdefs%3E%3ClinearGradient%20id='s'%20x1='0'%20y1='0'%20x2='0'%20y2='1'%3E%3Cstop%20offset='0'%20stop-color='%23ffe14d'/%3E%3Cstop%20offset='.5'%20stop-color='%23ff5fb0'/%3E%3Cstop%20offset='1'%20stop-color='%23b01cff'/%3E%3C/linearGradient%3E%3Cmask%20id='m'%3E%3Crect%20width='1600'%20height='400'%20fill='%23fff'/%3E%3Crect%20x='0'%20y='210'%20width='1600'%20height='4'%20fill='%23000'/%3E%3Crect%20x='0'%20y='236'%20width='1600'%20height='6'%20fill='%23000'/%3E%3Crect%20x='0'%20y='262'%20width='1600'%20height='8'%20fill='%23000'/%3E%3Crect%20x='0'%20y='288'%20width='1600'%20height='10'%20fill='%23000'/%3E%3Crect%20x='0'%20y='314'%20width='1600'%20height='12'%20fill='%23000'/%3E%3Crect%20x='0'%20y='340'%20width='1600'%20height='14'%20fill='%23000'/%3E%3C/mask%3E%3C/defs%3E%3Ccircle%20cx='800'%20cy='240'%20r='170'%20fill='url%28%23s%29'%20mask='url%28%23m%29'%20opacity='.85'/%3E%3Crect%20x='0'%20y='300'%20width='1600'%20height='260'%20fill='%2312002b'/%3E%3Cline%20x1='0'%20y1='300'%20x2='1600'%20y2='300'%20stroke='%2300e5ff'%20stroke-width='2'%20opacity='.9'/%3E%3Cline%20x1='800'%20y1='300'%20x2='-1600'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='-1450'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='-1300'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='-1150'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='-1000'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='-850'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='-700'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='-550'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='-400'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='-250'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='-100'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='50'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='200'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='350'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='500'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='650'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='800'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='950'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='1100'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='1250'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='1400'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='1550'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='1700'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='1850'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='2000'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='2150'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='2300'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='2450'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='2600'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='2750'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='2900'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='3050'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='800'%20y1='300'%20x2='3200'%20y2='560'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='0'%20y1='304.1'%20x2='1600'%20y2='304.1'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='0'%20y1='316.2'%20x2='1600'%20y2='316.2'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='0'%20y1='336.6'%20x2='1600'%20y2='336.6'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='0'%20y1='365.0'%20x2='1600'%20y2='365.0'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='0'%20y1='401.6'%20x2='1600'%20y2='401.6'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='0'%20y1='446.2'%20x2='1600'%20y2='446.2'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='0'%20y1='499.1'%20x2='1600'%20y2='499.1'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3Cline%20x1='0'%20y1='560.0'%20x2='1600'%20y2='560.0'%20stroke='%23ff2bd6'%20stroke-width='1.6'%20opacity='.55'/%3E%3C/svg%3E");
  --deco-size:100% auto;
  --deco-pos:center bottom;
  --deco-rep:no-repeat;
  --deco-op:.55;
  --overlay:none;
  --burst1:#ff2bd6;
  --burst2:#00e5ff;
  --burst3:#7c5cff;
  --burst4:#00ffa2;
  --burst5:#ffffff;
  --burst6:#ffe07a;
  --plat0:#ff4fdc;
  --plat1:#ff6b8a;
  --plat2:#ffb547;
  --plat3:#ff8ec0;
  --plat4:#00e5ff;
  --plat5:#a58bff;
  --plat6:#00ffa2;
  --plat-x:#b48ad6;
  --art-welcome:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20200%20120'%3E%3Cdefs%3E%3ClinearGradient%20id='s'%20x1='0'%20y1='0'%20x2='0'%20y2='1'%3E%3Cstop%20offset='0'%20stop-color='%23ffe14d'/%3E%3Cstop%20offset='.55'%20stop-color='%23ff5fb0'/%3E%3Cstop%20offset='1'%20stop-color='%23b01cff'/%3E%3C/linearGradient%3E%3Cmask%20id='m'%3E%3Crect%20width='200'%20height='90'%20fill='%23fff'/%3E%3Crect%20y='52'%20width='200'%20height='3'%20fill='%23000'/%3E%3Crect%20y='62'%20width='200'%20height='4'%20fill='%23000'/%3E%3Crect%20y='73'%20width='200'%20height='5'%20fill='%23000'/%3E%3C/mask%3E%3C/defs%3E%3Ccircle%20cx='100'%20cy='60'%20r='48'%20fill='url%28%23s%29'%20mask='url%28%23m%29'/%3E%3Cline%20x1='0'%20y1='86'%20x2='200'%20y2='86'%20stroke='%2300e5ff'%20stroke-width='2'/%3E%3Cline%20x1='100'%20y1='86'%20x2='-116'%20y2='120'%20stroke='%23ff2bd6'%20stroke-width='1.4'/%3E%3Cline%20x1='100'%20y1='86'%20x2='-80'%20y2='120'%20stroke='%23ff2bd6'%20stroke-width='1.4'/%3E%3Cline%20x1='100'%20y1='86'%20x2='-44'%20y2='120'%20stroke='%23ff2bd6'%20stroke-width='1.4'/%3E%3Cline%20x1='100'%20y1='86'%20x2='-8'%20y2='120'%20stroke='%23ff2bd6'%20stroke-width='1.4'/%3E%3Cline%20x1='100'%20y1='86'%20x2='28'%20y2='120'%20stroke='%23ff2bd6'%20stroke-width='1.4'/%3E%3Cline%20x1='100'%20y1='86'%20x2='64'%20y2='120'%20stroke='%23ff2bd6'%20stroke-width='1.4'/%3E%3Cline%20x1='100'%20y1='86'%20x2='100'%20y2='120'%20stroke='%23ff2bd6'%20stroke-width='1.4'/%3E%3Cline%20x1='100'%20y1='86'%20x2='136'%20y2='120'%20stroke='%23ff2bd6'%20stroke-width='1.4'/%3E%3Cline%20x1='100'%20y1='86'%20x2='172'%20y2='120'%20stroke='%23ff2bd6'%20stroke-width='1.4'/%3E%3Cline%20x1='100'%20y1='86'%20x2='208'%20y2='120'%20stroke='%23ff2bd6'%20stroke-width='1.4'/%3E%3Cline%20x1='100'%20y1='86'%20x2='244'%20y2='120'%20stroke='%23ff2bd6'%20stroke-width='1.4'/%3E%3Cline%20x1='100'%20y1='86'%20x2='280'%20y2='120'%20stroke='%23ff2bd6'%20stroke-width='1.4'/%3E%3Cline%20x1='100'%20y1='86'%20x2='316'%20y2='120'%20stroke='%23ff2bd6'%20stroke-width='1.4'/%3E%3Cline%20x1='0'%20y1='96'%20x2='200'%20y2='96'%20stroke='%23ff2bd6'%20stroke-width='1.2'/%3E%3Cline%20x1='0'%20y1='108'%20x2='200'%20y2='108'%20stroke='%23ff2bd6'%20stroke-width='1.2'/%3E%3C/svg%3E");
  --art-empty:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20164%20110'%3E%3Crect%20x='24'%20y='36'%20width='26'%20height='30'%20rx='3'%20fill='%232a1058'%20stroke='%23ff4fdc'%20stroke-width='4'/%3E%3Crect%20x='14'%20y='14'%20width='136'%20height='82'%20rx='10'%20fill='%231c0a3a'%20stroke='%23ff4fdc'%20stroke-width='4'/%3E%3Crect%20x='92'%20y='34'%20width='38'%20height='38'%20rx='4'%20fill='%232a1058'%20stroke='%23ff4fdc'%20stroke-width='3'/%3E%3Crect%20x='34'%20y='6'%20width='6'%20height='9'%20fill='%23ff4fdc'/%3E%3Crect%20x='34'%20y='95'%20width='6'%20height='9'%20fill='%23ff4fdc'/%3E%3Crect%20x='45'%20y='6'%20width='6'%20height='9'%20fill='%23ff4fdc'/%3E%3Crect%20x='45'%20y='95'%20width='6'%20height='9'%20fill='%23ff4fdc'/%3E%3Crect%20x='56'%20y='6'%20width='6'%20height='9'%20fill='%23ff4fdc'/%3E%3Crect%20x='56'%20y='95'%20width='6'%20height='9'%20fill='%23ff4fdc'/%3E%3Crect%20x='67'%20y='6'%20width='6'%20height='9'%20fill='%23ff4fdc'/%3E%3Crect%20x='67'%20y='95'%20width='6'%20height='9'%20fill='%23ff4fdc'/%3E%3Crect%20x='78'%20y='6'%20width='6'%20height='9'%20fill='%23ff4fdc'/%3E%3Crect%20x='78'%20y='95'%20width='6'%20height='9'%20fill='%23ff4fdc'/%3E%3Crect%20x='89'%20y='6'%20width='6'%20height='9'%20fill='%23ff4fdc'/%3E%3Crect%20x='89'%20y='95'%20width='6'%20height='9'%20fill='%23ff4fdc'/%3E%3Crect%20x='100'%20y='6'%20width='6'%20height='9'%20fill='%23ff4fdc'/%3E%3Crect%20x='100'%20y='95'%20width='6'%20height='9'%20fill='%23ff4fdc'/%3E%3Crect%20x='111'%20y='6'%20width='6'%20height='9'%20fill='%23ff4fdc'/%3E%3Crect%20x='111'%20y='95'%20width='6'%20height='9'%20fill='%23ff4fdc'/%3E%3Ccircle%20cx='66'%20cy='30'%20r='5'%20fill='%2300e5ff'/%3E%3Ccircle%20cx='60'%20cy='76'%20r='7'%20fill='none'%20stroke='%2300e5ff'%20stroke-width='3'/%3E%3C/svg%3E");
  --art-ok:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Ccircle%20cx='24'%20cy='24'%20r='19'%20fill='none'%20stroke='%2300ffa2'%20stroke-width='4'/%3E%3Cpath%20d='M14%2025%20l7%207%20l14%20-15'%20fill='none'%20stroke='%2300ffa2'%20stroke-width='5'%20stroke-linecap='round'%20stroke-linejoin='round'/%3E%3C/svg%3E");
  --art-err:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Ccircle%20cx='24'%20cy='24'%20r='19'%20fill='none'%20stroke='%23ff6b8a'%20stroke-width='4'/%3E%3Cpath%20d='M16%2016%20L32%2032%20M32%2016%20L16%2032'%20fill='none'%20stroke='%23ff6b8a'%20stroke-width='5'%20stroke-linecap='round'/%3E%3C/svg%3E");
}
/* ---- Papier (clair) ---- */
[data-mode="papier"][data-theme="light"]{
  color-scheme:light;
  --bg:#f6f1e6;
  --bg2:#fbf8f1;
  --panel-rgb:255,253,247;
  --panel:rgba(var(--panel-rgb),1);
  --panel-solid:#fffdf7;
  --fg:31,42,85;
  --panel2:rgba(var(--fg),.035);
  --line:rgba(var(--fg),.20);
  --line2:rgba(var(--fg),.34);
  --text:#1d2a5e;
  --muted:#454a63;
  --dim:#575c74;
  --accent:#1f3a8a;
  --accent2:#b91c1c;
  --accent3:#09628d;
  --accent-rgb:31,58,138;
  --accent2-rgb:185,28,28;
  --accent3-rgb:9,98,141;
  --ok:#146c33;
  --warn:#8f4a06;
  --err:#b01818;
  --ok-rgb:20,108,51;
  --warn-rgb:143,74,6;
  --err-rgb:176,24,24;
  --on-accent:#ffffff;
  --on-err:#ffffff;
  --on-warn:#ffffff;
  --on-ok:#ffffff;
  --warn-text:#6b3600;
  --grad:linear-gradient(135deg,#1f3a8a,#1f3a8a);
  --grad-btn:linear-gradient(#1f3a8a,#1f3a8a);
  --on-grad:#ffffff;
  --field:rgba(255,255,255,.9);
  --field2:rgba(31,42,85,.04);
  --scrim-rgb:31,42,85;
  --blob:0;
  --blob1:#000;
  --blob2:#000;
  --blob3:#000;
  --radius:3px;
  --rr:.3;
  --sans:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --font-head:Caveat,"Kalam","Comic Sans MS",cursive;
  --shadow:1px 2px 0 rgba(31,42,85,.12);
  --glass-blur:0px;
  --glass-sat:100%;
  --spd:1;
  --bw:1px;
  --code:#1d2a5e;
  --caret:#b91c1c;
  --sel:rgba(31,58,138,.16);
  --tk-c:#5f6379;
  --tk-s:#146c33;
  --tk-n:#a34205;
  --tk-k:#8a1c74;
  --tk-t:#1f3a8a;
  --tk-f:#09628d;
  --tk-p:#b91c1c;
  --tk-o:#3f5566;
  --tk-call:#7a5a00;
  --ext-h:#8a1c74;
  --info:#1f3a8a;
  --p0:#1f3a8a;
  --p1:#b91c1c;
  --p2:#8f4a06;
  --p3:#146c33;
  --p4:#09628d;
  --p5:#8a1c74;
  --p6:#6b5a00;
  --p7:#3f5566;
  --p8:#c2410c;
  --p9:#575c74;
  --plot-bg:#fffdf7;
  --plot-grid:rgba(var(--fg),.12);
  --plot-zero:rgba(var(--fg),.40);
  --plot-text:#1d2a5e;
  --plot-text2:#575c74;
  --d-find:rgba(var(--warn-rgb),.30);
  --d-cur:rgba(var(--accent-rgb),.55);
  --d-word:rgba(var(--accent2-rgb),.30);
  --d-br:rgba(var(--accent-rgb),.38);
  --logo1:#1f3a8a;
  --logo2:#b91c1c;
  --logo-bolt:#fffdf7;
  --knob:#fffdf7;
  --pin-gnd:#6b6f86;
  --sheen-rgb:255,255,255;
  --shade-rgb:31,42,85;
  --ink:#1d2a5e;
  --paper:#fffdf7;
  --dots:none;
  --deco-img:none;
  --deco-size:auto;
  --deco-pos:0 0;
  --deco-rep:no-repeat;
  --deco-op:1;
  --overlay:none;
  --burst1:#1f3a8a;
  --burst2:#b91c1c;
  --burst3:#146c33;
  --burst4:#8f4a06;
  --burst5:#09628d;
  --burst6:#1d2a5e;
  --plat0:#1f3a8a;
  --plat1:#b01818;
  --plat2:#8f4a06;
  --plat3:#b91c1c;
  --plat4:#09628d;
  --plat5:#8a1c74;
  --plat6:#146c33;
  --plat-x:#575c74;
  --art-welcome:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20164%20110'%3E%3Crect%20x='24'%20y='36'%20width='26'%20height='30'%20rx='3'%20fill='none'%20stroke='%231d2a5e'%20stroke-width='3'/%3E%3Crect%20x='14'%20y='14'%20width='136'%20height='82'%20rx='10'%20fill='none'%20stroke='%231d2a5e'%20stroke-width='3'/%3E%3Crect%20x='92'%20y='34'%20width='38'%20height='38'%20rx='4'%20fill='none'%20stroke='%231d2a5e'%20stroke-width='2'/%3E%3Crect%20x='34'%20y='6'%20width='6'%20height='9'%20fill='%231d2a5e'/%3E%3Crect%20x='34'%20y='95'%20width='6'%20height='9'%20fill='%231d2a5e'/%3E%3Crect%20x='45'%20y='6'%20width='6'%20height='9'%20fill='%231d2a5e'/%3E%3Crect%20x='45'%20y='95'%20width='6'%20height='9'%20fill='%231d2a5e'/%3E%3Crect%20x='56'%20y='6'%20width='6'%20height='9'%20fill='%231d2a5e'/%3E%3Crect%20x='56'%20y='95'%20width='6'%20height='9'%20fill='%231d2a5e'/%3E%3Crect%20x='67'%20y='6'%20width='6'%20height='9'%20fill='%231d2a5e'/%3E%3Crect%20x='67'%20y='95'%20width='6'%20height='9'%20fill='%231d2a5e'/%3E%3Crect%20x='78'%20y='6'%20width='6'%20height='9'%20fill='%231d2a5e'/%3E%3Crect%20x='78'%20y='95'%20width='6'%20height='9'%20fill='%231d2a5e'/%3E%3Crect%20x='89'%20y='6'%20width='6'%20height='9'%20fill='%231d2a5e'/%3E%3Crect%20x='89'%20y='95'%20width='6'%20height='9'%20fill='%231d2a5e'/%3E%3Crect%20x='100'%20y='6'%20width='6'%20height='9'%20fill='%231d2a5e'/%3E%3Crect%20x='100'%20y='95'%20width='6'%20height='9'%20fill='%231d2a5e'/%3E%3Crect%20x='111'%20y='6'%20width='6'%20height='9'%20fill='%231d2a5e'/%3E%3Crect%20x='111'%20y='95'%20width='6'%20height='9'%20fill='%231d2a5e'/%3E%3Ccircle%20cx='66'%20cy='30'%20r='5'%20fill='%23b91c1c'/%3E%3Ccircle%20cx='60'%20cy='76'%20r='7'%20fill='none'%20stroke='%23b91c1c'%20stroke-width='2'/%3E%3Cpath%20d='M146%207%20L147.96%2012.04%20L153%2014%20L147.96%2015.96%20L146%2021%20L144.04%2015.96%20L139%2014%20L144.04%2012.04Z'%20fill='%23b91c1c'%20opacity='1'/%3E%3Cpath%20d='M8%20104%20q40%208%2080%200%20t70%202'%20fill='none'%20stroke='%231d2a5e'%20stroke-width='2'%20stroke-dasharray='4%204'/%3E%3C/svg%3E");
  --art-empty:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20164%20110'%3E%3Crect%20x='24'%20y='36'%20width='26'%20height='30'%20rx='3'%20fill='none'%20stroke='%23575c74'%20stroke-width='3'/%3E%3Crect%20x='14'%20y='14'%20width='136'%20height='82'%20rx='10'%20fill='none'%20stroke='%23575c74'%20stroke-width='3'/%3E%3Crect%20x='92'%20y='34'%20width='38'%20height='38'%20rx='4'%20fill='none'%20stroke='%23575c74'%20stroke-width='2'/%3E%3Crect%20x='34'%20y='6'%20width='6'%20height='9'%20fill='%23575c74'/%3E%3Crect%20x='34'%20y='95'%20width='6'%20height='9'%20fill='%23575c74'/%3E%3Crect%20x='45'%20y='6'%20width='6'%20height='9'%20fill='%23575c74'/%3E%3Crect%20x='45'%20y='95'%20width='6'%20height='9'%20fill='%23575c74'/%3E%3Crect%20x='56'%20y='6'%20width='6'%20height='9'%20fill='%23575c74'/%3E%3Crect%20x='56'%20y='95'%20width='6'%20height='9'%20fill='%23575c74'/%3E%3Crect%20x='67'%20y='6'%20width='6'%20height='9'%20fill='%23575c74'/%3E%3Crect%20x='67'%20y='95'%20width='6'%20height='9'%20fill='%23575c74'/%3E%3Crect%20x='78'%20y='6'%20width='6'%20height='9'%20fill='%23575c74'/%3E%3Crect%20x='78'%20y='95'%20width='6'%20height='9'%20fill='%23575c74'/%3E%3Crect%20x='89'%20y='6'%20width='6'%20height='9'%20fill='%23575c74'/%3E%3Crect%20x='89'%20y='95'%20width='6'%20height='9'%20fill='%23575c74'/%3E%3Crect%20x='100'%20y='6'%20width='6'%20height='9'%20fill='%23575c74'/%3E%3Crect%20x='100'%20y='95'%20width='6'%20height='9'%20fill='%23575c74'/%3E%3Crect%20x='111'%20y='6'%20width='6'%20height='9'%20fill='%23575c74'/%3E%3Crect%20x='111'%20y='95'%20width='6'%20height='9'%20fill='%23575c74'/%3E%3Ccircle%20cx='66'%20cy='30'%20r='5'%20fill='%23b91c1c'/%3E%3Ccircle%20cx='60'%20cy='76'%20r='7'%20fill='none'%20stroke='%23b91c1c'%20stroke-width='2'/%3E%3C/svg%3E");
  --art-ok:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Ccircle%20cx='24'%20cy='24'%20r='19'%20fill='none'%20stroke='%23146c33'%20stroke-width='4'/%3E%3Cpath%20d='M14%2025%20l7%207%20l14%20-15'%20fill='none'%20stroke='%23146c33'%20stroke-width='5'%20stroke-linecap='round'%20stroke-linejoin='round'/%3E%3C/svg%3E");
  --art-err:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Ccircle%20cx='24'%20cy='24'%20r='19'%20fill='none'%20stroke='%23b01818'%20stroke-width='4'/%3E%3Cpath%20d='M16%2016%20L32%2032%20M32%2016%20L16%2032'%20fill='none'%20stroke='%23b01818'%20stroke-width='5'%20stroke-linecap='round'/%3E%3C/svg%3E");
}
/* ---- Contraste élevé (sombre) ---- */
[data-mode="contraste"][data-theme="dark"]{
  color-scheme:dark;
  --bg:#000000;
  --bg2:#000000;
  --panel-rgb:0,0,0;
  --panel:rgba(var(--panel-rgb),1);
  --panel-solid:#000000;
  --fg:255,255,255;
  --panel2:rgba(var(--fg),.10);
  --line:rgba(var(--fg),1);
  --line2:rgba(var(--fg),1);
  --text:#ffffff;
  --muted:#ececec;
  --dim:#dcdcdc;
  --accent:#ffd400;
  --accent2:#7fdcff;
  --accent3:#a8c8ff;
  --accent-rgb:255,212,0;
  --accent2-rgb:127,220,255;
  --accent3-rgb:168,200,255;
  --ok:#5dff8a;
  --warn:#ffd400;
  --err:#ff8a8a;
  --ok-rgb:93,255,138;
  --warn-rgb:255,212,0;
  --err-rgb:255,138,138;
  --on-accent:#000000;
  --on-err:#000000;
  --on-warn:#000000;
  --on-ok:#000000;
  --warn-text:#ffe680;
  --grad:linear-gradient(#ffd400,#ffd400);
  --grad-btn:linear-gradient(#ffd400,#ffd400);
  --on-grad:#000000;
  --field:rgba(0,0,0,1);
  --field2:rgba(255,255,255,.08);
  --scrim-rgb:0,0,0;
  --blob:0;
  --blob1:#000;
  --blob2:#000;
  --blob3:#000;
  --radius:4px;
  --rr:.3;
  --sans:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --font-head:var(--sans);
  --shadow:none;
  --glass-blur:0px;
  --glass-sat:100%;
  --spd:1;
  --bw:2px;
  --code:#ffffff;
  --caret:#ffd400;
  --sel:rgba(255,212,0,.40);
  --tk-c:#cfcfcf;
  --tk-s:#8dff9f;
  --tk-n:#ffc27a;
  --tk-k:#ff9cf0;
  --tk-t:#8fd4ff;
  --tk-f:#ffe680;
  --tk-p:#ffa0a0;
  --tk-o:#9be7ff;
  --tk-call:#ffe680;
  --ext-h:#ff9cf0;
  --info:#9be7ff;
  --p0:#ffd400;
  --p1:#7fdcff;
  --p2:#5dff8a;
  --p3:#ff8a8a;
  --p4:#ff9cf0;
  --p5:#ffc27a;
  --p6:#a8c8ff;
  --p7:#ffffff;
  --p8:#c4ff6a;
  --p9:#dcdcdc;
  --plot-bg:#000000;
  --plot-grid:rgba(var(--fg),.28);
  --plot-zero:rgba(var(--fg),.7);
  --plot-text:#ffffff;
  --plot-text2:#dcdcdc;
  --d-find:rgba(var(--warn-rgb),.30);
  --d-cur:rgba(var(--accent-rgb),.55);
  --d-word:rgba(var(--accent2-rgb),.30);
  --d-br:rgba(var(--accent-rgb),.38);
  --logo1:#ffd400;
  --logo2:#ffffff;
  --logo-bolt:#000000;
  --knob:#ffffff;
  --pin-gnd:#dcdcdc;
  --sheen-rgb:255,255,255;
  --shade-rgb:0,0,0;
  --ink:#000000;
  --paper:#ffffff;
  --dots:none;
  --deco-img:none;
  --deco-size:auto;
  --deco-pos:0 0;
  --deco-rep:no-repeat;
  --deco-op:1;
  --overlay:none;
  --burst1:#ffd400;
  --burst2:#7fdcff;
  --burst3:#5dff8a;
  --burst4:#ffffff;
  --burst5:#ff9cf0;
  --burst6:#ffc27a;
  --plat0:#ffd400;
  --plat1:#ff8a8a;
  --plat2:#ffc27a;
  --plat3:#ff9cf0;
  --plat4:#7fdcff;
  --plat5:#a8c8ff;
  --plat6:#5dff8a;
  --plat-x:#dcdcdc;
  --art-welcome:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20164%20110'%3E%3Crect%20x='24'%20y='36'%20width='26'%20height='30'%20rx='3'%20fill='%23000000'%20stroke='%23ffffff'%20stroke-width='5'/%3E%3Crect%20x='14'%20y='14'%20width='136'%20height='82'%20rx='10'%20fill='%23000000'%20stroke='%23ffffff'%20stroke-width='5'/%3E%3Crect%20x='92'%20y='34'%20width='38'%20height='38'%20rx='4'%20fill='%23000000'%20stroke='%23ffffff'%20stroke-width='4'/%3E%3Crect%20x='34'%20y='6'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='34'%20y='95'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='45'%20y='6'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='45'%20y='95'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='56'%20y='6'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='56'%20y='95'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='67'%20y='6'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='67'%20y='95'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='78'%20y='6'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='78'%20y='95'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='89'%20y='6'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='89'%20y='95'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='100'%20y='6'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='100'%20y='95'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='111'%20y='6'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='111'%20y='95'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Ccircle%20cx='66'%20cy='30'%20r='5'%20fill='%23ffd400'/%3E%3Ccircle%20cx='60'%20cy='76'%20r='7'%20fill='none'%20stroke='%23ffd400'%20stroke-width='4'/%3E%3C/svg%3E");
  --art-empty:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20164%20110'%3E%3Crect%20x='24'%20y='36'%20width='26'%20height='30'%20rx='3'%20fill='%23000000'%20stroke='%23ffffff'%20stroke-width='6'/%3E%3Crect%20x='14'%20y='14'%20width='136'%20height='82'%20rx='10'%20fill='%23000000'%20stroke='%23ffffff'%20stroke-width='6'/%3E%3Crect%20x='92'%20y='34'%20width='38'%20height='38'%20rx='4'%20fill='%23000000'%20stroke='%23ffffff'%20stroke-width='5'/%3E%3Crect%20x='34'%20y='6'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='34'%20y='95'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='45'%20y='6'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='45'%20y='95'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='56'%20y='6'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='56'%20y='95'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='67'%20y='6'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='67'%20y='95'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='78'%20y='6'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='78'%20y='95'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='89'%20y='6'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='89'%20y='95'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='100'%20y='6'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='100'%20y='95'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='111'%20y='6'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Crect%20x='111'%20y='95'%20width='6'%20height='9'%20fill='%23ffffff'/%3E%3Ccircle%20cx='66'%20cy='30'%20r='5'%20fill='%23ffd400'/%3E%3Ccircle%20cx='60'%20cy='76'%20r='7'%20fill='none'%20stroke='%23ffd400'%20stroke-width='5'/%3E%3C/svg%3E");
  --art-ok:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Ccircle%20cx='24'%20cy='24'%20r='19'%20fill='none'%20stroke='%235dff8a'%20stroke-width='4'/%3E%3Cpath%20d='M14%2025%20l7%207%20l14%20-15'%20fill='none'%20stroke='%235dff8a'%20stroke-width='5'%20stroke-linecap='round'%20stroke-linejoin='round'/%3E%3C/svg%3E");
  --art-err:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Ccircle%20cx='24'%20cy='24'%20r='19'%20fill='none'%20stroke='%23ff8a8a'%20stroke-width='4'/%3E%3Cpath%20d='M16%2016%20L32%2032%20M32%2016%20L16%2032'%20fill='none'%20stroke='%23ff8a8a'%20stroke-width='5'%20stroke-linecap='round'/%3E%3C/svg%3E");
}
/* ---- Contraste élevé (clair) ---- */
[data-mode="contraste"][data-theme="light"]{
  color-scheme:light;
  --bg:#ffffff;
  --bg2:#ffffff;
  --panel-rgb:255,255,255;
  --panel:rgba(var(--panel-rgb),1);
  --panel-solid:#ffffff;
  --fg:0,0,0;
  --panel2:rgba(var(--fg),.07);
  --line:rgba(var(--fg),1);
  --line2:rgba(var(--fg),1);
  --text:#000000;
  --muted:#262626;
  --dim:#333333;
  --accent:#0a2bb8;
  --accent2:#5a0a96;
  --accent3:#003f80;
  --accent-rgb:10,43,184;
  --accent2-rgb:90,10,150;
  --accent3-rgb:0,63,128;
  --ok:#004d19;
  --warn:#6b3a00;
  --err:#8a0014;
  --ok-rgb:0,77,25;
  --warn-rgb:107,58,0;
  --err-rgb:138,0,20;
  --on-accent:#ffffff;
  --on-err:#ffffff;
  --on-warn:#ffffff;
  --on-ok:#ffffff;
  --warn-text:#4a2800;
  --grad:linear-gradient(#0a2bb8,#0a2bb8);
  --grad-btn:linear-gradient(#0a2bb8,#0a2bb8);
  --on-grad:#ffffff;
  --field:rgba(255,255,255,1);
  --field2:rgba(0,0,0,.06);
  --scrim-rgb:0,0,0;
  --blob:0;
  --blob1:#fff;
  --blob2:#fff;
  --blob3:#fff;
  --radius:4px;
  --rr:.3;
  --sans:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --font-head:var(--sans);
  --shadow:none;
  --glass-blur:0px;
  --glass-sat:100%;
  --spd:1;
  --bw:2px;
  --code:#000000;
  --caret:#0a2bb8;
  --sel:rgba(10,43,184,.25);
  --tk-c:#404040;
  --tk-s:#004d16;
  --tk-n:#7a3400;
  --tk-k:#7a0a6e;
  --tk-t:#0a2f9a;
  --tk-f:#4a0a8a;
  --tk-p:#8a0014;
  --tk-o:#004a5c;
  --tk-call:#5c3a00;
  --ext-h:#5a0a96;
  --info:#0a2bb8;
  --p0:#0a2bb8;
  --p1:#8a0014;
  --p2:#6b3a00;
  --p3:#004d19;
  --p4:#5a0a96;
  --p5:#003f80;
  --p6:#4a2800;
  --p7:#333333;
  --p8:#8a1a00;
  --p9:#000000;
  --plot-bg:#ffffff;
  --plot-grid:rgba(var(--fg),.28);
  --plot-zero:rgba(var(--fg),.7);
  --plot-text:#000000;
  --plot-text2:#333333;
  --d-find:rgba(var(--warn-rgb),.30);
  --d-cur:rgba(var(--accent-rgb),.55);
  --d-word:rgba(var(--accent2-rgb),.30);
  --d-br:rgba(var(--accent-rgb),.38);
  --logo1:#0a2bb8;
  --logo2:#000000;
  --logo-bolt:#ffffff;
  --knob:#ffffff;
  --pin-gnd:#333333;
  --sheen-rgb:255,255,255;
  --shade-rgb:0,0,0;
  --ink:#000000;
  --paper:#ffffff;
  --dots:none;
  --deco-img:none;
  --deco-size:auto;
  --deco-pos:0 0;
  --deco-rep:no-repeat;
  --deco-op:1;
  --overlay:none;
  --burst1:#0a2bb8;
  --burst2:#8a0014;
  --burst3:#004d19;
  --burst4:#5a0a96;
  --burst5:#000000;
  --burst6:#6b3a00;
  --plat0:#0a2bb8;
  --plat1:#8a0014;
  --plat2:#6b3a00;
  --plat3:#5a0a96;
  --plat4:#003f80;
  --plat5:#4a2800;
  --plat6:#004d19;
  --plat-x:#333333;
  --art-welcome:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20164%20110'%3E%3Crect%20x='24'%20y='36'%20width='26'%20height='30'%20rx='3'%20fill='%23ffffff'%20stroke='%23000000'%20stroke-width='5'/%3E%3Crect%20x='14'%20y='14'%20width='136'%20height='82'%20rx='10'%20fill='%23ffffff'%20stroke='%23000000'%20stroke-width='5'/%3E%3Crect%20x='92'%20y='34'%20width='38'%20height='38'%20rx='4'%20fill='%23ffffff'%20stroke='%23000000'%20stroke-width='4'/%3E%3Crect%20x='34'%20y='6'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='34'%20y='95'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='45'%20y='6'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='45'%20y='95'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='56'%20y='6'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='56'%20y='95'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='67'%20y='6'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='67'%20y='95'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='78'%20y='6'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='78'%20y='95'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='89'%20y='6'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='89'%20y='95'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='100'%20y='6'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='100'%20y='95'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='111'%20y='6'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='111'%20y='95'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Ccircle%20cx='66'%20cy='30'%20r='5'%20fill='%230a2bb8'/%3E%3Ccircle%20cx='60'%20cy='76'%20r='7'%20fill='none'%20stroke='%230a2bb8'%20stroke-width='4'/%3E%3C/svg%3E");
  --art-empty:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20164%20110'%3E%3Crect%20x='24'%20y='36'%20width='26'%20height='30'%20rx='3'%20fill='%23ffffff'%20stroke='%23000000'%20stroke-width='6'/%3E%3Crect%20x='14'%20y='14'%20width='136'%20height='82'%20rx='10'%20fill='%23ffffff'%20stroke='%23000000'%20stroke-width='6'/%3E%3Crect%20x='92'%20y='34'%20width='38'%20height='38'%20rx='4'%20fill='%23ffffff'%20stroke='%23000000'%20stroke-width='5'/%3E%3Crect%20x='34'%20y='6'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='34'%20y='95'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='45'%20y='6'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='45'%20y='95'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='56'%20y='6'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='56'%20y='95'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='67'%20y='6'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='67'%20y='95'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='78'%20y='6'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='78'%20y='95'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='89'%20y='6'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='89'%20y='95'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='100'%20y='6'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='100'%20y='95'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='111'%20y='6'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Crect%20x='111'%20y='95'%20width='6'%20height='9'%20fill='%23000000'/%3E%3Ccircle%20cx='66'%20cy='30'%20r='5'%20fill='%230a2bb8'/%3E%3Ccircle%20cx='60'%20cy='76'%20r='7'%20fill='none'%20stroke='%230a2bb8'%20stroke-width='5'/%3E%3C/svg%3E");
  --art-ok:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Ccircle%20cx='24'%20cy='24'%20r='19'%20fill='none'%20stroke='%23004d19'%20stroke-width='4'/%3E%3Cpath%20d='M14%2025%20l7%207%20l14%20-15'%20fill='none'%20stroke='%23004d19'%20stroke-width='5'%20stroke-linecap='round'%20stroke-linejoin='round'/%3E%3C/svg%3E");
  --art-err:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2048%2048'%3E%3Ccircle%20cx='24'%20cy='24'%20r='19'%20fill='none'%20stroke='%238a0014'%20stroke-width='4'/%3E%3Cpath%20d='M16%2016%20L32%2032%20M32%2016%20L16%2032'%20fill='none'%20stroke='%238a0014'%20stroke-width='5'%20stroke-linecap='round'/%3E%3C/svg%3E");
}

*{box-sizing:border-box}
html,body{height:100%;margin:0}
body{background:var(--bg);color:var(--text);font:13.5px/1.45 var(--sans);overflow:hidden;-webkit-font-smoothing:antialiased}
button,input,select,textarea{font:inherit;color:inherit}
::-webkit-scrollbar{width:10px;height:10px}
::-webkit-scrollbar-thumb{background:rgba(var(--fg),.08);border-radius:calc(10px*var(--rr));border:2px solid transparent;background-clip:padding-box}
::-webkit-scrollbar-thumb:hover{background-color:rgba(var(--fg),.16)}
::-webkit-scrollbar-corner{background:transparent}
svg.i{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;flex:none}

/* ---------- fond animé ---------- */
.bg{position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden}
.bg i{position:absolute;border-radius:50%;filter:blur(90px);opacity:var(--blob);animation:float calc(26s*var(--spd)) ease-in-out infinite alternate}
.bg i:nth-child(1){width:560px;height:560px;background:var(--blob1);left:-160px;top:-180px}
.bg i:nth-child(2){width:620px;height:620px;background:var(--blob2);right:-220px;bottom:-260px;animation-delay:-9s}
.bg i:nth-child(3){width:380px;height:380px;background:var(--blob3);left:45%;top:35%;opacity:calc(var(--blob)*.5);animation-delay:-16s}
.bg::after{content:"";position:absolute;inset:0;background-image:radial-gradient(rgba(var(--fg),.045) 1px,transparent 1px);background-size:22px 22px;mask-image:radial-gradient(ellipse at center,#000 30%,transparent 80%)}
@keyframes float{to{transform:translate(80px,60px) scale(1.12)}}

/* ---------- structure ---------- */
.app{position:relative;z-index:1;display:grid;grid-template-columns:252px minmax(0,1fr);height:100vh;gap:10px;padding:10px}
.glass{background:var(--panel);backdrop-filter:blur(var(--glass-blur)) saturate(var(--glass-sat));-webkit-backdrop-filter:blur(var(--glass-blur)) saturate(var(--glass-sat));border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow)}
.sidebar{display:flex;flex-direction:column;min-height:0;overflow:hidden}
.main{display:grid;grid-template-columns:minmax(0,1fr);grid-template-rows:58px minmax(0,1fr) 6px var(--panel-h) 26px;min-width:0;min-height:0;gap:0}
.content{display:grid;grid-template-columns:minmax(0,1fr) 292px;gap:10px;min-height:0;margin-top:10px}

/* ---------- barre latérale ---------- */
.brand{display:flex;align-items:center;gap:11px;padding:18px 18px 14px}
.logo{width:34px;height:34px;position:relative;flex:none}
.logo svg{width:100%;height:100%;filter:drop-shadow(0 4px 14px rgba(var(--accent-rgb),.45))}
.logo::after{content:"";position:absolute;inset:-6px;border-radius:50%;background:conic-gradient(from 0deg,transparent,rgba(var(--accent-rgb),.35),transparent 40%);animation:spin calc(5s*var(--spd)) linear infinite;mask:radial-gradient(circle,transparent 58%,#000 60%)}
@keyframes spin{to{transform:rotate(360deg)}}
.brand b{font-size:19px;font-weight:800;letter-spacing:-.02em;background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.brand small{display:block;color:var(--muted);font-size:11px;margin-top:-2px}
.side-sec{padding:6px 14px;display:flex;align-items:center;justify-content:space-between;color:var(--muted);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.08em}
.search{margin:4px 12px 8px;position:relative}
.search input{width:100%;background:var(--field);border:1px solid var(--line);border-radius:calc(10px*var(--rr));padding:8px 10px 8px 32px;outline:none;transition:.2s}
.search input:focus{border-color:rgba(var(--accent-rgb),.5);box-shadow:0 0 0 3px rgba(var(--accent-rgb),.12)}
.search svg{position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--dim)}
.projects{list-style:none;margin:0;padding:2px 8px 8px;overflow:auto;flex:1}
.projects li{display:flex;align-items:center;gap:6px;padding:8px 10px;border-radius:calc(10px*var(--rr));cursor:pointer;transition:background .15s,transform .15s;position:relative}
.projects li:hover{background:var(--panel2)}
.projects li.active{background:linear-gradient(90deg,rgba(var(--accent-rgb),.16),rgba(var(--accent2-rgb),.08))}
.projects li.active::before{content:"";position:absolute;left:0;top:8px;bottom:8px;width:3px;border-radius:calc(3px*var(--rr));background:var(--grad)}
.projects .pi{width:30px;height:30px;flex:none;border-radius:calc(9px*var(--rr));display:grid;place-items:center;background:rgba(var(--fg),.05);color:var(--accent);flex:none;font-weight:700;font-size:12px}
.projects li.active .pi{background:var(--grad-btn);color:var(--on-grad)}
.projects .pn{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.projects .pf{font-size:11px;color:var(--dim);font-family:var(--mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.projects .empty{color:var(--dim);padding:14px;text-align:center;cursor:default}
.projects .grp{cursor:default;padding:8px 10px 2px;font-size:10.5px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--dim)}
.projects .grp:hover{background:none}
.projects li>div:nth-child(2){flex:1}
.pin{background:none;border:0;padding:4px;border-radius:calc(7px*var(--rr));color:var(--dim);cursor:pointer;opacity:0;transition:opacity .15s,color .15s;flex:none;display:grid;place-items:center}
.projects li:hover .pin,.pin:focus-visible,.pin[aria-pressed="true"]{opacity:1}
.pin[aria-pressed="true"]{color:var(--accent)}
.pin:hover{background:var(--panel2);color:var(--text)}
.pin svg{width:14px;height:14px}
.ctxmenu{position:fixed;z-index:90;min-width:220px;padding:5px;border-radius:calc(12px*var(--rr));background:var(--panel-solid);border:1px solid var(--line2);box-shadow:var(--shadow);animation:pop .15s}
.ctxmenu button{display:flex;width:100%;align-items:center;gap:10px;padding:8px 10px;border:0;background:none;border-radius:calc(8px*var(--rr));cursor:pointer;text-align:left;color:var(--text);font-weight:500}
.ctxmenu button:hover:not([disabled]),.ctxmenu button:focus-visible{background:rgba(var(--accent-rgb),.13)}
.ctxmenu button[disabled]{opacity:.4;cursor:not-allowed}
.ctxmenu button.danger{color:var(--err)}
.ctxmenu .k{margin-left:auto}
.ctxmenu hr{border:0;border-top:1px solid var(--line);margin:4px 2px}
.ftablist{display:flex;align-items:flex-end;gap:2px}
.ftab-add{flex:none;align-self:center;margin:0 0 4px 4px;width:26px;height:26px;border-radius:calc(8px*var(--rr));border:1px dashed var(--line2);background:none;color:var(--muted);cursor:pointer;display:grid;place-items:center;padding:0}
.ftab-add:hover{color:var(--accent);border-color:var(--accent)}
.seg{display:flex;gap:6px;margin:-4px 0 14px}
.seg button{flex:1;height:34px;border-radius:calc(9px*var(--rr));border:1px solid var(--line2);background:rgba(var(--fg),.03);cursor:pointer;font:600 13px var(--mono)}
.seg button[aria-checked="true"]{border-color:var(--accent);background:rgba(var(--accent-rgb),.12);color:var(--accent)}
.field .preview{font:12px var(--mono);color:var(--muted)}
.side-foot{padding:12px 14px;border-top:1px solid var(--line);font-size:11px;color:var(--dim);display:grid;gap:4px}
.side-foot code{font-family:var(--mono);color:var(--muted);word-break:break-all}
.btn-new{margin:0 12px 10px;display:flex;align-items:center;justify-content:center;gap:8px;padding:10px;border-radius:calc(11px*var(--rr));border:1px dashed rgba(var(--accent-rgb),.45);background:rgba(var(--accent-rgb),.06);color:var(--accent);font-weight:600;cursor:pointer;transition:.2s}
.btn-new:hover{background:rgba(var(--accent-rgb),.13);border-style:solid;transform:translateY(-1px)}

/* ---------- barre d'outils ---------- */
.toolbar{display:flex;align-items:center;gap:12px;padding:0 12px 0 16px;position:relative;overflow:visible;z-index:30;min-width:0}
.ptitle{display:flex;flex-direction:column;min-width:0;flex:0 1 auto}
.ptitle b{font-size:15px;font-weight:700;letter-spacing:-.01em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:220px}
.ptitle span{font-size:11px;color:var(--dim);font-family:var(--mono)}
.sep{width:1px;height:28px;background:var(--line);flex:none}
.sel{position:relative;display:flex;align-items:center;gap:8px;background:var(--field);border:1px solid var(--line);border-radius:calc(10px*var(--rr));padding:0 8px 0 10px;height:36px;min-width:0;transition:.2s}
.sel:hover{border-color:var(--line2)}
.sel:focus-within{border-color:rgba(var(--accent-rgb),.5);box-shadow:0 0 0 3px rgba(var(--accent-rgb),.1)}
.sel svg{color:var(--muted)}
.sel select{appearance:none;background:transparent;border:0;outline:0;padding:0 18px 0 0;height:100%;cursor:pointer;min-width:0;max-width:220px;text-overflow:ellipsis}
.sel select option,.sel select optgroup{background:var(--panel-solid);color:var(--text)}
.sel::after{content:"";position:absolute;right:10px;top:50%;width:6px;height:6px;border-right:1.6px solid var(--muted);border-bottom:1.6px solid var(--muted);transform:translateY(-70%) rotate(45deg);pointer-events:none}
.dot{width:8px;height:8px;border-radius:50%;background:var(--dim);flex:none}
.dot.on{background:var(--ok);box-shadow:0 0 0 0 rgba(var(--ok-rgb),.6);animation:pulse 2s infinite}
@keyframes pulse{70%{box-shadow:0 0 0 7px rgba(var(--ok-rgb),0)}100%{box-shadow:0 0 0 0 rgba(var(--ok-rgb),0)}}
.spacer{flex:1}
.btn{display:inline-flex;align-items:center;gap:8px;height:36px;padding:0 14px;border-radius:calc(10px*var(--rr));border:1px solid var(--line2);background:rgba(var(--fg),.04);cursor:pointer;font-weight:600;white-space:nowrap;transition:transform .15s,background .2s,border-color .2s,box-shadow .2s,opacity .2s;position:relative}
.btn:hover{background:rgba(var(--fg),.08);transform:translateY(-1px)}
.btn:active{transform:translateY(0) scale(.98)}
.btn:disabled{opacity:.45;pointer-events:none}
.btn.primary{border:0;background:var(--grad-btn);color:var(--on-grad);box-shadow:0 6px 22px -6px rgba(var(--accent-rgb),.65),inset 0 1px 0 rgba(var(--sheen-rgb),.25);overflow:hidden}
.btn.primary::after{content:"";position:absolute;inset:0;background:linear-gradient(115deg,transparent 30%,rgba(var(--sheen-rgb),.35) 50%,transparent 70%);transform:translateX(-120%);transition:transform .7s}
.btn.primary:hover::after{transform:translateX(120%)}
.btn.primary:hover{box-shadow:0 10px 28px -6px rgba(var(--accent-rgb),.8),inset 0 1px 0 rgba(var(--sheen-rgb),.25)}
@keyframes gradmove{50%{background-position:100% 50%}}
.btn.danger{border-color:rgba(var(--err-rgb),.45);color:var(--err);background:rgba(var(--err-rgb),.08)}
.btn.icon{width:36px;padding:0;justify-content:center}
.btn.sm{height:28px;padding:0 10px;font-size:12px;border-radius:calc(8px*var(--rr))}
.btn.on{border-color:rgba(var(--accent-rgb),.55);color:var(--accent);background:rgba(var(--accent-rgb),.1)}
.kbd{font:500 10.5px var(--mono);padding:1px 5px;border-radius:calc(5px*var(--rr));border:1px solid var(--line2);color:var(--muted);background:rgba(var(--fg),.04)}
.btn.primary .kbd{border-color:rgba(var(--sheen-rgb),.35);color:rgba(var(--sheen-rgb),.85);background:rgba(var(--sheen-rgb),.12)}
.switch{display:flex;align-items:center;gap:8px;cursor:pointer;user-select:none;color:var(--muted);font-weight:600;font-size:12px;white-space:nowrap}
.switch{position:relative}
.switch input{position:absolute;opacity:0;width:1px;height:1px;margin:0}
.switch i{width:34px;height:20px;border-radius:calc(20px*var(--rr));background:rgba(var(--fg),.1);position:relative;transition:.25s}
.switch i::after{content:"";position:absolute;left:3px;top:3px;width:14px;height:14px;border-radius:50%;background:var(--knob);transition:.25s cubic-bezier(.5,1.6,.4,1)}
.switch input:checked+i{background:var(--grad)}
.switch input:checked+i::after{left:17px}
.switch input:checked~span{color:var(--text)}

/* ---------- progression compilation / téléversement (dans la barre d'outils) ---------- */
.jobbar{display:none;flex:0 1 430px;min-width:0;gap:6px;align-items:flex-start;padding:0 4px}
.jobbar.show{display:flex;animation:fade .25s}
.jc{flex:1;min-width:34px;display:grid;gap:4px}
.js{display:block;height:5px;border-radius:calc(5px*var(--rr));background:rgba(var(--fg),.13);position:relative;overflow:hidden}
.jc span{font-size:10.5px;font-weight:600;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.jc.done .js{background:var(--ok)}.jc.done span{color:var(--ok)}
.jc.fail .js{background:var(--err)}.jc.fail span{color:var(--err)}
.jc.active span{color:var(--accent)}
.jc.active .js::after{content:"";position:absolute;top:0;bottom:0;width:45%;background:var(--grad-btn);border-radius:calc(5px*var(--rr));animation:indet 1.3s ease-in-out infinite}
.jobbar.single{flex-basis:220px}
@keyframes indet{0%{transform:translateX(-100%)}100%{transform:translateX(260%)}}
@keyframes pop{from{transform:scale(.94);opacity:0}}
.sr{position:absolute!important;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.skip{position:fixed;left:14px;top:-60px;z-index:100;padding:9px 14px;border-radius:calc(10px*var(--rr));background:var(--panel-solid);color:var(--text);border:2px solid var(--accent);font-weight:600;text-decoration:none;transition:top .15s}
.skip:focus{top:12px}
.themeseg{display:flex;gap:2px;padding:2px;border-radius:calc(10px*var(--rr));background:var(--field2);border:1px solid var(--line)}
.themeseg button{flex:1;display:flex;align-items:center;justify-content:center;gap:5px;height:26px;padding:0 4px;border:0;border-radius:calc(8px*var(--rr));background:none;color:var(--muted);cursor:pointer;font:600 11px var(--sans);white-space:nowrap}
.themeseg button svg{width:13px;height:13px}
.themeseg button:hover{color:var(--text)}
.themeseg button[aria-checked="true"]{background:var(--panel-solid);color:var(--accent);box-shadow:0 1px 4px rgba(var(--shade-rgb),.25)}
.pitem{display:flex;align-items:center;gap:10px;flex:1;min-width:0;background:none;border:0;padding:0;margin:0;color:inherit;font:inherit;text-align:left;cursor:pointer;border-radius:calc(8px*var(--rr))}
.ptablist{display:flex;align-items:center;gap:2px;flex:0 1 auto;min-width:0;overflow-x:auto;scrollbar-width:none}
@media (max-width:1560px){.ptab svg{display:none}}
/* focus clavier visible partout */
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
textarea.ta:focus-visible,.resizer:focus-visible{outline:none}
.editor-card:focus-within{border-color:rgba(var(--accent-rgb),.55)}
.search input:focus-visible,.field input:focus-visible,.sendbar input:focus-visible,.findbar input:focus-visible,.palette input:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.sel select:focus-visible{outline:none}
.sel:has(select:focus-visible){outline:2px solid var(--accent);outline-offset:2px}
.switch input:focus-visible+i{outline:2px solid var(--accent);outline-offset:2px}
/* mouvement réduit : aucune animation continue, transitions quasi instantanées */
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{animation-duration:.001ms!important;animation-iteration-count:1!important;animation-delay:0s!important;transition-duration:.001ms!important;scroll-behavior:auto!important}
  .bg i,.logo::after,.dot.on,.chip.on::after,.jc.active .js::after{animation:none!important}
  .jc.active .js::after{width:100%;transform:none}
}

/* ---------- éditeur ---------- */
.editor-card{display:flex;flex-direction:column;min-height:0;min-width:0;overflow:hidden}
.ftabs{display:flex;align-items:flex-end;gap:2px;padding:8px 10px 0;border-bottom:1px solid var(--line);overflow-x:auto;flex:none}
.ftab{display:flex;align-items:center;gap:7px;padding:7px 12px 8px;border-radius:calc(9px*var(--rr)) calc(9px*var(--rr)) 0 0;color:var(--muted);cursor:pointer;font-size:12.5px;white-space:nowrap;position:relative;transition:.15s}
.ftab:hover{color:var(--text);background:var(--panel2)}
.ftab.active{color:var(--text);background:rgba(var(--fg),.05)}
.ftab.active::after{content:"";position:absolute;left:10px;right:10px;bottom:-1px;height:2px;background:var(--grad);border-radius:calc(2px*var(--rr))}
.ftab .mod{width:7px;height:7px;border-radius:50%;background:var(--warn);display:none}
.ftab.dirty .mod{display:block}
.ftab .ext{font:600 9.5px var(--mono);padding:1px 4px;border-radius:calc(4px*var(--rr));background:rgba(var(--accent-rgb),.14);color:var(--accent)}
:root[data-theme="light"] .ftab .ext{background:rgba(var(--accent-rgb),.07)}
:root[data-theme="light"] .ftab .ext.h{background:rgba(var(--accent2-rgb),.08)}
.ftab .ext.h{background:rgba(var(--accent2-rgb),.16);color:var(--ext-h)}
.ftab .ext.t{background:rgba(var(--fg),.08);color:var(--muted)}
.ftab .errc{font:700 10px var(--mono);color:var(--on-err);background:var(--err);border-radius:calc(8px*var(--rr));padding:0 5px}
.editor{position:relative;flex:1;display:flex;min-height:0;font:var(--fs)/var(--lh) var(--mono);font-variant-ligatures:contextual}
.gutter{width:56px;flex:none;overflow:hidden;position:relative;color:var(--dim);text-align:right;user-select:none;border-right:1px solid var(--line)}
.gutter-in{padding:12px 12px 12px 0;will-change:transform}
.gutter-in div{height:var(--lh);position:relative;transition:color .15s}
.gutter-in div.cur{color:var(--text)}
.gutter-in div.e{color:var(--err);font-weight:700}
.gutter-in div.e::before{content:"";position:absolute;left:8px;top:50%;width:7px;height:7px;border-radius:50%;background:var(--err);transform:translateY(-50%);box-shadow:0 0 8px var(--err)}
.gutter-in div.w{color:var(--warn)}
.gutter-in div.w::before{content:"";position:absolute;left:8px;top:50%;width:7px;height:7px;border-radius:50%;background:var(--warn);transform:translateY(-50%)}
.code{position:relative;flex:1;overflow:hidden;min-width:0}
.layer{position:absolute;left:0;right:0;top:0;padding:12px 0;pointer-events:none;will-change:transform}
.curline{position:absolute;left:0;right:0;height:var(--lh);background:rgba(var(--fg),.035);border-top:1px solid rgba(var(--fg),.03);border-bottom:1px solid rgba(var(--fg),.03);transition:transform .06s}
.mark{position:absolute;left:0;right:0;height:var(--lh)}
.mark.e{background:linear-gradient(90deg,rgba(var(--err-rgb),.16),rgba(var(--err-rgb),.03))}
.mark.w{background:linear-gradient(90deg,rgba(var(--warn-rgb),.12),transparent)}
pre.hl,textarea.ta{margin:0;border:0;padding:12px 18px;font:inherit;line-height:var(--lh);white-space:pre;tab-size:2;-moz-tab-size:2;letter-spacing:0;word-spacing:0}
pre.hl,pre.hm{position:absolute;left:0;top:0;pointer-events:none;color:var(--code);will-change:transform;min-width:100%}
pre.hm{color:transparent}
.d-find{background:var(--d-find);border-radius:calc(2px*var(--rr))}
.d-cur{background:var(--d-cur);border-radius:calc(2px*var(--rr));box-shadow:0 0 0 1px var(--accent)}
.d-word{background:var(--d-word);border-radius:calc(2px*var(--rr))}
/* ================= Académie : parcours du développeur (page dédiée) ================= */
#stGrade{border:0;background:rgba(var(--accent-rgb),.12);color:var(--accent);font:600 11px var(--sans);padding:2px 8px;border-radius:calc(8px*var(--rr));cursor:pointer}
/* bouton de la barre latérale */
.acad-btn{position:relative;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:10px;width:100%;margin:0 0 10px;padding:10px 12px;border-radius:calc(14px*var(--rr));border:1px solid rgba(var(--accent-rgb),.35);background:linear-gradient(135deg,rgba(var(--accent-rgb),.14),rgba(var(--accent2-rgb),.10));color:var(--text);cursor:pointer;text-align:left;overflow:hidden;transition:transform .2s,border-color .2s,box-shadow .2s}
.acad-btn::after{content:"";position:absolute;inset:0;background:linear-gradient(115deg,transparent 30%,rgba(255,255,255,.14) 45%,transparent 60%);transform:translateX(-120%);transition:transform .9s}
.acad-btn:hover{transform:translateY(-1px);border-color:var(--accent);box-shadow:0 8px 26px -12px rgba(var(--accent-rgb),.7)}
.acad-btn:hover::after{transform:translateX(120%)}
.acad-btn.on{border-color:var(--accent);box-shadow:0 0 0 3px rgba(var(--accent-rgb),.18)}
.ab-ic{font-size:22px;width:34px;height:34px;display:grid;place-items:center;border-radius:calc(10px*var(--rr));background:var(--panel-solid);box-shadow:inset 0 0 0 1px var(--line2)}
.ab-txt{min-width:0}.ab-txt b{display:block;font-size:13.5px;font-family:var(--font-head)}.ab-txt small{display:block;color:var(--muted);font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ab-ring{--p:0;width:28px;height:28px;border-radius:50%;background:conic-gradient(var(--accent) calc(var(--p)*1%),rgba(var(--fg),.1) 0);display:grid;place-items:center;font:700 9px var(--mono);color:var(--muted)}
.ab-ring::before{content:attr(data-v);width:22px;height:22px;border-radius:50%;background:var(--panel-solid);display:grid;place-items:center}
/* la page remplace la zone de travail (la barre d'état reste) */
.academy{display:none}
.main.acad-open{grid-template-rows:minmax(0,1fr) 26px}
.main.acad-open>.toolbar,.main.acad-open>.content,.main.acad-open>.resizer,.main.acad-open>.panel{display:none!important}
.main.acad-open>.academy{display:flex;flex-direction:column;min-height:0;position:relative;animation:acIn .35s cubic-bezier(.2,.8,.2,1)}
@keyframes acIn{from{opacity:0;transform:translateY(10px) scale(.995)}to{opacity:1;transform:none}}
.ac-top{display:flex;align-items:center;gap:12px;padding:10px 14px;position:relative;z-index:3;min-width:0}
.ac-top .ac-langs{flex-wrap:nowrap;overflow-x:auto;min-width:0;scrollbar-width:none}
.ac-part{margin:18px 0 10px 44px;font:700 11px var(--sans);letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}
.ac-top .ac-lt,.ac-top .ac-brand,.ac-top .ac-nav,.ac-top .ac-xp,.ac-top #acBack{flex:none;white-space:nowrap}
.ac-brand{display:flex;align-items:center;gap:10px}.ac-brand b{display:block;font:700 16px var(--font-head);letter-spacing:.01em}.ac-brand small{display:block;color:var(--muted);font-size:11px}
.ac-logo{font-size:24px;filter:drop-shadow(0 4px 10px rgba(var(--accent-rgb),.45))}
.ac-langs{display:flex;flex-wrap:wrap;gap:6px}
.ac-lt{display:flex;align-items:center;gap:6px;padding:5px 11px;border:1px solid var(--line2);border-radius:calc(20px*var(--rr));background:var(--field);color:var(--text);cursor:pointer;font:500 12.5px var(--sans);transition:.15s}
.ac-lt small{color:var(--dim);font:600 10.5px var(--mono)}.ac-lt:hover{border-color:var(--accent)}
.ac-lt[aria-selected="true"]{border-color:var(--accent);background:rgba(var(--accent-rgb),.15);color:var(--accent);font-weight:700}
.ac-add select{max-width:170px}
.ac-nav{display:flex;gap:2px;padding:3px;border-radius:calc(11px*var(--rr));background:var(--field2);border:1px solid var(--line)}
.ac-nav button{height:30px;padding:0 14px;border:0;border-radius:calc(8px*var(--rr));background:none;color:var(--muted);cursor:pointer;font:600 12.5px var(--sans)}
.ac-nav button:hover{color:var(--text)}.ac-nav button[aria-selected="true"]{background:var(--panel-solid);color:var(--accent);box-shadow:0 1px 4px rgba(var(--shade-rgb,0,0,0),.25)}
.ac-xp{display:flex;align-items:center;gap:10px;font:600 12px var(--mono);color:var(--muted)}.ac-xp b{color:var(--accent);font-size:14px}
.ac-body{flex:1;overflow:auto;padding:16px 18px 40px;scroll-behavior:smooth}
.ac-wrap{max-width:1180px;margin:0 auto}
/* héros */
.ac-hero{position:relative;display:grid;grid-template-columns:auto minmax(0,1fr) minmax(250px,330px);gap:22px;align-items:center;padding:22px 24px;border-radius:calc(20px*var(--rr));border:1px solid rgba(var(--accent-rgb),.3);background:radial-gradient(120% 140% at 0% 0%,rgba(var(--accent-rgb),.20),transparent 55%),radial-gradient(120% 140% at 100% 100%,rgba(var(--accent2-rgb),.16),transparent 55%),var(--panel);overflow:hidden;margin-bottom:16px}
.ac-hero::before{content:"";position:absolute;inset:-40%;background:conic-gradient(from 0deg,transparent 0 70%,rgba(var(--accent-rgb),.10) 80%,transparent 90%);animation:acSpin 14s linear infinite;pointer-events:none}
@keyframes acSpin{to{transform:rotate(1turn)}}
.ac-badge{position:relative;width:132px;height:132px;display:grid;place-items:center}
.ac-badge svg{position:absolute;inset:0;transform:rotate(-90deg)}
.ac-badge circle{fill:none;stroke-width:8;stroke-linecap:round}
.ac-badge .bg-c{stroke:rgba(var(--fg),.09)}.ac-badge .fg-c{stroke:url(#acGrad);transition:stroke-dashoffset 1.2s cubic-bezier(.2,.8,.2,1)}
.ac-badge .ic{font-size:54px;line-height:1;filter:drop-shadow(0 6px 16px rgba(var(--accent-rgb),.55));animation:acFloat 4s ease-in-out infinite}
@keyframes acFloat{50%{transform:translateY(-5px)}}
.ac-who small{display:block;color:var(--muted);font-size:12px;letter-spacing:.06em;text-transform:uppercase}
.ac-who{min-width:0}.ac-who h2{overflow-wrap:anywhere;margin:2px 0 6px;font:800 clamp(26px,3.2vw,40px)/1.05 var(--font-head);background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.ac-meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:4px}
.ac-meta span{display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:calc(20px*var(--rr));background:rgba(var(--fg),.06);border:1px solid var(--line);font:600 11.5px var(--sans);color:var(--muted)}
.ac-meta span b{color:var(--text)}
.ac-steps{display:flex;gap:3px;margin-top:12px}.ac-steps i{flex:1;height:6px;border-radius:6px;background:rgba(var(--fg),.1)}
.ac-steps i.done{background:var(--grad)}.ac-steps i.cur{background:rgba(var(--accent-rgb),.45);animation:acPulse 1.6s ease-in-out infinite}
@keyframes acPulse{50%{opacity:.45}}
.ac-next{position:relative;padding:14px 16px;border-radius:calc(14px*var(--rr));background:var(--panel-solid);border:1px solid var(--line2);box-shadow:var(--shadow)}
.ac-next small{display:block;color:var(--muted);font-size:10.5px;letter-spacing:.07em;text-transform:uppercase}
.ac-next b{display:block;margin:4px 0 2px;font-size:15px}.ac-next p{margin:0 0 10px;color:var(--dim);font-size:12px}
.ac-next .btn{width:100%;justify-content:center}
.ac-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px;margin-bottom:22px}
.ac-card{display:grid;grid-template-columns:auto 1fr;gap:2px 12px;align-items:center;padding:12px 14px;border-radius:calc(14px*var(--rr));border:1px solid var(--line);background:var(--panel);cursor:pointer;text-align:left;color:var(--text);font:inherit;transition:.18s}
.ac-card:hover{transform:translateY(-2px);border-color:rgba(var(--accent-rgb),.5)}
.ac-card .e{grid-row:1/3;font-size:24px}.ac-card small{color:var(--muted);font-size:11px}.ac-card b{font-size:13px}
.ac-card.hl{border-color:rgba(var(--warn-rgb),.55);background:linear-gradient(135deg,rgba(var(--warn-rgb),.12),var(--panel))}
.ac-h{display:flex;align-items:baseline;gap:10px;margin:6px 0 12px}.ac-h h3{margin:0;font:700 18px var(--font-head)}.ac-h span{color:var(--muted);font-size:12px}
/* frise de carrière */
.ac-ladder{position:relative;padding-left:46px}
.ac-ladder::before{content:"";position:absolute;left:19px;top:14px;bottom:14px;width:3px;border-radius:3px;background:rgba(var(--fg),.1)}
.ac-ladder::after{content:"";position:absolute;left:19px;top:14px;width:3px;height:var(--fill,0%);border-radius:3px;background:var(--grad);box-shadow:0 0 12px rgba(var(--accent-rgb),.6);transition:height 1.2s cubic-bezier(.2,.8,.2,1)}
.ac-stage{position:relative;margin-bottom:12px;border-radius:calc(16px*var(--rr));border:1px solid var(--line);background:var(--panel);transition:border-color .2s,box-shadow .2s}
.ac-stage>.node{position:absolute;left:-46px;top:12px;width:40px;height:40px;border-radius:50%;display:grid;place-items:center;font-size:19px;background:var(--panel-solid);border:3px solid rgba(var(--fg),.14);z-index:1}
.ac-stage.done>.node{border-color:var(--accent);box-shadow:0 0 0 4px rgba(var(--accent-rgb),.14)}
.ac-stage.cur{border-color:rgba(var(--accent-rgb),.6);box-shadow:0 0 0 4px rgba(var(--accent-rgb),.09),0 18px 40px -24px rgba(var(--accent-rgb),.8)}
.ac-stage.cur>.node{border-color:var(--accent);animation:acGlow 2.2s ease-in-out infinite}
@keyframes acGlow{50%{box-shadow:0 0 0 9px rgba(var(--accent-rgb),.12),0 0 24px rgba(var(--accent-rgb),.55)}}
.ac-stage.locked>.node{filter:grayscale(1);opacity:.6}
.ac-stage.locked .ac-sh{opacity:.72}
.ac-sh{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px 14px;align-items:center;width:100%;padding:13px 16px;border:0;background:none;color:inherit;font:inherit;text-align:left;cursor:pointer}
.ac-sh .t{display:flex;flex-wrap:wrap;align-items:center;gap:8px}.ac-sh .t b{font:700 15px var(--font-head)}
.ac-sh p{grid-column:1/-1;margin:0;color:var(--dim);font-size:12px}
.ac-dom{font:700 10px var(--sans);letter-spacing:.06em;text-transform:uppercase;padding:2px 8px;border-radius:calc(6px*var(--rr));background:rgba(var(--accent2-rgb),.13);color:var(--accent2)}
.ac-st{font:700 10.5px var(--sans);padding:3px 9px;border-radius:calc(20px*var(--rr));background:rgba(var(--fg),.07);color:var(--muted);white-space:nowrap}
.ac-stage.done .ac-st{background:rgba(var(--ok-rgb),.15);color:var(--ok)}.ac-stage.cur .ac-st{background:var(--grad);color:var(--ink,#000)}
.ac-prog{display:flex;align-items:center;gap:10px;min-width:170px}.ac-prog i{flex:1;height:7px;border-radius:7px;background:rgba(var(--fg),.08);overflow:hidden}
.ac-prog em{display:block;height:100%;border-radius:7px;background:var(--grad);transition:width 1s}.ac-prog small{font:600 11px var(--mono);color:var(--muted)}
.ac-meds{font-size:12px;letter-spacing:1px;white-space:nowrap}
.ac-tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(205px,1fr));gap:8px;padding:0 14px 14px}
.ac-stage:not(.open) .ac-tiles{display:none}
.ac-tile{position:relative;display:grid;grid-template-columns:auto 1fr;gap:1px 10px;align-items:center;padding:10px 12px;border-radius:calc(12px*var(--rr));border:1px solid var(--line2);background:var(--field);color:var(--text);cursor:pointer;text-align:left;font:inherit;transition:transform .15s,border-color .15s,background .15s;animation:acTile .4s both;animation-delay:calc(var(--i,0)*30ms)}
@keyframes acTile{from{opacity:0;transform:translateY(6px)}}
.ac-tile:hover{transform:translateY(-2px);border-color:var(--accent);background:rgba(var(--accent-rgb),.07)}
.ac-tile .s{grid-row:1/4;width:30px;height:30px;display:grid;place-items:center;border-radius:50%;font-size:15px;background:rgba(var(--fg),.06)}
.ac-tile b{font-size:12.8px;line-height:1.25}.ac-tile small{color:var(--dim);font-size:10.8px;display:flex;gap:6px;flex-wrap:wrap}
.ac-tile.done{border-color:rgba(var(--ok-rgb),.45)}.ac-tile.done .s{background:rgba(var(--ok-rgb),.14)}
.ac-tile.locked{opacity:.55}.ac-tile.active{border-color:var(--warn);box-shadow:0 0 0 2px rgba(var(--warn-rgb),.2)}
.ac-tile.exam{grid-column:1/-1;border-width:2px;border-color:transparent;background:linear-gradient(var(--panel-solid),var(--panel-solid)) padding-box,var(--grad) border-box;padding:12px 14px}
.ac-tile.exam .s{background:var(--grad);color:#fff}
.ac-tile .tg{grid-column:2;font:700 9.5px var(--sans);letter-spacing:.04em;text-transform:uppercase;color:var(--warn);order:-1}
.ac-tile.exam .tg{color:var(--accent)}
/* tiroir de détail */
.ac-scrim{position:absolute;inset:0;background:rgba(0,0,0,.35);backdrop-filter:blur(2px);z-index:4;animation:acFade .2s}
@keyframes acFade{from{opacity:0}}
.ac-drawer{position:absolute;top:0;right:0;bottom:0;width:min(640px,100%);z-index:5;display:flex;flex-direction:column;background:var(--bg2);border-left:1px solid var(--line2);box-shadow:-20px 0 60px -20px rgba(0,0,0,.5);animation:acSlide .28s cubic-bezier(.2,.8,.2,1)}
@keyframes acSlide{from{transform:translateX(40px);opacity:0}}
.ac-dh{display:flex;align-items:flex-start;gap:12px;padding:18px 20px 12px;border-bottom:1px solid var(--line)}
.ac-dh .big{font-size:30px;line-height:1}.ac-dh h2{margin:2px 0 4px;font:800 20px/1.2 var(--font-head)}.ac-dh small{color:var(--muted);font-size:11.5px}
.ac-dh .x{margin-left:auto}
.ac-db{flex:1;overflow:auto;padding:16px 20px 24px}
.ac-chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
.ac-chips span{font:600 11px var(--sans);padding:3px 9px;border-radius:calc(20px*var(--rr));border:1px solid var(--line2);color:var(--muted)}
.ac-chips span.k{border-color:transparent;background:var(--grad);color:#fff}.ac-chips span.dbg{border-color:rgba(var(--warn-rgb),.5);color:var(--warn)}
.ac-desc{margin:0 0 14px;line-height:1.6;font-size:13.5px;white-space:pre-line}
.ac-ex{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:0 0 10px}
.ac-ex small{display:block;color:var(--dim);font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;margin-bottom:3px}
.ac-ex pre,.df-ex pre,.df-diff pre{margin:0;padding:8px 10px;background:var(--field);border:1px solid var(--line);border-radius:calc(8px*var(--rr));font:12px/1.45 var(--mono);max-height:170px;overflow:auto;white-space:pre-wrap;word-break:break-word}
.ac-acts{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0 4px}
.ac-hints{margin:12px 0 0;padding:10px 14px 10px 32px;border-radius:calc(10px*var(--rr));background:rgba(var(--warn-rgb),.07);border:1px dashed rgba(var(--warn-rgb),.4);color:var(--text)}
.ac-hints li{margin:4px 0;font-size:12.5px}
.ac-note{color:var(--dim);font-size:12px;margin:8px 0 0}
/* compétences */
.ac-grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px;margin-bottom:14px}
.ac-panel{padding:16px 18px;border-radius:calc(16px*var(--rr));border:1px solid var(--line);background:var(--panel)}
.ac-panel h3{margin:0 0 12px;font:700 11px var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);display:flex;justify-content:space-between}
.ac-radar{display:block;width:100%;max-width:360px;margin:0 auto}
.ac-radar .grid{fill:none;stroke:rgba(var(--fg),.12)}.ac-radar .axe{stroke:rgba(var(--fg),.1)}
.ac-radar .zone{fill:rgba(var(--accent-rgb),.22);stroke:var(--accent);stroke-width:2;transform-origin:center;animation:acGrow .9s cubic-bezier(.2,.8,.2,1)}
@keyframes acGrow{from{transform:scale(.2);opacity:0}}
.ac-radar text{fill:var(--muted);font:600 10.5px var(--sans)}.ac-radar .pt{fill:var(--accent)}
.ac-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.ac-stats div{padding:10px;border-radius:calc(12px*var(--rr));border:1px solid var(--line);text-align:center;background:rgba(var(--fg),.02)}
.ac-stats b{display:block;font:800 20px var(--font-head)}.ac-stats small{color:var(--dim);font-size:11px}
.ac-heat{display:grid;grid-auto-flow:column;grid-template-rows:repeat(7,13px);grid-auto-columns:13px;gap:3px;justify-content:start;overflow-x:auto;padding-bottom:4px}
.ac-heat i{width:13px;height:13px;border-radius:3px;background:rgba(var(--fg),.07)}
.ac-heat i[data-l="1"]{background:rgba(var(--accent-rgb),.3)}.ac-heat i[data-l="2"]{background:rgba(var(--accent-rgb),.55)}
.ac-heat i[data-l="3"]{background:rgba(var(--accent-rgb),.8)}.ac-heat i[data-l="4"]{background:var(--accent);box-shadow:0 0 6px rgba(var(--accent-rgb),.6)}
.ac-heat i.today{outline:2px solid var(--accent2);outline-offset:1px}
.ac-legend{display:flex;align-items:center;gap:4px;justify-content:flex-end;margin-top:6px;color:var(--dim);font-size:10.5px}.ac-legend i{width:10px;height:10px;border-radius:2px}
.ac-bar{display:grid;grid-template-columns:28px 1fr auto;gap:10px;align-items:center;margin:7px 0;font-size:12.5px}
.ac-bar i{height:8px;border-radius:8px;background:rgba(var(--fg),.08);overflow:hidden}.ac-bar em{display:block;height:100%;background:var(--grad);border-radius:8px}
.ac-bar small{color:var(--dim);font:600 11px var(--mono)}
.ac-row{display:flex;justify-content:space-between;gap:10px;font-size:12.5px;padding:5px 0;border-bottom:1px dashed var(--line)}.ac-row small{color:var(--dim)}
/* succès */
.ac-grades{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px}
.ac-gcard{display:grid;grid-template-columns:auto 1fr;gap:2px 10px;align-items:center;padding:12px;border-radius:calc(14px*var(--rr));border:1px solid var(--line);background:var(--panel)}
.ac-gcard span{grid-row:1/4;font-size:30px}.ac-gcard small{color:var(--dim);font-size:11px}.ac-gcard .btn{grid-column:1/-1;margin-top:8px;justify-content:center}
.ac-ach{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}
.ac-ach div{position:relative;display:grid;grid-template-columns:auto 1fr;gap:1px 12px;align-items:center;padding:12px;border-radius:calc(14px*var(--rr));border:1px solid var(--line);background:var(--panel);overflow:hidden}
.ac-ach div:not(.got){opacity:.5;filter:grayscale(.9)}
.ac-ach div.got{border-color:rgba(var(--accent-rgb),.45)}
.ac-ach div.got::after{content:"";position:absolute;inset:0;background:linear-gradient(115deg,transparent 35%,rgba(255,255,255,.16) 50%,transparent 65%);transform:translateX(-120%);animation:acShine 5s ease-in-out infinite;animation-delay:calc(var(--i,0)*.35s)}
@keyframes acShine{0%,70%{transform:translateX(-120%)}100%{transform:translateX(120%)}}
.ac-ach span{grid-row:1/3;font-size:28px}.ac-ach b{font-size:13px}.ac-ach small{color:var(--dim);font-size:11px}
/* promotion */
.promo{position:fixed;inset:0;z-index:200;display:grid;place-items:center;background:radial-gradient(circle at 50% 45%,rgba(var(--accent-rgb),.30),transparent 60%),rgba(6,8,16,.9);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);animation:acFade .4s;overflow:hidden}
.promo .rays{position:absolute;width:160vmax;height:160vmax;background:repeating-conic-gradient(from 0deg,rgba(var(--accent-rgb),.13) 0 6deg,transparent 6deg 18deg);animation:acSpin 30s linear infinite;mask:radial-gradient(circle,#000 10%,transparent 60%);-webkit-mask:radial-gradient(circle,#000 10%,transparent 60%)}
.promo .box{position:relative;text-align:center;color:#fff;padding:20px;max-width:560px}
.promo .lvl{font:800 12px var(--sans);letter-spacing:.4em;text-transform:uppercase;color:rgba(255,255,255,.75);animation:acUp .6s .2s both}
.promo .ic{font-size:120px;line-height:1.1;margin:10px 0;filter:drop-shadow(0 10px 40px rgba(var(--accent-rgb),.9));animation:acPop .9s cubic-bezier(.2,1.6,.3,1) both}
@keyframes acPop{0%{transform:scale(0) rotate(-30deg);opacity:0}100%{transform:none;opacity:1}}
@keyframes acUp{from{opacity:0;transform:translateY(14px)}}
.promo h2{margin:0;font:900 clamp(30px,5vw,54px)/1.05 var(--font-head);background:linear-gradient(90deg,#fff,rgba(var(--accent-rgb),1),#fff);background-size:200% 100%;-webkit-background-clip:text;background-clip:text;color:transparent;animation:acUp .6s .35s both,acShimmer 3s linear infinite}
@keyframes acShimmer{to{background-position:-200% 0}}
.promo p{color:rgba(255,255,255,.85);font-size:14.5px;line-height:1.55;animation:acUp .6s .5s both}
.promo .acts{display:flex;gap:10px;justify-content:center;margin-top:18px;animation:acUp .6s .65s both}
.promo .conf{position:absolute;top:-20px;width:10px;height:16px;border-radius:2px;animation:acFall var(--d) linear var(--dl) forwards}
@keyframes acFall{to{transform:translate(var(--x),110vh) rotate(var(--r))}}
/* panneau Défi dans l'inspecteur */
#itDefi{color:var(--accent)}
.df{display:flex;flex-direction:column;gap:10px}
.df-head{position:relative;padding:14px 16px;border-radius:var(--radius);border:1px solid rgba(var(--accent-rgb),.35);background:linear-gradient(135deg,rgba(var(--accent-rgb),.13),rgba(var(--accent2-rgb),.07)),var(--panel)}
.df-head small{display:block;color:var(--muted);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase}
.df-head b{display:block;margin:3px 0 8px;font:800 16px/1.25 var(--font-head)}
.df-tim{position:absolute;top:12px;right:14px;font:700 12.5px var(--mono);color:var(--muted)}.df-tim.over{color:var(--warn)}
.df-desc{font-size:12.8px;line-height:1.55;margin:0;white-space:pre-line}
.df-ex summary{cursor:pointer;color:var(--muted);font:700 11px var(--sans);letter-spacing:.06em;text-transform:uppercase;margin:4px 0 6px}
.df-ex .p{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:6px}.df-ex small{color:var(--dim);font-size:10px}
.df-go{width:100%;justify-content:center;height:40px;font-size:13.5px}
.df-next{width:100%;justify-content:center;height:40px;margin-top:10px;font-size:13.5px;animation:acFade .4s}
.df-row{display:flex;gap:6px}.df-row .btn{flex:1;justify-content:center}
.df-res{padding:12px 14px;border-radius:var(--radius);border:1px solid;animation:acUp .35s both}
.df-res.ok{border-color:rgba(var(--ok-rgb),.55);background:rgba(var(--ok-rgb),.08)}.df-res.ko{border-color:rgba(var(--err-rgb),.55);background:rgba(var(--err-rgb),.06)}
.df-res>b{display:block;font-size:13.5px}.df-res p{margin:8px 0 0;font-size:12px;color:var(--muted)}
.df-dots{display:flex;flex-wrap:wrap;gap:4px;margin-top:9px}
.df-dots span{width:20px;height:20px;border-radius:6px;display:grid;place-items:center;font-size:10px;font-weight:700;animation:acDot .3s both;animation-delay:calc(var(--i)*45ms)}
@keyframes acDot{from{transform:scale(0)}}
.df-dots .ok{background:rgba(var(--ok-rgb),.2);color:var(--ok)}.df-dots span:not(.ok){background:rgba(var(--err-rgb),.16);color:var(--err)}
.df-diff{display:grid;gap:6px;margin-top:8px}.df-diff small{color:var(--dim);font-size:10px;text-transform:uppercase;letter-spacing:.05em}
.df-diff pre.err{color:var(--err)}
.df-running{display:flex;align-items:center;gap:10px;padding:12px 14px;border-radius:var(--radius);border:1px dashed rgba(var(--accent-rgb),.5);color:var(--muted);font-size:12.5px}
.df-running i{width:14px;height:14px;border-radius:50%;border:2px solid rgba(var(--accent-rgb),.25);border-top-color:var(--accent);animation:acSpin .8s linear infinite}
.pg-sol{max-height:60vh;overflow:auto;padding:12px 14px;background:var(--field);border:1px solid var(--line);border-radius:calc(10px*var(--rr));font:12.5px/1.5 var(--mono)}
.sol-tabs{display:flex;gap:4px;margin-bottom:8px}.sol-tabs button{padding:4px 10px;border-radius:calc(8px*var(--rr));border:1px solid var(--line2);background:none;color:var(--muted);cursor:pointer;font:600 12px var(--sans)}
.sol-tabs button[aria-selected="true"]{border-color:var(--accent);color:var(--accent);background:rgba(var(--accent-rgb),.1)}
@media (max-width:1500px){.ac-brand small,.ac-xp span[title="Série de jours"]{display:none}}
@media (max-width:1280px){.ac-brand{display:none}.ac-hero{grid-template-columns:auto minmax(0,1fr)}.ac-next{grid-column:1/-1}}
@media (max-width:1000px){.ac-hero{grid-template-columns:auto 1fr}.ac-next{grid-column:1/-1}.ac-ladder{padding-left:0}.ac-ladder::before,.ac-ladder::after,.ac-stage>.node{display:none}}
@media (max-width:640px){.ac-hero{grid-template-columns:1fr;text-align:center}.ac-badge{margin:0 auto}.ac-meta,.ac-steps{justify-content:center}.ac-ex,.df-ex .p{grid-template-columns:1fr}}
.d-snip{box-shadow:inset 0 -2px 0 rgba(var(--accent-rgb),.55);background:rgba(var(--accent-rgb),.10);border-radius:calc(2px*var(--rr))}
.d-br{background:var(--d-br);border-radius:calc(2px*var(--rr));box-shadow:0 0 0 1px var(--accent)}
.d-brx{background:rgba(var(--err-rgb),.4);border-radius:calc(2px*var(--rr))}
.d-err,.d-warn{text-decoration:underline wavy;text-decoration-thickness:1.5px;text-underline-offset:3px;text-decoration-skip-ink:none}
.d-err{text-decoration-color:var(--err)}.d-warn{text-decoration-color:var(--warn)}
.ruler{width:12px;flex:none;position:relative;border-left:1px solid var(--line);cursor:pointer;background:var(--field2)}
.ruler i{position:absolute;left:2px;right:2px;height:4px;margin-top:-2px;border-radius:calc(2px*var(--rr));pointer-events:none}
.ruler i.e{background:var(--err)}.ruler i.w{background:var(--warn)}.ruler i.f{background:var(--accent3)}.ruler i.c{background:var(--muted);opacity:.55;height:2px}
.findbar{position:absolute;top:8px;right:24px;z-index:6;display:grid;gap:6px;padding:8px;border-radius:calc(12px*var(--rr));background:var(--panel-solid);border:1px solid var(--line2);box-shadow:var(--shadow);font-family:var(--sans)}
.findbar[hidden],.ac[hidden],.tip[hidden],.frow[hidden]{display:none}
.frow{display:flex;align-items:center;gap:5px}
.findbar input{height:28px;width:190px;background:var(--field);border:1px solid var(--line2);border-radius:calc(8px*var(--rr));padding:0 9px;outline:none;font:12.5px var(--mono)}
.findbar input:focus{border-color:var(--accent)}
.findbar input.bad{border-color:var(--err)}
.fcount{font:11.5px var(--mono);color:var(--muted);min-width:78px;text-align:center;white-space:nowrap}
.btn[aria-pressed="true"]{border-color:rgba(var(--accent-rgb),.55);color:var(--accent);background:rgba(var(--accent-rgb),.1)}
.btn.tg{font:600 11.5px var(--mono);padding:0 8px;height:28px;border-radius:calc(8px*var(--rr))}
.ac{position:absolute;z-index:8;min-width:200px;max-width:340px;max-height:214px;overflow:auto;padding:4px;border-radius:calc(10px*var(--rr));background:var(--panel-solid);border:1px solid var(--line2);box-shadow:var(--shadow);font:12.5px var(--mono)}
.ac div{display:flex;gap:14px;align-items:center;justify-content:space-between;padding:4px 8px;border-radius:calc(6px*var(--rr));cursor:pointer;color:var(--muted)}
.ac div.sel{background:linear-gradient(90deg,rgba(var(--accent-rgb),.2),rgba(var(--accent2-rgb),.12));color:var(--text)}
.ac small{color:var(--dim);font:11px var(--sans)}
.tip{position:fixed;z-index:80;max-width:440px;padding:7px 11px;border-radius:calc(9px*var(--rr));background:var(--panel-solid);border:1px solid var(--line2);box-shadow:var(--shadow);font:12px/1.45 var(--sans);pointer-events:none}
.tip b.e{color:var(--err)}.tip b.w{color:var(--warn)}
.fontctl{display:flex;align-items:center;gap:2px}
.tinybtn{background:none;border:0;color:var(--muted);cursor:pointer;padding:1px 6px;border-radius:calc(5px*var(--rr));font:600 11px var(--sans);white-space:nowrap;flex:none}
#stDiag{display:inline-flex;gap:8px;align-items:center}
.tinybtn:hover{background:var(--panel2);color:var(--text)}
textarea.ta{position:absolute;inset:0;width:100%;height:100%;resize:none;outline:none;background:transparent;color:transparent;caret-color:var(--caret);overflow:auto;z-index:2}
textarea.ta::selection{background:var(--sel);color:transparent}
.tk-c{color:var(--tk-c);font-style:italic}.tk-s{color:var(--tk-s)}.tk-n{color:var(--tk-n)}.tk-k{color:var(--tk-k);font-weight:500}
.tk-t{color:var(--tk-t)}.tk-f{color:var(--tk-f)}.tk-q{color:var(--tk-n)}.tk-p{color:var(--tk-p)}.tk-o{color:var(--tk-o)}.tk-call{color:var(--tk-call)}
.welcome{font-family:var(--sans);position:absolute;inset:0;display:none;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:30px;z-index:3;background:radial-gradient(ellipse at center,rgba(var(--panel-rgb),.2),rgba(var(--panel-rgb),.9))}
.welcome.show{display:flex}
.welcome h1{font-size:56px;margin:0;letter-spacing:-.045em;font-weight:800;background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent;line-height:1.05}
.welcome p{color:var(--muted);max-width:460px;font-size:15px;margin:12px 0 26px}
.welcome .row{display:flex;gap:10px;flex-wrap:wrap;justify-content:center}
.recent{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:10px;width:min(720px,100%);margin-top:34px}
.recent button{font:inherit;color:inherit;padding:14px;border-radius:calc(12px*var(--rr));border:1px solid var(--line);background:rgba(var(--fg),.03);cursor:pointer;text-align:left;transition:.2s}
.recent button:hover{border-color:rgba(var(--accent-rgb),.4);transform:translateY(-2px);background:rgba(var(--accent-rgb),.06)}
.recent b{display:block}.recent small{display:block;color:var(--dim);font-family:var(--mono);font-size:11px}
.warnbox{margin-top:22px;padding:12px 16px;border-radius:calc(12px*var(--rr));border:1px solid rgba(var(--warn-rgb),.35);background:rgba(var(--warn-rgb),.08);color:var(--warn-text);display:none;gap:10px;align-items:center;text-align:left}
.warnbox.show{display:flex}
.warnbox code{font-family:var(--mono);background:var(--field);padding:2px 6px;border-radius:calc(6px*var(--rr))}

/* ---------- inspecteur ---------- */
.inspector{display:flex;flex-direction:column;gap:10px;min-height:0;overflow:auto}
.card{padding:14px 16px}
.card h3{margin:0 0 12px;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);display:flex;align-items:center;justify-content:space-between}
.board{display:flex;gap:13px;align-items:center}
.chip{width:56px;height:56px;border-radius:calc(14px*var(--rr));display:grid;place-items:center;background:linear-gradient(135deg,rgba(var(--accent-rgb),.18),rgba(var(--accent2-rgb),.18));border:1px solid rgba(var(--fg),.08);position:relative;flex:none}
.chip svg{width:28px;height:28px;color:var(--accent)}
.chip.off{background:rgba(var(--fg),.04)}.chip.off svg{color:var(--dim)}
.chip.on::after{content:"";position:absolute;inset:-1px;border-radius:calc(14px*var(--rr));border:1px solid var(--accent);animation:ring 2.4s infinite}
@keyframes ring{0%{opacity:.8;transform:scale(1)}100%{opacity:0;transform:scale(1.25)}}
.board b{display:block;font-size:14.5px}
.board small{display:block;color:var(--muted);font-family:var(--mono);font-size:11px;word-break:break-all}
.pill{display:inline-flex;align-items:center;gap:6px;font-size:11px;font-weight:600;padding:3px 9px;border-radius:calc(20px*var(--rr));background:rgba(var(--ok-rgb),.1);color:var(--ok);margin-top:6px}
.pill.off{background:rgba(var(--fg),.06);color:var(--muted)}
.mem{display:grid;gap:11px}
.mrow{display:grid;grid-template-columns:44px minmax(0,1fr) auto;align-items:center;gap:4px 10px}
.mrow>b{font-size:12px;font-weight:600;color:var(--muted)}
.mbar{height:8px;border-radius:calc(8px*var(--rr));background:rgba(var(--fg),.07);overflow:hidden}
.mbar i{display:block;height:100%;width:0;border-radius:calc(8px*var(--rr));background:var(--grad);transition:width .9s cubic-bezier(.2,.8,.2,1)}
.mrow.warn .mbar i{background:var(--warn)}.mrow.crit .mbar i{background:var(--err)}
.mrow .mv{font:700 12.5px var(--mono);min-width:38px;text-align:right}
.mrow.warn .mv{color:var(--warn)}.mrow.crit .mv{color:var(--err)}
.mrow .mc{grid-column:2/4;font:11px var(--mono);color:var(--dim);margin-top:-2px}
.mem-empty{margin:0;color:var(--dim);font-size:12px;text-align:center;padding:4px 0}
.mem.has-data .mem-empty{display:none}
.mem:not(.has-data) .mbar{opacity:.5}
.muted{color:var(--muted)}.dim{color:var(--dim)}
.hist{display:grid;gap:6px;font-size:12px}
.hist div{display:flex;align-items:center;gap:8px;padding:7px 9px;border-radius:calc(9px*var(--rr));background:rgba(var(--fg),.03)}
.hist .ok{color:var(--ok)}.hist .ko{color:var(--err)}
.hist span:nth-child(2){flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hist time{color:var(--dim);font-family:var(--mono);font-size:11px}
.keys{display:grid;grid-template-columns:1fr auto;gap:7px 10px;font-size:12px;color:var(--muted)}

/* ---------- panneau bas ---------- */
.resizer{cursor:row-resize;position:relative;touch-action:none;outline:none}
.resizer:focus-visible::after{background:var(--accent);width:70px}
.main.collapsed{--panel-h:44px}
.main.collapsed .pbody{display:none}
.main.collapsed .ptabs{border-bottom-color:transparent}
.main.collapsed .resizer{cursor:pointer}
.ptoggle svg{transition:transform .2s}
.main.collapsed .ptoggle svg{transform:rotate(180deg)}
.resizer::after{content:"";position:absolute;left:50%;top:50%;width:44px;height:3px;border-radius:calc(3px*var(--rr));background:var(--line2);transform:translate(-50%,-50%);transition:.2s}
.resizer:hover::after{background:var(--accent);width:70px}
.panel{display:flex;flex-direction:column;min-height:0;overflow:hidden}
.ptabs{display:flex;align-items:center;gap:2px;padding:6px 8px;border-bottom:1px solid var(--line);flex:none;overflow:hidden}
.ptabs>.btn{flex:none}
.ptab{white-space:nowrap;flex:none;display:flex;align-items:center;gap:7px;padding:6px 12px;border-radius:calc(8px*var(--rr));cursor:pointer;color:var(--muted);font-weight:600;font-size:12.5px;transition:.15s;position:relative;border:0;background:none}
.ptab:hover{color:var(--text);background:var(--panel2)}
.ptab.active{color:var(--text);background:rgba(var(--fg),.07)}
.ptab.active svg{color:var(--accent)}
.badge{font:700 10px var(--mono);min-width:17px;height:17px;padding:0 5px;border-radius:calc(9px*var(--rr));display:none;place-items:center;background:var(--err);color:var(--on-err)}
.badge.show{display:grid}
.badge.info{background:var(--accent);color:var(--on-accent)}
.badge.warn{background:var(--warn);color:var(--on-warn)}
.pbody{flex:1;min-height:0;position:relative}
.pview{position:absolute;inset:0;display:none;flex-direction:column;min-height:0}
.pview.active{display:flex}
.ptools{display:flex;align-items:center;gap:8px;padding:8px 12px;border-bottom:1px solid var(--line);flex-wrap:wrap}
.ptools .sel{height:28px;border-radius:calc(8px*var(--rr))}
.ptools .sel select{font-size:12px}
.out{flex:1;overflow:auto;padding:8px 14px 12px;font:12.5px/1.6 var(--mono);white-space:pre-wrap;word-break:break-word}
#console .l{animation:fadein .25s ease}
@keyframes fadein{from{opacity:0;transform:translateY(2px)}}
.out .cmd{color:var(--accent3);margin-top:6px}
.out .cmd::before{content:"❯ ";color:var(--accent)}
.out .error{color:var(--err)}.out .warn{color:var(--warn)}.out .ok{color:var(--ok)}.out .info{color:var(--info)}
.out .jump{cursor:pointer;text-decoration:underline dotted;text-underline-offset:3px}
.out .jump:hover,.out .jump:focus-visible{background:rgba(var(--err-rgb),.12)}
.stdiag{display:flex;align-items:center;gap:6px}
#stDiagMsg{max-width:34ch;overflow:hidden;text-overflow:ellipsis;color:var(--muted)}
.out .sys{color:var(--dim);font-style:italic}
.out .ts{color:var(--dim);margin-right:10px;user-select:none}
.out .tx{color:var(--ext-h)}
.out .tx::before{content:"→ ";}
.emptyp{margin:auto;text-align:center;color:var(--dim);padding:20px}
.emptyp svg{width:34px;height:34px;opacity:.5;margin-bottom:6px}
.sendbar{display:flex;gap:8px;padding:8px 12px;border-top:1px solid var(--line)}
.sendbar input{flex:1;background:var(--field);border:1px solid var(--line);border-radius:calc(9px*var(--rr));padding:0 12px;height:32px;outline:none;font-family:var(--mono);font-size:12.5px}
.sendbar input:focus{border-color:rgba(var(--accent-rgb),.5)}
.plotwrap{flex:1;position:relative;min-height:0}
.plotwrap canvas{position:absolute;inset:0;width:100%;height:100%}
.plotwrap canvas{cursor:crosshair;touch-action:none}
.plotwrap canvas.grab{cursor:grabbing}
.legend{display:flex;gap:6px;flex-wrap:wrap;flex:1;min-width:0}
.lg{display:inline-flex;align-items:center;gap:7px;font:500 12px var(--mono);padding:3px 10px 3px 8px;border-radius:calc(20px*var(--rr));border:1px solid transparent;background:rgba(var(--fg),.05);cursor:pointer;user-select:none;transition:opacity .15s,background .15s}
.lg:hover{background:rgba(var(--fg),.09)}
.lg.off{opacity:.42}.lg.off .ln{text-decoration:line-through}
.lg i{width:10px;height:10px;border-radius:calc(3px*var(--rr));flex:none}
.lg b{font-weight:700}
.lg small{color:var(--muted);font:11px var(--mono)}
.ptip{position:absolute;z-index:5;min-width:130px;padding:7px 10px;border-radius:calc(10px*var(--rr));background:var(--panel-solid);border:1px solid var(--line2);box-shadow:var(--shadow);font:12px var(--mono);pointer-events:none}
.ptip[hidden]{display:none}
.ptip .th{color:var(--muted);font:600 11px var(--sans);margin-bottom:4px}
.ptip div:not(.th){display:flex;align-items:center;gap:7px}
.ptip i{width:9px;height:9px;border-radius:calc(3px*var(--rr));flex:none}
.ptip span{flex:1}
.grid-list{flex:1;overflow:auto;padding:12px;display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:10px;align-content:start}
.lib{padding:12px 14px;border-radius:calc(12px*var(--rr));border:1px solid var(--line);background:rgba(var(--fg),.025);display:flex;flex-direction:column;gap:6px;transition:.2s}
.lib:hover{border-color:var(--line2);background:rgba(var(--fg),.045)}
.lib b{font-size:13.5px}
.lib p{margin:0;color:var(--muted);font-size:12px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.lib .meta{display:flex;align-items:center;gap:8px;font-size:11px;color:var(--dim);margin-top:auto}
.lib .meta .spacer{flex:1}
.tag{font:600 10.5px var(--mono);padding:2px 7px;border-radius:calc(6px*var(--rr));background:rgba(var(--ok-rgb),.12);color:var(--ok)}
.check{display:flex;gap:12px;padding:13px 14px;border-radius:calc(12px*var(--rr));border:1px solid var(--line);background:rgba(var(--fg),.025)}
.check .ic{width:30px;height:30px;border-radius:calc(9px*var(--rr));display:grid;place-items:center;flex:none}
.check.ok .ic{background:rgba(var(--ok-rgb),.12);color:var(--ok)}
.check.warn .ic{background:rgba(var(--warn-rgb),.12);color:var(--warn)}
.check.fail .ic{background:rgba(var(--err-rgb),.12);color:var(--err)}
.check b{display:block}
.check p{margin:2px 0 0;color:var(--muted);font-size:12px;word-break:break-word}
.check code{display:inline-block;margin-top:6px;font:12px var(--mono);background:var(--field);padding:3px 8px;border-radius:calc(6px*var(--rr));color:var(--warn-text);cursor:copy}
.plat{padding:14px;border-radius:calc(12px*var(--rr));border:1px solid var(--line);background:rgba(var(--fg),.025);display:flex;gap:12px;align-items:center}
.plat .pic{width:44px;height:44px;border-radius:calc(12px*var(--rr));display:grid;place-items:center;font-weight:800;font-size:11.5px;letter-spacing:-.02em;flex:none}
.plat div:nth-child(2){flex:1;min-width:0}
.plat small{display:block;color:var(--dim);font-family:var(--mono);font-size:11px}

/* ---------- formulaires compacts (réglages des widgets, règles, commandes) ---------- */
.frm{display:grid;grid-template-columns:1fr 1fr;gap:12px 14px;margin-bottom:16px}
.frm .field{margin:0}.frm .full{grid-column:1/-1}
.field select{height:42px;background:var(--field);border:1px solid var(--line2);border-radius:calc(11px*var(--rr));padding:0 12px;outline:none;font-size:14px;width:100%}
.field select option{background:var(--panel-solid);color:var(--text)}
.field select:focus{border-color:var(--accent);box-shadow:0 0 0 4px rgba(var(--accent-rgb),.13)}
.field .chk{display:flex;align-items:center;gap:8px;height:42px;font-weight:500;color:var(--text);font-size:13px}
.field .chk input{width:16px;height:16px;accent-color:var(--accent)}
.modal .warnline{color:var(--err);font-size:12px;min-height:16px;margin:-6px 0 10px}

/* ---------- moniteur : vues, filtre, commandes, règles ---------- */
.pview[data-v=monitor] .ptools{padding:6px 12px;gap:7px}
.ptools.sub{padding:4px 12px;gap:6px;min-height:0}
.segs{display:inline-flex;border:1px solid var(--line2);border-radius:calc(8px*var(--rr));overflow:hidden;flex:none}
.segs button{height:26px;padding:0 11px;border:0;background:none;color:var(--muted);font:600 12px var(--sans);cursor:pointer}
.segs button+button{border-left:1px solid var(--line2)}
.segs button[aria-checked="true"]{background:rgba(var(--accent-rgb),.14);color:var(--accent)}
.segs button:hover{color:var(--text)}
input.mini{height:28px;width:170px;min-width:0;background:var(--field);border:1px solid var(--line);border-radius:calc(8px*var(--rr));padding:0 9px;outline:none;font:12px var(--mono)}
input.mini:focus{border-color:rgba(var(--accent-rgb),.5)}
input.mini.bad{border-color:var(--err)}
input.mini:disabled,.btn:disabled{opacity:.45}
.ptools .fcount{min-width:56px}
.cmdbar{display:flex;align-items:center;gap:6px;padding:5px 12px;border-top:1px solid var(--line);overflow-x:auto;flex:none;scrollbar-width:thin}
.btn.ghost{border-style:dashed;background:none;color:var(--muted)}
.btn.ghost:hover{color:var(--accent);border-color:var(--accent)}
.btn.cmd{font-family:var(--mono);font-weight:500}
mark.mk{background:var(--d-find);color:inherit;border-radius:calc(2px*var(--rr))}
mark.mk.cur{background:var(--d-cur);outline:1px solid var(--accent)}
pre.out{margin:0;white-space:pre;word-break:normal;font-size:12px;color:var(--code)}
.rules{display:grid;gap:8px;max-height:46vh;overflow:auto}
.rrow{display:grid;grid-template-columns:minmax(0,1fr) 120px auto 34px;gap:8px;align-items:center}
.rrow input[data-k=kw],.rrow select{height:36px;background:var(--field);border:1px solid var(--line2);border-radius:calc(9px*var(--rr));padding:0 10px;outline:none;font:13px var(--mono);width:100%}
.rrow select{font-family:var(--sans);font-weight:600}
.rrow .chk{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted);white-space:nowrap}
.rrow select option{background:var(--panel-solid);color:var(--text)}

.ex-h{grid-column:1/-1;display:flex;align-items:center;gap:9px;padding:8px 2px 0;font-size:13px}
.ex-h:first-child{padding-top:0}
.sel[hidden],.btn[hidden]{display:none}
.ptab-body{flex:1;overflow:auto;padding:10px 12px}
.ptable{width:100%;border-collapse:collapse;font-size:12.5px}
.ptable th{text-align:left;font:700 10.5px var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);padding:4px 10px 8px;border-bottom:1px solid var(--line)}
.ptable td{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
.ptable tr.on td{background:rgba(var(--accent-rgb),.06)}
.ptable td small{display:block;margin-top:2px;font-size:11px}
.ptable td>.btn{display:flex;width:max-content;margin-top:6px}
.toolbar.has-prof .btn .kbd{display:none}
.toolbar.has-prof .sel select{max-width:160px}
.toolbar.has-prof #profileSel{max-width:118px}
.ptable .mono{font-family:var(--mono);font-size:12px}
.ptable .ok{color:var(--ok)}.ptable .ko{color:var(--err)}.ptable .warnc{color:var(--warn)}
.ptable .ok svg,.ptable .ko svg{width:13px;height:13px;vertical-align:-2px}
.mb{display:inline-block;width:54px;height:6px;border-radius:calc(6px*var(--rr));background:rgba(var(--fg),.1);vertical-align:middle;margin-right:7px;overflow:hidden}
.mb i{display:block;height:100%;background:var(--grad);border-radius:calc(6px*var(--rr))}.mb i.warn{background:var(--warn)}.mb i.crit{background:var(--err)}
.spin{display:inline-block;width:11px;height:11px;border:2px solid rgba(var(--fg),.2);border-top-color:var(--accent);border-radius:50%;animation:spin 1s linear infinite;vertical-align:-2px}
pre.snip{text-align:left;font:12px/1.5 var(--mono);background:var(--field);border:1px solid var(--line);border-radius:calc(10px*var(--rr));padding:10px 14px;margin:10px 0 0;color:var(--code);white-space:pre}
/* ---------- inspecteur à onglets ---------- */
.itabs{display:flex;gap:2px;padding:3px;border-radius:calc(11px*var(--rr));background:var(--field2);border:1px solid var(--line);flex:none}
.itabs button{flex:1;height:28px;border:0;border-radius:calc(8px*var(--rr));background:none;color:var(--muted);cursor:pointer;font:600 12px var(--sans);white-space:nowrap}
.itabs button:hover{color:var(--text)}
.itabs button.active{background:var(--panel-solid);color:var(--accent);box-shadow:0 1px 4px rgba(var(--shade-rgb),.25)}
.ipane{display:none;flex-direction:column;gap:10px;min-height:0}
.ipane.active{display:flex}
.sharerow{display:flex;gap:8px;flex-wrap:wrap}

/* ---------- instantanés ---------- */
.snapauto{margin:12px 0 4px;white-space:normal;align-items:flex-start;line-height:1.35}
.snapauto i{flex:none;margin-top:1px}
.snapauto span{display:inline!important}
.snapst{font-size:11.5px;margin:8px 0 10px}.snapst.dirty{color:var(--warn)}
.snaplist{display:grid;gap:8px}
.snap{padding:9px 10px;border-radius:calc(10px*var(--rr));background:rgba(var(--fg),.03);border:1px solid var(--line)}
.snap b{font-size:12.5px;word-break:break-word}
.snap-m{font-size:11px;color:var(--dim);margin:2px 0 7px}
.snap-m code{font-family:var(--mono)}
.snap-a{display:flex;gap:6px}
.tag.auto{background:rgba(var(--accent2-rgb),.15);color:var(--ext-h)}
.modal.diff{width:min(940px,96vw);max-height:82vh;display:flex;flex-direction:column}
.diffbody{overflow:auto;flex:1;min-height:80px;border:1px solid var(--line);border-radius:calc(10px*var(--rr));background:var(--field)}
.df{border-bottom:1px solid var(--line)}
.df h4{margin:0;padding:8px 12px;font:600 12px var(--mono);background:var(--panel-solid);position:sticky;top:0;border-bottom:1px solid var(--line)}
.df pre{margin:0;padding:6px 0;font:12px/1.5 var(--mono);white-space:pre;overflow-x:auto}
.df pre span{display:block;padding:0 12px;min-width:max-content}
.df .a{background:rgba(var(--ok-rgb),.15)}.df .d{background:rgba(var(--err-rgb),.15)}.df .h{color:var(--accent3);background:rgba(var(--accent3-rgb),.08)}
.dl-a{color:var(--ok);font-weight:700}.dl-d{color:var(--err);font-weight:700}
/* ---------- barre d'état ---------- */
.status{display:flex;align-items:center;gap:16px;padding:0 6px;font-size:11.5px;color:var(--dim);white-space:nowrap;overflow:hidden}
.status span{display:flex;align-items:center;gap:6px}
.status .dot{width:7px;height:7px}
.status b{color:var(--muted);font-weight:500}

/* ---------- toasts, modales, palette ---------- */
.toasts{position:fixed;right:18px;bottom:44px;display:flex;flex-direction:column;gap:8px;z-index:50;pointer-events:none}
.toast{pointer-events:auto;display:flex;align-items:center;gap:10px;min-width:260px;max-width:420px;padding:11px 14px;border-radius:calc(12px*var(--rr));background:rgba(var(--panel-rgb),.92);backdrop-filter:blur(calc(var(--glass-blur)*.73));border:1px solid var(--line2);box-shadow:var(--shadow);animation:tin .35s cubic-bezier(.2,1.4,.4,1);font-weight:500}
.toast.out{animation:tout .25s ease forwards}
.toast .ti{width:26px;height:26px;border-radius:calc(8px*var(--rr));display:grid;place-items:center;flex:none;background:rgba(var(--accent3-rgb),.14);color:var(--accent3)}
.toast.ok .ti{background:rgba(var(--ok-rgb),.14);color:var(--ok)}
.toast.error .ti{background:rgba(var(--err-rgb),.14);color:var(--err)}
.toast.warn .ti{background:rgba(var(--warn-rgb),.14);color:var(--warn)}
@keyframes tin{from{transform:translateX(30px);opacity:0}}
@keyframes tout{to{transform:translateX(30px);opacity:0}}
.overlay{position:fixed;inset:0;z-index:60;background:rgba(var(--scrim-rgb),.55);backdrop-filter:blur(calc(var(--glass-blur)*.27));display:flex;align-items:flex-start;justify-content:center;padding-top:12vh;animation:fade .2s}
@keyframes fade{from{opacity:0}}
.modal{width:min(620px,92vw);padding:22px;animation:pop .25s cubic-bezier(.2,1.3,.4,1);background:rgba(var(--panel-rgb),.95)}
.modal h2{margin:0 0 4px;font-size:19px;letter-spacing:-.02em}
.modal .sub{color:var(--muted);margin:0 0 18px}
.field{display:grid;gap:6px;margin-bottom:16px}
.field label{font-size:12px;color:var(--muted);font-weight:600}
.field input{height:42px;background:var(--field);border:1px solid var(--line2);border-radius:calc(11px*var(--rr));padding:0 14px;outline:none;font-size:15px;transition:.2s}
.field input:focus{border-color:var(--accent);box-shadow:0 0 0 4px rgba(var(--accent-rgb),.13)}
.field .hint{font-size:11.5px;color:var(--err);min-height:16px}
.tpls{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:20px}
.tpl{font:inherit;color:inherit;padding:14px 12px;border-radius:calc(12px*var(--rr));border:1px solid var(--line2);background:rgba(var(--fg),.03);cursor:pointer;transition:.2s;text-align:left}
.tpl:hover{transform:translateY(-2px);border-color:rgba(var(--fg),.2)}
.tpl.active{border-color:var(--accent);background:rgba(var(--accent-rgb),.09);box-shadow:0 0 0 3px rgba(var(--accent-rgb),.12)}
.tpl .te{font-size:22px;margin-bottom:8px;display:block}
.tpl b{display:block;font-size:13px}
.tpl small{color:var(--muted);font-size:11.5px}
.mactions{display:flex;justify-content:flex-end;gap:10px}
.modal.help{width:min(720px,94vw);max-height:78vh;overflow:auto}
.helpgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:6px 28px}
.helpgrid h4{margin:14px 0 8px;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
.palette{width:min(600px,92vw);padding:0;overflow:hidden;animation:pop .2s cubic-bezier(.2,1.3,.4,1);background:rgba(var(--panel-rgb),.96)}
.palette input{width:100%;height:56px;border:0;border-bottom:1px solid var(--line);background:transparent;padding:0 20px 0 50px;font-size:16px;outline:none}
.palette .pw{position:relative}
.palette .pw svg{position:absolute;left:18px;top:50%;transform:translateY(-50%);width:18px;height:18px;color:var(--muted)}
.palette ul{list-style:none;margin:0;padding:6px;max-height:380px;overflow:auto}
.palette li{display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:calc(10px*var(--rr));cursor:pointer;color:var(--muted)}
.palette li.sel{background:linear-gradient(90deg,rgba(var(--accent-rgb),.16),rgba(var(--accent2-rgb),.08));color:var(--text)}
.palette li.sel svg{color:var(--accent)}
.palette li span{flex:1}
.particle{position:fixed;width:7px;height:7px;border-radius:calc(2px*var(--rr));pointer-events:none;z-index:70;animation:burst .9s cubic-bezier(.1,.8,.3,1) forwards}
@keyframes burst{to{transform:translate(var(--dx),var(--dy)) rotate(var(--r));opacity:0}}
.flash-ok{animation:flashok 1s ease}
@keyframes flashok{0%{box-shadow:0 0 0 0 rgba(var(--ok-rgb),.7)}100%{box-shadow:0 0 0 18px rgba(var(--ok-rgb),0)}}

/* ---------- repli des colonnes (grands écrans) et tiroirs (petits écrans) ---------- */
.scrim{display:none;position:fixed;inset:0;z-index:38;background:rgba(var(--scrim-rgb),.5);backdrop-filter:blur(calc(var(--glass-blur)*.14))}
.pathbox{display:block;font-family:var(--mono);color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
/* densité */
:root[data-dens="compact"]{--dens:.86}
:root[data-dens="aere"]{--dens:1.16}
.btn{height:calc(36px*var(--dens))}
.btn.sm{height:calc(28px*var(--dens))}
.sel{height:calc(36px*var(--dens))}
.projects li{padding:calc(8px*var(--dens)) 10px}
.card{padding:calc(14px*var(--dens)) 16px}
.ptab{padding:calc(6px*var(--dens)) 12px}
.lib{padding:calc(12px*var(--dens)) 14px}
.hist div{padding:calc(7px*var(--dens)) 9px}
@media (min-width:901px){
  .app.nosb{grid-template-columns:minmax(0,1fr)}
  .app.nosb .sidebar{display:none}
}
@media (min-width:1181px){
  .content.noinsp{grid-template-columns:minmax(0,1fr)}
  .content.noinsp .inspector{display:none}
}
@media (max-width:1380px){.btn .kbd{display:none}.switch span{display:none}.ptitle b{max-width:140px}.toolbar{gap:9px}}
@media (max-width:1180px){
  .sel select{max-width:110px}.ptitle b{max-width:90px}
  .hide-md,#btnVerify .lbl,.ptab svg,.jc span{display:none!important}
  .jobbar,.jobbar.single{flex-basis:180px}
  .ptab{padding:6px 9px}.toolbar{gap:8px}
  .content{grid-template-columns:minmax(0,1fr)}
  .inspector{position:fixed;top:10px;right:10px;bottom:10px;width:min(340px,92vw);z-index:40;padding:10px;border-radius:var(--radius);background:var(--bg2);border:1px solid var(--line2);box-shadow:var(--shadow);transform:translateX(calc(100% + 24px));visibility:hidden;transition:transform .25s ease,visibility 0s .25s}
  .inspector.drawer{transform:none;visibility:visible;transition:transform .25s ease}
  body.drawer-open .scrim{display:block}
}
@media (max-width:900px){
  .app{grid-template-columns:minmax(0,1fr)}
  .sidebar{position:fixed;top:10px;left:10px;bottom:10px;width:min(290px,90vw);z-index:40;background:var(--bg2);transform:translateX(calc(-100% - 24px));visibility:hidden;transition:transform .25s ease,visibility 0s .25s}
  .sidebar.drawer{transform:none;visibility:visible;transition:transform .25s ease}
  .hide-sm{display:none!important}
}

/* ================= modes : décor, détails, animations ================= */
.bg::before{content:"";position:absolute;inset:0;background-image:var(--deco-img);background-size:var(--deco-size);background-position:var(--deco-pos);background-repeat:var(--deco-rep);opacity:var(--deco-op)}
.bg::after{background-image:var(--dots)}
body::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:50;background:var(--overlay)}
:root[data-fx="off"][data-mode][data-theme]{--deco-img:none;--overlay:none;--blob:0;--dots:none}
.brand b,.ptitle b,.welcome h1,.modal h2,.card h3,.side-sec{font-family:var(--font-head)}
@keyframes blink{50%{opacity:0}}
:root[data-motion="reduced"] *,:root[data-motion="reduced"] *::before,:root[data-motion="reduced"] *::after{animation-duration:.001ms!important;animation-iteration-count:1!important;animation-delay:0s!important;transition-duration:.001ms!important;scroll-behavior:auto!important}
:root.morph *,:root.morph *::before,:root.morph *::after{transition:background-color .4s ease,color .4s ease,border-color .4s ease,box-shadow .4s ease,fill .4s ease,stroke .4s ease,border-radius .4s ease,opacity .4s ease!important}
/* illustrations */
.wart{display:none}
html[data-art] .wart{display:block;width:min(320px,70%);height:132px;margin:0 auto 12px;background:var(--art-welcome) center/contain no-repeat}
html[data-art] .mem-empty::before{content:"";display:block;height:46px;margin:0 auto 6px;background:var(--art-empty) center/contain no-repeat}
html[data-art] #hist>.dim::before{content:"";flex:none;width:52px;height:36px;background:var(--art-empty) center/contain no-repeat}
html[data-art] .toast.ok .ti,html[data-art] .toast.error .ti{background-size:82%;background-position:center;background-repeat:no-repeat}
html[data-art] .toast.ok .ti{background-image:var(--art-ok)}
html[data-art] .toast.error .ti{background-image:var(--art-err)}
html[data-art] .toast.ok .ti svg,html[data-art] .toast.error .ti svg{opacity:0}
/* sélecteur « Apparence » */
.overlay:has(>.look){padding-top:3vh}
.modal.look{width:min(940px,94vw);max-height:94vh;overflow:auto}
.mgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(164px,1fr));gap:8px;margin:10px 0 4px}
.mthumb{font:inherit;color:inherit;background:none;border:2px solid transparent;border-radius:calc(16px*var(--rr));padding:6px;text-align:left;cursor:pointer;display:grid;gap:6px;transition:border-color .2s,background .2s,transform .2s}
.mthumb:hover{border-color:var(--line2);transform:translateY(-2px)}
.mthumb[aria-checked="true"]{border-color:var(--accent);background:rgba(var(--accent-rgb),.09)}
.mthumb b{font-size:13px;padding:0 4px}
.mthumb small{color:var(--muted);font-size:11px;line-height:1.3;padding:0 4px 2px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.mprev{position:relative;height:108px;display:grid;grid-template-columns:32% 1fr;background:var(--bg);color:var(--text);font:10.5px/1.35 var(--sans);border:var(--bw) solid var(--line2);border-radius:calc(12px*var(--rr));overflow:hidden;isolation:isolate;pointer-events:none}
.mprev::before{content:"";position:absolute;inset:0;z-index:-1;background-image:var(--deco-img);background-size:var(--deco-size);background-position:var(--deco-pos);background-repeat:var(--deco-rep);opacity:var(--deco-op)}
:root[data-fx="off"] .mprev::before{display:none}
.mp-side{background:var(--panel);border-right:1px solid var(--line);padding:8px;display:grid;align-content:start;gap:5px}
.mp-logo{width:16px;height:16px;border-radius:calc(5px*var(--rr));background:var(--grad);margin-bottom:3px}
.mp-li{height:9px;border-radius:calc(4px*var(--rr));background:rgba(var(--fg),.13)}
.mp-li.on{background:rgba(var(--accent-rgb),.42)}
.mp-main{display:grid;grid-template-rows:auto 1fr auto;gap:5px;padding:6px;min-width:0}
.mp-bar{display:flex;gap:5px;align-items:center;background:var(--panel);border:1px solid var(--line);border-radius:calc(7px*var(--rr));padding:3px 6px}
.mp-bar b{font:700 10.5px var(--font-head);flex:1;white-space:nowrap}
.mp-btn{width:30px;height:11px;border-radius:calc(5px*var(--rr));background:var(--grad-btn)}
.mp-code{background:var(--panel);border:1px solid var(--line);border-radius:calc(7px*var(--rr));padding:5px 7px;font:10px/1.4 var(--mono);color:var(--code);white-space:nowrap;overflow:hidden}
.mp-code .k{color:var(--tk-k)}.mp-code .f{color:var(--tk-f)}.mp-code .n{color:var(--tk-n)}.mp-code .c{color:var(--tk-c)}.mp-code .s{color:var(--tk-s)}
.mp-con{background:var(--panel-solid);border:1px solid var(--line);border-radius:calc(6px*var(--rr));padding:3px 6px;font:9.5px var(--mono);color:var(--ok);white-space:nowrap;overflow:hidden}
.lookrow{display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:7px 0;border-top:1px solid var(--line)}
.lookrow>b{min-width:150px;font-size:13px}
.lookrow small{color:var(--muted);font-size:12px;flex:1 1 220px}
.lookrow .seg{max-width:340px;flex:1 1 260px}
.lookrow .seg button{font:600 12.5px var(--sans)}
.fsz{display:flex;align-items:center;gap:8px;font:600 13px var(--mono)}
/* animations de réussite */
.cele{position:fixed;inset:0;z-index:80;pointer-events:none;overflow:hidden}
.cele-hk{animation:celeout .4s 2.3s forwards}
@keyframes celeout{to{opacity:0}}
.ag{position:absolute;left:50%;top:40%;transform:translate(-50%,-50%);font:800 clamp(26px,6vw,62px)/1 var(--mono);letter-spacing:.12em;color:var(--accent);background:rgba(var(--scrim-rgb),.86);border:2px solid var(--accent);padding:.35em .6em;text-shadow:0 0 16px rgba(var(--accent-rgb),.85);white-space:nowrap;animation:aglitch .18s 1.2s 4 steps(2)}
.ag span{opacity:0;animation:cin .01s forwards;animation-delay:calc(var(--i)*60ms)}
.ag::after{content:"█";animation:blink .6s steps(1) infinite}
.agsub{position:absolute;left:50%;top:calc(40% + clamp(34px,5vw,58px));transform:translateX(-50%);font:600 13px var(--mono);color:var(--muted);background:rgba(var(--scrim-rgb),.86);padding:2px 10px;border:1px solid var(--line2)}
@keyframes cin{to{opacity:1}}
@keyframes aglitch{0%{transform:translate(-50%,-50%)}50%{transform:translate(calc(-50% + 4px),calc(-50% - 2px));filter:hue-rotate(60deg)}}
.petal{position:absolute;top:-30px;width:13px;height:18px;border-radius:70% 0 70% 0;background:var(--c);opacity:.9;animation:pfall var(--d) var(--dl) cubic-bezier(.3,.2,.6,1) forwards}
@keyframes pfall{0%{transform:translate(0,0) rotate(0)}50%{transform:translate(calc(var(--sw)*-.5),52vh) rotate(260deg)}100%{transform:translate(var(--sw),112vh) rotate(560deg);opacity:.55}}
.kstar{position:fixed;width:var(--z);height:var(--z);background:var(--c);clip-path:polygon(50% 0,61% 39%,100% 50%,61% 61%,50% 100%,39% 61%,0 50%,39% 39%);animation:kfly 1.5s ease-out forwards}
@keyframes kfly{0%{transform:translate(0,0) scale(.2) rotate(0);opacity:1}70%{opacity:1}100%{transform:translate(var(--dx),var(--dy)) scale(1) rotate(200deg);opacity:0}}
.kbub{position:fixed;transform:translate(-50%,-120%);padding:7px 14px;border-radius:999px;background:var(--panel-solid);color:var(--text);border:2px solid var(--accent);font:700 13px var(--font-head);box-shadow:var(--shadow);animation:kbub 2.2s ease forwards;white-space:nowrap}
@keyframes kbub{0%{transform:translate(-50%,-90%) scale(.4);opacity:0}15%{transform:translate(-50%,-130%) scale(1.1);opacity:1}25%{transform:translate(-50%,-125%) scale(1)}85%{opacity:1}100%{transform:translate(-50%,-160%);opacity:0}}
.sring{position:fixed;width:20px;height:20px;margin:-10px;border-radius:50%;border:2px solid var(--accent);box-shadow:0 0 18px var(--accent),inset 0 0 12px var(--accent2);animation:sring 1.6s ease-out forwards}
@keyframes sring{to{transform:scale(34);opacity:0}}
.sscan{position:absolute;left:0;right:0;top:0;height:3px;background:linear-gradient(90deg,transparent,var(--accent),var(--accent2),transparent);box-shadow:0 0 22px var(--accent);animation:sscan 1.4s ease-in forwards}
@keyframes sscan{to{transform:translateY(100vh);opacity:.2}}
.stxt{position:absolute;left:50%;top:42%;transform:translate(-50%,-50%);font:800 clamp(22px,4.6vw,46px)/1 var(--font-head);letter-spacing:.14em;background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent;filter:drop-shadow(0 0 14px rgba(var(--accent-rgb),.7));animation:stxt 2.2s ease forwards;white-space:nowrap}
@keyframes stxt{0%{opacity:0;transform:translate(-50%,-50%) scale(.7)}18%{opacity:1;transform:translate(-50%,-50%) scale(1)}80%{opacity:1}100%{opacity:0;transform:translate(-50%,-50%) scale(1.08)}}
.stamp{position:absolute;left:50%;top:44%;padding:.25em .7em;border:4px double var(--accent2);color:var(--accent2);font:700 clamp(28px,5vw,52px)/1 var(--font-head);letter-spacing:.06em;text-transform:uppercase;transform:translate(-50%,-50%) rotate(-8deg);opacity:0;animation:stamp 2.3s ease forwards;background:rgba(var(--panel-rgb),.6)}
@keyframes stamp{0%{opacity:0;transform:translate(-50%,-50%) rotate(-8deg) scale(2.4)}14%{opacity:.95;transform:translate(-50%,-50%) rotate(-8deg) scale(1)}80%{opacity:.95}100%{opacity:0}}
.hcban{position:fixed;left:50%;bottom:64px;transform:translateX(-50%);padding:14px 26px;background:var(--panel-solid);color:var(--text);border:3px solid var(--accent);font:700 18px var(--sans)}
/* ---- Hacker (Phosphore + Cyberpunk) ---- */
:root[data-mode^="hacker"] input,:root[data-mode^="hacker"] textarea{caret-shape:block}
:root[data-mode^="hacker"] .btn.primary{border:1px solid var(--accent);box-shadow:none;text-shadow:0 0 8px rgba(var(--accent-rgb),.7)}
:root[data-mode^="hacker"] .btn.primary::after{display:none}
:root[data-mode^="hacker"] .brand b,:root[data-mode^="hacker"] .ptitle b,:root[data-mode^="hacker"] .card h3{text-shadow:0 0 8px rgba(var(--accent-rgb),.45)}
:root[data-mode^="hacker"] .welcome h1{background:none;color:var(--accent);-webkit-background-clip:border-box;background-clip:border-box;font-size:34px;letter-spacing:.02em;text-shadow:0 0 14px rgba(var(--accent-rgb),.6)}
:root[data-mode^="hacker"] .welcome h1::after{content:"█";margin-left:6px;animation:blink 1s steps(1) infinite}
:root[data-mode^="hacker"] #console .l::before{content:"> ";color:var(--accent);opacity:.75}
:root[data-mode^="hacker"] #console::after{content:"█";color:var(--accent);animation:blink 1s steps(1) infinite}
:root[data-mode^="hacker"] .projects li.active{background:rgba(var(--accent-rgb),.14);border-left:2px solid var(--accent)}
:root[data-mode^="hacker"] .projects .pi{background:none;border:1px solid var(--line2)}
:root[data-mode^="hacker"] .projects li.active .pi{background:var(--accent);color:var(--on-accent)}
:root[data-mode^="hacker"] body::after{animation:flick calc(6s*var(--spd)) steps(1) infinite}
@keyframes flick{0%,100%{opacity:1}92%{opacity:.86}94%{opacity:1}97%{opacity:.92}}
:root[data-mode="hacker2"] .glass{position:relative}
:root[data-mode="hacker2"] .glass::before,:root[data-mode="hacker2"] .glass::after{content:"";position:absolute;width:11px;height:11px;pointer-events:none;z-index:2;border:2px solid var(--accent2);opacity:.9}
:root[data-mode="hacker2"] .glass::before{left:-1px;top:-1px;border-right:0;border-bottom:0}
:root[data-mode="hacker2"] .glass::after{right:-1px;bottom:-1px;border-left:0;border-top:0}
:root[data-mode="hacker2"] .status{background:var(--accent);color:var(--on-accent);padding:2px 10px;font-weight:600}
:root[data-mode="hacker2"] .status .tinybtn{color:var(--on-accent)}
:root[data-mode="hacker2"] .status span,:root[data-mode="hacker2"] .status b{color:inherit}
/* ---- Fleur ---- */
:root[data-mode^="fleur"] .welcome h1{background:none;color:var(--text);-webkit-background-clip:border-box;background-clip:border-box;font-weight:700;font-size:50px;letter-spacing:-.01em}
:root[data-mode^="fleur"] .btn.primary{box-shadow:0 8px 20px -10px rgba(var(--accent2-rgb),.7)}
:root[data-mode^="fleur"] .card h3,:root[data-mode^="fleur"] .side-sec{text-transform:none;letter-spacing:.01em;font-size:13px;font-weight:700}
:root[data-mode^="fleur"] .brand b{font-weight:700;font-size:19px}
/* ---- Kawaii ---- */
:root[data-mode^="kawaii"] .btn{font-weight:700}
:root[data-mode^="kawaii"] .btn:hover{transform:translateY(-2px) scale(1.03)}
:root[data-mode^="kawaii"] .btn.primary{box-shadow:0 5px 0 -1px rgba(var(--accent2-rgb),.45),0 10px 18px -8px rgba(var(--accent-rgb),.5)}
:root[data-mode^="kawaii"] .welcome h1{font-size:54px;font-weight:700}
:root[data-mode^="kawaii"] .card h3,:root[data-mode^="kawaii"] .side-sec{text-transform:none;letter-spacing:.02em;font-size:13px}
:root[data-mode^="kawaii"] .brand b{font-size:19px}
:root[data-mode^="kawaii"] .brand b,:root[data-mode^="kawaii"] .welcome h1{background:none;color:var(--accent);-webkit-background-clip:border-box;background-clip:border-box}
/* ---- Synthwave ---- */
:root[data-mode="synthwave"] .btn.primary{box-shadow:0 0 22px rgba(var(--accent-rgb),.6),0 0 44px -6px rgba(var(--accent2-rgb),.45)}
:root[data-mode="synthwave"] .glass{border-color:rgba(var(--accent-rgb),.32)}
:root[data-mode="synthwave"] .welcome h1{filter:drop-shadow(0 0 16px rgba(var(--accent-rgb),.6));letter-spacing:.06em;font-size:46px}
:root[data-mode="synthwave"] .brand b,:root[data-mode="synthwave"] .ptitle b{text-shadow:0 0 10px rgba(var(--accent-rgb),.65);letter-spacing:.04em}
:root[data-mode="synthwave"] .card h3{color:var(--accent2);text-shadow:0 0 8px rgba(var(--accent2-rgb),.55)}
:root[data-mode="synthwave"] .editor-card:focus-within{box-shadow:0 0 26px -6px rgba(var(--accent-rgb),.55)}
/* ---- Papier ---- */
:root[data-mode="papier"] .btn.primary{box-shadow:none}
:root[data-mode="papier"] .btn.primary::after{display:none}
:root[data-mode="papier"] .welcome h1{background:none;color:var(--text);-webkit-background-clip:border-box;background-clip:border-box;font-size:64px;font-weight:700;letter-spacing:0}
:root[data-mode="papier"] .brand b{font-size:24px;font-weight:700}
:root[data-mode="papier"] .gutter{border-right:2px solid rgba(var(--accent2-rgb),.55)}
:root[data-mode="papier"] textarea.ta{background-image:repeating-linear-gradient(to bottom,transparent 0,transparent calc(var(--lh) - 1px),rgba(var(--accent3-rgb),.20) calc(var(--lh) - 1px),rgba(var(--accent3-rgb),.20) var(--lh));background-position:0 12px;background-attachment:local}
:root[data-mode="papier"] .card h3{text-transform:none;letter-spacing:.01em;font-size:17px}
:root[data-mode="papier"] .glass{box-shadow:var(--shadow)}
/* ---- Contraste élevé ---- */
:root[data-mode="contraste"] :is(.glass,.btn:not(.primary),.sel,.search input,.field input,.field select,.ftab,.ptab,.pill,.lg,.tpl,.recent button,.lib,.check,.plat,.dw,.seg button,.themeseg,.kbd,input.mini,.sendbar input){border-width:2px}
:root[data-mode="contraste"] :focus-visible{outline:3px solid var(--accent);outline-offset:2px}
:root[data-mode="contraste"] .btn.primary::after{display:none}
:root[data-mode="contraste"] .btn.primary{box-shadow:none;border:2px solid var(--paper)}
:root[data-mode="contraste"] .welcome h1{background:none;color:var(--accent);-webkit-background-clip:border-box;background-clip:border-box}
:root[data-mode="contraste"] .ptab.active,:root[data-mode="contraste"] .ftab.active{outline:2px solid var(--accent);outline-offset:-2px}
:root[data-mode="contraste"] a{text-decoration:underline}

/* ================= Forge Code : éléments propres à l'atelier multi-langages ================= */
.lchip{font:800 9.5px var(--mono);letter-spacing:-.02em;padding:2px 5px;border-radius:calc(5px*var(--rr));background:var(--lc,var(--dim));color:var(--lct,var(--ink));flex:none;min-width:22px;text-align:center}
#langSel{max-width:170px}
.board .chip{font:800 13px var(--mono);letter-spacing:-.03em;background:var(--lc,rgba(var(--fg),.06));color:var(--lct,var(--muted))}
.board .chip.off{background:rgba(var(--fg),.05);color:var(--dim)}
.langacts{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.langacts:empty{display:none}
.projects .pi{background:var(--lc,rgba(var(--fg),.05));color:var(--lct,var(--accent));font:800 10px var(--mono);letter-spacing:-.03em}
.projects li.active .pi{background:var(--lc,var(--grad-btn));color:var(--lct,var(--on-grad));box-shadow:0 0 0 2px rgba(var(--accent-rgb),.35)}
:root[data-mode^="hacker"] .projects .pi{background:none;color:var(--lc,var(--accent))}
/* arbre des fichiers */
.tree{display:grid;gap:1px;max-height:300px;overflow:auto;margin:-4px -6px 0;font-size:12.5px}
.tree .tn{display:flex;align-items:center;gap:7px;padding:4px 8px;border-radius:calc(7px*var(--rr));cursor:pointer;color:var(--muted);white-space:nowrap;min-width:0;border:0;background:none;text-align:left;font:inherit;width:100%}
.tree .tn:hover{background:var(--panel2);color:var(--text)}
.tree .tn.open{color:var(--text)}
.tree .tn.cur{background:rgba(var(--accent-rgb),.12);color:var(--text)}
.tree .tn.dir{color:var(--dim);font-weight:600;cursor:default}
.tree .tn span.nm{overflow:hidden;text-overflow:ellipsis;flex:1}
.tree .tn .ext{font:600 9px var(--mono);padding:1px 4px;border-radius:calc(4px*var(--rr));background:rgba(var(--fg),.08);color:var(--muted);min-width:24px;text-align:center;flex:none}
.tree .tn .ext.l{background:rgba(var(--accent-rgb),.14);color:var(--accent)}
.tree .tn .star{color:var(--warn);font-size:11px;flex:none}
.tree .tn .errc{font:700 10px var(--mono);color:var(--on-err);background:var(--err);border-radius:calc(8px*var(--rr));padding:0 5px}
.tree .empty{color:var(--dim);padding:6px 8px}
/* onglets de fichiers ouverts */
.ftab .x{width:16px;height:16px;border-radius:calc(4px*var(--rr));display:grid;place-items:center;opacity:0;color:var(--dim);margin-right:-4px}
.ftab:hover .x,.ftab.active .x{opacity:.75}
.ftab .x:hover{opacity:1;background:rgba(var(--fg),.12);color:var(--text)}
.ftab .x svg{width:11px;height:11px}
.ftab.dirty .x{display:none}
.ftab .mstar{color:var(--warn);font-size:10px}
.noedit{position:absolute;inset:0;z-index:4;display:flex;align-items:center;justify-content:center;text-align:center;padding:30px;color:var(--muted);background:var(--panel-solid)}
.noedit[hidden]{display:none}
/* champs de l'inspecteur */
.field.sm{margin-bottom:10px;gap:4px}
.field.sm label{font-size:11px}
.field.sm input,.field.sm textarea{height:32px;font:12.5px var(--mono);border-radius:calc(9px*var(--rr));padding:0 10px}
.field textarea{background:var(--field);border:1px solid var(--line2);border-radius:calc(11px*var(--rr));padding:8px 12px;outline:none;resize:vertical;min-height:32px;font:13px var(--mono);color:var(--text)}
.field.sm textarea{height:auto;padding:6px 10px;min-height:44px}
.field textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(var(--accent-rgb),.13)}
.switch span{white-space:normal;line-height:1.3}
/* accueil : langages installés */
.wlangs{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;max-width:720px;margin-top:26px}
.wlangs button{display:inline-flex;align-items:center;gap:8px;padding:6px 12px 6px 6px;border-radius:calc(20px*var(--rr));border:1px solid var(--line2);background:rgba(var(--fg),.03);cursor:pointer;font:600 12.5px var(--sans);color:var(--text);transition:.2s}
.wlangs button:hover{border-color:rgba(var(--accent-rgb),.5);transform:translateY(-2px)}
.wlangs .lchip{font-size:9px}
.wlangs small{display:block;width:100%;text-align:center;color:var(--dim);font-size:11.5px;margin-bottom:-2px}
/* structure du fichier */
.outline{display:grid;gap:1px;max-height:calc(100vh - 260px);overflow:auto;margin:-4px -6px 0}
.outline button{display:flex;align-items:center;gap:8px;border:0;background:none;padding:4px 8px;border-radius:calc(7px*var(--rr));cursor:pointer;color:var(--text);font:12.5px var(--mono);text-align:left;min-width:0}
.outline button:hover{background:var(--panel2)}
.outline button.cur{background:rgba(var(--accent-rgb),.12)}
.outline i{font:700 9px var(--sans);font-style:normal;min-width:32px;text-align:center;padding:1px 4px;border-radius:calc(4px*var(--rr));background:rgba(var(--accent2-rgb),.15);color:var(--ext-h)}
.outline i.fn{background:rgba(var(--accent-rgb),.13);color:var(--accent)}
.outline span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}
.outline small{color:var(--dim);font-size:10.5px}
/* terminal */
.tstate{display:flex;align-items:center;gap:8px;font-weight:600;font-size:12px;color:var(--muted);min-width:0;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.tstate #tLbl{overflow:hidden;text-overflow:ellipsis}
.dot.run{background:var(--accent);box-shadow:0 0 0 0 rgba(var(--accent-rgb),.6);animation:pulse2 1.6s infinite}
@keyframes pulse2{70%{box-shadow:0 0 0 7px rgba(var(--accent-rgb),0)}100%{box-shadow:0 0 0 0 rgba(var(--accent-rgb),0)}}
.dot.ko{background:var(--err)}
.out.term{white-space:pre-wrap;word-break:break-all;font-size:12.8px;line-height:1.5;color:var(--code)}
.out.term .l{min-height:1.5em}
.out.term .l.cur::after{content:"";display:inline-block;width:.55em;height:1.05em;vertical-align:-.15em;background:var(--caret);opacity:.55;animation:blink 1.1s steps(1) infinite}
.term .cmd{color:var(--accent3);margin-top:4px}
.term .cmd::before{content:"";}
.term .web{color:var(--ext-h)}
.term .end{color:var(--dim);font-style:italic;border-top:1px dashed var(--line2);margin:6px 0 2px;padding-top:4px}
.term .end.ko{color:var(--err)}
.term .end.okk{color:var(--ok)}
.term .a-b{font-weight:700}.term .a-i{font-style:italic}.term .a-u{text-decoration:underline}.term .a-d{opacity:.65}
.sendbar .prompt{color:var(--accent);font:700 14px var(--mono);align-self:center}
.sendbar input:disabled{opacity:.55}
:root[data-mode^="hacker"] #term .l.sys::before{content:"> ";color:var(--accent);opacity:.75}
/* cartes d'extensions */
.xcard{padding:13px 14px;border-radius:calc(12px*var(--rr));border:1px solid var(--line);background:rgba(var(--fg),.025);display:flex;flex-direction:column;gap:8px;transition:.2s;min-width:0}
.xcard:hover{border-color:var(--line2);background:rgba(var(--fg),.045)}
.xcard.off{opacity:.62}
.xhead{display:flex;gap:11px;align-items:center;min-width:0}
.xhead .pic{width:40px;height:40px;border-radius:calc(11px*var(--rr));display:grid;place-items:center;font:800 11px var(--mono);letter-spacing:-.03em;flex:none;background:var(--lc);color:var(--lct)}
.xhead b{display:block;font-size:13.5px}
.xhead small{display:block;color:var(--dim);font:11px var(--mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.xcard p{margin:0;color:var(--muted);font-size:12px;line-height:1.4}
.xcard .meta{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-top:auto}
.xcard .meta .spacer{flex:1}
.tag.miss{background:rgba(var(--fg),.07);color:var(--muted)}
.tag.kind{background:rgba(var(--accent2-rgb),.13);color:var(--ext-h)}
.tag.cust{background:rgba(var(--warn-rgb),.14);color:var(--warn-text)}
.xhow{font:11px var(--mono);color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.xcard .spin{margin-right:4px}
.pkg{padding:10px 14px;border-radius:calc(12px*var(--rr));border:1px solid var(--line);background:rgba(var(--fg),.025);display:flex;align-items:center;gap:10px}
.pkg b{font:600 13px var(--mono);flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis}
.pkg small{color:var(--dim);font:11.5px var(--mono)}
.modal.wide{width:min(820px,94vw)}
.modal textarea.json{width:100%;height:46vh;font:12.5px/1.5 var(--mono);background:var(--field);border:1px solid var(--line2);border-radius:calc(11px*var(--rr));padding:10px 12px;outline:none;color:var(--code);resize:vertical;tab-size:2}
.modal textarea.json:focus{border-color:var(--accent)}
.lgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(128px,1fr));gap:8px;margin-bottom:16px;max-height:40vh;overflow:auto;padding:2px}
.lgrid .tpl{display:flex;align-items:center;gap:9px;padding:9px 10px}
.lgrid .tpl .lchip{font-size:9px}
.lgrid .tpl b{font-size:12.5px}
.lgrid .tpl.miss{opacity:.55}
.lgrid .tpl small{display:block;font-size:10.5px}
.tpls.t3{grid-template-columns:repeat(auto-fill,minmax(130px,1fr))}
/* « .sel » sert aussi aux listes (palette, autocomplétion) : on neutralise le style des sélecteurs */
.palette li.sel,.ac div.sel{height:auto;border:0;position:static;min-width:0}
.palette li.sel::after,.ac div.sel::after{content:none}
.ac div.sel{padding:4px 8px;border-radius:calc(6px*var(--rr))}
.xhead .switch{margin-left:auto;align-self:flex-start}
.ptitle{min-width:84px}
#targetSel{max-width:132px}
.badge.dotb{min-width:9px;width:9px;height:9px;padding:0;font-size:0}
.welcome{justify-content:safe center;overflow:auto}
.btn.primary.again{filter:saturate(.85)}
@media (max-width:1380px){.btn.primary.again .lbl{display:none}}
.toolbar .btn{flex-shrink:0}

</style>
</head>
<body>
<div class="bg"><i></i><i></i><i></i></div>

<a class="skip" href="#ta">Aller à l'éditeur</a>
<div class="app">
  <div class="scrim" id="scrim"></div>
  <!-- ===================== barre latérale ===================== -->
  <aside class="sidebar glass">
    <div class="brand">
      <div class="logo"><svg viewBox="0 0 24 24"><defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" style="stop-color:var(--logo1)"/><stop offset="1" style="stop-color:var(--logo2)"/></linearGradient></defs><path d="M12 1.5 21.5 7v10L12 22.5 2.5 17V7z" fill="url(#lg)"/><path d="m9.6 8.2-3.4 3.8 3.4 3.8M14.4 8.2l3.4 3.8-3.4 3.8" style="stroke:var(--logo-bolt)" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
      <div><b>Forge Code</b><small>Atelier multi-langages</small></div>
    </div>
    <button class="btn-new" id="btnNew"><svg class="i" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>Nouveau projet</button>
    <button class="acad-btn" id="btnAcad" title="Académie : parcours, défis et grades (F9)" aria-label="Ouvrir l'Académie (F9)">
      <span class="ab-ic" id="abIc" aria-hidden="true">🎓</span>
      <span class="ab-txt"><b>Académie</b><small id="abSub">Du stage à la légende</small></span>
      <span class="ab-ring" id="abRing" data-v="0" style="--p:0" aria-hidden="true"></span>
    </button>
    <div class="search"><svg class="i" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg><input id="projFilter" placeholder="Rechercher un projet…" aria-label="Rechercher un projet"></div>
    <div class="side-sec"><span>Projets</span><span style="display:flex;align-items:center;gap:6px"><button class="tinybtn" id="projSort" title="Changer l'ordre de tri" aria-label="Ordre de tri des projets"></button><span id="projCount" class="dim"></span></span></div>
    <ul class="projects" id="projList"></ul>
    <div class="side-foot">
      <span>Dossier des projets</span><span class="pathbox" id="wsPath">…</span>
      <span style="margin-top:6px;display:flex;align-items:center;gap:6px"><span class="kbd">Ctrl K</span> palette de commandes</span>
      <span style="display:flex;align-items:center;gap:6px"><span class="kbd">?</span> aide et raccourcis</span>
      <button class="btn sm" id="btnLook" title="Modes et réglages d'apparence (Ctrl Alt T : mode suivant)" style="justify-content:center;margin:4px 0 2px"><svg class="i" viewBox="0 0 24 24"><circle cx="13.5" cy="6.5" r="1.5"/><circle cx="17.5" cy="10.5" r="1.5"/><circle cx="8.5" cy="7.5" r="1.5"/><circle cx="6.5" cy="12.5" r="1.5"/><path d="M12 2a10 10 0 0 0 0 20c1.1 0 2-.9 2-2v-.5c0-.6.4-1 1-1h1.5A5.5 5.5 0 0 0 22 12.5C22 6.7 17.5 2 12 2z"/></svg>Apparence…</button>
      <div class="themeseg" role="radiogroup" aria-label="Thème de l'interface" id="themeSeg">
        <button role="radio" data-theme="dark" aria-checked="false" title="Thème sombre"><svg class="i" viewBox="0 0 24 24"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>Sombre</button>
        <button role="radio" data-theme="light" aria-checked="false" title="Thème clair"><svg class="i" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>Clair</button>
        <button role="radio" data-theme="system" aria-checked="false" title="Suivre le thème du système"><svg class="i" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg>Système</button>
      </div>
    </div>
  </aside>

  <!-- ===================== zone principale ===================== -->
  <main class="main">
    <header class="toolbar glass">
      <button class="btn icon sm" id="btnSide" title="Barre latérale (Ctrl+B)" aria-label="Afficher ou masquer la barre latérale" aria-pressed="true"><svg class="i" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></svg></button>
      <div class="ptitle"><b id="projName">Aucun projet</b><span id="projFile">—</span></div>
      <div class="sep hide-sm"></div>
      <div class="sel" id="langWrap" title="Langage du projet"><span class="lchip" id="langChip">?</span><select id="langSel" aria-label="Langage du projet"></select></div>
      <div class="sel hide-sm" title="Exécuter le fichier principal du projet (★) ou l'onglet actif"><svg class="i" viewBox="0 0 24 24"><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6"/></svg><select id="targetSel" aria-label="Fichier à exécuter"><option value="main">Principal</option><option value="current">Onglet actif</option></select></div>
      <div class="spacer"></div>
      <div class="jobbar" id="jobbar" aria-hidden="true"></div>
      <span class="sr" id="jobSr" role="status" aria-live="polite"></span>
      <label class="switch hide-sm" title="Exécute automatiquement à chaque enregistrement (Ctrl+S)"><input type="checkbox" id="autoRun"><i></i><span>Auto</span></label>
      <button class="btn" id="btnVerify" title="Vérifier sans exécuter : compilation ou analyse de syntaxe (Ctrl+R)" aria-label="Vérifier"><svg class="i" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5"/></svg><span class="lbl">Vérifier</span></button>
      <button class="btn primary" id="btnRun" title="Enregistrer, compiler si besoin et exécuter (Ctrl+Entrée ou F5)"><svg class="i" viewBox="0 0 24 24"><path d="m6 4 14 8-14 8z"/></svg>Exécuter <span class="kbd hide-sm">Ctrl ⏎</span></button>
      <button class="btn danger" id="btnStop" style="display:none" title="Arrêter le programme (⇧F5)"><svg class="i" viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>Arrêter</button>
      <button class="btn icon sm" id="btnInsp" title="Inspecteur (Ctrl+Alt+B)" aria-label="Afficher ou masquer l'inspecteur" aria-pressed="true"><svg class="i" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/></svg></button>
      <button class="btn icon sm hide-md" id="btnHelp" title="Aide et raccourcis (?)" aria-label="Aide et raccourcis"><svg class="i" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1 .9-1 1.7M12 17h.01"/></svg></button>
    </header>

    <div class="content">
      <section class="editor-card glass">
        <div class="ftabs" id="ftabs"><div class="ftablist" id="ftabList" role="tablist" aria-label="Fichiers ouverts"></div><button class="ftab-add" id="ftabAdd" aria-label="Nouveau fichier" title="Nouveau fichier"><svg class="i" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg></button></div>
        <div class="editor" id="editor">
          <div class="gutter"><div class="gutter-in" id="gutter"></div></div>
          <div class="code" id="code">
            <div class="layer" id="layer"><div class="curline" id="curline"></div><div id="marks"></div></div>
            <pre class="hm" id="dec" aria-hidden="true"></pre>
            <pre class="hl" id="hl" aria-hidden="true"></pre>
            <textarea class="ta" id="ta" spellcheck="false" autocomplete="off" autocapitalize="off" wrap="off" aria-label="Éditeur de code" aria-autocomplete="list" aria-controls="ac" aria-expanded="false"></textarea>
            <div class="ac" id="ac" role="listbox" aria-label="Suggestions de code" hidden></div>
          </div>
          <div class="ruler" id="ruler" aria-hidden="true" title="Erreurs et occurrences (clic pour y aller)"></div>
          <div class="findbar" id="findbar" role="search" aria-label="Rechercher et remplacer" hidden>
            <div class="frow">
              <input id="fInput" placeholder="Rechercher" aria-label="Rechercher" autocomplete="off" spellcheck="false">
              <span class="fcount" id="fCount" aria-live="polite"></span>
              <button class="btn tg" id="fCase" aria-pressed="false" title="Respecter la casse" aria-label="Respecter la casse">Aa</button>
              <button class="btn tg" id="fWord" aria-pressed="false" title="Mot entier" aria-label="Mot entier">ab</button>
              <button class="btn tg" id="fRe" aria-pressed="false" title="Expression régulière" aria-label="Expression régulière">.*</button>
              <button class="btn icon sm" id="fPrev" title="Précédent (Maj+Entrée)" aria-label="Occurrence précédente"><svg class="i" viewBox="0 0 24 24"><path d="m6 15 6-6 6 6"/></svg></button>
              <button class="btn icon sm" id="fNext" title="Suivant (Entrée)" aria-label="Occurrence suivante"><svg class="i" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg></button>
              <button class="btn icon sm" id="fClose" title="Fermer (Échap)" aria-label="Fermer la recherche"><svg class="i" viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12"/></svg></button>
            </div>
            <div class="frow" id="fRepRow" hidden>
              <input id="fRep" placeholder="Remplacer par" aria-label="Remplacer par" autocomplete="off" spellcheck="false">
              <button class="btn sm" id="fRepOne">Remplacer</button>
              <button class="btn sm" id="fRepAll">Tout remplacer</button>
            </div>
          </div>
          <div class="noedit" id="noedit" hidden></div>
          <div class="welcome" id="welcome">
            <div class="wart" aria-hidden="true"></div>
            <h1>Forge Code</h1>
            <p>Écrivez et exécutez du code dans le langage de votre choix. Chaque langage est une extension : installez-en autant que vous voulez.</p>
            <div class="row">
              <button class="btn primary" id="wNew"><svg class="i" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>Nouveau projet</button>
              <button class="btn" id="wImport"><svg class="i" viewBox="0 0 24 24"><path d="M12 15V3M6 7l6-6 6 6M4 21h16"/></svg>Importer un .zip</button>
              <button class="btn" id="wAcad" title="Parcours Développeur et Mathématicien : défis, grades et promotions (F9)">🎓 Académie</button>
              <button class="btn" id="wExt"><svg class="i" viewBox="0 0 24 24"><path d="M20 7h-3a2 2 0 0 1-2-2V2M9 18a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h7l4 4v10a2 2 0 0 1-2 2zM3 7.6v12.8A1.6 1.6 0 0 0 4.6 22h9.8"/></svg>Extensions</button>
            </div>
            <div class="wlangs" id="wLangs"></div>
            <div class="recent" id="recent"></div>
          </div>
        </div>
      </section>

      <aside class="inspector">
        <div class="itabs" id="itabs" role="tablist" aria-label="Inspecteur">
          <button role="tab" data-it="defi" id="itDefi" aria-selected="false" tabindex="-1" hidden>🎯 Défi</button>
          <button role="tab" data-it="proj" class="active" aria-selected="true">Projet</button>
          <button role="tab" data-it="outline" aria-selected="false" tabindex="-1">Structure</button>
          <button role="tab" data-it="snaps" aria-selected="false" tabindex="-1">Instantanés</button>
        </div>
        <div class="ipane" data-it="defi"><div class="df" id="dfPane"></div></div>
        <div class="ipane active" data-it="proj">
          <div class="card glass">
            <h3>Langage <button class="btn icon sm" id="btnExtGo" title="Extensions" aria-label="Ouvrir les extensions"><svg class="i" viewBox="0 0 24 24"><path d="M20 7h-3a2 2 0 0 1-2-2V2M9 18a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h7l4 4v10a2 2 0 0 1-2 2zM3 7.6v12.8A1.6 1.6 0 0 0 4.6 22h9.8"/></svg></button></h3>
            <div class="board">
              <div class="chip off" id="langBig">?</div>
              <div style="min-width:0"><b id="langName">—</b><small id="langVer">Ouvrez un projet</small><span class="pill off" id="langPill"><span class="dot"></span>—</span></div>
            </div>
            <div class="langacts" id="langActs"></div>
          </div>
          <div class="card glass">
            <h3>Fichiers <span style="display:flex;gap:4px"><button class="btn icon sm" id="btnFileNew" title="Nouveau fichier" aria-label="Nouveau fichier"><svg class="i" viewBox="0 0 24 24"><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6M12 12v6M9 15h6"/></svg></button><button class="btn icon sm" id="btnFilesRefresh" title="Relire le dossier" aria-label="Relire le dossier du projet"><svg class="i" viewBox="0 0 24 24"><path d="M21 12a9 9 0 1 1-2.6-6.4M21 3v6h-6"/></svg></button></span></h3>
            <div class="tree" id="tree" role="tree" aria-label="Fichiers du projet"></div>
          </div>
          <div class="card glass">
            <h3>Exécution</h3>
            <div class="field sm"><label for="runArgs">Arguments</label><input id="runArgs" placeholder="ex. --verbose fichier.txt" autocomplete="off" spellcheck="false"></div>
            <div class="field sm"><label for="runStdin">Entrée envoyée au démarrage</label><textarea id="runStdin" rows="2" placeholder="Texte tapé automatiquement dans le programme (facultatif)" spellcheck="false"></textarea></div>
            <label class="switch" style="margin-top:2px"><input type="checkbox" id="runClear"><i></i><span>Effacer le terminal à chaque exécution</span></label>
          </div>
          <div class="card glass">
            <h3>Historique</h3>
            <div class="hist" id="hist"><div class="dim" style="background:none;padding:0">Rien pour l'instant.</div></div>
          </div>
          <div class="card glass">
            <h3>Partage</h3>
            <div class="sharerow"><button class="btn sm" id="btnExport" title="Télécharger le projet (.zip)"><svg class="i" viewBox="0 0 24 24"><path d="M12 3v12M6 11l6 6 6-6M4 21h16"/></svg>Exporter .zip</button><button class="btn sm" id="btnImport" title="Importer un projet depuis un .zip"><svg class="i" viewBox="0 0 24 24"><path d="M12 15V3M6 7l6-6 6 6M4 21h16"/></svg>Importer .zip</button></div>
            <p class="dim" style="font-size:11.5px;margin:9px 0 0">Le .zip contient le projet sans les dossiers générés (.venv, node_modules, target…).</p>
            <input type="file" id="importFile" accept=".zip,application/zip" hidden>
          </div>
        </div>
        <div class="ipane" data-it="outline"><div class="card glass"><h3>Structure <span class="dim" id="outlineInfo" style="text-transform:none;letter-spacing:0;font-weight:500"></span></h3><div class="outline" id="outline"></div></div></div>
        <div class="ipane" data-it="snaps"><div class="card glass" id="snapCard"><h3>Instantanés</h3><div id="snapBody"></div></div></div>
      </aside>
    </div>

    <div class="resizer" id="resizer" role="separator" aria-orientation="horizontal" aria-label="Redimensionner le panneau du bas (flèches haut/bas, Entrée pour replier)" tabindex="0"></div>

    <section class="panel glass">
      <nav class="ptabs" id="ptabs" aria-label="Panneau du bas">
        <div class="ptablist" role="tablist" aria-label="Panneau du bas">
        <button class="ptab active" data-v="terminal"><svg class="i" viewBox="0 0 24 24"><path d="m4 17 6-6-6-6M12 19h8"/></svg>Terminal<span class="badge" id="bTerm"></span></button>
        <button class="ptab" data-v="plotter"><svg class="i" viewBox="0 0 24 24"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>Traceur</button>
        <button class="ptab" data-v="pkgs"><svg class="i" viewBox="0 0 24 24"><path d="M21 8 12 3 3 8v8l9 5 9-5zM3 8l9 5 9-5M12 13v8"/></svg>Paquets</button>
        <button class="ptab" data-v="exts"><svg class="i" viewBox="0 0 24 24"><path d="M20 7h-3a2 2 0 0 1-2-2V2M9 18a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h7l4 4v10a2 2 0 0 1-2 2zM3 7.6v12.8A1.6 1.6 0 0 0 4.6 22h9.8"/></svg>Extensions<span class="badge info" id="bExt"></span></button>
        <button class="ptab" data-v="examples"><svg class="i" viewBox="0 0 24 24"><path d="m16 18 6-6-6-6M8 6l-6 6 6 6"/></svg>Exemples</button>
        <button class="ptab" data-v="doctor"><svg class="i" viewBox="0 0 24 24"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1.1L12 21l7.8-7.5 1-1.1a5.5 5.5 0 0 0 0-7.8z"/></svg>Diagnostic<span class="badge" id="bDoctor"></span></button>
        </div>
        <div class="spacer"></div>
        <button class="btn icon sm" id="btnBig" aria-pressed="false" title="Agrandir / réduire le panneau" aria-label="Agrandir ou réduire le panneau du bas"><svg class="i" viewBox="0 0 24 24"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg></button>
        <button class="btn icon sm" id="btnClearPanel" title="Effacer" aria-label="Effacer le contenu de l'onglet"><svg class="i" viewBox="0 0 24 24"><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/></svg></button>
        <button class="btn icon sm ptoggle" id="btnPanel" title="Replier / déplier le panneau (Ctrl+J)" aria-label="Replier ou déplier le panneau du bas" aria-expanded="true"><svg class="i" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg></button>
      </nav>
      <div class="pbody">
        <div class="pview active" data-v="terminal">
          <div class="ptools">
            <span class="tstate" id="tState"><span class="dot" id="tDot"></span><span id="tLbl">Terminal libre</span></span>
            <div class="spacer"></div>
            <button class="btn sm" id="btnRepl" title="Console interactive du langage (REPL) dans le dossier du projet"><svg class="i" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg><span id="replLbl">Console</span></button>
            <button class="btn sm" id="btnShell" title="Shell (bash) dans le dossier du projet"><svg class="i" viewBox="0 0 24 24"><path d="m4 17 6-6-6-6M12 19h8"/></svg>Shell</button>
            <button class="btn sm" id="btnSigInt" title="Interrompre (envoie Ctrl+C au programme)" disabled>Ctrl+C</button>
            <label class="switch"><input type="checkbox" id="tScroll" checked><i></i><span>Défilement auto</span></label>
            <button class="btn sm" id="btnTermSave" title="Exporter en .txt" aria-label="Exporter le terminal en fichier texte"><svg class="i" viewBox="0 0 24 24"><path d="M12 3v12M6 11l6 6 6-6M4 21h16"/></svg></button>
          </div>
          <div class="out term" id="term" role="log" aria-live="off" aria-label="Terminal" tabindex="0"><div class="l sys">Prêt. Ouvrez un projet puis appuyez sur Exécuter (Ctrl+Entrée).</div></div>
          <div class="sendbar">
            <span class="prompt" aria-hidden="true">❯</span>
            <input id="tInput" aria-label="Texte à envoyer au programme" placeholder="Lancez un programme pour lui écrire ici… (↑ historique)" autocomplete="off" spellcheck="false">
            <button class="btn sm" id="btnSend" style="height:32px">Envoyer</button>
            <button class="btn sm" id="btnEof" style="height:32px" title="Fin de l'entrée (Ctrl+D) : le programme ne recevra plus rien" disabled>Fin (Ctrl+D)</button>
          </div>
        </div>

        <div class="pview" data-v="plotter">
          <div class="ptools">
            <div class="legend" id="legend" role="group" aria-label="Courbes affichées"></div>
            <div class="sel"><select id="plotWin" aria-label="Nombre de points affichés"><option value="200">200 points</option><option value="500" selected>500 points</option><option value="1000">1000 points</option><option value="3000">3000 points</option><option value="0" id="winCustom" hidden>zoom</option></select></div>
            <button class="btn sm" id="btnPlotPause" aria-pressed="false"><svg class="i" viewBox="0 0 24 24"><path d="M8 5v14M16 5v14"/></svg>Pause</button>
            <button class="btn sm" id="btnPlotFit" title="Revenir au suivi en direct avec échelle automatique (double-clic sur le graphique)"><svg class="i" viewBox="0 0 24 24"><path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3"/></svg>Ajuster</button>
            <button class="btn sm" id="btnPlotCsv" title="Exporter les données en CSV"><svg class="i" viewBox="0 0 24 24"><path d="M12 3v12M6 11l6 6 6-6M4 21h16"/></svg>CSV</button>
            <button class="btn sm" id="btnPlotPng" title="Enregistrer le graphique en image PNG"><svg class="i" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m21 16-5-5-8 8"/></svg>PNG</button>
          </div>
          <div class="plotwrap"><canvas id="plot" role="img" aria-label="Graphique des mesures écrites par le programme. Molette : zoom, glisser : déplacer, double-clic : ajuster."></canvas><div class="ptip" id="plotTip" hidden></div></div>
        </div>

        <div class="pview" data-v="pkgs">
          <div class="ptools">
            <span class="dim" id="pkgKind" style="font-weight:600"></span>
            <input class="mini" id="pkgName" placeholder="Nom du paquet (ex. requests)" aria-label="Nom du paquet à ajouter" autocomplete="off" spellcheck="false" style="width:260px">
            <button class="btn sm primary" id="btnPkgAdd"><svg class="i" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>Ajouter</button>
            <button class="btn sm" id="btnPkgRefresh" title="Relire la liste"><svg class="i" viewBox="0 0 24 24"><path d="M21 12a9 9 0 1 1-2.6-6.4M21 3v6h-6"/></svg></button>
            <span class="dim" id="pkgNote"></span>
          </div>
          <div class="grid-list" id="pkgList"></div>
        </div>

        <div class="pview" data-v="exts">
          <div class="ptools">
            <div class="search" style="margin:0;flex:1;max-width:340px"><svg class="i" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg><input id="extQ" aria-label="Chercher une extension" placeholder="Chercher (Rust, formateur, analyseur…)" autocomplete="off"></div>
            <div class="segs" id="extFilter" role="radiogroup" aria-label="Filtrer"><button role="radio" aria-checked="true" data-f="all">Tout</button><button role="radio" aria-checked="false" data-f="lang">Langages</button><button role="radio" aria-checked="false" data-f="tool">Outils</button><button role="radio" aria-checked="false" data-f="inst">Installées</button></div>
            <button class="btn sm" id="btnExtAdd" title="Ajouter un langage ou un outil décrit en JSON"><svg class="i" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>Extension personnelle…</button>
            <button class="btn sm" id="btnExtRefresh" title="Rechercher à nouveau les outils installés"><svg class="i" viewBox="0 0 24 24"><path d="M21 12a9 9 0 1 1-2.6-6.4M21 3v6h-6"/></svg></button>
            <span class="dim" id="extInfo"></span>
          </div>
          <div class="grid-list" id="extList"><div class="emptyp">Chargement…</div></div>
        </div>

        <div class="pview" data-v="examples">
          <div class="ptools">
            <div class="search" style="margin:0;flex:1;max-width:420px"><svg class="i" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg><input id="exQ" aria-label="Chercher un exemple" placeholder="Chercher un exemple (python, jeu, traceur…)" autocomplete="off"></div>
            <label class="switch"><input type="checkbox" id="exAll"><i></i><span>Langages non installés aussi</span></label>
            <span class="dim" id="exInfo"></span>
          </div>
          <div class="grid-list" id="exList"></div>
        </div>

        <div class="pview" data-v="doctor">
          <div class="ptools"><button class="btn sm" id="btnDoctor"><svg class="i" viewBox="0 0 24 24"><path d="M21 12a9 9 0 1 1-2.6-6.4M21 3v6h-6"/></svg>Relancer le diagnostic</button><span class="dim">Cliquez sur une commande pour la copier.</span></div>
          <div class="grid-list" id="docList"><div class="emptyp">Lancez le diagnostic pour vérifier votre installation.</div></div>
        </div>
      </div>
    </section>

    <section class="academy" id="academy" aria-label="Académie" hidden>
      <svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs><linearGradient id="acGrad" x1="0" y1="0" x2="1" y2="1"><stop offset="0" style="stop-color:var(--accent)"/><stop offset="1" style="stop-color:var(--accent2)"/></linearGradient></defs></svg>
      <header class="ac-top glass">
        <button class="btn sm ghost" id="acBack" title="Revenir à l'atelier (Échap ou F9)">← Atelier</button>
        <div class="ac-brand"><span class="ac-logo" aria-hidden="true">🎓</span><div><b>Académie</b><small id="acSub">Du stage à la légende</small></div></div>
        <nav class="ac-nav" id="acTracks" role="tablist" aria-label="Filière"></nav>
        <div class="ac-langs" id="acLangs" role="tablist" aria-label="Mes langages"></div>
        <div class="sel ac-add"><select id="acLang" aria-label="Commencer un autre langage"></select></div>
        <span class="spacer" style="flex:1"></span>
        <nav class="ac-nav" id="acNav" role="tablist" aria-label="Vue"><button role="tab" data-av="path">Carrière</button><button role="tab" data-av="skills">Compétences</button><button role="tab" data-av="ach">Succès</button></nav>
        <div class="ac-xp" id="acXp"></div>
      </header>
      <div class="ac-body" id="acBody"></div>
    </section>

    <footer class="status">
      <span title="Liaison avec le serveur Forge Code"><span class="dot" id="sseDot"></span><b id="sseLbl">Connexion…</b></span>
      <span id="stVer"></span>
      <span class="spacer" style="flex:1"></span>
      <span class="stdiag"><button class="tinybtn" id="stDiag" hidden></button><span id="stDiagMsg"></span></span>
      <span id="stJob"></span>
      <span class="fontctl" title="Taille de la police de l'éditeur (Ctrl + / Ctrl −)"><button class="tinybtn" id="fntDown" aria-label="Réduire la police">A−</button><b id="fntVal">13.5</b><button class="tinybtn" id="fntUp" aria-label="Agrandir la police">A+</button></span>
      <span id="stPos">Ln 1, Col 1</span>
      <button id="stGrade" hidden>—</button>
      <span id="stLang">—</span>
      <span id="stTerm">Terminal libre</span>
    </footer>
  </main>
</div>
<div class="tip" id="tip" role="tooltip" hidden></div>
<div class="toasts" id="toasts" role="region" aria-label="Notifications"></div>
<script>
"use strict";
const TOKEN = "__TOKEN__";
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const sleep = ms => new Promise(r => setTimeout(r, ms));

const ICONS = {
  check:'<path d="M20 6 9 17l-5-5"/>', x:'<path d="M18 6 6 18M6 6l12 12"/>',
  alert:'<path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 16v-4M12 8h.01"/>',
  plus:'<path d="M12 5v14M5 12h14"/>', arrow:'<path d="M5 12h14M13 5l7 7-7 7"/>',
  folder:'<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  radio:'<circle cx="12" cy="12" r="2"/><path d="M16.2 7.8a6 6 0 0 1 0 8.4M7.8 16.2a6 6 0 0 1 0-8.4M19.1 4.9a10 10 0 0 1 0 14.2M4.9 19.1a10 10 0 0 1 0-14.2"/>',
  activity:'<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>', book:'<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V2H6.5A2.5 2.5 0 0 0 4 4.5v15zM4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5"/>',
  heart:'<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1.1L12 21l7.8-7.5 1-1.1a5.5 5.5 0 0 0 0-7.8z"/>',
  refresh:'<path d="M21 12a9 9 0 1 1-2.6-6.4M21 3v6h-6"/>', trash:'<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/>',
  save:'<path d="M5 3h11l5 5v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2zM7 3v6h8M7 21v-8h10v8"/>',
  layers:'<path d="m12 2 10 5-10 5L2 7l10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>', terminal:'<path d="m4 17 6-6-6-6M12 19h8"/>',
  download:'<path d="M12 3v12M6 11l6 6 6-6M4 21h16"/>', search:'<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
  pin:'<path d="M12 17v5M9 3h6l-1 7 3 3H7l3-3z"/>', edit:'<path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>', filePlus:'<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6M12 12v6M9 15h6"/>',
  play:'<path d="m6 4 14 8-14 8z"/>', pause:'<path d="M8 5v14M16 5v14"/>', zap:'<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>',
  gauge:'<path d="M4 18a8 8 0 1 1 16 0"/><path d="m12 18 4-5"/>', hash:'<path d="M5 9h14M5 15h14M10 4 8 20M16 4l-2 16"/>',
  led:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19"/>',
  wand:'<path d="M15 4V2M15 16v-2M8 9H6M22 9h-2M17.8 11.8 19 13M17.8 6.2 19 5M12.2 6.2 11 5M3 21l9-9"/>',
  layout:'<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
  code:'<path d="m16 18 6-6-6-6M8 6l-6 6 6 6"/>',
  gear:'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  pkg:'<path d="M21 8 12 3 3 8v8l9 5 9-5zM3 8l9 5 9-5M12 13v8"/>', puzzle:'<path d="M20 7h-3a2 2 0 0 1-2-2V2M9 18a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h7l4 4v10a2 2 0 0 1-2 2zM3 7.6v12.8A1.6 1.6 0 0 0 4.6 22h9.8"/>',
  chat:'<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>', star:'<path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z"/>',
  file:'<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6"/>', sparkle:'<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18"/>',
  lint:'<path d="M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>', stop:'<rect x="6" y="6" width="12" height="12" rx="2"/>'
};
const icon = (n, cls = "i") => `<svg class="${cls}" viewBox="0 0 24 24">${ICONS[n] || ""}</svg>`;

/* ------------------------------------------------------------------ préférences */
const PREF_KEY = "forgecode.prefs";
const prefs = (() => { try { return JSON.parse(localStorage.getItem(PREF_KEY)) || {}; } catch { return {}; } })();
function savePrefs() { try { localStorage.setItem(PREF_KEY, JSON.stringify(prefs)); } catch {} }

/* chemin long : « …/Code » (le chemin complet reste dans l'infobulle) */
function midTrunc(p, max = 26) {
  const parts = p.split(/[\\/]/).filter(Boolean);
  return p.length <= max || parts.length < 2 ? p : "…/" + parts[parts.length - 1];
}

/* ------------------------------------------------------------------ thème */
const mqLight = matchMedia("(prefers-color-scheme: light)"), mqReduce = matchMedia("(prefers-reduced-motion: reduce)");
const modeOf = id => FORGE_MODES.find(m => m.id === id) || FORGE_MODES[0];
const DENS = { compact: .92, normal: 1, aere: 1.12 };
function syncFavicon() {
  const cs = getComputedStyle(document.documentElement), v = n => cs.getPropertyValue(n).trim(), fm = modeOf(prefs.mode).fam;
  const a = v("--logo1"), b = v("--logo2"), k = v("--logo-bolt");
  const shape = {
    hacker: `<rect x='2' y='2' width='20' height='20' fill='${v("--bg")}' stroke='${a}' stroke-width='2'/><path d='M7 8l4 4-4 4M13 16h4' fill='none' stroke='${a}' stroke-width='2.4'/>`,
    fleur: [0, 1, 2, 3, 4].map(i => `<ellipse cx='12' cy='6.6' rx='3.6' ry='5.2' fill='url(%23g)' transform='rotate(${i * 72} 12 12)'/>`).join("") + `<circle cx='12' cy='12' r='3' fill='${k}'/>`,
    kawaii: `<path d='M12 1.5l3 6.6 7.2.9-5.3 4.9 1.5 7.1L12 17.4 5.6 21l1.5-7.1L1.8 9l7.2-.9z' fill='url(%23g)'/><circle cx='9.4' cy='11.4' r='1.2' fill='${k}'/><circle cx='14.6' cy='11.4' r='1.2' fill='${k}'/>`
  }[fm] || `<path d='M12 1.5 21.5 7v10L12 22.5 2.5 17V7z' fill='url(%23g)'/><path d='M13 5.5 8 13h3.5l-1 5.5 5-7.5H12z' fill='${k}'/>`;
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='${a}'/><stop offset='1' stop-color='${b}'/></linearGradient></defs>${shape}</svg>`;
  $("#fav").href = "data:image/svg+xml," + encodeURIComponent(svg).replace(/%2523/g, "%23");
  $("#themeColor").content = v("--bg");
}
function applyTheme() {
  forgeApply(prefs);
  const mode = ["dark", "light", "system"].includes(prefs.theme) ? prefs.theme : "system";
  $$("#themeSeg button").forEach(b => { b.setAttribute("aria-checked", b.dataset.theme === mode); b.tabIndex = b.dataset.theme === mode ? 0 : -1; });
  syncFavicon();
  try { PL.dirty = true; } catch { /* le traceur n'est pas encore initialisé */ }
  try { renderLangBits(); } catch { /* interface pas encore prête */ }
  try { ED.setFont(prefs.fs || 13.5); } catch { /* éditeur pas encore prêt */ }
  try { lookRefresh(); } catch { /* fenêtre Apparence fermée */ }
}
function morph() {
  const R = document.documentElement; if (R.dataset.motion === "reduced") return;
  R.classList.add("morph"); clearTimeout(morph.t); morph.t = setTimeout(() => R.classList.remove("morph"), 480);
}
function setTheme(mode) { morph(); prefs.theme = mode; savePrefs(); applyTheme(); }
function setMode(id) { if (!FORGE_MODES.some(m => m.id === id)) return; morph(); prefs.mode = id; savePrefs(); applyTheme(); }
function nextMode(d = 1) {
  const n = FORGE_MODES.length, i = FORGE_MODES.findIndex(m => m.id === modeOf(prefs.mode).id), m = FORGE_MODES[(i + d + n) % n];
  setMode(m.id); toast(`Mode : ${m.name}`, "info", 1600);
}
mqLight.addEventListener("change", applyTheme);
mqReduce.addEventListener("change", applyTheme);
$("#themeSeg").addEventListener("click", e => { const b = e.target.closest("[data-theme]"); if (b) setTheme(b.dataset.theme); });
$("#themeSeg").addEventListener("keydown", e => {
  const l = $$("#themeSeg button"), i = l.findIndex(b => b.getAttribute("aria-checked") === "true");
  if (e.key === "ArrowRight" || e.key === "ArrowDown") { e.preventDefault(); setTheme(l[(i + 1) % 3].dataset.theme); $("#themeSeg [tabindex='0']").focus(); }
  else if (e.key === "ArrowLeft" || e.key === "ArrowUp") { e.preventDefault(); setTheme(l[(i + 2) % 3].dataset.theme); $("#themeSeg [tabindex='0']").focus(); }
});
applyTheme();

/* ------------------------------------------------------------------ état */
const S = {
  status: null, projects: [], project: null, info: null, files: [], tabs: [], file: null, docs: {},
  exts: [], ext: {}, extByFile: {}, diags: [], history: [], meta: { pinned: [], opened: {} }, conf: {},
  session: { running: false, kind: null }, run: null, job: null, lastRunOk: true
};

/* ------------------------------------------------------------------ API */
async function api(path, body) {
  const opt = body === undefined
    ? { headers: { "X-Token": TOKEN } }
    : { method: "POST", headers: { "X-Token": TOKEN, "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const r = await fetch(path, opt);
  const j = await r.json().catch(() => ({ error: "Réponse invalide du serveur" }));
  if (!r.ok || (j && j.error)) throw new Error(j.error || r.statusText);
  return j;
}
const qs = o => Object.entries(o).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");

/* ------------------------------------------------------------------ toasts & effets */
function toast(text, kind = "info", ms = 3800) {
  const ic = { ok: "check", error: "x", warn: "alert", info: "info" }[kind] || "info";
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.setAttribute("role", kind === "error" ? "alert" : "status");
  el.innerHTML = `<div class="ti">${icon(ic)}</div><div>${esc(text)}</div>`;
  $("#toasts").appendChild(el);
  setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 260); }, ms);
}
const reducedMotion = () => document.documentElement.dataset.motion === "reduced";
function burst(el) {
  if (reducedMotion() || document.documentElement.dataset.fx === "off") return;
  const r = el.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  const cs = getComputedStyle(document.documentElement), colors = [1, 2, 3, 4, 5, 6].map(i => cs.getPropertyValue("--burst" + i).trim());
  for (let i = 0; i < 26; i++) {
    const p = document.createElement("i");
    const a = Math.random() * Math.PI * 2, d = 50 + Math.random() * 90;
    p.className = "particle";
    p.style.cssText = `left:${cx}px;top:${cy}px;background:${colors[i % colors.length]};--dx:${Math.cos(a) * d}px;--dy:${Math.sin(a) * d + 30}px;--r:${Math.random() * 540}deg`;
    document.body.appendChild(p);
    setTimeout(() => p.remove(), 950);
  }
  el.classList.remove("flash-ok"); void el.offsetWidth; el.classList.add("flash-ok");
}


/* animations de réussite (quand un programme repart après une erreur), propres à chaque famille de modes */
function celebrate(el) {
  const R = document.documentElement, fam = modeOf(prefs.mode).fam, fx = R.dataset.fx !== "off";
  if (fam === "tech") return burst(el);
  if (!fx) return;
  const r = el.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2, rnd = (a, b) => a + Math.random() * (b - a);
  const add = (cls, html, ms) => { const d = document.createElement("div"); d.className = "cele " + cls; d.setAttribute("aria-hidden", "true"); d.innerHTML = html; document.body.appendChild(d); setTimeout(() => d.remove(), ms); return d; };
  if (fam === "contraste") { add("", '<div class="hcban">✔ Ça fonctionne !</div>', 3200); return; }
  if (reducedMotion()) return;
  if (fam === "hacker") add("cele-hk", `<div class="ag">${[..."ACCESS GRANTED"].map((c, i) => `<span style="--i:${i}">${c === " " ? "&nbsp;" : c}</span>`).join("")}</div><div class="agsub">programme corrigé</div>`, 2800);
  else if (fam === "fleur") add("", Array.from({ length: 28 }, (_, i) => `<i class="petal" style="left:${rnd(0, 100)}%;--d:${rnd(3.2, 5.4).toFixed(2)}s;--dl:${rnd(0, .9).toFixed(2)}s;--sw:${rnd(-90, 90).toFixed(0)}px;--c:var(--burst${[1, 2, 3, 4][i % 4]})"></i>`).join(""), 6600);
  else if (fam === "kawaii") add("", Array.from({ length: 24 }, (_, i) => { const a = rnd(-Math.PI, 0), d = rnd(70, 190); return `<i class="kstar" style="left:${cx}px;top:${cy}px;--z:${rnd(10, 22).toFixed(0)}px;--c:var(--burst${1 + i % 6});--dx:${(Math.cos(a) * d).toFixed(0)}px;--dy:${(Math.sin(a) * d).toFixed(0)}px"></i>`; }).join("") + `<div class="kbub" style="left:${cx}px;top:${cy}px">Ça marche ! ✦</div>`, 2400);
  else if (fam === "synth") add("", `<i class="sring" style="left:${cx}px;top:${cy}px"></i><i class="sring" style="left:${cx}px;top:${cy}px;animation-delay:.25s"></i><div class="sscan"></div><div class="stxt">RUN COMPLETE</div>`, 2500);
  else if (fam === "papier") add("", '<div class="stamp">Réussi ✓</div>', 2500);
}

/* ------------------------------------------------------------------ langages : couleurs et coloration syntaxique */
function textOn(varName) {   // encre sombre ou papier selon le contraste du fond (variable CSS)
  const c = document.createElement("canvas").getContext("2d");
  c.fillStyle = getComputedStyle(document.documentElement).getPropertyValue(varName).trim() || "gray"; c.fillRect(0, 0, 1, 1);
  const [r, g, b] = [...c.getImageData(0, 0, 1, 1).data].slice(0, 3).map(v => v / 255).map(v => v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4));
  const L = .2126 * r + .7152 * g + .0722 * b;
  return (L + .05) / .05 > 1.05 / (L + .05) ? "var(--ink)" : "var(--paper)";
}
const _onCache = {};
function langStyle(x) {                        // style="--lc:…;--lct:…" pour une pastille de langage
  if (!x) return "";
  const v = "--p" + ((x.color ?? 9) % 10), key = v + document.documentElement.dataset.mode + document.documentElement.dataset.theme;
  const on = _onCache[key] || (_onCache[key] = textOn(v));
  return `--lc:var(${v});--lct:${on}`;
}

const W = s => new Set((s || "").split(/\s+/).filter(Boolean));
const C_KW = "if else for while do switch case default break continue return goto sizeof typedef struct union enum static const volatile extern inline register auto signed unsigned";
const CPP_KW = C_KW + " new delete this class namespace using public private protected virtual template typename operator friend try catch throw nullptr override final constexpr noexcept explicit mutable decltype concept requires co_await co_return co_yield static_assert";
const JS_KW = "break case catch class const continue debugger default delete do else export extends finally for function if import in instanceof let new of return super switch this throw try typeof var void while with yield async await static get set from as";
const HLDEF = {
  python: { lc: ["#"], str: ["py"], kw: "and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield match case",
    ty: "int float str list dict set tuple bool bytes object type complex frozenset", co: "True False None self cls __name__ __main__",
    fn: "print input len range open enumerate zip map filter sorted reversed sum min max abs round isinstance super repr format any all iter next hasattr getattr setattr id hash chr ord divmod pow help dir vars", pp: "@[\\w.]+" },
  javascript: { lc: ["//"], bc: [["/*", "*/"]], str: ['"', "'", "`"], kw: JS_KW, co: "true false null undefined NaN Infinity",
    fn: "console Math JSON Object Array String Number Boolean Promise Date Map Set RegExp Error require module exports process setTimeout setInterval clearInterval clearTimeout document window fetch parseInt parseFloat globalThis Symbol BigInt" },
  c: { lc: ["//"], bc: [["/*", "*/"]], str: ['"', "c'"], kw: C_KW, ty: "void bool char short int long float double size_t ssize_t FILE uint8_t uint16_t uint32_t uint64_t int8_t int16_t int32_t int64_t",
    co: "true false NULL EOF stdin stdout stderr EXIT_SUCCESS EXIT_FAILURE", fn: "printf scanf puts putchar getchar gets fgets fputs fprintf fscanf sprintf snprintf malloc calloc realloc free memcpy memset memmove strlen strcmp strncmp strcpy strncpy strcat strchr strstr strcspn fopen fclose fflush fread fwrite exit atoi atof rand srand time abs sqrt pow sin cos main", pp: "^[ \\t]*#[^\\n]*" },
  rust: { lc: ["//"], bc: [["/*", "*/"]], str: ['"', "c'"], kw: "as async await break const continue crate dyn else enum extern fn for if impl in let loop match mod move mut pub ref return static struct super trait type unsafe use where while",
    ty: "i8 i16 i32 i64 i128 isize u8 u16 u32 u64 u128 usize f32 f64 bool char str String Vec Option Result Box HashMap HashSet Rc Arc Self self", co: "true false None Some Ok Err",
    fn: "println print format vec panic eprintln eprint assert assert_eq assert_ne write writeln todo unimplemented unreachable dbg matches", pp: "#!?\\[[^\\]\\n]*\\]" },
  go: { lc: ["//"], bc: [["/*", "*/"]], str: ['"', "c'", "`"], kw: "break case chan const continue default defer else fallthrough for func go goto if import interface map package range return select struct switch type var",
    ty: "bool byte complex64 complex128 error float32 float64 int int8 int16 int32 int64 rune string uint uint8 uint16 uint32 uint64 uintptr any", co: "true false nil iota",
    fn: "append cap close copy delete len make new panic print println recover min max fmt Println Printf Sprintf Print Errorf strings strconv os math time bufio" },
  java: { lc: ["//"], bc: [["/*", "*/"]], str: ['"', "c'"], kw: "abstract assert break case catch class continue default do else enum extends final finally for if implements import instanceof interface native new package private protected public return static strictfp super switch synchronized this throw throws transient try volatile while var record yield sealed permits",
    ty: "boolean byte char double float int long short void String Integer Long Double Boolean Object List ArrayList Map HashMap Set HashSet Scanner", co: "true false null", fn: "System out println printf print Math main length equals", pp: "@\\w+" },
  kotlin: { lc: ["//"], bc: [["/*", "*/"]], str: ['"', "c'"], kw: "as break class continue do else for fun if in interface is object package return super this throw try typealias typeof val var when while by catch constructor data enum finally get import init lateinit open override private protected public sealed set suspend companion internal inline",
    ty: "Int Long Double Float Boolean Char String Unit Any Nothing List MutableList Map Set Array", co: "true false null it", fn: "println print readln readlnOrNull listOf mutableListOf mapOf setOf arrayOf repeat require check", pp: "@\\w+" },
  csharp: { lc: ["//"], bc: [["/*", "*/"]], str: ['"', "c'"], kw: "abstract as base break case catch checked class const continue default delegate do else enum event explicit extern finally fixed for foreach goto if implicit in interface internal is lock namespace new operator out override params private protected public readonly ref return sealed sizeof stackalloc static struct switch this throw try typeof unchecked unsafe using virtual volatile while var async await record init get set yield",
    ty: "bool byte char decimal double float int long object sbyte short string uint ulong ushort void List Dictionary Task", co: "true false null", fn: "Console WriteLine Write ReadLine Math", pp: "^[ \\t]*#[^\\n]*" },
  ruby: { lc: ["#"], str: ['"', "'"], kw: "alias and begin break case class def defined? do else elsif end ensure for if in module next not or redo rescue retry return self super then undef unless until when while yield require require_relative attr_accessor attr_reader lambda proc",
    co: "true false nil", fn: "puts print p gets format printf each map select reject times upto to_s to_i to_f length", pp: "(?::[A-Za-z_]\\w*|@@?\\w+|\\$\\w+)" },
  php: { lc: ["//", "#"], bc: [["/*", "*/"]], str: ['"', "'"], kw: "abstract and as break callable case catch class clone const continue declare default do echo else elseif empty enddeclare endfor endforeach endif endswitch endwhile extends final finally fn for foreach function global goto if implements include include_once instanceof insteadof interface isset list match namespace new or print private protected public readonly require require_once return static switch throw trait try unset use var while yield",
    ty: "int float string bool array object mixed void iterable", co: "true false null TRUE FALSE NULL PHP_EOL", fn: "echo printf sprintf strlen count array_map array_filter explode implode trim fgets range json_encode json_decode var_dump print_r", pp: "(?:\\$\\w+|<\\?php|\\?>)" },
  lua: { lc: ["--"], bc: [["--[[", "]]"]], str: ['"', "'"], kw: "and break do else elseif end for function goto if in local not or repeat return then until while",
    co: "true false nil", fn: "print io write read string table math pairs ipairs tostring tonumber type require select error pcall assert setmetatable getmetatable os" },
  bash: { lc: ["#"], str: ['"', "'"], kw: "if then else elif fi case esac for select while until do done in function time return exit break continue local export readonly declare set unset shift source",
    fn: "echo printf read cd ls pwd cat grep sed awk test seq sleep mkdir rm cp mv find xargs sort head tail wc true false", pp: "\\$(?:\\{[^}\\n]*\\}|\\(\\(?|\\w+|[@#?$!*0-9-])" },
  perl: { lc: ["#"], str: ['"', "'"], kw: "if elsif else unless while until for foreach do last next redo return sub my our local use no package require print printf say and or not eq ne lt gt le ge cmp",
    fn: "chomp chop split join push pop shift unshift keys values each sort reverse length substr index open close die warn defined scalar exists delete", pp: "[$@%][\\w:]+" },
  r: { lc: ["#"], str: ['"', "'"], kw: "if else repeat while function for in next break return library require",
    co: "TRUE FALSE NULL NA NaN Inf T F", fn: "c print cat paste paste0 mean median sd sum length seq rep data.frame list vector matrix apply sapply lapply summary plot head tail round nrow ncol" },
  dart: { lc: ["//"], bc: [["/*", "*/"]], str: ['"', "'"], kw: "abstract as assert async await break case catch class const continue default do else enum export extends extension external factory final finally for get if implements import in is late library mixin new on operator part required rethrow return set static super switch sync this throw try typedef var while with yield",
    ty: "int double num String bool List Map Set void dynamic Object Future Stream", co: "true false null", fn: "print main stdin stdout", pp: "@\\w+" },
  haskell: { lc: ["--"], bc: [["{-", "-}"]], str: ['"'], kw: "case class data default deriving do else foreign if import in infix infixl infixr instance let module newtype of then type where qualified as hiding",
    ty: "Int Integer Float Double Char String Bool IO Maybe Either", co: "True False Nothing Just Left Right", fn: "putStrLn putStr print getLine show read map filter foldr foldl zip mapM_ return length head tail" },
  julia: { lc: ["#"], bc: [["#=", "=#"]], str: ['"'], kw: "function end if elseif else for while in do begin let local global const return break continue module using import struct mutable abstract type try catch finally macro quote",
    ty: "Int Int64 Float64 String Bool Char Vector Array Dict Nothing Any", co: "true false nothing missing", fn: "println print readline length push! map filter sum isempty strip parse", pp: "@\\w+" },
  zig: { lc: ["//"], str: ['"', "c'"], kw: "const var fn pub return if else while for switch break continue defer errdefer try catch orelse struct enum union error comptime inline test unreachable and or",
    ty: "u8 u16 u32 u64 usize i8 i16 i32 i64 isize f32 f64 bool void anyerror type anytype", co: "true false null undefined", pp: "@\\w+" },
  web: { html: true, bc: [["<!--", "-->"]], str: ['"', "'"], kw: "", pp: "</?[A-Za-z][\\w-]*|/?>|<!doctype|<!DOCTYPE" },
  css: { bc: [["/*", "*/"]], str: ['"', "'"], kw: "important", co: "inherit initial none auto", fn: "var calc rgb rgba hsl url linear-gradient radial-gradient min max clamp", pp: "(?:@[\\w-]+|#[0-9a-fA-F]{3,8}\\b|[.#][A-Za-z_][\\w-]*)" },
  json: { str: ['"'], co: "true false null" },
  markdown: { pp: "^#{1,6} [^\\n]*|^\\s*[-*+] |`[^`\\n]*`|\\*\\*[^*\\n]+\\*\\*" },
  plain: {}
};
HLDEF.typescript = { ...HLDEF.javascript, kw: JS_KW + " interface type enum implements namespace declare readonly private public protected abstract keyof infer is satisfies",
  ty: "string number boolean any unknown never void object bigint symbol Record Partial Readonly Array Promise" };
HLDEF.cpp = { ...HLDEF.c, kw: CPP_KW, ty: HLDEF.c.ty + " string vector map set unordered_map array pair tuple optional unique_ptr shared_ptr auto",
  fn: HLDEF.c.fn + " std cout cin cerr endl getline size push_back begin end sort find make_unique make_shared move" };
const EXT_HL = { ".css": "css", ".scss": "css", ".json": "json", ".md": "markdown", ".txt": "plain", ".toml": "plain", ".yaml": "plain", ".yml": "plain", ".csproj": "web", ".xml": "web", ".svg": "web", ".h": "c", ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript", ".tsx": "typescript" };
const reEsc = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const RX_CACHE = {};
function hlOf(id) { return HLDEF[id] || (S.ext[id] && S.ext[id].keywords ? { lc: [S.ext[id].comment || "#"], str: ['"', "'"], kw: S.ext[id].keywords, ty: S.ext[id].types, fn: S.ext[id].builtins } : null) || HLDEF.plain; }
/* expression régulière d'un langage : 1 commentaire, 2 chaîne, 3 directive/décorateur/balise, 4 nombre, 5 identifiant (6 appel), 7 opérateur */
function langRx(id) {
  if (RX_CACHE[id]) return RX_CACHE[id];
  const d = hlOf(id), com = [], str = [];
  (d.bc || []).forEach(([a, b]) => com.push(reEsc(a) + "[\\s\\S]*?(?:" + reEsc(b) + "|$)"));
  (d.lc || []).forEach(t => com.push(reEsc(t) + "[^\\n]*"));
  (d.str || []).forEach(q => {
    if (q === "py") { str.push('[rbfuRBFU]{0,2}"{3}[\\s\\S]*?(?:"{3}|$)', "[rbfuRBFU]{0,2}'{3}[\\s\\S]*?(?:'{3}|$)", '[rbfuRBFU]{0,2}"(?:\\\\.|[^"\\\\\\n])*"?', "[rbfuRBFU]{0,2}'(?:\\\\.|[^'\\\\\\n])*'?"); }
    else if (q === "c'") str.push("'(?:\\\\.[^'\\n]{0,8}|[^'\\\\\\n])'");
    else if (q === "`") str.push("`(?:\\\\.|[^`\\\\])*`?");
    else str.push(q + "(?:\\\\.|[^" + q + "\\\\\\n])*" + q + "?");
  });
  const src = [
    com.length ? "(" + com.join("|") + ")" : "($^)",
    str.length ? "(" + str.join("|") + ")" : "($^)",
    d.pp ? "(" + d.pp + ")" : "($^)",
    "(\\b(?:0[xX][0-9a-fA-F_]+|0[bB][01_]+|\\d[\\d_]*\\.?\\d*(?:[eE][+-]?\\d+)?)[A-Za-z]*\\b)",
    d.html ? "([A-Za-z_][\\w-]*)(?=(\\s*=))?" : "([A-Za-z_]\\w*[?!]?)(?=(\\s*\\(|!\\s*\\())?",
    "([{}()[\\];,.<>=!+\\-*/%&|^~?:]+)"
  ].join("|");
  let rx;
  try { rx = new RegExp(src, "gm"); } catch { rx = /($^)|($^)|($^)|(\b\d+\b)|([A-Za-z_]\w*)(?=(\s*\())?|([{}()[\];,.<>=!+\-*/%&|^~?:]+)/gm; }
  const sets = { kw: W(d.kw), ty: W(d.ty), fn: W(d.fn), co: W(d.co) };
  return (RX_CACHE[id] = { rx, ...sets, html: !!d.html, caps: !["bash", "web", "css", "plain", "json", "markdown", "haskell"].includes(id) });
}
function highlight(src, id) {
  const L = langRx(id), RX = L.rx;
  if (src.length > 400000) return esc(src);
  let out = "", last = 0, m;
  RX.lastIndex = 0;
  while ((m = RX.exec(src))) {
    if (m.index > last) out += esc(src.slice(last, m.index));
    const t = m[0];
    let c = null;
    if (m[1]) c = "c";
    else if (m[2]) c = "s";
    else if (m[3]) c = "p";
    else if (m[4]) c = "n";
    else if (m[5]) {
      const w = t.replace(/[?!]$/, "");
      c = L.kw.has(t) || L.kw.has(w) ? "k" : L.ty.has(w) ? "t" : L.fn.has(w) ? "f" : L.co.has(w) ? "q" : m[6] ? (L.html ? "t" : "call") : (L.caps && /^[A-Z][a-z0-9]/.test(w) ? "t" : null);
    }
    else if (m[7]) c = "o";
    out += c ? `<span class="tk-${c}">${esc(t)}</span>` : esc(t);
    last = RX.lastIndex;
    if (m[0].length === 0) RX.lastIndex++;
  }
  return out + esc(src.slice(last));
}
/* langage d'un fichier d'après son extension (extensions installées d'abord) */
function langOfFile(f) {
  if (!f) return "plain";
  const e = "." + f.split(".").pop(), low = e.toLowerCase();
  if (S.info && S.info.lang === "web" && /\.(html?|css|js)$/i.test(f)) return low === ".css" ? "css" : low === ".js" ? "javascript" : "web";
  if (EXT_HL[low] && !S.extByFile[e]) return EXT_HL[low];
  return S.extByFile[e] || S.extByFile[low] || EXT_HL[low] || (/^(Makefile|Dockerfile)$/.test(f.split("/").pop()) ? "bash" : "plain");
}
function commentOf(id) {
  if (id === "web") return ["<!--", "-->"];
  if (id === "css") return ["/*", "*/"];
  const d = hlOf(id);
  return d.lc ? [d.lc[0], ""] : d.bc ? d.bc[0] : ["#", ""];
}
function indentOf(id) {
  if (id === "go") return "\t";
  const x = S.ext[id]; return " ".repeat(x && x.indent ? x.indent : (["python", "c", "cpp", "java", "kotlin", "csharp", "php", "rust", "perl", "julia", "zig"].includes(id) ? 4 : 2));
}

/* ------------------------------------------------------------------ éditeur */
const PAD_X = 18, PAD_Y = 12, TAB = 4;
const vcol = (line, col) => { let v = 0; for (let i = 0; i < col && i < line.length; i++) v += line[i] === "\t" ? TAB - (v % TAB) : 1; return v; };
const colAt = (line, vc) => { let v = 0, i = 0; while (i < line.length) { const w = line[i] === "\t" ? TAB - (v % TAB) : 1; if (v + w > vc) break; v += w; i++; } return i; };

/* marque les caractères situés dans un commentaire, une chaîne ou une directive */
function buildMask(text, id) {
  const mask = new Uint8Array(text.length + 1), RX = langRx(id).rx;
  RX.lastIndex = 0;
  let m;
  while ((m = RX.exec(text))) {
    if (m[1] || m[2]) mask.fill(1, m.index, RX.lastIndex);
    if (m[0].length === 0) RX.lastIndex++;
  }
  return mask;
}
/* découpe le texte en segments portant les classes de tous les intervalles qui les couvrent */
function decorate(text, ranges) {
  const pts = new Set([0, text.length]);
  for (const r of ranges) { pts.add(r[0]); pts.add(r[1]); }
  const b = [...pts].filter(x => x >= 0 && x <= text.length).sort((x, y) => x - y);
  let out = "";
  for (let i = 0; i < b.length - 1; i++) {
    const a = b[i], z = b[i + 1], cls = [];
    for (const r of ranges) if (r[0] <= a && r[1] >= z) cls.push(r[2]);
    const seg = esc(text.slice(a, z));
    out += cls.length ? `<span class="${cls.join(" ")}">${seg}</span>` : seg;
  }
  return out;
}

const ED = {
  lang: "plain", _ml: null,
  ta: $("#ta"), hl: $("#hl"), dec: $("#dec"), gutter: $("#gutter"), layer: $("#layer"), cur: $("#curline"), marks: $("#marks"),
  code: $("#code"), ruler: $("#ruler"), tip: $("#tip"),
  lh: 21, charW: 8.1, lines: 0, raf: 0, _mv: null, _mask: null, _sv: null, _starts: [0], _hlText: null, _dk: null, _dv: null,
  set(text) {
    this.ta.value = text;
    this.ta.scrollTop = 0; this.ta.scrollLeft = 0;
    this.render(); this.caret();
  },
  render() {
    cancelAnimationFrame(this.raf);
    this.raf = requestAnimationFrame(() => this.renderNow());
  },
  renderNow() {
    const v = this.ta.value;
    this.hl.innerHTML = highlight(v, this.lang) + "\n ";
    this._hlText = v; this._dk = null;
    const n = this.starts().length;
    if (n !== this.lines) {
      this.lines = n;
      let g = "";
      for (let i = 1; i <= n; i++) g += `<div data-l="${i}">${i}</div>`;
      this.gutter.innerHTML = g;
    }
    this.paintDiags();
    if (FIND.open) findCompute(false);
    this.sync(); this.caret();
  },
  sync() {
    const x = this.ta.scrollLeft, y = this.ta.scrollTop;
    const t = `translate(${-x}px,${-y}px)`;
    this.hl.style.transform = t; this.dec.style.transform = t;
    this.gutter.style.transform = `translateY(${-y}px)`;
    this.layer.style.transform = `translateY(${-y}px)`;
  },
  /* décalages de début de ligne (mis en cache tant que le texte ne change pas) */
  starts() {
    const v = this.ta.value;
    if (this._sv !== v) {
      const a = [0]; let i = -1;
      while ((i = v.indexOf("\n", i + 1)) >= 0) a.push(i + 1);
      this._starts = a; this._sv = v;
    }
    return this._starts;
  },
  lineOf(pos) {
    const a = this.starts();
    let lo = 0, hi = a.length - 1;
    while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (a[mid] <= pos) lo = mid; else hi = mid - 1; }
    return lo;   // indice de ligne, à partir de 0
  },
  lineText(i) { const a = this.starts(), v = this.ta.value; return v.slice(a[i], a[i + 1] === undefined ? v.length : a[i + 1] - 1); },
  mask() { const v = this.ta.value; if (this._mv !== v || this._ml !== this.lang) { this._mask = buildMask(v, this.lang); this._mv = v; this._ml = this.lang; } return this._mask; },
  measure() {
    const s = document.createElement("span");
    s.style.cssText = "position:absolute;visibility:hidden;white-space:pre;font:inherit;left:0;top:0";
    s.textContent = "M".repeat(100);
    this.code.appendChild(s);
    this.charW = s.getBoundingClientRect().width / 100 || 8.1;
    s.remove();
  },
  setFont(px) {
    px = Math.max(10, Math.min(26, Math.round(px * 2) / 2));
    const root = document.documentElement;
    this.lh = Math.round(px * 1.56 * (DENS[document.documentElement.dataset.dens] || 1));
    root.style.setProperty("--fs", px + "px"); root.style.setProperty("--lh", this.lh + "px");
    prefs.fs = px; savePrefs();
    $("#fntVal").textContent = px;
    this.measure(); this.lines = 0; this.render();
  },
  caret() {
    const pos = this.ta.selectionStart, line = this.lineOf(pos), col = pos - this.starts()[line] + 1;
    this.cur.style.transform = `translateY(${line * this.lh}px)`;
    const prev = this.gutter.querySelector(".cur"); if (prev) prev.classList.remove("cur");
    const g = this.gutter.children[line]; if (g) g.classList.add("cur");
    $("#stPos").textContent = `Ln ${line + 1}, Col ${col}`;
    this.decorate();
    if (prefs.insp === "outline") outlineRender();
  },
  /* intervalles de surlignage : recherche, mot sélectionné, accolade appariée, erreurs */
  diagRanges(v) {
    const out = [], a = this.starts();
    for (const d of S.diags) {
      if (d.file !== S.file || a[d.line - 1] === undefined) continue;
      const ls = a[d.line - 1], le = a[d.line] === undefined ? v.length : a[d.line] - 1;
      if (le <= ls) continue;
      let s = ls + Math.max(0, d.col - 1);
      if (s >= le) s = le - 1;
      const m = /^[A-Za-z_]\w*|^\s*[^\s\w]+|^\s*\S/.exec(v.slice(s, le));
      out.push([s, Math.min(le, s + Math.max(1, m ? m[0].length : 1)), d.severity === "error" ? "d-err" : "d-warn", d]);
    }
    return out;
  },
  decorate() {
    const v = this.ta.value;
    if (this._hlText !== v) return;               // renderNow s'en chargera
    const R = [];
    if (FIND.open) FIND.matches.forEach(([s, e], i) => R.push([s, e, i === FIND.cur ? "d-cur" : "d-find"]));
    const focused = document.activeElement === this.ta;
    const s0 = this.ta.selectionStart, e0 = this.ta.selectionEnd;
    if (focused && e0 > s0 && e0 - s0 <= 60) {
      const w = v.slice(s0, e0);
      if (/^[A-Za-z_]\w*$/.test(w)) {
        const rx = new RegExp("(?<![\\w])" + w + "(?![\\w])", "g");
        let m, n = 0;
        while ((m = rx.exec(v)) && n++ < 500) if (m.index !== s0) R.push([m.index, m.index + w.length, "d-word"]);
      }
    }
    if (focused && s0 === e0) {
      const mask = this.mask(), OPEN = "([{", CLOSE = ")]}";
      const at = [s0 - 1, s0].find(i => i >= 0 && (OPEN + CLOSE).includes(v[i]) && !mask[i]);
      if (at !== undefined) {
        const ch = v[at], op = OPEN.includes(ch), pair = op ? CLOSE[OPEN.indexOf(ch)] : OPEN[CLOSE.indexOf(ch)];
        let depth = 0, found = -1;
        for (let i = at; op ? i < v.length : i >= 0; i += op ? 1 : -1) {
          if (mask[i]) continue;
          if (v[i] === ch) depth++; else if (v[i] === pair && --depth === 0) { found = i; break; }
        }
        if (found >= 0) R.push([at, at + 1, "d-br"], [found, found + 1, "d-br"]); else R.push([at, at + 1, "d-brx"]);
      }
    }
    if (this.snip) this.snip.stops.forEach(([a, b], i) => { if (i >= this.snip.i && b > a) R.push([a, b, "d-snip"]); });
    const dr = this.diagRanges(v);
    R.push(...dr);
    this._diagRanges = dr;
    const key = R.map(r => r[0] + "," + r[1] + "," + r[2]).join("|");
    if (key !== this._dk || v !== this._dv) { this._dk = key; this._dv = v; this.dec.innerHTML = decorate(v, R) + "\n "; }
    this.paintRuler();
  },
  paintDiags() {
    const list = S.diags.filter(d => d.file === S.file);
    this.gutter.querySelectorAll(".e,.w").forEach(el => { el.classList.remove("e", "w"); delete el.dataset.tip; });
    this.marks.innerHTML = "";
    const seen = new Set();
    for (const d of list) {
      const k = d.severity === "error" ? "e" : "w";
      const g = this.gutter.children[d.line - 1];
      if (g && !g.classList.contains("e")) { g.classList.remove("w"); g.classList.add(k); g.dataset.tip = d.message; }
      if (seen.has(d.line)) continue;
      seen.add(d.line);
      const m = document.createElement("div");
      m.className = `mark ${k}`;
      m.style.top = `${PAD_Y + (d.line - 1) * this.lh}px`;
      this.marks.appendChild(m);
    }
    this._dk = null; this.decorate();
  },
  /* barre de défilement annotée : erreurs, avertissements, occurrences de la recherche, ligne courante */
  paintRuler() {
    const n = this.starts().length, H = this.ruler.clientHeight;
    if (!H) return;
    const total = Math.max(n * this.lh + 2 * PAD_Y, this.code.clientHeight);
    const y = line => Math.min(H - 3, Math.max(0, (PAD_Y + line * this.lh) / total * H));
    let h = "";
    if (FIND.open) for (const [s] of FIND.matches.slice(0, 400)) h += `<i class="f" style="top:${y(this.lineOf(s))}px"></i>`;
    for (const d of S.diags) if (d.file === S.file) h += `<i class="${d.severity === "error" ? "e" : "w"}" style="top:${y(d.line - 1)}px"></i>`;
    h += `<i class="c" style="top:${y(this.lineOf(this.ta.selectionStart))}px"></i>`;
    if (h !== this._rh) { this._rh = h; this.ruler.innerHTML = h; }
  },
  goto(line, col = 1) {
    const a = this.starts(), v = this.ta.value;
    const l = Math.max(0, Math.min(line - 1, a.length - 1));
    const end = a[l + 1] === undefined ? v.length : a[l + 1] - 1;
    const pos = Math.min(end, a[l] + Math.max(0, col - 1));
    this.ta.focus();
    this.ta.setSelectionRange(pos, pos);
    this.ta.scrollTop = Math.max(0, l * this.lh - this.ta.clientHeight / 3);
    this.sync(); this.caret();
  },
  /* fait défiler pour rendre visible une position, sans toucher au focus */
  reveal(pos) {
    const l = this.lineOf(pos), y = l * this.lh, ta = this.ta;
    if (y < ta.scrollTop || y > ta.scrollTop + ta.clientHeight - this.lh * 3) ta.scrollTop = Math.max(0, y - ta.clientHeight / 3);
    const x = PAD_X + vcol(this.lineText(l), pos - this.starts()[l]) * this.charW;
    if (x < ta.scrollLeft + 20 || x > ta.scrollLeft + ta.clientWidth - 40) ta.scrollLeft = Math.max(0, x - ta.clientWidth / 2);
    this.sync();
  },
  /* insère du texte en gardant l'historique d'annulation ; rend le focus à l'élément d'origine si besoin */
  insert(text, keepFocus) {
    const prev = document.activeElement;
    this.ta.focus();
    if (!document.execCommand("insertText", false, text)) {
      this.ta.setRangeText(text, this.ta.selectionStart, this.ta.selectionEnd, "end");
      this.ta.dispatchEvent(new Event("input"));
    }
    if (keepFocus && prev && prev !== this.ta) prev.focus();
  },
  lineRange() {
    const v = this.ta.value, s0 = this.ta.selectionStart, e0 = this.ta.selectionEnd;
    const s = v.lastIndexOf("\n", s0 - 1) + 1;
    let e = v.indexOf("\n", Math.max(e0 - (e0 > s0 && v[e0 - 1] === "\n" ? 1 : 0), s0));
    if (e < 0) e = v.length;
    return [s, e];
  },
  transformLines(fn) {
    const [s, e] = this.lineRange();
    const out = fn(this.ta.value.slice(s, e).split("\n")).join("\n");
    this.ta.setSelectionRange(s, e);
    this.insert(out);
    this.ta.setSelectionRange(s, s + out.length);
  },
  duplicateLines() {
    const [s, e] = this.lineRange(), block = this.ta.value.slice(s, e);
    const a = this.ta.selectionStart, b = this.ta.selectionEnd;
    this.ta.setSelectionRange(e, e);
    this.insert("\n" + block);
    const off = block.length + 1;
    this.ta.setSelectionRange(a + off, b + off);
  },
  moveLines(dir) {
    const v = this.ta.value, [s, e] = this.lineRange(), a = this.ta.selectionStart, b = this.ta.selectionEnd;
    if (dir < 0) {
      if (s === 0) return;
      const ps = s - 1 === 0 ? 0 : v.lastIndexOf("\n", s - 2) + 1;
      const prev = v.slice(ps, s - 1), block = v.slice(s, e);
      this.ta.setSelectionRange(ps, e); this.insert(block + "\n" + prev);
      this.ta.setSelectionRange(a - prev.length - 1, b - prev.length - 1);
    } else {
      if (e >= v.length) return;
      const ne = v.indexOf("\n", e + 1) < 0 ? v.length : v.indexOf("\n", e + 1);
      const next = v.slice(e + 1, ne), block = v.slice(s, e);
      this.ta.setSelectionRange(s, ne); this.insert(next + "\n" + block);
      this.ta.setSelectionRange(a + next.length + 1, b + next.length + 1);
    }
    this.caret();
  },
  /* ---- info-bulle au survol des erreurs ---- */
  tipShow(html, x, y) {
    const t = this.tip; t.innerHTML = html; t.hidden = false;
    const w = t.offsetWidth, h = t.offsetHeight;
    t.style.left = Math.max(8, Math.min(innerWidth - w - 8, x + 12)) + "px";
    t.style.top = (y + 20 + h > innerHeight ? y - h - 10 : y + 20) + "px";
  },
  tipHide() { this.tip.hidden = true; },
  tipFor(d) { return `<b class="${d.severity === "error" ? "e" : "w"}">${d.severity === "error" ? "Erreur" : "Avertissement"}</b> · ${esc(d.message)}`; },
  /* ---- autocomplétion ---- */
  acOpen: false, acItems: [], acSel: 0, acFrom: 0,
  acUpdate(force) {
    const ta = this.ta, v = ta.value, p = ta.selectionStart;
    if (ta.selectionEnd !== p || this.mask()[p - 1]) return this.acClose();
    const line = v.slice(v.lastIndexOf("\n", p - 1) + 1, p);
    let items = [], word = "";
    const inc = ["c", "cpp"].includes(this.lang) && /^\s*#\s*include\s*<([\w./]*)$/.exec(line);
    const mem = !inc && /([A-Za-z_]\w*)(\.|::|->)(\w*)$/.exec(line);
    if (inc) {
      word = inc[1];
      items = HEADERS[this.lang].filter(h => h.startsWith(word) && h !== word).map(h => [h, "en-tête"]);
    } else if (mem) {
      word = mem[3];
      const M = MEMBERS[this.lang] || {}, lw = word.toLowerCase();
      const list = M[mem[1]] || (mem[2] !== "::" && word ? M["*"] : null) || [];
      items = list.filter(w => w.toLowerCase().startsWith(lw) && w !== word).map(w => [w, mem[2] === "::" ? "std" : "méthode"]);
    } else {
      const m = /[A-Za-z_]\w*$/.exec(line);
      word = m ? m[0] : "";
      if (word.length < 2 && !(force && word.length >= 0)) return this.acClose();
      items = acCandidates(word);
    }
    if (!items.length || (!force && !word && !mem && !inc)) return this.acClose();
    this.acItems = items.slice(0, 60); this.acSel = 0; this.acFrom = p - word.length; this.acOpen = true;
    this.acDraw();
  },
  acDraw() {
    const box = $("#ac");
    box.innerHTML = this.acItems.map(([w, k, body], i) => `<div role="option" id="ac${i}" data-i="${i}" aria-selected="${i === this.acSel}" class="${i === this.acSel ? "sel" : ""}"${body ? ` title="${esc(snipPreview(body))}"` : ""}><span>${esc(w)}</span><small>${esc(body ? "⇥ " + k : k)}</small></div>`).join("");
    box.hidden = false;
    this.ta.setAttribute("aria-expanded", "true"); this.ta.setAttribute("aria-activedescendant", "ac" + this.acSel);
    const p = this.ta.selectionStart, l = this.lineOf(p), txt = this.lineText(l), c = p - this.starts()[l];
    let x = PAD_X + vcol(txt, c) * this.charW - this.ta.scrollLeft - (p - this.acFrom) * this.charW;
    let y = PAD_Y + (l + 1) * this.lh - this.ta.scrollTop + 2;
    if (y + box.offsetHeight > this.code.clientHeight) y = y - this.lh - box.offsetHeight - 4;
    box.style.left = Math.max(4, Math.min(this.code.clientWidth - box.offsetWidth - 4, x)) + "px";
    box.style.top = Math.max(2, y) + "px";
    const s = box.children[this.acSel]; if (s) s.scrollIntoView({ block: "nearest" });
  },
  acMove(d) { this.acSel = (this.acSel + d + this.acItems.length) % this.acItems.length; this.acDraw(); },
  acClose() {
    if (!this.acOpen && $("#ac").hidden) return;
    this.acOpen = false; $("#ac").hidden = true;
    this.ta.setAttribute("aria-expanded", "false"); this.ta.removeAttribute("aria-activedescendant");
  },
  acAccept(i = this.acSel) {
    const it = this.acItems[i]; if (!it) return this.acClose();
    const p = this.ta.selectionStart, v = this.ta.value;
    this.acClose();
    if (it[2]) return this.snipExpand(it[2], this.acFrom, p);
    this.ta.setSelectionRange(this.acFrom, p);
    if (it[1] === "en-tête") {                       // #include <…> : ferme le chevron et passe derrière
      if (v[p] === ">") { this.insert(it[0]); this.ta.setSelectionRange(this.acFrom + it[0].length + 1, this.acFrom + it[0].length + 1); }
      else this.insert(it[0] + ">");
      return;
    }
    this.insert(it[0]);
  },
  /* ---- extraits de code (snippets) : champs à remplir, Tab / ⇧Tab pour passer de l'un à l'autre ---- */
  snip: null,
  snipAt(p = this.ta.selectionStart) {             // extrait dont le déclencheur est juste avant le curseur
    const m = /(?:^|[^\w#])(#?[A-Za-z_]\w*)$/.exec(this.ta.value.slice(Math.max(0, p - 40), p));
    const S2 = m && snippetsOf(this.lang);
    return S2 && S2[m[1]] ? [m[1], S2[m[1]]] : null;
  },
  snipExpand(body, from, to) {
    this.snipEnd();
    const ta = this.ta, v = ta.value, ls = v.lastIndexOf("\n", from - 1) + 1;
    const ind = v.slice(ls, from).match(/^[ \t]*/)[0];
    if (this.lang === "cpp" && /\busing\s+namespace\s+std\s*;/.test(v)) body = body.replace(/std::/g, "");
    body = body.replace(/\t/g, indentOf(this.lang)).replace(/\n/g, "\n" + ind);
    const stops = {}, rx = /\\\$|\$\{(\d+)(?::([^}]*))?\}|\$(\d+)/g;
    let out = "", last = 0, m;
    while ((m = rx.exec(body))) {
      out += body.slice(last, m.index); last = rx.lastIndex;
      if (m[0] === "\\$") { out += "$"; continue; }
      const n = +(m[1] || m[3]), def = (m[2] || "").replace(/\\\$/g, "$");
      if (!(n in stops)) stops[n] = [out.length, out.length + def.length];
      out += def;
    }
    out += body.slice(last);
    ta.setSelectionRange(from, to);
    this.insert(out);
    const list = Object.keys(stops).map(Number).filter(n => n > 0).sort((a, b) => a - b).map(n => stops[n]);
    list.push(stops[0] || [out.length, out.length]);
    this.snip = { stops: list.map(([a, b]) => [from + a, from + b]), i: 0, len: ta.value.length };
    this.snipGo(0);
  },
  snipGo(i) {
    const sn = this.snip; if (!sn) return;
    sn.i = Math.max(0, Math.min(i, sn.stops.length - 1));
    const [a, b] = sn.stops[sn.i];
    this.ta.setSelectionRange(a, b);
    if (sn.i === sn.stops.length - 1) this.snip = null;   // dernier champ : l'extrait est terminé
    this.reveal(a); this.caret(); this._dk = null; this.decorate();
  },
  /* après une frappe : le champ courant s'allonge, les suivants se décalent ; une frappe ailleurs termine l'extrait */
  snipEdit() {
    const sn = this.snip, ta = this.ta, d = ta.value.length - sn.len, p = ta.selectionStart;
    sn.len = ta.value.length;
    const at = d > 0 ? p - d : p, [a, b] = sn.stops[sn.i];
    if (at < a || at > b) return this.snipEnd();
    sn.stops = sn.stops.map(([x, y], j) => j === sn.i ? [x, y + d] : x >= b ? [x + d, y + d] : [x, y]);
  },
  snipIn() {                                        // le curseur est-il encore dans le champ courant ?
    const sn = this.snip; if (!sn) return false;
    const [a, b] = sn.stops[sn.i], s = this.ta.selectionStart, e = this.ta.selectionEnd;
    return s >= a && e <= b;
  },
  snipEnd() { if (this.snip) { this.snip = null; this._dk = null; this.decorate(); } }
};

/* ---- données d'autocomplétion ---- */
const MEMBERS = {
  python: { math: "sqrt pi e sin cos tan floor ceil log log10 exp pow fabs radians degrees hypot inf".split(" "), random: "random randint choice shuffle uniform sample seed randrange".split(" "),
    os: "path getcwd listdir mkdir makedirs remove rename environ getenv walk system".split(" "), sys: "argv exit stdin stdout stderr path version platform".split(" "),
    time: "time sleep perf_counter strftime localtime monotonic".split(" "), json: "dumps loads dump load".split(" ") },
  javascript: { console: "log error warn info table time timeEnd dir".split(" "), Math: "abs ceil floor round max min pow sqrt random sin cos tan PI E log trunc sign".split(" "),
    JSON: "stringify parse".split(" "), Object: "keys values entries assign freeze fromEntries".split(" "), Array: "from isArray of".split(" "), Promise: "all race resolve reject allSettled any".split(" "),
    process: "argv env exit stdout stdin cwd platform".split(" ") },
  go: { fmt: "Println Printf Sprintf Print Errorf Sprint Scan Scanln Fprintf".split(" "), strings: "Split Join Contains TrimSpace ToUpper ToLower Replace Fields HasPrefix HasSuffix Repeat".split(" "),
    strconv: "Atoi Itoa ParseFloat FormatInt".split(" "), os: "Args Exit Stdin Stdout Getenv ReadFile WriteFile".split(" "), math: "Sqrt Pow Sin Cos Abs Floor Ceil Max Min Pi".split(" "), time: "Now Sleep Since Millisecond Second".split(" ") },
  rust: { std: "io fs env collections thread time fmt".split(" ") },
  java: { System: "out in err exit currentTimeMillis nanoTime".split(" "), Math: "abs max min pow sqrt random floor ceil round PI".split(" ") }
};
MEMBERS.cpp = {
  std: ("cout cin cerr clog endl string vector map set unordered_map unordered_set array pair tuple optional variant deque list queue stack priority_queue "
    + "unique_ptr shared_ptr make_unique make_shared make_pair move swap sort stable_sort reverse find find_if count count_if accumulate min max min_element max_element "
    + "abs sqrt pow getline to_string stoi stol stod size_t function thread mutex lock_guard ifstream ofstream stringstream istringstream ostringstream setw setprecision fixed "
    + "runtime_error exception invalid_argument out_of_range numeric_limits iota fill copy transform all_of any_of none_of lower_bound upper_bound binary_search unique "
    + "begin end size ref cref chrono this_thread random_device mt19937 uniform_int_distribution uniform_real_distribution filesystem format").split(" "),
  chrono: "steady_clock system_clock high_resolution_clock duration duration_cast milliseconds microseconds nanoseconds seconds minutes hours".split(" "),
  this_thread: "sleep_for sleep_until get_id yield".split(" "),
  "*": ("push_back emplace_back pop_back push pop top front back size empty clear begin end rbegin rend insert erase find count at reserve resize "
    + "substr length c_str append replace data first second get reset swap contains").split(" ")
};
MEMBERS.c = {};
MEMBERS.python["*"] = ("append extend insert remove pop clear index count sort reverse copy keys values items get update setdefault "
  + "split join strip lstrip rstrip replace upper lower title startswith endswith find format encode decode isdigit isalpha add discard").split(" ");
MEMBERS.javascript["*"] = ("length push pop shift unshift slice splice map filter reduce forEach find findIndex includes indexOf join sort reverse concat some every flat flatMap at "
  + "split trim toUpperCase toLowerCase startsWith endsWith replace replaceAll padStart padEnd toString toFixed then catch finally addEventListener querySelector").split(" ");
MEMBERS.java.out = "println print printf".split(" ");
MEMBERS.java["*"] = "length size get set add remove contains isEmpty equals toString charAt substring indexOf trim split toUpperCase toLowerCase put getOrDefault keySet values nextInt nextLine nextDouble close".split(" ");
const HEADERS = {
  c: "stdio.h stdlib.h string.h math.h stdbool.h stdint.h stddef.h ctype.h time.h limits.h float.h assert.h errno.h signal.h stdarg.h unistd.h pthread.h".split(" "),
  cpp: ("iostream string vector map set unordered_map unordered_set array algorithm numeric cmath cstdio cstdlib cstring cstdint cassert iomanip sstream fstream "
    + "memory utility functional tuple optional variant deque list queue stack chrono thread mutex random limits stdexcept iterator filesystem format bitset climits").split(" ")
};
const GENERICS = W("vector map set unordered_map unordered_set multimap multiset array pair tuple optional variant deque list queue stack priority_queue unique_ptr shared_ptr weak_ptr function "
  + "make_unique make_shared static_cast dynamic_cast reinterpret_cast const_cast numeric_limits basic_string span atomic future promise Vec Option Result Box HashMap HashSet BTreeMap Rc Arc RefCell");
/* extraits : $1, ${1:texte} = champs (Tab / ⇧Tab), $0 = position finale, \t = une indentation, \$ = dollar */
const SNIP_C = {
  "#inc": ["#include <$1>$0", "#include <…>"], inc: ["#include <$1>$0", "#include <…>"], incl: ['#include "$1"$0', '#include "…"'],
  main: ["int main(void) {\n\t$0\n\treturn 0;\n}", "fonction main"],
  for: ["for (int ${1:i} = 0; ${2:i < n}; ${3:i++}) {\n\t$0\n}", "boucle for"],
  fori: ["for (int i = 0; i < ${1:n}; i++) {\n\t$0\n}", "for i de 0 à n"],
  if: ["if (${1:condition}) {\n\t$0\n}", "si"], ife: ["if (${1:condition}) {\n\t$2\n} else {\n\t$0\n}", "si / sinon"],
  elif: ["else if (${1:condition}) {\n\t$0\n}", "sinon si"], else: ["else {\n\t$0\n}", "sinon"],
  while: ["while (${1:condition}) {\n\t$0\n}", "tant que"], do: ["do {\n\t$0\n} while (${1:condition});", "faire… tant que"],
  sw: ["switch (${1:valeur}) {\n\tcase ${2:0}:\n\t\t$0\n\t\tbreak;\n\tdefault:\n\t\tbreak;\n}", "switch / case"],
  case: ["case ${1:0}:\n\t$0\n\tbreak;", "case"],
  st: ["struct ${1:Nom} {\n\t$0\n};", "struct"],
  fn: ["${1:void} ${2:nom}(${3}) {\n\t$0\n}", "fonction"],
  pf: ['printf("${1:%d}\\n"${2:, x});$0', "printf"], printf: ['printf("${1:%d}\\n"${2:, x});$0', "printf"],
  sf: ['scanf("${1:%d}", &${2:x});$0', "scanf"], scanf: ['scanf("${1:%d}", &${2:x});$0', "scanf"],
  mal: ["${1:int} *${2:t} = malloc(${3:n} * sizeof(${4:int}));$0", "malloc"],
  once: ["#ifndef ${1:NOM_H}\n#define ${2:NOM_H}\n\n$0\n\n#endif", "garde d'en-tête"]
};
const SNIPPETS = {
  c: SNIP_C,
  cpp: { ...SNIP_C,
    main: ["int main() {\n\t$0\n\treturn 0;\n}", "fonction main"],
    cout: ["std::cout << $1 << std::endl;$0", "std::cout << … << endl"], co: ["std::cout << $1 << std::endl;$0", "std::cout << … << endl"],
    coutn: ['std::cout << $1 << "\\n";$0', 'std::cout << … << "\\n"'],
    cerr: ["std::cerr << $1 << std::endl;$0", "std::cerr << …"], cin: ["std::cin >> $1;$0", "std::cin >> …"], ci: ["std::cin >> $1;$0", "std::cin >> …"],
    getl: ["std::getline(std::cin, ${1:ligne});$0", "getline"],
    uns: ["using namespace std;\n$0", "using namespace std"],
    ios: ["#include <iostream>\n\nint main() {\n\t$0\n\treturn 0;\n}", "programme de base"],
    for: ["for (int ${1:i} = 0; ${2:i < n}; ${3:++i}) {\n\t$0\n}", "boucle for"],
    fori: ["for (int i = 0; i < ${1:n}; ++i) {\n\t$0\n}", "for i de 0 à n"],
    forr: ["for (${1:const auto&} ${2:x} : ${3:v}) {\n\t$0\n}", "for (x : conteneur)"], fore: ["for (${1:const auto&} ${2:x} : ${3:v}) {\n\t$0\n}", "for (x : conteneur)"],
    vec: ["std::vector<${1:int}> ${2:v}$0;", "std::vector<…>"], str: ["std::string ${1:s}$0;", "std::string"],
    map: ["std::map<${1:std::string}, ${2:int}> ${3:m}$0;", "std::map<…, …>"], umap: ["std::unordered_map<${1:std::string}, ${2:int}> ${3:m}$0;", "std::unordered_map"],
    set: ["std::set<${1:int}> ${2:s}$0;", "std::set<…>"], pair: ["std::pair<${1:int}, ${2:int}> ${3:p}$0;", "std::pair<…, …>"],
    uptr: ["std::unique_ptr<${1:T}> ${2:p} = std::make_unique<${3:T}>($4);$0", "unique_ptr"],
    sptr: ["std::shared_ptr<${1:T}> ${2:p} = std::make_shared<${3:T}>($4);$0", "shared_ptr"],
    cl: ["class ${1:Nom} {\npublic:\n\t${2:Nom}();\n\t$0\nprivate:\n};", "class"], class: ["class ${1:Nom} {\npublic:\n\t$0\nprivate:\n};", "class"],
    st: ["struct ${1:Nom} {\n\t$0\n};", "struct"],
    tpl: ["template <typename ${1:T}>\n$0", "template <typename T>"],
    ns: ["namespace ${1:nom} {\n\n$0\n\n}", "namespace"],
    try: ["try {\n\t$1\n} catch (const ${2:std::exception}& e) {\n\t$0\n}", "try / catch"],
    lam: ["[${1:&}](${2:auto x}) { $0 }", "lambda"],
    all: ["${1:v}.begin(), ${2:v}.end()$0", "v.begin(), v.end()"],
    pb: ["push_back($1);$0", "push_back(…)"], eb: ["emplace_back($1);$0", "emplace_back(…)"]
  },
  python: {
    def: ["def ${1:nom}(${2}):\n\t${0:pass}", "fonction"], class: ["class ${1:Nom}:\n\tdef __init__(self${2}):\n\t\t${0:pass}", "classe"],
    for: ["for ${1:x} in ${2:liste}:\n\t$0", "boucle for"], fori: ["for i in range(${1:n}):\n\t$0", "for i in range(n)"],
    fore: ["for ${1:i}, ${2:x} in enumerate(${3:liste}):\n\t$0", "for … enumerate"],
    if: ["if ${1:condition}:\n\t$0", "si"], ife: ["if ${1:condition}:\n\t$2\nelse:\n\t$0", "si / sinon"], elif: ["elif ${1:condition}:\n\t$0", "sinon si"],
    while: ["while ${1:condition}:\n\t$0", "tant que"], try: ["try:\n\t$1\nexcept ${2:Exception} as e:\n\t$0", "try / except"],
    with: ["with open(${1:\"fichier.txt\"}) as ${2:f}:\n\t$0", "with open(…)"],
    main: ["def main():\n\t$0\n\n\nif __name__ == \"__main__\":\n\tmain()", "programme principal"], ifmain: ["if __name__ == \"__main__\":\n\t${0:main()}", "if __name__ == …"],
    pr: ["print($1)$0", "print(…)"], prf: ["print(f\"$1\")$0", "print(f\"…\")"], inp: ["${1:x} = input(\"${2:? }\")$0", "input(…)"],
    lc: ["[${1:x} for ${2:x} in ${3:liste}]$0", "liste en compréhension"], lam: ["lambda ${1:x}: $0", "lambda"]
  },
  javascript: {
    log: ["console.log($1);$0", "console.log(…)"], cl: ["console.log($1);$0", "console.log(…)"],
    fn: ["function ${1:nom}(${2}) {\n\t$0\n}", "fonction"], afn: ["(${1}) => {\n\t$0\n}", "fonction fléchée"], asf: ["async function ${1:nom}(${2}) {\n\t$0\n}", "fonction async"],
    for: ["for (let ${1:i} = 0; ${2:i < n}; ${3:i++}) {\n\t$0\n}", "boucle for"], forof: ["for (const ${1:x} of ${2:liste}) {\n\t$0\n}", "for … of"],
    forin: ["for (const ${1:k} in ${2:objet}) {\n\t$0\n}", "for … in"],
    if: ["if (${1:condition}) {\n\t$0\n}", "si"], ife: ["if (${1:condition}) {\n\t$2\n} else {\n\t$0\n}", "si / sinon"],
    while: ["while (${1:condition}) {\n\t$0\n}", "tant que"], try: ["try {\n\t$1\n} catch (${2:e}) {\n\t$0\n}", "try / catch"],
    class: ["class ${1:Nom} {\n\tconstructor(${2}) {\n\t\t$0\n\t}\n}", "classe"],
    imp: ["import ${2:x} from \"${1:module}\";$0", "import"], req: ["const ${2:x} = require(\"${1:module}\");$0", "require"],
    tpl: ["`\\${$1}`$0", "gabarit `${}`"], qs: ["document.querySelector(\"$1\")$0", "querySelector"],
    ael: ["addEventListener(\"${1:click}\", (${2:e}) => {\n\t$0\n});", "addEventListener"]
  },
  java: {
    sout: ["System.out.println($1);$0", "System.out.println"], pl: ["System.out.println($1);$0", "System.out.println"], souf: ["System.out.printf(\"$1%n\"$2);$0", "System.out.printf"],
    main: ["public static void main(String[] args) {\n\t$0\n}", "main"], psvm: ["public static void main(String[] args) {\n\t$0\n}", "main"],
    for: ["for (int ${1:i} = 0; ${2:i < n}; ${3:i++}) {\n\t$0\n}", "boucle for"], fori: ["for (int i = 0; i < ${1:n}; i++) {\n\t$0\n}", "for i de 0 à n"],
    fore: ["for (${1:var} ${2:x} : ${3:liste}) {\n\t$0\n}", "for (x : liste)"],
    if: ["if (${1:condition}) {\n\t$0\n}", "si"], ife: ["if (${1:condition}) {\n\t$2\n} else {\n\t$0\n}", "si / sinon"],
    while: ["while (${1:condition}) {\n\t$0\n}", "tant que"], try: ["try {\n\t$1\n} catch (${2:Exception} e) {\n\t$0\n}", "try / catch"],
    class: ["public class ${1:Nom} {\n\t$0\n}", "classe"], sc: ["Scanner ${1:sc} = new Scanner(System.in);$0", "Scanner"],
    list: ["List<${1:Integer}> ${2:liste} = new ArrayList<>();$0", "List<…>"], hmap: ["Map<${1:String}, ${2:Integer}> ${3:m} = new HashMap<>();$0", "Map<…, …>"]
  },
  rust: {
    pl: ["println!(\"{}\", $1);$0", "println!"], pln: ["println!(\"$1\");$0", "println!(\"…\")"], fmt: ["format!(\"{}\", $1)$0", "format!"],
    fn: ["fn ${1:nom}(${2}) {\n\t$0\n}", "fonction"], fnr: ["fn ${1:nom}(${2}) -> ${3:i32} {\n\t$0\n}", "fonction → valeur"],
    main: ["fn main() {\n\t$0\n}", "main"], for: ["for ${1:x} in ${2:0..n} {\n\t$0\n}", "boucle for"],
    if: ["if ${1:condition} {\n\t$0\n}", "si"], ife: ["if ${1:condition} {\n\t$2\n} else {\n\t$0\n}", "si / sinon"],
    while: ["while ${1:condition} {\n\t$0\n}", "tant que"], loop: ["loop {\n\t$0\n}", "loop"],
    match: ["match ${1:valeur} {\n\t${2:_} => $0,\n}", "match"], st: ["struct ${1:Nom} {\n\t$0\n}", "struct"],
    impl: ["impl ${1:Nom} {\n\t$0\n}", "impl"], lm: ["let mut ${1:x} = $0;", "let mut"], vec: ["let ${1:v}: Vec<${2:i32}> = Vec::new();$0", "Vec::new()"],
    test: ["#[test]\nfn ${1:teste}() {\n\t$0\n}", "test"]
  },
  go: {
    pl: ["fmt.Println($1)$0", "fmt.Println"], pf: ["fmt.Printf(\"${1:%v}\\n\", $2)$0", "fmt.Printf"],
    fn: ["func ${1:nom}(${2}) {\n\t$0\n}", "fonction"], main: ["func main() {\n\t$0\n}", "main"],
    for: ["for ${1:i} := 0; ${2:i < n}; ${3:i++} {\n\t$0\n}", "boucle for"], forr: ["for ${1:_}, ${2:x} := range ${3:liste} {\n\t$0\n}", "for … range"],
    if: ["if ${1:condition} {\n\t$0\n}", "si"], iferr: ["if err != nil {\n\t${0:return err}\n}", "if err != nil"],
    st: ["type ${1:Nom} struct {\n\t$0\n}", "struct"], sw: ["switch ${1:valeur} {\ncase ${2:0}:\n\t$0\n}", "switch"]
  },
  csharp: {
    cw: ["Console.WriteLine($1);$0", "Console.WriteLine"], rl: ["Console.ReadLine()$0", "Console.ReadLine"],
    for: ["for (int ${1:i} = 0; ${2:i < n}; ${3:i++})\n{\n\t$0\n}", "boucle for"], fore: ["foreach (var ${1:x} in ${2:liste})\n{\n\t$0\n}", "foreach"],
    if: ["if (${1:condition})\n{\n\t$0\n}", "si"], while: ["while (${1:condition})\n{\n\t$0\n}", "tant que"],
    class: ["class ${1:Nom}\n{\n\t$0\n}", "classe"], try: ["try\n{\n\t$1\n}\ncatch (${2:Exception} e)\n{\n\t$0\n}", "try / catch"]
  },
  kotlin: {
    pl: ["println($1)$0", "println"], fn: ["fun ${1:nom}(${2}) {\n\t$0\n}", "fonction"], main: ["fun main() {\n\t$0\n}", "main"],
    for: ["for (${1:x} in ${2:0 until n}) {\n\t$0\n}", "boucle for"], if: ["if (${1:condition}) {\n\t$0\n}", "si"],
    when: ["when (${1:valeur}) {\n\t${2:0} -> $0\n\telse -> {}\n}", "when"], class: ["class ${1:Nom}(${2}) {\n\t$0\n}", "classe"], dc: ["data class ${1:Nom}(${0:val x: Int})", "data class"]
  },
  php: {
    echo: ["echo $1;$0", "echo"], fn: ["function ${1:nom}(${2}) {\n\t$0\n}", "fonction"],
    fore: ["foreach (${1:\\$liste} as ${2:\\$x}) {\n\t$0\n}", "foreach"], for: ["for (${1:\\$i = 0}; ${2:\\$i < \\$n}; ${3:\\$i++}) {\n\t$0\n}", "boucle for"],
    if: ["if (${1:condition}) {\n\t$0\n}", "si"], class: ["class ${1:Nom} {\n\t$0\n}", "classe"], vd: ["var_dump($1);$0", "var_dump"]
  },
  ruby: {
    def: ["def ${1:nom}${2}\n\t$0\nend", "méthode"], class: ["class ${1:Nom}\n\tdef initialize${2}\n\t\t$0\n\tend\nend", "classe"],
    each: ["each do |${1:x}|\n\t$0\nend", "each do |x|"], if: ["if ${1:condition}\n\t$0\nend", "si"], times: ["${1:n}.times do |${2:i}|\n\t$0\nend", "n.times"]
  },
  lua: {
    fn: ["function ${1:nom}(${2})\n\t$0\nend", "fonction"], lfn: ["local function ${1:nom}(${2})\n\t$0\nend", "fonction locale"],
    for: ["for ${1:i} = ${2:1}, ${3:n} do\n\t$0\nend", "boucle for"], forp: ["for ${1:k}, ${2:v} in ipairs(${3:t}) do\n\t$0\nend", "for … ipairs"],
    if: ["if ${1:condition} then\n\t$0\nend", "si"], while: ["while ${1:condition} do\n\t$0\nend", "tant que"]
  },
  bash: {
    sb: ["#!/usr/bin/env bash\nset -euo pipefail\n\n$0", "en-tête de script"],
    if: ["if [[ ${1:condition} ]]; then\n\t$0\nfi", "si"], ife: ["if [[ ${1:condition} ]]; then\n\t$2\nelse\n\t$0\nfi", "si / sinon"],
    for: ["for ${1:x} in ${2:1 2 3}; do\n\t$0\ndone", "boucle for"], fori: ["for ((i = 0; i < ${1:n}; i++)); do\n\t$0\ndone", "for ((i…))"],
    while: ["while ${1:condition}; do\n\t$0\ndone", "tant que"], rl: ["while IFS= read -r ${1:ligne}; do\n\t$0\ndone < ${2:fichier}", "lire ligne par ligne"],
    fn: ["${1:nom}() {\n\t$0\n}", "fonction"], case: ["case ${1:\\$x} in\n\t${2:motif})\n\t\t$0\n\t\t;;\n\t*)\n\t\t;;\nesac", "case"]
  },
  dart: { pl: ["print($1);$0", "print"], main: ["void main() {\n\t$0\n}", "main"], for: ["for (var ${1:i} = 0; ${2:i < n}; ${3:i++}) {\n\t$0\n}", "boucle for"] },
  zig: { pl: ["std.debug.print(\"${1:{}}\\n\", .{$2});$0", "std.debug.print"], fn: ["fn ${1:nom}(${2}) ${3:void} {\n\t$0\n}", "fonction"] },
  julia: { fn: ["function ${1:nom}(${2})\n\t$0\nend", "fonction"], for: ["for ${1:i} in ${2:1:n}\n\t$0\nend", "boucle for"], pl: ["println($1)$0", "println"] },
  r: { fn: ["${1:nom} <- function(${2}) {\n\t$0\n}", "fonction"], for: ["for (${1:i} in ${2:1:n}) {\n\t$0\n}", "boucle for"] },
  haskell: { main: ["main :: IO ()\nmain = do\n\t$0", "main"] },
  perl: { sub: ["sub ${1:nom} {\n\tmy (${2:\\$x}) = @_;\n\t$0\n}", "sub"], fore: ["foreach my ${1:\\$x} (${2:@liste}) {\n\t$0\n}", "foreach"] },
  web: {
    html: ["<!doctype html>\n<html lang=\"fr\">\n<head>\n\t<meta charset=\"utf-8\">\n\t<title>${1:Titre}</title>\n</head>\n<body>\n\t$0\n</body>\n</html>", "page HTML"],
    div: ["<div class=\"$1\">$0</div>", "<div>"], a: ["<a href=\"$1\">$0</a>", "<a href>"], img: ["<img src=\"$1\" alt=\"$2\">$0", "<img>"],
    ul: ["<ul>\n\t<li>$0</li>\n</ul>", "<ul><li>"], btn: ["<button>$0</button>", "<button>"], script: ["<script src=\"${1:script.js}\"><\/script>$0", "<script>"],
    link: ["<link rel=\"stylesheet\" href=\"${1:style.css}\">$0", "feuille de style"], p: ["<p>$0</p>", "<p>"], h1: ["<h1>$0</h1>", "<h1>"]
  }
};
SNIPPETS.typescript = { ...SNIPPETS.javascript, iface: ["interface ${1:Nom} {\n\t$0\n}", "interface"], type: ["type ${1:Nom} = $0;", "type"] };
/* extraits du langage + ceux d'une extension personnelle (« snippets »: {"déclencheur": "corps"}) */
function snippetsOf(id) {
  const x = S.ext[id], own = x && x.snippets;
  if (!own) return SNIPPETS[id] || null;
  const add = {};
  for (const [k, b] of Object.entries(own)) add[k] = Array.isArray(b) ? b : [String(b), "extrait"];
  return { ...(SNIPPETS[id] || {}), ...add };
}
const snipPreview = b => b.replace(/\\\$/g, "$").replace(/\$\{\d+:([^}]*)\}/g, "$1").replace(/\$\d+/g, "").replace(/\t/g, "  ");
MEMBERS.typescript = MEMBERS.javascript;
MEMBERS.web = MEMBERS.javascript;
function acCandidates(word) {
  const lw = word.toLowerCase(), seen = new Set(), out = [];
  const L = langRx(ED.lang), stat = [...[...L.kw].map(w => [w, "mot-clé"]), ...[...L.ty].map(w => [w, "type"]), ...[...L.fn].map(w => [w, "fonction"]), ...[...L.co].map(w => [w, "constante"])];
  const fileWords = new Set();
  for (const [f, d] of Object.entries(S.docs)) if (langOfFile(f) === ED.lang || f === S.file) for (const m of (d.text || "").matchAll(/\b[A-Za-z_]\w{2,}\b/g)) fileWords.add(m[0]);
  const push = (w, k) => { if (w === word || seen.has(w) || !w.toLowerCase().startsWith(lw)) return; seen.add(w); out.push([w, k]); };
  const SN = snippetsOf(ED.lang) || {};
  Object.keys(SN).filter(t => /^\w/.test(t) && t.toLowerCase().startsWith(lw)).sort((a, b) => (a !== word) - (b !== word) || a.length - b.length)
    .forEach(t => { seen.add(t); out.push([t, SN[t][1], SN[t][0]]); });
  stat.forEach(([w, k]) => { if (w.startsWith(word)) push(w, k); });
  [...fileWords].sort().forEach(w => push(w, "dans le projet"));
  stat.forEach(([w, k]) => push(w, k));
  return out;
}

/* ---- rechercher / remplacer ---- */
const FIND = { open: false, q: "", cs: false, word: false, re: false, matches: [], cur: -1 };
function findRegex() {
  if (!FIND.q) return null;
  let src = FIND.re ? FIND.q : FIND.q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  if (FIND.word) src = "(?<![\\w])(?:" + src + ")(?![\\w])";
  try { return new RegExp(src, FIND.cs ? "g" : "gi"); } catch { return null; }
}
function findCompute(jump) {
  const rx = findRegex(), v = ED.ta.value;
  FIND.matches = [];
  $("#fInput").classList.toggle("bad", !!FIND.q && !rx);
  if (rx) {
    let m;
    while ((m = rx.exec(v)) && FIND.matches.length < 5000) {
      if (m[0].length === 0) { rx.lastIndex++; continue; }
      FIND.matches.push([m.index, m.index + m[0].length]);
    }
  }
  const p = ED.ta.selectionStart;
  let i = FIND.matches.findIndex(([s]) => s >= p);
  FIND.cur = FIND.matches.length ? (i < 0 ? 0 : i) : -1;
  findCount();
  if (jump && FIND.cur >= 0) ED.reveal(FIND.matches[FIND.cur][0]);
  ED._dk = null; ED.decorate();
}
function findCount() {
  const n = FIND.matches.length;
  $("#fCount").textContent = !FIND.q ? "" : n ? `${FIND.cur + 1} / ${n}` : "Aucun résultat";
}
function findStep(dir) {
  if (!FIND.matches.length) return;
  FIND.cur = (FIND.cur + dir + FIND.matches.length) % FIND.matches.length;
  const [s, e] = FIND.matches[FIND.cur];
  ED.ta.setSelectionRange(s, e);
  ED.reveal(s); findCount(); ED._dk = null; ED.decorate();
}
function findOpen(replace) {
  if (!S.file) return;
  const bar = $("#findbar"), sel = ED.ta.value.slice(ED.ta.selectionStart, ED.ta.selectionEnd);
  FIND.open = true; bar.hidden = false;
  $("#fRepRow").hidden = !replace;
  if (sel && !sel.includes("\n")) { $("#fInput").value = sel; FIND.q = sel; }
  findCompute(true);
  const inp = $("#fInput"); inp.focus(); inp.select();
}
function findClose() {
  if (!FIND.open) return;
  FIND.open = false; $("#findbar").hidden = true; ED._dk = null; ED.decorate(); ED.ta.focus();
}
function findReplaceOne() {
  if (FIND.cur < 0) return;
  const [s, e] = FIND.matches[FIND.cur];
  ED.ta.setSelectionRange(s, e);
  const rx = findRegex(), txt = ED.ta.value.slice(s, e);
  ED.insert(FIND.re && rx ? txt.replace(new RegExp(rx.source, rx.flags.replace("g", "")), $("#fRep").value) : $("#fRep").value, true);
  findCompute(true);
}
function findReplaceAll() {
  const rx = findRegex(); if (!rx || !FIND.matches.length) return;
  const n = FIND.matches.length, top = ED.ta.scrollTop;
  ED.ta.setSelectionRange(0, ED.ta.value.length);
  ED.insert(ED.ta.value.replace(rx, FIND.re ? $("#fRep").value : () => $("#fRep").value), true);
  ED.ta.scrollTop = top; ED.sync();
  findCompute(false); toast(`${n} remplacement(s)`, "ok", 1800);
}
$("#fInput").addEventListener("input", e => { FIND.q = e.target.value; findCompute(true); });
$("#fInput").addEventListener("keydown", e => {
  if (e.key === "Enter") { e.preventDefault(); findStep(e.shiftKey ? -1 : 1); }
  else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); findClose(); }
});
$("#fRep").addEventListener("keydown", e => {
  if (e.key === "Enter") { e.preventDefault(); findReplaceOne(); }
  else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); findClose(); }
});
$("#findbar").addEventListener("keydown", e => { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); findClose(); } });
$("#fPrev").addEventListener("click", () => findStep(-1));
$("#fNext").addEventListener("click", () => findStep(1));
$("#fClose").addEventListener("click", findClose);
$("#fRepOne").addEventListener("click", findReplaceOne);
$("#fRepAll").addEventListener("click", findReplaceAll);
[["fCase", "cs"], ["fWord", "word"], ["fRe", "re"]].forEach(([id, k]) => $("#" + id).addEventListener("click", e => {
  FIND[k] = !FIND[k]; e.currentTarget.setAttribute("aria-pressed", FIND[k]); findCompute(true);
}));


/* ---- événements de l'éditeur ---- */
ED.ta.addEventListener("input", e => {
  if (ED.snip) ED.snipEdit();
  if (S.file && S.docs[S.file]) diagsFollowEdit(S.docs[S.file].text || "", ED.ta.value);
  ED.render();
  if (S.file) {
    const d = S.docs[S.file];
    d.text = ED.ta.value;
    liveSchedule();
    setDirty(S.file, d.text !== d.saved);
  }
  ED.tipHide();
  if ((e.inputType === "insertText" && e.data && e.data.length === 1) || (e.inputType === "deleteContentBackward" && ED.acOpen)) ED.acUpdate(false); else ED.acClose();
});
ED.ta.addEventListener("scroll", () => { ED.sync(); ED.tipHide(); if (ED.acOpen) ED.acDraw(); });
["click", "keyup", "select", "focus"].forEach(ev => ED.ta.addEventListener(ev, () => ED.caret()));
ED.ta.addEventListener("blur", () => { setTimeout(() => { if (document.activeElement !== ED.ta) ED.acClose(); ED.caret(); }, 120); });
ED.ta.addEventListener("mousedown", () => { ED.acClose(); ED.snipEnd(); });
$("#ac").addEventListener("mousedown", e => { e.preventDefault(); const d = e.target.closest("[data-i]"); if (d) ED.acAccept(+d.dataset.i); });

/* survol : message de l'erreur sous la souris */
let tipTimer = 0;
ED.ta.addEventListener("mousemove", e => {
  clearTimeout(tipTimer);
  if (!S.diags.length) return ED.tipHide();
  tipTimer = setTimeout(() => {
    const r = ED.ta.getBoundingClientRect();
    const l = Math.floor((e.clientY - r.top + ED.ta.scrollTop - PAD_Y) / ED.lh);
    if (l < 0 || l >= ED.starts().length) return ED.tipHide();
    const c = colAt(ED.lineText(l), Math.floor((e.clientX - r.left + ED.ta.scrollLeft - PAD_X) / ED.charW + .0));
    const pos = ED.starts()[l] + c;
    const hit = (ED._diagRanges || []).filter(([s, z]) => pos >= s - 1 && pos <= z && ED.lineOf(s) === l).map(x => x[3]);
    hit.length ? ED.tipShow(hit.map(ED.tipFor).join("<br>"), e.clientX, e.clientY) : ED.tipHide();
  }, 160);
});
ED.ta.addEventListener("mouseleave", () => { clearTimeout(tipTimer); ED.tipHide(); });
$("#gutter").addEventListener("mouseover", e => {
  const g = e.target.closest("[data-tip]");
  if (!g) return ED.tipHide();
  const d = S.diags.find(x => x.file === S.file && x.line === +g.dataset.l);
  const r = g.getBoundingClientRect();
  ED.tipShow(d ? ED.tipFor(d) : esc(g.dataset.tip), r.right, r.top);
});
$("#gutter").addEventListener("mouseleave", () => ED.tipHide());
$("#ruler").addEventListener("click", e => {
  const r = $("#ruler").getBoundingClientRect();
  const total = Math.max(ED.starts().length * ED.lh + 2 * PAD_Y, ED.code.clientHeight);
  ED.goto(Math.round(((e.clientY - r.top) / r.height * total - PAD_Y) / ED.lh) + 1);
});

const PAIRS = { "(": ")", "[": "]", "{": "}", '"': '"', "'": "'" };
ED.ta.addEventListener("keydown", e => {
  if (e.isComposing) return;
  const ta = ED.ta, v = ta.value, s = ta.selectionStart, en = ta.selectionEnd;
  const mod = e.ctrlKey || e.metaKey, k = e.key.toLowerCase();
  if (ED.acOpen) {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); ED.acMove(e.key === "ArrowDown" ? 1 : -1); return; }
    if (e.key === "Enter" || e.key === "Tab") { e.preventDefault(); ED.acAccept(); return; }
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); ED.acClose(); return; }
    if (["ArrowLeft", "ArrowRight", "Home", "End", "PageUp", "PageDown"].includes(e.key)) ED.acClose();
  }
  if (e.key === "Escape" && ED.snip) ED.snipEnd();
  if (e.key === "Escape" && FIND.open) { findClose(); return; }
  if (mod && e.key === " ") { e.preventDefault(); ED.acUpdate(true); return; }
  if (mod && !e.altKey && k === "d") { e.preventDefault(); ED.duplicateLines(); return; }
  if (mod && !e.altKey && (e.key === "/" || e.code === "Slash")) {
    e.preventDefault();
    const [co, cc] = commentOf(ED.lang), eo = reEsc(co), ec = reEsc(cc);
    const rxOn = new RegExp("^\\s*" + eo), rxOff = new RegExp("^(\\s*)" + eo + " ?"), rxEnd = cc ? new RegExp(" ?" + ec + "\\s*$") : null;
    ED.transformLines(ls => {
      const all = ls.filter(l => l.trim()).every(l => rxOn.test(l));
      return ls.map(l => !l.trim() ? l : all ? (rxEnd ? l.replace(rxOff, "$1").replace(rxEnd, "") : l.replace(rxOff, "$1")) : l.replace(/^(\s*)/, "$1" + co + " ") + (cc ? " " + cc : ""));
    });
    return;
  }
  if (mod && !e.altKey && ["+", "=", "-", "0"].includes(e.key)) {
    e.preventDefault(); ED.setFont(e.key === "0" ? 13.5 : (prefs.fs || 13.5) + (e.key === "-" ? -1 : 1)); return;
  }
  if (e.altKey && !mod && (e.key === "ArrowUp" || e.key === "ArrowDown")) { e.preventDefault(); ED.moveLines(e.key === "ArrowUp" ? -1 : 1); return; }
  /* Alt+< : « << » (« >> » sur une ligne cin), Alt+> : « >> » — espaces compris */
  if (e.altKey && !mod && (e.key === "<" || e.key === ">") && !(e.getModifierState && e.getModifierState("AltGraph"))) {
    e.preventDefault();
    const before = v.slice(v.lastIndexOf("\n", s - 1) + 1, s);
    const op = e.key === ">" || /\b(cin|getline)\b|>>/.test(before) && !/<</.test(before) ? ">>" : "<<";
    ED.insert((/\s$/.test(before) || !before ? "" : " ") + op + (v[en] === " " ? "" : " "));
    return;
  }
  if (mod && !e.altKey) return;
  if (e.key === "Tab") {
    e.preventDefault();
    if (ED.snip && !ED.snipIn()) ED.snipEnd();
    if (ED.snip) { ED.snipGo(ED.snip.i + (e.shiftKey ? -1 : 1)); return; }
    if (!e.shiftKey && s === en && !ED.mask()[s - 1]) {
      const sn = ED.snipAt();
      if (sn) { ED.snipExpand(sn[1][0], s - sn[0].length, s); return; }
    }
    const U = indentOf(ED.lang), rxU = new RegExp("^ {1," + Math.max(1, U.length) + "}|^\\t");
    if (e.shiftKey) ED.transformLines(ls => ls.map(l => l.replace(rxU, "")));
    else if (v.slice(s, en).includes("\n")) ED.transformLines(ls => ls.map(l => U + l));
    else ED.insert(U);
    return;
  }
  if (e.key === "Enter") {
    e.preventDefault();
    const lineStart = v.lastIndexOf("\n", s - 1) + 1;
    const indent = v.slice(lineStart, s).match(/^[ \t]*/)[0];
    const prev = v.slice(lineStart, s).trimEnd();
    const U = indentOf(ED.lang), L = ED.lang, closer = { "{": "}", "[": "]", "(": ")" }[prev.slice(-1)];
    const opens = !!closer || (L === "python" && /:$/.test(prev)) || (["lua", "ruby", "julia", "bash"].includes(L) && /(\b(then|do)|\bdo \|[^|]*\|)$|^\s*(local\s+)?(function|def|class|module|while|for|if|begin)\b(?!.*\bend\b)/.test(prev)) || (L === "haskell" && /(\bwhere|\bdo|=)$/.test(prev));
    if (closer && v[en] === closer) {
      ED.insert("\n" + indent + U + "\n" + indent);
      const p = s + 1 + indent.length + U.length;
      ta.setSelectionRange(p, p);
    } else ED.insert("\n" + indent + (opens ? U : ""));
    return;
  }
  if (e.key === "Backspace" && s === en && s > 0 && (PAIRS[v[s - 1]] === v[s] || (v[s - 1] === "<" && v[s] === ">"))) {
    e.preventDefault(); ta.setSelectionRange(s - 1, s + 1); document.execCommand("delete"); return;
  }
  const plain = !e.metaKey && (!(e.ctrlKey || e.altKey) || (e.getModifierState && e.getModifierState("AltGraph")));
  if (!plain) return;
  if (PAIRS[e.key]) {
    const close = PAIRS[e.key], quote = e.key === close;
    if (s !== en) { e.preventDefault(); ED.insert(e.key + v.slice(s, en) + close); ta.setSelectionRange(s + 1, en + 1); return; }
    if (quote && v[s] === e.key) { e.preventDefault(); ta.setSelectionRange(s + 1, s + 1); return; }
    const prev = v[s - 1], next = v[s], inCode = !ED.mask()[s - 1];
    const nextOk = next === undefined || /[\s)\]};,]/.test(next);
    if (nextOk && (!quote || (inCode && !/[\w"'\\]/.test(prev || "")))) {
      e.preventDefault(); ED.insert(e.key + close); ta.setSelectionRange(s + 1, s + 1);
    }
    return;
  }
  if ((e.key === ")" || e.key === "]" || e.key === "}") && s === en && v[s] === e.key) { e.preventDefault(); ta.setSelectionRange(s + 1, s + 1); return; }
  /* chevrons : #include <…>, template <…>, vector<…>, List<…> ; « > » passe par-dessus celui déjà inséré */
  if ((e.key === "<" || e.key === ">") && s === en && !ED.mask()[s - 1]) {
    const before = v.slice(v.lastIndexOf("\n", s - 1) + 1, s);
    if (e.key === ">") {
      if (v[s] === ">" && (before.match(/</g) || []).length > (before.match(/>/g) || []).length && !/<<|->/.test(before.slice(-2))) { e.preventDefault(); ta.setSelectionRange(s + 1, s + 1); }
      return;
    }
    const L = ED.lang, w = (/([A-Za-z_]\w*)$/.exec(before) || [])[1];
    const inc = ["c", "cpp"].includes(L) && /^\s*#\s*include\s*$/.test(before);
    const gen = w && ["cpp", "java", "kotlin", "csharp", "rust", "typescript", "dart"].includes(L) && (langRx(L).ty.has(w) || GENERICS.has(w) || (L !== "cpp" && /^[A-Z]/.test(w)));
    const tpl = L === "cpp" && /\btemplate\s*$/.test(before);
    if ((inc || gen || tpl) && (v[s] === undefined || /[\s)\]};,>]/.test(v[s]))) {
      e.preventDefault(); ED.insert("<>"); ta.setSelectionRange(s + 1, s + 1);
      if (inc) ED.acUpdate(true);
    }
    return;
  }
  if (e.key === "}" && s === en) {
    const before = v.slice(v.lastIndexOf("\n", s - 1) + 1, s);
    const U = indentOf(ED.lang);
    if (/^[ \t]+$/.test(before) && before.endsWith(U)) { e.preventDefault(); ta.setSelectionRange(s - U.length, s); ED.insert("}"); }
  }
});

/* ------------------------------------------------------------------ projets & fichiers */
function sortedProjects(list) {
  const pin = new Set(S.meta.pinned), when = p => S.meta.opened[p.name] || p.modified * 1000;
  const cmp = (a, b) => prefs.sort === "name" ? a.name.localeCompare(b.name, "fr", { sensitivity: "base" }) : when(b) - when(a) || a.name.localeCompare(b.name);
  return [list.filter(p => pin.has(p.name)).sort(cmp), list.filter(p => !pin.has(p.name)).sort(cmp)];
}
const langName = id => (S.ext[id] && S.ext[id].name) || (id ? id : "langage inconnu");
const langAbbr = id => (S.ext[id] && S.ext[id].abbr) || "?";
function renderProjects() {
  const f = $("#projFilter").value.trim().toLowerCase();
  const list = S.projects.filter(p => !f || p.name.toLowerCase().includes(f) || langName(p.lang).toLowerCase().includes(f));
  const [pinned, others] = sortedProjects(list);
  $("#projCount").textContent = S.projects.length || "";
  $("#projSort").textContent = prefs.sort === "name" ? "A → Z" : "Récents";
  const item = p => {
    const on = S.meta.pinned.includes(p.name), x = S.ext[p.lang];
    return `<li data-p="${esc(p.name)}" class="${S.project === p.name ? "active" : ""}">
      <button class="pitem" ${S.project === p.name ? 'aria-current="true"' : ""}><span class="pi" style="${langStyle(x)}">${esc(langAbbr(p.lang))}</span>
      <span style="min-width:0;flex:1"><span class="pn" style="display:block">${esc(p.name)}</span><span class="pf" style="display:block">${esc(langName(p.lang))}</span></span></button>
      <button class="pin" data-pin="${esc(p.name)}" aria-pressed="${on}" aria-label="${on ? "Désépingler" : "Épingler"} ${esc(p.name)}" title="${on ? "Désépingler" : "Épingler en haut de la liste"}">${icon("pin")}</button>
    </li>`;
  };
  $("#projList").innerHTML = list.length
    ? (pinned.length ? `<li class="grp" aria-hidden="true">Épinglés</li>${pinned.map(item).join("")}${others.length ? `<li class="grp" aria-hidden="true">Projets</li>` : ""}` : "") + others.map(item).join("")
    : `<li class="empty">${S.projects.length ? "Aucun résultat" : "Aucun projet pour l'instant"}</li>`;
  const recent = sortedProjects(S.projects).flat().slice(0, 6);
  $("#recent").innerHTML = recent.map(p => `<button data-p="${esc(p.name)}"><b>${esc(p.name)}</b><small>${esc(langName(p.lang))}</small></button>`).join("");
}
let metaTimer = 0;
function saveMeta() {
  clearTimeout(metaTimer);
  metaTimer = setTimeout(() => api("/api/meta", { pinned: S.meta.pinned, opened: S.meta.opened }).catch(() => {}), 300);
}
function togglePin(name) {
  const i = S.meta.pinned.indexOf(name);
  if (i >= 0) S.meta.pinned.splice(i, 1); else S.meta.pinned.push(name);
  saveMeta(); renderProjects();
  toast(i >= 0 ? `« ${name} » désépinglé` : `« ${name} » épinglé en haut de la liste`, "info", 1600);
}
$("#projList").addEventListener("click", e => {
  const pin = e.target.closest("[data-pin]");
  if (pin) { e.stopPropagation(); return togglePin(pin.dataset.pin); }
  const li = e.target.closest("li[data-p]"); if (li) openProject(li.dataset.p);
});
$("#projList").addEventListener("contextmenu", e => {
  const li = e.target.closest("li[data-p]"); if (!li) return;
  e.preventDefault();
  const on = S.meta.pinned.includes(li.dataset.p);
  ctxMenu([{ label: on ? "Désépingler" : "Épingler en haut", icon: "pin", action: () => togglePin(li.dataset.p) },
           { label: "Ouvrir", icon: "folder", action: () => openProject(li.dataset.p) },
           "-", { label: "Exporter en .zip", icon: "download", action: () => exportProject(li.dataset.p) }], e.clientX, e.clientY, li);
});
$("#recent").addEventListener("click", e => { const d = e.target.closest("[data-p]"); if (d) openProject(d.dataset.p); });
$("#projSort").addEventListener("click", () => { prefs.sort = prefs.sort === "name" ? "recent" : "name"; savePrefs(); renderProjects(); });
$("#projFilter").addEventListener("input", renderProjects);

async function loadProjects() {
  S.projects = await api("/api/projects");
  renderProjects();
}

function applyInfo(p) {
  S.info = p; S.files = p.files; S.conf = p.conf || {};
  const pr = S.projects.find(x => x.name === p.name); if (pr) pr.lang = p.lang;
}
async function openProject(name) {
  if (S.project && anyDirty()) await saveAll();
  try {
    const p = await api("/api/project?" + qs({ name }));
    if (S.project && S.project !== name && S.session.running && S.session.kind !== "run") api("/api/stop", {}).catch(() => {});
    S.project = name; S.docs = {}; S.diags = []; S.file = null; updateConsoleBadge();
    applyInfo(p);
    prefs.lastProject = name; savePrefs();
    S.meta.opened[name] = Date.now(); saveMeta();
    $("#welcome").classList.remove("show");
    $("#projName").textContent = name;
    const saved = (prefs.tabs && prefs.tabs[name]) || [];
    S.tabs = saved.filter(f => S.files.includes(f));
    if (!S.tabs.length && p.main) S.tabs = [p.main];
    renderProjects(); renderLang(); renderTree(); runFieldsLoad(); updateButtons();
    const first = (prefs.curFile && prefs.curFile[name] && S.tabs.includes(prefs.curFile[name])) ? prefs.curFile[name] : S.tabs[0];
    if (first) await openFile(first); else { S.file = null; ED.set(""); renderTabs(); editorEmpty("Ce projet est vide : créez un fichier (bouton +)."); }
    if (prefs.insp === "snaps") snapsLoad();
    if (activeTab === "pkgs") pkgsLoad();
    document.title = `${name} · Forge Code`;
    const ch = S.conf && S.conf.challenge;
    progProject(ch && ch.lang && ch.id ? ch : null);
    if (PG.data) progBadge(); else progLoad("");
  } catch (e) { toast(e.message, "error"); }
}
async function reloadInfo() {
  if (!S.project) return;
  const p = await api("/api/project?" + qs({ name: S.project }));
  applyInfo(p);
  S.tabs = S.tabs.filter(f => S.files.includes(f));
  renderTree(); renderTabs(); renderLang(); renderProjects();
}

/* ---- arbre des fichiers ---- */
function extClass(f) { return langOfFile(f) === S.info?.lang ? "l" : ""; }
function renderTree() {
  const box = $("#tree");
  if (!S.project) { box.innerHTML = `<div class="empty">Aucun projet ouvert.</div>`; return; }
  if (!S.files.length) { box.innerHTML = `<div class="empty">Dossier vide.</div>`; return; }
  const errs = f => S.diags.filter(x => x.file === f && x.severity === "error").length;
  let h = "", lastDir = [];
  const files = [...S.files].sort((a, b) => {
    const da = a.includes("/"), db = b.includes("/");
    return a === S.info.main ? -1 : b === S.info.main ? 1 : da !== db ? (da ? 1 : -1) : a.localeCompare(b, "fr", { numeric: true });
  });
  for (const f of files) {
    const parts = f.split("/"), dirs = parts.slice(0, -1), name = parts[parts.length - 1];
    dirs.forEach((d, i) => { if (lastDir[i] !== d) { h += `<div class="tn dir" style="padding-left:${8 + i * 14}px">${icon("folder")}<span class="nm">${esc(d)}</span></div>`; lastDir = dirs.slice(0, i + 1); } });
    lastDir = dirs;
    const ext = name.lastIndexOf(".") > 0 ? name.split(".").pop().slice(0, 4) : "·", n = errs(f);
    h += `<button class="tn ${S.tabs.includes(f) ? "open" : ""} ${f === S.file ? "cur" : ""}" role="treeitem" data-f="${esc(f)}" style="padding-left:${8 + dirs.length * 14}px" title="${esc(f)}${f === S.info.main ? " — fichier principal" : ""}">
      <span class="ext ${extClass(f)}">${esc(ext)}</span><span class="nm">${esc(name)}</span>${f === S.info.main ? `<span class="star" title="Fichier principal">★</span>` : ""}${n ? `<span class="errc">${n}</span>` : ""}</button>`;
  }
  if (S.info.truncated) h += `<div class="empty">Liste tronquée (trop de fichiers).</div>`;
  box.innerHTML = h;
}
$("#tree").addEventListener("click", e => { const t = e.target.closest("[data-f]"); if (t) openFile(t.dataset.f); });
$("#tree").addEventListener("contextmenu", e => { const t = e.target.closest("[data-f]"); e.preventDefault(); fileMenu(t ? t.dataset.f : null, e.clientX, e.clientY, t); });
$("#btnFileNew").addEventListener("click", () => fileNew());
$("#btnFilesRefresh").addEventListener("click", () => reloadInfo().then(() => toast("Dossier relu", "info", 1200)).catch(e => toast(e.message, "error")));

/* ---- onglets des fichiers ouverts ---- */
function renderTabs() {
  $("#ftabList").innerHTML = S.tabs.map(f => {
    const d = S.docs[f], dirty = d && d.text !== d.saved;
    const errs = S.diags.filter(x => x.file === f && x.severity === "error").length;
    const name = f.split("/").pop(), ext = name.includes(".") ? name.split(".").pop() : "txt";
    return `<div class="ftab ${f === S.file ? "active" : ""} ${dirty ? "dirty" : ""}" data-f="${esc(f)}" role="tab" tabindex="${f === S.file ? 0 : -1}" aria-selected="${f === S.file}" title="${dirty ? "Modifié — " : ""}${esc(f)} (clic milieu : fermer ; clic droit : menu)">
      <span class="ext ${extClass(f) ? "" : "t"}">${esc(ext.slice(0, 4))}</span>${esc(name)}${f === S.info?.main ? `<span class="mstar" title="Fichier principal">★</span>` : ""}${errs ? `<span class="errc" aria-label="${errs} erreur(s)">${errs}</span>` : ""}<span class="mod" role="img" aria-label="modifié"></span><span class="x" data-close="${esc(f)}" role="button" aria-label="Fermer ${esc(name)}" title="Fermer (Alt+W)">${icon("x")}</span></div>`;
  }).join("");
  $$("#tree .tn[data-f]").forEach(t => { t.classList.toggle("cur", t.dataset.f === S.file); t.classList.toggle("open", S.tabs.includes(t.dataset.f)); });
  if (S.project) { prefs.tabs = prefs.tabs || {}; prefs.tabs[S.project] = S.tabs.slice(0, 30); prefs.curFile = prefs.curFile || {}; prefs.curFile[S.project] = S.file; savePrefs(); }
}
$("#ftabs").addEventListener("click", e => {
  if (e.target.closest("#ftabAdd")) return fileNew();
  const x = e.target.closest("[data-close]"); if (x) { e.stopPropagation(); return closeTab(x.dataset.close); }
  const t = e.target.closest(".ftab"); if (t) openFile(t.dataset.f);
});
$("#ftabs").addEventListener("auxclick", e => { const t = e.target.closest(".ftab"); if (t && e.button === 1) { e.preventDefault(); closeTab(t.dataset.f); } });
$("#ftabs").addEventListener("contextmenu", e => { e.preventDefault(); const t = e.target.closest(".ftab"); fileMenu(t ? t.dataset.f : null, e.clientX, e.clientY, t); });
$("#ftabs").addEventListener("keydown", e => {
  const t = e.target.closest(".ftab"); if (!t) return;
  const f = t.dataset.f, tabs = $$(".ftab", $("#ftabs")), i = tabs.indexOf(t);
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openFile(f); }
  else if (e.key === "ArrowRight" || e.key === "ArrowLeft") { e.preventDefault(); const n = tabs[(i + (e.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length]; n.focus(); openFile(n.dataset.f).then(() => $(`.ftab[data-f="${CSS.escape(n.dataset.f)}"]`)?.focus()); }
  else if (e.key === "F2") { e.preventDefault(); fileRename(f); }
  else if (e.key === "Delete") { e.preventDefault(); fileDelete(f); }
  else if (e.key === "ContextMenu" || (e.shiftKey && e.key === "F10")) { e.preventDefault(); const r = t.getBoundingClientRect(); fileMenu(f, r.left, r.bottom, t); }
});
async function closeTab(f) {
  const d = S.docs[f];
  if (d && d.text !== d.saved) {
    const yes = await confirmModal("Fermer sans enregistrer ?", `<b>${esc(f)}</b> a des modifications. Elles seront enregistrées avant de fermer l'onglet.`, "Enregistrer et fermer");
    if (!yes) return;
    await api("/api/file", { project: S.project, file: f, content: d.text }); d.saved = d.text;
  }
  const i = S.tabs.indexOf(f); if (i < 0) return;
  S.tabs.splice(i, 1); delete S.docs[f];
  if (S.file === f) {
    const n = S.tabs[Math.min(i, S.tabs.length - 1)];
    S.file = null;
    if (n) await openFile(n); else { ED.set(""); renderTabs(); editorEmpty("Aucun fichier ouvert : choisissez-en un dans l'inspecteur (Fichiers)."); }
  } else renderTabs();
}
function cycleTab(d) { if (S.tabs.length < 2) return; const i = S.tabs.indexOf(S.file); openFile(S.tabs[(i + d + S.tabs.length) % S.tabs.length]); }
function fileMenu(f, x, y, back) {
  ctxMenu([
    { label: "Nouveau fichier…", icon: "filePlus", action: () => fileNew(f && f.includes("/") ? f.slice(0, f.lastIndexOf("/") + 1) : "") },
    ...(f ? ["-", { label: "Ouvrir", icon: "file", action: () => openFile(f) },
             { label: "Exécuter ce fichier", icon: "play", action: () => run("run", f) },
             { label: "Définir comme fichier principal", icon: "star", disabled: f === S.info?.main, action: () => setMain(f) },
             { label: "Renommer / déplacer…", icon: "edit", key: "F2", action: () => fileRename(f) },
             { label: "Supprimer…", icon: "trash", key: "Suppr", danger: true, action: () => fileDelete(f) }] : [])
  ], x, y, back);
}
async function setMain(f) {
  try { await api("/api/conf", { project: S.project, section: "main", data: f }); S.info.main = f; renderTree(); renderTabs(); toast(`« ${f} » est le fichier principal`, "ok", 1800); }
  catch (e) { toast(e.message, "error"); }
}

/* nouveau fichier, renommer, supprimer */
const validFileName = name => {
  if (!name) return "";
  if (name.split("/").length > 6) return "Trop de sous-dossiers";
  if (!name.split("/").every(p => /^[A-Za-z0-9_.@+-][A-Za-z0-9_.@+ -]{0,99}$/.test(p) && p !== "." && p !== "..")) return "Lettres, chiffres, _ . - (et / pour un sous-dossier)";
  return "";
};
function suggestExts() {
  const x = S.ext[S.info?.lang];
  const base = x && x.exts ? x.exts.slice(0, 3) : [".txt"];
  return [...new Set([...base, ".txt", ".md", ".json"])].slice(0, 5);
}
async function fileNew(prefix = "") {
  if (!S.project) return toast("Ouvrez d'abord un projet", "warn");
  const name = await nameModal({
    title: "Nouveau fichier", sub: "Nom du fichier, avec son extension. Utilisez « dossier/fichier » pour le ranger dans un sous-dossier.",
    value: prefix, placeholder: "module" + (suggestExts()[0] || ".txt"), types: suggestExts(), okLabel: "Créer",
    validate: n => validFileName(n) || (S.files.some(f => f.toLowerCase() === n.toLowerCase()) ? "Ce fichier existe déjà" : "")
  });
  if (!name) return;
  try {
    const r = await api("/api/file/new", { project: S.project, file: name });
    applyInfo(r); renderTree();
    await openFile(name);
    toast(`« ${name} » créé`, "ok");
  } catch (e) { toast(e.message, "error"); }
}
async function fileRename(f) {
  if (!S.project) return;
  const to = await nameModal({
    title: "Renommer le fichier", sub: `Nouveau nom (ou chemin) pour « ${f} ».`, value: f, okLabel: "Renommer",
    validate: n => n === f ? "" : validFileName(n) || (S.files.some(x => x.toLowerCase() === n.toLowerCase() && x.toLowerCase() !== f.toLowerCase()) ? "Ce fichier existe déjà" : "")
  });
  if (!to || to === f) return;
  try {
    await saveAll();
    const r = await api("/api/file/rename", { project: S.project, file: f, to });
    applyInfo(r);
    if (S.docs[f]) { S.docs[to] = S.docs[f]; delete S.docs[f]; }
    S.tabs = S.tabs.map(x => x === f ? to : x);
    S.diags.forEach(d => { if (d.file === f) d.file = to; });
    if (S.file === f) { S.file = to; $("#projFile").textContent = to; ED.lang = langOfFile(to); ED.lines = 0; ED.render(); }
    renderTabs(); renderTree(); toast(`« ${f} » renommé en « ${to} »`, "ok");
  } catch (e) { toast(e.message, "error"); }
}
async function fileDelete(f) {
  if (!S.project) return;
  const d = S.docs[f], dirty = d && d.text !== d.saved;
  const yes = await confirmModal("Supprimer ce fichier ?",
    `Le fichier <b>${esc(f)}</b> sera définitivement supprimé du disque${dirty ? ", avec ses modifications non enregistrées" : ""}.${f === S.info.main ? "<br><br>C'est le <b>fichier principal</b> du projet." : ""} Un instantané permet de revenir en arrière.`, "Supprimer", true);
  if (!yes) return;
  try {
    const r = await api("/api/file/delete", { project: S.project, file: f });
    applyInfo(r); delete S.docs[f];
    S.diags = S.diags.filter(x => x.file !== f);
    const i = S.tabs.indexOf(f);
    if (i >= 0) S.tabs.splice(i, 1);
    if (S.file === f) { S.file = null; const n = S.tabs[Math.max(0, i - 1)] || S.info.main; if (n && S.files.includes(n)) { if (!S.tabs.includes(n)) S.tabs.push(n); await openFile(n); } else { ED.set(""); renderTabs(); editorEmpty("Aucun fichier ouvert."); } }
    else renderTabs();
    renderTree(); updateConsoleBadge(); ED.paintDiags();
    toast(`« ${f} » supprimé`, "ok");
  } catch (e) { toast(e.message, "error"); }
}

function editorEmpty(msg) {
  const n = $("#noedit");
  if (!msg) { n.hidden = true; return; }
  n.hidden = false; n.innerHTML = `<div>${icon("file")}<br>${esc(msg)}</div>`;
  $("#projFile").textContent = "—";
}
async function openFile(f, line, col) {
  if (!f) return;
  if (S.file && S.docs[S.file]) Object.assign(S.docs[S.file], { sel: ED.ta.selectionStart, top: ED.ta.scrollTop });
  if (!S.docs[f]) {
    try {
      const r = await api("/api/file?" + qs({ project: S.project, file: f }));
      S.docs[f] = { text: r.content, saved: r.content, sel: 0, top: 0 };
    } catch (e) { toast(e.message, "warn"); return; }
  }
  if (!S.tabs.includes(f)) S.tabs.push(f);
  S.file = f;
  editorEmpty(null);
  const d = S.docs[f];
  ED.lang = langOfFile(f);
  ED.set(d.text);
  ED.lines = 0; ED.render();
  requestAnimationFrame(() => {
    if (line) ED.goto(line, col);
    else { ED.ta.setSelectionRange(d.sel, d.sel); ED.ta.scrollTop = d.top; ED.sync(); ED.caret(); }
  });
  $("#projFile").textContent = f;
  $("#stLang").textContent = langName(ED.lang) === ED.lang ? ({ css: "CSS", json: "JSON", markdown: "Markdown", plain: "Texte", web: "HTML" }[ED.lang] || ED.lang) : langName(ED.lang);
  renderTabs(); outlineRender(); liveSchedule(250);
}

function setDirty(f, dirty) {
  const t = $(`.ftab[data-f="${CSS.escape(f)}"]`);
  if (t) { t.classList.toggle("dirty", dirty); t.title = (dirty ? "Modifié — " : "") + f; }
  updateTitle();
}
function updateTitle() { document.title = `${anyDirty() ? "● " : ""}${S.project ? S.project + " · " : ""}Forge Code`; }
const anyDirty = () => Object.values(S.docs).some(d => d.text !== d.saved);

async function saveAll(quiet = true) {
  let n = 0;
  for (const [f, d] of Object.entries(S.docs)) {
    if (d.text === d.saved) continue;
    const text = d.text;
    await api("/api/file", { project: S.project, file: f, content: text });
    d.saved = text; n++;
    setDirty(f, d.text !== d.saved);
  }
  if (!quiet) toast(n ? `${n} fichier(s) enregistré(s)` : "Rien à enregistrer", n ? "ok" : "info", 1800);
  return n;
}

/* ------------------------------------------------------------------ langage du projet */
function renderLangSel() {
  const sel = $("#langSel"), cur = S.info ? S.info.lang : "";
  const langs = S.exts.filter(x => x.kind === "lang" && (x.enabled || x.id === cur));
  const inst = langs.filter(x => x.installed), miss = langs.filter(x => !x.installed);
  const opt = x => `<option value="${esc(x.id)}" ${x.id === cur ? "selected" : ""}>${esc(x.name)}${x.installed ? "" : " (à installer)"}</option>`;
  sel.innerHTML = (cur ? "" : `<option value="" selected>Langage ?</option>`) + (inst.length ? `<optgroup label="Installés">${inst.map(opt).join("")}</optgroup>` : "") +
    (miss.length ? `<optgroup label="Non installés">${miss.map(opt).join("")}</optgroup>` : "") + `<optgroup label="Plus"><option value="__ext">Gérer les extensions…</option></optgroup>`;
  sel.disabled = !S.project;
  const x = S.ext[cur];
  $("#langChip").textContent = x ? x.abbr : "?";
  $("#langChip").style.cssText = langStyle(x);
}
$("#langSel").addEventListener("change", async e => {
  const v = e.target.value;
  if (v === "__ext") { renderLangSel(); return showTab("exts"); }
  if (!S.project || !v) return;
  try {
    const p = await api("/api/project/lang", { project: S.project, lang: v });
    applyInfo(p); renderLang(); renderTree(); renderProjects();
    if (S.file) { ED.lang = langOfFile(S.file); ED.render(); }
    toast(`Langage du projet : ${langName(v)}`, "info", 1800);
  } catch (err) { toast(err.message, "error"); renderLangSel(); }
});
function renderLang() {
  renderLangSel();
  const x = S.info && S.ext[S.info.lang], big = $("#langBig");
  if (!S.project) { big.className = "chip off"; big.textContent = "?"; $("#langName").textContent = "—"; $("#langVer").textContent = "Ouvrez un projet"; $("#langActs").innerHTML = ""; return; }
  big.className = "chip" + (x && x.installed ? " on" : " off");
  big.textContent = x ? x.abbr : "?"; big.style.cssText = x && x.installed ? langStyle(x) : "";
  $("#langName").textContent = x ? x.name : "Langage inconnu";
  $("#langVer").textContent = x ? (x.installed ? `${x.version || "installé"}${x.path ? " · " + x.path : ""}` : (x.plan ? `à installer · ${x.plan}` : x.why)) : "Choisissez-le dans la barre d'outils";
  $("#langVer").title = $("#langVer").textContent;
  const pill = $("#langPill");
  pill.className = "pill" + (x && x.installed ? "" : " off");
  pill.innerHTML = x && x.installed ? `<span class="dot on"></span>Prêt` : `<span class="dot"></span>${x ? "Non installé" : "—"}`;
  const acts = [];
  if (x && !x.installed && x.plan) acts.push(`<button class="btn sm primary" data-la="install">${icon("download")}Installer ${esc(x.name)}</button>`);
  if (x && x.installed && x.repl) acts.push(`<button class="btn sm" data-la="repl">${icon("chat")}Console</button>`);
  if (x && x.installed) acts.push(`<button class="btn sm" data-la="format" title="Formater le fichier ouvert (⇧ Alt F)">${icon("sparkle")}Formater</button>`, `<button class="btn sm" data-la="lint" title="Analyser le fichier ouvert (⇧ Alt L)">${icon("lint")}Analyser</button>`);
  $("#langActs").innerHTML = acts.join("");
  $("#replLbl").textContent = x && x.repl ? `Console ${x.name.split(" ")[0]}` : "Console";
  $("#btnRepl").disabled = !(x && x.installed && x.repl);
  $("#btnRepl").title = x && x.repl ? `Console interactive ${x.name} dans le dossier du projet` : "Pas de console interactive pour ce langage";
  updateButtons();
}
$("#langActs").addEventListener("click", e => {
  const b = e.target.closest("[data-la]"); if (!b) return;
  ({ install: () => extInstall(S.info.lang), repl: () => interactive("repl"), format: formatFile, lint: lintFile })[b.dataset.la]();
});
$("#btnExtGo").addEventListener("click", () => showTab("exts"));

/* ------------------------------------------------------------------ exécution */
function updateButtons() {
  const running = !!S.run, can = !!S.project && !!(S.info && S.info.lang);
  const busy = running || (S.session.running && S.session.kind === "run");
  $("#btnVerify").disabled = !can || running;
  const x = S.info && S.ext[S.info.lang];
  $("#btnVerify").hidden = !!(x && !x.check);
  $("#btnRun").disabled = !can;
  $("#btnRun").classList.toggle("again", busy);
  $("#btnRun").innerHTML = busy ? `${icon("refresh")}<span class="lbl">Relancer</span>` : `${icon("play")}Exécuter <span class="kbd hide-sm">Ctrl ⏎</span>`;
  $("#btnStop").style.display = busy ? "" : "none";
  $("#btnRun").title = x && !x.installed ? `${x.name} n'est pas installé : cliquez pour l'installer` : "Enregistrer, compiler si besoin et exécuter (Ctrl+Entrée ou F5)";
  const on = S.session.running;
  $("#btnSigInt").disabled = !on; $("#btnEof").disabled = !on; $("#tInput").disabled = !on;
  $("#tInput").placeholder = on ? (S.session.kind === "run" ? "Écrire au programme… (Entrée pour envoyer, ↑ historique)" : "Commande… (Entrée pour envoyer, ↑ historique)") : "Lancez un programme pour lui écrire ici…";
}
function termSize() {
  const el = $("#term"), cw = ED.charW * (12.8 / (prefs.fs || 13.5)) || 7.7;
  return { cols: Math.max(40, Math.floor((el.clientWidth - 28) / cw)) || 120, rows: Math.max(10, Math.floor(el.clientHeight / 19)) || 30 };
}
async function run(mode = "run", target) {
  if (!S.project) return toast("Ouvrez d'abord un projet", "warn");
  const x = S.ext[S.info.lang];
  if (x && !x.installed) {
    const yes = await confirmModal(`${x.name} n'est pas installé`, `Pour exécuter ce projet, il faut installer l'extension <b>${esc(x.name)}</b>${x.plan ? ` (${esc(x.plan)})` : ""}.${x.root ? "<br><br>Votre mot de passe administrateur peut être demandé." : ""}`, "Installer");
    if (yes) extInstall(x.id);
    return;
  }
  if (S.run && S.run.building) return toast("Compilation en cours…", "info", 1500);
  try {
    await saveAll();
    if (mode === "run" && (S.conf.run || {}).clear) termClear();
    const tgt = target || ($("#targetSel").value === "current" ? S.file : "");
    S.run = { mode, t0: Date.now() };
    updateButtons();
    showTab("terminal", false, true);
    await api("/api/run", { project: S.project, target: tgt || "", mode, args: (S.conf.run || {}).args || "", stdin: mode === "run" ? ((S.conf.run || {}).stdin || "") : "", ...termSize() });
  } catch (e) { S.run = null; setSteps(null); updateButtons(); toast(e.message, "error", 6000); }
}
async function stopRun() { try { await api("/api/stop", {}); } catch (e) { toast(e.message, "error"); } }
$("#btnVerify").addEventListener("click", () => run("check"));
$("#btnRun").addEventListener("click", () => run("run"));
$("#btnStop").addEventListener("click", stopRun);
$("#targetSel").value = prefs.target === "current" ? "current" : "main";
$("#targetSel").addEventListener("change", e => { prefs.target = e.target.value; savePrefs(); });

/* étapes dans la barre d'outils */
let stepsTimer = 0, jobT0 = 0;
function setSteps(steps, active, failed) {
  clearTimeout(stepsTimer);
  const el = $("#jobbar"), tb = $(".toolbar");
  if (!steps) { el.classList.remove("show"); tb.removeAttribute("aria-busy"); return; }
  const done = active === "done", ai = done ? steps.length : Math.max(0, steps.findIndex(s => s[0] === active));
  el.classList.toggle("single", steps.length === 1);
  el.innerHTML = steps.map(([k, label, long], i) => {
    const c = done || i < ai ? "done" : i === ai ? (failed ? "fail" : "active") : "";
    return `<div class="jc ${c}" title="${esc(long)}"><i class="js"></i><span>${esc(label)}${c === "done" ? " ✓" : c === "fail" ? " ✕" : ""}</span></div>`;
  }).join("");
  el.classList.add("show");
  tb.setAttribute("aria-busy", !done && !failed);
  $("#jobSr").textContent = done ? "Terminé" : failed ? `Échec : ${steps[ai] ? steps[ai][2] : ""}` : `${steps[ai] ? steps[ai][2] : ""}`;
  if (done || failed) stepsTimer = setTimeout(() => el.classList.remove("show"), 3500);
}
function tickJob() {
  const t0 = S.run ? S.run.t0 : S.job ? jobT0 : 0, t = t0 ? Math.round((Date.now() - t0) / 1000) : 0;
  $("#stJob").textContent = S.stepText ? `${S.stepText}${t ? ` · ${t} s` : ""}` : "";
}
setInterval(tickJob, 1000);

function addHistory(ok, label, secs) {
  S.history.unshift({ ok, label, secs, t: new Date() });
  S.history = S.history.slice(0, 8);
  $("#hist").innerHTML = S.history.map(h => `<div><span class="${h.ok ? "ok" : "ko"}">${icon(h.ok ? "check" : "x")}</span><span>${esc(h.label)}${h.secs != null ? ` · ${h.secs}s` : ""}</span><time>${h.t.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}</time></div>`).join("");
}

/* ------------------------------------------------------------------ terminal (émulation ANSI légère) */
const TERM = $("#term");
const ANSI16 = ["var(--dim)", "var(--err)", "var(--ok)", "var(--warn)", "var(--accent3)", "var(--tk-p)", "var(--accent)", "var(--text)"];
const T = { cur: null, col: 0, st: { fg: null, bg: null, b: 0, i: 0, u: 0, d: 0, inv: 0 }, pend: "", raf: 0, lines: [], plain: [] };
function xterm256(n) {
  if (n < 8) return ANSI16[n];
  if (n < 16) return ANSI16[n - 8];
  if (n >= 232) { const g = 8 + (n - 232) * 10; return `rgb(${g},${g},${g})`; }
  n -= 16; const c = v => v ? 55 + v * 40 : 0;
  return `rgb(${c(Math.floor(n / 36))},${c(Math.floor(n / 6) % 6)},${c(n % 6)})`;
}
function sgr(params) {
  const p = params.length ? params.split(";").map(x => +x || 0) : [0], s = T.st;
  for (let i = 0; i < p.length; i++) {
    const v = p[i];
    if (v === 0) Object.assign(s, { fg: null, bg: null, b: 0, i: 0, u: 0, d: 0, inv: 0 });
    else if (v === 1) s.b = 1; else if (v === 2) s.d = 1; else if (v === 3) s.i = 1; else if (v === 4) s.u = 1; else if (v === 7) s.inv = 1;
    else if (v === 22) { s.b = 0; s.d = 0; } else if (v === 23) s.i = 0; else if (v === 24) s.u = 0; else if (v === 27) s.inv = 0;
    else if (v >= 30 && v <= 37) s.fg = ANSI16[v - 30]; else if (v >= 90 && v <= 97) s.fg = ANSI16[v - 90];
    else if (v === 39) s.fg = null; else if (v === 49) s.bg = null;
    else if (v >= 40 && v <= 47) s.bg = ANSI16[v - 40]; else if (v >= 100 && v <= 107) s.bg = ANSI16[v - 100];
    else if (v === 38 || v === 48) {
      let col = null;
      if (p[i + 1] === 5) { col = xterm256(p[i + 2] || 0); i += 2; }
      else if (p[i + 1] === 2) { col = `rgb(${p[i + 2] || 0},${p[i + 3] || 0},${p[i + 4] || 0})`; i += 4; }
      if (v === 38) s.fg = col; else s.bg = col;
    }
  }
}
const stKey = s => `${s.fg || ""}|${s.bg || ""}|${s.b}${s.i}${s.u}${s.d}${s.inv}`;
const stCss = {};
function stAttr(k) {
  if (k in stCss) return stCss[k];
  const [fg, bg, f] = k.split("|"), cls = [], css = [];
  let F = fg, B = bg;
  if (f[4] === "1") { F = bg || "var(--panel-solid)"; B = fg || "var(--text)"; }
  if (F) css.push(`color:${F}`);
  if (B) css.push(`background:color-mix(in srgb,${B} ${f[4] === "1" ? 85 : 28}%,transparent)`);
  if (f[0] === "1") cls.push("a-b"); if (f[1] === "1") cls.push("a-i"); if (f[2] === "1") cls.push("a-u"); if (f[3] === "1") cls.push("a-d");
  return (stCss[k] = (cls.length ? ` class="${cls.join(" ")}"` : "") + (css.length ? ` style="${css.join(";")}"` : ""));
}
function cellsHtml(cells) {
  let h = "", i = 0;
  while (i < cells.length) {
    const k = cells[i] ? cells[i][1] : "", a = stAttr(k); let j = i, txt = "";
    while (j < cells.length && (cells[j] ? cells[j][1] : "") === k) { txt += cells[j] ? cells[j][0] : " "; j++; }
    h += a ? `<span${a}>${esc(txt)}</span>` : esc(txt);
    i = j;
  }
  return h;
}
const RX_LOCJS = /((?:[A-Za-z]:)?[\w./\\@+-]*[\w@+-]\.[A-Za-z0-9]{1,6})(?::(\d+)(?::(\d+))?|", line (\d+)|\((\d+),(\d+)\)| line (\d+))/g;
function locate(text) {                        // premier emplacement « fichier:ligne » d'un fichier du projet
  if (!S.info) return null;
  const root = S.info.path.replace(/\\/g, "/") + "/";
  for (const m of text.matchAll(RX_LOCJS)) {
    let f = m[1].replace(/\\/g, "/").replace(/^file:\/\//, "");
    if (f.startsWith(root)) f = f.slice(root.length);
    if (f.startsWith("./")) f = f.slice(2);
    if (!S.files.includes(f)) { const g = S.files.find(x => x.endsWith("/" + f)); if (!g) continue; f = g; }
    return { file: f, line: +(m[2] || m[4] || m[5] || m[7]), col: +(m[3] || m[6] || 1) };
  }
  return null;
}
function termAtBottom() { return TERM.scrollHeight - TERM.scrollTop - TERM.clientHeight < 40; }
function termScroll(force) { if (force || $("#tScroll").checked) TERM.scrollTop = TERM.scrollHeight; }
function termTrim() { while (TERM.childElementCount > 5000) { TERM.firstChild.remove(); T.plain.shift(); } }
function termNewLine() {
  const d = document.createElement("div"); d.className = "l cur"; TERM.appendChild(d);
  T.cur = { cells: [], el: d }; T.col = 0; termTrim();
  return T.cur;
}
function termFinish() {                         // la ligne en cours est terminée : rendu définitif, liens, traceur
  const c = T.cur; if (!c) return;
  cancelAnimationFrame(T.raf); T.raf = 0;
  c.el.classList.remove("cur");
  c.el.innerHTML = cellsHtml(c.cells);
  const plain = c.cells.map(x => x ? x[0] : " ").join("");
  T.plain.push(plain);
  const loc = locate(plain);
  if (loc) { c.el.classList.add("jump"); c.el.tabIndex = 0; c.el.setAttribute("role", "button"); c.el.title = "Ouvrir à cet endroit"; Object.assign(c.el.dataset, { file: loc.file, line: loc.line, col: loc.col }); }
  plotLine(plain);
  T.cur = null;
}
function termPaintSoon() {
  if (T.raf) return;
  T.raf = requestAnimationFrame(() => { T.raf = 0; if (T.cur) T.cur.el.innerHTML = cellsHtml(T.cur.cells); termScroll(); });
}
function termPty(text) {
  let s = T.pend + text; T.pend = "";
  if (!T.cur) termNewLine();
  const key = () => stKey(T.st);
  let k = key();
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (ch === "\x1b") {
      const rest = s.slice(i);
      let m = /^\x1b\[([0-9;?<>=]*)([ -\/]*)([@-~])/.exec(rest);
      if (m) {
        const [all, par, , fin] = m;
        if (fin === "m") { sgr(par.replace(/[?<>=]/g, "")); k = key(); }
        else if (fin === "K") { const n = +par || 0; if (n === 0) T.cur.cells.length = Math.min(T.cur.cells.length, T.col); else if (n === 2) { T.cur.cells = []; } }
        else if (fin === "G") T.col = Math.max(0, (+par || 1) - 1);
        else if (fin === "C") T.col += +par || 1;
        else if (fin === "D") T.col = Math.max(0, T.col - (+par || 1));
        else if (fin === "J" && (par === "2" || par === "3")) { TERM.innerHTML = ""; T.plain = []; termNewLine(); }
        i += all.length - 1; continue;
      }
      m = /^\x1b\][^\x07\x1b]*(\x07|\x1b\\)/.exec(rest);
      if (m) { i += m[0].length - 1; continue; }
      if (/^\x1b(\[[0-9;?<>=]*[ -\/]*|\][^\x07\x1b]*|\x1b?)$/.test(rest) && rest.length < 64) { T.pend = rest; break; }   // séquence coupée : suite au prochain paquet
      i += 1; continue;
    }
    if (ch === "\n") { termFinish(); termNewLine(); continue; }
    if (ch === "\r") { if (s[i + 1] !== "\n") T.col = 0; continue; }
    if (ch === "\b") { T.col = Math.max(0, T.col - 1); continue; }
    if (ch === "\t") { const n = 8 - (T.col % 8); for (let j = 0; j < n; j++) T.cur.cells[T.col++] = [" ", k]; continue; }
    if (ch < " " || ch === "\x7f") continue;
    T.cur.cells[T.col++] = [ch, k];
    if (T.col > 4000) { termFinish(); termNewLine(); }
  }
  termPaintSoon();
}
function termLine(text, kind = "sys") {          // lignes de Forge Code (compilation, messages), pas du programme
  const atBottom = termAtBottom();
  if (T.cur && T.cur.cells.length) { termFinish(); } else if (T.cur) { T.cur.el.remove(); T.cur = null; }
  for (const line of text.replace(/\n$/, "").split("\n")) {
    const d = document.createElement("div");
    d.className = "l " + (kind === "out" ? "" : kind);
    d.textContent = line;
    const loc = locate(line);
    if (loc) { d.classList.add("jump"); d.tabIndex = 0; d.setAttribute("role", "button"); d.title = "Ouvrir à cet endroit"; Object.assign(d.dataset, { file: loc.file, line: loc.line, col: loc.col }); }
    TERM.appendChild(d); T.plain.push(line);
  }
  termTrim();
  if (atBottom || kind === "error") termScroll();
  if (kind === "error" && activeTab !== "terminal") { termErrs++; termUnread = 1; const b = $("#bTerm"); b.classList.remove("info", "dotb"); badge("bTerm", termErrs); }
  autoOpenPanel();
}
let termUnread = 0, termErrs = 0;
function termWrite(text, kind) {
  autoOpenPanel();
  if (kind === "pty") { termPty(text); if (activeTab !== "terminal" && !termUnread) { termUnread = 1; const b = $("#bTerm"); b.classList.add("show", "info", "dotb"); b.title = "Nouvelle sortie"; } }
  else termLine(text, kind);
}
function termClear() { TERM.innerHTML = ""; T.cur = null; T.plain = []; T.pend = ""; sgr("0"); }
function jumpFromTerm(d) { openFile(d.dataset.file, +d.dataset.line, +d.dataset.col); }
TERM.addEventListener("click", e => { const d = e.target.closest(".jump"); if (d && !getSelection().toString()) jumpFromTerm(d); });
TERM.addEventListener("keydown", e => { const d = e.target.closest && e.target.closest(".jump"); if (d && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); jumpFromTerm(d); } });

/* saisie envoyée au programme (le terminal renvoie l'écho) */
let tHist = [], tHistI = -1;
async function termSend(eof) {
  const inp = $("#tInput");
  if (!S.session.running) return toast("Aucun programme en cours : lancez-le d'abord (Ctrl+Entrée)", "warn");
  try {
    if (eof) { await api("/api/signal", { sig: "eof" }); return; }
    const t = inp.value;
    await api("/api/stdin", { text: t + "\n" });
    if (t && tHist[0] !== t) { tHist.unshift(t); tHist = tHist.slice(0, 100); }
    tHistI = -1; inp.value = "";
    termScroll(true);
  } catch (e) { toast(e.message, "error"); }
}
$("#btnSend").addEventListener("click", () => termSend());
$("#btnEof").addEventListener("click", () => termSend(true));
$("#tInput").addEventListener("keydown", e => {
  if (e.key === "Enter") { e.preventDefault(); termSend(); }
  else if (e.key === "ArrowUp" && tHist.length) { tHistI = Math.min(tHist.length - 1, tHistI + 1); e.target.value = tHist[tHistI]; e.preventDefault(); }
  else if (e.key === "ArrowDown") { tHistI = Math.max(-1, tHistI - 1); e.target.value = tHistI < 0 ? "" : tHist[tHistI]; e.preventDefault(); }
  else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "d") { e.preventDefault(); termSend(true); }
  else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "c" && !e.target.value.slice(e.target.selectionStart, e.target.selectionEnd)) { e.preventDefault(); api("/api/signal", { sig: "int" }).catch(() => {}); }
  else if (e.key === "Tab" && S.session.running && S.session.kind !== "run") { e.preventDefault(); }
});
$("#btnSigInt").addEventListener("click", () => api("/api/signal", { sig: "int" }).catch(e => toast(e.message, "error")));
async function interactive(what) {
  if (!S.project) return toast("Ouvrez d'abord un projet", "warn");
  if (S.session.running && S.session.kind === "run") {
    const yes = await confirmModal("Arrêter le programme en cours ?", "Le terminal est occupé par votre programme. Il sera arrêté pour ouvrir la console.", "Arrêter et ouvrir");
    if (!yes) return;
  }
  try {
    showTab("terminal", false, true);
    await api("/api/interactive", { project: S.project, what, ...termSize() });
    setTimeout(() => $("#tInput").focus(), 150);
  } catch (e) { toast(e.message, "error", 5000); }
}
$("#btnRepl").addEventListener("click", () => interactive("repl"));
$("#btnShell").addEventListener("click", () => interactive("shell"));
$("#btnTermSave").addEventListener("click", () => {
  const body = T.plain.concat(T.cur ? [T.cur.cells.map(x => x ? x[0] : " ").join("")] : []).join("\n");
  downloadBlob(new Blob([body + "\n"], { type: "text/plain" }), `${S.project || "terminal"}-${stamp()}.txt`);
});
function termState() {
  const s = S.session, dot = $("#tDot"), lbl = $("#tLbl");
  dot.className = "dot" + (s.running ? " run" : S.lastExit && S.lastExit.code ? " ko" : "");
  const kind = { run: "Programme", repl: "Console interactive", shell: "Shell" }[s.kind] || "Programme";
  lbl.textContent = s.running ? `${kind} en cours${s.cmd ? " · " + s.cmd : ""}` : S.lastExit ? `${kind} terminé · code ${S.lastExit.code} · ${S.lastExit.seconds} s` : "Terminal libre";
  lbl.title = lbl.textContent;
  $("#stTerm").textContent = s.running ? `${kind} en cours` : "Terminal libre";
  updateButtons();
}

/* compteur d'erreurs (onglet Terminal + barre d'état) et navigation F8 */
const diagCounts = () => { const e = S.diags.filter(d => d.severity === "error").length; return [e, S.diags.length - e]; };
const plural = (n, un, plu) => `${n} ${n > 1 ? plu : un}`;
function updateConsoleBadge() {
  const [e, w] = diagCounts(), st = $("#stDiag");
  st.hidden = !(e || w);
  if (e || w) {
    const t = `${plural(e, "erreur", "erreurs")}, ${plural(w, "avertissement", "avertissements")}`;
    st.innerHTML = `<span style="color:var(--err)">✕ ${e}</span> <span style="color:var(--warn)">⚠ ${w}</span>`;
    st.setAttribute("aria-label", `${t} — aller au suivant (F8)`); st.title = "Aller au problème suivant (F8)";
  } else $("#stDiagMsg").textContent = "";
}
let diagMsgTimer = 0;
async function jumpDiag(dir) {
  const order = f => { const i = S.tabs.indexOf(f); return i >= 0 ? i : 100 + S.files.indexOf(f); };
  const list = S.diags.filter(d => S.files.includes(d.file)).sort((a, b) => order(a.file) - order(b.file) || a.line - b.line || a.col - b.col);
  if (!list.length) return toast("Aucune erreur ni avertissement", "info", 1500);
  const cf = order(S.file), p = ED.ta.selectionStart, l = ED.lineOf(p), col = p - ED.starts()[l] + 1;
  const cmp = d => (order(d.file) - cf) || (d.line - (l + 1)) || (d.col - col);
  let i;
  if (dir > 0) { i = list.findIndex(d => cmp(d) > 0); if (i < 0) i = 0; }
  else { i = -1; list.forEach((d, k) => { if (cmp(d) < 0) i = k; }); if (i < 0) i = list.length - 1; }
  const d = list[i];
  if (d.file !== S.file) await openFile(d.file);
  ED.goto(d.line, d.col);
  const m = $("#stDiagMsg");
  m.textContent = `${i + 1}/${list.length} · ${d.message}`; m.title = d.message; m.style.color = d.severity === "error" ? "var(--err)" : "var(--warn)";
  clearTimeout(diagMsgTimer); diagMsgTimer = setTimeout(() => { m.textContent = ""; }, 6000);
}
$("#stDiag").addEventListener("click", () => jumpDiag(1));
function badge(id, n) { const b = $("#" + id); b.textContent = n > 99 ? "99+" : n; b.classList.toggle("show", n > 0); }
function setDiags(items) {
  S.diags = items || [];
  ED.paintDiags(); renderTabs(); renderTree(); updateConsoleBadge();
}
/* pendant la frappe : les erreurs sous les lignes modifiées suivent le texte, celles des lignes touchées
   disparaissent tout de suite (la vérification en direct les remet si elles sont toujours là) */
function diagsFollowEdit(old, now) {
  if (old === now || !S.diags.some(d => d.file === S.file)) return;
  let p = 0; const n = Math.min(old.length, now.length);
  while (p < n && old.charCodeAt(p) === now.charCodeAt(p)) p++;
  let a = old.length, b = now.length;
  while (a > p && b > p && old.charCodeAt(a - 1) === now.charCodeAt(b - 1)) { a--; b--; }
  const nl = (t, i, j) => { let c = 0; for (let k = i; k < j; k++) if (t.charCodeAt(k) === 10) c++; return c; };
  const first = nl(old, 0, p), removed = nl(old, p, a), delta = nl(now, p, b) - removed;
  let gone = false;
  S.diags = S.diags.filter(d => {
    if (d.file !== S.file || d.line - 1 < first) return true;
    if (d.line - 1 > first + removed) { d.line += delta; return true; }
    gone = true; return false;
  });
  if (gone) setDiags(S.diags);
}
/* vérification en direct : compile / contrôle la syntaxe du texte non enregistré, une demi-seconde après la dernière frappe */
const LIVE = { timer: 0, busy: false, again: false };
function liveSchedule(delay = 650) {
  if (!S.project || !S.file || prefs.live === false) return;
  clearTimeout(LIVE.timer); LIVE.timer = setTimeout(liveRun, delay);
}
async function liveRun() {
  if (!S.project || !S.file || prefs.live === false) return;
  if (LIVE.busy) { LIVE.again = true; return; }
  LIVE.busy = true;
  const proj = S.project, file = S.file, docs = {}, sent = {};
  for (const [f, d] of Object.entries(S.docs)) { sent[f] = d.text; if (d.text !== d.saved) docs[f] = d.text; }
  try {
    const r = await api("/api/live", { project: proj, file, docs });
    const same = proj === S.project && Object.entries(sent).every(([f, t]) => !S.docs[f] || S.docs[f].text === t);
    if (r.supported && same) {                     // texte modifié pendant la vérification : on attend la suivante
      const seen = new Set(r.items.map(d => d.file)), key = d => `${d.file}:${d.line}:${d.message}`, have = new Set(r.items.map(key));
      const keep = S.diags.filter(d => !d.live && (d.runtime ? !have.has(key(d)) : d.file !== file && !seen.has(d.file)));
      setDiags([...keep, ...r.items.map(d => ({ ...d, live: true }))]);
    }
  } catch { /* vérification en direct : silencieuse */ }
  finally {
    LIVE.busy = false;
    if (LIVE.again) { LIVE.again = false; liveSchedule(150); }
  }
}

/* ------------------------------------------------------------------ panneau à onglets */
let activeTab = "terminal";
function showTab(v, keepClosed, noFocus) {
  if (!keepClosed && !panelOpen()) setPanel(true, false);
  activeTab = v; prefs.tab = v; savePrefs();
  $$(".ptab").forEach(t => { const on = t.dataset.v === v; t.classList.toggle("active", on); t.setAttribute("aria-selected", on); t.tabIndex = on ? 0 : -1; });
  $$(".pview").forEach(p => p.classList.toggle("active", p.dataset.v === v));
  if (v === "terminal") { termUnread = termErrs = 0; badge("bTerm", 0); $("#bTerm").classList.remove("info", "dotb"); termScroll(true); }
  if (v === "plotter") PL.dirty = true;
  if (v === "pkgs") pkgsLoad();
  if (v === "exts") extRender();
  if (v === "examples") exRender();
  if (v === "doctor" && !docLoaded) runDoctor();
}
$$(".ptab").forEach(t => { const v = t.dataset.v; t.id = "pt-" + v; t.setAttribute("role", "tab"); t.setAttribute("aria-controls", "pv-" + v); });
$$(".pview").forEach(p => { const v = p.dataset.v; p.id = "pv-" + v; p.setAttribute("role", "tabpanel"); p.setAttribute("aria-labelledby", "pt-" + v); });
$("#ptabs").addEventListener("click", e => { const t = e.target.closest(".ptab"); if (t) showTab(t.dataset.v); });
$(".ptablist").addEventListener("keydown", e => {
  const l = $$(".ptab"), i = l.indexOf(document.activeElement);
  if (i < 0 || !["ArrowRight", "ArrowLeft", "Home", "End"].includes(e.key)) return;
  e.preventDefault();
  const n = e.key === "Home" ? l[0] : e.key === "End" ? l[l.length - 1] : l[(i + (e.key === "ArrowRight" ? 1 : -1) + l.length) % l.length];
  showTab(n.dataset.v); n.focus();
});
$("#btnClearPanel").addEventListener("click", () => {
  if (activeTab === "terminal") termClear();
  if (activeTab === "plotter") plotClear();
});
$("#btnBig").addEventListener("click", e => {
  const on = !MAIN.classList.contains("big");
  MAIN.classList.toggle("big", on); e.currentTarget.setAttribute("aria-pressed", on); if (on && !panelOpen()) setPanel(true, true); PL.dirty = true;
});

/* redimensionnement et repli du panneau du bas */
const MAIN = $(".main");
const panelOpen = () => !MAIN.classList.contains("collapsed");
function setPanel(open, user) {
  MAIN.classList.toggle("collapsed", !open);
  $("#btnPanel").setAttribute("aria-expanded", open);
  if (user) { prefs.panelOpen = open; savePrefs(); }
  PL.dirty = true;
}
/* tant que l'utilisateur n'a pas choisi, le panneau reste replié s'il est vide et s'ouvre au premier contenu */
function autoOpenPanel() { if (prefs.panelOpen === undefined && !panelOpen()) setPanel(true, false); }
$("#btnPanel").addEventListener("click", () => setPanel(!panelOpen(), true));
(() => {
  const root = document.documentElement, rz = $("#resizer");
  const set = h => { h = Math.max(120, Math.min(window.innerHeight * .72, h)); root.style.setProperty("--panel-h", h + "px"); prefs.panelH = h; };
  const cur = () => parseFloat(getComputedStyle(root).getPropertyValue("--panel-h")) || 340;
  if (prefs.panelH) set(prefs.panelH);
  rz.addEventListener("pointerdown", e => {
    e.preventDefault(); rz.setPointerCapture(e.pointerId); rz.focus();
    const y0 = e.clientY, wasOpen = panelOpen(), h0 = wasOpen ? cur() : 44;
    let moved = false;
    const mv = ev => {
      if (!moved && Math.abs(ev.clientY - y0) < 4) return;
      moved = true;
      if (!panelOpen()) setPanel(true, true);
      set(h0 - (ev.clientY - y0)); PL.dirty = true;
    };
    const up = () => {
      rz.removeEventListener("pointermove", mv); rz.removeEventListener("pointerup", up); rz.removeEventListener("pointercancel", up);
      if (moved) savePrefs(); else setPanel(!wasOpen, true);
    };
    rz.addEventListener("pointermove", mv); rz.addEventListener("pointerup", up); rz.addEventListener("pointercancel", up);
  });
  rz.addEventListener("keydown", e => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setPanel(!panelOpen(), true); }
    else if (e.key === "ArrowUp" || e.key === "ArrowDown") {
      e.preventDefault();
      if (!panelOpen()) setPanel(true, true);
      set(cur() + (e.key === "ArrowUp" ? 24 : -24)); savePrefs(); PL.dirty = true;
    }
  });
})();

/* ------------------------------------------------------------------ colonnes repliables et tiroirs */
const mqSide = matchMedia("(max-width:900px)"), mqInsp = matchMedia("(max-width:1180px)");
const APP = $(".app"), CONTENT = $(".content"), SIDE = $(".sidebar"), INSP = $(".inspector");
function syncPanes() {
  $("#btnSide").setAttribute("aria-pressed", mqSide.matches ? SIDE.classList.contains("drawer") : !APP.classList.contains("nosb"));
  $("#btnInsp").setAttribute("aria-pressed", mqInsp.matches ? INSP.classList.contains("drawer") : !CONTENT.classList.contains("noinsp"));
  document.body.classList.toggle("drawer-open", SIDE.classList.contains("drawer") || INSP.classList.contains("drawer"));
}
function closeDrawers() { SIDE.classList.remove("drawer"); INSP.classList.remove("drawer"); syncPanes(); }
function toggleSide() {
  if (mqSide.matches) { const o = !SIDE.classList.contains("drawer"); closeDrawers(); SIDE.classList.toggle("drawer", o); }
  else { APP.classList.toggle("nosb"); prefs.sideOpen = !APP.classList.contains("nosb"); savePrefs(); }
  syncPanes();
}
function toggleInspector() {
  if (mqInsp.matches) { const o = !INSP.classList.contains("drawer"); closeDrawers(); INSP.classList.toggle("drawer", o); }
  else { CONTENT.classList.toggle("noinsp"); prefs.inspOpen = !CONTENT.classList.contains("noinsp"); savePrefs(); }
  syncPanes();
}
$("#btnSide").addEventListener("click", toggleSide);
$("#btnInsp").addEventListener("click", toggleInspector);
$("#scrim").addEventListener("click", closeDrawers);
[mqSide, mqInsp].forEach(q => q.addEventListener("change", closeDrawers));
addEventListener("keydown", e => { if (e.key === "Escape" && document.body.classList.contains("drawer-open") && !$(".overlay")) closeDrawers(); });
$("#projList").addEventListener("click", () => { if (mqSide.matches) closeDrawers(); });
if (prefs.sideOpen === false) APP.classList.add("nosb");
if (prefs.inspOpen === false) CONTENT.classList.add("noinsp");
syncPanes();

/* ------------------------------------------------------------------ traceur (lignes « nom:valeur » écrites par le programme) */
const PAL_N = 10;
const PL = {
  series: new Map(), n: 0, win: 500, presetWin: 500, paused: false, dirty: true, tmap: new Map(), t0: 0,
  view: { live: true, x0: 0, x1: 0, yAuto: true, y0: 0, y1: 1 }, hover: null, drag: null, geo: null
};
$("#plotWin").value = "500";
const hashName = s => { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; };
/* couleur stable par nom : indice mémorisé, tiré d'un hachage du nom, jamais en double parmi les courbes affichées */
function colorIndex(name) {
  const map = prefs.plotColors || (prefs.plotColors = {});
  const used = new Set([...PL.series.values()].map(s => s.ci));
  let i = map[name];
  if (i !== undefined && !used.has(i)) return i;
  const persist = i === undefined;
  i = hashName(name) % PAL_N;
  for (let k = 0; k < PAL_N && used.has(i); k++) i = (i + 1) % PAL_N;
  if (persist) { map[name] = i; savePrefs(); }
  return i;
}
/* « nom:valeur,nom2:valeur2 » → [[nom, valeur], …] ; null si la ligne n'est pas une mesure */
function parseMeasures(line) {
  const t = line.trim().replace(/\s*[:=]\s*/g, ":");
  if (!t) return null;
  const toks = t.split(/[\s,;\t]+/).filter(Boolean);
  const vals = [];
  for (const tok of toks) {
    let m = /^([A-Za-z_][\w.\-°%]*):(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)$/.exec(tok);
    if (m) { vals.push([m[1], +m[2]]); continue; }
    if (/^-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?$/.test(tok)) vals.push(["valeur " + (vals.length + 1), +tok]);
    else return null;
  }
  return vals.length ? vals : null;
}
function plotLine(line) {
  const vals = parseMeasures(line);
  if (!vals) return;
  if (PL.paused) return;
  PL.n++;
  const now = Date.now();
  if (!PL.t0) PL.t0 = now;
  PL.tmap.set(PL.n, now); PL.tmap.delete(PL.n - 6000);
  let added = false;
  for (const [k, v] of vals) {
    let s = PL.series.get(k);
    if (!s) { s = { name: k, ci: colorIndex(k), data: [], on: true, last: v, vmin: v, vmax: v }; PL.series.set(k, s); added = true; }
    s.data.push([PL.n, v]);
    if (s.data.length > 6000) s.data.splice(0, s.data.length - 6000);
    s.last = v;
  }
  if (added) renderLegend();
  autoOpenPanel();
  PL.dirty = true;
}
function plotClear() {
  PL.series.clear(); PL.n = 0; PL.tmap.clear(); PL.t0 = 0; PL.hover = null;
  PL.view = { live: true, x0: 0, x1: 0, yAuto: true, y0: 0, y1: 1 }; PL.win = PL.presetWin; syncWinSelect();
  renderLegend(); PL.dirty = true;
}
function renderLegend() {
  const lg = $("#legend");
  if (!PL.series.size) { lg.innerHTML = `<span class="dim" style="font:500 12px var(--sans)">Faites écrire des mesures à votre programme, par exemple <b>temp:23.5,hum:40</b> (une ligne par instant).</span>`; return; }
  lg.innerHTML = [...PL.series.values()].map(s => `<button class="lg${s.on ? "" : " off"}" data-k="${esc(s.name)}" aria-pressed="${s.on}" title="Afficher / masquer la courbe « ${esc(s.name)} »"><i style="background:var(--p${s.ci})"></i><span class="ln">${esc(s.name)}</span><b class="lv"></b><small class="lm"></small></button>`).join("");
}
$("#legend").addEventListener("click", e => {
  const b = e.target.closest("[data-k]"); if (!b) return;
  const s = PL.series.get(b.dataset.k); s.on = !s.on;
  b.classList.toggle("off", !s.on); b.setAttribute("aria-pressed", s.on); PL.dirty = true;
});
function syncWinSelect() {
  const sel = $("#plotWin"), preset = [...sel.options].some(o => o.value === String(PL.win) && o.id !== "winCustom");
  const c = $("#winCustom");
  if (preset) sel.value = String(PL.win);
  else { c.value = String(PL.win); c.textContent = `${PL.win} points (zoom)`; c.hidden = false; sel.value = c.value; }
}
$("#plotWin").addEventListener("change", e => { PL.win = PL.presetWin = +e.target.value; $("#winCustom").hidden = true; PL.view.live = true; PL.dirty = true; });
$("#btnPlotPause").addEventListener("click", e => {
  PL.paused = !PL.paused;
  e.currentTarget.innerHTML = PL.paused ? `${icon("play")}Reprendre` : `${icon("pause")}Pause`;
  e.currentTarget.setAttribute("aria-pressed", PL.paused);
});
function plotFit() {
  PL.view = { live: true, x0: 0, x1: 0, yAuto: true, y0: 0, y1: 1 };
  PL.win = PL.presetWin; $("#winCustom").hidden = true; syncWinSelect(); PL.dirty = true;
}
$("#btnPlotFit").addEventListener("click", plotFit);

/* ---- téléchargements ---- */
function downloadBlob(blob, name) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
const stamp = () => new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
function plotCSV() {
  if (!PL.series.size) return toast("Rien à exporter : le traceur est vide", "warn");
  const names = [...PL.series.keys()], rows = new Map();
  for (const s of PL.series.values()) for (const [n, v] of s.data) { let r = rows.get(n); if (!r) rows.set(n, r = {}); r[s.name] = v; }
  const q = x => /[",;\n]/.test(x) ? `"${x.replace(/"/g, '""')}"` : x;
  const out = [["echantillon", "temps_s", ...names].map(q).join(",")];
  for (const n of [...rows.keys()].sort((a, b) => a - b)) {
    const r = rows.get(n), t = PL.tmap.get(n);
    out.push([n, t ? ((t - PL.t0) / 1000).toFixed(3) : "", ...names.map(k => r[k] === undefined ? "" : r[k])].join(","));
  }
  downloadBlob(new Blob([out.join("\n") + "\n"], { type: "text/csv;charset=utf-8" }), `${S.project || "traceur"}-${stamp()}.csv`);
  toast(`${rows.size} lignes exportées`, "ok", 1800);
}
function plotPNG() {
  const cv = $("#plot");
  if (!PL.series.size || !cv.width) return toast("Rien à capturer : le traceur est vide", "warn");
  const hov = PL.hover; PL.hover = null; paintPlot(); PL.hover = hov;
  const css = getComputedStyle(document.documentElement), dpr = cv.width / cv.clientWidth;
  const head = Math.round(30 * dpr), out = document.createElement("canvas");
  out.width = cv.width; out.height = cv.height + head;
  const c = out.getContext("2d");
  c.fillStyle = css.getPropertyValue("--plot-bg").trim() || "transparent"; c.fillRect(0, 0, out.width, out.height);
  c.font = `${Math.round(12 * dpr)}px ${css.getPropertyValue("--mono")}`; c.textBaseline = "middle";
  let x = 16 * dpr;
  for (const s of PL.series.values()) {
    if (!s.on) continue;
    c.fillStyle = css.getPropertyValue("--p" + s.ci).trim(); c.fillRect(x, head / 2 - 5 * dpr, 10 * dpr, 10 * dpr);
    c.fillStyle = css.getPropertyValue("--plot-text").trim(); c.fillText(s.name, x + 16 * dpr, head / 2);
    x += 16 * dpr + c.measureText(s.name).width + 22 * dpr;
  }
  c.drawImage(cv, 0, head);
  out.toBlob(b => { downloadBlob(b, `${S.project || "traceur"}-${stamp()}.png`); toast("Capture enregistrée", "ok", 1800); }, "image/png");
}
$("#btnPlotCsv").addEventListener("click", plotCSV);
$("#btnPlotPng").addEventListener("click", plotPNG);

/* ---- géométrie de la vue ---- */
function plotRange() {
  const v = PL.view;
  if (v.live) return [Math.max(0, PL.n - PL.win), Math.max(PL.n, 1)];
  return [v.x0, v.x1];
}
const plotVal = (s, i) => {          // dernière valeur connue à l'échantillon i (fonction en escalier)
  const d = s.data; let lo = 0, hi = d.length - 1;
  if (!d.length || d[0][0] > i) return undefined;
  while (lo < hi) { const m = (lo + hi + 1) >> 1; if (d[m][0] <= i) lo = m; else hi = m - 1; }
  return d[lo][1];
};
function niceStep(r) { const p = Math.pow(10, Math.floor(Math.log10(r || 1))), n = r / p; return (n < 1.5 ? 1 : n < 3 ? 2 : n < 7 ? 5 : 10) * p; }
function fmtNum(v) { return v === undefined || v === null || isNaN(v) ? "—" : Math.abs(v) >= 1e5 || (Math.abs(v) < 1e-3 && v !== 0) ? v.toExponential(1) : +v.toFixed(3) + ""; }

function paintPlot() {
  const cv = $("#plot"), dpr = window.devicePixelRatio || 1;
  const w = cv.clientWidth, h = cv.clientHeight;
  if (!w || !h) return;
  if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
  const c = cv.getContext("2d"), css = getComputedStyle(document.documentElement), cs = n => css.getPropertyValue(n).trim();
  c.setTransform(dpr, 0, 0, dpr, 0, 0);
  c.clearRect(0, 0, w, h);
  const L = 56, R = 16, T = 14, B = 26, pw = w - L - R, ph = h - T - B;
  const [x0, x1] = plotRange(), span = Math.max(1, x1 - x0);
  // échelle verticale : automatique sur les courbes visibles, sinon celle choisie à la souris
  let lo = Infinity, hi = -Infinity;
  for (const s of PL.series.values()) {
    let mn = Infinity, mx = -Infinity;
    for (let i = s.data.length - 1; i >= 0; i--) { const [n, v] = s.data[i]; if (n > x1 + 1) continue; if (n < x0 - 1) break; if (v < mn) mn = v; if (v > mx) mx = v; }
    s.vmin = mn; s.vmax = mx;
    if (s.on) { if (mn < lo) lo = mn; if (mx > hi) hi = mx; }
  }
  if (!PL.view.yAuto) { lo = PL.view.y0; hi = PL.view.y1; }
  else {
    if (!isFinite(lo)) { lo = -1; hi = 1; }
    if (lo === hi) { lo -= 1; hi += 1; }
    const pad = (hi - lo) * .12; lo -= pad; hi += pad;
  }
  const X = i => L + (i - x0) / span * pw, Y = v => T + (1 - (v - lo) / (hi - lo)) * ph;
  PL.geo = { L, T, pw, ph, x0, x1, lo, hi, w, h };
  // grille
  c.font = "11px " + cs("--mono"); c.textAlign = "right"; c.textBaseline = "middle";
  const step = niceStep((hi - lo) / 5);
  for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) {
    const y = Y(v);
    c.strokeStyle = Math.abs(v) < step / 1e6 ? cs("--plot-zero") : cs("--plot-grid");
    c.lineWidth = 1; c.beginPath(); c.moveTo(L, y); c.lineTo(w - R, y); c.stroke();
    c.fillStyle = cs("--plot-text2"); c.fillText(fmtNum(v), L - 8, y);
  }
  c.textAlign = "center"; c.textBaseline = "top"; c.fillStyle = cs("--plot-text2");
  for (let k = 0; k <= 4; k++) { const i = Math.round(x0 + span * k / 4); c.fillText(i, X(i), h - B + 8); }
  if (!PL.series.size) {
    c.fillStyle = cs("--plot-text2"); c.font = "13px " + cs("--sans"); c.textBaseline = "middle";
    c.fillText("En attente de données au format nom:valeur", L + pw / 2, T + ph / 2);
    return;
  }
  // courbes
  c.save(); c.beginPath(); c.rect(L, T - 4, pw, ph + 8); c.clip();
  for (const s of PL.series.values()) {
    if (!s.on || !s.data.length) continue;
    const col = cs("--p" + s.ci);
    let a = s.data.length - 1; while (a > 0 && s.data[a][0] >= x0 - 1) a--;
    let b = a; while (b < s.data.length - 1 && s.data[b][0] <= x1 + 1) b++;
    const pts = s.data.slice(a, b + 1);
    if (!pts.length) continue;
    c.beginPath();
    pts.forEach(([i, v], k) => k ? c.lineTo(X(i), Y(v)) : c.moveTo(X(i), Y(v)));
    c.strokeStyle = col; c.lineWidth = 2; c.lineJoin = "round"; c.stroke();
    if (pts.length > 1) {
      const grad = c.createLinearGradient(0, T, 0, T + ph);
      grad.addColorStop(0, col + "30"); grad.addColorStop(1, col + "00");
      c.lineTo(X(pts[pts.length - 1][0]), T + ph); c.lineTo(X(pts[0][0]), T + ph); c.closePath(); c.fillStyle = grad; c.fill();
    }
    if (PL.view.live) { const [li, lv] = pts[pts.length - 1]; c.beginPath(); c.arc(X(li), Y(lv), 3.5, 0, Math.PI * 2); c.fillStyle = col; c.fill(); }
  }
  c.restore();
  // survol : ligne verticale et points sur chaque courbe
  if (PL.hover) {
    const i = PL.hover.i, x = X(i);
    c.strokeStyle = cs("--plot-text2"); c.lineWidth = 1; c.setLineDash([4, 4]);
    c.beginPath(); c.moveTo(x, T); c.lineTo(x, T + ph); c.stroke(); c.setLineDash([]);
    for (const s of PL.series.values()) {
      const v = s.on ? plotVal(s, i) : undefined; if (v === undefined) continue;
      c.beginPath(); c.arc(x, Y(v), 4, 0, Math.PI * 2); c.fillStyle = cs("--p" + s.ci); c.fill();
      c.lineWidth = 2; c.strokeStyle = cs("--plot-bg"); c.stroke();
    }
  }
}
/* mise à jour de la légende (dernière valeur, min et max de la fenêtre affichée) */
function paintLegend() {
  $$("#legend [data-k]").forEach(b => {
    const s = PL.series.get(b.dataset.k); if (!s) return;
    b.querySelector(".lv").textContent = fmtNum(s.last);
    b.querySelector(".lm").textContent = isFinite(s.vmin) ? `min ${fmtNum(s.vmin)} · max ${fmtNum(s.vmax)}` : "";
  });
}
function drawPlot() {
  requestAnimationFrame(drawPlot);
  if (activeTab !== "plotter" || !PL.dirty || !panelOpen()) return;
  PL.dirty = false;
  paintPlot(); paintLegend(); paintPlotTip();
}
function paintPlotTip() {
  const tip = $("#plotTip");
  if (!PL.hover || !PL.geo || !PL.series.size) { tip.hidden = true; return; }
  const i = PL.hover.i, rows = [...PL.series.values()].filter(s => s.on && plotVal(s, i) !== undefined);
  if (!rows.length) { tip.hidden = true; return; }
  const t = PL.tmap.get(i);
  tip.innerHTML = `<div class="th">Échantillon ${i}${t ? ` · ${((t - PL.t0) / 1000).toFixed(2)} s` : ""}</div>` +
    rows.map(s => `<div><i style="background:var(--p${s.ci})"></i><span>${esc(s.name)}</span><b>${fmtNum(plotVal(s, i))}</b></div>`).join("");
  tip.hidden = false;
  const g = PL.geo, x = g.L + (i - g.x0) / Math.max(1, g.x1 - g.x0) * g.pw;
  const left = x + 14 + tip.offsetWidth > g.w - 6 ? x - 14 - tip.offsetWidth : x + 14;
  tip.style.left = Math.max(4, left) + "px"; tip.style.top = Math.max(4, Math.min(PL.hover.y - 10, g.h - tip.offsetHeight - 30)) + "px";
}
requestAnimationFrame(drawPlot);
new ResizeObserver(() => PL.dirty = true).observe($("#plot"));

/* ---- souris : survol, zoom à la molette, déplacement au glisser ---- */
(() => {
  const cv = $("#plot");
  const local = e => { const r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
  const clampView = (x0, x1) => {   // reste dans [0, n]
    const w = x1 - x0, n = Math.max(PL.n, 2);
    if (w >= n) return [0, n];
    if (x0 < 0) return [0, w];
    if (x1 > n) return [n - w, n];
    return [x0, x1];
  };
  const leaveLive = () => { if (PL.view.live) { const [a, b] = plotRange(); PL.view.live = false; PL.view.x0 = a; PL.view.x1 = b; } };
  cv.addEventListener("wheel", e => {
    if (!PL.geo || !PL.series.size) return;
    e.preventDefault();
    const [mx, my] = local(e), g = PL.geo, f = Math.exp(Math.max(-200, Math.min(200, e.deltaY)) * 0.0015);
    if (e.shiftKey) {                       // zoom vertical autour du curseur
      const va = g.hi - (my - g.T) / g.ph * (g.hi - g.lo), h2 = (g.hi - g.lo) * f;
      const a = (my - g.T) / g.ph;
      PL.view.yAuto = false; PL.view.y1 = va + a * h2; PL.view.y0 = PL.view.y1 - h2;
    } else if (PL.view.live) {              // en direct : le bord droit reste ancré sur la dernière mesure
      const shown = Math.min(PL.win, Math.max(PL.n, 20));   // largeur réellement affichée
      PL.win = Math.round(Math.max(10, Math.min(Math.max(PL.n, 20), 6000, shown * f))); syncWinSelect();
    } else {
      const a = Math.max(0, Math.min(1, (mx - g.L) / g.pw)), w = g.x1 - g.x0, w2 = Math.max(10, Math.min(Math.max(PL.n, 20), w * f));
      const xa = g.x0 + a * w, x0 = xa - a * w2;
      [PL.view.x0, PL.view.x1] = clampView(x0, x0 + w2);
    }
    PL.dirty = true;
  }, { passive: false });
  cv.addEventListener("pointerdown", e => {
    if (!PL.geo || e.button !== 0) return;
    cv.setPointerCapture(e.pointerId);
    const [mx, my] = local(e);
    PL.drag = { mx, my, x0: PL.geo.x0, x1: PL.geo.x1, lo: PL.geo.lo, hi: PL.geo.hi, moved: false };
    cv.classList.add("grab");
  });
  cv.addEventListener("pointermove", e => {
    if (!PL.geo) return;
    const [mx, my] = local(e), g = PL.geo;
    if (PL.drag) {
      const d = PL.drag, dx = mx - d.mx, dy = my - d.my;
      if (!d.moved && Math.hypot(dx, dy) < 4) return;
      d.moved = true; PL.hover = null;
      const w = d.x1 - d.x0, shift = -dx / g.pw * w;
      const [x0, x1] = clampView(d.x0 + shift, d.x1 + shift);
      if (x1 >= PL.n - 0.5 && shift > 0) { PL.view.live = true; PL.win = Math.round(w); syncWinSelect(); }   // retour au bord droit : on suit de nouveau
      else { PL.view.live = false; PL.view.x0 = x0; PL.view.x1 = x1; }
      if (Math.abs(dy) > 6 || !PL.view.yAuto) { const dv = dy / g.ph * (d.hi - d.lo); PL.view.yAuto = false; PL.view.y0 = d.lo + dv; PL.view.y1 = d.hi + dv; }
      PL.dirty = true; return;
    }
    if (mx < g.L || mx > g.L + g.pw || my < g.T || my > g.T + g.ph) { if (PL.hover) { PL.hover = null; PL.dirty = true; } return; }
    const i = Math.max(Math.ceil(g.x0), Math.min(Math.floor(g.x1), Math.round(g.x0 + (mx - g.L) / g.pw * (g.x1 - g.x0))));
    PL.hover = { i, y: my }; PL.dirty = true;
  });
  const end = () => { PL.drag = null; cv.classList.remove("grab"); };
  cv.addEventListener("pointerup", end); cv.addEventListener("pointercancel", end);
  cv.addEventListener("pointerleave", () => { if (!PL.drag && PL.hover) { PL.hover = null; PL.dirty = true; } });
  cv.addEventListener("dblclick", plotFit);
})();

/* ------------------------------------------------------------------ réglages du projet (.forge.json) */
const confTimers = {};
function confSave(section) {
  const project = S.project; if (!project) return;
  const data = S.conf[section], key = project + "/" + section;
  clearTimeout(confTimers[key]);
  confTimers[key] = setTimeout(() => api("/api/conf", { project, section, data }).catch(e => toast("Réglages du projet non enregistrés : " + e.message, "error")), 400);
}
function runFieldsLoad() {
  const r = S.conf.run || {};
  $("#runArgs").value = r.args || ""; $("#runStdin").value = r.stdin || ""; $("#runClear").checked = !!r.clear;
}
["runArgs", "runStdin", "runClear"].forEach(id => $("#" + id).addEventListener(id === "runClear" ? "change" : "input", () => {
  if (!S.project) return;
  S.conf.run = { args: $("#runArgs").value, stdin: $("#runStdin").value, clear: $("#runClear").checked };
  confSave("run");
}));

/* ------------------------------------------------------------------ inspecteur à onglets */
function openInsp(name) {
  if (mqInsp.matches ? !INSP.classList.contains("drawer") : CONTENT.classList.contains("noinsp")) toggleInspector();
  showInsp(name);
}
function showInsp(name) {
  prefs.insp = name; savePrefs();
  $$("#itabs button").forEach(b => { const on = b.dataset.it === name; b.classList.toggle("active", on); b.setAttribute("aria-selected", on); b.tabIndex = on ? 0 : -1; });
  $$(".ipane").forEach(p => p.classList.toggle("active", p.dataset.it === name));
  if (name === "snaps") snapsLoad();
  if (name === "outline") outlineRender();
}
$("#itabs").addEventListener("click", e => { const b = e.target.closest("[data-it]"); if (b) showInsp(b.dataset.it); });
$("#itabs").addEventListener("keydown", e => {
  if (!["ArrowRight", "ArrowLeft"].includes(e.key)) return;
  const l = $$("#itabs button"), i = l.indexOf(document.activeElement); if (i < 0) return;
  e.preventDefault(); const n = l[(i + (e.key === "ArrowRight" ? 1 : l.length - 1)) % l.length]; showInsp(n.dataset.it); n.focus();
});

/* ------------------------------------------------------------------ structure du fichier (fonctions, classes…) */
const OUTLINE = [
  [/^\s*(?:async\s+)?def\s+(\w+)/, "fn", ["python"]], [/^\s*class\s+(\w+)/, "class", ["python", "ruby", "javascript", "typescript", "java", "kotlin", "csharp", "cpp", "dart", "php"]],
  [/^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*([\w$]+)/, "fn", ["javascript", "typescript", "php", "web"]],
  [/^\s*(?:export\s+)?(?:const|let|var)\s+([\w$]+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[\w$]+)\s*=>/, "fn", ["javascript", "typescript", "web"]],
  [/^\s*(?:export\s+)?(?:interface|type|enum)\s+(\w+)/, "type", ["typescript"]],
  [/^\s*func\s+(?:\([^)]*\)\s*)?(\w+)/, "fn", ["go"]], [/^\s*type\s+(\w+)/, "type", ["go"]],
  [/^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:unsafe\s+)?fn\s+(\w+)/, "fn", ["rust", "zig"]], [/^\s*(?:pub\s+)?(?:struct|enum|trait|impl(?:<[^>]*>)?)\s+([\w:<>]+)/, "type", ["rust"]],
  [/^\s*(?:pub\s+)?const\s+(\w+)\s*=\s*(?:struct|enum|union)/, "type", ["zig"]],
  [/^\s*(?:public|private|protected|internal|static|final|override|abstract|virtual|async|\s)*(?:fun|void|int|long|double|float|boolean|bool|char|String|string|var|[\w<>\[\],]+)\s+(\w+)\s*\([^;{]*\)?\s*(?:\{|=|throws|$)/, "fn", ["java", "kotlin", "csharp", "dart", "c", "cpp"]],
  [/^\s*fun\s+(?:<[^>]*>\s*)?([\w.]+)/, "fn", ["kotlin"]],
  [/^\s*(?:struct|enum|union|typedef\s+struct)\s+(\w+)/, "type", ["c", "cpp"]], [/^\s*(?:module)\s+(\w+)/, "type", ["ruby", "haskell"]],
  [/^\s*def\s+(?:self\.)?(\w+[?!=]?)/, "fn", ["ruby"]], [/^\s*(?:local\s+)?function\s+([\w.:]+)/, "fn", ["lua"]],
  [/^\s*(?:function\s+)?(\w+)\s*\(\)\s*\{/, "fn", ["bash"]], [/^\s*function\s+(\w+)/, "fn", ["bash", "julia"]], [/^\s*sub\s+(\w+)/, "fn", ["perl"]],
  [/^\s*([\w.]+)\s*<-\s*function/, "fn", ["r"]], [/^(\w+)\s*::/, "fn", ["haskell"]], [/^\s*(?:mutable\s+)?struct\s+(\w+)/, "type", ["julia"]],
  [/<h([1-6])[^>]*>([^<]{1,60})/i, "h", ["web"]], [/^\s*([^{}\/@][^{}]{0,60}?)\s*\{\s*$/, "css", ["css"]]
];
const CTRL = new Set(["if", "for", "while", "switch", "return", "else", "catch", "sizeof", "new", "throw", "case", "do", "elif"]);
function outlineOf(text, lang) {
  const out = [], rules = OUTLINE.filter(r => r[2].includes(lang));
  const lines = text.split("\n");
  for (let i = 0; i < lines.length && out.length < 400; i++) {
    const ln = lines[i];
    for (const [rx, kind] of rules) {
      const m = rx.exec(ln);
      if (!m) continue;
      let name = kind === "h" ? m[2].trim() : m[1];
      if (!name || CTRL.has(name)) continue;
      if (kind === "h") name = "h" + m[1] + " · " + name;
      out.push({ name, kind: kind === "css" ? "sel" : kind === "h" ? "titre" : kind, line: i + 1, depth: Math.min(4, Math.floor((ln.match(/^\s*/)[0].replace(/\t/g, "    ").length) / 4)) });
      break;
    }
  }
  return out;
}
let outlineTimer = 0;
function outlineRender() {
  if (prefs.insp !== "outline") return;
  clearTimeout(outlineTimer);
  outlineTimer = setTimeout(() => {
    const box = $("#outline");
    if (!S.file) { box.innerHTML = `<p class="dim" style="margin:6px">Aucun fichier ouvert.</p>`; $("#outlineInfo").textContent = ""; return; }
    const items = outlineOf(ED.ta.value, ED.lang), cur = ED.lineOf(ED.ta.selectionStart) + 1;
    let here = -1; items.forEach((it, i) => { if (it.line <= cur) here = i; });
    $("#outlineInfo").textContent = items.length ? `${items.length}` : "";
    box.innerHTML = items.length ? items.map((it, i) => `<button data-l="${it.line}" class="${i === here ? "cur" : ""}" style="padding-left:${8 + it.depth * 12}px"><i class="${it.kind === "fn" ? "fn" : ""}">${esc({ fn: "fonction", class: "classe", type: "type", sel: "règle", titre: "titre" }[it.kind] || it.kind)}</i><span>${esc(it.name)}</span><small>${it.line}</small></button>`).join("")
      : `<p class="dim" style="margin:6px">Aucune fonction ni classe repérée dans ${esc(S.file)}.</p>`;
  }, 120);
}
$("#outline").addEventListener("click", e => { const b = e.target.closest("[data-l]"); if (b) ED.goto(+b.dataset.l); });

/* ------------------------------------------------------------------ formateurs et analyseurs */
async function formatFile() {
  if (!S.file) return;
  try {
    await saveAll();
    const r = await api("/api/format", { project: S.project, file: S.file, lang: S.info.lang });
    if (!r.changed) return toast(`${r.tool} : déjà bien formaté`, "info", 1800);
    const top = ED.ta.scrollTop, sel = ED.ta.selectionStart;
    ED.ta.focus(); ED.ta.setSelectionRange(0, ED.ta.value.length); ED.insert(r.content);
    const p = Math.min(sel, r.content.length); ED.ta.setSelectionRange(p, p); ED.ta.scrollTop = top; ED.sync();
    await saveAll();
    toast(`Formaté avec ${r.tool}`, "ok", 1800);
  } catch (e) { toast(e.message, "warn", 6000); }
}
async function lintFile() {
  if (!S.file) return;
  try {
    await saveAll();
    const r = await api("/api/lint", { project: S.project, file: S.file, lang: S.info.lang });
    setDiags([...S.diags.filter(d => d.file !== S.file), ...r.items]);
    toast(r.items.length ? `${r.tool} : ${plural(r.items.length, "remarque", "remarques")} (F8 pour les parcourir)` : `${r.tool} : rien à signaler`, r.items.length ? "warn" : "ok", 3000);
    if (r.items.length) jumpDiag(1);
  } catch (e) { toast(e.message, "warn", 6000); }
}

/* ------------------------------------------------------------------ instantanés (git) */
const SNAP = { data: null };
function relTime(ts) {
  const s = Math.round(Date.now() / 1000 - ts), rtf = new Intl.RelativeTimeFormat("fr", { numeric: "auto" });
  if (s < 45) return "à l'instant";
  if (s < 3600) return rtf.format(-Math.round(s / 60), "minute");
  if (s < 86400) return rtf.format(-Math.round(s / 3600), "hour");
  if (s < 86400 * 7) return rtf.format(-Math.round(s / 86400), "day");
  return new Date(ts * 1000).toLocaleDateString("fr-FR");
}
async function snapsLoad() {
  const box = $("#snapBody");
  if (!S.project) { box.innerHTML = `<p class="dim" style="margin:0">Ouvrez un projet.</p>`; return; }
  try { SNAP.data = await api("/api/snapshots?" + qs({ project: S.project })); snapsRender(); }
  catch (e) { box.innerHTML = `<p class="dim" style="margin:0">${esc(e.message)}</p>`; }
}
function snapsRender() {
  const d = SNAP.data, box = $("#snapBody");
  if (!d.git) { box.innerHTML = `<div class="emptyp" style="padding:8px">${icon("alert")}<br><b>git n'est pas installé</b><br><span class="dim">Les instantanés utilisent git.<br>Installez l'extension Git (onglet Extensions) puis rouvrez cet onglet.</span></div>`; return; }
  const st = !d.items.length ? "Aucun instantané pour l'instant." : d.dirty ? "Modifications depuis le dernier instantané." : "Identique au dernier instantané.";
  box.innerHTML = `<button class="btn primary" id="snapNew" style="width:100%;justify-content:center" title="Enregistre l'état actuel du projet">${icon("save")}Instantané</button>
    <label class="switch snapauto" title="Après chaque exécution réussie, l'état du projet est enregistré automatiquement"><input type="checkbox" id="snapAuto" ${d.auto ? "checked" : ""}><i></i><span>Instantané automatique après chaque exécution réussie</span></label>
    <p class="dim snapst${d.dirty && d.items.length ? " dirty" : ""}">${st}</p>
    <div class="snaplist">${d.items.map(it => `<div class="snap" data-rev="${esc(it.rev)}"><div><b>${esc(it.label)}</b>${it.auto ? ` <span class="tag auto">auto</span>` : ""}</div>
      <div class="snap-m"><code>${esc(it.rev)}</code> · <time title="${esc(new Date(it.time * 1000).toLocaleString("fr-FR"))}">${esc(relTime(it.time))}</time></div>
      <div class="snap-a"><button class="btn sm" data-a="diff" title="Voir les différences avec l'état actuel">Comparer</button><button class="btn sm" data-a="restore" title="Revenir à cet instantané">Restaurer</button></div></div>`).join("")}</div>`;
}
function snapModal() {
  return new Promise(res => {
    let out = null;
    modal(`<div class="modal glass"><h2>Nouvel instantané</h2><p class="sub">Enregistre l'état actuel du projet (tous ses fichiers). Vous pourrez le comparer ou y revenir à tout moment.</p>
      <div class="field"><label for="snL">Description (facultative)</label><input id="snL" placeholder="ex. Avant d'ajouter le capteur" maxlength="120" autocomplete="off"></div>
      <div class="mactions"><button class="btn" data-x>Annuler</button><button class="btn primary" data-ok>Enregistrer</button></div></div>`,
      (ov, close) => {
        const i = $("#snL", ov); i.focus();
        const ok = () => { out = i.value.trim(); close(); };
        $("[data-ok]", ov).onclick = ok; $("[data-x]", ov).onclick = close;
        i.onkeydown = e => { if (e.key === "Enter") ok(); };
      }, () => res(out));
  });
}
async function snapCreate() {
  if (!S.project) return;
  try {
    await saveAll();
    const label = await snapModal(); if (label === null) return;
    const r = await api("/api/snapshots/create", { project: S.project, label });
    toast(r.created ? `Instantané enregistré (${r.hash})` : "Rien de nouveau depuis le dernier instantané", r.created ? "ok" : "info");
    snapsLoad();
  } catch (e) { toast(e.message, "error"); }
}
function renderPatch(d) {
  const LBL = { M: "modifié", A: "ajouté depuis l'instantané", D: "supprimé depuis l'instantané", T: "type modifié" };
  const blocks = d.patch.split(/^diff --git /m).slice(1).map(b => {
    const lines = b.split("\n"), name = (/ b\/(.+)$/.exec(lines[0]) || [, lines[0]])[1], f = d.files.find(x => x.file === name);
    const body = lines.slice(1).filter(l => !/^(index |--- |\+\+\+ |new file mode|deleted file mode|old mode|new mode)/.test(l) && l !== "")
      .map(l => `<span class="${l[0] === "+" ? "a" : l[0] === "-" ? "d" : l[0] === "@" ? "h" : ""}">${esc(l) || " "}</span>`).join("");
    return `<div class="df"><h4>${esc(name)} <small class="dim">${f ? LBL[f.status] || "" : ""}</small></h4><pre>${body}</pre></div>`;
  });
  const missing = d.files.filter(f => !d.patch.includes(" b/" + f.file));
  return blocks.join("") + (missing.length ? `<div class="df"><h4>Autres fichiers</h4><pre><span>${esc(missing.map(f => f.file).join("\n"))}</span></pre></div>` : "") + (d.truncated ? `<p class="dim" style="padding:8px 12px">Différences tronquées (trop volumineuses).</p>` : "");
}
async function snapDiff(rev) {
  try {
    await saveAll();
    const it = SNAP.data && SNAP.data.items.find(i => i.rev === rev), d = await api("/api/snapshots/diff?" + qs({ project: S.project, rev }));
    modal(`<div class="modal diff glass"><h2>Comparer avec l'instantané ${esc(rev)}</h2>
      <p class="sub">« ${esc(it ? it.label : rev)} » → état actuel du projet. <span class="dl-d">−</span> dans l'instantané, <span class="dl-a">+</span> dans l'état actuel · ${plural(d.files.length, "fichier différent", "fichiers différents")}.</p>
      <div class="diffbody">${d.files.length ? renderPatch(d) : `<p class="dim" style="padding:14px">Aucune différence : le projet est identique à cet instantané.</p>`}</div>
      <div class="mactions" style="margin-top:14px"><button class="btn" data-x>Fermer</button>${d.files.length ? `<button class="btn danger" data-restore>Restaurer cet instantané…</button>` : ""}</div></div>`,
      (ov, close) => {
        $("[data-x]", ov).onclick = close; $("[data-x]", ov).focus();
        const r = $("[data-restore]", ov); if (r) r.onclick = () => { close(); snapRestore(rev); };
      });
  } catch (e) { toast(e.message, "error"); }
}
async function snapRestore(rev) {
  try {
    await saveAll();
    const it = SNAP.data && SNAP.data.items.find(i => i.rev === rev), d = await api("/api/snapshots/diff?" + qs({ project: S.project, rev }));
    if (!d.files.length) return toast("Le projet est déjà identique à cet instantané", "info");
    const back = d.files.filter(f => f.status !== "A"), gone = d.files.filter(f => f.status === "A");
    const list = fs => fs.slice(0, 6).map(f => `<code>${esc(f.file)}</code>`).join(", ") + (fs.length > 6 ? `, … (+${fs.length - 6})` : "");
    const yes = await confirmModal("Restaurer cet instantané ?",
      `Le projet reviendra à l'état de « <b>${esc(it ? it.label : rev)}</b> » (${esc(rev)}${it ? ", " + esc(relTime(it.time)) : ""}).<br><br>
      ${back.length ? `${plural(back.length, "fichier sera remplacé ou recréé", "fichiers seront remplacés ou recréés")} : ${list(back)}.<br>` : ""}
      ${gone.length ? `${plural(gone.length, "fichier créé depuis sera supprimé", "fichiers créés depuis seront supprimés")} : ${list(gone)}.<br>` : ""}<br>
      Rien n'est perdu : votre état actuel reste dans les instantanés (un instantané « Avant restauration » est créé s'il y a des modifications non enregistrées).`, "Restaurer", true);
    if (!yes) return;
    const r = await api("/api/snapshots/restore", { project: S.project, rev });
    S.docs = {};
    await openProject(S.project);
    snapsLoad();
    toast(`Projet restauré (${plural(r.restored + r.deleted, "fichier touché", "fichiers touchés")})${r.safety ? " — ancien état gardé dans " + r.safety : ""}`, "ok", 5000);
  } catch (e) { toast(e.message, "error"); }
}
$("#snapBody").addEventListener("click", e => {
  if (e.target.closest("#snapNew")) return snapCreate();
  const b = e.target.closest("[data-a]"); if (!b) return;
  const rev = b.closest(".snap").dataset.rev;
  if (b.dataset.a === "diff") snapDiff(rev); else snapRestore(rev);
});
$("#snapBody").addEventListener("change", e => {
  if (e.target.id !== "snapAuto") return;
  S.conf.snapshots = { auto: e.target.checked }; confSave("snapshots"); SNAP.data.auto = e.target.checked;
  toast(e.target.checked ? "Instantané automatique après chaque exécution réussie" : "Instantané automatique désactivé", "info", 2000);
});

/* ------------------------------------------------------------------ export / import (.zip) */
async function exportProject(name = S.project) {
  if (!name) return toast("Ouvrez d'abord un projet", "warn");
  try {
    if (name === S.project) await saveAll();
    const r = await fetch("/api/export?" + qs({ project: name }), { headers: { "X-Token": TOKEN } });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || r.statusText);
    downloadBlob(await r.blob(), `${name}.zip`);
    toast(`« ${name}.zip » téléchargé`, "ok");
  } catch (e) { toast("Export impossible : " + e.message, "error", 6000); }
}
async function importZip(file) {
  if (!file) return;
  try {
    const r = await fetch("/api/import", { method: "POST", headers: { "X-Token": TOKEN, "Content-Type": "application/zip" }, body: await file.arrayBuffer() });
    const j = await r.json().catch(() => ({ error: "Réponse invalide du serveur" }));
    if (!r.ok || j.error) throw new Error(j.error || r.statusText);
    await loadProjects(); await openProject(j.name);
    toast(j.renamed ? `Projet importé sous le nom « ${j.name} »` : `Projet « ${j.name} » importé`, "ok", 4500);
  } catch (e) { toast("Import impossible : " + e.message, "error", 6000); }
}
const pickZip = () => $("#importFile").click();
$("#btnExport").addEventListener("click", () => exportProject());
$("#btnImport").addEventListener("click", pickZip);
$("#wImport").addEventListener("click", pickZip);
$("#importFile").addEventListener("change", e => { const f = e.target.files[0]; e.target.value = ""; importZip(f); });

function renderLangBits() { renderProjects(); renderLang(); renderWelcomeLangs(); if (activeTab === "exts") extRender(); if (activeTab === "examples") exRender(); }

/* ------------------------------------------------------------------ extensions */
const EXTV = { filter: prefs.extFilter || "all", busy: null };
async function extLoad(refresh) {
  try {
    const r = await api("/api/exts" + (refresh ? "?refresh=1" : ""));
    S.exts = r.items; S.extInfo = r;
    S.ext = Object.fromEntries(r.items.map(x => [x.id, x]));
    S.extByFile = {};
    r.items.filter(x => x.kind === "lang").sort((a, b) => (b.installed - a.installed) || (a.id === "web") - (b.id === "web")).forEach(x => (x.exts || []).forEach(e => { if (!S.extByFile[e]) S.extByFile[e] = x.id; }));
    Object.keys(RX_CACHE).forEach(k => { if (!HLDEF[k]) delete RX_CACHE[k]; });
    renderLang(); renderProjects(); renderWelcomeLangs();
    if (activeTab === "exts") extRender();
    if (activeTab === "examples") exRender();
    if (S.file) { const l = langOfFile(S.file); if (l !== ED.lang) { ED.lang = l; ED.lines = 0; ED.render(); } }
    badge("bExt", r.errors.length);
  } catch (e) { toast("Extensions : " + e.message, "error"); }
}
function extCard(x) {
  const st = x.installed ? `<span class="tag">${x.version ? "v" + esc(x.version) : "installé"}</span>` : `<span class="tag miss">non installé</span>`;
  const busy = EXTV.busy === x.id;
  const acts = [];
  if (busy) acts.push(`<button class="btn sm" disabled><span class="spin"></span>Installation…</button>`);
  else if (!x.installed && x.plan) acts.push(`<button class="btn sm primary" data-a="install" title="${esc(x.plan)}${x.root ? " — droits administrateur" : ""}">${icon("download")}Installer</button>`);
  if (x.installed && x.kind === "lang" && x.enabled) acts.push(`<button class="btn sm" data-a="new" title="Nouveau projet ${esc(x.name)}">${icon("plus")}Projet</button>`);
  if (x.removable && x.installed && !busy) acts.push(`<button class="btn sm" data-a="remove" title="Désinstaller">${icon("trash")}</button>`);
  if (x.source === "custom") acts.push(`<button class="btn sm" data-a="edit" title="Modifier le JSON">${icon("edit")}</button>`);

  const kind = x.kind === "lang" ? "langage" : "outil" + (x.format && x.lint ? " · formateur + analyseur" : x.format ? " · formateur" : x.lint ? " · analyseur" : "");
  return `<div class="xcard ${x.enabled ? "" : "off"}" data-id="${esc(x.id)}">
    <div class="xhead"><div class="pic" style="${langStyle(x)}">${esc(x.abbr)}</div><div style="min-width:0"><b>${esc(x.name)}</b><small title="${esc(x.installed ? x.path || "" : x.plan || x.why || "")}">${x.installed ? esc(x.path || "intégré") : esc(x.plan || x.why || "")}</small></div><label class="switch" title="${x.enabled ? "Activée — décocher pour la masquer" : "Désactivée — cocher pour l'activer"}"><input type="checkbox" data-a="toggle" ${x.enabled ? "checked" : ""} aria-label="Activer ${esc(x.name)}"><i></i></label></div>
    <p>${esc(x.desc || "")}</p>
    <div class="meta"><span class="tag kind">${esc(kind)}</span>${x.source === "custom" ? `<span class="tag cust">personnelle</span>` : ""}${st}<span class="spacer"></span>${acts.join("")}</div></div>`;
}
function extRender() {
  if (!S.exts.length) return;
  const q = $("#extQ").value.trim().toLowerCase(), f = EXTV.filter;
  $$("#extFilter button").forEach(b => b.setAttribute("aria-checked", b.dataset.f === f));
  let list = S.exts.filter(x => (f === "all" || (f === "inst" ? x.installed : x.kind === f)) && (!q || `${x.name} ${x.id} ${x.desc} ${(x.langs || []).join(" ")} ${x.kind === "tool" ? "outil formateur analyseur" : "langage"}`.toLowerCase().includes(q)));
  list.sort((a, b) => (a.kind === b.kind ? 0 : a.kind === "lang" ? -1 : 1) || (b.installed - a.installed) || a.name.localeCompare(b.name, "fr"));
  const n = S.exts.filter(x => x.installed).length, info = S.extInfo || {};
  $("#extInfo").textContent = `${n} installée(s) sur ${S.exts.length}` + (info.pmName ? ` · ${info.pmName}` : "");
  const errs = (info.errors || []).map(e => `<div class="check fail" style="grid-column:1/-1"><div class="ic">${icon("x")}</div><div><b>Extension personnelle invalide</b><p>${esc(e)}</p></div></div>`).join("");
  $("#extList").innerHTML = errs + (list.length ? list.map(extCard).join("") : `<div class="emptyp">${icon("puzzle")}<br>Aucune extension ne correspond.</div>`);
}
$("#extQ").addEventListener("input", () => { clearTimeout(EXTV.t); EXTV.t = setTimeout(extRender, 100); });
$("#extFilter").addEventListener("click", e => { const b = e.target.closest("[data-f]"); if (!b) return; EXTV.filter = prefs.extFilter = b.dataset.f; savePrefs(); extRender(); });
$("#btnExtRefresh").addEventListener("click", async () => { await extLoad(true); toast("Outils installés relus", "info", 1500); });
async function extInstall(id, remove) {
  const x = S.ext[id]; if (!x) return;
  try {
    await api(remove ? "/api/ext/remove" : "/api/ext/install", { id });
    EXTV.busy = id; extRender();
    showTab("terminal", false, true);
    toast(`${remove ? "Désinstallation" : "Installation"} de ${x.name} lancée — suivez-la dans le terminal`, "info", 3500);
  } catch (e) { toast(e.message, "error"); }
}
$("#extList").addEventListener("click", async e => {
  const b = e.target.closest("[data-a]"), card = e.target.closest("[data-id]"); if (!b || !card || b.dataset.a === "toggle") return;
  const id = card.dataset.id, x = S.ext[id];
  if (b.dataset.a === "install") extInstall(id);
  else if (b.dataset.a === "remove") { if (await confirmModal(`Désinstaller ${x.name} ?`, `L'outil sera retiré de votre compte (installation utilisateur).`, "Désinstaller", true)) extInstall(id, true); }
  else if (b.dataset.a === "new") newProject(id);
  else if (b.dataset.a === "edit") customExtModal(id);
});
$("#extList").addEventListener("change", async e => {
  const b = e.target.closest("[data-a=toggle]"), card = e.target.closest("[data-id]"); if (!b || !card) return;
  try { await api("/api/ext/toggle", { id: card.dataset.id, enabled: b.checked }); }
  catch (err) { toast(err.message, "error"); b.checked = !b.checked; }
});
const CUSTOM_SAMPLE = {
  id: "nim", kind: "lang", name: "Nim", abbr: "NIM", color: 7,
  desc: "Exemple d'extension personnelle : compilé avec nim, puis exécuté.",
  exts: [".nim"], main: "main.nim", bins: ["nim"], version: ["nim", "--version"],
  run: [{ needs: ["nim"], exec: ["nim", "r", "--hints:off", "{main}"] }],
  check: [{ needs: ["nim"], build: [["nim", "check", "--hints:off", "{main}"]] }],
  install: [{ pm: { apt: ["nim"], pacman: ["nim"], brew: ["nim"] } }],
  comment: "#", indent: 2,
  keywords: "proc func var let const if elif else for while in return import type object of case when",
  templates: { hello: "# {name}\necho \"Bonjour depuis Nim !\"\nfor i in 1..3:\n  echo i, \" × 7 = \", i * 7\n" }
};
async function customExtModal(id) {
  let src = JSON.stringify(CUSTOM_SAMPLE, null, 2);
  if (id) { try { const x = await api("/api/ext?" + qs({ id })); src = JSON.stringify(x, null, 2); } catch (e) { return toast(e.message, "error"); } }
  modal(`<div class="modal wide glass"><h2>${id ? "Modifier l'extension" : "Extension personnelle"}</h2>
    <p class="sub">Décrivez un langage (ou un outil) en JSON : comment l'exécuter, le vérifier, l'installer, et ses modèles. Emplacements : <code>{main}</code> <code>{stem}</code> <code>{out}</code> <code>{exe}</code> <code>{srcs:.ext}</code> <code>{bin}</code> <code>{file}</code>. Enregistré dans <code>${esc((S.extInfo || {}).dir || "~/.config/forge-code/extensions")}</code>. N'ajoutez que des commandes de confiance.</p>
    <textarea class="json" id="cxJson" spellcheck="false" aria-label="Description JSON de l'extension">${esc(src)}</textarea>
    <div class="warnline" id="cxErr" role="alert" style="margin-top:8px"></div>
    <div class="mactions">${id ? `<button class="btn danger" data-del style="margin-right:auto">Supprimer</button>` : `<button class="btn" id="cxFile" style="margin-right:auto">${icon("folder")}Charger un .json…</button>`}<button class="btn" data-x>Annuler</button><button class="btn primary" data-ok>Enregistrer</button></div></div>`,
    (ov, close) => {
      const ta = $("#cxJson", ov); ta.focus();
      ta.addEventListener("keydown", e => { if (e.key === "Tab") { e.preventDefault(); document.execCommand("insertText", false, "  "); } });
      $("[data-x]", ov).onclick = close;
      $("[data-ok]", ov).onclick = async () => {
        let obj;
        try { obj = JSON.parse(ta.value); } catch (e) { $("#cxErr", ov).textContent = "JSON invalide : " + e.message; return; }
        try { const r = await api("/api/ext/custom", { ext: obj }); close(); toast(`Extension « ${r.id} » enregistrée`, "ok"); await extLoad(true); showTab("exts"); }
        catch (e) { $("#cxErr", ov).textContent = e.message; }
      };
      const del = $("[data-del]", ov);
      if (del) del.onclick = async () => { try { await api("/api/ext/custom/delete", { id }); close(); toast("Extension supprimée", "ok"); extLoad(true); } catch (e) { $("#cxErr", ov).textContent = e.message; } };
      const pick = $("#cxFile", ov);
      if (pick) pick.onclick = () => { const i = document.createElement("input"); i.type = "file"; i.accept = ".json,application/json"; i.onchange = async () => { const f = i.files[0]; if (f) ta.value = await f.text(); }; i.click(); };
    });
}
$("#btnExtAdd").addEventListener("click", () => customExtModal());
$("#wExt").addEventListener("click", () => showTab("exts"));
function renderWelcomeLangs() {
  const inst = S.exts.filter(x => x.kind === "lang" && x.installed && x.enabled);
  $("#wLangs").innerHTML = inst.length ? `<small>Langages prêts : cliquez pour créer un projet</small>` + inst.map(x => `<button data-l="${esc(x.id)}"><span class="lchip" style="${langStyle(x)}">${esc(x.abbr)}</span>${esc(x.name)}</button>`).join("") : "";
}
$("#wLangs").addEventListener("click", e => { const b = e.target.closest("[data-l]"); if (b) newProject(b.dataset.l); });

/* ------------------------------------------------------------------ paquets du projet */
async function pkgsLoad() {
  const list = $("#pkgList");
  if (!S.project) { list.innerHTML = `<div class="emptyp">${icon("pkg")}<br>Ouvrez un projet.</div>`; $("#pkgKind").textContent = ""; $("#pkgNote").textContent = ""; return; }
  list.innerHTML = `<div class="emptyp">Lecture…</div>`;
  try {
    const r = await api("/api/pkgs?" + qs({ project: S.project }));
    const names = { pip: "pip", npm: "npm", cargo: "Cargo", go: "Go modules", gem: "RubyGems", composer: "Composer", luarocks: "LuaRocks", cran: "CRAN", dotnet: "NuGet" };
    $("#pkgKind").textContent = r.kind ? names[r.kind] || r.kind : "";
    $("#pkgNote").textContent = r.note || "";
    const ph = { pip: "requests", npm: "lodash", cargo: "rand", go: "github.com/fatih/color", gem: "colorize", composer: "monolog/monolog", luarocks: "luasocket", cran: "ggplot2", dotnet: "Newtonsoft.Json" }[r.kind];
    $("#pkgName").placeholder = ph ? `Nom du paquet (ex. ${ph})` : "Pas de gestionnaire de paquets";
    $("#pkgName").disabled = $("#btnPkgAdd").disabled = !r.kind;
    list.innerHTML = r.items.length ? r.items.map(p => `<div class="pkg"><b title="${esc(p.name)}">${esc(p.name)}</b><small>${esc(p.version || "")}</small><button class="btn sm" data-rm="${esc(p.name)}" title="Retirer">${icon("trash")}</button></div>`).join("")
      : `<div class="emptyp">${icon("pkg")}<br>${r.kind ? "Aucun paquet pour l'instant : ajoutez-en un ci-dessus." : esc(r.note)}</div>`;
  } catch (e) { list.innerHTML = `<div class="emptyp">${esc(e.message)}</div>`; }
}
async function pkgAdd() {
  const name = $("#pkgName").value.trim(); if (!name || !S.project) return;
  try { await api("/api/pkgs/install", { project: S.project, name }); $("#pkgName").value = ""; showTab("terminal", false, true); }
  catch (e) { toast(e.message, "error"); }
}
$("#btnPkgAdd").addEventListener("click", pkgAdd);
$("#pkgName").addEventListener("keydown", e => { if (e.key === "Enter") pkgAdd(); });
$("#btnPkgRefresh").addEventListener("click", pkgsLoad);
$("#pkgList").addEventListener("click", async e => {
  const b = e.target.closest("[data-rm]"); if (!b) return;
  if (!await confirmModal("Retirer ce paquet ?", `<b>${esc(b.dataset.rm)}</b> sera retiré du projet.`, "Retirer", true)) return;
  try { await api("/api/pkgs/remove", { project: S.project, name: b.dataset.rm }); showTab("terminal", false, true); } catch (err) { toast(err.message, "error"); }
});

/* ------------------------------------------------------------------ Académie : parcours, grades, défis (page dédiée) */
const PG = { data: null, view: ["path", "skills", "ach"].includes(prefs.pgView) ? prefs.pgView : "path", track: prefs.pgTrack || "dev", det: null, here: null, res: {}, pastes: 0, clip: "",
             timer: 0, busy: false, open: {}, loading: null };
const MEDAL_ICON = ["", "🥉", "🥈", "🥇"];
const WHY = { wrong: "mauvaise réponse", timeout: "trop lent", crash: "plantage", compile: "ne compile pas", constraint: "contrainte non respectée" };
/* les paliers ouverts, par filière et par langage */
const acOpenSet = (track, lang) => PG.open[`${track}/${lang}`] = PG.open[`${track}/${lang}`] || new Set();
/* le palier d'un défi, s'il appartient à la filière affichée */
const acStageOf = d => d && d.stage >= 0 && PG.data && PG.data.track === (d.track || "dev") ? PG.data.stages[d.stage] : null;
const CH_TITLES = {};
const fmtSecs = s => s >= 3600 ? `${Math.floor(s / 3600)} h ${String(Math.floor(s / 60) % 60).padStart(2, "0")}` : s >= 60 ? `${Math.floor(s / 60)} min ${String(s % 60).padStart(2, "0")}` : `${s} s`;
const nf = n => Number(n).toLocaleString("fr-FR");
const acIsOpen = () => $(".main").classList.contains("acad-open");

async function progLoad(lang, track) {
  const want = lang || prefs.pgLang || (S.info && S.info.lang) || "";
  const job = PG.loading = api("/api/prog?" + qs({ lang: want, track: track || PG.track }));
  try {
    const D = await job;
    if (job !== PG.loading) return;
    PG.data = D;
    PG.track = D.track; prefs.pgLang = D.lang; prefs.pgTrack = D.track; savePrefs();
    D.stages.forEach(st => st.items.forEach(i => { CH_TITLES[i.id] = i.title; }));
    D.custom.forEach(i => { CH_TITLES[i.id] = i.title; });
    const op = acOpenSet(D.track, D.lang); if (!op.size) op.add(Math.min(D.grade, D.stages.length - 1));
    progBadge();
    if (acIsOpen()) acRender();
  } catch (e) { if (acIsOpen()) $("#acBody").innerHTML = `<div class="emptyp">${esc(e.message)}</div>`; }
}
/* le grade du langage courant : barre d'état et bouton de la barre latérale */
function progBadge() {
  const D = PG.data; if (!D) return;
  const lang = S.info && D.langs.some(l => l.id === S.info.lang) ? S.info.lang : D.lang;
  const L = D.langs.find(l => l.id === lang); if (!L) return;
  const [n, i] = D.levels[L.grade];
  const b = $("#stGrade");
  b.hidden = false; b.textContent = `${i} ${n}`; b.title = `Votre grade ${D.track_name} en ${L.name} · ${nf(D.xp)} XP — ouvrir l'Académie (F9)`;
  $("#abIc").textContent = i;
  $("#abSub").textContent = `${n} · ${L.name}`;
  const pct = Math.round(L.done / Math.max(1, D.total) * 100), ring = $("#abRing");
  ring.style.setProperty("--p", pct); ring.dataset.v = L.grade; ring.title = `${L.done}/${D.total} défis en ${L.name}`;
}

/* ---- ouvrir / fermer la page */
function acOpen(view) {
  if (view) { PG.view = view; prefs.pgView = view; savePrefs(); }
  const main = $(".main");
  if (!acIsOpen()) {
    main.classList.add("acad-open"); $("#academy").hidden = false; $("#btnAcad").classList.add("on");
    $("#btnAcad").setAttribute("aria-pressed", "true");
  }
  if (PG.data) acRender(); else $("#acBody").innerHTML = `<div class="emptyp">Chargement du parcours…</div>`;
  progLoad(PG.data ? PG.data.lang : "");
  setTimeout(() => $("#acBack").focus(), 30);
}
function acClose() {
  if (!acIsOpen()) return;
  acDrawerClose();
  $(".main").classList.remove("acad-open"); $("#academy").hidden = true; $("#btnAcad").classList.remove("on");
  $("#btnAcad").setAttribute("aria-pressed", "false");
  if (S.file) setTimeout(() => ED.ta.focus(), 30);
}
function acToggle() { acIsOpen() ? acClose() : acOpen(); }

/* ---- rendu de la page */
function acRender() {
  const D = PG.data; if (!D) return;
  const mine = D.langs.filter(l => l.started || l.id === D.lang);
  $("#acLangs").innerHTML = mine.map(l => `<button class="ac-lt" role="tab" aria-selected="${l.id === D.lang}" data-lt="${esc(l.id)}" title="${esc(l.name)} : ${esc(D.levels[l.grade][0])} · ${l.done}/${D.total} défis · ${nf(l.xp)} XP">${D.levels[l.grade][1]} ${esc(l.name)} <small>${l.done}/${D.total}</small></button>`).join("");
  const rest = D.langs.filter(l => !mine.includes(l)).sort((a, b) => b.installed - a.installed || a.name.localeCompare(b.name));
  $("#acLang").innerHTML = `<option value="">＋ ${mine.length ? "Autre langage" : "Choisir un langage"}…</option>` + rest.map(l => `<option value="${esc(l.id)}">${esc(l.name)}${l.installed ? "" : " (non installé)"}</option>`).join("");
  $("#acLang").parentElement.hidden = !rest.length;
  $$("#acNav button").forEach(b => b.setAttribute("aria-selected", b.dataset.av === PG.view));
  $("#acSub").textContent = D.track_sub;
  $("#acTracks").innerHTML = D.tracks.map(t => `<button role="tab" data-tr="${esc(t.id)}" aria-selected="${t.id === D.track}" title="Filière ${esc(t.name)} en ${esc(langName(D.lang))} : ${esc(t.glyph + " " + t.level)}">${esc(t.icon)} ${esc(t.name)}</button>`).join("");
  $("#acXp").innerHTML = `${D.streak ? `<span title="Série de jours">🔥 ${D.streak} j</span>` : ""}<span title="XP au total, tous langages"><b>${nf(D.xp)}</b> XP</span>`;
  const body = $("#acBody"), top = body.scrollTop;
  body.innerHTML = `<div class="ac-wrap">${PG.view === "skills" ? acSkillsHtml(D) : PG.view === "ach" ? acAchHtml(D) : acPathHtml(D)}</div>`;
  body.scrollTop = top;
  const lad = $(".ac-ladder", body);
  if (lad) requestAnimationFrame(() => {
    const nodes = $$(".ac-stage", lad), cur = nodes[Math.min(D.grade, nodes.length - 1)];
    const h = lad.getBoundingClientRect().height, y = cur ? cur.getBoundingClientRect().top - lad.getBoundingClientRect().top + 30 : h;
    lad.style.setProperty("--fill", D.grade >= D.stages.length ? "calc(100% - 28px)" : `${Math.max(0, y - 14)}px`);
  });
}
function acItems(D) { return D.stages.flatMap(s => s.items).concat(D.custom); }
/* ce qu'il y a à faire maintenant dans ce langage */
function progNext(D) {
  const act = acItems(D).find(i => i.active);
  if (act) return { item: act, run: true };
  if (D.grade >= D.stages.length) return null;
  const st = D.stages[D.grade];
  const mini = st.items.find(i => i.kind === "mini" && !i.medal);
  return { item: mini || st.items.find(i => i.kind === "exam"), exam: !mini };
}
function acTile(it, lang, num, st) {
  const locked = it.status === "locked";
  const ic = locked ? "🔒" : it.medal ? MEDAL_ICON[it.medal] : it.active ? "⏳" : it.kind === "exam" ? "⚔️" : `<small style="font:700 11px var(--mono)">${num}</small>`;
  const sub = locked ? "verrouillé" : it.medal ? ["", "bronze", "argent", "or"][it.medal] + (it.review ? " · à réviser" : "") : it.lock ? `réessai dans ${Math.ceil(it.lock / 60)} min` : it.active ? "en cours" : it.tries ? `${it.tries} essai${it.tries > 1 ? "s" : ""}` : "à faire";
  const tg = it.kind === "exam" ? `examen · ${st ? st.icon + " " + esc(st.name) : ""}` : it.tag === "debug" ? "🐛 débogage" : "";
  return `<button class="ac-tile ${it.kind} ${it.status}${it.active ? " active" : ""}" style="--i:${num || 0}" data-ch="${esc(it.id)}" data-lang="${esc(lang)}" title="${esc(it.theme)}">
    <span class="s">${ic}</span>${tg ? `<span class="tg">${tg}</span>` : ""}<b>${it.kind === "exam" ? "Examen de promotion : " + esc(it.title.replace(/^Examen( final)? : /, "")) : esc(it.title)}</b>
    <small><span>${esc(it.theme)}</span><span>· ${esc(sub)}</span><span>· ${it.xp} XP</span></small></button>`;
}
function acPathHtml(D) {
  const L = D.langs.find(l => l.id === D.lang) || { name: langName(D.lang), done: 0, installed: true };
  const g = D.grade, n = D.stages.length, nx = progNext(D);
  const cur = D.stages[Math.min(g, n - 1)], cdone = cur.items.filter(i => i.medal).length;
  const p = g >= n ? 1 : cdone / Math.max(1, cur.items.length), C = 2 * Math.PI * 58;
  let next;
  const top = D.levels[D.levels.length - 1];
  if (!nx) next = `<small>Parcours terminé</small><b>${top[1]} ${esc(top[0])}</b><p>Vous avez tout conquis en ${esc(L.name)}. Visez l'or partout, ou attaquez un nouveau langage !</p>`;
  else {
    const it = nx.item;
    next = `<small>${nx.run ? "Défi en cours" : nx.exam ? "Prochaine étape : l'examen de promotion" : "Prochaine étape"}</small><b>${nx.run ? "⏳" : nx.exam ? "⚔️" : "▶"} ${esc(it.title)}</b>
      <p>${esc(it.theme)} · ${it.xp} XP${nx.exam && g < n ? ` · promotion : ${D.levels[g + 1][1]} ${esc(D.levels[g + 1][0])}` : ""}</p>
      <button class="btn primary" data-ch="${esc(it.id)}" data-lang="${esc(D.lang)}">${nx.run ? "Reprendre" : nx.exam ? "Voir l'examen" : "Commencer"}</button>`;
  }
  let h = `<section class="ac-hero">
    <div class="ac-badge" title="${cdone}/${cur.items.length} défis du palier en cours"><svg viewBox="0 0 132 132" aria-hidden="true"><circle class="bg-c" cx="66" cy="66" r="58"/><circle class="fg-c" cx="66" cy="66" r="58" stroke-dasharray="${C.toFixed(1)}" stroke-dashoffset="${(C * (1 - p)).toFixed(1)}"/></svg><span class="ic">${D.icon}</span></div>
    <div class="ac-who"><small>${D.track === "dev" ? "Votre poste" : "Votre grade de " + esc(D.track_name.toLowerCase())} en ${esc(L.name)}</small><h2>${esc(D.level)}</h2>
      <div class="ac-meta"><span>Échelon <b>${g}</b> / ${n}</span><span><b>${L.done}</b> / ${D.total} défis</span><span><b>${nf(D.lxp)}</b> XP</span>${D.stats.golds ? `<span>🥇 <b>${D.stats.golds}</b></span>` : ""}${D.streak ? `<span>🔥 <b>${D.streak}</b> jour${D.streak > 1 ? "s" : ""}</span>` : ""}</div>
      <div class="ac-steps" aria-hidden="true">${D.stages.map((s, i) => `<i class="${i < g ? "done" : i === g ? "cur" : ""}" title="${esc(D.levels[i + 1][0])}"></i>`).join("")}</div>
      ${L.installed ? "" : `<p class="ac-note">⚠️ ${esc(L.name)} n'est pas installé : installez-le depuis les extensions pour pouvoir soumettre.</p>`}
    </div>
    <div class="ac-next">${next}</div></section>`;
  const cards = [];
  if (D.daily) cards.push(`<button class="ac-card hl" data-ch="${esc(D.daily.id)}" data-lang="${esc(D.lang)}"><span class="e">☀️</span><small>Défi du jour · XP ×2</small><b>${esc(D.daily.title)}</b></button>`);
  if (D.suggestion) cards.push(`<button class="ac-card" data-ch="${esc(D.suggestion.id)}" data-lang="${esc(D.lang)}"><span class="e">🧭</span><small>À travailler : ${esc(D.suggestion.theme)}</small><b>${esc(D.suggestion.title)}</b></button>`);
  const rev = acItems(D).filter(i => i.review);
  if (rev.length) cards.push(`<button class="ac-card" data-ch="${esc(rev[0].id)}" data-lang="${esc(D.lang)}"><span class="e">🐘</span><small>À réviser · ${rev.length} défi${rev.length > 1 ? "s" : ""} · +30 % d'XP</small><b>${esc(rev[0].title)}</b></button>`);
  cards.push(`<button class="ac-card" data-av2="skills"><span class="e">📊</span><small>Radar, activité, statistiques</small><b>Mes compétences</b></button>`);
  h += `<div class="ac-cards">${cards.join("")}</div>`;
  h += `<div class="ac-h"><h3>Plan de carrière</h3><span>${D.stages.length} échelons · ${esc(D.track_sub.toLowerCase())} · réussissez l'examen d'un palier pour être promu</span></div><div class="ac-ladder">`;
  const open = acOpenSet(D.track, D.lang);
  const half = D.track === "math" ? D.stages.length / 2 : -1;
  for (const st of D.stages) {
    if (st.index === 0 && half > 0) h += `<div class="ac-part">Partie 1 · Algorithme</div>`;
    if (st.index === half) h += `<div class="ac-part">Partie 2 · Algorithme avancé</div>`;
    const state = g > st.index ? "done" : g === st.index ? "cur" : "locked";
    const nd = st.items.filter(i => i.medal).length, tot = st.items.length;
    const lab = state === "done" ? "✔ promu" : state === "cur" ? "en cours" : `🔒 ${D.levels[st.index][1]} requis`;
    const meds = st.items.map(i => i.medal ? MEDAL_ICON[i.medal] : "·").join("");
    let num = 0;
    h += `<section class="ac-stage ${state}${open.has(st.index) ? " open" : ""}" data-st="${st.index}">
      <span class="node" aria-hidden="true">${st.icon}</span>
      <button class="ac-sh" aria-expanded="${open.has(st.index)}" data-tog="${st.index}">
        <span class="t"><b>Palier ${st.index + 1} · ${esc(st.theme)}</b><span class="ac-dom">${esc(st.domain)}</span><span class="ac-st">${lab}</span></span>
        <span class="ac-prog"><i><em style="width:${Math.round(nd / tot * 100)}%"></em></i><small>${nd}/${tot}</small></span>
        <p>${esc(st.about)} → devenir <b>${st.icon} ${esc(st.name)}</b>${nd ? ` · <span class="ac-meds" aria-hidden="true">${meds}</span>` : ""}</p>
      </button>
      <div class="ac-tiles">${st.items.map(i => acTile(i, D.lang, i.kind === "exam" ? 0 : ++num, st)).join("")}</div></section>`;
  }
  h += `</div>`;
  if (D.track !== "dev") return h;
  h += `<div class="ac-h" style="margin-top:22px"><h3>🧩 Défis personnels</h3><span>vos propres défis en JSON, hors grades</span><span style="flex:1"></span><button class="btn sm" id="pgImport">${icon("plus")}Ajouter un défi…</button></div>`;
  h += D.custom.length ? `<div class="ac-tiles" style="padding:0">${D.custom.map((i, k) => acTile(i, D.lang, k + 1)).join("")}</div>` : `<p class="ac-note">Aucun pour l'instant : créez les vôtres pour vous entraîner sur vos propres sujets.</p>`;
  return h;
}
function acRadar(D) {
  const R = 100, cx = 160, cy = 140, pts = [], lab = [], DOMAINS = D.domains;
  const val = DOMAINS.map(dm => {
    const it = D.stages.filter(s => s.domain === dm).flatMap(s => s.items);
    return it.length ? it.filter(i => i.medal).length / it.length : 0;
  });
  const at = (i, r) => { const a = -Math.PI / 2 + i * Math.PI * 2 / DOMAINS.length; return [cx + Math.cos(a) * r, cy + Math.sin(a) * r]; };
  let grid = "";
  for (const f of [.25, .5, .75, 1]) grid += `<polygon class="grid" points="${DOMAINS.map((_, i) => at(i, R * f).join(",")).join(" ")}"/>`;
  DOMAINS.forEach((dm, i) => {
    const [x, y] = at(i, R), [lx, ly] = at(i, R + 22), v = Math.max(.03, val[i]), [px, py] = at(i, R * v);
    grid += `<line class="axe" x1="${cx}" y1="${cy}" x2="${x}" y2="${y}"/>`;
    pts.push(`${px.toFixed(1)},${py.toFixed(1)}`);
    lab.push(`<text x="${lx}" y="${ly}" text-anchor="middle" dominant-baseline="middle">${esc(dm)} ${Math.round(val[i] * 100)}%</text><circle class="pt" cx="${px}" cy="${py}" r="3.5"/>`);
  });
  return `<svg class="ac-radar" viewBox="0 0 320 280" role="img" aria-label="Radar des compétences : ${DOMAINS.map((d, i) => `${d} ${Math.round(val[i] * 100)} %`).join(", ")}">${grid}<polygon class="zone" points="${pts.join(" ")}"/>${lab.join("")}</svg>`;
}
function acHeat(D) {
  const day = 86400000, today = new Date(D.today + "T12:00:00"), start = new Date(today - 181 * day);
  start.setDate(start.getDate() - ((start.getDay() + 6) % 7));      // on commence un lundi
  let h = "", total = 0, actifs = 0;
  for (let t = +start; t <= +today; t += day) {
    const d = new Date(t), k = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`, n = D.heat[k] || 0;
    total += n; actifs += n > 0;
    h += `<i data-l="${n === 0 ? 0 : n < 2 ? 1 : n < 4 ? 2 : n < 7 ? 3 : 4}" class="${k === D.today ? "today" : ""}" title="${d.toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })} : ${n} défi${n > 1 ? "s" : ""} réussi${n > 1 ? "s" : ""}"></i>`;
  }
  return `<h3>Activité (6 mois) <span>${total} réussite${total > 1 ? "s" : ""} · ${actifs} jour${actifs > 1 ? "s" : ""} actif${actifs > 1 ? "s" : ""}</span></h3><div class="ac-heat">${h}</div>
    <div class="ac-legend">moins <i style="background:rgba(var(--fg),.07)"></i><i style="background:rgba(var(--accent-rgb),.3)"></i><i style="background:rgba(var(--accent-rgb),.55)"></i><i style="background:rgba(var(--accent-rgb),.8)"></i><i style="background:var(--accent)"></i> plus</div>`;
}
function acSkillsHtml(D) {
  const s = D.stats, rate = s.attempts ? Math.round(s.success / s.attempts * 100) : 0;
  const reasons = Object.entries(s.reasons).sort((a, b) => b[1] - a[1]);
  const weak = [...D.skills].filter(k => k.fails).sort((a, b) => b.fails - a.fails).slice(0, 6);
  return `<div class="ac-grid2">
    <div class="ac-panel"><h3>Radar des compétences <span>${esc(langName(D.lang))}</span></h3>${acRadar(D)}
      ${D.suggestion ? `<p class="ac-note" style="text-align:center">À travailler : <b>${esc(D.suggestion.theme)}</b> — <a href="#" data-ch="${esc(D.suggestion.id)}" data-lang="${esc(D.lang)}">${esc(D.suggestion.title)}</a></p>` : ""}</div>
    <div class="ac-panel"><h3>Statistiques</h3><div class="ac-stats">
      <div><b>${s.done}</b><small>défis réussis</small></div><div><b>${s.golds}</b><small>médailles d'or</small></div><div><b>${rate} %</b><small>de réussite</small></div>
      <div><b>${s.attempts}</b><small>soumissions</small></div><div><b>${s.avg_secs ? fmtSecs(s.avg_secs) : "—"}</b><small>temps moyen</small></div><div><b>${nf(D.lxp)}</b><small>XP ${esc(langName(D.lang))}</small></div></div>
      ${reasons.length ? `<p class="ac-note">Causes d'échec :</p>${reasons.map(([k, n]) => `<div class="ac-row"><span>${esc(WHY[k] || k)}</span><b>${n}</b></div>`).join("")}` : ""}</div></div>
    <div class="ac-panel" style="margin-bottom:14px">${acHeat(D)}</div>
    <div class="ac-grid2"><div class="ac-panel"><h3>Maîtrise par palier</h3>
      ${D.stages.map(st => { const d = st.items.filter(i => i.medal).length; return `<div class="ac-bar"><span title="${esc(st.name)}">${st.icon}</span><div><div style="font-size:12px;margin-bottom:3px">${esc(st.theme)}</div><i><em style="width:${Math.round(d / st.items.length * 100)}%"></em></i></div><small>${d}/${st.items.length}</small></div>`; }).join("")}</div>
    <div class="ac-panel"><h3>Points faibles et historique</h3>
      ${weak.length ? weak.map(k => `<div class="ac-row"><span>${esc(k.theme)}</span><small>${k.fails} échec${k.fails > 1 ? "s" : ""} · ${k.done}/${k.total} réussis</small></div>`).join("") : `<p class="ac-note">Aucun échec pour l'instant. Impressionnant.</p>`}
      ${D.recent.length ? `<p class="ac-note">Dernières soumissions :</p>${D.recent.map(r => `<div class="ac-row"><span>${r.ok ? "✔" : "✕"} ${esc(CH_TITLES[r.key.split("/")[1]] || r.key.split("/")[1])}</span><small>${r.ok ? "réussi" : esc(WHY[r.why] || "échec")} · ${new Date(r.t * 1000).toLocaleDateString("fr-FR")}</small></div>`).join("")}` : ""}</div></div>`;
}
function acAchHtml(D) {
  const got = D.achievements.filter(a => a.got).length;
  const ls = D.langs.filter(l => l.grade || l.started || l.installed).sort((a, b) => b.grade - a.grade || b.done - a.done);
  return `<div class="ac-h"><h3>${D.track === "dev" ? "Mes postes" : "Mes grades"}</h3><span>filière ${esc(D.track_name)} · un grade par langage</span></div>
    <div class="ac-grades" style="margin-bottom:22px">${ls.map(l => `<div class="ac-gcard"><span>${D.levels[l.grade][1]}</span><b>${esc(l.name)}</b><small>${esc(D.levels[l.grade][0])}</small><small>${l.done}/${D.total} défis · ${nf(l.xp)} XP</small>${l.grade ? `<button class="btn sm" data-cert="${esc(l.id)}">${icon("download")}Certificat</button>` : ""}</div>`).join("")}</div>
    <div class="ac-h"><h3>Succès</h3><span>${got} / ${D.achievements.length} débloqués</span></div>
    <div class="ac-ach">${D.achievements.map((a, i) => `<div class="${a.got ? "got" : ""}" style="--i:${i}" title="${esc(a.desc)}"><span>${a.got ? a.icon : "🔒"}</span><b>${esc(a.name)}</b><small>${esc(a.desc)}${a.got ? ` · ${new Date(a.got * 1000).toLocaleDateString("fr-FR")}` : ""}</small></div>`).join("")}</div>`;
}

/* ---- tiroir : le détail d'un défi, dans l'Académie */
async function acDrawerOpen(id, lang) {
  try {
    PG.det = await api("/api/prog/detail?" + qs({ lang, id }));
    acDrawerRender();
  } catch (e) { toast(e.message, "error"); }
}
function acDrawerClose() {
  const d = $("#acDrawer"); if (!d) return;
  d.remove(); $(".ac-scrim") && $(".ac-scrim").remove(); PG.det = null;
}
function progLimits(d) {
  const L = d.limits, exam = d.kind === "exam";
  return [`⏱ ${L.time} s par test`, L.minutes ? `⌛ ${L.minutes} min pour l'or` : "", L.max_lines ? `📏 ${L.max_lines} lignes max` : "",
    Object.values(L.banned || {}).flat().length ? "🚫 fonctions interdites" : "", exam ? "📋 copier-coller externe bloqué" : ""].filter(Boolean);
}
function acDrawerRender() {
  const d = PG.det; if (!d || !acIsOpen()) return;
  const D = PG.data, st = acStageOf(d), exam = d.kind === "exam";
  let el = $("#acDrawer");
  if (!el) {
    const sc = document.createElement("div"); sc.className = "ac-scrim"; sc.onclick = acDrawerClose; $("#academy").appendChild(sc);
    el = document.createElement("aside"); el.className = "ac-drawer"; el.id = "acDrawer"; el.setAttribute("role", "dialog"); el.setAttribute("aria-modal", "true");
    $("#academy").appendChild(el);
  }
  el.setAttribute("aria-label", `Défi ${d.title}`);
  const busyStart = d.status === "locked";
  const res = PG.res[`${d.lang}/${d.id}`];
  el.innerHTML = `<header class="ac-dh"><span class="big" aria-hidden="true">${exam ? "⚔️" : d.tag === "debug" ? "🐛" : d.medal ? MEDAL_ICON[d.medal] : "🎯"}</span>
      <div><small>${esc(langName(d.lang))} › ${st ? `Palier ${d.stage + 1} · ${esc(st.theme)}` : "défi personnel"}</small><h2>${esc(d.title)}</h2>
      <small>${exam && st ? `Examen de promotion : réussir fait de vous un ${st.icon} ${esc(st.name)}` : esc(d.theme)}</small></div>
      <button class="btn icon sm x" id="acDx" title="Fermer (Échap)" aria-label="Fermer">${icon("x")}</button></header>
    <div class="ac-db">
      <div class="ac-chips"><span class="k">${exam ? "⚔️ Examen" : "Mini-défi"}</span><span>${d.xp} XP</span>${d.tag === "debug" ? `<span class="dbg">🐛 code bogué fourni</span>` : ""}${progLimits(d).map(x => `<span>${esc(x)}</span>`).join("")}${d.medal ? `<span>${MEDAL_ICON[d.medal]} meilleure médaille</span>` : ""}</div>
      <p class="ac-desc">${esc(d.desc)}</p>
      ${d.examples.map((t, i) => `<div class="ac-ex"><div><small>Exemple ${i + 1} · entrée</small><pre>${esc(t.in) || "<i>(vide)</i>"}</pre></div><div><small>Sortie attendue</small><pre>${esc(t.out) || "<i>(rien)</i>"}</pre></div></div>`).join("")}
      <p class="ac-note">${d.ntests - d.examples.length} test${d.ntests - d.examples.length > 1 ? "s" : ""} caché${d.ntests - d.examples.length > 1 ? "s" : ""} en plus des exemples · ${d.tries} tentative${d.tries > 1 ? "s" : ""} · solutions de référence en ${d.sol_langs.map(langName).join(", ")}</p>
      <div class="ac-acts">${busyStart ? `<span class="ac-note">🔒 Se débloque ${st ? `en devenant ${esc(D.levels[d.stage][1] + " " + D.levels[d.stage][0])}` : "plus loin dans le parcours"}.</span>`
        : `<button class="btn primary" id="acGo">${icon("play")}${d.tries || d.medal || d.active ? "Ouvrir mon projet" : exam ? "Passer l'examen" : "Relever le défi"}</button>
           <button class="btn" data-hint ${d.hints.length >= d.nhints ? "disabled" : ""} title="Chaque indice fait perdre la médaille d'or">💡 Indice ${d.hints.length}/${d.nhints}</button>
           ${d.has_solution ? `<button class="btn" data-sol ${!d.sol_free && d.tries < 3 ? "disabled" : ""} title="${d.sol_free ? "Comparer avec les solutions de référence" : "Disponible après 3 tentatives"}">📖 Solutions${d.sol_free ? "" : d.tries < 3 ? ` (${d.tries}/3)` : ""}</button>` : ""}
           ${d.active ? `<button class="btn ghost danger" data-quit="${esc(d.id)}">⏹ Abandonner</button>` : ""}
           ${d.id.startsWith("perso-") ? `<button class="btn ghost danger" id="pgDel">Supprimer</button>` : ""}`}</div>
      ${d.hints.length ? `<ol class="ac-hints">${d.hints.map(x => `<li>${esc(x)}</li>`).join("")}</ol>` : ""}
      ${res ? progResHtml(res) + progNextHtml(d, res) : ""}
    </div>`;
  $("#acDx", el).onclick = acDrawerClose;
  const go = $("#acGo", el); if (go) go.onclick = () => progStart(d);
  setTimeout(() => (go || $("#acDx", el)).focus(), 30);
}

/* ---- panneau « Défi » dans l'inspecteur (projet de défi ouvert) */
function dfShow(on) {
  const t = $("#itDefi");
  t.hidden = !on;
  if (!on && prefs.insp === "defi") showInsp("proj");
}
async function progProject(ch) {
  if (!ch || !ch.lang || !ch.id) { PG.here = null; clearInterval(PG.timer); dfShow(false); $("#dfPane").innerHTML = ""; return; }
  try {
    const d = await api("/api/prog/detail?" + qs({ lang: ch.lang, id: ch.id }));
    if (!(S.conf && S.conf.challenge && S.conf.challenge.id === ch.id)) return;
    if (!PG.here || PG.here.id !== d.id || PG.here.lang !== d.lang) PG.pastes = 0;
    PG.here = d;
    dfShow(true); dfRender(); openInsp("defi");
  } catch (e) { toast(e.message, "error"); }
}
function dfRender() {
  const d = PG.here, box = $("#dfPane"); if (!d) return;
  const st = acStageOf(d), exam = d.kind === "exam", res = PG.res[`${d.lang}/${d.id}`];
  box.innerHTML = `<div class="df-head"><span class="df-tim" id="dfTim"></span>
      <small>${exam ? "⚔️ Examen de promotion" : d.tag === "debug" ? "🐛 Débogage" : "🎯 Mini-défi"}${st ? ` · palier ${d.stage + 1}` : ""}</small>
      <b>${esc(d.title)}</b>
      <div class="ac-chips" style="margin:0"><span>${d.xp} XP</span>${d.medal ? `<span>${MEDAL_ICON[d.medal]}</span>` : ""}${progLimits(d).map(x => `<span>${esc(x)}</span>`).join("")}</div></div>
    <div class="card glass"><p class="df-desc">${esc(d.desc)}</p>
      <details class="df-ex" ${d.examples.length && !res ? "open" : ""}><summary>Exemples (${d.examples.length}) · ${d.ntests - d.examples.length} tests cachés</summary>
        ${d.examples.map(t => `<div class="p"><div><small>entrée</small><pre>${esc(t.in) || "<i>(vide)</i>"}</pre></div><div><small>attendu</small><pre>${esc(t.out) || "<i>(rien)</i>"}</pre></div></div>`).join("")}</details></div>
    <button class="btn primary df-go" id="dfGo" ${d.lock || PG.busy ? "disabled" : ""} title="Enregistrer et lancer tous les tests (F6)">${icon("check")}${PG.busy ? "Correction…" : d.lock ? `Réessai dans ${Math.ceil(d.lock / 60)} min` : "Soumettre"} <span class="kbd">F6</span></button>
    <div class="df-row"><button class="btn sm" data-hint ${d.hints.length >= d.nhints ? "disabled" : ""}>💡 ${d.hints.length}/${d.nhints}</button>
      ${d.has_solution ? `<button class="btn sm" data-sol ${!d.sol_free && d.tries < 3 ? "disabled" : ""} title="${d.sol_free ? "Solutions de référence" : "Après 3 tentatives"}">📖 Solutions</button>` : ""}
      ${!d.medal ? `<button class="btn sm ghost danger" data-quit="${esc(d.id)}" title="Abandonner ce défi">⏹</button>` : ""}</div>
    ${d.hints.length ? `<ol class="ac-hints">${d.hints.map(x => `<li>${esc(x)}</li>`).join("")}</ol>` : ""}
    <div id="dfRes">${PG.busy ? `<div class="df-running"><i></i>Compilation et tests en cours…</div>` : res ? progResHtml(res) + progNextHtml(d, res) : ""}</div>
    <button class="btn sm ghost" id="dfAcad" style="justify-content:center">🎓 Voir dans l'Académie</button>`;
  clearInterval(PG.timer);
  const tick = () => {
    const el = $("#dfTim"); if (!el || !d.started || d.medal) { if (el) el.textContent = d.medal ? MEDAL_ICON[d.medal] : ""; return; }
    const s = Math.round(Date.now() / 1000 - d.started), m = d.limits.minutes * 60;
    el.textContent = m ? (s <= m ? `⌛ ${fmtSecs(m - s)}` : `⌛ +${fmtSecs(s - m)}`) : `⏱ ${fmtSecs(s)}`;
    el.classList.toggle("over", !!m && s > m);
  };
  tick(); PG.timer = setInterval(tick, 1000);
}
function progNext(d) {
  const D = PG.data; if (!D || D.lang !== d.lang || D.track !== (d.track || "dev")) return null;
  const all = D.stages.flatMap(s => s.items), i = all.findIndex(x => x.id === d.id);
  if (i < 0) return null;
  const after = all.slice(i + 1).filter(x => x.status !== "locked");
  return after.find(x => !x.medal) || after[0] || null;
}
function progNextHtml(d, r) {
  const n = r && r.ok && progNext(d);
  return n ? `<button class="btn primary df-next" data-next="${esc(n.id)}" title="Ouvrir le défi suivant">${n.kind === "exam" ? "⚔️ " : ""}Suivant : ${esc(n.title)} →</button>` : "";
}
async function progGoNext(id) {
  const D = PG.data, n = D && D.stages.flatMap(s => s.items).find(x => x.id === id);
  if (n) return progStart({ lang: D.lang, id: n.id, kind: n.kind, track: D.track });
}
function progResHtml(r) {
  if (r.why === "compile" || r.why === "constraint") return `<div class="df-res ko"><b>✕ ${esc(r.message)}</b>${r.output ? `<div class="df-diff"><pre class="err">${esc(r.output)}</pre></div>` : ""}</div>`;
  let h = `<div class="df-res ${r.ok ? "ok" : "ko"}"><b>${r.ok ? `✔ Réussi ! ${r.passed}/${r.total} tests ${MEDAL_ICON[r.medal] || ""}${r.gained ? ` · +${r.gained} XP` : ""}${r.daily ? " · défi du jour ×2" : ""}` : `✕ ${r.passed}/${r.total} tests réussis`}</b>
    <div class="df-dots">${r.results.map((t, i) => `<span class="${t.status}" style="--i:${i}" title="Test ${i + 1}${t.hidden ? " (caché)" : ""} : ${esc(t.status === "ok" ? "réussi" : WHY[t.status])} · ${t.secs} s">${t.status === "ok" ? "✔" : "✕"}</span>`).join("")}</div>`;
  const f = r.results.find(t => t.status !== "ok");
  if (f) h += f.hidden ? `<p>Un test caché échoue (${esc(WHY[f.status])}). Pensez aux cas limites : 0, négatifs, très grands nombres, entrée vide, performances…</p>${f.stderr ? `<div class="df-diff"><pre class="err">${esc(f.stderr)}</pre></div>` : ""}`
    : `<div class="df-diff"><div><small>entrée</small><pre>${esc(f.input) || "<i>(vide)</i>"}</pre></div><div><small>attendu</small><pre>${esc(f.expected) || "<i>(rien)</i>"}</pre></div><div><small>obtenu (${esc(WHY[f.status])})</small><pre>${esc(f.got) || "<i>(rien)</i>"}</pre></div>${f.stderr ? `<pre class="err">${esc(f.stderr)}</pre>` : ""}</div>`;
  if (r.lock) h += `<p>Examen raté : nouvel essai possible dans ${Math.ceil(r.lock / 60)} min. Relisez l'énoncé et testez vos cas limites en attendant.</p>`;
  return h + `</div>`;
}

/* ---- actions */
async function progStart(d) {
  try {
    const r = await api("/api/prog/start", { lang: d.lang, id: d.id });
    acClose();
    await loadProjects(); await openProject(r.project);
    progLoad(d.lang, d.track);
    toast(d.kind === "exam" ? "Examen lancé : le chrono tourne. Bonne chance !" : "À vous ! Soumettez avec F6 quand c'est prêt.", "info");
  } catch (e) { toast(e.message, "error"); }
}
async function progSubmit() {
  const d = PG.here;
  if (!d || PG.busy) return;
  if (!(S.conf && S.conf.challenge && S.conf.challenge.id === d.id)) return;
  if (d.lock) return toast(`Examen raté récemment : réessai dans ${Math.ceil(d.lock / 60)} min.`, "warn");
  PG.busy = true; dfRender(); openInsp("defi");
  try {
    await saveAll();
    const r = await api("/api/prog/submit", { lang: d.lang, id: d.id, project: S.project, pastes: PG.pastes });
    PG.res[`${d.lang}/${d.id}`] = r;
    PG.here = await api("/api/prog/detail?" + qs({ lang: d.lang, id: d.id }));
    if (r.ok) {
      celebrate($("#dfGo") || $("#dfPane"));
      toast(`Défi réussi ${MEDAL_ICON[r.medal]} ${r.gained ? `+${r.gained} XP` : ""}`, "ok", 5000);
    } else toast(`${r.passed != null ? `${r.passed}/${r.total} tests` : "Échec"} — ${WHY[r.why] || "à revoir"}`, "warn", 4000);
    (r.achievements || []).forEach((a, i) => setTimeout(() => toast(`${a.icon} Succès débloqué : ${a.name}`, "ok", 5000), 700 * (i + 1)));
    await progLoad(d.lang, d.track);
    if (r.grade_up) progPromo(r.grade_up);
  } catch (e) { toast(e.message, "error", 6000); }
  PG.busy = false; dfRender();
  const rs = $("#dfRes"); if (rs && rs.firstElementChild) rs.scrollIntoView({ block: "nearest", behavior: "smooth" });
}
/* arrêter un défi en cours */
async function progQuit(lang, id) {
  const title = CH_TITLES[id] || (PG.here && PG.here.title) || id, proj = `Defi-${lang}-${id}`;
  const ok = await new Promise(res => modal(`<div class="modal glass"><h2>Abandonner « ${esc(title)} » ?</h2>
    <p class="sub">Le défi est arrêté et le chrono remis à zéro. Vous pourrez le relever de nouveau quand vous voulez ; vos essais et médailles déjà obtenus sont conservés.</p>
    <label class="chk" style="display:flex;gap:8px;align-items:center;margin:4px 0 8px"><input type="checkbox" id="pgReset"> Effacer aussi mon code (repartir d'une page blanche)</label>
    <div class="mactions"><button class="btn" data-x>Continuer le défi</button><button class="btn primary danger" data-ok>⏹ Abandonner</button></div></div>`, (ov, close) => {
      $("[data-x]", ov).onclick = () => { close(); res(null); };
      $("[data-ok]", ov).onclick = () => { const r = $("#pgReset", ov).checked; close(); res({ reset: r }); };
    }));
  if (!ok) return;
  try {
    const here = S.project === proj;
    if (here) { if (S.session.running) await api("/api/stop", {}).catch(() => {}); if (!ok.reset && anyDirty()) await saveAll(); }
    if (here && ok.reset) S.docs = {};
    await api("/api/prog/abandon", { lang, id, reset: ok.reset });
    delete PG.res[`${lang}/${id}`]; PG.pastes = 0;
    await loadProjects();
    if (here) {
      const back = S.projects.filter(p => !p.name.startsWith("Defi-")).sort((a, b) => (S.meta.opened[b.name] || 0) - (S.meta.opened[a.name] || 0))[0];
      if (back) await openProject(back.name);
      else { S.project = null; S.docs = {}; S.tabs = []; S.file = null; ED.set(""); renderTabs(); renderProjects(); renderTree(); $("#projName").textContent = ""; $("#welcome").classList.add("show"); progProject(null); }
    }
    await progLoad(lang);
    if (PG.det && PG.det.id === id) acDrawerOpen(id, lang);
    toast(ok.reset ? "Défi abandonné, code effacé." : "Défi abandonné. Votre code est gardé pour plus tard.", "info");
  } catch (e) { toast(e.message, "error"); }
}
async function progHint(d) {
  if (!d.hints.length && !await confirmModal("Prendre un indice ?", "Avec un indice, ce défi ne peut plus rapporter la médaille d'or et rapporte un peu moins d'XP.", "Voir l'indice")) return;
  try {
    const r = await api("/api/prog/hint", { lang: d.lang, id: d.id });
    for (const x of [PG.here, PG.det]) if (x && x.id === d.id && x.lang === d.lang) x.hints = r.hints;
    if (PG.here) dfRender();
    acDrawerRender();
  } catch (e) { toast(e.message, "error"); }
}
async function progSolution(d) {
  if (!d.sol_free && !await confirmModal("Voir les solutions ?", "Le défi n'est pas encore réussi : les consulter limite ce défi à la médaille de bronze et divise son XP par deux.", "Voir les solutions", true)) return;
  try {
    const r = await api("/api/prog/solution", { lang: d.lang, id: d.id });
    const langs = Object.keys(r.all).sort((a, b) => (b === d.lang) - (a === d.lang) || a.localeCompare(b));
    let cur = r.lang;
    modal(`<div class="modal wide glass"><h2>Solutions de référence — ${esc(d.title)}</h2><p class="sub">Il existe souvent d'autres bonnes façons de faire : comparez les idées, pas seulement la syntaxe.</p>
      <div class="sol-tabs" role="tablist">${langs.map(l => `<button role="tab" data-l="${esc(l)}" aria-selected="${l === cur}">${esc(langName(l))}</button>`).join("")}</div>
      <pre class="pg-sol" id="solCode"></pre><div class="mactions"><button class="btn" data-copy>${icon("save")}Copier</button><button class="btn primary" data-x>Fermer</button></div></div>`, (ov, close) => {
      const show = l => { cur = l; $("#solCode", ov).innerHTML = highlight(r.all[l], l); $$(".sol-tabs button", ov).forEach(b => b.setAttribute("aria-selected", b.dataset.l === l)); };
      show(cur);
      $(".sol-tabs", ov).onclick = e => { const b = e.target.closest("[data-l]"); if (b) show(b.dataset.l); };
      $("[data-copy]", ov).onclick = () => { navigator.clipboard && navigator.clipboard.writeText(r.all[cur]).then(() => toast("Solution copiée", "ok", 1600)); };
      $("[data-x]", ov).onclick = close;
    });
    d.sol_seen = true;
  } catch (e) { toast(e.message, "error"); }
}
/* promotion : la cinématique */
function progPromo(g) {
  const D = PG.data, nextSt = D && D.stages[g.grade], rnd = (a, b) => a + Math.random() * (b - a);
  const cols = ["var(--accent)", "var(--accent2)", "var(--accent3)", "var(--ok)", "var(--warn)", "#fff"];
  const conf = reducedMotion() ? "" : Array.from({ length: 110 }, (_, i) => `<i class="conf" style="left:${rnd(0, 100).toFixed(1)}%;background:${cols[i % 6]};--x:${rnd(-160, 160).toFixed(0)}px;--r:${rnd(-720, 720).toFixed(0)}deg;--d:${rnd(2.6, 5).toFixed(2)}s;--dl:${rnd(0, 1.2).toFixed(2)}s"></i>`).join("");
  const el = document.createElement("div");
  el.className = "promo"; el.setAttribute("role", "dialog"); el.setAttribute("aria-modal", "true"); el.setAttribute("aria-label", `Promotion : ${g.name}`);
  el.innerHTML = `<div class="rays" aria-hidden="true"></div>${conf}<div class="box"><div class="lvl">Promotion · ${esc(langName(g.lang))}</div><div class="ic">${g.icon}</div>
    <h2>${esc(g.name)}</h2><p>Examen réussi : vous êtes désormais <b>${esc(g.name)}</b> en ${esc(langName(g.lang))}.${nextSt ? `<br>Nouveau palier débloqué : <b>${esc(nextSt.theme)}</b> — ${nextSt.items.length} défis vous attendent.` : "<br>Vous avez atteint le sommet du parcours. Respect."}</p>
    <div class="acts"><button class="btn" data-cert>${icon("download")}Certificat</button><button class="btn primary" data-go>${nextSt ? "Voir le nouveau palier" : "Continuer"}</button></div></div>`;
  const prev = document.activeElement;
  const close = () => { el.remove(); removeEventListener("keydown", key, true); prev && prev.focus && prev.focus(); };
  const key = e => { if (e.key === "Escape") { e.stopPropagation(); close(); } };
  addEventListener("keydown", key, true);
  document.body.appendChild(el);
  $("[data-cert]", el).onclick = () => { close(); progCert(g.lang); };
  $("[data-go]", el).onclick = () => { close(); if (nextSt) { acOpenSet(g.track || "dev", g.lang).add(g.grade); acOpen("path"); } };
  setTimeout(() => $("[data-go]", el).focus(), 60);
}
/* certificat (image PNG) */
function progCert(lang) {
  const D = PG.data, L = D && D.langs.find(l => l.id === lang); if (!L || !L.grade) return;
  modal(`<div class="modal glass"><h2>Certificat de grade</h2><div class="field"><label for="ctName">Nom à inscrire</label><input id="ctName" value="${esc(prefs.certName || "")}" placeholder="Votre nom" maxlength="60" autocomplete="off"></div>
    <div class="mactions"><button class="btn" data-x>Annuler</button><button class="btn primary" data-ok>${icon("download")}Télécharger (PNG)</button></div></div>`, (ov, close) => {
    const go = () => {
      const name = $("#ctName", ov).value.trim() || "Élève de la forge"; prefs.certName = name; savePrefs(); close();
      const [gn, gi] = D.levels[L.grade], W = 1600, H = 1100, cv = document.createElement("canvas"); cv.width = W; cv.height = H;
      const c = cv.getContext("2d"), cs = getComputedStyle(document.documentElement), acc = cs.getPropertyValue("--accent").trim() || "#2a9d8f";
      c.fillStyle = "#fbf8f1"; c.fillRect(0, 0, W, H);
      c.strokeStyle = acc; c.lineWidth = 14; c.strokeRect(40, 40, W - 80, H - 80); c.lineWidth = 3; c.strokeRect(70, 70, W - 140, H - 140);
      c.textAlign = "center"; c.fillStyle = "#222";
      c.font = "600 34px Georgia, serif"; c.fillText(`FORGE CODE · ACADÉMIE · FILIÈRE ${D.track_name.toUpperCase()}`, W / 2, 190);
      c.font = "150px serif"; c.fillText(gi, W / 2, 380);
      c.font = "italic 36px Georgia, serif"; c.fillStyle = "#555"; c.fillText("est décerné à", W / 2, 470);
      c.font = "bold 76px Georgia, serif"; c.fillStyle = "#111"; c.fillText(name, W / 2, 570);
      c.font = "36px Georgia, serif"; c.fillStyle = "#333"; c.fillText(`pour avoir atteint le grade de`, W / 2, 660);
      c.font = "bold 64px Georgia, serif"; c.fillStyle = acc; c.fillText(`${gn} en ${L.name}`, W / 2, 750);
      c.font = "28px Georgia, serif"; c.fillStyle = "#666";
      c.fillText(`Échelon ${L.grade} sur ${D.stages.length} · ${L.done} défis validés par tests automatiques · ${new Date().toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })}`, W / 2, 880);
      const a = document.createElement("a"); a.href = cv.toDataURL("image/png"); a.download = `certificat-${D.track}-${lang}-${gn.replace(/\s+/g, "-").toLowerCase()}.png`; a.click();
    };
    $("[data-ok]", ov).onclick = go; $("[data-x]", ov).onclick = close; $("#ctName", ov).onkeydown = e => { if (e.key === "Enter") go(); }; $("#ctName", ov).focus();
  });
}
/* défi personnel (JSON) */
function progImport() {
  const ex = JSON.stringify({ id: "mon-defi", title: "Double", theme: "entrées/sorties", desc: "Lisez un entier et affichez son double.", langs: [], xp: 30,
    tests: [{ in: "4", out: "8" }, { in: "-3", out: "-6" }, { in: "0", out: "0", hidden: true }], hints: ["Multipliez par 2."], limits: { time: 2, minutes: 0, max_lines: 0 },
    solutions: { python: "print(int(input()) * 2)\n" } }, null, 2);
  modal(`<div class="modal wide glass"><h2>Ajouter un défi personnel</h2><p class="sub">Décrivez le défi en JSON : chaque test envoie « in » au programme et attend « out » (espaces de fin ignorés). « hidden » cache un test ; « langs » vide = tous les langages. Enregistré dans ~/.config/forge-code/challenges/.</p>
    <textarea class="json" id="pgJson" spellcheck="false" aria-label="Description JSON du défi">${esc(ex)}</textarea><div class="hint" id="pgJErr" role="alert"></div>
    <div class="mactions"><button class="btn" data-x>Annuler</button><button class="btn primary" data-ok>Ajouter</button></div></div>`, (ov, close) => {
    $("[data-x]", ov).onclick = close;
    $("[data-ok]", ov).onclick = async () => {
      try { const data = JSON.parse($("#pgJson", ov).value); const r = await api("/api/prog/custom", { data }); close(); toast("Défi ajouté 🧩", "ok"); await progLoad(PG.data && PG.data.lang); acDrawerOpen(r.id, PG.data.lang); }
      catch (e) { $("#pgJErr", ov).textContent = e.message; }
    };
  });
}

/* ---- événements */
$("#btnAcad").addEventListener("click", acToggle);
$("#wAcad").addEventListener("click", () => acOpen("path"));
$("#acBack").addEventListener("click", acClose);
$("#stGrade").addEventListener("click", () => acOpen());
$("#acLang").addEventListener("change", e => { if (e.target.value) { acDrawerClose(); progLoad(e.target.value); } });
$("#acLangs").addEventListener("click", e => { const b = e.target.closest("[data-lt]"); if (b) { acDrawerClose(); progLoad(b.dataset.lt); } });
$("#acTracks").addEventListener("click", e => { const b = e.target.closest("[data-tr]"); if (b && PG.data && b.dataset.tr !== PG.data.track) { acDrawerClose(); $("#acBody").scrollTop = 0; progLoad(PG.data.lang, b.dataset.tr); } });
$("#acNav").addEventListener("click", e => { const b = e.target.closest("[data-av]"); if (b) { PG.view = b.dataset.av; prefs.pgView = PG.view; savePrefs(); acRender(); $("#acBody").scrollTop = 0; } });
$("#academy").addEventListener("click", async e => {
  const ch = e.target.closest("[data-ch]");
  if (ch) { e.preventDefault(); return acDrawerOpen(ch.dataset.ch, ch.dataset.lang); }
  const t = e.target.closest("button,[data-av2]"); if (!t) return;
  if (t.dataset.tog !== undefined) {
    const D = PG.data, set = acOpenSet(D.track, D.lang), i = +t.dataset.tog;
    set.has(i) ? set.delete(i) : set.add(i);
    const sec = t.closest(".ac-stage"); sec.classList.toggle("open", set.has(i)); t.setAttribute("aria-expanded", set.has(i));
    return;
  }
  if (t.dataset.av2) { PG.view = t.dataset.av2; prefs.pgView = PG.view; savePrefs(); acRender(); $("#acBody").scrollTop = 0; return; }
  if (t.dataset.cert) return progCert(t.dataset.cert);
  if (t.dataset.next) return progGoNext(t.dataset.next);
  if (t.dataset.quit) return progQuit(PG.det ? PG.det.lang : PG.data.lang, t.dataset.quit);
  if (t.hasAttribute("data-hint") && PG.det) return progHint(PG.det);
  if (t.hasAttribute("data-sol") && PG.det) return progSolution(PG.det);
  if (t.id === "pgImport") return progImport();
  if (t.id === "pgDel" && PG.det && await confirmModal("Supprimer ce défi personnel ?", "Le fichier JSON du défi sera supprimé (vos projets restent).", "Supprimer", true)) {
    try { await api("/api/prog/custom/delete", { id: PG.det.id }); acDrawerClose(); progLoad(PG.data.lang); } catch (err) { toast(err.message, "error"); }
  }
});
$("#dfPane").addEventListener("click", e => {
  const t = e.target.closest("button"); if (!t || !PG.here) return;
  if (t.id === "dfGo") return progSubmit();
  if (t.id === "dfAcad") { acOpen("path"); return acDrawerOpen(PG.here.id, PG.here.lang); }
  if (t.dataset.next) return progGoNext(t.dataset.next);
  if (t.dataset.quit) return progQuit(PG.here.lang, t.dataset.quit);
  if (t.hasAttribute("data-hint")) return progHint(PG.here);
  if (t.hasAttribute("data-sol")) return progSolution(PG.here);
});
addEventListener("keydown", e => {
  if ($(".overlay") || $(".promo")) return;
  if (e.key === "F9") { e.preventDefault(); acToggle(); return; }
  if (e.key === "F6" && !e.ctrlKey && !e.altKey && !e.metaKey) { e.preventDefault(); if (PG.here) progSubmit(); else toast("Ouvrez un défi depuis l'Académie (F9) pour le soumettre.", "info"); return; }
  if (e.key === "Escape" && acIsOpen()) { e.preventDefault(); $("#acDrawer") ? acDrawerClose() : acClose(); }
}, true);
/* examen : le copier-coller venant d'ailleurs est bloqué (ce qui a été copié dans l'éditeur reste permis) */
["copy", "cut"].forEach(ev => ED.ta.addEventListener(ev, () => { PG.clip = ED.ta.value.slice(ED.ta.selectionStart, ED.ta.selectionEnd); }));
ED.ta.addEventListener("paste", e => {
  const d = PG.here, c = S.conf && S.conf.challenge;
  if (!d || !c || c.id !== d.id || d.kind !== "exam" || d.medal) return;
  const t = (e.clipboardData && e.clipboardData.getData("text")) || "";
  if (t.length > 20 && t.trim() !== PG.clip.trim()) { e.preventDefault(); PG.pastes++; toast("Examen : le copier-coller depuis l'extérieur est bloqué. Écrivez votre propre code 💪", "warn", 4000); }
});

/* ------------------------------------------------------------------ exemples (modèles de chaque langage) */
const TPL_INFO = { hello: ["👋", "Bonjour", "Question, réponse, boucle"], plot: ["📈", "Traceur", "Courbes en direct (nom:valeur)"], guess: ["🎯", "Devine le nombre", "Jeu interactif dans le terminal"], empty: ["✨", "Vide", "Page blanche"] };
function exRender() {
  const q = $("#exQ").value.trim().toLowerCase(), all = $("#exAll").checked;
  const langs = S.exts.filter(x => x.kind === "lang" && x.enabled && (all || x.installed));
  let n = 0, h = "";
  for (const x of langs) {
    const tp = (x.templates || []).filter(t => { const i = TPL_INFO[t] || ["", t, ""]; return !q || `${x.name} ${i[1]} ${i[2]} ${t}`.toLowerCase().includes(q); });
    if (!tp.length) continue;
    h += `<div class="ex-h"><span class="lchip" style="${langStyle(x)}">${esc(x.abbr)}</span><b>${esc(x.name)}</b>${x.installed ? "" : `<span class="tag miss">non installé</span>`}</div>`;
    h += tp.map(t => { n++; const i = TPL_INFO[t] || ["📄", t, ""]; return `<div class="lib"><b>${i[0]} ${esc(i[1])}</b><p>${esc(i[2])}</p><div class="meta"><span class="spacer"></span><button class="btn sm" data-l="${esc(x.id)}" data-t="${esc(t)}">${icon("plus")}Créer le projet</button></div></div>`; }).join("");
  }
  $("#exInfo").textContent = n ? `${n} exemple(s)` : "";
  $("#exList").innerHTML = h || `<div class="emptyp">${icon("code")}<br>${all ? "Aucun exemple ne correspond." : "Aucun langage installé ne correspond : cochez « Langages non installés aussi » ou installez-en un (Extensions)."}</div>`;
}
$("#exQ").addEventListener("input", exRender);
$("#exAll").addEventListener("change", exRender);
$("#exList").addEventListener("click", e => { const b = e.target.closest("[data-t]"); if (b) newProject(b.dataset.l, b.dataset.t); });

/* ------------------------------------------------------------------ diagnostic */
let docLoaded = false;
async function runDoctor() {
  docLoaded = true;
  $("#docList").innerHTML = `<div class="emptyp">Analyse en cours…</div>`;
  try {
    const checks = await api("/api/doctor");
    const bad = checks.filter(c => c.status !== "ok").length;
    badge("bDoctor", checks.filter(c => c.status === "fail").length);
    $("#docList").innerHTML = checks.map(c => `<div class="check ${c.status}"><div class="ic">${icon(c.status === "ok" ? "check" : c.status === "warn" ? "alert" : "x")}</div>
      <div style="min-width:0"><b>${esc(c.title)}</b><p>${esc(c.detail)}</p>${c.fix ? `<code title="Copier">${esc(c.fix)}</code>` : ""}</div></div>`).join("");
    if (!bad) toast("Diagnostic : tout est en ordre", "ok");
  } catch (e) { $("#docList").innerHTML = `<div class="emptyp">${esc(e.message)}</div>`; }
}
$("#btnDoctor").addEventListener("click", runDoctor);
$("#docList").addEventListener("click", e => {
  const c = e.target.closest("code"); if (!c) return;
  navigator.clipboard?.writeText(c.textContent).then(() => toast("Commande copiée", "ok", 1500), () => {});
});

/* ------------------------------------------------------------------ modales */
let modalN = 0;
function modal(html, onMount, onClose) {
  const ov = document.createElement("div");
  ov.className = "overlay";
  ov.innerHTML = html;
  const prevFocus = document.activeElement;
  document.body.appendChild(ov);
  const box = ov.firstElementChild;
  if (box) {
    if (!box.hasAttribute("role")) box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    const h = box.querySelector("h2");
    if (h && !box.hasAttribute("aria-labelledby")) { h.id = h.id || "mdT" + (++modalN); box.setAttribute("aria-labelledby", h.id); }
    if (!h && !box.hasAttribute("aria-label")) box.setAttribute("aria-label", "Palette de commandes");
  }
  let closed = false;
  const close = () => {
    if (closed) return; closed = true;
    ov.remove(); removeEventListener("keydown", key, true);
    if (prevFocus && prevFocus.isConnected && prevFocus.focus) setTimeout(() => prevFocus.focus(), 0);   // différé : la touche Entrée qui ferme ne doit pas réactiver le bouton
    onClose && onClose();
  };
  const key = e => {
    if (e.key === "Escape") { e.stopPropagation(); close(); }
    else if (e.key === "Tab") {           // le focus reste dans la fenêtre
      const f = $$("button:not([disabled]),input,select,textarea,[tabindex]:not([tabindex='-1'])", ov).filter(x => x.offsetParent !== null);
      if (!f.length) return;
      const i = f.indexOf(document.activeElement);
      if (e.shiftKey && i <= 0) { e.preventDefault(); f[f.length - 1].focus(); }
      else if (!e.shiftKey && (i === f.length - 1 || i < 0)) { e.preventDefault(); f[0].focus(); }
    }
  };
  addEventListener("keydown", key, true);
  ov.addEventListener("mousedown", e => { if (e.target === ov) close(); });
  onMount && onMount(ov, close);
  return close;
}
function confirmModal(title, message, okLabel = "Confirmer", danger = false) {
  return new Promise(res => {
    let result = false;
    modal(`<div class="modal glass" role="alertdialog" aria-describedby="cfM"><h2>${esc(title)}</h2><p class="sub" id="cfM">${message}</p>
      <div class="mactions"><button class="btn" data-x>Annuler</button><button class="btn ${danger ? "danger" : "primary"}" data-ok>${esc(okLabel)}</button></div></div>`,
      (ov, close) => {
        $("[data-ok]", ov).onclick = () => { result = true; close(); };
        $("[data-x]", ov).onclick = close;
        $(danger ? "[data-x]" : "[data-ok]", ov).focus();
      }, () => res(result));
  });
}
/* saisie d'un nom de fichier, avec validation en direct ; `types` propose une extension */
function nameModal({ title, sub, value = "", placeholder = "", types = null, okLabel = "Valider", validate }) {
  return new Promise(res => {
    let result = null, ext = types ? types[0] : "";
    modal(`<div class="modal glass"><h2>${esc(title)}</h2><p class="sub">${esc(sub)}</p>
      <div class="field"><label for="nmIn">Nom du fichier</label><input id="nmIn" value="${esc(value)}" placeholder="${esc(placeholder)}" autocomplete="off" spellcheck="false" style="font-family:var(--mono)"><div class="hint" id="nmHint" role="alert"></div>${types ? `<div class="preview" id="nmPrev"></div>` : ""}</div>
      ${types ? `<div class="seg" role="radiogroup" aria-label="Type de fichier">${types.map((t, i) => `<button type="button" role="radio" aria-checked="${i === 0}" data-ext="${t}">${t}</button>`).join("")}</div>` : ""}
      <div class="mactions"><button class="btn" data-x>Annuler</button><button class="btn primary" data-ok>${esc(okLabel)}</button></div></div>`,
      (ov, close) => {
        const inp = $("#nmIn", ov), hint = $("#nmHint", ov);
        const full = () => { const v = inp.value.trim(); return !types || /\.[A-Za-z0-9]{1,8}$/.test(v.split("/").pop()) ? v : v + ext; };
        const check = () => { const f = full(); hint.textContent = inp.value.trim() ? validate(f) : ""; if (types) $("#nmPrev", ov).textContent = inp.value.trim() ? "Sera créé : " + f : ""; return f; };
        inp.oninput = check;
        $$("[data-ext]", ov).forEach(b => b.onclick = () => { ext = b.dataset.ext; $$("[data-ext]", ov).forEach(x => x.setAttribute("aria-checked", x === b)); check(); inp.focus(); });
        const ok = () => { const f = check(); if (!inp.value.trim() || validate(f)) { inp.focus(); return; } result = f; close(); };
        $("[data-ok]", ov).onclick = ok; $("[data-x]", ov).onclick = close;
        inp.onkeydown = e => { if (e.key === "Enter") ok(); };
        inp.focus();
        const dot = value.lastIndexOf("."), sl = value.lastIndexOf("/") + 1; if (value.endsWith("/")) inp.setSelectionRange(value.length, value.length); else inp.setSelectionRange(sl, dot > sl ? dot : value.length);
      }, () => res(result));
  });
}
/* menu contextuel : items = [{label, icon, key, danger, disabled, title, action}] ou "-" pour un séparateur */
function ctxMenu(items, x, y, returnFocus) {
  $$(".ctxmenu").forEach(m => m.remove());
  const m = document.createElement("div");
  m.className = "ctxmenu"; m.setAttribute("role", "menu");
  m.innerHTML = items.map((it, i) => it === "-" ? "<hr>" : `<button role="menuitem" data-i="${i}" ${it.disabled ? "disabled" : ""} ${it.title ? `title="${esc(it.title)}"` : ""} class="${it.danger ? "danger" : ""}">${it.icon ? icon(it.icon) : ""}<span>${esc(it.label)}</span>${it.key ? `<span class="kbd k">${esc(it.key)}</span>` : ""}</button>`).join("");
  document.body.appendChild(m);
  m.style.left = Math.max(6, Math.min(x, innerWidth - m.offsetWidth - 6)) + "px";
  m.style.top = Math.max(6, Math.min(y, innerHeight - m.offsetHeight - 6)) + "px";
  const btns = () => $$("button:not([disabled])", m);
  const close = back => {
    m.remove(); removeEventListener("mousedown", away, true); removeEventListener("blur", close); removeEventListener("resize", close);
    if (back !== false && returnFocus && returnFocus.isConnected) returnFocus.focus();
  };
  const away = e => { if (!m.contains(e.target)) close(false); };
  addEventListener("mousedown", away, true); addEventListener("blur", close); addEventListener("resize", close);
  m.addEventListener("click", e => { const b = e.target.closest("[data-i]"); if (!b || b.disabled) return; close(); items[+b.dataset.i].action(); });
  m.addEventListener("keydown", e => {
    const l = btns(), i = l.indexOf(document.activeElement);
    if (e.key === "ArrowDown") { e.preventDefault(); l[(i + 1) % l.length].focus(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); l[(i - 1 + l.length) % l.length].focus(); }
    else if (e.key === "Home") { e.preventDefault(); l[0].focus(); }
    else if (e.key === "End") { e.preventDefault(); l[l.length - 1].focus(); }
    else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(); }
    else if (e.key === "Tab") { e.preventDefault(); close(); }
  });
  const first = btns()[0]; if (first) first.focus();
  return close;
}
function promptModal(title, sub, value = "", placeholder = "") {
  return new Promise(res => {
    let done = false;
    modal(`<div class="modal glass"><h2>${esc(title)}</h2><p class="sub">${esc(sub)}</p>
      <div class="field"><input id="pmIn" aria-label="${esc(title)}" value="${esc(value)}" placeholder="${esc(placeholder)}" style="font-family:var(--mono)"></div>
      <div class="mactions"><button class="btn" data-x>Annuler</button><button class="btn primary" data-ok>Valider</button></div></div>`,
      (ov, close) => {
        const inp = $("#pmIn", ov); inp.focus(); inp.select();
        const ok = () => { done = true; close(); res(inp.value.trim()); };
        $("[data-ok]", ov).onclick = ok; $("[data-x]", ov).onclick = () => { close(); };
        inp.onkeydown = e => { if (e.key === "Enter") ok(); };
        const mo = new MutationObserver(() => { if (!ov.isConnected) { mo.disconnect(); if (!done) res(""); } });
        mo.observe(document.body, { childList: true });
      });
  });
}

function newProject(lang, template) {
  const langs = S.exts.filter(x => x.kind === "lang" && x.enabled).sort((a, b) => (b.installed - a.installed) || a.name.localeCompare(b.name, "fr"));
  let L = lang || prefs.lastLang || (langs.find(x => x.installed) || langs[0] || {}).id || "python", tpl = template || "hello";
  modal(`<div class="modal wide glass"><h2>Nouveau projet</h2><p class="sub">Un dossier dans votre espace de projets, avec un premier programme prêt à exécuter.</p>
    <div class="field"><label for="npName">Nom du projet</label><input id="npName" placeholder="MonProjet" autocomplete="off"><div class="hint" id="npHint"></div></div>
    <div class="field"><label id="lgLbl">Langage</label></div>
    <div class="lgrid" role="radiogroup" aria-labelledby="lgLbl" id="npLangs"></div>
    <div class="field"><label id="tplLbl">Modèle de départ</label></div>
    <div class="tpls t3" role="radiogroup" aria-labelledby="tplLbl" id="npTpls"></div>
    <div class="mactions"><span class="dim" id="npNote" style="margin-right:auto;align-self:center;font-size:12px"></span><button class="btn" data-x>Annuler</button><button class="btn primary" data-ok>${icon("plus")}Créer</button></div></div>`,
    (ov, close) => {
      const inp = $("#npName", ov), hint = $("#npHint", ov);
      const draw = () => {
        $("#npLangs", ov).innerHTML = langs.map(x => `<button type="button" role="radio" aria-checked="${x.id === L}" class="tpl ${x.id === L ? "active" : ""} ${x.installed ? "" : "miss"}" data-l="${esc(x.id)}"><span class="lchip" style="${langStyle(x)}">${esc(x.abbr)}</span><span><b>${esc(x.name)}</b>${x.installed ? "" : "<small>à installer</small>"}</span></button>`).join("");
        const x = S.ext[L] || {}, tp = x.templates || ["empty"];
        if (!tp.includes(tpl)) tpl = tp.includes("hello") ? "hello" : tp[0];
        $("#npTpls", ov).innerHTML = tp.map(t => { const i = TPL_INFO[t] || ["📄", t, ""]; return `<button type="button" role="radio" aria-checked="${t === tpl}" class="tpl ${t === tpl ? "active" : ""}" data-t="${esc(t)}"><span class="te" aria-hidden="true">${i[0]}</span><b>${esc(i[1])}</b><small>${esc(i[2])}</small></button>`; }).join("");
        $("#npNote", ov).textContent = x.installed ? "" : `${x.name} sera à installer (${x.plan || x.why || "voir Extensions"}).`;
      };
      draw(); inp.focus();
      const valid = v => /^[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$/.test(v);
      inp.oninput = () => { const v = inp.value; hint.textContent = !v || valid(v) ? (S.projects.some(p => p.name === v) ? "Ce projet existe déjà" : "") : "Lettres, chiffres, _ . - uniquement, sans espace"; };
      $("#npLangs", ov).addEventListener("click", e => { const b = e.target.closest("[data-l]"); if (b) { L = b.dataset.l; draw(); } });
      $("#npTpls", ov).addEventListener("click", e => { const b = e.target.closest("[data-t]"); if (b) { tpl = b.dataset.t; draw(); } });
      const create = async () => {
        const name = inp.value.trim();
        if (!valid(name)) { hint.textContent = "Nom invalide"; inp.focus(); return; }
        try {
          await api("/api/project/new", { name, lang: L, template: tpl });
          prefs.lastLang = L; savePrefs();
          close(); await loadProjects(); await openProject(name);
          toast(`Projet « ${name} » créé — Ctrl+Entrée pour l'exécuter`, "ok", 4000);
          if (tpl === "plot") toast("Exécutez-le puis ouvrez l'onglet Traceur ✨", "info", 5000);
        } catch (e) { hint.textContent = e.message; }
      };
      $("[data-ok]", ov).onclick = create; $("[data-x]", ov).onclick = close;
      inp.onkeydown = e => { if (e.key === "Enter") create(); };
    });
}
$("#btnNew").addEventListener("click", () => newProject());
$("#wNew").addEventListener("click", () => newProject());

/* ------------------------------------------------------------------ aide et raccourcis */
const SHORTCUTS = [
  ["Général", [["Palette de commandes", "Ctrl K"], ["Aide et raccourcis", "?"], ["Barre latérale", "Ctrl B"], ["Inspecteur", "Ctrl Alt B"], ["Panneau du bas", "Ctrl J"], ["Mode d'apparence suivant", "Ctrl Alt T"]]],
  ["Exécution", [["Enregistrer", "Ctrl S"], ["Exécuter", "Ctrl ⏎"], ["Exécuter (variante)", "F5"], ["Arrêter", "⇧ F5"], ["Vérifier (compiler / syntaxe)", "Ctrl R"], ["Exécuter le fichier ouvert", "Ctrl ⇧ ⏎"]]],
  ["Terminal", [["Aller au terminal", "Ctrl ²"], ["Envoyer une ligne", "Entrée"], ["Historique", "↑ ↓"], ["Interrompre", "Ctrl C"], ["Fin de l'entrée", "Ctrl D"], ["Ouvrir l'erreur", "~clic sur la ligne"]]],
  ["Édition", [["Commenter / décommenter", "Ctrl /"], ["Dupliquer la ligne", "Ctrl D"], ["Déplacer vers le haut", "Alt ↑"], ["Déplacer vers le bas", "Alt ↓"],
    ["Indenter la sélection", "Tab"], ["Désindenter", "⇧ Tab"], ["Autocomplétion", "Ctrl Espace"], ["Déplier un extrait (cout, for, main…)", "Tab"], ["Champ suivant / précédent de l'extrait", "Tab / ⇧ Tab"],
    ["Insérer « << »", "Alt <"], ["Insérer « >> »", "Alt >"], ["Formater le fichier", "⇧ Alt F"], ["Analyser le fichier", "⇧ Alt L"],
    ["Police plus grande", "Ctrl +"], ["Police plus petite", "Ctrl −"], ["Taille par défaut", "Ctrl 0"]]],
  ["Recherche", [["Rechercher", "Ctrl F"], ["Remplacer", "Ctrl H"], ["Occurrence suivante", "Entrée"], ["Occurrence précédente", "⇧ Entrée"], ["Fermer", "Échap"]]],
  ["Erreurs", [["Erreur suivante", "F8"], ["Erreur précédente", "⇧ F8"]]],
  ["Fichiers", [["Onglet suivant", "Alt PgDn"], ["Onglet précédent", "Alt PgUp"], ["Fermer l'onglet", "Alt W"], ["Menu d'un fichier", "~clic droit"], ["Renommer (onglet actif)", "F2"]]],
  ["Traceur", [["Zoom horizontal", "Molette"], ["Zoom vertical", "⇧ Molette"], ["Déplacer la vue", "~glisser"], ["Ajuster (suivi en direct)", "~double-clic"]]],
  ["Académie", [["Ouvrir / fermer l'Académie", "F9"], ["Soumettre le défi en cours", "F6"], ["Fermer le détail, puis l'Académie", "Échap"], ["Voir son grade", "~badge en bas à droite"]]],
  ["Extensions", [["Installer un langage", "~onglet Extensions"], ["Ajouter le vôtre (JSON)", "~« Extension personnelle… »"], ["Paquets du projet", "~onglet Paquets"], ["En ligne de commande", "~./code.sh install rust"]]]
];
function helpModal() {
  if ($(".help")) return;
  modal(`<div class="modal help glass" role="dialog" aria-modal="true" aria-labelledby="helpT"><h2 id="helpT">Aide et raccourcis</h2>
    <p class="sub">Forge Code exécute vos programmes dans un vrai terminal : couleurs, saisie au clavier, Ctrl+C. Appuyez sur <span class="kbd">?</span> pour rouvrir cette fenêtre.</p>
    <p class="sub" style="font-size:12.5px;margin-top:-10px">Chaque langage est une <b>extension</b> (onglet Extensions) : installez-la en un clic, ou décrivez la vôtre en JSON. Les réglages d'un projet (langage, fichier principal, arguments) sont dans <code>.forge.json</code>.
    En ligne de commande : <code>./code.sh list</code> · <code>install</code> · <code>run</code> · <code>export</code>.</p>
    <div class="helpgrid">${SHORTCUTS.map(([g, rows]) => `<section><h4>${esc(g)}</h4><div class="keys">${rows.map(([n, k]) => `<span>${esc(n)}</span><span>${k[0] === "~" ? `<span class="dim">${esc(k.slice(1))}</span>` : k.split(" ").map(x => `<span class="kbd">${esc(x)}</span>`).join(" ")}</span>`).join("")}</div></section>`).join("")}</div>
    <div class="mactions" style="margin-top:18px"><button class="btn primary" data-x>Fermer</button></div></div>`,
    (ov, close) => { const b = $("[data-x]", ov); b.onclick = close; b.focus({ preventScroll: true }); });
}
$("#btnHelp").addEventListener("click", helpModal);

/* ------------------------------------------------------------------ fenêtre « Apparence » */
function lookThumb(m) {
  const t = forgeTheme(prefs, m), on = modeOf(prefs.mode).id === m.id;
  return `<button class="mthumb" role="radio" aria-checked="${on}" tabindex="${on ? 0 : -1}" data-pick="${m.id}" aria-label="${esc(m.name)}. ${esc(m.desc)}">
    <div class="mprev" data-mode="${m.id}" data-theme="${t}" aria-hidden="true">
      <div class="mp-side"><i class="mp-logo"></i><i class="mp-li on"></i><i class="mp-li"></i><i class="mp-li"></i><i class="mp-li"></i></div>
      <div class="mp-main"><div class="mp-bar"><b>Aa Forge</b><i class="mp-btn"></i></div>
        <div class="mp-code"><span class="c"># bonjour</span><br><span class="k">def</span> <span class="f">main</span>():<br>&nbsp;&nbsp;<span class="f">print</span>(<span class="s">"ok"</span>)<br>&nbsp;&nbsp;<span class="k">return</span> <span class="n">42</span></div>
        <div class="mp-con">✓ Terminé · code 0 · 0,4 s</div></div>
    </div>
    <b>${esc(m.name)}</b><small>${esc(m.desc)}${m.v.length === 1 ? " · " + (m.v === "d" ? "sombre" : "clair") + " uniquement" : ""}</small></button>`;
}
function lookRefresh() {
  const g = $("#lookGrid"); if (!g) return;
  const cur = modeOf(prefs.mode).id;
  $$(".mthumb", g).forEach(b => {
    const m = modeOf(b.dataset.pick), on = m.id === cur, p = $(".mprev", b);
    b.setAttribute("aria-checked", on); b.tabIndex = on ? 0 : -1; p.dataset.theme = forgeTheme(prefs, m);
  });
  const th = ["dark", "light", "system"].includes(prefs.theme) ? prefs.theme : "system";
  $$("#lkTheme button").forEach(b => b.setAttribute("aria-checked", b.dataset.v === th));
  $$("#lkDens button").forEach(b => b.setAttribute("aria-checked", b.dataset.v === (prefs.dens || "normal")));
  $("#lkFs").textContent = prefs.fs || 13.5;
  $("#lkMotion").checked = document.documentElement.dataset.motion === "reduced";
  $("#lkFx").checked = prefs.fx !== false;
  const m = modeOf(cur); $("#lkThemeNote").textContent = m.v.length === 1 ? `Ce mode n'existe qu'en version ${m.v === "d" ? "sombre" : "claire"}.` : "Le mode suit votre choix.";
}
function lookModal() {
  if ($(".look")) return;
  modal(`<div class="modal look glass" role="dialog" aria-modal="true" aria-labelledby="lkT"><h2 id="lkT">Apparence</h2>
    <p class="sub">Choisissez un mode : couleurs, polices, formes, décor et animations changent ensemble. <span class="kbd">Ctrl Alt T</span> passe au mode suivant.</p>
    <div class="mgrid" id="lookGrid" role="radiogroup" aria-label="Modes d'apparence">${FORGE_MODES.map(lookThumb).join("")}</div>
    <div class="lookrow"><b>Luminosité</b><div class="seg" id="lkTheme" role="radiogroup" aria-label="Luminosité">
      <button role="radio" data-v="light" aria-checked="false">Clair</button><button role="radio" data-v="dark" aria-checked="false">Sombre</button><button role="radio" data-v="system" aria-checked="false">Système</button></div><small id="lkThemeNote"></small></div>
    <div class="lookrow"><b>Taille de la police</b><div class="fsz"><button class="btn sm icon" id="lkFsDn" aria-label="Police plus petite">A−</button><span id="lkFs">13.5</span> px<button class="btn sm icon" id="lkFsUp" aria-label="Police plus grande">A+</button></div><small>Taille du code dans l'éditeur (Ctrl + / Ctrl −).</small></div>
    <div class="lookrow"><b>Densité</b><div class="seg" id="lkDens" role="radiogroup" aria-label="Densité">
      <button role="radio" data-v="compact" aria-checked="false">Compact</button><button role="radio" data-v="normal" aria-checked="false">Normal</button><button role="radio" data-v="aere" aria-checked="false">Aéré</button></div><small>Espacement des boutons, listes, cartes et lignes de code.</small></div>
    <div class="lookrow"><label class="switch"><input type="checkbox" id="lkMotion"><i></i><span>Animations réduites</span></label><small>Coupe les mouvements (arrière-plan, transitions, animation de réussite). Suit le réglage du système tant que vous n'y touchez pas.</small></div>
    <div class="lookrow"><label class="switch"><input type="checkbox" id="lkFx"><i></i><span>Effets décoratifs</span></label><small>Motifs de fond, balayage CRT, halos et animation quand un programme repart après une erreur.</small></div>
    <div class="mactions" style="margin-top:14px;display:flex;gap:8px;justify-content:flex-end"><button class="btn" id="lkTest">Voir l'animation de réussite</button><button class="btn primary" data-x>Fermer</button></div></div>`,
    (ov, close) => {
      lookRefresh();
      $("[data-x]", ov).onclick = close;
      $("#lookGrid", ov).addEventListener("click", e => { const b = e.target.closest("[data-pick]"); if (b) setMode(b.dataset.pick); });
      $("#lookGrid", ov).addEventListener("keydown", e => {
        const l = $$(".mthumb", ov), i = l.findIndex(b => b.getAttribute("aria-checked") === "true"), d = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
        if (!d) return; e.preventDefault(); setMode(l[(i + d + l.length) % l.length].dataset.pick); $(".mthumb[tabindex='0']", ov).focus();
      });
      $("#lkTheme", ov).addEventListener("click", e => { const b = e.target.closest("[data-v]"); if (b) setTheme(b.dataset.v); });
      $("#lkDens", ov).addEventListener("click", e => { const b = e.target.closest("[data-v]"); if (b) { prefs.dens = b.dataset.v; savePrefs(); applyTheme(); } });
      $("#lkFsDn", ov).onclick = () => { ED.setFont((prefs.fs || 13.5) - 1); lookRefresh(); };
      $("#lkFsUp", ov).onclick = () => { ED.setFont((prefs.fs || 13.5) + 1); lookRefresh(); };
      $("#lkMotion", ov).onchange = e => { prefs.reduced = e.target.checked; savePrefs(); applyTheme(); };
      $("#lkFx", ov).onchange = e => { prefs.fx = e.target.checked; savePrefs(); applyTheme(); };
      $("#lkTest", ov).onclick = () => celebrate($("#lkTest", ov));
      $(".mthumb[tabindex='0']", ov).focus({ preventScroll: true });
    });
}
$("#btnLook").addEventListener("click", lookModal);

/* ------------------------------------------------------------------ palette de commandes */
function commands() {
  const x = S.info && S.ext[S.info.lang];
  const c = [
    ["Exécuter", "play", () => run("run"), "Ctrl ⏎"],
    ["Exécuter le fichier ouvert", "play", () => run("run", S.file), "Ctrl ⇧ ⏎"],
    ["Vérifier (compiler / syntaxe)", "check", () => run("check"), "Ctrl R"],
    ["Arrêter le programme", "stop", stopRun, "⇧ F5"],
    ["Enregistrer", "save", () => saveAll(false), "Ctrl S"],
    [x && x.repl ? `Console interactive ${x.name}` : "Console interactive", "chat", () => interactive("repl"), ""],
    ["Shell dans le dossier du projet", "terminal", () => interactive("shell"), ""],
    ["Formater le fichier", "sparkle", formatFile, "⇧ Alt F"],
    ["Analyser le fichier", "lint", lintFile, "⇧ Alt L"],
    [prefs.live === false ? "Activer la vérification en direct" : "Désactiver la vérification en direct", "check", () => {
      prefs.live = prefs.live === false; savePrefs(); toast(prefs.live ? "Vérification en direct activée" : "Vérification en direct désactivée", "info", 1800);
      if (prefs.live) liveSchedule(0); else setDiags(S.diags.filter(d => !d.live));
    }, ""],
    ["Nouveau projet", "plus", () => newProject(), ""],
    ["Nouveau fichier…", "filePlus", () => fileNew(), ""],
    ["Renommer le fichier actif…", "edit", () => S.file && fileRename(S.file), "F2"],
    ["Supprimer le fichier actif…", "trash", () => S.file && fileDelete(S.file), ""],
    ["Définir le fichier actif comme principal", "star", () => S.file && setMain(S.file), ""],
    ["Fermer l'onglet", "x", () => S.file && closeTab(S.file), "Alt W"],
    [S.meta.pinned.includes(S.project) ? "Désépingler le projet" : "Épingler le projet", "pin", () => S.project && togglePin(S.project), ""],
    ["Extensions : langages et outils", "puzzle", () => { showTab("exts"); $("#extQ").focus(); }, ""],
    ["Extension personnelle (JSON)…", "puzzle", () => customExtModal(), ""],
    ["Paquets du projet", "pkg", () => { showTab("pkgs"); $("#pkgName").focus(); }, ""],
    ["Exemples", "code", () => { showTab("examples"); $("#exQ").focus(); }, ""],
    ["Académie : parcours, défis et grades", "star", () => acOpen("path"), "F9"],
    ["Académie : mes compétences", "activity", () => acOpen("skills"), ""],
    ["Académie : succès et certificats", "star", () => acOpen("ach"), ""],
    ...(PG.here ? [["Soumettre le défi en cours", "check", progSubmit, "F6"]] : []),
    ["Apparence…", "heart", lookModal, ""],
    ["Mode d'apparence suivant", "heart", () => nextMode(1), "Ctrl Alt T"],
    ["Mode d'apparence précédent", "heart", () => nextMode(-1), ""],
    ...FORGE_MODES.map(m => [`Mode : ${m.name}`, "heart", () => setMode(m.id), ""]),
    ["Thème sombre", "heart", () => setTheme("dark"), ""],
    ["Thème clair", "heart", () => setTheme("light"), ""],
    ["Thème du système", "heart", () => setTheme("system"), ""],
    ["Aide et raccourcis", "info", helpModal, "?"],
    ["Afficher / masquer la barre latérale", "folder", toggleSide, "Ctrl B"],
    ["Afficher / masquer l'inspecteur", "layers", toggleInspector, "Ctrl Alt B"],
    ["Replier / déplier le panneau du bas", "terminal", () => setPanel(!panelOpen(), true), "Ctrl J"],
    ["Afficher le traceur", "activity", () => showTab("plotter"), ""],
    ["Structure du fichier", "layers", () => openInsp("outline"), ""],
    ["Créer un instantané…", "save", () => { openInsp("snaps"); snapCreate(); }, ""],
    ["Afficher les instantanés", "save", () => openInsp("snaps"), ""],
    ["Exporter le projet en .zip", "download", () => exportProject(), ""],
    ["Importer un projet (.zip)…", "folder", pickZip, ""],
    ["Lancer le diagnostic", "heart", () => { showTab("doctor"); runDoctor(); }, ""],
    ["Effacer le terminal", "trash", termClear, ""],
    ["Basculer exécution auto à l'enregistrement", "zap", () => { const a = $("#autoRun"); a.checked = !a.checked; a.dispatchEvent(new Event("change")); }, ""]
  ];
  S.exts.filter(e => e.kind === "lang" && !e.installed && e.plan && e.enabled).forEach(e => c.push([`Installer ${e.name}`, "download", () => extInstall(e.id), ""]));
  S.projects.forEach(p => c.push([`Ouvrir ${p.name}`, "folder", () => openProject(p.name), langName(p.lang)]));
  S.tabs.forEach(f => c.push([`Aller à ${f}`, "file", () => openFile(f), ""]));
  return c;
}
function fuzzy(q, s) { q = q.toLowerCase(); s = s.toLowerCase(); let i = 0; for (const ch of s) if (ch === q[i]) i++; return i === q.length; }
function palette() {
  if ($(".palette")) return;
  let items = [], sel = 0;
  modal(`<div class="palette glass"><div class="pw">${icon("search")}<input id="palIn" placeholder="Tapez une commande ou un projet…"></div><ul id="palList"></ul></div>`, (ov, close) => {
    const inp = $("#palIn", ov), ul = $("#palList", ov);
    const draw = () => {
      items = commands().filter(c => fuzzy(inp.value, c[0])).slice(0, 40);
      sel = Math.min(sel, Math.max(0, items.length - 1));
      ul.innerHTML = items.map((c, i) => `<li class="${i === sel ? "sel" : ""}" data-i="${i}">${icon(c[1])}<span>${esc(c[0])}</span>${c[3] ? `<span class="kbd">${esc(c[3])}</span>` : ""}</li>`).join("") || `<li>Aucune commande</li>`;
      const s = ul.children[sel]; s && s.scrollIntoView({ block: "nearest" });
    };
    const go = i => { const c = items[i]; if (c) { close(); c[2](); } };
    inp.oninput = () => { sel = 0; draw(); };
    inp.onkeydown = e => {
      if (e.key === "ArrowDown") { sel = Math.min(items.length - 1, sel + 1); draw(); e.preventDefault(); }
      else if (e.key === "ArrowUp") { sel = Math.max(0, sel - 1); draw(); e.preventDefault(); }
      else if (e.key === "Enter") go(sel);
    };
    ul.onclick = e => { const li = e.target.closest("[data-i]"); if (li) go(+li.dataset.i); };
    draw(); inp.focus();
  });
}

/* ------------------------------------------------------------------ raccourcis globaux */
$("#autoRun").checked = !!prefs.auto;
$("#autoRun").addEventListener("change", e => { prefs.auto = e.target.checked; savePrefs(); toast(e.target.checked ? "Exécution automatique à chaque Ctrl+S" : "Exécution automatique désactivée", "info", 2200); });
addEventListener("keydown", e => {
  const mod = e.ctrlKey || e.metaKey, k = e.key.toLowerCase(), ov = !!$(".overlay");
  if (e.key === "F8" && !mod && !e.altKey && !ov) { e.preventDefault(); jumpDiag(e.shiftKey ? -1 : 1); return; }
  if (e.key === "F5" && !mod && !ov) { e.preventDefault(); e.shiftKey ? stopRun() : run("run"); return; }
  if (e.altKey && !mod && !ov) {
    if (e.key === "PageDown" || e.key === "PageUp") { e.preventDefault(); cycleTab(e.key === "PageDown" ? 1 : -1); return; }
    if (e.code === "KeyW" && S.file) { e.preventDefault(); closeTab(S.file); return; }
    if (e.shiftKey && e.code === "KeyF") { e.preventDefault(); formatFile(); return; }
    if (e.shiftKey && e.code === "KeyL") { e.preventDefault(); lintFile(); return; }
  }
  if (!mod) {
    const t = e.target, typing = t && (/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || t.isContentEditable);
    if (e.key === "?" && !typing && !e.altKey && !ov) { e.preventDefault(); helpModal(); }
    return;
  }
  if (e.key === "Enter" && !ov && e.target.id !== "tInput") { e.preventDefault(); e.shiftKey ? run("run", S.file) : run("run"); return; }
  if (e.code === "Backquote" || e.key === "²" || e.code === "IntlBackslash") { e.preventDefault(); showTab("terminal"); $("#tInput").focus(); return; }
  if (e.altKey && !e.shiftKey && e.code === "KeyT") { e.preventDefault(); nextMode(1); return; }
  if ((k === "f" || k === "h") && !e.altKey && !e.shiftKey && S.file && !ov) { e.preventDefault(); findOpen(k === "h"); }
  else if (k === "b") { e.preventDefault(); e.altKey ? toggleInspector() : toggleSide(); }
  else if (k === "j") { e.preventDefault(); setPanel(!panelOpen(), true); }
  else if (k === "s") { e.preventDefault(); if (!S.project) return; saveAll(false).then(() => { if ($("#autoRun").checked) run("run"); }); }
  else if (k === "r" && !e.shiftKey) { e.preventDefault(); run("check"); }
  else if (k === "k" || (e.shiftKey && k === "p")) { e.preventDefault(); palette(); }
});
addEventListener("beforeunload", e => { if (anyDirty()) { e.preventDefault(); e.returnValue = ""; } });
addEventListener("resize", () => { clearTimeout(window.__rz); window.__rz = setTimeout(() => { if (S.session.running) api("/api/resize", termSize()).catch(() => {}); }, 300); });

/* ------------------------------------------------------------------ événements serveur */
let firstConnect = true;
function connectEvents() {
  const es = new EventSource("/api/events?token=" + encodeURIComponent(TOKEN));
  es.onopen = () => {
    $("#sseDot").classList.add("on"); $("#sseLbl").textContent = "Connecté";
    if (!firstConnect) init(true);
    firstConnect = false;
  };
  es.onerror = () => { $("#sseDot").classList.remove("on"); $("#sseLbl").textContent = "Reconnexion…"; };
  es.onmessage = ev => {
    let m; try { m = JSON.parse(ev.data); } catch { return; }
    (HANDLERS[m.type] || (() => {}))(m);
  };
}
const RUN_STEPS = { build: ["build", "Compilation", "Compilation du programme"], exec: ["exec", "Exécution", "Exécution dans le terminal"], check: ["build", "Vérification", "Vérification du code"] };
const HANDLERS = {
  term: m => termWrite(m.text, m.kind),
  toast: m => toast(m.text, m.kind),
  session: m => {
    S.session = { running: m.state === "open", kind: m.kind, cmd: m.state === "open" ? m.cmd : "" };
    if (m.state === "closed") {
      S.lastExit = { code: m.code, seconds: m.seconds };
      if (m.kind !== "run") termLine(`— ${m.kind === "repl" ? "console" : "shell"} fermé${m.kind === "repl" ? "e" : ""} —`, "end");
    } else S.lastExit = null;
    termState();
  },
  run: m => {
    if (m.state === "start") {
      S.run = S.run || { mode: m.mode, t0: Date.now() };
      S.run.steps = m.mode === "check" ? [RUN_STEPS.check] : [...(m.steps ? [RUN_STEPS.build] : []), ...(m.exec ? [RUN_STEPS.exec] : [])];
      if (!S.run.steps.length) S.run.steps = [RUN_STEPS.check];
      S.run.building = !!m.steps;
      setSteps(S.run.steps, S.run.steps[0][0]);
      S.stepText = m.mode === "check" ? "Vérification…" : m.steps ? "Compilation…" : "Exécution…"; tickJob();
      updateButtons();
    } else if (m.state === "step") {
      if (!S.run) return;
      S.run.building = m.step === "build";
      setSteps(S.run.steps, m.step);
      S.stepText = m.step === "exec" ? "Exécution…" : S.run.mode === "check" ? "Vérification…" : "Compilation…"; tickJob();
    } else if (m.state === "done") {
      if (m.stopped && S.run && !S.run.steps) {          // l'ancien programme, arrêté pour laisser place à la nouvelle exécution
        termLine(`— programme arrêté après ${m.seconds} s (relancé) —`, "end"); return;
      }
      const steps = (S.run && S.run.steps) || [RUN_STEPS.exec], mode = m.mode || (S.run && S.run.mode) || "run";
      S.run = null; S.stepText = ""; tickJob();
      if (m.preview) { setSteps(null); updateButtons(); return; }
      const failStep = m.stage === "build" ? "build" : "exec";
      if (m.ok) setSteps(steps, "done"); else setSteps(steps, steps.some(s => s[0] === failStep) ? failStep : steps[0][0], true);
      const [ne] = diagCounts();
      if (mode === "check") {
        if (m.ok) { toast(m.warnings ? `Vérifié : ${plural(m.warnings, "avertissement", "avertissements")}` : `Aucune erreur (${m.seconds} s)`, m.warnings ? "warn" : "ok"); addHistory(true, "Vérification", m.seconds); }
        else if (!m.cancelled) { toast(ne ? `${plural(ne, "erreur", "erreurs")} — F8 pour les parcourir` : "La vérification a échoué — voir le terminal", "error", 5000); addHistory(false, "Vérification", m.seconds); }
        termLine(m.ok ? `— vérification terminée en ${m.seconds} s —` : m.cancelled ? "— vérification annulée —" : `— vérification échouée —`, m.ok ? "end okk" : "end ko");
      } else if (m.stage === "build" || m.stage === "start") {
        if (!m.cancelled) { toast(ne ? `Compilation échouée : ${plural(ne, "erreur", "erreurs")}` : "Échec avant l'exécution — voir le terminal", "error", 5000); addHistory(false, "Compilation", m.seconds); S.lastRunOk = false; }
        termLine(m.cancelled ? "— compilation annulée —" : "— compilation échouée —", "end ko");
      } else {
        const ok = m.ok, sig = m.code < 0 ? ` (signal ${-m.code})` : "";
        termLine(m.stopped ? `— programme arrêté après ${m.seconds} s —` : `— programme terminé · code ${m.code}${sig} · ${m.seconds} s —`, "end " + (ok ? "okk" : "ko"));
        addHistory(ok || m.stopped, m.stopped ? "Arrêté" : ok ? "Exécution" : `Erreur (code ${m.code})`, m.seconds);
        if (!ok && !m.stopped) toast(ne ? `Le programme s'est arrêté sur ${plural(ne, "erreur", "erreurs")} (F8)` : `Le programme s'est terminé avec le code ${m.code}`, "error", 5000);
        if (ok && !S.lastRunOk) celebrate($("#btnRun"));
        if (!m.stopped) S.lastRunOk = ok;
        if (ok && SNAP.data && SNAP.data.auto && S.project) api("/api/snapshots/create", { project: S.project, label: "", auto: true }).catch(() => {});
      }
      if (!m.ok && ne) { const first = S.diags.find(d => d.severity === "error"); if (first) openFile(first.file, first.line, first.col); }
      updateButtons();
    }
  },
  diagnostics: m => setDiags(m.items),
  preview: m => {
    const w = window.open(m.url, "forge-preview-" + m.project);
    if (!w) toast("Aperçu bloqué par le navigateur : autorisez les fenêtres surgissantes", "warn", 5000); else toast("Aperçu ouvert — il se recharge à chaque Ctrl+S", "ok", 2500);
  },
  job: m => {
    if (m.state === "running") {
      S.job = m; jobT0 = Date.now(); S.stepText = `${m.kind === "pkg" ? "Paquet" : "Installation"} : ${m.label}…`;
      setSteps([["job", m.kind === "pkg" ? "Paquet" : "Installation", `${m.kind === "pkg" ? "Paquet" : "Installation"} : ${m.label}`]], "job");
    } else {
      S.job = null; S.stepText = ""; EXTV.busy = null;
      setSteps([["job", m.kind === "pkg" ? "Paquet" : "Installation", m.label]], m.ok ? "done" : "job", !m.ok);
      if (m.kind === "pkg" && activeTab === "pkgs") pkgsLoad();
      extRender();
    }
    tickJob();
  },
  exts_changed: () => extLoad(false),
  pkgs_changed: m => { if (m.project === S.project && activeTab === "pkgs") pkgsLoad(); },
  need_root: m => {
    modal(`<div class="modal glass"><h2>Droits administrateur nécessaires</h2>
      <p class="sub">L'installation de <b>${esc(m.name)}</b> passe par le gestionnaire de paquets du système, et Forge Code ne peut pas demander votre mot de passe ici. Lancez plutôt, dans un terminal :</p>
      <pre class="snip" style="cursor:copy" title="Copier">./code.sh install ${esc(m.ext)}</pre>
      <p class="sub" style="margin-top:12px">ou directement :</p><pre class="snip" style="cursor:copy;white-space:pre-wrap" title="Copier">${esc(m.cmd)}</pre>
      <p class="sub" style="margin-top:12px">Revenez ensuite ici et cliquez sur ⟳ (Extensions) : Forge Code détectera ${esc(m.name)}.</p>
      <div class="mactions"><button class="btn primary" data-x>Compris</button></div></div>`,
      (ov, close) => { $("[data-x]", ov).onclick = close; $$("pre", ov).forEach(p => p.onclick = () => navigator.clipboard?.writeText(p.textContent).then(() => toast("Copié", "ok", 1200))); });
  },
  snapshot: m => {
    if (m.project !== S.project) return;
    if (prefs.insp === "snaps") snapsLoad();
    if (m.auto) toast(`Instantané automatique enregistré (${m.hash})`, "ok", 2500);
  }
};

/* ------------------------------------------------------------------ démarrage */
async function init(resync) {
  try {
    const st = await api("/api/status");
    S.status = st;
    $("#wsPath").textContent = midTrunc(st.workspace); $("#wsPath").title = st.workspace;
    $("#stVer").innerHTML = `Forge Code <b>${esc(st.version)}</b>`;
    S.projects = st.projects; S.meta = st.meta || { pinned: [], opened: {} };
    S.session = { running: st.session.running, kind: st.session.kind };
    termState();
    await extLoad(false);
    renderProjects();
    if (!resync) {
      const last = prefs.lastProject && S.projects.find(p => p.name === prefs.lastProject);
      if (last) await openProject(last.name);
      else { $("#welcome").classList.add("show"); renderTree(); }
      if (!PG.data) progLoad("");
      if (prefs.tab && prefs.tab !== "doctor" && prefs.tab !== "prog") showTab(prefs.tab, true);
    }
    updateButtons();
  } catch (e) { toast("Serveur injoignable : " + e.message, "error"); }
}
$("#welcome").classList.add("show");
setPanel(prefs.panelOpen === true, false);
$("#fntDown").addEventListener("click", () => ED.setFont((prefs.fs || 13.5) - 1));
$("#fntUp").addEventListener("click", () => ED.setFont((prefs.fs || 13.5) + 1));
ED.setFont(prefs.fs || 13.5);
showInsp(["proj", "outline", "snaps"].includes(prefs.insp) ? prefs.insp : "proj");
connectEvents();
init();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
