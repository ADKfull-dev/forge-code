# -*- coding: utf-8 -*-
"""Palier 5 — Structures de données : piles, files, tas, listes chaînées, ensembles, historiques."""
from .base import ch, lines


def _spirale(h, w, m):
    out, t, b, l, r = [], 0, h - 1, 0, w - 1
    while t <= b and l <= r:
        out += [m[t][j] for j in range(l, r + 1)]
        out += [m[i][r] for i in range(t + 1, b + 1)]
        if t < b:
            out += [m[b][j] for j in range(r - 1, l - 1, -1)]
        if l < r:
            out += [m[i][l] for i in range(b - 1, t, -1)]
        t, b, l, r = t + 1, b - 1, l + 1, r - 1
    return " ".join(map(str, out))


# ---------------------------------------------------------------- tests générés
def _gen_pile():
    c = [f"PUSH {100000 - i}" if i % 3 else "MIN" for i in range(60000)] + ["POP" if i % 2 else "MIN" for i in range(60000)] + [f"PUSH {i * 7 % 1000}" for i in range(30000)] + ["MIN"] * 30000
    return f"{len(c)}\n" + lines(c)


def _gen_deque():
    c = []
    for i in range(160000):
        c.append(f"AVANT {i}" if i % 4 == 0 else f"ARRIERE {i}" if i % 4 == 1 else f"AVANT {i}" if i % 4 == 2 else "RETIRE_AVANT" if i % 8 == 3 else "RETIRE_ARRIERE")
    c += ["RETIRE_AVANT"] * 20000
    return f"{len(c)}\n" + lines(c)


def _gen_taches():
    c = [f"AJOUTE t{i} {(i * 7919) % 1000}" for i in range(100000)] + ["SUIVANTE" if i % 3 else f"AJOUTE u{i} {i % 50}" for i in range(100000)]
    return f"{len(c)}\n" + lines(c)


def _gen_nav():
    c = []
    for i in range(20000):
        c.append(f"VISITE p{i % 97}" if i % 5 in (0, 3) else "RETOUR" if i % 5 in (1, 4) else "AVANCE")
    return f"{len(c)}\n" + lines(c)


def _gen_edit():
    c = []
    for i in range(100000):
        r = i % 10
        c.append(f"AJOUTE {'abcdefghij'[i % 10] * (i % 7 + 1)}" if r < 4 else "EFFACE 1" if r == 4 else "AFFICHE 1" if r in (5, 6) else "ANNULE" if r in (7, 8) else "AFFICHE 2")
    c = ["AJOUTE forgecode"] + c
    return f"{len(c)}\n" + lines(c)


_P1 = "7\nPUSH 5\nPUSH 2\nMIN\nPUSH 8\nPOP\nPOP\nMIN"
_P2 = "6\nMIN\nPOP\nPUSH -3\nPUSH -3\nPOP\nMIN"
_PB = _gen_pile
_D1 = "7\nARRIERE a\nAVANT b\nARRIERE c\nRETIRE_AVANT\nRETIRE_ARRIERE\nRETIRE_ARRIERE\nRETIRE_AVANT"
_D2 = "4\nAVANT x\nAVANT y\nAVANT z\nRETIRE_ARRIERE"
_DB = _gen_deque
_K1 = "6\nAJOUTE cafe 2\nAJOUTE bug 9\nAJOUTE mail 2\nSUIVANTE\nSUIVANTE\nSUIVANTE"
_K2 = "5\nSUIVANTE\nAJOUTE a 1\nAJOUTE b 1\nSUIVANTE\nSUIVANTE"
_KB = _gen_taches
_E1 = "4\n1 2 3 3 4\n3 4 5"
_E2 = "4\n7 7 7\n"
_E3 = "4\n-1 0 1\n-1 0 1"
_EB = lambda: "4\n" + " ".join(str((i * 7919) % 100003) for i in range(100000)) + "\n" + " ".join(str((i * 104729) % 100019) for i in range(100000))
_N1 = "6\nVISITE a\nVISITE b\nRETOUR\nRETOUR\nRETOUR\nAVANCE"
_N2 = "6\nVISITE a\nVISITE b\nRETOUR\nVISITE c\nAVANCE\nRETOUR"
_NB = _gen_nav
_RP1 = "4\n3 4 + 2 *\n5 1 2 + 4 * + 3 -\n1 +\n4 0 /"
_RP2 = "5\n-7 2 /\n7 -2 /\n1 2 3\n42\n1000000000 1000000000 * 3 *"
_ED1 = "8\nAJOUTE abc\nAFFICHE 3\nEFFACE 3\nAJOUTE xy\nAFFICHE 2\nANNULE\nANNULE\nAFFICHE 3"
_ED2 = "6\nAJOUTE forge\nAJOUTE code\nEFFACE 3\nAFFICHE 4\nANNULE\nAFFICHE 9"
_EDB = _gen_edit
_SP = [[i * 30 + j for j in range(30)] for i in range(20)]

