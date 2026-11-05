# -*- coding: utf-8 -*-
"""Palier 6 — Recherche, tri et complexité : recherche binaire, deux pointeurs, fenêtres, sommes préfixes, O(n log n)."""
from math import isqrt

from .base import ch, lines


def _rand(n, lo, hi, seed=1):
    """Suite pseudo-aléatoire reproductible (générateur congruentiel)."""
    x, out = seed, []
    for _ in range(n):
        x = (x * 6364136223846793005 + 1442695040888963407) % 2 ** 64
        out.append(lo + (x >> 33) % (hi - lo + 1))
    return out


def _j(v):
    return " ".join(map(str, v))


# ---------------------------------------------------------------- tests


def _RB():
    a = sorted(_rand(200000, -10 ** 9, 10 ** 9, 3))
    return f"200000 200000\n{_j(a)}\n{_j(a[i * 7 % 200000] + (i % 3 == 0) for i in range(200000))}"


_R1 = "6 5\n1 3 3 3 7 9\n3 1 9 4 10"
_R2 = "1 3\n5\n5 4 6"
_PB1 = lambda: "200000 0\n" + _j(_rand(200000, -50, 50, 5))
_PB2 = lambda: "200000 1000000000\n" + _j(_rand(200000, 1, 10 ** 9, 7))
_F1 = "6 3\n1 -2 3 10 -4 7"
_F2 = "5 5\n-1 -2 -3 -4 -5"
_FB = lambda: "200000 100000\n" + _j(_rand(200000, -10 ** 9, 10 ** 9, 11))
_Q1 = "5 3\n1 2 3 4 5\n1 5\n2 3\n4 4"
_QB = lambda: "200000 200000\n" + _j(_rand(200000, -10 ** 9, 10 ** 9, 13)) + "\n" + lines(f"{min(a, b)} {max(a, b)}" for a, b in zip(_rand(200000, 1, 200000, 17), _rand(200000, 1, 200000, 19)))
_NOMS = ["lea", "tom", "ines", "hugo", "zoe", "adam", "lina", "noah", "emma", "jade", "leo", "mia"]
_T1 = "5\nzoe 30\nadam 25\nlea 30\nhugo 41\nbob 25"
_T2 = "3\nb 1\na 1\nc 1"
_TB = lambda: "100000\n" + lines(f"{_NOMS[a % 12]}{b} {c}" for a, b, c in zip(_rand(100000, 0, 11, 23), _rand(100000, 0, 999, 29), _rand(100000, 0, 99, 31)))
_I1 = "5\n2 4 1 3 5"
_I2 = "4\n4 3 2 1"
_IB = lambda: "100000\n" + _j(_rand(100000, -10 ** 9, 10 ** 9, 37))
_IB2 = lambda: "100000\n" + _j(range(100000, 0, -1))
_RAC = [0, 1, 2, 3, 4, 15, 16, 17, 999999999999999999, 10 ** 18, 999999998000000001, 999999998000000000, 2 ** 59 + 12345, 123456789012345678]
_K1 = "9\n-2 1 -3 4 -1 2 1 -5 4"
_K2 = "3\n-5 -1 -8"
_KB = lambda: "200000\n" + _j(_rand(200000, -10 ** 9, 10 ** 9, 41))
_S1 = "4\n9 12\n10 11\n11 13\n12 14"
_S2 = "3\n1 2\n2 3\n3 4"
_SB = lambda: "200000\n" + lines(f"{d} {d + l}" for d, l in zip(_rand(200000, 0, 10 ** 9, 43), _rand(200000, 1, 10 ** 5, 47)))

