# -*- coding: utf-8 -*-
"""Palier 3 — Fonctions et récursivité : décomposer, récurser, associer (dictionnaires)."""
from itertools import permutations

from .base import ch, lines

_BIG = list(range(60000, 0, -7)) + list(range(-3, 20000, 11))


def _hanoi(n):
    out = []

    def go(k, a, b, c):
        if k:
            go(k - 1, a, c, b)
            out.append(f"{a} -> {c}")
            go(k - 1, b, a, c)
    go(n, "A", "B", "C")
    return lines(out + [f"total: {len(out)}"])


def _perms(s):
    return lines("".join(p) for p in permutations(sorted(s)))


def _roman(n):
    r = ""
    for v, s in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            r += s
            n -= v
    return r


def _annuaire():
    cmds, out, d = [], [], {}
    for i in range(3000):
        k = f"p{(i * 37) % 450}"
        if i % 5 == 0:
            cmds.append(f"SUPPRIME {k}")
            d.pop(k, None)
        elif i % 3 == 0:
            cmds.append(f"CHERCHE {k}")
            out.append(d.get(k, "inconnu"))
        elif i % 97 == 0:
            cmds.append("TAILLE")
            out.append(str(len(d)))
        else:
            cmds.append(f"AJOUTE {k} 06{i:08d}")
            d[k] = f"06{i:08d}"
    return f"{len(cmds)}\n" + lines(cmds), lines(out)


_AN = _annuaire()

