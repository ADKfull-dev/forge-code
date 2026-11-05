# -*- coding: utf-8 -*-
"""Palier 7 — Modélisation et simulation : objets, états, règles métier, simulations."""
from .base import ch, lines


def _rand(n, lo, hi, seed=1):
    x, out = seed, []
    for _ in range(n):
        x = (x * 6364136223846793005 + 1442695040888963407) % 2 ** 64
        out.append(lo + (x >> 33) % (hi - lo + 1))
    return out


# ---------------------------------------------------------------- entrées générées
def _gen_banque():
    noms = [f"c{i}" for i in range(60)]
    r = _rand(20000, 0, 10 ** 9, 5)
    cmds = []
    for i in range(20000):
        a, b, m = noms[r[i] % 70 % 60] if r[i] % 70 < 60 else f"x{r[i] % 7}", noms[(r[i] >> 7) % 60], (r[i] >> 3) % 5000 - 200
        k = i % 7
        cmds.append([f"OUVRE {a}", f"DEPOT {a} {m}", f"RETRAIT {a} {m}", f"VIREMENT {a} {b} {m}", f"SOLDE {a}", f"DEPOT {a} {m + 300}", f"VIREMENT {b} {b} 5"][k])
    return f"{len(cmds)}\n" + lines(cmds)


def _gen_tournoi():
    eq = ["Lyon", "Paris", "Nantes", "Lille", "Brest", "Nice", "Metz", "Reims", "Lens", "Rennes", "Monaco", "Toulouse"]
    r = _rand(400, 0, 10 ** 6, 9)
    m = []
    for i in range(0, 400, 4):
        a, b = eq[r[i] % 12], eq[r[i + 1] % 12]
        if a != b:
            m.append(f"{a} {r[i + 2] % 5}-{r[i + 3] % 4} {b}")
    return f"{len(m)}\n" + lines(m)


def _gen_vie(h, w, g, seed):
    r = _rand(h * w, 0, 99, seed)
    return f"{h} {w} {g}\n" + lines("".join("#" if r[i * w + j] < 35 else "." for j in range(w)) for i in range(h))


def _gen_robot():
    h, w = 40, 60
    r = _rand(h * w, 0, 99, 21)
    g = [["#" if r[i * w + j] < 18 else "." for j in range(w)] for i in range(h)]
    g[20][30] = "R"
    c = "".join("AAAGADAAGAAAADDA"[x % 16] for x in _rand(5000, 0, 10 ** 6, 23))
    return f"{h} {w}\n" + lines("".join(x) for x in g) + "\n" + c


def _gen_distrib():
    prod = "4\nA1 eau 80 3\nA2 cafe 120 5\nB1 chips 150 2\nB2 barre 95 10"
    c = []
    for x in _rand(3000, 0, 10 ** 6, 29):
        k = x % 10
        c.append(f"PIECE {[10, 20, 50, 100, 200, 5, 100, 50][x % 8]}" if k < 6 else f"CHOIX {['A1', 'A2', 'B1', 'B2', 'C9'][x % 5]}" if k < 9 else "ANNULE")
    return prod + "\n" + lines(c)


def _gen_lru():
    r = _rand(200000, 0, 10 ** 9, 31)
    c = [f"GET {x % 150000}" if x % 3 == 0 else f"PUT {x % 150000} {x % 1000}" for x in r]
    return f"100000 {len(c)}\n" + lines(c)


def _gen_guichets():
    t, out = 0, []
    for a, d in zip(_rand(20000, 0, 3, 37), _rand(20000, 1, 120, 41)):
        t += a
        out.append(f"{t} {d}")
    return "40 20000\n" + lines(out)


def _gen_biblio():
    r = _rand(30000, 0, 10 ** 9, 43)
    c = [f"MEMBRE m{i}" for i in range(30)] + [f"LIVRE L{i}" for i in range(80)] + ["MEMBRE m3", "LIVRE L7"]
    jour = 1
    for x in r:
        jour += x % 3 == 0
        m, l, k = f"m{x % 33}", f"L{(x >> 8) % 85}", (x >> 4) % 10
        c.append(f"EMPRUNTE {m} {l} {jour}" if k < 4 else f"RENDS {m} {l} {jour + (x >> 12) % 25}" if k < 8 else f"PAYE {m} {(x >> 5) % 60}" if k == 8 else f"ETAT {m}")
    return f"{len(c)}\n" + lines(c)