DEFIS = [
    ch("premiers", 6, "mini", "Nombres premiers", "complexité",
       "Lisez n (jusqu'à 5 000 000) et affichez combien il y a de nombres premiers inférieurs ou égaux à n. Limite : 2 secondes.",
       [("10", "4"), ("100", "25"), ("1", "0"), ("2", "1"), ("1000000", "78498"), ("5000000", "348513")],
       ["Tester chaque nombre un par un est trop lent pour 5 millions.",
        "Crible d'Ératosthène : un tableau de booléens, on barre les multiples de chaque nombre premier.", "Commencez à barrer à p × p, et arrêtez quand p × p > n."],
       {"cpp": r"""
#include <iostream>
#include <vector>
int main() {
    int n;
    std::cin >> n;
    if (n < 2) { std::cout << 0 << std::endl; return 0; }
    std::vector<char> p(n + 1, 1);
    p[0] = p[1] = 0;
    for (long long i = 2; i * i <= n; ++i)
        if (p[i]) for (long long j = i * i; j <= n; j += i) p[j] = 0;
    int c = 0;
    for (int i = 2; i <= n; ++i) c += p[i];
    std::cout << c << std::endl;
}""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 1;
    if (n < 2) { puts("0"); return 0; }
    char *p = calloc(n + 1, 1);
    int c = 0;
    for (long long i = 2; i <= n; ++i) {
        if (p[i]) continue;
        ++c;
        for (long long j = i * i; j <= n; j += i) p[j] = 1;
    }
    printf("%d\n", c);
    free(p);
    return 0;
}""", "python": r"""
n = int(input())
if n < 2:
    print(0)
else:
    p = bytearray([1]) * (n + 1)
    p[0] = p[1] = 0
    i = 2
    while i * i <= n:
        if p[i]:
            p[i * i::i] = bytearray(len(range(i * i, n + 1, i)))
        i += 1
    print(sum(p))""", "javascript": r"""
const n = parseInt(require("fs").readFileSync(0, "utf8"), 10);
const p = new Uint8Array(n + 1);
let c = 0;
for (let i = 2; i <= n; i++) {
  if (p[i]) continue;
  c++;
  for (let j = i * i; j <= n; j += i) p[j] = 1;
}
console.log(c);""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
if ($n < 2) { echo "0\n"; exit; }
$p = str_repeat("\1", $n + 1);
$p[0] = $p[1] = "\0";
for ($i = 2; $i * $i <= $n; $i++)
    if ($p[$i] === "\1") for ($j = $i * $i; $j <= $n; $j += $i) $p[$j] = "\0";
echo substr_count($p, "\1"), "\n";"""}),

    ch("recherche", 6, "mini", "Recherche dichotomique", "recherche binaire",
       "Ligne 1 : n et q (jusqu'à 200 000 chacun). Ligne 2 : n entiers triés par ordre croissant (avec répétitions possibles). Ligne 3 : q valeurs "
       "à chercher. Pour chacune, affichez la position (à partir de 1) de sa PREMIÈRE apparition, ou -1. Réponses sur une ligne, séparées par des espaces.",
       [_R1, _R2, _RB],
       ["Parcourir tout le tableau pour chaque question fait 4 × 10^10 opérations : beaucoup trop.",
        "Recherche dichotomique : on compare au milieu de l'intervalle et on garde la bonne moitié. log2(200 000) ≈ 18 étapes.",
        "Pour la première apparition : cherchez le plus petit indice i tel que a[i] ≥ x (borne inférieure), puis vérifiez que a[i] == x."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
a = list(map(int, L[1].split()))
out = []
for x in map(int, L[2].split()):
    lo, hi = 0, len(a)
    while lo < hi:
        m = (lo + hi) // 2
        if a[m] < x:
            lo = m + 1
        else:
            hi = m
    out.append(lo + 1 if lo < len(a) and a[lo] == x else -1)
print(*out)""", "c": r"""
#include <stdio.h>
static long long a[200005];
int main(void) {
    int n, q;
    if (scanf("%d %d", &n, &q) != 2) return 1;
    for (int i = 0; i < n; ++i) if (scanf("%lld", &a[i]) != 1) return 1;
    for (int k = 0; k < q; ++k) {
        long long x;
        if (scanf("%lld", &x) != 1) return 1;
        int lo = 0, hi = n;
        while (lo < hi) {
            int m = lo + (hi - lo) / 2;
            if (a[m] < x) lo = m + 1; else hi = m;
        }
        printf(k ? " %d" : "%d", lo < n && a[lo] == x ? lo + 1 : -1);
    }
    printf("\n");
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <vector>
#include <algorithm>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n, q;
    std::cin >> n >> q;
    std::vector<long long> a(n);
    for (auto& x : a) std::cin >> x;
    for (int k = 0; k < q; ++k) {
        long long x;
        std::cin >> x;
        auto it = std::lower_bound(a.begin(), a.end(), x);
        std::cout << (k ? " " : "") << (it != a.end() && *it == x ? it - a.begin() + 1 : -1);
    }
    std::cout << "\n";
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const a = L[1].trim().split(" ").map(Number), out = [];
for (const s of L[2].trim().split(" ")) {
  const x = Number(s);
  let lo = 0, hi = a.length;
  while (lo < hi) {
    const m = (lo + hi) >> 1;
    if (a[m] < x) lo = m + 1; else hi = m;
  }
  out.push(lo < a.length && a[lo] === x ? lo + 1 : -1);
}
console.log(out.join(" "));""", "php": r"""
<?php
fgets(STDIN);
$a = array_map('intval', explode(' ', trim(fgets(STDIN))));
$n = count($a);
$out = [];
foreach (explode(' ', trim(fgets(STDIN))) as $s) {
    $x = (int) $s;
    $lo = 0; $hi = $n;
    while ($lo < $hi) {
        $m = ($lo + $hi) >> 1;
        if ($a[$m] < $x) $lo = $m + 1; else $hi = $m;
    }
    $out[] = $lo < $n && $a[$lo] === $x ? $lo + 1 : -1;
}
echo implode(' ', $out), "\n";"""}, time=3),

    ch("paires", 6, "mini", "Les paires qui font la somme", "tables de hachage",
       "Ligne 1 : n (jusqu'à 200 000) et une cible S. Ligne 2 : n entiers. Affichez le nombre de paires d'indices i < j telles que a[i] + a[j] = S.",
       [("5 6\n1 5 3 3 2", "2"), ("4 2\n1 1 1 1", "6"), ("3 100\n1 2 3", "0"), ("2 0\n-7 7", "1"), _PB1, _PB2],
       ["Tester toutes les paires fait 2 × 10^10 opérations pour n = 200 000.",
        "Parcourez le tableau une seule fois ; pour chaque x, le nombre de partenaires déjà vus est le nombre de fois où S - x est apparu.",
        "Un dictionnaire valeur → nombre d'apparitions. Le résultat peut dépasser 2 milliards (64 bits). En C : triez puis deux pointeurs."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
s = int(L[0].split()[1])
vu, c = {}, 0
for x in map(int, L[1].split()):
    c += vu.get(s - x, 0)
    vu[x] = vu.get(x, 0) + 1
print(c)""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
static int cmp(const void *x, const void *y) { long long a = *(const long long *)x, b = *(const long long *)y; return (a > b) - (a < b); }
static long long a[200005];
int main(void) {
    int n;
    long long s, c = 0;
    if (scanf("%d %lld", &n, &s) != 2) return 1;
    for (int i = 0; i < n; ++i) if (scanf("%lld", &a[i]) != 1) return 1;
    qsort(a, n, sizeof *a, cmp);
    int i = 0, j = n - 1;
    while (i < j) {
        long long t = a[i] + a[j];
        if (t < s) ++i;
        else if (t > s) --j;
        else if (a[i] == a[j]) { long long k = j - i + 1; c += k * (k - 1) / 2; break; }
        else {
            long long ni = 0, nj = 0;
            long long vi = a[i], vj = a[j];
            while (i <= j && a[i] == vi) { ++i; ++ni; }
            while (j >= i && a[j] == vj) { --j; ++nj; }
            c += ni * nj;
        }
    }
    printf("%lld\n", c);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <unordered_map>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n;
    long long s, c = 0;
    std::cin >> n >> s;
    std::unordered_map<long long, long long> vu;
    vu.reserve(n * 2);
    for (int i = 0; i < n; ++i) {
        long long x;
        std::cin >> x;
        auto it = vu.find(s - x);
        if (it != vu.end()) c += it->second;
        ++vu[x];
    }
    std::cout << c << "\n";
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const s = Number(L[0].trim().split(/\s+/)[1]);
const vu = new Map();
let c = 0;
for (const t of L[1].trim().split(" ")) {
  const x = Number(t);
  c += vu.get(s - x) || 0;
  vu.set(x, (vu.get(x) || 0) + 1);
}
console.log(c);""", "php": r"""
<?php
[, $s] = array_map('intval', explode(' ', trim(fgets(STDIN))));
$vu = [];
$c = 0;
foreach (explode(' ', trim(fgets(STDIN))) as $t) {
    $x = (int) $t;
    $c += $vu[$s - $x] ?? 0;
    $vu[$x] = ($vu[$x] ?? 0) + 1;
}
echo $c, "\n";"""}),

    ch("fenetre", 6, "mini", "La fenêtre glissante", "fenêtre glissante",
       "Ligne 1 : n (jusqu'à 200 000) et k (1 ≤ k ≤ n). Ligne 2 : n entiers. Affichez la plus grande somme de k éléments consécutifs.",
       [_F1, _F2, ("1 1\n-3", "-3"), ("4 1\n3 9 -1 2", "9"), _FB],
       ["Recalculer chaque somme de k éléments coûte n × k opérations : 2 × 10^10 ici.",
        "Passer de la fenêtre [i, i+k) à [i+1, i+k+1) : on ajoute l'élément qui entre et on retire celui qui sort.",
        "Les sommes atteignent 10^14 : 64 bits. Initialisez le maximum avec la première fenêtre, pas avec 0 (tout peut être négatif)."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
k = int(L[0].split()[1])
a = list(map(int, L[1].split()))
s = best = sum(a[:k])
for i in range(k, len(a)):
    s += a[i] - a[i - k]
    if s > best:
        best = s
print(best)""", "c": r"""
#include <stdio.h>
static long long a[200005];
int main(void) {
    int n, k;
    if (scanf("%d %d", &n, &k) != 2) return 1;
    for (int i = 0; i < n; ++i) if (scanf("%lld", &a[i]) != 1) return 1;
    long long s = 0;
    for (int i = 0; i < k; ++i) s += a[i];
    long long best = s;
    for (int i = k; i < n; ++i) { s += a[i] - a[i - k]; if (s > best) best = s; }
    printf("%lld\n", best);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <vector>
#include <algorithm>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n, k;
    std::cin >> n >> k;
    std::vector<long long> a(n);
    for (auto& x : a) std::cin >> x;
    long long s = 0;
    for (int i = 0; i < k; ++i) s += a[i];
    long long best = s;
    for (int i = k; i < n; ++i) { s += a[i] - a[i - k]; best = std::max(best, s); }
    std::cout << best << "\n";
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const k = Number(L[0].trim().split(/\s+/)[1]);
const a = L[1].trim().split(" ").map(Number);
let s = 0;
for (let i = 0; i < k; i++) s += a[i];
let best = s;
for (let i = k; i < a.length; i++) { s += a[i] - a[i - k]; if (s > best) best = s; }
console.log(best);""", "php": r"""
<?php
[, $k] = array_map('intval', explode(' ', trim(fgets(STDIN))));
$a = array_map('intval', explode(' ', trim(fgets(STDIN))));
$s = array_sum(array_slice($a, 0, $k));
$best = $s;
for ($i = $k, $n = count($a); $i < $n; $i++) { $s += $a[$i] - $a[$i - $k]; if ($s > $best) $best = $s; }
echo $best, "\n";"""}),

    ch("prefixes", 6, "mini", "Sommes sur des intervalles", "sommes préfixes",
       "Ligne 1 : n et q (jusqu'à 200 000). Ligne 2 : n entiers. Puis q lignes « l r » (1 ≤ l ≤ r ≤ n). Pour chacune, affichez la somme des "
       "éléments de la position l à la position r incluses.",
       [_Q1, ("1 1\n-5\n1 1", "-5"), _QB],
       ["Additionner l'intervalle à chaque question peut coûter 200 000 × 200 000 opérations.",
        "Précalculez P[i] = somme des i premiers éléments (P[0] = 0, P[i] = P[i-1] + a[i]).",
        "La somme de l à r vaut alors P[r] - P[l-1] : une seule soustraction par question. Pensez 64 bits."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
n, q = map(int, L[0].split())
p = [0]
for x in map(int, L[1].split()):
    p.append(p[-1] + x)
out = []
for i in range(2, 2 + q):
    l, r = map(int, L[i].split())
    out.append(p[r] - p[l - 1])
print("\n".join(map(str, out)))""", "c": r"""
#include <stdio.h>
static long long p[200005];
int main(void) {
    int n, q;
    if (scanf("%d %d", &n, &q) != 2) return 1;
    for (int i = 1; i <= n; ++i) { long long x; if (scanf("%lld", &x) != 1) return 1; p[i] = p[i - 1] + x; }
    while (q-- > 0) {
        int l, r;
        if (scanf("%d %d", &l, &r) != 2) return 1;
        printf("%lld\n", p[r] - p[l - 1]);
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <vector>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n, q;
    std::cin >> n >> q;
    std::vector<long long> p(n + 1, 0);
    for (int i = 1; i <= n; ++i) { long long x; std::cin >> x; p[i] = p[i - 1] + x; }
    while (q-- > 0) { int l, r; std::cin >> l >> r; std::cout << p[r] - p[l - 1] << "\n"; }
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const q = Number(L[0].trim().split(/\s+/)[1]);
const a = L[1].trim().split(" ").map(Number);
const p = new Float64Array(a.length + 1);
for (let i = 0; i < a.length; i++) p[i + 1] = p[i] + a[i];
const out = [];
for (let i = 2; i < 2 + q; i++) {
  const [l, r] = L[i].split(" ").map(Number);
  out.push(p[r] - p[l - 1]);
}
console.log(out.join("\n"));""", "php": r"""
<?php
[$n, $q] = array_map('intval', explode(' ', trim(fgets(STDIN))));
$p = [0];
foreach (explode(' ', trim(fgets(STDIN))) as $i => $x) $p[] = $p[$i] + (int) $x;
$out = [];
for ($k = 0; $k < $q; $k++) {
    [$l, $r] = explode(' ', trim(fgets(STDIN)));
    $out[] = $p[(int) $r] - $p[(int) $l - 1];
}
echo implode("\n", $out), "\n";"""}),

    ch("tri-perso", 6, "mini", "Le classement", "tri personnalisé",
       "Ligne 1 : n (jusqu'à 100 000). Puis n lignes « nom âge ». Affichez-les triés par âge décroissant, puis, à âge égal, par nom dans l'ordre "
       "alphabétique (ordre des codes ASCII), au même format.",
       [_T1, _T2, ("1\nsolo 7", "solo 7"), _TB],
       ["Les fonctions de tri acceptent une fonction de comparaison (ou une clé) : c'est elle qui définit l'ordre.",
        "Comparez d'abord les âges (le plus grand avant), et seulement s'ils sont égaux, les noms.",
        "Python : key=lambda p: (-age, nom). JS : sort((a, b) => b.age - a.age || (a.nom < b.nom ? -1 : 1)). C : qsort avec strcmp. PHP : usort avec <=>."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
v = []
for x in L[1:int(L[0]) + 1]:
    nom, age = x.split()
    v.append((nom, int(age)))
v.sort(key=lambda p: (-p[1], p[0]))
print("\n".join(f"{n} {a}" for n, a in v))""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct { char nom[32]; int age; } Pers;
static Pers v[100005];
static int cmp(const void *x, const void *y) {
    const Pers *a = x, *b = y;
    if (a->age != b->age) return b->age - a->age;
    return strcmp(a->nom, b->nom);
}
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 1;
    for (int i = 0; i < n; ++i) if (scanf("%31s %d", v[i].nom, &v[i].age) != 2) return 1;
    qsort(v, n, sizeof *v, cmp);
    for (int i = 0; i < n; ++i) printf("%s %d\n", v[i].nom, v[i].age);
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
    std::vector<std::pair<std::string, int>> v(n);
    for (auto& [nom, age] : v) std::cin >> nom >> age;
    std::sort(v.begin(), v.end(), [](const auto& a, const auto& b) {
        return a.second != b.second ? a.second > b.second : a.first < b.first;
    });
    for (auto& [nom, age] : v) std::cout << nom << " " << age << "\n";
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const v = L.slice(1, Number(L[0]) + 1).map(l => { const [nom, age] = l.trim().split(" "); return { nom, age: Number(age) }; });
v.sort((a, b) => b.age - a.age || (a.nom < b.nom ? -1 : a.nom > b.nom ? 1 : 0));
console.log(v.map(p => `${p.nom} ${p.age}`).join("\n"));""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
$v = [];
for ($i = 0; $i < $n; $i++) { [$nom, $age] = explode(' ', trim(fgets(STDIN))); $v[] = [$nom, (int) $age]; }
usort($v, fn($a, $b) => [$b[1], $a[0]] <=> [$a[1], $b[0]]);
echo implode("\n", array_map(fn($p) => "$p[0] $p[1]", $v)), "\n";"""}, time=3),

    ch("inversions", 6, "mini", "Compter les inversions", "diviser pour régner",
       "Ligne 1 : n (jusqu'à 100 000). Ligne 2 : n entiers. Une inversion est une paire d'indices i < j avec a[i] > a[j]. Affichez leur nombre.",
       [_I1, _I2, ("1\n7", "0"), ("3\n5 5 5", "0"), _IB, _IB2],
       ["Tester toutes les paires est en n² : 5 × 10^9 comparaisons pour n = 100 000.",
        "Tri fusion : pendant la fusion de deux moitiés triées, quand un élément de droite passe devant, il est plus petit que TOUS les éléments restants à gauche.",
        "Ajoutez alors le nombre d'éléments restants à gauche au compteur. Total : O(n log n). Le résultat dépasse 2^31 : 64 bits."],
       {"python": r"""
import sys
sys.setrecursionlimit(10000)

def fusion(v):
    if len(v) < 2:
        return v, 0
    m = len(v) // 2
    g, x = fusion(v[:m])
    d, y = fusion(v[m:])
    r, i, j, c = [], 0, 0, x + y
    while i < len(g) and j < len(d):
        if d[j] < g[i]:
            r.append(d[j])
            c += len(g) - i
            j += 1
        else:
            r.append(g[i])
            i += 1
    r.extend(g[i:])
    r.extend(d[j:])
    return r, c

L = sys.stdin.read().split("\n")
print(fusion(list(map(int, L[1].split())))[1])""", "c": r"""
#include <stdio.h>
static long long a[100005], tmp[100005];
static long long tri(int lo, int hi) {
    if (hi - lo < 2) return 0;
    int m = (lo + hi) / 2;
    long long c = tri(lo, m) + tri(m, hi);
    int i = lo, j = m, k = lo;
    while (i < m && j < hi) {
        if (a[j] < a[i]) { tmp[k++] = a[j++]; c += m - i; }
        else tmp[k++] = a[i++];
    }
    while (i < m) tmp[k++] = a[i++];
    while (j < hi) tmp[k++] = a[j++];
    for (k = lo; k < hi; ++k) a[k] = tmp[k];
    return c;
}
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 1;
    for (int i = 0; i < n; ++i) if (scanf("%lld", &a[i]) != 1) return 1;
    printf("%lld\n", tri(0, n));
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <vector>
std::vector<long long> a, tmp;
long long tri(int lo, int hi) {
    if (hi - lo < 2) return 0;
    int m = (lo + hi) / 2;
    long long c = tri(lo, m) + tri(m, hi);
    int i = lo, j = m, k = lo;
    while (i < m && j < hi) {
        if (a[j] < a[i]) { tmp[k++] = a[j++]; c += m - i; }
        else tmp[k++] = a[i++];
    }
    while (i < m) tmp[k++] = a[i++];
    while (j < hi) tmp[k++] = a[j++];
    for (k = lo; k < hi; ++k) a[k] = tmp[k];
    return c;
}
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n;
    std::cin >> n;
    a.resize(n);
    tmp.resize(n);
    for (auto& x : a) std::cin >> x;
    std::cout << tri(0, n) << "\n";
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const a = L[1].trim().split(" ").map(Number), tmp = new Array(a.length);
const tri = (lo, hi) => {
  if (hi - lo < 2) return 0;
  const m = (lo + hi) >> 1;
  let c = tri(lo, m) + tri(m, hi), i = lo, j = m, k = lo;
  while (i < m && j < hi) {
    if (a[j] < a[i]) { tmp[k++] = a[j++]; c += m - i; }
    else tmp[k++] = a[i++];
  }
  while (i < m) tmp[k++] = a[i++];
  while (j < hi) tmp[k++] = a[j++];
  for (k = lo; k < hi; k++) a[k] = tmp[k];
  return c;
};
console.log(tri(0, a.length));""", "php": r"""
<?php
fgets(STDIN);
$a = array_map('intval', explode(' ', trim(fgets(STDIN))));
$tmp = $a;
function tri(array &$a, array &$tmp, int $lo, int $hi): int {
    if ($hi - $lo < 2) return 0;
    $m = ($lo + $hi) >> 1;
    $c = tri($a, $tmp, $lo, $m) + tri($a, $tmp, $m, $hi);
    $i = $lo; $j = $m; $k = $lo;
    while ($i < $m && $j < $hi) {
        if ($a[$j] < $a[$i]) { $tmp[$k++] = $a[$j++]; $c += $m - $i; }
        else $tmp[$k++] = $a[$i++];
    }
    while ($i < $m) $tmp[$k++] = $a[$i++];
    while ($j < $hi) $tmp[$k++] = $a[$j++];
    for ($k = $lo; $k < $hi; $k++) $a[$k] = $tmp[$k];
    return $c;
}
echo tri($a, $tmp, 0, count($a)), "\n";"""}),

    ch("racine", 6, "mini", "Racine carrée entière", "recherche binaire",
       "Ligne 1 : t. Puis t entiers n (0 ≤ n ≤ 10^18). Pour chacun, affichez ⌊√n⌋, le plus grand entier r tel que r × r ≤ n. "
       "Attention : la racine des nombres à virgule n'est pas assez précise pour de si grands nombres.",
       [("4\n16\n17\n0\n1", "4\n4\n0\n1"), ("2\n999999999999999999\n1000000000000000000", "999999999\n1000000000"),
        (f"{len(_RAC)}\n" + lines(_RAC), lines(isqrt(x) for x in _RAC))],
       ["sqrt(999999999999999999) en double vaut exactement 10^9 : c'est faux d'une unité !",
        "Recherche dichotomique sur r entre 0 et 10^9 + 1 : si r × r ≤ n, la réponse est au moins r ; sinon elle est plus petite.",
        "r × r atteint 10^18 : entier 64 bits (BigInt en JavaScript). Autre méthode : partir de sqrt() et corriger d'une unité dans chaque sens."],
       {"python": r"""
t = int(input())
for _ in range(t):
    n = int(input())
    lo, hi = 0, 10 ** 9 + 1
    while lo < hi:
        m = (lo + hi + 1) // 2
        if m * m <= n:
            lo = m
        else:
            hi = m - 1
    print(lo)""", "c": r"""
#include <stdio.h>
int main(void) {
    int t;
    if (scanf("%d", &t) != 1) return 1;
    while (t-- > 0) {
        long long n;
        if (scanf("%lld", &n) != 1) return 1;
        long long lo = 0, hi = 1000000001LL;
        while (lo < hi) {
            long long m = (lo + hi + 1) / 2;
            if (m * m <= n) lo = m; else hi = m - 1;
        }
        printf("%lld\n", lo);
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
int main() {
    int t;
    std::cin >> t;
    while (t-- > 0) {
        long long n;
        std::cin >> n;
        long long lo = 0, hi = 1000000001LL;
        while (lo < hi) {
            long long m = (lo + hi + 1) / 2;
            if (m * m <= n) lo = m; else hi = m - 1;
        }
        std::cout << lo << "\n";
    }
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").trim().split(/\s+/);
const out = [];
for (let i = 1; i <= Number(L[0]); i++) {
  const n = BigInt(L[i]);
  let lo = 0n, hi = 1000000001n;
  while (lo < hi) {
    const m = (lo + hi + 1n) / 2n;
    if (m * m <= n) lo = m; else hi = m - 1n;
  }
  out.push(lo.toString());
}
console.log(out.join("\n"));""", "php": r"""
<?php
$t = (int) trim(fgets(STDIN));
for ($k = 0; $k < $t; $k++) {
    $n = (int) trim(fgets(STDIN));
    $lo = 0; $hi = 1000000001;
    while ($lo < $hi) {
        $m = intdiv($lo + $hi + 1, 2);
        if ($m * $m <= $n) $lo = $m; else $hi = $m - 1;
    }
    echo $lo, "\n";
}"""}, banned={"python": [r"isqrt"]}),

    ch("kadane", 6, "mini", "Le meilleur sous-tableau", "programmation linéaire",
       "Ligne 1 : n (jusqu'à 200 000). Ligne 2 : n entiers. Affichez la plus grande somme d'une suite non vide d'éléments CONSÉCUTIFS.",
       [_K1, _K2, ("1\n0", "0"), ("5\n1 2 3 4 5", "15"), _KB],
       ["Essayer tous les couples (début, fin) coûte n² ou n³ : trop lent.",
        "Algorithme de Kadane : parcourez le tableau en gardant la meilleure somme d'une suite qui SE TERMINE à la position courante.",
        "À chaque x : courant = max(x, courant + x) (on prolonge ou on repart de zéro), meilleur = max(meilleur, courant). Tout peut être négatif."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
a = list(map(int, L[1].split()))
best = cur = a[0]
for x in a[1:]:
    cur = x if cur < 0 else cur + x
    if cur > best:
        best = cur
print(best)""", "c": r"""
#include <stdio.h>
int main(void) {
    int n;
    long long x;
    if (scanf("%d %lld", &n, &x) != 2) return 1;
    long long best = x, cur = x;
    for (int i = 1; i < n; ++i) {
        if (scanf("%lld", &x) != 1) return 1;
        cur = cur < 0 ? x : cur + x;
        if (cur > best) best = cur;
    }
    printf("%lld\n", best);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <algorithm>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n;
    long long x;
    std::cin >> n >> x;
    long long best = x, cur = x;
    for (int i = 1; i < n; ++i) {
        std::cin >> x;
        cur = std::max(x, cur + x);
        best = std::max(best, cur);
    }
    std::cout << best << "\n";
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const a = L[1].trim().split(" ").map(Number);
let best = a[0], cur = a[0];
for (let i = 1; i < a.length; i++) {
  cur = Math.max(a[i], cur + a[i]);
  if (cur > best) best = cur;
}
console.log(best);""", "php": r"""
<?php
fgets(STDIN);
$a = array_map('intval', explode(' ', trim(fgets(STDIN))));
$best = $cur = $a[0];
for ($i = 1, $n = count($a); $i < $n; $i++) {
    $cur = $cur < 0 ? $a[$i] : $cur + $a[$i];
    if ($cur > $best) $best = $cur;
}
echo $best, "\n";"""}),

    ch("salles", 6, "exam", "Examen : le planning des salles", "tri et balayage",
       "Ligne 1 : n (jusqu'à 200 000). Puis n réunions « début fin » (entiers, début < fin) ; une réunion occupe une salle de début "
       "inclus à fin exclue (une réunion qui finit à 10 libère sa salle pour une qui commence à 10). Affichez le nombre minimal de salles.",
       [_S1, _S2, ("1\n0 1", "1"), ("3\n0 10\n0 10\n0 10", "3"), _SB],
       ["Le nombre de salles nécessaires est le nombre maximal de réunions en cours au même instant.",
        "Transformez chaque réunion en deux événements : (début, +1) et (fin, -1). Triez-les par instant, en plaçant les fins AVANT les débuts à instant égal.",
        "Parcourez les événements triés en tenant le compte des réunions en cours : le maximum atteint est la réponse. O(n log n)."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
ev = []
for x in L[1:int(L[0]) + 1]:
    d, f = map(int, x.split())
    ev.append((d, 1))
    ev.append((f, -1))
ev.sort()
cur = best = 0
for _, t in ev:
    cur += t
    best = max(best, cur)
print(best)""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
typedef struct { long long t; int d; } Ev;
static Ev ev[400005];
static int cmp(const void *x, const void *y) {
    const Ev *a = x, *b = y;
    if (a->t != b->t) return (a->t > b->t) - (a->t < b->t);
    return a->d - b->d;
}
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 1;
    for (int i = 0; i < n; ++i) {
        if (scanf("%lld %lld", &ev[2 * i].t, &ev[2 * i + 1].t) != 2) return 1;
        ev[2 * i].d = 1;
        ev[2 * i + 1].d = -1;
    }
    qsort(ev, 2 * n, sizeof *ev, cmp);
    int cur = 0, best = 0;
    for (int i = 0; i < 2 * n; ++i) { cur += ev[i].d; if (cur > best) best = cur; }
    printf("%d\n", best);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <vector>
#include <algorithm>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n;
    std::cin >> n;
    std::vector<std::pair<long long, int>> ev;
    for (int i = 0; i < n; ++i) { long long d, f; std::cin >> d >> f; ev.push_back({d, 1}); ev.push_back({f, -1}); }
    std::sort(ev.begin(), ev.end());
    int cur = 0, best = 0;
    for (auto& [t, d] : ev) best = std::max(best, cur += d);
    std::cout << best << "\n";
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const n = Number(L[0]);
const deb = new Float64Array(n), fin = new Float64Array(n);
for (let i = 0; i < n; i++) { const [d, f] = L[i + 1].split(" ").map(Number); deb[i] = d; fin[i] = f; }
deb.sort(); fin.sort();
let cur = 0, best = 0, j = 0;
for (let i = 0; i < n; i++) {
  while (fin[j] <= deb[i]) { j++; cur--; }
  cur++;
  if (cur > best) best = cur;
}
console.log(best);""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
$deb = []; $fin = [];
for ($i = 0; $i < $n; $i++) { [$d, $f] = explode(' ', trim(fgets(STDIN))); $deb[] = (int) $d; $fin[] = (int) $f; }
sort($deb); sort($fin);
$cur = $best = $j = 0;
for ($i = 0; $i < $n; $i++) {
    while ($fin[$j] <= $deb[$i]) { $j++; $cur--; }
    $cur++;
    if ($cur > $best) $best = $cur;
}
echo $best, "\n";"""}, minutes=40, time=3),
]