DEFIS = [
    ch("fibo", 3, "mini", "Fibonacci rapide", "récursion",
       "Lisez n (0 à 90) et affichez F(n), avec F(0) = 0, F(1) = 1 et F(n) = F(n-1) + F(n-2). Limite : 1 seconde.",
       [("0", "0"), ("10", "55"), ("1", "1"), ("50", "12586269025"), ("90", "2880067194370816120")],
       ["La récursion naïve recalcule les mêmes valeurs des milliards de fois : trop lente pour n = 50.",
        "Gardez seulement les deux dernières valeurs et avancez dans une boucle (ou mémorisez les résultats déjà calculés).",
        "F(90) tient dans un long long, mais pas dans un Number JavaScript exact : BigInt."],
       {"cpp": r"""
#include <iostream>
int main() {
    int n;
    std::cin >> n;
    long long a = 0, b = 1;
    for (int i = 0; i < n; ++i) { long long t = a + b; a = b; b = t; }
    std::cout << a << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 1;
    long long a = 0, b = 1;
    for (int i = 0; i < n; ++i) { long long t = a + b; a = b; b = t; }
    printf("%lld\n", a);
    return 0;
}""", "python": r"""
a, b = 0, 1
for _ in range(int(input())):
    a, b = b, a + b
print(a)""", "javascript": r"""
const n = parseInt(require("fs").readFileSync(0, "utf8"), 10);
let a = 0n, b = 1n;
for (let i = 0; i < n; i++) [a, b] = [b, a + b];
console.log(a.toString());""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
[$a, $b] = [0, 1];
for ($i = 0; $i < $n; $i++) [$a, $b] = [$b, $a + $b];
echo $a, "\n";"""}, time=1),

    ch("tri", 3, "mini", "Trier", "tri",
       "Ligne 1 : n. Ligne 2 : n entiers. Affichez-les triés dans l'ordre croissant, séparés par des espaces. n peut dépasser 10 000.",
       [("5\n3 1 4 1 5", "1 1 3 4 5"), ("4\n-1 -3 2 0", "-3 -1 0 2"), ("1\n42", "42"),
        (f"{len(_BIG)}\n" + " ".join(map(str, _BIG)), " ".join(map(str, sorted(_BIG))))],
       ["Rangez les nombres dans un tableau.", "Un tri à bulles (n²) sera trop lent pour plus de 10 000 nombres dans certains langages.",
        "qsort (C), std::sort (C++), sorted (Python), sort((a, b) => a - b) en JS (sans comparateur, JS trie comme du texte !), sort (PHP)."],
       {"cpp": r"""
#include <iostream>
#include <vector>
#include <algorithm>
int main() {
    int n;
    std::cin >> n;
    std::vector<long long> v(n);
    for (auto& x : v) std::cin >> x;
    std::sort(v.begin(), v.end());
    for (int i = 0; i < n; ++i) std::cout << (i ? " " : "") << v[i];
    std::cout << "\n";
}""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
static int cmp(const void *a, const void *b) {
    long long x = *(const long long *)a, y = *(const long long *)b;
    return (x > y) - (x < y);
}
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 1;
    long long *v = malloc(sizeof *v * n);
    for (int i = 0; i < n; ++i) if (scanf("%lld", &v[i]) != 1) return 1;
    qsort(v, n, sizeof *v, cmp);
    for (int i = 0; i < n; ++i) printf(i ? " %lld" : "%lld", v[i]);
    printf("\n");
    free(v);
    return 0;
}""", "python": r"""
input()
print(*sorted(map(int, input().split())))""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
console.log(L[1].trim().split(/\s+/).map(Number).sort((a, b) => a - b).join(" "));""", "php": r"""
<?php
fgets(STDIN);
$v = array_map('intval', explode(' ', trim(fgets(STDIN))));
sort($v);
echo implode(' ', $v), "\n";"""}),

    ch("mots", 3, "mini", "Fréquence des mots", "dictionnaires",
       "Lisez une ligne de mots en minuscules séparés par des espaces. Affichez chaque mot distinct et son nombre d'apparitions, "
       "« mot: k », par ordre alphabétique.",
       [("le chat et le chien", "chat: 1\nchien: 1\net: 1\nle: 2"), ("a a a", "a: 3"), ("forge code forge", "code: 1\nforge: 2"),
        ("un deux trois deux un un", "deux: 2\ntrois: 1\nun: 3")],
       ["Il faut associer un compteur à chaque mot : c'est le rôle d'un dictionnaire (table associative).",
        "C++ : std::map<std::string, int> garde les clés triées. Python : dict puis sorted(). JS : Map ou objet. PHP : tableau puis ksort.",
        "En C : rangez les mots dans un tableau, triez-le (qsort + strcmp), puis comptez les mots identiques consécutifs."],
       {"cpp": r"""
#include <iostream>
#include <map>
#include <string>
int main() {
    std::map<std::string, int> m;
    std::string w;
    while (std::cin >> w) ++m[w];
    for (auto& [k, v] : m) std::cout << k << ": " << v << "\n";
}""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int cmp(const void *a, const void *b) { return strcmp(*(char *const *)a, *(char *const *)b); }
int main(void) {
    static char buf[1 << 16];
    char *w[20000];
    int n = 0;
    if (!fgets(buf, sizeof buf, stdin)) return 0;
    for (char *t = strtok(buf, " \r\n"); t; t = strtok(NULL, " \r\n")) w[n++] = t;
    qsort(w, n, sizeof *w, cmp);
    for (int i = 0; i < n;) {
        int j = i;
        while (j < n && strcmp(w[j], w[i]) == 0) ++j;
        printf("%s: %d\n", w[i], j - i);
        i = j;
    }
    return 0;
}""", "python": r"""
m = {}
for w in input().split():
    m[w] = m.get(w, 0) + 1
for k in sorted(m):
    print(f"{k}: {m[k]}")""", "javascript": r"""
const m = new Map();
for (const w of require("fs").readFileSync(0, "utf8").trim().split(/\s+/)) m.set(w, (m.get(w) || 0) + 1);
for (const k of [...m.keys()].sort()) console.log(`${k}: ${m.get(k)}`);""", "php": r"""
<?php
$m = array_count_values(preg_split('/\s+/', trim(fgets(STDIN))));
ksort($m, SORT_STRING);
foreach ($m as $k => $v) echo "$k: $v\n";"""}),

    ch("pgcd", 3, "mini", "PGCD et PPCM", "fonctions",
       "Lisez deux entiers positifs a et b. Affichez « pgcd ppcm » (séparés par un espace). "
       "Contrainte : sans les fonctions toutes faites gcd / lcm, écrivez votre propre fonction.",
       [("12 18", "6 36"), ("7 13", "1 91"), ("100 100", "100 100"), ("1000000 999999", "1 999999000000"), ("48 180", "12 720")],
       ["Algorithme d'Euclide : pgcd(a, b) = pgcd(b, a % b), et pgcd(a, 0) = a.",
        "ppcm(a, b) = a / pgcd(a, b) × b (divisez d'abord pour éviter le débordement).", "Écrivez une fonction pgcd(a, b) qui renvoie un entier."],
       {"cpp": r"""
#include <iostream>
long long pg(long long a, long long b) { return b == 0 ? a : pg(b, a % b); }
int main() {
    long long a, b;
    std::cin >> a >> b;
    long long g = pg(a, b);
    std::cout << g << " " << a / g * b << std::endl;
}""", "c": r"""
#include <stdio.h>
static long long pg(long long a, long long b) { return b == 0 ? a : pg(b, a % b); }
int main(void) {
    long long a, b;
    if (scanf("%lld %lld", &a, &b) != 2) return 1;
    long long g = pg(a, b);
    printf("%lld %lld\n", g, a / g * b);
    return 0;
}""", "python": r"""
def pg(a, b):
    return a if b == 0 else pg(b, a % b)

a, b = map(int, input().split())
g = pg(a, b)
print(g, a // g * b)""", "javascript": r"""
const pg = (a, b) => (b === 0 ? a : pg(b, a % b));
const [a, b] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
const g = pg(a, b);
console.log(`${g} ${(a / g) * b}`);""", "php": r"""
<?php
function pg(int $a, int $b): int { return $b === 0 ? $a : pg($b, $a % $b); }
[$a, $b] = array_map('intval', explode(' ', trim(fgets(STDIN))));
$g = pg($a, $b);
echo $g, " ", intdiv($a, $g) * $b, "\n";"""}, banned={"*": [r"\bgcd\b", r"\blcm\b"]}),

    ch("puissance", 3, "mini", "Exponentiation rapide", "récursion",
       "Lisez a, b et m (0 ≤ a ≤ 10^9, 0 ≤ b ≤ 10^18, 1 ≤ m ≤ 10^9). Affichez a^b modulo m (avec la convention a^0 = 1). "
       "Contrainte : sans fonction de puissance toute faite. Limite : 1 seconde.",
       [("2 10 1000", "24"), ("3 0 7", "1"), ("5 3 1", "0"), ("0 0 5", "1"), ("2 1000000000000000000 1000000007", "719476260"),
        ("123456789 987654321987654321 998244353", "89607075"), ("999999999 999999999999999999 999999937", "655652178")],
       ["Multiplier a par lui-même b fois est impossible pour b = 10^18.",
        "a^b = (a^(b/2))² si b est pair, et a × a^(b-1) sinon : environ 60 étapes seulement.",
        "Réduisez modulo m après chaque multiplication. Les produits atteignent 10^18 : entier 64 bits (BigInt en JavaScript)."],
       {"cpp": r"""
#include <iostream>
long long puis(long long a, long long b, long long m) {
    if (b == 0) return 1 % m;
    long long h = puis(a, b / 2, m);
    h = h * h % m;
    return b % 2 ? h * (a % m) % m : h;
}
int main() {
    long long a, b, m;
    std::cin >> a >> b >> m;
    std::cout << puis(a, b, m) << std::endl;
}""", "c": r"""
#include <stdio.h>
static long long puis(long long a, long long b, long long m) {
    if (b == 0) return 1 % m;
    long long h = puis(a, b / 2, m);
    h = h * h % m;
    return b % 2 ? h * (a % m) % m : h;
}
int main(void) {
    long long a, b, m;
    if (scanf("%lld %lld %lld", &a, &b, &m) != 3) return 1;
    printf("%lld\n", puis(a, b, m));
    return 0;
}""", "python": r"""
def puis(a, b, m):
    if b == 0:
        return 1 % m
    h = puis(a, b // 2, m)
    h = h * h % m
    return h * (a % m) % m if b % 2 else h

a, b, m = map(int, input().split())
print(puis(a, b, m))""", "javascript": r"""
const puis = (a, b, m) => {
  if (b === 0n) return 1n % m;
  let h = puis(a, b / 2n, m);
  h = (h * h) % m;
  return b % 2n ? (h * (a % m)) % m : h;
};
const [a, b, m] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(BigInt);
console.log(puis(a, b, m).toString());""", "php": r"""
<?php
function puis(int $a, int $b, int $m): int {
    if ($b === 0) return 1 % $m;
    $h = puis($a, intdiv($b, 2), $m);
    $h = $h * $h % $m;
    return $b % 2 ? $h * ($a % $m) % $m : $h;
}
[$a, $b, $m] = array_map('intval', explode(' ', trim(fgets(STDIN))));
echo puis($a, $b, $m), "\n";"""}, time=1, banned={"python": [r"\bpow\s*\("], "php": [r"\bbcpowmod\b", r"\bgmp_"], "javascript": [r"\*\*"]}),

    ch("hanoi", 3, "mini", "Les tours de Hanoï", "récursion",
       "Lisez n (1 à 12). Déplacez une tour de n disques du piquet A vers le piquet C (en s'aidant de B), sans jamais poser un disque "
       "sur un plus petit. Affichez chaque déplacement « X -> Y » de la solution la plus courte, puis « total: k ».",
       [("1", _hanoi(1)), ("2", _hanoi(2)), ("3", _hanoi(3)), ("5", _hanoi(5)), ("12", _hanoi(12))],
       ["Pensez récursivement : pour déplacer n disques de A vers C, il faut d'abord déplacer n - 1 disques de A vers B.",
        "hanoi(n, A, B, C) = hanoi(n - 1, A, C, B) ; déplacer A -> C ; hanoi(n - 1, B, A, C).", "Le cas de base : n = 0, il n'y a rien à faire. Le total vaut 2^n - 1."],
       {"cpp": r"""
#include <iostream>
int total = 0;
void hanoi(int n, char a, char b, char c) {
    if (n == 0) return;
    hanoi(n - 1, a, c, b);
    std::cout << a << " -> " << c << "\n";
    ++total;
    hanoi(n - 1, b, a, c);
}
int main() {
    int n;
    std::cin >> n;
    hanoi(n, 'A', 'B', 'C');
    std::cout << "total: " << total << "\n";
}""", "c": r"""
#include <stdio.h>
static int total = 0;
static void hanoi(int n, char a, char b, char c) {
    if (n == 0) return;
    hanoi(n - 1, a, c, b);
    printf("%c -> %c\n", a, c);
    ++total;
    hanoi(n - 1, b, a, c);
}
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 1;
    hanoi(n, 'A', 'B', 'C');
    printf("total: %d\n", total);
    return 0;
}""", "python": r"""
out = []

def hanoi(n, a, b, c):
    if n == 0:
        return
    hanoi(n - 1, a, c, b)
    out.append(f"{a} -> {c}")
    hanoi(n - 1, b, a, c)

hanoi(int(input()), "A", "B", "C")
print("\n".join(out))
print(f"total: {len(out)}")""", "javascript": r"""
const out = [];
const hanoi = (n, a, b, c) => {
  if (n === 0) return;
  hanoi(n - 1, a, c, b);
  out.push(`${a} -> ${c}`);
  hanoi(n - 1, b, a, c);
};
hanoi(parseInt(require("fs").readFileSync(0, "utf8"), 10), "A", "B", "C");
console.log(out.join("\n") + `\ntotal: ${out.length}`);""", "php": r"""
<?php
$total = 0;
function hanoi(int $n, string $a, string $b, string $c): void {
    global $total;
    if ($n === 0) return;
    hanoi($n - 1, $a, $c, $b);
    echo "$a -> $c\n";
    $total++;
    hanoi($n - 1, $b, $a, $c);
}
hanoi((int) trim(fgets(STDIN)), 'A', 'B', 'C');
echo "total: $total\n";"""}),

    ch("annuaire", 3, "mini", "L'annuaire", "dictionnaires",
       "Ligne 1 : n. Puis n commandes : « AJOUTE nom numéro » (remplace le numéro si le nom existe), « CHERCHE nom » (affiche le numéro, "
       "ou « inconnu »), « SUPPRIME nom » (n'affiche rien, même si le nom n'existe pas) et « TAILLE » (affiche le nombre de contacts).",
       [("5\nAJOUTE alice 0601\nAJOUTE bob 0702\nCHERCHE alice\nCHERCHE carl\nTAILLE", "0601\ninconnu\n2"),
        ("6\nAJOUTE a 1\nAJOUTE a 2\nCHERCHE a\nSUPPRIME a\nSUPPRIME a\nCHERCHE a", "2\ninconnu"),
        ("1\nTAILLE", "0"), _AN],
       ["Un dictionnaire nom → numéro fait tout le travail.", "Lisez le premier mot de chaque commande pour savoir quoi faire.",
        "En C, sans dictionnaire tout fait : un tableau de paires (nom, numéro) et une recherche linéaire suffisent ici."],
       {"cpp": r"""
#include <iostream>
#include <string>
#include <unordered_map>
int main() {
    int n;
    std::cin >> n;
    std::unordered_map<std::string, std::string> d;
    std::string c, nom, num;
    while (n-- > 0 && std::cin >> c) {
        if (c == "AJOUTE") { std::cin >> nom >> num; d[nom] = num; }
        else if (c == "CHERCHE") { std::cin >> nom; auto it = d.find(nom); std::cout << (it == d.end() ? "inconnu" : it->second) << "\n"; }
        else if (c == "SUPPRIME") { std::cin >> nom; d.erase(nom); }
        else std::cout << d.size() << "\n";
    }
}""", "c": r"""
#include <stdio.h>
#include <string.h>
static char noms[5000][64], nums[5000][64];
static int nb = 0;
static int trouve(const char *s) {
    for (int i = 0; i < nb; ++i) if (strcmp(noms[i], s) == 0) return i;
    return -1;
}
int main(void) {
    int n;
    char c[32], nom[64], num[64];
    if (scanf("%d", &n) != 1) return 1;
    while (n-- > 0 && scanf("%31s", c) == 1) {
        if (strcmp(c, "AJOUTE") == 0) {
            if (scanf("%63s %63s", nom, num) != 2) return 1;
            int i = trouve(nom);
            if (i < 0) { i = nb++; strcpy(noms[i], nom); }
            strcpy(nums[i], num);
        } else if (strcmp(c, "CHERCHE") == 0) {
            if (scanf("%63s", nom) != 1) return 1;
            int i = trouve(nom);
            puts(i < 0 ? "inconnu" : nums[i]);
        } else if (strcmp(c, "SUPPRIME") == 0) {
            if (scanf("%63s", nom) != 1) return 1;
            int i = trouve(nom);
            if (i >= 0) { --nb; strcpy(noms[i], noms[nb]); strcpy(nums[i], nums[nb]); }
        } else printf("%d\n", nb);
    }
    return 0;
}""", "python": r"""
import sys
d = {}
lignes = sys.stdin.read().split("\n")
for l in lignes[1:int(lignes[0]) + 1]:
    p = l.split()
    if p[0] == "AJOUTE":
        d[p[1]] = p[2]
    elif p[0] == "CHERCHE":
        print(d.get(p[1], "inconnu"))
    elif p[0] == "SUPPRIME":
        d.pop(p[1], None)
    else:
        print(len(d))""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const d = new Map(), out = [];
for (const l of L.slice(1, Number(L[0]) + 1)) {
  const [c, nom, num] = l.trim().split(/\s+/);
  if (c === "AJOUTE") d.set(nom, num);
  else if (c === "CHERCHE") out.push(d.has(nom) ? d.get(nom) : "inconnu");
  else if (c === "SUPPRIME") d.delete(nom);
  else out.push(d.size);
}
if (out.length) console.log(out.join("\n"));""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
$d = [];
for ($i = 0; $i < $n; $i++) {
    $p = explode(' ', trim(fgets(STDIN)));
    switch ($p[0]) {
        case 'AJOUTE': $d[$p[1]] = $p[2]; break;
        case 'CHERCHE': echo $d[$p[1]] ?? 'inconnu', "\n"; break;
        case 'SUPPRIME': unset($d[$p[1]]); break;
        default: echo count($d), "\n";
    }
}"""}),

    ch("permutations", 3, "mini", "Toutes les permutations", "récursion",
       "Lisez un mot de 1 à 7 lettres minuscules toutes différentes. Affichez toutes ses permutations dans l'ordre alphabétique, une par ligne. "
       "Contrainte : écrivez la génération vous-même (pas de fonction de bibliothèque qui le fait).",
       [("abc", _perms("abc")), ("a", "a"), ("ba", "ab\nba"), ("dcab", _perms("dcab")), ("forgeui", _perms("forgeui"))],
       ["Triez d'abord les lettres : si on choisit toujours les lettres dans l'ordre, les permutations sortent dans l'ordre alphabétique.",
        "Récursion : choisir une première lettre parmi celles qui restent, puis permuter les autres.",
        "Un tableau « utilisé[] » indique quelles lettres sont déjà placées ; on le remet à faux en revenant (retour sur trace)."],
       {"cpp": r"""
#include <iostream>
#include <string>
#include <algorithm>
std::string s, cur;
bool pris[8];
void gen() {
    if (cur.size() == s.size()) { std::cout << cur << "\n"; return; }
    for (size_t i = 0; i < s.size(); ++i) if (!pris[i]) {
        pris[i] = true; cur += s[i];
        gen();
        cur.pop_back(); pris[i] = false;
    }
}
int main() {
    std::cin >> s;
    std::sort(s.begin(), s.end());
    gen();
}""", "c": r"""
#include <stdio.h>
#include <string.h>
static char s[16], cur[16];
static int n, pris[16];
static void gen(int k) {
    if (k == n) { cur[k] = '\0'; puts(cur); return; }
    for (int i = 0; i < n; ++i) if (!pris[i]) {
        pris[i] = 1; cur[k] = s[i];
        gen(k + 1);
        pris[i] = 0;
    }
}
int main(void) {
    if (scanf("%15s", s) != 1) return 1;
    n = (int)strlen(s);
    for (int i = 0; i < n; ++i) for (int j = i + 1; j < n; ++j) if (s[j] < s[i]) { char t = s[i]; s[i] = s[j]; s[j] = t; }
    gen(0);
    return 0;
}""", "python": r"""
s = sorted(input().strip())
out, cur, pris = [], [], [False] * len(s)

def gen():
    if len(cur) == len(s):
        out.append("".join(cur))
        return
    for i, c in enumerate(s):
        if not pris[i]:
            pris[i] = True
            cur.append(c)
            gen()
            cur.pop()
            pris[i] = False

gen()
print("\n".join(out))""", "javascript": r"""
const s = [...require("fs").readFileSync(0, "utf8").trim()].sort();
const out = [], cur = [], pris = s.map(() => false);
const gen = () => {
  if (cur.length === s.length) { out.push(cur.join("")); return; }
  s.forEach((c, i) => {
    if (pris[i]) return;
    pris[i] = true; cur.push(c);
    gen();
    cur.pop(); pris[i] = false;
  });
};
gen();
console.log(out.join("\n"));""", "php": r"""
<?php
$s = str_split(trim(fgets(STDIN)));
sort($s);
$pris = array_fill(0, count($s), false);
function gen(array &$s, array &$pris, string $cur): void {
    if (strlen($cur) === count($s)) { echo $cur, "\n"; return; }
    foreach ($s as $i => $c) {
        if ($pris[$i]) continue;
        $pris[$i] = true;
        gen($s, $pris, $cur . $c);
        $pris[$i] = false;
    }
}
gen($s, $pris, "");"""}, banned={"python": [r"itertools", r"permutations"], "cpp": [r"next_permutation"]}),

    ch("romains", 3, "mini", "Chiffres romains", "fonctions",
       "Lisez un entier entre 1 et 3999 et affichez-le en chiffres romains (I V X L C D M, avec les formes soustractives IV, IX, XL, XC, CD, CM).",
       [("1994", "MCMXCIV"), ("4", "IV"), ("1", "I"), ("9", "IX"), ("14", "XIV"), ("40", "XL"), ("90", "XC"), ("400", "CD"),
        ("2026", "MMXXVI"), ("3999", "MMMCMXCIX"), ("444", "CDXLIV")],
       ["Préparez deux tableaux parallèles : les valeurs (1000, 900, 500, 400, …, 1) et leurs symboles (M, CM, D, CD, …, I).",
        "Parcourez-les du plus grand au plus petit : tant que la valeur tient dans n, ajoutez le symbole et retranchez la valeur.",
        "Les formes soustractives (CM, CD, XC…) étant dans le tableau, il n'y a aucun cas particulier à gérer."],
       {"cpp": r"""
#include <iostream>
#include <string>
std::string romain(int n) {
    const int v[] = {1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1};
    const char *s[] = {"M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"};
    std::string r;
    for (int i = 0; i < 13; ++i) while (n >= v[i]) { r += s[i]; n -= v[i]; }
    return r;
}
int main() {
    int n;
    std::cin >> n;
    std::cout << romain(n) << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    const int v[] = {1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1};
    const char *s[] = {"M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"};
    int n;
    if (scanf("%d", &n) != 1) return 1;
    for (int i = 0; i < 13; ++i) while (n >= v[i]) { fputs(s[i], stdout); n -= v[i]; }
    putchar('\n');
    return 0;
}""", "python": r"""
def romain(n):
    r = ""
    for v, s in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
                 (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            r += s
            n -= v
    return r

print(romain(int(input())))""", "javascript": r"""
const romain = n => {
  const T = [[1000, "M"], [900, "CM"], [500, "D"], [400, "CD"], [100, "C"], [90, "XC"], [50, "L"], [40, "XL"], [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"]];
  let r = "";
  for (const [v, s] of T) while (n >= v) { r += s; n -= v; }
  return r;
};
console.log(romain(parseInt(require("fs").readFileSync(0, "utf8"), 10)));""", "php": r"""
<?php
function romain(int $n): string {
    $t = [1000 => 'M', 900 => 'CM', 500 => 'D', 400 => 'CD', 100 => 'C', 90 => 'XC', 50 => 'L', 40 => 'XL', 10 => 'X', 9 => 'IX', 5 => 'V', 4 => 'IV', 1 => 'I'];
    $r = '';
    foreach ($t as $v => $s) while ($n >= $v) { $r .= $s; $n -= $v; }
    return $r;
}
echo romain((int) trim(fgets(STDIN))), "\n";"""}),

    ch("anagrammes", 3, "exam", "Examen : anagrammes", "dictionnaires",
       "Ligne 1 : n. Ligne 2 : n mots en minuscules. Regroupez les anagrammes (mêmes lettres dans un autre ordre). "
       "Affichez un groupe par ligne, ses mots triés et séparés par un espace ; les groupes sont triés selon leur premier mot.",
       [("6\nchien niche chat tach acht rose", "acht chat tach\nchien niche\nrose"), ("1\nforge", "forge"),
        ("4\nsoir rois oris cle", "cle\noris rois soir"), ("3\nab ba ab", "ab ab ba"), ("5\nare era ear bca abc", "abc bca\nare ear era")],
       ["Deux mots sont anagrammes si leurs lettres triées sont identiques : c'est une bonne clé.",
        "Dictionnaire : clé = lettres triées, valeur = liste des mots.", "Triez chaque groupe, puis triez les groupes selon leur premier mot."],
       {"cpp": r"""
#include <iostream>
#include <map>
#include <vector>
#include <string>
#include <algorithm>
int main() {
    int n;
    std::cin >> n;
    std::map<std::string, std::vector<std::string>> g;
    for (int i = 0; i < n; ++i) {
        std::string w;
        std::cin >> w;
        std::string k = w;
        std::sort(k.begin(), k.end());
        g[k].push_back(w);
    }
    std::vector<std::vector<std::string>> out;
    for (auto& [k, v] : g) { std::sort(v.begin(), v.end()); out.push_back(v); }
    std::sort(out.begin(), out.end());
    for (auto& v : out) {
        for (size_t i = 0; i < v.size(); ++i) std::cout << (i ? " " : "") << v[i];
        std::cout << "\n";
    }
}""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct { char mot[64], cle[64]; } Mot;
static int parcle(const void *a, const void *b) {
    const Mot *x = a, *y = b;
    int c = strcmp(x->cle, y->cle);
    return c ? c : strcmp(x->mot, y->mot);
}
static int parmot(const void *a, const void *b) { return strcmp(((const Mot *)a)->mot, ((const Mot *)b)->mot); }
static int lettres(const void *a, const void *b) { return *(const char *)a - *(const char *)b; }
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 1;
    Mot *m = malloc(sizeof *m * n);
    for (int i = 0; i < n; ++i) {
        if (scanf("%63s", m[i].mot) != 1) return 1;
        strcpy(m[i].cle, m[i].mot);
        qsort(m[i].cle, strlen(m[i].cle), 1, lettres);
    }
    qsort(m, n, sizeof *m, parcle);
    /* chaque groupe est trié ; on trie les groupes par leur premier mot */
    int *deb = malloc(sizeof *deb * (n + 1)), ng = 0;
    for (int i = 0; i < n; ++i) if (i == 0 || strcmp(m[i].cle, m[i - 1].cle)) deb[ng++] = i;
    deb[ng] = n;
    Mot *tete = malloc(sizeof *tete * ng);
    for (int g = 0; g < ng; ++g) { tete[g] = m[deb[g]]; sprintf(tete[g].cle, "%d", g); }
    qsort(tete, ng, sizeof *tete, parmot);
    for (int k = 0; k < ng; ++k) {
        int g = atoi(tete[k].cle);
        for (int i = deb[g]; i < deb[g + 1]; ++i) printf(i > deb[g] ? " %s" : "%s", m[i].mot);
        printf("\n");
    }
    free(m); free(deb); free(tete);
    return 0;
}""", "python": r"""
input()
g = {}
for w in input().split():
    g.setdefault("".join(sorted(w)), []).append(w)
for grp in sorted(sorted(v) for v in g.values()):
    print(" ".join(grp))""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const g = new Map();
for (const w of L[1].trim().split(/\s+/)) {
  const k = [...w].sort().join("");
  if (!g.has(k)) g.set(k, []);
  g.get(k).push(w);
}
const out = [...g.values()].map(v => v.sort());
out.sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
console.log(out.map(v => v.join(" ")).join("\n"));""", "php": r"""
<?php
fgets(STDIN);
$g = [];
foreach (explode(' ', trim(fgets(STDIN))) as $w) {
    $l = str_split($w);
    sort($l);
    $g[implode('', $l)][] = $w;
}
$out = array_values($g);
foreach ($out as &$v) sort($v, SORT_STRING);
unset($v);
usort($out, fn($a, $b) => strcmp($a[0], $b[0]));
foreach ($out as $v) echo implode(' ', $v), "\n";"""}, minutes=30),
]