DEFIS = [
    ch("banque", 7, "mini", "La banque", "règles métier",
       "Ligne 1 : n. Puis n opérations : « OUVRE nom », « DEPOT nom m », « RETRAIT nom m », « VIREMENT source destination m », « SOLDE nom » "
       "(montants entiers, en centimes). Réponses : « ok », ou pour SOLDE « nom: solde », ou une erreur, vérifiée dans cet ordre : "
       "« erreur: compte existant » (OUVRE), « erreur: compte inconnu », « erreur: même compte » (virement vers soi-même), "
       "« erreur: montant invalide » (m ≤ 0), « erreur: solde insuffisant ». Une opération en erreur ne change rien.",
       ["9\nOUVRE ana\nOUVRE ana\nDEPOT ana 500\nRETRAIT ana 800\nOUVRE bob\nVIREMENT ana bob 200\nSOLDE ana\nSOLDE bob\nSOLDE eve",
        "5\nOUVRE a\nDEPOT a 0\nDEPOT a -5\nVIREMENT a a 1\nVIREMENT a z 1", _gen_banque],
       ["Un dictionnaire nom → solde modélise la banque.", "Écrivez une fonction par opération ; chacune vérifie ses erreurs dans l'ordre imposé avant de modifier quoi que ce soit.",
        "Pour un virement, vérifiez les DEUX comptes avant tout, et ne débitez que si tout est bon (l'opération est « atomique »)."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
comptes, out = {}, []
for c in L[1:int(L[0]) + 1]:
    p = c.split()
    op = p[0]
    if op == "OUVRE":
        if p[1] in comptes:
            out.append("erreur: compte existant")
        else:
            comptes[p[1]] = 0
            out.append("ok")
        continue
    noms = p[1:3] if op == "VIREMENT" else p[1:2]
    if any(n not in comptes for n in noms):
        out.append("erreur: compte inconnu")
    elif op == "SOLDE":
        out.append(f"{p[1]}: {comptes[p[1]]}")
    elif op == "VIREMENT" and p[1] == p[2]:
        out.append("erreur: même compte")
    else:
        m = int(p[-1])
        if m <= 0:
            out.append("erreur: montant invalide")
        elif op == "DEPOT":
            comptes[p[1]] += m
            out.append("ok")
        elif comptes[p[1]] < m:
            out.append("erreur: solde insuffisant")
        else:
            comptes[p[1]] -= m
            if op == "VIREMENT":
                comptes[p[2]] += m
            out.append("ok")
print("\n".join(out))""", "c": r"""
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
static char noms[5000][32];
static long long solde[5000];
static int nb = 0;
static int cherche(const char *s) { for (int i = 0; i < nb; ++i) if (!strcmp(noms[i], s)) return i; return -1; }
int main(void) {
    int n;
    char op[16], a[32], b[32], m[32];
    if (scanf("%d", &n) != 1) return 1;
    while (n-- > 0 && scanf("%15s %31s", op, a) == 2) {
        int ia = cherche(a), ib = -1;
        long long v = 0;
        if (!strcmp(op, "OUVRE")) {
            if (ia >= 0) puts("erreur: compte existant");
            else { strcpy(noms[nb], a); solde[nb++] = 0; puts("ok"); }
            continue;
        }
        if (!strcmp(op, "VIREMENT")) { if (scanf("%31s", b) != 1) return 1; ib = cherche(b); }
        if (strcmp(op, "SOLDE")) { if (scanf("%31s", m) != 1) return 1; v = atoll(m); }
        if (ia < 0 || (!strcmp(op, "VIREMENT") && ib < 0)) puts("erreur: compte inconnu");
        else if (!strcmp(op, "SOLDE")) printf("%s: %lld\n", a, solde[ia]);
        else if (!strcmp(op, "VIREMENT") && ia == ib) puts("erreur: même compte");
        else if (v <= 0) puts("erreur: montant invalide");
        else if (!strcmp(op, "DEPOT")) { solde[ia] += v; puts("ok"); }
        else if (solde[ia] < v) puts("erreur: solde insuffisant");
        else { solde[ia] -= v; if (ib >= 0) solde[ib] += v; puts("ok"); }
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <map>
#include <string>
class Banque {
    std::map<std::string, long long> comptes;
public:
    std::string ouvre(const std::string& n) {
        if (comptes.count(n)) return "erreur: compte existant";
        comptes[n] = 0;
        return "ok";
    }
    std::string solde(const std::string& n) {
        auto it = comptes.find(n);
        return it == comptes.end() ? "erreur: compte inconnu" : n + ": " + std::to_string(it->second);
    }
    std::string mouvement(const std::string& op, const std::string& a, const std::string& b, long long m) {
        if (!comptes.count(a) || (op == "VIREMENT" && !comptes.count(b))) return "erreur: compte inconnu";
        if (op == "VIREMENT" && a == b) return "erreur: même compte";
        if (m <= 0) return "erreur: montant invalide";
        if (op == "DEPOT") { comptes[a] += m; return "ok"; }
        if (comptes[a] < m) return "erreur: solde insuffisant";
        comptes[a] -= m;
        if (op == "VIREMENT") comptes[b] += m;
        return "ok";
    }
};
int main() {
    int n;
    std::cin >> n;
    Banque banque;
    std::string op, a, b;
    long long m;
    while (n-- > 0 && std::cin >> op >> a) {
        if (op == "OUVRE") std::cout << banque.ouvre(a) << "\n";
        else if (op == "SOLDE") std::cout << banque.solde(a) << "\n";
        else {
            if (op == "VIREMENT") std::cin >> b;
            std::cin >> m;
            std::cout << banque.mouvement(op, a, b, m) << "\n";
        }
    }
}""", "javascript": r"""
class Banque {
  constructor() { this.comptes = new Map(); }
  ouvre(n) {
    if (this.comptes.has(n)) return "erreur: compte existant";
    this.comptes.set(n, 0);
    return "ok";
  }
  solde(n) { return this.comptes.has(n) ? `${n}: ${this.comptes.get(n)}` : "erreur: compte inconnu"; }
  mouvement(op, a, b, m) {
    const c = this.comptes;
    if (!c.has(a) || (op === "VIREMENT" && !c.has(b))) return "erreur: compte inconnu";
    if (op === "VIREMENT" && a === b) return "erreur: même compte";
    if (m <= 0) return "erreur: montant invalide";
    if (op === "DEPOT") { c.set(a, c.get(a) + m); return "ok"; }
    if (c.get(a) < m) return "erreur: solde insuffisant";
    c.set(a, c.get(a) - m);
    if (op === "VIREMENT") c.set(b, c.get(b) + m);
    return "ok";
  }
}
const L = require("fs").readFileSync(0, "utf8").split("\n");
const banque = new Banque(), out = [];
for (let i = 1; i <= Number(L[0]); i++) {
  const p = L[i].trim().split(/\s+/);
  if (p[0] === "OUVRE") out.push(banque.ouvre(p[1]));
  else if (p[0] === "SOLDE") out.push(banque.solde(p[1]));
  else if (p[0] === "VIREMENT") out.push(banque.mouvement("VIREMENT", p[1], p[2], Number(p[3])));
  else out.push(banque.mouvement(p[0], p[1], null, Number(p[2])));
}
console.log(out.join("\n"));""", "php": r"""
<?php
class Banque {
    private array $comptes = [];
    public function ouvre(string $n): string {
        if (isset($this->comptes[$n])) return "erreur: compte existant";
        $this->comptes[$n] = 0;
        return "ok";
    }
    public function solde(string $n): string {
        return isset($this->comptes[$n]) ? "$n: {$this->comptes[$n]}" : "erreur: compte inconnu";
    }
    public function mouvement(string $op, string $a, ?string $b, int $m): string {
        if (!isset($this->comptes[$a]) || ($op === 'VIREMENT' && !isset($this->comptes[$b]))) return "erreur: compte inconnu";
        if ($op === 'VIREMENT' && $a === $b) return "erreur: même compte";
        if ($m <= 0) return "erreur: montant invalide";
        if ($op === 'DEPOT') { $this->comptes[$a] += $m; return "ok"; }
        if ($this->comptes[$a] < $m) return "erreur: solde insuffisant";
        $this->comptes[$a] -= $m;
        if ($op === 'VIREMENT') $this->comptes[$b] += $m;
        return "ok";
    }
}
$n = (int) trim(fgets(STDIN));
$banque = new Banque();
$out = [];
for ($i = 0; $i < $n; $i++) {
    $p = preg_split('/\s+/', trim(fgets(STDIN)));
    $out[] = match ($p[0]) {
        'OUVRE' => $banque->ouvre($p[1]),
        'SOLDE' => $banque->solde($p[1]),
        'VIREMENT' => $banque->mouvement('VIREMENT', $p[1], $p[2], (int) $p[3]),
        default => $banque->mouvement($p[0], $p[1], null, (int) $p[2]),
    };
}
echo implode("\n", $out), "\n";"""}),

    ch("championnat", 7, "mini", "Le classement du championnat", "modélisation",
       "Ligne 1 : n. Puis n matchs « EquipeA a-b EquipeB ». Victoire : 3 points, nul : 1, défaite : 0. Affichez le classement : "
       "« rang. équipe points pts différence buts », la différence avec son signe (+3, +0, -2). Ordre : points, puis différence de buts, "
       "puis buts marqués (décroissants), puis nom (alphabétique). Les ex æquo ont chacun un rang différent (1, 2, 3…).",
       ["3\nLyon 2-0 Paris\nParis 1-1 Nantes\nNantes 0-3 Lyon", "2\nA 1-1 B\nB 0-0 A", _gen_tournoi],
       ["Une structure par équipe : points, buts marqués, buts encaissés (dictionnaire nom → fiche).",
        "Pour chaque match, mettez à jour les deux équipes : buts pour/contre, puis les points selon le résultat.",
        "Triez avec une clé multiple : (-points, -différence, -buts, nom). Le format « %+d » affiche le signe, même pour 0."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
eq = {}
for m in L[1:int(L[0]) + 1]:
    a, score, b = m.split()
    x, y = map(int, score.split("-"))
    for nom, pour, contre in ((a, x, y), (b, y, x)):
        e = eq.setdefault(nom, [0, 0, 0])
        e[0] += 3 if pour > contre else 1 if pour == contre else 0
        e[1] += pour
        e[2] += contre
cl = sorted(eq.items(), key=lambda t: (-t[1][0], -(t[1][1] - t[1][2]), -t[1][1], t[0]))
for i, (nom, (pts, bp, bc)) in enumerate(cl, 1):
    print(f"{i}. {nom} {pts} pts {bp - bc:+d} {bp}")""", "c": r"""
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
typedef struct { char nom[32]; int pts, bp, bc; } Equipe;
static Equipe eq[200];
static int ne = 0;
static Equipe *trouve(const char *n) {
    for (int i = 0; i < ne; ++i) if (!strcmp(eq[i].nom, n)) return &eq[i];
    strcpy(eq[ne].nom, n);
    return &eq[ne++];
}
static void joue(Equipe *e, int pour, int contre) {
    e->pts += pour > contre ? 3 : pour == contre ? 1 : 0;
    e->bp += pour;
    e->bc += contre;
}
static int cmp(const void *x, const void *y) {
    const Equipe *a = x, *b = y;
    if (a->pts != b->pts) return b->pts - a->pts;
    if (a->bp - a->bc != b->bp - b->bc) return (b->bp - b->bc) - (a->bp - a->bc);
    if (a->bp != b->bp) return b->bp - a->bp;
    return strcmp(a->nom, b->nom);
}
int main(void) {
    int n, x, y;
    char a[32], b[32];
    if (scanf("%d", &n) != 1) return 1;
    for (int i = 0; i < n; ++i) {
        if (scanf("%31s %d-%d %31s", a, &x, &y, b) != 4) return 1;
        joue(trouve(a), x, y);
        joue(trouve(b), y, x);
    }
    qsort(eq, ne, sizeof *eq, cmp);
    for (int i = 0; i < ne; ++i) printf("%d. %s %d pts %+d %d\n", i + 1, eq[i].nom, eq[i].pts, eq[i].bp - eq[i].bc, eq[i].bp);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <map>
#include <string>
#include <vector>
#include <algorithm>
#include <cstdio>
struct Equipe {
    std::string nom;
    int pts = 0, bp = 0, bc = 0;
    void joue(int pour, int contre) { pts += pour > contre ? 3 : pour == contre ? 1 : 0; bp += pour; bc += contre; }
    int diff() const { return bp - bc; }
};
int main() {
    int n;
    std::cin >> n;
    std::map<std::string, Equipe> eq;
    for (int i = 0; i < n; ++i) {
        std::string a, s, b;
        std::cin >> a >> s >> b;
        int x = std::stoi(s.substr(0, s.find('-'))), y = std::stoi(s.substr(s.find('-') + 1));
        eq[a].nom = a; eq[a].joue(x, y);
        eq[b].nom = b; eq[b].joue(y, x);
    }
    std::vector<Equipe> v;
    for (auto& [k, e] : eq) v.push_back(e);
    std::sort(v.begin(), v.end(), [](const Equipe& a, const Equipe& b) {
        if (a.pts != b.pts) return a.pts > b.pts;
        if (a.diff() != b.diff()) return a.diff() > b.diff();
        if (a.bp != b.bp) return a.bp > b.bp;
        return a.nom < b.nom;
    });
    for (size_t i = 0; i < v.size(); ++i) std::printf("%zu. %s %d pts %+d %d\n", i + 1, v[i].nom.c_str(), v[i].pts, v[i].diff(), v[i].bp);
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const eq = new Map();
const joue = (nom, pour, contre) => {
  if (!eq.has(nom)) eq.set(nom, { nom, pts: 0, bp: 0, bc: 0 });
  const e = eq.get(nom);
  e.pts += pour > contre ? 3 : pour === contre ? 1 : 0;
  e.bp += pour;
  e.bc += contre;
};
for (let i = 1; i <= Number(L[0]); i++) {
  const [a, s, b] = L[i].trim().split(/\s+/);
  const [x, y] = s.split("-").map(Number);
  joue(a, x, y);
  joue(b, y, x);
}
const v = [...eq.values()].sort((a, b) => b.pts - a.pts || (b.bp - b.bc) - (a.bp - a.bc) || b.bp - a.bp || (a.nom < b.nom ? -1 : 1));
console.log(v.map((e, i) => { const d = e.bp - e.bc; return `${i + 1}. ${e.nom} ${e.pts} pts ${d >= 0 ? "+" : ""}${d} ${e.bp}`; }).join("\n"));""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
$eq = [];
function joue(array &$eq, string $nom, int $pour, int $contre): void {
    $eq[$nom] ??= ['nom' => $nom, 'pts' => 0, 'bp' => 0, 'bc' => 0];
    $eq[$nom]['pts'] += $pour > $contre ? 3 : ($pour === $contre ? 1 : 0);
    $eq[$nom]['bp'] += $pour;
    $eq[$nom]['bc'] += $contre;
}
for ($i = 0; $i < $n; $i++) {
    [$a, $s, $b] = preg_split('/\s+/', trim(fgets(STDIN)));
    [$x, $y] = array_map('intval', explode('-', $s));
    joue($eq, $a, $x, $y);
    joue($eq, $b, $y, $x);
}
$v = array_values($eq);
usort($v, fn($a, $b) => [$b['pts'], $b['bp'] - $b['bc'], $b['bp'], $a['nom']] <=> [$a['pts'], $a['bp'] - $a['bc'], $a['bp'], $b['nom']]);
foreach ($v as $i => $e) printf("%d. %s %d pts %+d %d\n", $i + 1, $e['nom'], $e['pts'], $e['bp'] - $e['bc'], $e['bp']);"""}),

    ch("vie", 7, "mini", "Le jeu de la vie", "simulation",
       "Ligne 1 : h, w et g. Puis h lignes de w caractères (« # » vivante, « . » morte). Appliquez g générations du jeu de la vie de Conway : "
       "une cellule vivante survit si elle a 2 ou 3 voisines vivantes (parmi ses 8 voisines), une morte naît si elle en a exactement 3. "
       "Tout ce qui est hors de la grille est mort. Affichez la grille finale.",
       ["5 5 1\n.....\n..#..\n..#..\n..#..\n.....", "4 4 3\n##..\n##..\n....\n....", "6 6 4\n.#....\n..#...\n###...\n......\n......\n......",
        lambda: _gen_vie(50, 50, 100, 3), lambda: _gen_vie(30, 70, 57, 7)],
       ["Toutes les cellules changent EN MÊME TEMPS : calculez la nouvelle grille dans un second tableau, sans modifier l'ancienne pendant le calcul.",
        "Pour compter les voisines, parcourez les 8 décalages (-1, 0, +1) × (-1, 0, +1) sauf (0, 0), en vérifiant qu'on reste dans la grille.",
        "Après chaque génération, la nouvelle grille remplace l'ancienne."],
       {"python": r"""
h, w, g = map(int, input().split())
grille = [list(input()) for _ in range(h)]
for _ in range(g):
    nouv = [["."] * w for _ in range(h)]
    for i in range(h):
        for j in range(w):
            v = 0
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if (di or dj) and 0 <= i + di < h and 0 <= j + dj < w and grille[i + di][j + dj] == "#":
                        v += 1
            if v == 3 or (v == 2 and grille[i][j] == "#"):
                nouv[i][j] = "#"
    grille = nouv
print("\n".join("".join(r) for r in grille))""", "c": r"""
#include <stdio.h>
#include <string.h>
static char g[2][105][105];
int main(void) {
    int h, w, gen, c = 0;
    if (scanf("%d %d %d", &h, &w, &gen) != 3) return 1;
    for (int i = 0; i < h; ++i) if (scanf("%104s", g[0][i]) != 1) return 1;
    while (gen-- > 0) {
        for (int i = 0; i < h; ++i) {
            for (int j = 0; j < w; ++j) {
                int v = 0;
                for (int di = -1; di <= 1; ++di)
                    for (int dj = -1; dj <= 1; ++dj)
                        if ((di || dj) && i + di >= 0 && i + di < h && j + dj >= 0 && j + dj < w && g[c][i + di][j + dj] == '#') ++v;
                g[1 - c][i][j] = (v == 3 || (v == 2 && g[c][i][j] == '#')) ? '#' : '.';
            }
            g[1 - c][i][w] = '\0';
        }
        c = 1 - c;
    }
    for (int i = 0; i < h; ++i) puts(g[c][i]);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
#include <vector>
int main() {
    int h, w, gen;
    std::cin >> h >> w >> gen;
    std::vector<std::string> g(h);
    for (auto& r : g) std::cin >> r;
    while (gen-- > 0) {
        std::vector<std::string> n(h, std::string(w, '.'));
        for (int i = 0; i < h; ++i)
            for (int j = 0; j < w; ++j) {
                int v = 0;
                for (int di = -1; di <= 1; ++di)
                    for (int dj = -1; dj <= 1; ++dj)
                        if ((di || dj) && i + di >= 0 && i + di < h && j + dj >= 0 && j + dj < w && g[i + di][j + dj] == '#') ++v;
                if (v == 3 || (v == 2 && g[i][j] == '#')) n[i][j] = '#';
            }
        g = n;
    }
    for (auto& r : g) std::cout << r << "\n";
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const [h, w, gen] = L[0].trim().split(/\s+/).map(Number);
let g = L.slice(1, h + 1).map(l => [...l.trim()]);
for (let t = 0; t < gen; t++) {
  const n = g.map(r => r.map(() => "."));
  for (let i = 0; i < h; i++)
    for (let j = 0; j < w; j++) {
      let v = 0;
      for (let di = -1; di <= 1; di++)
        for (let dj = -1; dj <= 1; dj++)
          if ((di || dj) && i + di >= 0 && i + di < h && j + dj >= 0 && j + dj < w && g[i + di][j + dj] === "#") v++;
      if (v === 3 || (v === 2 && g[i][j] === "#")) n[i][j] = "#";
    }
  g = n;
}
console.log(g.map(r => r.join("")).join("\n"));""", "php": r"""
<?php
[$h, $w, $gen] = array_map('intval', explode(' ', trim(fgets(STDIN))));
$g = [];
for ($i = 0; $i < $h; $i++) $g[] = trim(fgets(STDIN));
for ($t = 0; $t < $gen; $t++) {
    $n = [];
    for ($i = 0; $i < $h; $i++) {
        $l = '';
        for ($j = 0; $j < $w; $j++) {
            $v = 0;
            for ($di = -1; $di <= 1; $di++)
                for ($dj = -1; $dj <= 1; $dj++)
                    if (($di || $dj) && $i + $di >= 0 && $i + $di < $h && $j + $dj >= 0 && $j + $dj < $w && $g[$i + $di][$j + $dj] === '#') $v++;
            $l .= ($v === 3 || ($v === 2 && $g[$i][$j] === '#')) ? '#' : '.';
        }
        $n[] = $l;
    }
    $g = $n;
}
echo implode("\n", $g), "\n";"""}, time=3),

    ch("robot", 7, "mini", "Le robot aspirateur", "simulation",
       "Ligne 1 : h et w. Puis la pièce : h lignes de w caractères (« # » obstacle, « . » libre, « R » le robot, qui regarde vers le nord). "
       "Dernière ligne : les ordres, « A » (avancer d'une case), « G » (tourner à gauche), « D » (tourner à droite). Un pas vers un obstacle ou "
       "hors de la pièce est ignoré (le robot est « bloqué »). Affichez « position: ligne colonne » (à partir de 1), « direction: N/E/S/O » et « bloqué: k ».",
       ["3 4\n....\n.R#.\n....\nAADAAA", "1 1\nR\nAGAGAGA", "4 5\n#....\n..#..\n..R..\n.....\nDDAAGAAAAAGG", _gen_robot],
       ["Représentez la direction par un indice 0 à 3 (N, E, S, O) et deux tableaux de décalages : dl = [-1, 0, 1, 0], dc = [0, 1, 0, -1].",
        "Tourner à droite : (d + 1) % 4 ; à gauche : (d + 3) % 4 (évite le modulo négatif).",
        "Avant d'avancer, calculez la case visée et vérifiez qu'elle est dans la pièce et libre ; sinon comptez un blocage."],
       {"python": r"""
h, w = map(int, input().split())
g = [input() for _ in range(h)]
ordres = input().strip()
l, c = next((i, row.index("R")) for i, row in enumerate(g) if "R" in row)
d, bloque = 0, 0
dl, dc = (-1, 0, 1, 0), (0, 1, 0, -1)
for o in ordres:
    if o == "G":
        d = (d + 3) % 4
    elif o == "D":
        d = (d + 1) % 4
    else:
        nl, nc = l + dl[d], c + dc[d]
        if 0 <= nl < h and 0 <= nc < w and g[nl][nc] != "#":
            l, c = nl, nc
        else:
            bloque += 1
print(f"position: {l + 1} {c + 1}")
print(f"direction: {'NESO'[d]}")
print(f"bloqué: {bloque}")""", "c": r"""
#include <stdio.h>
#include <string.h>
static char g[205][205], ordres[100005];
int main(void) {
    int h, w, l = 0, c = 0, d = 0, bloque = 0;
    const int dl[] = {-1, 0, 1, 0}, dc[] = {0, 1, 0, -1};
    if (scanf("%d %d", &h, &w) != 2) return 1;
    for (int i = 0; i < h; ++i) {
        if (scanf("%204s", g[i]) != 1) return 1;
        char *r = strchr(g[i], 'R');
        if (r) { l = i; c = (int)(r - g[i]); }
    }
    if (scanf("%100004s", ordres) != 1) ordres[0] = '\0';
    for (char *o = ordres; *o; ++o) {
        if (*o == 'G') d = (d + 3) % 4;
        else if (*o == 'D') d = (d + 1) % 4;
        else {
            int nl = l + dl[d], nc = c + dc[d];
            if (nl >= 0 && nl < h && nc >= 0 && nc < w && g[nl][nc] != '#') { l = nl; c = nc; }
            else ++bloque;
        }
    }
    printf("position: %d %d\ndirection: %c\nbloqué: %d\n", l + 1, c + 1, "NESO"[d], bloque);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
#include <vector>
struct Robot {
    int l, c, d = 0, bloque = 0;
    void execute(char o, const std::vector<std::string>& g) {
        static const int dl[] = {-1, 0, 1, 0}, dc[] = {0, 1, 0, -1};
        if (o == 'G') d = (d + 3) % 4;
        else if (o == 'D') d = (d + 1) % 4;
        else {
            int nl = l + dl[d], nc = c + dc[d];
            if (nl >= 0 && nl < (int)g.size() && nc >= 0 && nc < (int)g[0].size() && g[nl][nc] != '#') { l = nl; c = nc; }
            else ++bloque;
        }
    }
};
int main() {
    int h, w;
    std::cin >> h >> w;
    std::vector<std::string> g(h);
    Robot r{0, 0};
    for (int i = 0; i < h; ++i) {
        std::cin >> g[i];
        auto p = g[i].find('R');
        if (p != std::string::npos) { r.l = i; r.c = (int)p; }
    }
    std::string ordres;
    std::cin >> ordres;
    for (char o : ordres) r.execute(o, g);
    std::cout << "position: " << r.l + 1 << " " << r.c + 1 << "\ndirection: " << "NESO"[r.d] << "\nbloqué: " << r.bloque << "\n";
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const [h, w] = L[0].trim().split(/\s+/).map(Number);
const g = L.slice(1, h + 1).map(s => s.trim());
const ordres = (L[h + 1] || "").trim();
let l = g.findIndex(r => r.includes("R")), c = g[l].indexOf("R"), d = 0, bloque = 0;
const dl = [-1, 0, 1, 0], dc = [0, 1, 0, -1];
for (const o of ordres) {
  if (o === "G") d = (d + 3) % 4;
  else if (o === "D") d = (d + 1) % 4;
  else {
    const nl = l + dl[d], nc = c + dc[d];
    if (nl >= 0 && nl < h && nc >= 0 && nc < w && g[nl][nc] !== "#") { l = nl; c = nc; }
    else bloque++;
  }
}
console.log(`position: ${l + 1} ${c + 1}\ndirection: ${"NESO"[d]}\nbloqué: ${bloque}`);""", "php": r"""
<?php
[$h, $w] = array_map('intval', explode(' ', trim(fgets(STDIN))));
$g = [];
$l = $c = 0;
for ($i = 0; $i < $h; $i++) {
    $g[] = trim(fgets(STDIN));
    if (($p = strpos($g[$i], 'R')) !== false) { $l = $i; $c = $p; }
}
$ordres = trim((string) fgets(STDIN));
$d = 0; $bloque = 0;
$dl = [-1, 0, 1, 0]; $dc = [0, 1, 0, -1];
for ($k = 0; $k < strlen($ordres); $k++) {
    $o = $ordres[$k];
    if ($o === 'G') $d = ($d + 3) % 4;
    elseif ($o === 'D') $d = ($d + 1) % 4;
    else {
        $nl = $l + $dl[$d]; $nc = $c + $dc[$d];
        if ($nl >= 0 && $nl < $h && $nc >= 0 && $nc < $w && $g[$nl][$nc] !== '#') { $l = $nl; $c = $nc; }
        else $bloque++;
    }
}
echo "position: ", $l + 1, " ", $c + 1, "\ndirection: ", "NESO"[$d], "\nbloqué: $bloque\n";"""}),

    ch("distributeur", 7, "mini", "Le distributeur automatique", "machine à états",
       "Ligne 1 : k, puis k produits « code nom prix stock » (prix en centimes). Ensuite, jusqu'à la fin, des actions : « PIECE v » — acceptée si v "
       "vaut 10, 20, 50, 100 ou 200 (affiche « crédit c »), sinon « pièce refusée v » ; « CHOIX code » — affiche « produit inconnu », « épuisé », "
       "« crédit insuffisant (manque x) » ou « servi nom, rendu r » (le crédit repart à 0) ; « ANNULE » — affiche « rendu c » et remet le crédit à 0.",
       ["2\nA1 eau 80 1\nB2 chips 150 5\nPIECE 50\nCHOIX A1\nPIECE 50\nCHOIX A1\nPIECE 100\nCHOIX A1\nCHOIX Z9\nPIECE 3\nANNULE",
        "1\nX cafe 100 0\nPIECE 200\nCHOIX X\nANNULE\nANNULE", _gen_distrib],
       ["L'état de la machine : le crédit courant et, pour chaque code produit, (nom, prix, stock).",
        "Chaque action est une transition : elle lit l'état, affiche un message et modifie l'état. Traitez-les dans un switch / match.",
        "Vérifiez les cas dans l'ordre de l'énoncé pour CHOIX : inconnu, puis épuisé, puis crédit insuffisant."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
k = int(L[0])
produits = {}
for l in L[1:k + 1]:
    code, nom, prix, stock = l.split()
    produits[code] = [nom, int(prix), int(stock)]
credit, out = 0, []
for l in L[k + 1:]:
    p = l.split()
    if not p:
        continue
    if p[0] == "PIECE":
        v = int(p[1])
        if v in (10, 20, 50, 100, 200):
            credit += v
            out.append(f"crédit {credit}")
        else:
            out.append(f"pièce refusée {v}")
    elif p[0] == "CHOIX":
        pr = produits.get(p[1])
        if not pr:
            out.append("produit inconnu")
        elif pr[2] == 0:
            out.append("épuisé")
        elif credit < pr[1]:
            out.append(f"crédit insuffisant (manque {pr[1] - credit})")
        else:
            pr[2] -= 1
            out.append(f"servi {pr[0]}, rendu {credit - pr[1]}")
            credit = 0
    else:
        out.append(f"rendu {credit}")
        credit = 0
print("\n".join(out))""", "c": r"""
#include <stdio.h>
#include <string.h>
typedef struct { char code[16], nom[32]; int prix, stock; } Produit;
int main(void) {
    int k, credit = 0;
    Produit p[100];
    char a[16], b[16];
    if (scanf("%d", &k) != 1) return 1;
    for (int i = 0; i < k; ++i) if (scanf("%15s %31s %d %d", p[i].code, p[i].nom, &p[i].prix, &p[i].stock) != 4) return 1;
    while (scanf("%15s", a) == 1) {
        if (!strcmp(a, "ANNULE")) { printf("rendu %d\n", credit); credit = 0; continue; }
        if (scanf("%15s", b) != 1) break;
        if (!strcmp(a, "PIECE")) {
            int v;
            sscanf(b, "%d", &v);
            if (v == 10 || v == 20 || v == 50 || v == 100 || v == 200) printf("crédit %d\n", credit += v);
            else printf("pièce refusée %d\n", v);
        } else {
            Produit *q = NULL;
            for (int i = 0; i < k; ++i) if (!strcmp(p[i].code, b)) q = &p[i];
            if (!q) puts("produit inconnu");
            else if (q->stock == 0) puts("épuisé");
            else if (credit < q->prix) printf("crédit insuffisant (manque %d)\n", q->prix - credit);
            else { q->stock--; printf("servi %s, rendu %d\n", q->nom, credit - q->prix); credit = 0; }
        }
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <map>
#include <string>
struct Produit { std::string nom; int prix, stock; };
class Distributeur {
    std::map<std::string, Produit> produits;
    int credit = 0;
public:
    void ajoute(const std::string& code, Produit p) { produits[code] = p; }
    std::string piece(int v) {
        if (v != 10 && v != 20 && v != 50 && v != 100 && v != 200) return "pièce refusée " + std::to_string(v);
        credit += v;
        return "crédit " + std::to_string(credit);
    }
    std::string choix(const std::string& code) {
        auto it = produits.find(code);
        if (it == produits.end()) return "produit inconnu";
        Produit& p = it->second;
        if (p.stock == 0) return "épuisé";
        if (credit < p.prix) return "crédit insuffisant (manque " + std::to_string(p.prix - credit) + ")";
        --p.stock;
        std::string r = "servi " + p.nom + ", rendu " + std::to_string(credit - p.prix);
        credit = 0;
        return r;
    }
    std::string annule() { std::string r = "rendu " + std::to_string(credit); credit = 0; return r; }
};
int main() {
    int k;
    std::cin >> k;
    Distributeur d;
    for (int i = 0; i < k; ++i) { std::string code, nom; int prix, stock; std::cin >> code >> nom >> prix >> stock; d.ajoute(code, {nom, prix, stock}); }
    std::string a, b;
    while (std::cin >> a) {
        if (a == "ANNULE") std::cout << d.annule() << "\n";
        else if (std::cin >> b) std::cout << (a == "PIECE" ? d.piece(std::stoi(b)) : d.choix(b)) << "\n";
    }
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const k = Number(L[0]);
const produits = new Map();
for (let i = 1; i <= k; i++) {
  const [code, nom, prix, stock] = L[i].trim().split(/\s+/);
  produits.set(code, { nom, prix: Number(prix), stock: Number(stock) });
}
let credit = 0;
const out = [];
for (const l of L.slice(k + 1)) {
  const [a, b] = l.trim().split(/\s+/);
  if (!a) continue;
  if (a === "PIECE") {
    const v = Number(b);
    if ([10, 20, 50, 100, 200].includes(v)) out.push(`crédit ${(credit += v)}`);
    else out.push(`pièce refusée ${v}`);
  } else if (a === "CHOIX") {
    const p = produits.get(b);
    if (!p) out.push("produit inconnu");
    else if (p.stock === 0) out.push("épuisé");
    else if (credit < p.prix) out.push(`crédit insuffisant (manque ${p.prix - credit})`);
    else { p.stock--; out.push(`servi ${p.nom}, rendu ${credit - p.prix}`); credit = 0; }
  } else { out.push(`rendu ${credit}`); credit = 0; }
}
console.log(out.join("\n"));""", "php": r"""
<?php
$k = (int) trim(fgets(STDIN));
$produits = [];
for ($i = 0; $i < $k; $i++) {
    [$code, $nom, $prix, $stock] = preg_split('/\s+/', trim(fgets(STDIN)));
    $produits[$code] = ['nom' => $nom, 'prix' => (int) $prix, 'stock' => (int) $stock];
}
$credit = 0;
while (($l = fgets(STDIN)) !== false) {
    $p = preg_split('/\s+/', trim($l));
    if ($p[0] === '') continue;
    if ($p[0] === 'PIECE') {
        $v = (int) $p[1];
        if (in_array($v, [10, 20, 50, 100, 200], true)) { $credit += $v; echo "crédit $credit\n"; }
        else echo "pièce refusée $v\n";
    } elseif ($p[0] === 'CHOIX') {
        $pr = &$produits[$p[1]];
        if ($pr === null) { echo "produit inconnu\n"; unset($produits[$p[1]]); }
        elseif ($pr['stock'] === 0) echo "épuisé\n";
        elseif ($credit < $pr['prix']) echo "crédit insuffisant (manque ", $pr['prix'] - $credit, ")\n";
        else { $pr['stock']--; echo "servi {$pr['nom']}, rendu ", $credit - $pr['prix'], "\n"; $credit = 0; }
        unset($pr);
    } else { echo "rendu $credit\n"; $credit = 0; }
}"""}),

    ch("lru", 7, "mini", "Le cache LRU", "conception de structures",
       "Un cache de capacité c garde des paires clé → valeur. Ligne 1 : c et n (jusqu'à 200 000). Puis n opérations : « GET k » affiche la valeur "
       "de k (ou -1) et en fait la clé la plus récemment utilisée ; « PUT k v » insère ou met à jour k (qui devient la plus récente) — si le cache "
       "dépasse alors c éléments, la clé utilisée il y a le plus longtemps est supprimée. Clés : entiers de 0 à 10^6. Chaque opération en temps constant.",
       ["2 9\nPUT 1 10\nPUT 2 20\nGET 1\nPUT 3 30\nGET 2\nGET 3\nPUT 1 11\nGET 1\nGET 3", "1 4\nPUT 5 1\nPUT 6 2\nGET 5\nGET 6", _gen_lru],
       ["Il faut deux choses à la fois : retrouver une clé vite (dictionnaire) et connaître l'ordre d'utilisation (liste).",
        "Liste doublement chaînée des clés, de la plus récente à la plus ancienne, + dictionnaire clé → nœud : déplacer un nœud en tête coûte O(1).",
        "Raccourcis : Python OrderedDict (move_to_end), JS Map (l'ordre d'insertion : delete puis set), PHP : tableau (unset puis réaffectation, array_key_first)."],
       {"python": r"""
import sys
from collections import OrderedDict
L = sys.stdin.read().split("\n")
cap, n = map(int, L[0].split())
cache, out = OrderedDict(), []
for l in L[1:n + 1]:
    p = l.split()
    k = int(p[1])
    if p[0] == "GET":
        if k in cache:
            cache.move_to_end(k)
            out.append(str(cache[k]))
        else:
            out.append("-1")
    else:
        cache[k] = int(p[2])
        cache.move_to_end(k)
        if len(cache) > cap:
            cache.popitem(last=False)
print("\n".join(out))""", "c": r"""
#include <stdio.h>
#include <string.h>
#define N 1000001
/* liste doublement chaînée indexée par la clé ; TETE est une sentinelle */
static int prec[N + 1], suiv[N + 1], present[N + 1];
static long long val[N + 1];
#define TETE N
static void retire(int k) { suiv[prec[k]] = suiv[k]; prec[suiv[k]] = prec[k]; }
static void en_tete(int k) { prec[k] = TETE; suiv[k] = suiv[TETE]; prec[suiv[TETE]] = k; suiv[TETE] = k; }
int main(void) {
    int cap, n, taille = 0, k;
    char op[8];
    long long v;
    if (scanf("%d %d", &cap, &n) != 2) return 1;
    prec[TETE] = suiv[TETE] = TETE;
    while (n-- > 0 && scanf("%7s %d", op, &k) == 2) {
        if (op[0] == 'G') {
            if (present[k]) { retire(k); en_tete(k); printf("%lld\n", val[k]); }
            else puts("-1");
        } else {
            if (scanf("%lld", &v) != 1) return 1;
            if (present[k]) retire(k); else { present[k] = 1; ++taille; }
            val[k] = v;
            en_tete(k);
            if (taille > cap) { int vieux = prec[TETE]; retire(vieux); present[vieux] = 0; --taille; }
        }
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <list>
#include <string>
#include <unordered_map>
class CacheLRU {
    size_t cap;
    std::list<std::pair<int, long long>> ordre;               // de la plus récente à la plus ancienne
    std::unordered_map<int, std::list<std::pair<int, long long>>::iterator> index;
public:
    explicit CacheLRU(size_t c) : cap(c) {}
    long long get(int k) {
        auto it = index.find(k);
        if (it == index.end()) return -1;
        ordre.splice(ordre.begin(), ordre, it->second);
        return it->second->second;
    }
    void put(int k, long long v) {
        auto it = index.find(k);
        if (it != index.end()) { it->second->second = v; ordre.splice(ordre.begin(), ordre, it->second); return; }
        ordre.emplace_front(k, v);
        index[k] = ordre.begin();
        if (ordre.size() > cap) { index.erase(ordre.back().first); ordre.pop_back(); }
    }
};
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    size_t cap;
    int n, k;
    long long v;
    std::string op;
    std::cin >> cap >> n;
    CacheLRU c(cap);
    while (n-- > 0 && std::cin >> op >> k) {
        if (op == "GET") std::cout << c.get(k) << "\n";
        else { std::cin >> v; c.put(k, v); }
    }
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const [cap, n] = L[0].trim().split(/\s+/).map(Number);
const cache = new Map(), out = [];   // une Map garde l'ordre d'insertion : la première clé est la plus ancienne
for (let i = 1; i <= n; i++) {
  const [op, ks, vs] = L[i].trim().split(" ");
  const k = Number(ks);
  if (op === "GET") {
    if (!cache.has(k)) { out.push(-1); continue; }
    const v = cache.get(k);
    cache.delete(k);
    cache.set(k, v);
    out.push(v);
  } else {
    cache.delete(k);
    cache.set(k, Number(vs));
    if (cache.size > cap) cache.delete(cache.keys().next().value);
  }
}
console.log(out.join("\n"));""", "php": r"""
<?php
[$cap, $n] = array_map('intval', explode(' ', trim(fgets(STDIN))));
$cache = [];
$out = [];
for ($i = 0; $i < $n; $i++) {
    $p = explode(' ', trim(fgets(STDIN)));
    $k = (int) $p[1];
    if ($p[0] === 'GET') {
        if (!isset($cache[$k])) { $out[] = -1; continue; }
        $v = $cache[$k];
        unset($cache[$k]);
        $cache[$k] = $v;
        $out[] = $v;
    } else {
        unset($cache[$k]);
        $cache[$k] = (int) $p[2];
        if (count($cache) > $cap) unset($cache[array_key_first($cache)]);
    }
}
echo implode("\n", $out), "\n";"""}),

    ch("guichets", 7, "mini", "La file d'attente aux guichets", "simulation",
       "Ligne 1 : c guichets et n clients. Puis n lignes « arrivée durée », par arrivées croissantes. Chaque client, dans l'ordre d'arrivée, va au "
       "guichet où il sera servi le plus tôt (à égalité, le guichet de plus petit numéro) ; il attend si nécessaire. Affichez « attente totale: T », "
       "« attente max: M », « fin: F » (heure où le dernier service se termine), puis pour chaque guichet « guichet g: k » (k clients servis).",
       ["2 5\n0 5\n1 3\n2 2\n3 4\n10 1", "1 3\n0 10\n0 10\n0 10", _gen_guichets],
       ["Pour chaque guichet, retenez l'heure à laquelle il sera libre.",
        "Pour un client arrivant à a, le début de service à un guichet libre en f est max(a, f) : choisissez le guichet qui minimise ce début.",
        "Attente = début - arrivée. Mettez ensuite à jour l'heure de libération du guichet choisi : début + durée."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
c, n = map(int, L[0].split())
libre = [0] * c
servis = [0] * c
total = pire = fin = 0
for l in L[1:n + 1]:
    a, d = map(int, l.split())
    g = min(range(c), key=lambda i: (max(a, libre[i]), i))
    debut = max(a, libre[g])
    total += debut - a
    pire = max(pire, debut - a)
    libre[g] = debut + d
    fin = max(fin, libre[g])
    servis[g] += 1
print(f"attente totale: {total}")
print(f"attente max: {pire}")
print(f"fin: {fin}")
for i in range(c):
    print(f"guichet {i + 1}: {servis[i]}")""", "c": r"""
#include <stdio.h>
int main(void) {
    int c, n;
    long long libre[1000] = {0}, total = 0, pire = 0, fin = 0;
    int servis[1000] = {0};
    if (scanf("%d %d", &c, &n) != 2) return 1;
    for (int k = 0; k < n; ++k) {
        long long a, d;
        if (scanf("%lld %lld", &a, &d) != 2) return 1;
        int g = 0;
        long long best = -1;
        for (int i = 0; i < c; ++i) {
            long long deb = libre[i] > a ? libre[i] : a;
            if (best < 0 || deb < best) { best = deb; g = i; }
        }
        total += best - a;
        if (best - a > pire) pire = best - a;
        libre[g] = best + d;
        if (libre[g] > fin) fin = libre[g];
        servis[g]++;
    }
    printf("attente totale: %lld\nattente max: %lld\nfin: %lld\n", total, pire, fin);
    for (int i = 0; i < c; ++i) printf("guichet %d: %d\n", i + 1, servis[i]);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <vector>
#include <algorithm>
int main() {
    int c, n;
    std::cin >> c >> n;
    std::vector<long long> libre(c, 0);
    std::vector<int> servis(c, 0);
    long long total = 0, pire = 0, fin = 0;
    for (int k = 0; k < n; ++k) {
        long long a, d;
        std::cin >> a >> d;
        int g = 0;
        for (int i = 1; i < c; ++i) if (std::max(a, libre[i]) < std::max(a, libre[g])) g = i;
        long long debut = std::max(a, libre[g]);
        total += debut - a;
        pire = std::max(pire, debut - a);
        libre[g] = debut + d;
        fin = std::max(fin, libre[g]);
        ++servis[g];
    }
    std::cout << "attente totale: " << total << "\nattente max: " << pire << "\nfin: " << fin << "\n";
    for (int i = 0; i < c; ++i) std::cout << "guichet " << i + 1 << ": " << servis[i] << "\n";
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const [c, n] = L[0].trim().split(/\s+/).map(Number);
const libre = new Array(c).fill(0), servis = new Array(c).fill(0);
let total = 0, pire = 0, fin = 0;
for (let k = 1; k <= n; k++) {
  const [a, d] = L[k].trim().split(/\s+/).map(Number);
  let g = 0;
  for (let i = 1; i < c; i++) if (Math.max(a, libre[i]) < Math.max(a, libre[g])) g = i;
  const debut = Math.max(a, libre[g]);
  total += debut - a;
  pire = Math.max(pire, debut - a);
  libre[g] = debut + d;
  fin = Math.max(fin, libre[g]);
  servis[g]++;
}
const out = [`attente totale: ${total}`, `attente max: ${pire}`, `fin: ${fin}`];
servis.forEach((s, i) => out.push(`guichet ${i + 1}: ${s}`));
console.log(out.join("\n"));""", "php": r"""
<?php
[$c, $n] = array_map('intval', explode(' ', trim(fgets(STDIN))));
$libre = array_fill(0, $c, 0);
$servis = array_fill(0, $c, 0);
$total = $pire = $fin = 0;
for ($k = 0; $k < $n; $k++) {
    [$a, $d] = array_map('intval', explode(' ', trim(fgets(STDIN))));
    $g = 0;
    for ($i = 1; $i < $c; $i++) if (max($a, $libre[$i]) < max($a, $libre[$g])) $g = $i;
    $debut = max($a, $libre[$g]);
    $total += $debut - $a;
    $pire = max($pire, $debut - $a);
    $libre[$g] = $debut + $d;
    $fin = max($fin, $libre[$g]);
    $servis[$g]++;
}
echo "attente totale: $total\nattente max: $pire\nfin: $fin\n";
foreach ($servis as $i => $s) echo "guichet ", $i + 1, ": $s\n";"""}),

    ch("morpion", 7, "mini", "L'arbitre du morpion", "règles métier",
       "Ligne 1 : t. Puis t grilles de morpion de 3 lignes (« X », « O », « . » pour vide). X joue toujours en premier. Pour chaque grille, affichez "
       "« X gagne », « O gagne », « match nul » (grille pleine sans gagnant), « en cours » ou « invalide » (nombre de coups impossible, deux "
       "gagnants, ou partie qui aurait dû s'arrêter : X aligné alors que O a joué autant que lui, O aligné alors que X a joué un coup de plus).",
       ["4\nXXX\nOO.\n...\nXOX\nXOO\nOXX\nX..\n.O.\n...\nOOO\nXX.\nX..",
        "4\nXXX\nOOO\n...\n...\n...\n...\nXOX\nOXO\nOXO\nXXX\nOOX\nOOX", "5\nOO.\nXX.\n...\nXO.\n.X.\n..O\nXXX\nXOO\nOXO\nX.O\n.XO\n..X\nXX.\nOOO\nX..",
        "1\nXOX\nXOX\nOXO"],
       ["Comptez les X et les O : on doit avoir nx = no (au tour de X) ou nx = no + 1.",
        "Écrivez une fonction « aligne(grille, joueur) » qui teste les 3 lignes, 3 colonnes et 2 diagonales.",
        "Ordre de décision : d'abord les invalidités (comptes, double victoire, victoire incohérente avec les comptes), puis gagnant, puis plein → nul, sinon en cours."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
LIGNES = [[(i, 0), (i, 1), (i, 2)] for i in range(3)] + [[(0, j), (1, j), (2, j)] for j in range(3)] + [[(0, 0), (1, 1), (2, 2)], [(0, 2), (1, 1), (2, 0)]]

def aligne(g, j):
    return any(all(g[a][b] == j for a, b in l) for l in LIGNES)

for t in range(int(L[0])):
    g = L[1 + 3 * t:4 + 3 * t]
    nx = sum(r.count("X") for r in g)
    no = sum(r.count("O") for r in g)
    x, o = aligne(g, "X"), aligne(g, "O")
    if nx not in (no, no + 1) or (x and o) or (x and nx != no + 1) or (o and nx != no):
        print("invalide")
    elif x:
        print("X gagne")
    elif o:
        print("O gagne")
    elif nx + no == 9:
        print("match nul")
    else:
        print("en cours")""", "c": r"""
#include <stdio.h>
static char g[3][8];
static int aligne(char j) {
    for (int i = 0; i < 3; ++i) {
        if (g[i][0] == j && g[i][1] == j && g[i][2] == j) return 1;
        if (g[0][i] == j && g[1][i] == j && g[2][i] == j) return 1;
    }
    return (g[0][0] == j && g[1][1] == j && g[2][2] == j) || (g[0][2] == j && g[1][1] == j && g[2][0] == j);
}
int main(void) {
    int t;
    if (scanf("%d", &t) != 1) return 1;
    while (t-- > 0) {
        int nx = 0, no = 0;
        for (int i = 0; i < 3; ++i) {
            if (scanf("%7s", g[i]) != 1) return 1;
            for (int j = 0; j < 3; ++j) { nx += g[i][j] == 'X'; no += g[i][j] == 'O'; }
        }
        int x = aligne('X'), o = aligne('O');
        if ((nx != no && nx != no + 1) || (x && o) || (x && nx != no + 1) || (o && nx != no)) puts("invalide");
        else if (x) puts("X gagne");
        else if (o) puts("O gagne");
        else if (nx + no == 9) puts("match nul");
        else puts("en cours");
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
#include <array>
using Grille = std::array<std::string, 3>;
bool aligne(const Grille& g, char j) {
    for (int i = 0; i < 3; ++i) {
        if (g[i][0] == j && g[i][1] == j && g[i][2] == j) return true;
        if (g[0][i] == j && g[1][i] == j && g[2][i] == j) return true;
    }
    return (g[0][0] == j && g[1][1] == j && g[2][2] == j) || (g[0][2] == j && g[1][1] == j && g[2][0] == j);
}
std::string arbitre(const Grille& g) {
    int nx = 0, no = 0;
    for (auto& r : g) for (char c : r) { nx += c == 'X'; no += c == 'O'; }
    bool x = aligne(g, 'X'), o = aligne(g, 'O');
    if ((nx != no && nx != no + 1) || (x && o) || (x && nx != no + 1) || (o && nx != no)) return "invalide";
    if (x) return "X gagne";
    if (o) return "O gagne";
    return nx + no == 9 ? "match nul" : "en cours";
}
int main() {
    int t;
    std::cin >> t;
    while (t-- > 0) {
        Grille g;
        for (auto& r : g) std::cin >> r;
        std::cout << arbitre(g) << "\n";
    }
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n").map(l => l.trim());
const LIGNES = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]];
const out = [];
for (let t = 0; t < Number(L[0]); t++) {
  const g = L.slice(1 + 3 * t, 4 + 3 * t).join("");
  const nx = [...g].filter(c => c === "X").length, no = [...g].filter(c => c === "O").length;
  const aligne = j => LIGNES.some(l => l.every(i => g[i] === j));
  const x = aligne("X"), o = aligne("O");
  if ((nx !== no && nx !== no + 1) || (x && o) || (x && nx !== no + 1) || (o && nx !== no)) out.push("invalide");
  else if (x) out.push("X gagne");
  else if (o) out.push("O gagne");
  else out.push(nx + no === 9 ? "match nul" : "en cours");
}
console.log(out.join("\n"));""", "php": r"""
<?php
$t = (int) trim(fgets(STDIN));
$lignes = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]];
for ($k = 0; $k < $t; $k++) {
    $g = trim(fgets(STDIN)) . trim(fgets(STDIN)) . trim(fgets(STDIN));
    $nx = substr_count($g, 'X');
    $no = substr_count($g, 'O');
    $aligne = function (string $j) use ($g, $lignes): bool {
        foreach ($lignes as $l) if ($g[$l[0]] === $j && $g[$l[1]] === $j && $g[$l[2]] === $j) return true;
        return false;
    };
    $x = $aligne('X');
    $o = $aligne('O');
    if (($nx !== $no && $nx !== $no + 1) || ($x && $o) || ($x && $nx !== $no + 1) || ($o && $nx !== $no)) echo "invalide\n";
    elseif ($x) echo "X gagne\n";
    elseif ($o) echo "O gagne\n";
    else echo $nx + $no === 9 ? "match nul\n" : "en cours\n";
}"""}),

    ch("bowling", 7, "mini", "Le score au bowling", "règles métier",
       "Chaque ligne décrit une partie complète : la suite des quilles renversées à chaque lancer. Une partie compte 10 tours (frames) : "
       "un strike (10 au premier lancer) vaut 10 + les deux lancers suivants ; un spare (10 en deux lancers) vaut 10 + le lancer suivant ; "
       "sinon le tour vaut ses quilles. Au 10e tour, un strike ou un spare donne des lancers bonus. Affichez le score de chaque partie.",
       ["10 10 10 10 10 10 10 10 10 10 10 10\n9 0 9 0 9 0 9 0 9 0 9 0 9 0 9 0 9 0 9 0",
        "5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5\n0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0\n10 9 1 5 5 7 2 10 10 10 9 0 8 2 9 1 10\n1 4 4 5 6 4 5 5 10 0 1 7 3 6 4 10 2 8 6",
        "10 10 10 10 10 10 10 10 10 10 9 1\n0 10 10 3 7 10 10 10 10 10 10 10 10 10\n3 4 3 4 3 4 3 4 3 4 3 4 3 4 3 4 3 4 3 4"],
       ["Parcourez les lancers avec un indice i, tour par tour, exactement 10 fois.",
        "Strike : score += 10 + r[i+1] + r[i+2], puis i += 1. Spare : score += 10 + r[i+2], puis i += 2. Sinon : score += r[i] + r[i+1], i += 2.",
        "Les lancers bonus du 10e tour ne sont jamais des tours à part : ils ne servent qu'aux bonus, et la boucle s'arrête après 10 tours."],
       {"python": r"""
import sys
for l in sys.stdin.read().split("\n"):
    if not l.strip():
        continue
    r = list(map(int, l.split()))
    score, i = 0, 0
    for _ in range(10):
        if r[i] == 10:
            score += 10 + r[i + 1] + r[i + 2]
            i += 1
        elif r[i] + r[i + 1] == 10:
            score += 10 + r[i + 2]
            i += 2
        else:
            score += r[i] + r[i + 1]
            i += 2
    print(score)""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(void) {
    char l[1024];
    while (fgets(l, sizeof l, stdin)) {
        int r[32], n = 0;
        for (char *t = strtok(l, " \r\n"); t; t = strtok(NULL, " \r\n")) r[n++] = atoi(t);
        if (n == 0) continue;
        int score = 0, i = 0;
        for (int f = 0; f < 10; ++f) {
            if (r[i] == 10) { score += 10 + r[i + 1] + r[i + 2]; i += 1; }
            else if (r[i] + r[i + 1] == 10) { score += 10 + r[i + 2]; i += 2; }
            else { score += r[i] + r[i + 1]; i += 2; }
        }
        printf("%d\n", score);
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
int score(const std::vector<int>& r) {
    int s = 0;
    size_t i = 0;
    for (int f = 0; f < 10; ++f) {
        if (r[i] == 10) { s += 10 + r[i + 1] + r[i + 2]; i += 1; }
        else if (r[i] + r[i + 1] == 10) { s += 10 + r[i + 2]; i += 2; }
        else { s += r[i] + r[i + 1]; i += 2; }
    }
    return s;
}
int main() {
    std::string l;
    while (std::getline(std::cin, l)) {
        std::istringstream in(l);
        std::vector<int> r;
        int x;
        while (in >> x) r.push_back(x);
        if (!r.empty()) std::cout << score(r) << "\n";
    }
}""", "javascript": r"""
const out = [];
for (const l of require("fs").readFileSync(0, "utf8").split("\n")) {
  if (!l.trim()) continue;
  const r = l.trim().split(/\s+/).map(Number);
  let s = 0, i = 0;
  for (let f = 0; f < 10; f++) {
    if (r[i] === 10) { s += 10 + r[i + 1] + r[i + 2]; i += 1; }
    else if (r[i] + r[i + 1] === 10) { s += 10 + r[i + 2]; i += 2; }
    else { s += r[i] + r[i + 1]; i += 2; }
  }
  out.push(s);
}
console.log(out.join("\n"));""", "php": r"""
<?php
while (($l = fgets(STDIN)) !== false) {
    if (trim($l) === '') continue;
    $r = array_map('intval', preg_split('/\s+/', trim($l)));
    $s = 0; $i = 0;
    for ($f = 0; $f < 10; $f++) {
        if ($r[$i] === 10) { $s += 10 + $r[$i + 1] + $r[$i + 2]; $i += 1; }
        elseif ($r[$i] + $r[$i + 1] === 10) { $s += 10 + $r[$i + 2]; $i += 2; }
        else { $s += $r[$i] + $r[$i + 1]; $i += 2; }
    }
    echo $s, "\n";
}"""}),

    ch("bibliotheque", 7, "exam", "Examen : la bibliothèque", "modélisation",
       "Ligne 1 : n. Puis n commandes. « MEMBRE nom » / « LIVRE code » : « ok » ou « erreur: membre existant » / « erreur: livre existant ». "
       "« EMPRUNTE nom code jour » : erreurs dans l'ordre « membre inconnu », « livre inconnu », « amende impayée » (dette > 0), « livre indisponible » "
       "(déjà emprunté), « limite atteinte » (3 livres), sinon « ok ». « RENDS nom code jour » : erreurs « membre inconnu », « livre inconnu », "
       "« pas emprunté » (pas par ce membre) ; sinon, si le livre est rendu plus de 14 jours après l'emprunt, amende de 10 par jour de retard : "
       "« retard r jour(s), amende a » (ajoutée à la dette), sinon « ok ». « PAYE nom m » : « reste d » (dette jamais négative). "
       "« ETAT nom » : « nom: k livre(s), dette d ». Toutes les erreurs commencent par « erreur: ». Pluriel : « 1 livre », « 2 livres », « 1 jour ».",
       ["12\nMEMBRE ana\nLIVRE L1\nLIVRE L2\nEMPRUNTE ana L1 1\nEMPRUNTE bob L1 1\nEMPRUNTE ana L1 2\nETAT ana\nRENDS ana L1 20\nEMPRUNTE ana L2 21\nPAYE ana 30\nPAYE ana 100\nEMPRUNTE ana L2 22",
        "11\nMEMBRE x\nMEMBRE x\nLIVRE a\nLIVRE b\nLIVRE c\nLIVRE d\nEMPRUNTE x a 1\nEMPRUNTE x b 1\nEMPRUNTE x c 1\nEMPRUNTE x d 1\nRENDS x d 2",
        _gen_biblio],
       ["Modélisez trois choses : les membres (dette, livres empruntés), les livres (emprunteur actuel et jour d'emprunt), et les commandes.",
        "Une fonction par commande, qui vérifie les erreurs dans l'ordre exact de l'énoncé avant de modifier l'état.",
        "Retard = jour du retour - jour de l'emprunt - 14 ; seulement s'il est positif. Attention aux accords : jour/jours, livre/livres."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
membres, livres, out = {}, {}, []   # membres : nom → {"dette", "livres"} ; livres : code → (nom, jour) ou None
for c in L[1:int(L[0]) + 1]:
    p = c.split()
    op = p[0]
    if op == "MEMBRE":
        if p[1] in membres:
            out.append("erreur: membre existant")
        else:
            membres[p[1]] = {"dette": 0, "livres": set()}
            out.append("ok")
    elif op == "LIVRE":
        if p[1] in livres:
            out.append("erreur: livre existant")
        else:
            livres[p[1]] = None
            out.append("ok")
    elif p[1] not in membres:
        out.append("erreur: membre inconnu")
    elif op == "PAYE":
        m = membres[p[1]]
        m["dette"] = max(0, m["dette"] - int(p[2]))
        out.append(f"reste {m['dette']}")
    elif op == "ETAT":
        m = membres[p[1]]
        k = len(m["livres"])
        out.append(f"{p[1]}: {k} livre{'s' if k > 1 else ''}, dette {m['dette']}")
    elif p[2] not in livres:
        out.append("erreur: livre inconnu")
    elif op == "EMPRUNTE":
        m = membres[p[1]]
        if m["dette"] > 0:
            out.append("erreur: amende impayée")
        elif livres[p[2]] is not None:
            out.append("erreur: livre indisponible")
        elif len(m["livres"]) >= 3:
            out.append("erreur: limite atteinte")
        else:
            livres[p[2]] = (p[1], int(p[3]))
            m["livres"].add(p[2])
            out.append("ok")
    else:
        e = livres[p[2]]
        if e is None or e[0] != p[1]:
            out.append("erreur: pas emprunté")
        else:
            m = membres[p[1]]
            livres[p[2]] = None
            m["livres"].discard(p[2])
            r = int(p[3]) - e[1] - 14
            if r > 0:
                m["dette"] += 10 * r
                out.append(f"retard {r} jour{'s' if r > 1 else ''}, amende {10 * r}")
            else:
                out.append("ok")
print("\n".join(out))""", "c": r"""
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
typedef struct { char nom[32]; long long dette; int nb; } Membre;
typedef struct { char code[32]; int emprunteur, jour; } Livre;   /* emprunteur = -1 si disponible */
static Membre mb[2000];
static Livre lv[2000];
static int nm = 0, nl = 0;
static int cherche_m(const char *s) { for (int i = 0; i < nm; ++i) if (!strcmp(mb[i].nom, s)) return i; return -1; }
static int cherche_l(const char *s) { for (int i = 0; i < nl; ++i) if (!strcmp(lv[i].code, s)) return i; return -1; }
int main(void) {
    int n;
    char op[16], a[32], b[32];
    if (scanf("%d", &n) != 1) return 1;
    while (n-- > 0 && scanf("%15s %31s", op, a) == 2) {
        if (!strcmp(op, "MEMBRE")) {
            if (cherche_m(a) >= 0) puts("erreur: membre existant");
            else { strcpy(mb[nm].nom, a); mb[nm].dette = 0; mb[nm++].nb = 0; puts("ok"); }
            continue;
        }
        if (!strcmp(op, "LIVRE")) {
            if (cherche_l(a) >= 0) puts("erreur: livre existant");
            else { strcpy(lv[nl].code, a); lv[nl++].emprunteur = -1; puts("ok"); }
            continue;
        }
        int m = cherche_m(a);
        if (!strcmp(op, "PAYE")) {
            long long v;
            if (scanf("%lld", &v) != 1) return 1;
            if (m < 0) { puts("erreur: membre inconnu"); continue; }
            mb[m].dette = mb[m].dette > v ? mb[m].dette - v : 0;
            printf("reste %lld\n", mb[m].dette);
            continue;
        }
        if (!strcmp(op, "ETAT")) {
            if (m < 0) puts("erreur: membre inconnu");
            else printf("%s: %d livre%s, dette %lld\n", a, mb[m].nb, mb[m].nb > 1 ? "s" : "", mb[m].dette);
            continue;
        }
        int jour;
        if (scanf("%31s %d", b, &jour) != 2) return 1;
        int l = cherche_l(b);
        if (m < 0) { puts("erreur: membre inconnu"); continue; }
        if (l < 0) { puts("erreur: livre inconnu"); continue; }
        if (!strcmp(op, "EMPRUNTE")) {
            if (mb[m].dette > 0) puts("erreur: amende impayée");
            else if (lv[l].emprunteur >= 0) puts("erreur: livre indisponible");
            else if (mb[m].nb >= 3) puts("erreur: limite atteinte");
            else { lv[l].emprunteur = m; lv[l].jour = jour; mb[m].nb++; puts("ok"); }
        } else {
            if (lv[l].emprunteur != m) { puts("erreur: pas emprunté"); continue; }
            lv[l].emprunteur = -1;
            mb[m].nb--;
            int r = jour - lv[l].jour - 14;
            if (r > 0) { mb[m].dette += 10LL * r; printf("retard %d jour%s, amende %d\n", r, r > 1 ? "s" : "", 10 * r); }
            else puts("ok");
        }
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <map>
#include <set>
#include <string>
struct Membre { long long dette = 0; std::set<std::string> livres; };
struct Livre { bool pris = false; std::string par; int jour = 0; };
class Bibliotheque {
    std::map<std::string, Membre> membres;
    std::map<std::string, Livre> livres;
public:
    std::string membre(const std::string& n) { if (membres.count(n)) return "erreur: membre existant"; membres[n]; return "ok"; }
    std::string livre(const std::string& c) { if (livres.count(c)) return "erreur: livre existant"; livres[c]; return "ok"; }
    std::string emprunte(const std::string& n, const std::string& c, int jour) {
        if (!membres.count(n)) return "erreur: membre inconnu";
        if (!livres.count(c)) return "erreur: livre inconnu";
        Membre& m = membres[n];
        Livre& l = livres[c];
        if (m.dette > 0) return "erreur: amende impayée";
        if (l.pris) return "erreur: livre indisponible";
        if (m.livres.size() >= 3) return "erreur: limite atteinte";
        l = {true, n, jour};
        m.livres.insert(c);
        return "ok";
    }
    std::string rends(const std::string& n, const std::string& c, int jour) {
        if (!membres.count(n)) return "erreur: membre inconnu";
        if (!livres.count(c)) return "erreur: livre inconnu";
        Livre& l = livres[c];
        if (!l.pris || l.par != n) return "erreur: pas emprunté";
        Membre& m = membres[n];
        l.pris = false;
        m.livres.erase(c);
        int r = jour - l.jour - 14;
        if (r <= 0) return "ok";
        m.dette += 10LL * r;
        return "retard " + std::to_string(r) + (r > 1 ? " jours" : " jour") + ", amende " + std::to_string(10 * r);
    }
    std::string paye(const std::string& n, long long v) {
        if (!membres.count(n)) return "erreur: membre inconnu";
        Membre& m = membres[n];
        m.dette = m.dette > v ? m.dette - v : 0;
        return "reste " + std::to_string(m.dette);
    }
    std::string etat(const std::string& n) {
        if (!membres.count(n)) return "erreur: membre inconnu";
        Membre& m = membres[n];
        size_t k = m.livres.size();
        return n + ": " + std::to_string(k) + (k > 1 ? " livres" : " livre") + ", dette " + std::to_string(m.dette);
    }
};
int main() {
    int n;
    std::cin >> n;
    Bibliotheque b;
    std::string op, x, y;
    while (n-- > 0 && std::cin >> op >> x) {
        std::string r;
        if (op == "MEMBRE") r = b.membre(x);
        else if (op == "LIVRE") r = b.livre(x);
        else if (op == "ETAT") r = b.etat(x);
        else if (op == "PAYE") { long long v; std::cin >> v; r = b.paye(x, v); }
        else { int j; std::cin >> y >> j; r = op == "EMPRUNTE" ? b.emprunte(x, y, j) : b.rends(x, y, j); }
        std::cout << r << "\n";
    }
}""", "javascript": r"""
class Bibliotheque {
  constructor() { this.membres = new Map(); this.livres = new Map(); }
  membre(n) { if (this.membres.has(n)) return "erreur: membre existant"; this.membres.set(n, { dette: 0, livres: new Set() }); return "ok"; }
  livre(c) { if (this.livres.has(c)) return "erreur: livre existant"; this.livres.set(c, null); return "ok"; }
  emprunte(n, c, jour) {
    if (!this.membres.has(n)) return "erreur: membre inconnu";
    if (!this.livres.has(c)) return "erreur: livre inconnu";
    const m = this.membres.get(n);
    if (m.dette > 0) return "erreur: amende impayée";
    if (this.livres.get(c) !== null) return "erreur: livre indisponible";
    if (m.livres.size >= 3) return "erreur: limite atteinte";
    this.livres.set(c, { par: n, jour });
    m.livres.add(c);
    return "ok";
  }
  rends(n, c, jour) {
    if (!this.membres.has(n)) return "erreur: membre inconnu";
    if (!this.livres.has(c)) return "erreur: livre inconnu";
    const e = this.livres.get(c);
    if (!e || e.par !== n) return "erreur: pas emprunté";
    const m = this.membres.get(n);
    this.livres.set(c, null);
    m.livres.delete(c);
    const r = jour - e.jour - 14;
    if (r <= 0) return "ok";
    m.dette += 10 * r;
    return `retard ${r} jour${r > 1 ? "s" : ""}, amende ${10 * r}`;
  }
  paye(n, v) {
    if (!this.membres.has(n)) return "erreur: membre inconnu";
    const m = this.membres.get(n);
    m.dette = Math.max(0, m.dette - v);
    return `reste ${m.dette}`;
  }
  etat(n) {
    if (!this.membres.has(n)) return "erreur: membre inconnu";
    const m = this.membres.get(n), k = m.livres.size;
    return `${n}: ${k} livre${k > 1 ? "s" : ""}, dette ${m.dette}`;
  }
}
const L = require("fs").readFileSync(0, "utf8").split("\n");
const b = new Bibliotheque(), out = [];
for (let i = 1; i <= Number(L[0]); i++) {
  const [op, x, y, z] = L[i].trim().split(/\s+/);
  if (op === "MEMBRE") out.push(b.membre(x));
  else if (op === "LIVRE") out.push(b.livre(x));
  else if (op === "ETAT") out.push(b.etat(x));
  else if (op === "PAYE") out.push(b.paye(x, Number(y)));
  else if (op === "EMPRUNTE") out.push(b.emprunte(x, y, Number(z)));
  else out.push(b.rends(x, y, Number(z)));
}
console.log(out.join("\n"));""", "php": r"""
<?php
class Bibliotheque {
    private array $membres = [];   // nom => ['dette' => int, 'livres' => [code => true]]
    private array $livres = [];    // code => null ou ['par' => nom, 'jour' => int]
    public function membre(string $n): string {
        if (isset($this->membres[$n])) return "erreur: membre existant";
        $this->membres[$n] = ['dette' => 0, 'livres' => []];
        return "ok";
    }
    public function livre(string $c): string {
        if (array_key_exists($c, $this->livres)) return "erreur: livre existant";
        $this->livres[$c] = null;
        return "ok";
    }
    public function emprunte(string $n, string $c, int $jour): string {
        if (!isset($this->membres[$n])) return "erreur: membre inconnu";
        if (!array_key_exists($c, $this->livres)) return "erreur: livre inconnu";
        $m = &$this->membres[$n];
        if ($m['dette'] > 0) return "erreur: amende impayée";
        if ($this->livres[$c] !== null) return "erreur: livre indisponible";
        if (count($m['livres']) >= 3) return "erreur: limite atteinte";
        $this->livres[$c] = ['par' => $n, 'jour' => $jour];
        $m['livres'][$c] = true;
        return "ok";
    }
    public function rends(string $n, string $c, int $jour): string {
        if (!isset($this->membres[$n])) return "erreur: membre inconnu";
        if (!array_key_exists($c, $this->livres)) return "erreur: livre inconnu";
        $e = $this->livres[$c];
        if ($e === null || $e['par'] !== $n) return "erreur: pas emprunté";
        $m = &$this->membres[$n];
        $this->livres[$c] = null;
        unset($m['livres'][$c]);
        $r = $jour - $e['jour'] - 14;
        if ($r <= 0) return "ok";
        $m['dette'] += 10 * $r;
        return "retard $r jour" . ($r > 1 ? "s" : "") . ", amende " . (10 * $r);
    }
    public function paye(string $n, int $v): string {
        if (!isset($this->membres[$n])) return "erreur: membre inconnu";
        $m = &$this->membres[$n];
        $m['dette'] = max(0, $m['dette'] - $v);
        return "reste {$m['dette']}";
    }
    public function etat(string $n): string {
        if (!isset($this->membres[$n])) return "erreur: membre inconnu";
        $k = count($this->membres[$n]['livres']);
        return "$n: $k livre" . ($k > 1 ? "s" : "") . ", dette {$this->membres[$n]['dette']}";
    }
}
$n = (int) trim(fgets(STDIN));
$b = new Bibliotheque();
$out = [];
for ($i = 0; $i < $n; $i++) {
    $p = preg_split('/\s+/', trim(fgets(STDIN)));
    $out[] = match ($p[0]) {
        'MEMBRE' => $b->membre($p[1]),
        'LIVRE' => $b->livre($p[1]),
        'ETAT' => $b->etat($p[1]),
        'PAYE' => $b->paye($p[1], (int) $p[2]),
        'EMPRUNTE' => $b->emprunte($p[1], $p[2], (int) $p[3]),
        default => $b->rends($p[1], $p[2], (int) $p[3]),
    };
}
echo implode("\n", $out), "\n";"""}, minutes=60),
]
