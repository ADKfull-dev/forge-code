# -*- coding: utf-8 -*-
"""RÉSERVE (non chargée) — anciens défis du palier 0 maths, trop durs pour débuter : à recaser dans les paliers avancés."""
from .base import ch, lines


def _rnd(n, lo, hi, seed=1):
    """Suite pseudo-aléatoire reproductible sur 64 bits (splitmix64), valeurs dans [lo, hi]."""
    x, out = seed, []
    for _ in range(n):
        x = (x + 0x9E3779B97F4A7C15) % 2 ** 64
        z = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) % 2 ** 64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) % 2 ** 64
        out.append(lo + (z ^ (z >> 31)) % (hi - lo + 1))
    return out


# ---------------------------------------------------------------- tests générés

def _EU():
    a = _rnd(100000, -10 ** 18, 10 ** 18, 3)
    b = [v or 1 for v in _rnd(50000, -10 ** 18, 10 ** 18, 5) + _rnd(50000, -20, 20, 7)]
    return "100000\n" + lines(f"{x} {y}" for x, y in zip(a, b))


def _PG1():
    v = [123456789 * m for m in _rnd(100000, 1, 8 * 10 ** 9, 11)]
    v[5000] = 1000000007
    return "100000\n" + " ".join(map(str, v))


_PG2 = lambda: "100000\n" + " ".join(map(str, _rnd(100000, 1, 10 ** 18, 13)))
_PG3 = lambda: "100000\n" + " ".join(["1000000000000000000"] * 100000)


def _FR():
    v = _rnd(400000, -10 ** 9, 10 ** 9, 17)
    fr = lambda p, q: f"{p}/{q or 1}"
    return "100000\n" + lines(f"{fr(v[4 * i], v[4 * i + 1])} {fr(v[4 * i + 2], v[4 * i + 3])}" for i in range(100000))


def _ZE():
    n = _rnd(30000, 0, 10 ** 18, 19)
    b = _rnd(30000, 2, 36, 23)
    return "30000\n" + lines(f"{x} {y}" for x, y in zip(n, b))


_RN1 = lambda: "".join(map(str, [1 + _rnd(1, 0, 8, 29)[0]] + _rnd(199999, 0, 9, 31)))
_RN2 = lambda: "9" * 200000
_RN3 = lambda: "1" + "0" * 199999


def _MU():
    ab = _rnd(200000, -10 ** 18, 10 ** 18, 37)
    xy = _rnd(100000, 1, 10 ** 9, 41) + _rnd(100000, 1, 30, 43)
    out = []
    for i in range(100000):
        a, b = sorted(ab[2 * i:2 * i + 2])
        out.append(f"{a} {b} {xy[i]} {xy[100000 + i]}" if i % 2 else f"{a} {b} {xy[100000 + i]} {xy[i]}")
    return "100000\n" + lines(out)


_NB = lambda: "20000\n" + lines(_rnd(20000, -10 ** 18, 10 ** 18, 47))