DEFIS = [
    ch("parentheses", 5, "mini", "Parenthèses équilibrées", "piles",
       "Lisez une ligne. Les ( ) [ ] { } sont-ils bien équilibrés et imbriqués (les autres caractères sont ignorés) ? Affichez « valide » ou « invalide ».",
       [("(a[b]{c})", "valide"), ("(]", "invalide"), ("((())", "invalide"), ("sans parenthese", "valide"), ("{[()()]}", "valide"), (")(", "invalide"), ("([)]", "invalide"),
        ("(" * 50000 + ")" * 50000, "valide"), ("[" * 50000 + ")" * 50000, "invalide")],
       ["Utilisez une pile.", "Ouvrante : on l'empile. Fermante : le sommet doit être l'ouvrante correspondante, qu'on dépile.", "À la fin, la pile doit être vide."],
       {"cpp": r"""
#include <iostream>
#include <string>
int main() {
    std::string s, st;
    std::getline(std::cin, s);
    bool ok = true;
    for (char c : s) {
        if (c == '(' || c == '[' || c == '{') st += c;
        else if (c == ')' || c == ']' || c == '}') {
            char o = c == ')' ? '(' : c == ']' ? '[' : '{';
            if (st.empty() || st.back() != o) { ok = false; break; }
            st.pop_back();
        }
    }
    std::cout << (ok && st.empty() ? "valide" : "invalide") << std::endl;
}""", "c": r"""
#include <stdio.h>
#include <string.h>
int main(void) {
    static char s[1 << 20], st[1 << 20];
    int n = 0, ok = 1;
    if (!fgets(s, sizeof s, stdin)) s[0] = '\0';
    for (char *p = s; *p && ok; ++p) {
        char c = *p;
        if (c == '(' || c == '[' || c == '{') st[n++] = c;
        else if (c == ')' || c == ']' || c == '}') {
            char o = c == ')' ? '(' : c == ']' ? '[' : '{';
            if (n == 0 || st[n - 1] != o) ok = 0;
            else --n;
        }
    }
    puts(ok && n == 0 ? "valide" : "invalide");
    return 0;
}""", "python": r"""
pile, ok = [], True
for c in input():
    if c in "([{":
        pile.append(c)
    elif c in ")]}":
        if not pile or pile.pop() != "([{"[")]}".index(c)]:
            ok = False
            break
print("valide" if ok and not pile else "invalide")""", "javascript": r"""
const s = require("fs").readFileSync(0, "utf8").split("\n")[0];
const pile = [], paire = { ")": "(", "]": "[", "}": "{" };
let ok = true;
for (const c of s) {
  if ("([{".includes(c)) pile.push(c);
  else if (c in paire && pile.pop() !== paire[c]) { ok = false; break; }
}
console.log(ok && pile.length === 0 ? "valide" : "invalide");""", "php": r"""
<?php
$s = rtrim((string) fgets(STDIN), "\r\n");
$pile = [];
$paire = [')' => '(', ']' => '[', '}' => '{'];
$ok = true;
for ($i = 0; $i < strlen($s); $i++) {
    $c = $s[$i];
    if ($c === '(' || $c === '[' || $c === '{') $pile[] = $c;
    elseif (isset($paire[$c]) && array_pop($pile) !== $paire[$c]) { $ok = false; break; }
}
echo $ok && !$pile ? "valide" : "invalide", "\n";"""}),

    ch("pile-min", 5, "mini", "La pile qui connaît son minimum", "piles",
       "Ligne 1 : n (jusqu'à 200 000). Puis n commandes : « PUSH x » (empile x), « POP » (dépile et affiche la valeur, ou « vide »), "
       "« MIN » (affiche le plus petit élément de la pile, ou « vide »). Chaque commande doit se faire en temps constant.",
       [_P1, _P2, _PB],
       ["Chercher le minimum dans toute la pile à chaque « MIN » est bien trop lent quand la pile contient 100 000 éléments.",
        "Astuce : une deuxième pile, en parallèle, où l'on empile à chaque PUSH le minimum courant min(x, ancien minimum).",
        "Au POP, on dépile les deux piles ensemble : le sommet de la seconde est toujours le minimum de ce qui reste."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
pile, mins, out = [], [], []
for c in L[1:int(L[0]) + 1]:
    p = c.split()
    if p[0] == "PUSH":
        x = int(p[1])
        pile.append(x)
        mins.append(min(x, mins[-1]) if mins else x)
    elif p[0] == "POP":
        out.append(str(pile.pop()) if pile else "vide")
        if mins:
            mins.pop()
    else:
        out.append(str(mins[-1]) if mins else "vide")
print("\n".join(out))""", "c": r"""
#include <stdio.h>
#include <string.h>
static long long pile[200005], mins[200005];
int main(void) {
    int n, t = 0;
    char c[8];
    long long x;
    if (scanf("%d", &n) != 1) return 1;
    while (n-- > 0 && scanf("%7s", c) == 1) {
        if (strcmp(c, "PUSH") == 0) {
            if (scanf("%lld", &x) != 1) return 1;
            pile[t] = x;
            mins[t] = t && mins[t - 1] < x ? mins[t - 1] : x;
            ++t;
        } else if (strcmp(c, "POP") == 0) {
            if (t) printf("%lld\n", pile[--t]); else puts("vide");
        } else {
            if (t) printf("%lld\n", mins[t - 1]); else puts("vide");
        }
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n;
    std::cin >> n;
    std::vector<long long> pile, mins;
    std::string c;
    while (n-- > 0 && std::cin >> c) {
        if (c == "PUSH") {
            long long x;
            std::cin >> x;
            pile.push_back(x);
            mins.push_back(mins.empty() ? x : std::min(x, mins.back()));
        } else if (c == "POP") {
            if (pile.empty()) std::cout << "vide\n";
            else { std::cout << pile.back() << "\n"; pile.pop_back(); mins.pop_back(); }
        } else std::cout << (mins.empty() ? "vide" : std::to_string(mins.back())) << "\n";
    }
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const pile = [], mins = [], out = [];
for (let i = 1; i <= Number(L[0]); i++) {
  const [c, v] = L[i].trim().split(" ");
  if (c === "PUSH") {
    const x = Number(v);
    pile.push(x);
    mins.push(mins.length ? Math.min(x, mins[mins.length - 1]) : x);
  } else if (c === "POP") {
    out.push(pile.length ? pile.pop() : "vide");
    mins.pop();
  } else out.push(mins.length ? mins[mins.length - 1] : "vide");
}
console.log(out.join("\n"));""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
$pile = []; $mins = []; $out = [];
for ($i = 0; $i < $n; $i++) {
    $p = explode(' ', trim(fgets(STDIN)));
    if ($p[0] === 'PUSH') {
        $x = (int) $p[1];
        $pile[] = $x;
        $mins[] = $mins ? min($x, end($mins)) : $x;
    } elseif ($p[0] === 'POP') {
        $out[] = $pile ? array_pop($pile) : 'vide';
        array_pop($mins);
    } else $out[] = $mins ? end($mins) : 'vide';
}
echo implode("\n", $out), "\n";"""}),

    ch("deque", 5, "mini", "La file à deux bouts", "files",
       "Ligne 1 : n (jusqu'à 180 000). Puis n commandes : « AVANT x » et « ARRIERE x » ajoutent un mot au début ou à la fin, « RETIRE_AVANT » "
       "et « RETIRE_ARRIERE » l'enlèvent et l'affichent (ou « vide »). Terminez par « taille: k ». Chaque opération doit être rapide.",
       [_D1, _D2, _DB],
       ["Insérer au début d'un tableau décale tous les éléments : 100 000 insertions deviennent des milliards d'opérations.",
        "Python : collections.deque. PHP : SplDoublyLinkedList. C++ : std::deque. JavaScript et C : à construire soi-même.",
        "Tableau circulaire : un indice de début, un indice de fin, et des indices qui « font le tour » avec un modulo (ou deux piles tête-bêche)."],
       {"python": r"""
import sys
from collections import deque
L = sys.stdin.read().split("\n")
d, out = deque(), []
for c in L[1:int(L[0]) + 1]:
    p = c.split()
    if p[0] == "AVANT":
        d.appendleft(p[1])
    elif p[0] == "ARRIERE":
        d.append(p[1])
    elif p[0] == "RETIRE_AVANT":
        out.append(d.popleft() if d else "vide")
    else:
        out.append(d.pop() if d else "vide")
out.append(f"taille: {len(d)}")
print("\n".join(out))""", "c": r"""
#include <stdio.h>
#include <string.h>
#define CAP 262144
static char buf[CAP][16];
int main(void) {
    int n, deb = 0, taille = 0;
    char c[16], mot[16];
    if (scanf("%d", &n) != 1) return 1;
    while (n-- > 0 && scanf("%15s", c) == 1) {
        if (strcmp(c, "AVANT") == 0) {
            if (scanf("%15s", mot) != 1) return 1;
            deb = (deb - 1 + CAP) % CAP;
            strcpy(buf[deb], mot);
            ++taille;
        } else if (strcmp(c, "ARRIERE") == 0) {
            if (scanf("%15s", mot) != 1) return 1;
            strcpy(buf[(deb + taille) % CAP], mot);
            ++taille;
        } else if (taille == 0) puts("vide");
        else if (strcmp(c, "RETIRE_AVANT") == 0) { puts(buf[deb]); deb = (deb + 1) % CAP; --taille; }
        else { puts(buf[(deb + taille - 1) % CAP]); --taille; }
    }
    printf("taille: %d\n", taille);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
#include <deque>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n;
    std::cin >> n;
    std::deque<std::string> d;
    std::string c, m;
    while (n-- > 0 && std::cin >> c) {
        if (c == "AVANT") { std::cin >> m; d.push_front(m); }
        else if (c == "ARRIERE") { std::cin >> m; d.push_back(m); }
        else if (d.empty()) std::cout << "vide\n";
        else if (c == "RETIRE_AVANT") { std::cout << d.front() << "\n"; d.pop_front(); }
        else { std::cout << d.back() << "\n"; d.pop_back(); }
    }
    std::cout << "taille: " << d.size() << "\n";
}""", "javascript": r"""
// tableau circulaire qui double de taille quand il est plein
class Deque {
  constructor() { this.t = new Array(16); this.deb = 0; this.n = 0; }
  grandir() {
    const t = new Array(this.t.length * 2);
    for (let i = 0; i < this.n; i++) t[i] = this.t[(this.deb + i) % this.t.length];
    this.t = t; this.deb = 0;
  }
  avant(x) { if (this.n === this.t.length) this.grandir(); this.deb = (this.deb - 1 + this.t.length) % this.t.length; this.t[this.deb] = x; this.n++; }
  arriere(x) { if (this.n === this.t.length) this.grandir(); this.t[(this.deb + this.n) % this.t.length] = x; this.n++; }
  retireAvant() { const x = this.t[this.deb]; this.deb = (this.deb + 1) % this.t.length; this.n--; return x; }
  retireArriere() { this.n--; return this.t[(this.deb + this.n) % this.t.length]; }
}
const L = require("fs").readFileSync(0, "utf8").split("\n");
const d = new Deque(), out = [];
for (let i = 1; i <= Number(L[0]); i++) {
  const [c, x] = L[i].trim().split(" ");
  if (c === "AVANT") d.avant(x);
  else if (c === "ARRIERE") d.arriere(x);
  else if (d.n === 0) out.push("vide");
  else out.push(c === "RETIRE_AVANT" ? d.retireAvant() : d.retireArriere());
}
out.push(`taille: ${d.n}`);
console.log(out.join("\n"));""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
$d = new SplDoublyLinkedList();
$out = [];
for ($i = 0; $i < $n; $i++) {
    $p = explode(' ', trim(fgets(STDIN)));
    if ($p[0] === 'AVANT') $d->unshift($p[1]);
    elseif ($p[0] === 'ARRIERE') $d->push($p[1]);
    elseif ($d->isEmpty()) $out[] = 'vide';
    elseif ($p[0] === 'RETIRE_AVANT') $out[] = $d->shift();
    else $out[] = $d->pop();
}
$out[] = 'taille: ' . count($d);
echo implode("\n", $out), "\n";"""}),

    ch("taches", 5, "mini", "Les tâches prioritaires", "tas",
       "Ligne 1 : n (jusqu'à 200 000). Puis n commandes : « AJOUTE nom priorité » ou « SUIVANTE », qui retire et affiche la tâche de plus "
       "haute priorité (à égalité, la plus anciennement ajoutée), ou « rien » s'il n'y en a pas.",
       [_K1, _K2, _KB],
       ["Parcourir toutes les tâches à chaque « SUIVANTE » est trop lent : il faut un tas (file de priorité), O(log n) par opération.",
        "Clé de comparaison : (priorité décroissante, ordre d'arrivée croissant). Numérotez les ajouts pour départager les égalités.",
        "Python : heapq avec (-priorité, numéro, nom). C++ : std::priority_queue. PHP : SplPriorityQueue avec [priorité, -numéro]. En C et en JS, codez le tas."],
       {"python": r"""
import heapq
import sys
L = sys.stdin.read().split("\n")
tas, out = [], []
for i, c in enumerate(L[1:int(L[0]) + 1]):
    p = c.split()
    if p[0] == "AJOUTE":
        heapq.heappush(tas, (-int(p[2]), i, p[1]))
    else:
        out.append(heapq.heappop(tas)[2] if tas else "rien")
print("\n".join(out))""", "c": r"""
#include <stdio.h>
#include <string.h>
typedef struct { int prio, num; char nom[16]; } Tache;
static Tache tas[200005];
static int n_tas = 0;
static int avant(const Tache *a, const Tache *b) { return a->prio != b->prio ? a->prio > b->prio : a->num < b->num; }
static void echange(int i, int j) { Tache t = tas[i]; tas[i] = tas[j]; tas[j] = t; }
static void ajoute(Tache t) {
    int i = n_tas++;
    tas[i] = t;
    while (i > 0 && avant(&tas[i], &tas[(i - 1) / 2])) { echange(i, (i - 1) / 2); i = (i - 1) / 2; }
}
static Tache retire(void) {
    Tache r = tas[0];
    tas[0] = tas[--n_tas];
    int i = 0;
    for (;;) {
        int g = 2 * i + 1, d = g + 1, m = i;
        if (g < n_tas && avant(&tas[g], &tas[m])) m = g;
        if (d < n_tas && avant(&tas[d], &tas[m])) m = d;
        if (m == i) break;
        echange(i, m);
        i = m;
    }
    return r;
}
int main(void) {
    int n;
    char c[16];
    if (scanf("%d", &n) != 1) return 1;
    for (int k = 0; k < n && scanf("%15s", c) == 1; ++k) {
        if (strcmp(c, "AJOUTE") == 0) {
            Tache t;
            t.num = k;
            if (scanf("%15s %d", t.nom, &t.prio) != 2) return 1;
            ajoute(t);
        } else if (n_tas == 0) puts("rien");
        else puts(retire().nom);
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <queue>
#include <string>
#include <tuple>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n;
    std::cin >> n;
    std::priority_queue<std::tuple<int, int, std::string>> tas;   // (priorité, -numéro, nom)
    std::string c, nom;
    int p;
    for (int k = 0; k < n && std::cin >> c; ++k) {
        if (c == "AJOUTE") { std::cin >> nom >> p; tas.emplace(p, -k, nom); }
        else if (tas.empty()) std::cout << "rien\n";
        else { std::cout << std::get<2>(tas.top()) << "\n"; tas.pop(); }
    }
}""", "javascript": r"""
class Tas {
  constructor(avant) { this.t = []; this.avant = avant; }
  get taille() { return this.t.length; }
  ajoute(x) {
    const t = this.t;
    t.push(x);
    let i = t.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (!this.avant(t[i], t[p])) break;
      [t[i], t[p]] = [t[p], t[i]];
      i = p;
    }
  }
  retire() {
    const t = this.t, r = t[0], der = t.pop();
    if (t.length) {
      t[0] = der;
      let i = 0;
      for (;;) {
        const g = 2 * i + 1, d = g + 1;
        let m = i;
        if (g < t.length && this.avant(t[g], t[m])) m = g;
        if (d < t.length && this.avant(t[d], t[m])) m = d;
        if (m === i) break;
        [t[i], t[m]] = [t[m], t[i]];
        i = m;
      }
    }
    return r;
  }
}
const L = require("fs").readFileSync(0, "utf8").split("\n");
const tas = new Tas((a, b) => (a.p !== b.p ? a.p > b.p : a.k < b.k)), out = [];
for (let k = 1; k <= Number(L[0]); k++) {
  const [c, nom, p] = L[k].trim().split(" ");
  if (c === "AJOUTE") tas.ajoute({ nom, p: Number(p), k });
  else out.push(tas.taille ? tas.retire().nom : "rien");
}
console.log(out.join("\n"));""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
$tas = new SplPriorityQueue();
$out = [];
for ($k = 0; $k < $n; $k++) {
    $p = explode(' ', trim(fgets(STDIN)));
    if ($p[0] === 'AJOUTE') $tas->insert($p[1], [(int) $p[2], -$k]);
    else $out[] = $tas->isEmpty() ? 'rien' : $tas->extract();
}
echo implode("\n", $out), "\n";"""}),

    ch("josephus", 5, "mini", "Le cercle de Josèphe", "listes",
       "n personnes, numérotées de 1 à n, sont en cercle. On compte k personnes à partir de la première ; la k-ième sort du cercle, "
       "et on recommence à compter à partir de la suivante. Lisez n (jusqu'à 10 000) et k (jusqu'à 10^9), et affichez l'ordre de sortie.",
       ["7 3", ("1 1", "1"), ("5 1", "1 2 3 4 5"), "6 2", "10 1000000000",
        "10000 7", "10000 123456789"],
       ["Une liste des personnes restantes et un indice courant.", "La personne qui sort est à l'indice (courant + k - 1) modulo le nombre de personnes restantes.",
        "Après l'avoir retirée, l'indice courant pointe déjà sur la suivante. Le modulo évite de compter 10^9 fois."],
       {"python": r"""
n, k = map(int, input().split())
v, i, out = list(range(1, n + 1)), 0, []
while v:
    i = (i + k - 1) % len(v)
    out.append(v.pop(i))
print(*out)""", "c": r"""
#include <stdio.h>
#include <string.h>
int main(void) {
    int n;
    long long k;
    static int v[10005];
    if (scanf("%d %lld", &n, &k) != 2) return 1;
    for (int i = 0; i < n; ++i) v[i] = i + 1;
    int reste = n;
    long long i = 0;
    while (reste > 0) {
        i = (i + k - 1) % reste;
        printf(reste == n ? "%d" : " %d", v[i]);
        memmove(v + i, v + i + 1, sizeof *v * (reste - i - 1));
        --reste;
    }
    printf("\n");
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <vector>
int main() {
    int n;
    long long k;
    std::cin >> n >> k;
    std::vector<int> v;
    for (int i = 1; i <= n; ++i) v.push_back(i);
    long long i = 0;
    bool premier = true;
    while (!v.empty()) {
        i = (i + k - 1) % (long long)v.size();
        std::cout << (premier ? "" : " ") << v[i];
        premier = false;
        v.erase(v.begin() + i);
    }
    std::cout << "\n";
}""", "javascript": r"""
const [n, k] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
const v = Array.from({ length: n }, (_, i) => i + 1), out = [];
let i = 0;
while (v.length) {
  i = (i + ((k - 1) % v.length)) % v.length;
  out.push(v.splice(i, 1)[0]);
}
console.log(out.join(" "));""", "php": r"""
<?php
[$n, $k] = array_map('intval', explode(' ', trim(fgets(STDIN))));
$v = range(1, $n);
$i = 0;
$out = [];
while ($v) {
    $i = ($i + $k - 1) % count($v);
    $out[] = $v[$i];
    array_splice($v, $i, 1);
}
echo implode(' ', $out), "\n";"""}),

    ch("ensembles", 5, "mini", "Opérations sur les ensembles", "ensembles",
       "Ligne 1 : 4 (ignoré). Ligne 2 : les éléments de A. Ligne 3 : ceux de B (des entiers, avec d'éventuels doublons ; une ligne peut être vide). "
       "Affichez « union: … », « inter: … » et « diff: … » (A privé de B), éléments triés et sans doublon, ou « vide ». Jusqu'à 100 000 éléments.",
       [_E1, _E2, _E3, _EB],
       ["Tester l'appartenance en parcourant tout B pour chaque élément de A est en n² : trop lent pour 100 000 éléments.",
        "Un ensemble (set, Set, std::set, clés d'un tableau PHP) répond en temps constant à « x est-il dedans ? ».",
        "En C : triez les deux tableaux, supprimez les doublons, puis fusionnez-les avec deux indices (comme dans le tri fusion)."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
a = {int(x) for x in L[1].split()}
b = {int(x) for x in (L[2] if len(L) > 2 else "").split()}
f = lambda s: " ".join(map(str, sorted(s))) or "vide"
print(f"union: {f(a | b)}")
print(f"inter: {f(a & b)}")
print(f"diff: {f(a - b)}")""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int cmp(const void *x, const void *y) { long long a = *(const long long *)x, b = *(const long long *)y; return (a > b) - (a < b); }
static int lire(char *l, long long *v) {
    int n = 0;
    for (char *t = strtok(l, " \r\n"); t; t = strtok(NULL, " \r\n")) v[n++] = atoll(t);
    qsort(v, n, sizeof *v, cmp);
    int m = 0;
    for (int i = 0; i < n; ++i) if (m == 0 || v[m - 1] != v[i]) v[m++] = v[i];
    return m;
}
static void aff(const char *nom, long long *r, int n) {
    printf("%s:", nom);
    if (n == 0) printf(" vide");
    for (int i = 0; i < n; ++i) printf(" %lld", r[i]);
    printf("\n");
}
int main(void) {
    static char l[1 << 21];
    static long long a[200000], b[200000], u[400000], in[200000], d[200000];
    if (!fgets(l, sizeof l, stdin)) return 1;
    if (!fgets(l, sizeof l, stdin)) l[0] = '\0';
    int na = lire(l, a);
    if (!fgets(l, sizeof l, stdin)) l[0] = '\0';
    int nb = lire(l, b);
    int i = 0, j = 0, nu = 0, ni = 0, nd = 0;
    while (i < na || j < nb) {
        if (j >= nb || (i < na && a[i] < b[j])) { u[nu++] = a[i]; d[nd++] = a[i++]; }
        else if (i >= na || b[j] < a[i]) u[nu++] = b[j++];
        else { u[nu++] = a[i]; in[ni++] = a[i]; ++i; ++j; }
    }
    aff("union", u, nu); aff("inter", in, ni); aff("diff", d, nd);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <set>
#include <sstream>
#include <string>
#include <algorithm>
#include <iterator>
#include <vector>
std::set<long long> lire(const std::string& l) {
    std::istringstream in(l);
    return {std::istream_iterator<long long>(in), std::istream_iterator<long long>()};
}
void aff(const char* nom, const std::vector<long long>& v) {
    std::cout << nom << ":";
    if (v.empty()) std::cout << " vide";
    for (auto x : v) std::cout << " " << x;
    std::cout << "\n";
}
int main() {
    std::string l;
    std::getline(std::cin, l);
    std::getline(std::cin, l);
    auto a = lire(l);
    l.clear();
    std::getline(std::cin, l);
    auto b = lire(l);
    std::vector<long long> u, in, d;
    std::set_union(a.begin(), a.end(), b.begin(), b.end(), std::back_inserter(u));
    std::set_intersection(a.begin(), a.end(), b.begin(), b.end(), std::back_inserter(in));
    std::set_difference(a.begin(), a.end(), b.begin(), b.end(), std::back_inserter(d));
    aff("union", u); aff("inter", in); aff("diff", d);
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const lire = l => new Set((l || "").trim().split(/\s+/).filter(Boolean).map(Number));
const a = lire(L[1]), b = lire(L[2]);
const f = s => [...s].sort((x, y) => x - y).join(" ") || "vide";
console.log(`union: ${f(new Set([...a, ...b]))}`);
console.log(`inter: ${f([...a].filter(x => b.has(x)))}`);
console.log(`diff: ${f([...a].filter(x => !b.has(x)))}`);""", "php": r"""
<?php
fgets(STDIN);
$lire = function () {
    $l = trim((string) fgets(STDIN));
    $s = [];
    if ($l !== '') foreach (preg_split('/\s+/', $l) as $x) $s[(int) $x] = true;
    return $s;
};
$a = $lire();
$b = $lire();
$f = function (array $s) { $k = array_keys($s); sort($k); return $k ? implode(' ', $k) : 'vide'; };
echo "union: ", $f($a + $b), "\ninter: ", $f(array_intersect_key($a, $b)), "\ndiff: ", $f(array_diff_key($a, $b)), "\n";"""}),

    ch("spirale", 5, "mini", "Lecture en spirale", "matrices",
       "Ligne 1 : h et w. Puis une matrice h × w d'entiers. Affichez ses éléments en spirale, sur une seule ligne : la première ligne de gauche "
       "à droite, puis la dernière colonne vers le bas, la dernière ligne de droite à gauche, la première colonne vers le haut, et ainsi de suite vers le centre.",
       [("3 3\n1 2 3\n4 5 6\n7 8 9", "1 2 3 6 9 8 7 4 5"), ("3 4\n1 2 3 4\n5 6 7 8\n9 10 11 12", "1 2 3 4 8 12 11 10 9 5 6 7"), ("1 1\n5", "5"),
        ("1 4\n1 2 3 4", "1 2 3 4"), ("4 1\n1\n2\n3\n4", "1 2 3 4"), ("2 2\n1 2\n3 4", "1 2 4 3"),
        ("20 30\n" + lines(" ".join(map(str, r)) for r in _SP), _spirale(20, 30, _SP))],
       ["Gardez quatre bornes : haut, bas, gauche, droite.", "Parcourez le bord délimité par ces bornes, puis resserrez-les (haut+1, bas-1, gauche+1, droite-1).",
        "Attention aux matrices d'une seule ligne ou colonne : ne repassez pas deux fois sur les mêmes cases (testez haut < bas et gauche < droite)."],
       {"python": r"""
h, w = map(int, input().split())
m = [input().split() for _ in range(h)]
out, t, b, l, r = [], 0, h - 1, 0, w - 1
while t <= b and l <= r:
    out += [m[t][j] for j in range(l, r + 1)]
    out += [m[i][r] for i in range(t + 1, b + 1)]
    if t < b:
        out += [m[b][j] for j in range(r - 1, l - 1, -1)]
    if l < r:
        out += [m[i][l] for i in range(b - 1, t, -1)]
    t, b, l, r = t + 1, b - 1, l + 1, r - 1
print(" ".join(out))""", "c": r"""
#include <stdio.h>
static long long m[200][200];
static int premier = 1;
static void aff(long long x) { printf(premier ? "%lld" : " %lld", x); premier = 0; }
int main(void) {
    int h, w;
    if (scanf("%d %d", &h, &w) != 2) return 1;
    for (int i = 0; i < h; ++i) for (int j = 0; j < w; ++j) if (scanf("%lld", &m[i][j]) != 1) return 1;
    int t = 0, b = h - 1, l = 0, r = w - 1;
    while (t <= b && l <= r) {
        for (int j = l; j <= r; ++j) aff(m[t][j]);
        for (int i = t + 1; i <= b; ++i) aff(m[i][r]);
        if (t < b) for (int j = r - 1; j >= l; --j) aff(m[b][j]);
        if (l < r) for (int i = b - 1; i > t; --i) aff(m[i][l]);
        ++t; --b; ++l; --r;
    }
    printf("\n");
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <vector>
int main() {
    int h, w;
    std::cin >> h >> w;
    std::vector<std::vector<long long>> m(h, std::vector<long long>(w));
    for (auto& row : m) for (auto& x : row) std::cin >> x;
    std::vector<long long> out;
    int t = 0, b = h - 1, l = 0, r = w - 1;
    while (t <= b && l <= r) {
        for (int j = l; j <= r; ++j) out.push_back(m[t][j]);
        for (int i = t + 1; i <= b; ++i) out.push_back(m[i][r]);
        if (t < b) for (int j = r - 1; j >= l; --j) out.push_back(m[b][j]);
        if (l < r) for (int i = b - 1; i > t; --i) out.push_back(m[i][l]);
        ++t; --b; ++l; --r;
    }
    for (size_t i = 0; i < out.size(); ++i) std::cout << (i ? " " : "") << out[i];
    std::cout << "\n";
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const [h, w] = L[0].trim().split(/\s+/).map(Number);
const m = L.slice(1, h + 1).map(l => l.trim().split(/\s+/));
const out = [];
let t = 0, b = h - 1, l = 0, r = w - 1;
while (t <= b && l <= r) {
  for (let j = l; j <= r; j++) out.push(m[t][j]);
  for (let i = t + 1; i <= b; i++) out.push(m[i][r]);
  if (t < b) for (let j = r - 1; j >= l; j--) out.push(m[b][j]);
  if (l < r) for (let i = b - 1; i > t; i--) out.push(m[i][l]);
  t++; b--; l++; r--;
}
console.log(out.join(" "));""", "php": r"""
<?php
[$h, $w] = array_map('intval', explode(' ', trim(fgets(STDIN))));
$m = [];
for ($i = 0; $i < $h; $i++) $m[] = explode(' ', trim(fgets(STDIN)));
$out = [];
[$t, $b, $l, $r] = [0, $h - 1, 0, $w - 1];
while ($t <= $b && $l <= $r) {
    for ($j = $l; $j <= $r; $j++) $out[] = $m[$t][$j];
    for ($i = $t + 1; $i <= $b; $i++) $out[] = $m[$i][$r];
    if ($t < $b) for ($j = $r - 1; $j >= $l; $j--) $out[] = $m[$b][$j];
    if ($l < $r) for ($i = $b - 1; $i > $t; $i--) $out[] = $m[$i][$l];
    $t++; $b--; $l++; $r--;
}
echo implode(' ', $out), "\n";"""}),

    ch("navigateur", 5, "mini", "L'historique du navigateur", "piles",
       "On démarre sur la page « accueil ». Ligne 1 : n. Puis n commandes : « VISITE page », « RETOUR » (page précédente) et « AVANCE » "
       "(annule le dernier retour). Visiter une page efface la possibilité d'avancer. Un retour ou une avance impossible ne fait rien. "
       "Après chaque commande, affichez la page courante.",
       [_N1, _N2, _NB],
       ["Deux piles : les pages derrière (pour RETOUR) et les pages devant (pour AVANCE).",
        "RETOUR : la page courante va sur la pile « devant », la courante devient le sommet de la pile « derrière ». AVANCE : l'inverse.",
        "VISITE : la courante va sur la pile « derrière », et la pile « devant » est vidée."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
cur, derriere, devant, out = "accueil", [], [], []
for c in L[1:int(L[0]) + 1]:
    p = c.split()
    if p[0] == "VISITE":
        derriere.append(cur)
        cur = p[1]
        devant.clear()
    elif p[0] == "RETOUR" and derriere:
        devant.append(cur)
        cur = derriere.pop()
    elif p[0] == "AVANCE" and devant:
        derriere.append(cur)
        cur = devant.pop()
    out.append(cur)
print("\n".join(out))""", "c": r"""
#include <stdio.h>
#include <string.h>
static char derriere[20005][64], devant[20005][64];
int main(void) {
    int n, nd = 0, nv = 0;
    char cur[64] = "accueil", c[16];
    if (scanf("%d", &n) != 1) return 1;
    while (n-- > 0 && scanf("%15s", c) == 1) {
        if (strcmp(c, "VISITE") == 0) {
            strcpy(derriere[nd++], cur);
            if (scanf("%63s", cur) != 1) return 1;
            nv = 0;
        } else if (strcmp(c, "RETOUR") == 0 && nd) { strcpy(devant[nv++], cur); strcpy(cur, derriere[--nd]); }
        else if (strcmp(c, "AVANCE") == 0 && nv) { strcpy(derriere[nd++], cur); strcpy(cur, devant[--nv]); }
        puts(cur);
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <stack>
#include <string>
int main() {
    int n;
    std::cin >> n;
    std::string cur = "accueil", c;
    std::stack<std::string> derriere, devant;
    while (n-- > 0 && std::cin >> c) {
        if (c == "VISITE") { derriere.push(cur); std::cin >> cur; devant = {}; }
        else if (c == "RETOUR" && !derriere.empty()) { devant.push(cur); cur = derriere.top(); derriere.pop(); }
        else if (c == "AVANCE" && !devant.empty()) { derriere.push(cur); cur = devant.top(); devant.pop(); }
        std::cout << cur << "\n";
    }
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
let cur = "accueil", devant = [];
const derriere = [], out = [];
for (let i = 1; i <= Number(L[0]); i++) {
  const [c, page] = L[i].trim().split(" ");
  if (c === "VISITE") { derriere.push(cur); cur = page; devant = []; }
  else if (c === "RETOUR" && derriere.length) { devant.push(cur); cur = derriere.pop(); }
  else if (c === "AVANCE" && devant.length) { derriere.push(cur); cur = devant.pop(); }
  out.push(cur);
}
console.log(out.join("\n"));""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
$cur = 'accueil'; $derriere = []; $devant = []; $out = [];
for ($i = 0; $i < $n; $i++) {
    $p = explode(' ', trim(fgets(STDIN)));
    if ($p[0] === 'VISITE') { $derriere[] = $cur; $cur = $p[1]; $devant = []; }
    elseif ($p[0] === 'RETOUR' && $derriere) { $devant[] = $cur; $cur = array_pop($derriere); }
    elseif ($p[0] === 'AVANCE' && $devant) { $derriere[] = $cur; $cur = array_pop($devant); }
    $out[] = $cur;
}
echo implode("\n", $out), "\n";"""}),

    ch("rpn", 5, "mini", "La calculatrice polonaise", "piles",
       "Ligne 1 : n. Puis n expressions en notation polonaise inverse (« 3 4 + 2 * » vaut 14) : entiers et opérateurs + - * / séparés par "
       "des espaces ; / est la division entière tronquée vers zéro (-7 / 2 = -3). Affichez la valeur de chaque expression, ou « erreur » s'il "
       "manque un opérande, s'il reste plusieurs valeurs à la fin, ou en cas de division par zéro. Les résultats tiennent sur 64 bits.",
       [_RP1, _RP2],
       ["Une pile : un nombre est empilé ; un opérateur dépile deux valeurs b puis a et empile « a op b ».",
        "S'il y a moins de deux valeurs au moment d'un opérateur, c'est une erreur. À la fin, il doit rester exactement une valeur.",
        "Python : // arrondit vers -∞, pas vers zéro ! Calculez abs(a) // abs(b) puis remettez le signe. JavaScript : BigInt (division tronquée)."],
       {"python": r"""
n = int(input())
for _ in range(n):
    pile, ok = [], True
    for t in input().split():
        if t in ("+", "-", "*", "/"):
            if len(pile) < 2:
                ok = False
                break
            b, a = pile.pop(), pile.pop()
            if t == "+":
                pile.append(a + b)
            elif t == "-":
                pile.append(a - b)
            elif t == "*":
                pile.append(a * b)
            elif b == 0:
                ok = False
                break
            else:
                q = abs(a) // abs(b)
                pile.append(q if (a < 0) == (b < 0) else -q)
        else:
            pile.append(int(t))
    print(pile[0] if ok and len(pile) == 1 else "erreur")""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(void) {
    int n;
    char l[4096];
    long long p[2048];
    if (!fgets(l, sizeof l, stdin) || sscanf(l, "%d", &n) != 1) return 1;
    while (n-- > 0) {
        if (!fgets(l, sizeof l, stdin)) l[0] = '\0';
        int t = 0, ok = 1;
        for (char *s = strtok(l, " \r\n"); s && ok; s = strtok(NULL, " \r\n")) {
            if (strlen(s) == 1 && strchr("+-*/", s[0])) {
                if (t < 2) { ok = 0; break; }
                long long b = p[--t], a = p[--t];
                if (s[0] == '/' && b == 0) { ok = 0; break; }
                p[t++] = s[0] == '+' ? a + b : s[0] == '-' ? a - b : s[0] == '*' ? a * b : a / b;
            } else p[t++] = atoll(s);
        }
        if (ok && t == 1) printf("%lld\n", p[0]); else puts("erreur");
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
int main() {
    std::string l;
    std::getline(std::cin, l);
    int n = std::stoi(l);
    while (n-- > 0) {
        std::getline(std::cin, l);
        std::istringstream in(l);
        std::vector<long long> p;
        std::string t;
        bool ok = true;
        while (ok && in >> t) {
            if (t == "+" || t == "-" || t == "*" || t == "/") {
                if (p.size() < 2) { ok = false; break; }
                long long b = p.back(); p.pop_back();
                long long a = p.back(); p.pop_back();
                if (t == "/" && b == 0) { ok = false; break; }
                p.push_back(t == "+" ? a + b : t == "-" ? a - b : t == "*" ? a * b : a / b);
            } else p.push_back(std::stoll(t));
        }
        if (ok && p.size() == 1) std::cout << p[0] << "\n"; else std::cout << "erreur\n";
    }
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const out = [];
for (let k = 1; k <= Number(L[0]); k++) {
  const p = [];
  let ok = true;
  for (const t of (L[k] || "").trim().split(/\s+/).filter(Boolean)) {
    if ("+-*/".includes(t) && t.length === 1) {
      if (p.length < 2) { ok = false; break; }
      const b = p.pop(), a = p.pop();
      if (t === "/" && b === 0n) { ok = false; break; }
      p.push(t === "+" ? a + b : t === "-" ? a - b : t === "*" ? a * b : a / b);
    } else p.push(BigInt(t));
  }
  out.push(ok && p.length === 1 ? p[0].toString() : "erreur");
}
console.log(out.join("\n"));""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
for ($k = 0; $k < $n; $k++) {
    $p = [];
    $ok = true;
    foreach (preg_split('/\s+/', trim((string) fgets(STDIN)), -1, PREG_SPLIT_NO_EMPTY) as $t) {
        if (in_array($t, ['+', '-', '*', '/'], true)) {
            if (count($p) < 2) { $ok = false; break; }
            $b = array_pop($p);
            $a = array_pop($p);
            if ($t === '/' && $b === 0) { $ok = false; break; }
            $p[] = match ($t) { '+' => $a + $b, '-' => $a - $b, '*' => $a * $b, '/' => intdiv($a, $b) };
        } else $p[] = (int) $t;
    }
    echo $ok && count($p) === 1 ? $p[0] : 'erreur', "\n";
}"""}),

    ch("editeur", 5, "exam", "Examen : l'éditeur avec annulation", "piles",
       "Un texte, vide au départ. Ligne 1 : n (jusqu'à 100 000). Puis n commandes : « AJOUTE mot » (ajoute le mot à la fin du texte), "
       "« EFFACE k » (supprime les k derniers caractères, k ne dépasse jamais la longueur), « AFFICHE k » (affiche le k-ième caractère, "
       "en partant de 1) et « ANNULE » (annule la dernière commande AJOUTE ou EFFACE pas encore annulée ; ne fait rien s'il n'y en a pas).",
       [_ED1, _ED2, _EDB],
       ["Recopier tout le texte à chaque commande pour pouvoir l'annuler est bien trop lent sur 100 000 commandes.",
        "Gardez une pile des opérations : pour AJOUTE, sa longueur ; pour EFFACE, le texte effacé.",
        "ANNULE dépile la dernière opération et fait l'inverse : retirer les caractères ajoutés, ou remettre le texte effacé."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
texte, hist, out = [], [], []
for c in L[1:int(L[0]) + 1]:
    p = c.split()
    if p[0] == "AJOUTE":
        texte.extend(p[1])
        hist.append(("A", len(p[1])))
    elif p[0] == "EFFACE":
        k = int(p[1])
        hist.append(("E", texte[len(texte) - k:]))
        del texte[len(texte) - k:]
    elif p[0] == "AFFICHE":
        out.append(texte[int(p[1]) - 1])
    elif hist:
        t, v = hist.pop()
        if t == "A":
            del texte[len(texte) - v:]
        else:
            texte.extend(v)
print("\n".join(out))""", "c": r"""
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
typedef struct { char type; int len; char *efface; } Op;
static char texte[4000000];
static Op hist[200005];
int main(void) {
    int n, t = 0, nh = 0;
    char c[16];
    static char mot[1 << 16];
    if (scanf("%d", &n) != 1) return 1;
    while (n-- > 0 && scanf("%15s", c) == 1) {
        if (strcmp(c, "AJOUTE") == 0) {
            if (scanf("%65535s", mot) != 1) return 1;
            int k = (int)strlen(mot);
            memcpy(texte + t, mot, k);
            t += k;
            hist[nh++] = (Op){'A', k, NULL};
        } else if (strcmp(c, "EFFACE") == 0) {
            int k;
            if (scanf("%d", &k) != 1) return 1;
            char *e = malloc(k + 1);
            memcpy(e, texte + t - k, k);
            t -= k;
            hist[nh++] = (Op){'E', k, e};
        } else if (strcmp(c, "AFFICHE") == 0) {
            int k;
            if (scanf("%d", &k) != 1) return 1;
            printf("%c\n", texte[k - 1]);
        } else if (nh) {
            Op o = hist[--nh];
            if (o.type == 'A') t -= o.len;
            else { memcpy(texte + t, o.efface, o.len); t += o.len; free(o.efface); }
        }
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
#include <vector>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n;
    std::cin >> n;
    std::string texte, c, mot;
    std::vector<std::pair<char, std::string>> hist;   // ('A', mot ajouté) ou ('E', texte effacé)
    while (n-- > 0 && std::cin >> c) {
        if (c == "AJOUTE") { std::cin >> mot; texte += mot; hist.push_back({'A', mot}); }
        else if (c == "EFFACE") {
            size_t k;
            std::cin >> k;
            hist.push_back({'E', texte.substr(texte.size() - k)});
            texte.resize(texte.size() - k);
        } else if (c == "AFFICHE") { size_t k; std::cin >> k; std::cout << texte[k - 1] << "\n"; }
        else if (!hist.empty()) {
            auto [t, s] = hist.back();
            hist.pop_back();
            if (t == 'A') texte.resize(texte.size() - s.size()); else texte += s;
        }
    }
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const texte = [], hist = [], out = [];
for (let i = 1; i <= Number(L[0]); i++) {
  const [c, a] = L[i].trim().split(" ");
  if (c === "AJOUTE") { for (const ch of a) texte.push(ch); hist.push(["A", a.length]); }
  else if (c === "EFFACE") { const k = Number(a); hist.push(["E", texte.splice(texte.length - k, k)]); }
  else if (c === "AFFICHE") out.push(texte[Number(a) - 1]);
  else if (hist.length) {
    const [t, v] = hist.pop();
    if (t === "A") texte.length -= v; else for (const ch of v) texte.push(ch);
  }
}
console.log(out.join("\n"));""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
$texte = '';
$hist = [];
$out = [];
for ($i = 0; $i < $n; $i++) {
    $p = explode(' ', trim(fgets(STDIN)));
    if ($p[0] === 'AJOUTE') { $texte .= $p[1]; $hist[] = ['A', strlen($p[1])]; }
    elseif ($p[0] === 'EFFACE') { $k = (int) $p[1]; $hist[] = ['E', substr($texte, -$k)]; $texte = substr($texte, 0, strlen($texte) - $k); }
    elseif ($p[0] === 'AFFICHE') $out[] = $texte[(int) $p[1] - 1];
    elseif ($hist) {
        [$t, $v] = array_pop($hist);
        if ($t === 'A') $texte = substr($texte, 0, strlen($texte) - $v); else $texte .= $v;
    }
}
echo implode("\n", $out), "\n";"""}, minutes=40),
]