DEFIS = [
    ch("math-euclide", 0, "mini", "La vraie division euclidienne", "division euclidienne",
       "Première ligne : T. Puis T lignes « a b » avec |a| ≤ 10^18 et 1 ≤ |b| ≤ 10^18 (a et b peuvent être négatifs). "
       "Pour chaque ligne, affichez le quotient q et le reste r de la division euclidienne au sens des mathématiciens : "
       "a = b × q + r avec 0 ≤ r < |b|. Le reste n'est jamais négatif !",
       [("4\n17 5\n-17 5\n17 -5\n-17 -5", "3 2\n-4 3\n-3 2\n4 3"),
        ("3\n0 7\n-1 1000000000000000000\n1000000000000000000 -1", "0 0\n-1 999999999999999999\n-1000000000000000000 0"),
        ("6\n5 1\n-5 1\n5 -1\n1 5\n-1 5\n-1 -5", "5 0\n-5 0\n-5 0\n0 1\n-1 4\n1 4"),
        ("2\n-1000000000000000000 1000000000000000000\n999999999999999999 -1000000000000000000", None),
        _EU],
       ["En C, C++, JavaScript et PHP, -17 % 5 vaut -2 : l'opérateur % suit le signe du dividende. Python, lui, suit le signe du diviseur.",
        "Calculez d'abord le reste r = a mod |b|, puis corrigez-le : s'il est négatif, ajoutez |b|.",
        "Une fois r connu, q = (a − r) / b est une division exacte : plus aucun problème d'arrondi."],
       {"cpp": r"""
#include <iostream>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int t;
    std::cin >> t;
    while (t--) {
        long long a, b;
        std::cin >> a >> b;
        long long m = b < 0 ? -b : b, r = a % m;
        if (r < 0) r += m;
        std::cout << (a - r) / b << ' ' << r << '\n';
    }
}""", "c": r"""
#include <stdio.h>
int main(void) {
    int t;
    if (scanf("%d", &t) != 1) return 1;
    while (t--) {
        long long a, b;
        if (scanf("%lld %lld", &a, &b) != 2) return 1;
        long long m = b < 0 ? -b : b, r = a % m;
        if (r < 0) r += m;
        printf("%lld %lld\n", (a - r) / b, r);
    }
    return 0;
}""", "python": r"""
import sys
d = sys.stdin.buffer.read().split()
out = []
for i in range(int(d[0])):
    a, b = int(d[1 + 2 * i]), int(d[2 + 2 * i])
    r = a % abs(b)
    out.append(f"{(a - r) // b} {r}")
print("\n".join(out))""", "javascript": r"""
const d = require("fs").readFileSync(0, "utf8").trim().split(/\s+/);
const out = [];
for (let i = 0; i < Number(d[0]); i++) {
  const a = BigInt(d[1 + 2 * i]), b = BigInt(d[2 + 2 * i]), m = b < 0n ? -b : b;
  let r = a % m;
  if (r < 0n) r += m;
  out.push(`${(a - r) / b} ${r}`);
}
console.log(out.join("\n"));""", "php": r"""
<?php
$d = preg_split('/\s+/', trim(stream_get_contents(STDIN)));
$out = [];
for ($i = 0; $i < (int) $d[0]; $i++) {
    $a = (int) $d[1 + 2 * $i];
    $b = (int) $d[2 + 2 * $i];
    $m = abs($b);
    $r = $a % $m;
    if ($r < 0) $r += $m;
    $out[] = intdiv($a - $r, $b) . " $r";
}
echo implode("\n", $out), "\n";"""}),

    ch("math-pgcd-intrus", 0, "mini", "Le PGCD sans l'intrus", "PGCD",
       "Première ligne : n (2 ≤ n ≤ 100 000). Deuxième ligne : n entiers entre 1 et 10^18. On retire exactement un nombre de la liste : "
       "quel est le plus grand PGCD possible des n − 1 nombres restants ? Recalculer le PGCD pour chaque nombre retiré est bien trop lent.",
       [("3\n12 18 24", "12"), ("4\n7 14 28 5", "7"), ("2\n1000000000000000000 3", "1000000000000000000"), ("2\n5 5", "5"),
        ("5\n6 10 15 30 60", "5"), _PG1, _PG2, _PG3],
       ["PGCD(a, b) = PGCD(b, a mod b), et PGCD(0, a) = a : l'algorithme d'Euclide.",
        "Précalculez les PGCD de tous les préfixes a[0..i] et de tous les suffixes a[i..n-1].",
        "Le PGCD de la liste privée de a[i] vaut PGCD(préfixe jusqu'à i − 1, suffixe depuis i + 1) : tout se fait en O(n log M)."],
       {"cpp": r"""
#include <iostream>
#include <vector>
#include <numeric>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n;
    std::cin >> n;
    std::vector<long long> a(n), pre(n + 1, 0);
    for (int i = 0; i < n; ++i) { std::cin >> a[i]; pre[i + 1] = std::gcd(pre[i], a[i]); }
    long long suf = 0, best = 0;
    for (int i = n - 1; i >= 0; --i) {
        best = std::max(best, std::gcd(pre[i], suf));
        suf = std::gcd(suf, a[i]);
    }
    std::cout << best << '\n';
}""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
static long long pgcd(long long a, long long b) {
    while (b) { long long r = a % b; a = b; b = r; }
    return a;
}
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 1;
    long long *a = malloc(n * sizeof *a), *pre = calloc(n + 1, sizeof *pre);
    for (int i = 0; i < n; ++i) {
        if (scanf("%lld", &a[i]) != 1) return 1;
        pre[i + 1] = pgcd(pre[i], a[i]);
    }
    long long suf = 0, best = 0;
    for (int i = n - 1; i >= 0; --i) {
        long long g = pgcd(pre[i], suf);
        if (g > best) best = g;
        suf = pgcd(suf, a[i]);
    }
    printf("%lld\n", best);
    free(a);
    free(pre);
    return 0;
}""", "python": r"""
import sys
from math import gcd
d = sys.stdin.buffer.read().split()
n = int(d[0])
a = list(map(int, d[1:n + 1]))
pre = [0] * (n + 1)
for i in range(n):
    pre[i + 1] = gcd(pre[i], a[i])
suf = best = 0
for i in range(n - 1, -1, -1):
    best = max(best, gcd(pre[i], suf))
    suf = gcd(suf, a[i])
print(best)""", "javascript": r"""
const d = require("fs").readFileSync(0, "utf8").trim().split(/\s+/);
const n = Number(d[0]), a = d.slice(1, n + 1).map(BigInt);
const pgcd = (x, y) => { while (y) [x, y] = [y, x % y]; return x; };
const pre = [0n];
for (let i = 0; i < n; i++) pre.push(pgcd(pre[i], a[i]));
let suf = 0n, best = 0n;
for (let i = n - 1; i >= 0; i--) {
  const g = pgcd(pre[i], suf);
  if (g > best) best = g;
  suf = pgcd(suf, a[i]);
}
console.log(String(best));""", "php": r"""
<?php
function pgcd($a, $b) {
    while ($b) { $r = $a % $b; $a = $b; $b = $r; }
    return $a;
}
$d = preg_split('/\s+/', trim(stream_get_contents(STDIN)));
$n = (int) $d[0];
$pre = [0];
for ($i = 0; $i < $n; $i++) $pre[] = pgcd($pre[$i], (int) $d[$i + 1]);
$suf = 0;
$best = 0;
for ($i = $n - 1; $i >= 0; $i--) {
    $best = max($best, pgcd($pre[$i], $suf));
    $suf = pgcd($suf, (int) $d[$i + 1]);
}
echo $best, "\n";"""}),

    ch("math-fractions", 0, "mini", "Fractions irréductibles", "fractions",
       "Première ligne : T. Puis T lignes « a/b c/d » : deux fractions avec |a|, |c| ≤ 10^9 et 1 ≤ |b|, |d| ≤ 10^9 (les signes peuvent être "
       "n'importe où). Affichez leur somme sous forme irréductible « p/q » avec q > 0, ou seulement « p » si c'est un entier.",
       [("3\n1/2 1/3\n1/2 -1/2\n3/-4 1/4", "5/6\n0\n-1/2"), ("2\n2/4 3/6\n1000000000/1 1000000000/1", "1\n2000000000"),
        ("4\n-1/-3 1/-6\n0/5 0/-7\n1/1000000000 -1/999999999\n-1000000000/1 -1000000000/1", "1/6\n0\n-1/999999999000000000\n-2000000000"),
        _FR],
       ["a/b + c/d = (a·d + c·b) / (b·d). Les produits atteignent 2·10^18 : prévoyez des entiers 64 bits (BigInt en JavaScript).",
        "Divisez numérateur et dénominateur par leur PGCD (calculé sur les valeurs absolues).",
        "Si le dénominateur est négatif, changez le signe des deux. Si q vaut 1, n'affichez que p."],
       {"cpp": r"""
#include <iostream>
#include <cstdio>
#include <numeric>
int main() {
    int t;
    if (scanf("%d", &t) != 1) return 1;
    while (t--) {
        long long a, b, c, d;
        if (scanf("%lld/%lld %lld/%lld", &a, &b, &c, &d) != 4) return 1;
        long long p = a * d + c * b, q = b * d, g = std::gcd(p, q);
        p /= g; q /= g;
        if (q < 0) { p = -p; q = -q; }
        if (q == 1) printf("%lld\n", p);
        else printf("%lld/%lld\n", p, q);
    }
}""", "c": r"""
#include <stdio.h>
static long long pgcd(long long a, long long b) {
    if (a < 0) a = -a;
    if (b < 0) b = -b;
    while (b) { long long r = a % b; a = b; b = r; }
    return a;
}
int main(void) {
    int t;
    if (scanf("%d", &t) != 1) return 1;
    while (t--) {
        long long a, b, c, d;
        if (scanf("%lld/%lld %lld/%lld", &a, &b, &c, &d) != 4) return 1;
        long long p = a * d + c * b, q = b * d, g = pgcd(p, q);
        p /= g; q /= g;
        if (q < 0) { p = -p; q = -q; }
        if (q == 1) printf("%lld\n", p);
        else printf("%lld/%lld\n", p, q);
    }
    return 0;
}""", "python": r"""
import sys
from math import gcd
d = sys.stdin.read().split()
out = []
for i in range(int(d[0])):
    a, b = map(int, d[1 + 2 * i].split("/"))
    c, e = map(int, d[2 + 2 * i].split("/"))
    p, q = a * e + c * b, b * e
    g = gcd(p, q)
    p, q = p // g, q // g
    if q < 0:
        p, q = -p, -q
    out.append(str(p) if q == 1 else f"{p}/{q}")
print("\n".join(out))""", "javascript": r"""
const d = require("fs").readFileSync(0, "utf8").trim().split(/\s+/);
const pgcd = (x, y) => { if (x < 0n) x = -x; if (y < 0n) y = -y; while (y) [x, y] = [y, x % y]; return x; };
const out = [];
for (let i = 0; i < Number(d[0]); i++) {
  const [a, b] = d[1 + 2 * i].split("/").map(BigInt), [c, e] = d[2 + 2 * i].split("/").map(BigInt);
  let p = a * e + c * b, q = b * e;
  const g = pgcd(p, q);
  p /= g; q /= g;
  if (q < 0n) { p = -p; q = -q; }
  out.push(q === 1n ? `${p}` : `${p}/${q}`);
}
console.log(out.join("\n"));""", "php": r"""
<?php
function pgcd($a, $b) {
    $a = abs($a);
    $b = abs($b);
    while ($b) { $r = $a % $b; $a = $b; $b = $r; }
    return $a;
}
$d = preg_split('/\s+/', trim(stream_get_contents(STDIN)));
$out = [];
for ($i = 0; $i < (int) $d[0]; $i++) {
    [$a, $b] = array_map('intval', explode('/', $d[1 + 2 * $i]));
    [$c, $e] = array_map('intval', explode('/', $d[2 + 2 * $i]));
    $p = $a * $e + $c * $b;
    $q = $b * $e;
    $g = pgcd($p, $q);
    $p = intdiv($p, $g);
    $q = intdiv($q, $g);
    if ($q < 0) { $p = -$p; $q = -$q; }
    $out[] = $q === 1 ? "$p" : "$p/$q";
}
echo implode("\n", $out), "\n";"""}),

    ch("math-zeros", 0, "mini", "Les zéros de la factorielle", "factorielles",
       "Première ligne : T. Puis T lignes « n b » avec 0 ≤ n ≤ 10^18 et 2 ≤ b ≤ 36. Pour chaque ligne, affichez le nombre de zéros "
       "à la fin de l'écriture de n! en base b. Impossible de calculer n! : il a des milliards de milliards de chiffres.",
       [("3\n10 10\n25 10\n5 2", "2\n6\n3"), ("3\n0 10\n100 16\n4 4", "0\n24\n1"),
        ("4\n1 36\n1000000000000000000 10\n1000000000000000000 36\n999999999999999999 7", None), _ZE],
       ["Un zéro final en base b, c'est un facteur b. Décomposez b en facteurs premiers : b = p1^e1 × p2^e2 × …",
        "Formule de Legendre : l'exposant de p dans n! vaut n/p + n/p² + n/p³ + … (divisions entières). Calculez-le en divisant n par p en boucle.",
        "Le nombre de zéros est le minimum, sur les facteurs premiers p de b, de (exposant de p dans n!) / e."],
       {"cpp": r"""
#include <iostream>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int t;
    std::cin >> t;
    while (t--) {
        long long n, b, best = -1;
        std::cin >> n >> b;
        for (long long p = 2; b > 1; ++p) {
            if (b % p) continue;
            int e = 0;
            while (b % p == 0) { b /= p; ++e; }
            long long v = 0;
            for (long long m = n; m; m /= p) v += m / p;
            if (best < 0 || v / e < best) best = v / e;
        }
        std::cout << best << '\n';
    }
}""", "c": r"""
#include <stdio.h>
int main(void) {
    int t;
    if (scanf("%d", &t) != 1) return 1;
    while (t--) {
        long long n, b, best = -1;
        if (scanf("%lld %lld", &n, &b) != 2) return 1;
        for (long long p = 2; b > 1; ++p) {
            if (b % p) continue;
            int e = 0;
            while (b % p == 0) { b /= p; ++e; }
            long long v = 0;
            for (long long m = n; m; m /= p) v += m / p;
            if (best < 0 || v / e < best) best = v / e;
        }
        printf("%lld\n", best);
    }
    return 0;
}""", "python": r"""
import sys
d = sys.stdin.buffer.read().split()
out = []
for i in range(int(d[0])):
    n, b = int(d[1 + 2 * i]), int(d[2 + 2 * i])
    best, p = None, 2
    while b > 1:
        if b % p == 0:
            e = 0
            while b % p == 0:
                b //= p
                e += 1
            v, m = 0, n
            while m:
                m //= p
                v += m
            best = v // e if best is None else min(best, v // e)
        p += 1
    out.append(str(best))
print("\n".join(out))""", "javascript": r"""
const d = require("fs").readFileSync(0, "utf8").trim().split(/\s+/);
const out = [];
for (let i = 0; i < Number(d[0]); i++) {
  const n = BigInt(d[1 + 2 * i]);
  let b = Number(d[2 + 2 * i]), best = -1n;
  for (let p = 2; b > 1; p++) {
    if (b % p) continue;
    let e = 0;
    while (b % p === 0) { b /= p; e++; }
    const P = BigInt(p);
    let v = 0n;
    for (let m = n / P; m; m /= P) v += m;
    const z = v / BigInt(e);
    if (best < 0n || z < best) best = z;
  }
  out.push(String(best));
}
console.log(out.join("\n"));""", "php": r"""
<?php
$d = preg_split('/\s+/', trim(stream_get_contents(STDIN)));
$out = [];
for ($i = 0; $i < (int) $d[0]; $i++) {
    $n = (int) $d[1 + 2 * $i];
    $b = (int) $d[2 + 2 * $i];
    $best = -1;
    for ($p = 2; $b > 1; $p++) {
        if ($b % $p) continue;
        $e = 0;
        while ($b % $p === 0) { $b = intdiv($b, $p); $e++; }
        $v = 0;
        for ($m = intdiv($n, $p); $m; $m = intdiv($m, $p)) $v += $m;
        $z = intdiv($v, $e);
        if ($best < 0 || $z < $best) $best = $z;
    }
    $out[] = $best;
}
echo implode("\n", $out), "\n";"""}, time=3),

    ch("math-racine", 0, "mini", "Racine numérique", "chiffres",
       "Lisez un entier positif ou nul, écrit avec jusqu'à 200 000 chiffres. On remplace le nombre par la somme de ses chiffres, "
       "et on recommence jusqu'à obtenir un seul chiffre : c'est sa racine numérique. Le nombre d'étapes est sa persistance additive. "
       "Affichez « racine persistance ». Exemple : 9875 → 29 → 11 → 2, soit « 2 3 ».",
       [("9875", "2 3"), ("7", "7 0"), ("0", "0 0"), ("999999999999", "9 2"), ("19999999999", "1 3"), _RN1, _RN2, _RN3],
       ["Le nombre ne tient dans aucun type entier (et Python refuse de convertir plus de 4 300 chiffres) : traitez-le comme une chaîne.",
        "La première somme se fait chiffre par chiffre sur la chaîne ; elle vaut au plus 9 × 200 000 et tient dans un entier.",
        "Les étapes suivantes sont toutes petites. Attention : un nombre d'un seul chiffre a une persistance de 0."],
       {"cpp": r"""
#include <iostream>
#include <string>
int main() {
    std::string s;
    std::cin >> s;
    if (s.size() == 1) { std::cout << s << " 0" << std::endl; return 0; }
    long long v = 0;
    for (char c : s) v += c - '0';
    int p = 1;
    while (v >= 10) {
        long long w = 0;
        for (; v; v /= 10) w += v % 10;
        v = w;
        ++p;
    }
    std::cout << v << ' ' << p << std::endl;
}""", "c": r"""
#include <stdio.h>
#include <ctype.h>
int main(void) {
    long long v = 0, len = 0, first = 0;
    int c;
    while ((c = getchar()) != EOF && isdigit(c)) {
        if (!len) first = c - '0';
        v += c - '0';
        ++len;
    }
    if (len <= 1) { printf("%lld 0\n", first); return 0; }
    int p = 1;
    while (v >= 10) {
        long long w = 0;
        for (; v; v /= 10) w += v % 10;
        v = w;
        ++p;
    }
    printf("%lld %d\n", v, p);
    return 0;
}""", "python": r"""
s = input().strip()
if len(s) == 1:
    print(s, 0)
else:
    v = sum(int(c) * s.count(c) for c in "123456789")
    p = 1
    while v >= 10:
        v = sum(map(int, str(v)))
        p += 1
    print(v, p)""", "javascript": r"""
const s = require("fs").readFileSync(0, "utf8").trim();
if (s.length === 1) console.log(`${s} 0`);
else {
  let v = 0, p = 1;
  for (let i = 0; i < s.length; i++) v += s.charCodeAt(i) - 48;
  while (v >= 10) {
    let w = 0;
    for (; v; v = Math.floor(v / 10)) w += v % 10;
    v = w;
    p++;
  }
  console.log(`${v} ${p}`);
}""", "php": r"""
<?php
$s = trim(fgets(STDIN));
if (strlen($s) === 1) { echo "$s 0\n"; exit; }
$v = array_sum(str_split($s));
$p = 1;
while ($v >= 10) {
    $v = array_sum(str_split((string) $v));
    $p++;
}
echo "$v $p\n";"""}),

    ch("math-multiples", 0, "mini", "Multiples dans un intervalle", "divisibilité",
       "Première ligne : T. Puis T lignes « a b x y » avec −10^18 ≤ a ≤ b ≤ 10^18 et 1 ≤ x, y ≤ 10^9. "
       "Pour chaque ligne, affichez combien d'entiers de l'intervalle [a, b] sont divisibles par x ou par y. Zéro est divisible par tout le monde.",
       [("3\n1 10 2 3\n-10 10 5 5\n0 0 7 3", "7\n5\n1"), ("2\n-7 -1 2 3\n1 1000000000000000000 1000000000 999999999", "4\n2000000000"),
        ("3\n-1000000000000000000 1000000000000000000 1 1\n5 5 2 4\n-6 -6 4 6", "2000000000000000001\n0\n1"), _MU],
       ["Le nombre de multiples de m dans [a, b] vaut ⌊b / m⌋ − ⌊(a − 1) / m⌋, avec la partie entière mathématique (vers −∞).",
        "En C, C++, JavaScript et PHP, la division entière tronque vers zéro : pour un nombre négatif non divisible, retirez 1.",
        "Inclusion-exclusion : multiples de x + multiples de y − multiples de PPCM(x, y), avec PPCM = x / PGCD(x, y) × y (au plus 10^18)."],
       {"cpp": r"""
#include <iostream>
#include <numeric>
long long fl(long long n, long long m) { long long q = n / m; return (n % m != 0 && n < 0) ? q - 1 : q; }
long long cnt(long long a, long long b, long long m) { return fl(b, m) - fl(a - 1, m); }
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int t;
    std::cin >> t;
    while (t--) {
        long long a, b, x, y;
        std::cin >> a >> b >> x >> y;
        std::cout << cnt(a, b, x) + cnt(a, b, y) - cnt(a, b, x / std::gcd(x, y) * y) << '\n';
    }
}""", "c": r"""
#include <stdio.h>
static long long fl(long long n, long long m) { long long q = n / m; return (n % m != 0 && n < 0) ? q - 1 : q; }
static long long cnt(long long a, long long b, long long m) { return fl(b, m) - fl(a - 1, m); }
static long long pgcd(long long a, long long b) { while (b) { long long r = a % b; a = b; b = r; } return a; }
int main(void) {
    int t;
    if (scanf("%d", &t) != 1) return 1;
    while (t--) {
        long long a, b, x, y;
        if (scanf("%lld %lld %lld %lld", &a, &b, &x, &y) != 4) return 1;
        printf("%lld\n", cnt(a, b, x) + cnt(a, b, y) - cnt(a, b, x / pgcd(x, y) * y));
    }
    return 0;
}""", "python": r"""
import sys
from math import gcd
d = sys.stdin.buffer.read().split()
out = []
for i in range(int(d[0])):
    a, b, x, y = map(int, d[1 + 4 * i:5 + 4 * i])
    cnt = lambda m: b // m - (a - 1) // m
    out.append(cnt(x) + cnt(y) - cnt(x // gcd(x, y) * y))
print("\n".join(map(str, out)))""", "javascript": r"""
const d = require("fs").readFileSync(0, "utf8").trim().split(/\s+/);
const fl = (n, m) => { const q = n / m; return n % m !== 0n && n < 0n ? q - 1n : q; };
const pgcd = (x, y) => { while (y) [x, y] = [y, x % y]; return x; };
const out = [];
for (let i = 0; i < Number(d[0]); i++) {
  const [a, b, x, y] = d.slice(1 + 4 * i, 5 + 4 * i).map(BigInt);
  const cnt = m => fl(b, m) - fl(a - 1n, m);
  out.push(String(cnt(x) + cnt(y) - cnt(x / pgcd(x, y) * y)));
}
console.log(out.join("\n"));""", "php": r"""
<?php
function fl($n, $m) { $q = intdiv($n, $m); return ($n % $m !== 0 && $n < 0) ? $q - 1 : $q; }
function cnt($a, $b, $m) { return fl($b, $m) - fl($a - 1, $m); }
function pgcd($a, $b) { while ($b) { $r = $a % $b; $a = $b; $b = $r; } return $a; }
$d = preg_split('/\s+/', trim(stream_get_contents(STDIN)));
$out = [];
for ($i = 0; $i < (int) $d[0]; $i++) {
    [$a, $b, $x, $y] = array_map('intval', array_slice($d, 1 + 4 * $i, 4));
    $out[] = cnt($a, $b, $x) + cnt($a, $b, $y) - cnt($a, $b, intdiv($x, pgcd($x, $y)) * $y);
}
echo implode("\n", $out), "\n";"""}, time=3),

    ch("math-negabinaire", 0, "mini", "La base −2", "bases de numération",
       "Tout entier, positif ou négatif, s'écrit de façon unique en base −2 avec les chiffres 0 et 1, sans signe : "
       "110 vaut 1·(−2)² + 1·(−2) + 0 = 2. Première ligne : T. Puis T entiers n avec |n| ≤ 10^18 : affichez l'écriture de chacun en base −2.",
       [("4\n2\n3\n-1\n0", "110\n111\n11\n0"), ("3\n-2\n6\n-3", "10\n11010\n1101"),
        ("3\n1000000000000000000\n-1000000000000000000\n1", None), _NB],
       ["Comme pour la base 2 : on prend le reste, puis on divise, et on lit les restes à l'envers.",
        "Le reste doit valoir 0 ou 1 : utilisez la division euclidienne (reste positif), pas l'opérateur % brut.",
        "À chaque étape : r = n mod 2 (0 ou 1), puis n = (n − r) / (−2), division exacte. Jusqu'à n = 0."],
       {"cpp": r"""
#include <iostream>
#include <string>
#include <algorithm>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int t;
    std::cin >> t;
    while (t--) {
        long long n;
        std::cin >> n;
        std::string s = n ? "" : "0";
        while (n) {
            long long r = ((n % 2) + 2) % 2;
            s += char('0' + r);
            n = (n - r) / -2;
        }
        std::reverse(s.begin(), s.end());
        std::cout << s << '\n';
    }
}""", "c": r"""
#include <stdio.h>
int main(void) {
    int t;
    if (scanf("%d", &t) != 1) return 1;
    while (t--) {
        long long n;
        if (scanf("%lld", &n) != 1) return 1;
        char s[80];
        int k = 0;
        if (!n) s[k++] = '0';
        while (n) {
            long long r = ((n % 2) + 2) % 2;
            s[k++] = (char) ('0' + r);
            n = (n - r) / -2;
        }
        while (k) putchar(s[--k]);
        putchar('\n');
    }
    return 0;
}""", "python": r"""
import sys
d = sys.stdin.buffer.read().split()
out = []
for i in range(int(d[0])):
    n, s = int(d[1 + i]), []
    while n:
        r = n % 2
        s.append("01"[r])
        n = (n - r) // -2
    out.append("".join(reversed(s)) or "0")
print("\n".join(out))""", "javascript": r"""
const d = require("fs").readFileSync(0, "utf8").trim().split(/\s+/);
const out = [];
for (let i = 0; i < Number(d[0]); i++) {
  let n = BigInt(d[1 + i]), s = "";
  while (n) {
    const r = ((n % 2n) + 2n) % 2n;
    s = (r ? "1" : "0") + s;
    n = (n - r) / -2n;
  }
  out.push(s || "0");
}
console.log(out.join("\n"));""", "php": r"""
<?php
$d = preg_split('/\s+/', trim(stream_get_contents(STDIN)));
$out = [];
for ($i = 0; $i < (int) $d[0]; $i++) {
    $n = (int) $d[1 + $i];
    $s = "";
    while ($n) {
        $r = (($n % 2) + 2) % 2;
        $s .= $r;
        $n = intdiv($n - $r, -2);
    }
    $out[] = $s === "" ? "0" : strrev($s);
}
echo implode("\n", $out), "\n";"""}),

    ch("math-palindromes", 0, "mini", "Doubles palindromes", "chiffres",
       "Lisez n et k (2 ≤ n ≤ 10^9, 2 ≤ k ≤ 9). Combien d'entiers x avec 1 ≤ x < n sont des palindromes à la fois en base 10 et en base k, "
       "et quelle est leur somme ? Affichez « nombre somme ». Exemple : 9 = 1001 en base 2 est un double palindrome.",
       [("10 2", "5 25"), ("1000000 2", "19 872187"), ("2 5", "1 1"), ("1 2", "0 0"), ("1000 3", None), ("1000000000 2", None),
        ("1000000000 3", None), ("999999999 9", None), ("123456789 7", None), ("1000000000 5", None)],
       ["Tester les 10^9 nombres un par un est bien trop lent.",
        "Il n'y a qu'environ 110 000 palindromes décimaux sous 10^9 : fabriquez-les directement à partir de leur première moitié.",
        "Pour une moitié p et une longueur impaire, recopiez les chiffres de p / 10 à l'envers derrière p ; pour une longueur paire, ceux de p. Puis testez la base k."],
       {"cpp": r"""
#include <iostream>
bool pal(long long x, int k) {
    long long r = 0;
    for (long long y = x; y; y /= k) r = r * k + y % k;
    return r == x;
}
int main() {
    long long n;
    int k;
    std::cin >> n >> k;
    long long c = 0, s = 0, lo = 1;
    for (int L = 1; lo < n; ++L, lo *= 10) {
        long long a = 1, b;
        for (int i = 1; i < (L + 1) / 2; ++i) a *= 10;
        b = a * 10;
        for (long long p = a; p < b; ++p) {
            long long x = p;
            for (long long q = L % 2 ? p / 10 : p; q; q /= 10) x = x * 10 + q % 10;
            if (x >= n) break;
            if (pal(x, k)) { ++c; s += x; }
        }
    }
    std::cout << c << ' ' << s << std::endl;
}""", "c": r"""
#include <stdio.h>
static int pal(long long x, int k) {
    long long r = 0;
    for (long long y = x; y; y /= k) r = r * k + y % k;
    return r == x;
}
int main(void) {
    long long n;
    int k;
    if (scanf("%lld %d", &n, &k) != 2) return 1;
    long long c = 0, s = 0, lo = 1;
    for (int L = 1; lo < n; ++L, lo *= 10) {
        long long a = 1;
        for (int i = 1; i < (L + 1) / 2; ++i) a *= 10;
        for (long long p = a; p < a * 10; ++p) {
            long long x = p;
            for (long long q = L % 2 ? p / 10 : p; q; q /= 10) x = x * 10 + q % 10;
            if (x >= n) break;
            if (pal(x, k)) { ++c; s += x; }
        }
    }
    printf("%lld %lld\n", c, s);
    return 0;
}""", "python": r"""
n, k = map(int, input().split())
c = s = 0
L = 1
while 10 ** (L - 1) < n:
    h = (L + 1) // 2
    for p in range(10 ** (h - 1), 10 ** h):
        t = str(p)
        x = int(t + t[::-1][L % 2:])
        if x >= n:
            break
        r, y = 0, x
        while y:
            r = r * k + y % k
            y //= k
        if r == x:
            c += 1
            s += x
    L += 1
print(c, s)""", "javascript": r"""
const [n, k] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
let c = 0, s = 0;
for (let L = 1, lo = 1; lo < n; L++, lo *= 10) {
  const a = 10 ** (Math.floor((L + 1) / 2) - 1);
  for (let p = a; p < a * 10; p++) {
    let x = p;
    for (let q = L % 2 ? Math.floor(p / 10) : p; q; q = Math.floor(q / 10)) x = x * 10 + q % 10;
    if (x >= n) break;
    let r = 0;
    for (let y = x; y; y = Math.floor(y / k)) r = r * k + y % k;
    if (r === x) { c++; s += x; }
  }
}
console.log(`${c} ${s}`);""", "php": r"""
<?php
[$n, $k] = array_map('intval', preg_split('/\s+/', trim(fgets(STDIN))));
$c = 0;
$s = 0;
for ($L = 1, $lo = 1; $lo < $n; $L++, $lo *= 10) {
    $a = 10 ** (intdiv($L + 1, 2) - 1);
    for ($p = $a; $p < $a * 10; $p++) {
        $x = $p;
        for ($q = $L % 2 ? intdiv($p, 10) : $p; $q; $q = intdiv($q, 10)) $x = $x * 10 + $q % 10;
        if ($x >= $n) break;
        $r = 0;
        for ($y = $x; $y; $y = intdiv($y, $k)) $r = $r * $k + $y % $k;
        if ($r === $x) { $c++; $s += $x; }
    }
}
echo "$c $s\n";"""}, time=5),

    ch("math-pythagore", 0, "mini", "Triplets pythagoriciens", "triplets",
       "Lisez P (1 ≤ P ≤ 3 000 000). Un triplet pythagoricien est un triplet d'entiers 0 < a < b < c avec a² + b² = c². "
       "Il est primitif si PGCD(a, b, c) = 1. Parmi les triplets de périmètre a + b + c ≤ P, affichez « primitifs total » : "
       "le nombre de triplets primitifs puis le nombre total de triplets.",
       [("12", "1 1"), ("30", "2 3"), ("11", "0 0"), ("1", "0 0"), ("100", None), ("1000", None), ("1000000", None), ("2999999", None), ("3000000", None)],
       ["Parcourir tous les couples (a, b) est bien trop lent pour 3 millions.",
        "Formule d'Euclide : les triplets primitifs sont exactement a = m² − n², b = 2mn, c = m² + n² avec m > n ≥ 1, m − n impair et PGCD(m, n) = 1. Leur périmètre vaut 2m(m + n).",
        "Chaque triplet primitif de périmètre p engendre ⌊P / p⌋ triplets en tout (ses multiples k·(a, b, c))."],
       {"cpp": r"""
#include <iostream>
#include <numeric>
int main() {
    long long P;
    std::cin >> P;
    long long prim = 0, total = 0;
    for (long long m = 2; 2 * m * (m + 1) <= P; ++m)
        for (long long n = (m % 2) ? 2 : 1; n < m; n += 2) {
            long long p = 2 * m * (m + n);
            if (p > P) break;
            if (std::gcd(m, n) != 1) continue;
            ++prim;
            total += P / p;
        }
    std::cout << prim << ' ' << total << std::endl;
}""", "c": r"""
#include <stdio.h>
static long long pgcd(long long a, long long b) { while (b) { long long r = a % b; a = b; b = r; } return a; }
int main(void) {
    long long P;
    if (scanf("%lld", &P) != 1) return 1;
    long long prim = 0, total = 0;
    for (long long m = 2; 2 * m * (m + 1) <= P; ++m)
        for (long long n = (m % 2) ? 2 : 1; n < m; n += 2) {
            long long p = 2 * m * (m + n);
            if (p > P) break;
            if (pgcd(m, n) != 1) continue;
            ++prim;
            total += P / p;
        }
    printf("%lld %lld\n", prim, total);
    return 0;
}""", "python": r"""
from math import gcd
P = int(input())
prim = total = 0
m = 2
while 2 * m * (m + 1) <= P:
    for n in range(2 if m % 2 else 1, m, 2):
        p = 2 * m * (m + n)
        if p > P:
            break
        if gcd(m, n) == 1:
            prim += 1
            total += P // p
    m += 1
print(prim, total)""", "javascript": r"""
const P = Number(require("fs").readFileSync(0, "utf8").trim());
const pgcd = (a, b) => { while (b) [a, b] = [b, a % b]; return a; };
let prim = 0, total = 0;
for (let m = 2; 2 * m * (m + 1) <= P; m++)
  for (let n = m % 2 ? 2 : 1; n < m; n += 2) {
    const p = 2 * m * (m + n);
    if (p > P) break;
    if (pgcd(m, n) !== 1) continue;
    prim++;
    total += Math.floor(P / p);
  }
console.log(`${prim} ${total}`);""", "php": r"""
<?php
function pgcd($a, $b) { while ($b) { $r = $a % $b; $a = $b; $b = $r; } return $a; }
$P = (int) trim(fgets(STDIN));
$prim = 0;
$total = 0;
for ($m = 2; 2 * $m * ($m + 1) <= $P; $m++)
    for ($n = $m % 2 ? 2 : 1; $n < $m; $n += 2) {
        $p = 2 * $m * ($m + $n);
        if ($p > $P) break;
        if (pgcd($m, $n) !== 1) continue;
        $prim++;
        $total += intdiv($P, $p);
    }
echo "$prim $total\n";"""}),

    ch("math-quotients", 0, "exam", "Examen : la somme des quotients", "sommes de quotients",
       "Lisez n (1 ≤ n ≤ 10^11). Affichez deux lignes : D(n) = ⌊n/1⌋ + ⌊n/2⌋ + … + ⌊n/n⌋, qui compte les diviseurs de tous les entiers de 1 à n, "
       "puis S(n) = 1·⌊n/1⌋ + 2·⌊n/2⌋ + … + n·⌊n/n⌋, la somme de tous les diviseurs de tous les entiers de 1 à n, modulo 1 000 000 007. "
       "Limite : 2 secondes, donc pas question de faire 10^11 tours de boucle.",
       [("6", "14\n33"), ("1", "1\n1"), ("10", "27\n87"), ("2", "3\n4"), ("100000000000", None), ("99999999999", None),
        ("12345678910", None), ("1000000007", None), ("7777777777", None), ("999999", None)],
       ["⌊n/k⌋ ne prend qu'environ 2√n valeurs différentes : les k qui donnent le même quotient forment des blocs consécutifs.",
        "Si q = ⌊n/l⌋, le bloc qui commence en l se termine en r = ⌊n/q⌋. Il ajoute q × (r − l + 1) à D, et q × (l + … + r) à S.",
        "l + … + r = (l + r)(r − l + 1) / 2 : divisez par 2 le facteur pair avant de réduire modulo 10^9 + 7, et gardez chaque produit sous 10^18 (BigInt en JavaScript)."],
       {"cpp": r"""
#include <iostream>
int main() {
    const long long M = 1000000007;
    long long n;
    std::cin >> n;
    long long D = 0, S = 0;
    for (long long l = 1, r; l <= n; l = r + 1) {
        long long q = n / l;
        r = n / q;
        D += q * (r - l + 1);
        long long a = l + r, b = r - l + 1;
        if (a % 2 == 0) a /= 2; else b /= 2;
        S = (S + a % M * (b % M) % M * (q % M)) % M;
    }
    std::cout << D << '\n' << S << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    const long long M = 1000000007;
    long long n;
    if (scanf("%lld", &n) != 1) return 1;
    long long D = 0, S = 0;
    for (long long l = 1, r; l <= n; l = r + 1) {
        long long q = n / l;
        r = n / q;
        D += q * (r - l + 1);
        long long a = l + r, b = r - l + 1;
        if (a % 2 == 0) a /= 2; else b /= 2;
        S = (S + a % M * (b % M) % M * (q % M)) % M;
    }
    printf("%lld\n%lld\n", D, S);
    return 0;
}""", "python": r"""
M = 10 ** 9 + 7
n = int(input())
D = S = 0
l = 1
while l <= n:
    q = n // l
    r = n // q
    D += q * (r - l + 1)
    S += q * (l + r) * (r - l + 1) // 2
    l = r + 1
print(D)
print(S % M)""", "javascript": r"""
const M = 1000000007n;
const n = Number(require("fs").readFileSync(0, "utf8").trim());
let D = 0, S = 0n;
for (let l = 1, r; l <= n; l = r + 1) {
  const q = Math.floor(n / l);
  r = Math.floor(n / q);
  D += q * (r - l + 1);
  let a = l + r, b = r - l + 1;
  if (a % 2 === 0) a /= 2; else b /= 2;
  S = (S + BigInt(a) % M * BigInt(b % 1000000007) % M * BigInt(q % 1000000007)) % M;
}
console.log(`${D}\n${S}`);""", "php": r"""
<?php
const M = 1000000007;
$n = (int) trim(fgets(STDIN));
$D = 0;
$S = 0;
for ($l = 1; $l <= $n; $l = $r + 1) {
    $q = intdiv($n, $l);
    $r = intdiv($n, $q);
    $D += $q * ($r - $l + 1);
    $a = $l + $r;
    $b = $r - $l + 1;
    if ($a % 2 === 0) $a = intdiv($a, 2); else $b = intdiv($b, 2);
    $S = ($S + $a % M * ($b % M) % M * ($q % M)) % M;
}
echo "$D\n$S\n";"""}, minutes=40, time=3),
]
