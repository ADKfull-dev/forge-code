# -*- coding: utf-8 -*-
"""Palier 1 — Les boucles : for/while, accumulateurs, boucles imbriquées, lecture jusqu'à la fin."""
from .base import ch, lines


def _forgecode(n):
    return lines("ForgeCode" if i % 15 == 0 else "Forge" if i % 3 == 0 else "Code" if i % 5 == 0 else i for i in range(1, n + 1))


def _sapin(n):
    return lines([" " * (n - i) + "*" * (2 * i - 1) for i in range(1, n + 1)] + [" " * (n - 1) + "|"])


_DIV_1E12 = " ".join(map(str, sorted(2 ** i * 5 ** j for i in range(13) for j in range(13))))

DEFIS = [
    ch("compte", 1, "mini", "Compter jusqu'à n", "boucles",
       "Lisez n et affichez les nombres de 1 à n, un par ligne (rien si n vaut 0).",
       [("3", "1\n2\n3"), ("1", "1"), ("0", ""), ("10", lines(range(1, 11))), ("1000", lines(range(1, 1001)))],
       ["Une boucle qui va de 1 à n inclus.", "for (int i = 1; i <= n; i++) en C/C++/JS/PHP ; for i in range(1, n + 1) en Python.",
        "Chaque nombre sur sa propre ligne."],
       {"cpp": r"""
#include <iostream>
int main() {
    int n;
    std::cin >> n;
    for (int i = 1; i <= n; ++i) std::cout << i << "\n";
}""", "c": r"""
#include <stdio.h>
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 1;
    for (int i = 1; i <= n; ++i) printf("%d\n", i);
    return 0;
}""", "python": r"""
for i in range(1, int(input()) + 1):
    print(i)""", "javascript": r"""
const n = parseInt(require("fs").readFileSync(0, "utf8"), 10);
const out = [];
for (let i = 1; i <= n; i++) out.push(i);
if (n > 0) console.log(out.join("\n"));""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
for ($i = 1; $i <= $n; $i++) echo $i, "\n";"""}),

    ch("table", 1, "mini", "Table de multiplication", "boucles",
       "Lisez n et affichez sa table de 1 à 10 sous la forme « n x i = résultat ».",
       [("3", lines(f"3 x {i} = {3 * i}" for i in range(1, 11))), ("7", lines(f"7 x {i} = {7 * i}" for i in range(1, 11))),
        ("0", lines(f"0 x {i} = 0" for i in range(1, 11))), ("-2", lines(f"-2 x {i} = {-2 * i}" for i in range(1, 11)))],
       ["Une boucle de 1 à 10.", "À chaque tour, affichez n, i et n * i.", "Respectez exactement les espaces autour de « x » et « = »."],
       {"cpp": r"""
#include <iostream>
int main() {
    int n;
    std::cin >> n;
    for (int i = 1; i <= 10; ++i) std::cout << n << " x " << i << " = " << n * i << "\n";
}""", "c": r"""
#include <stdio.h>
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 1;
    for (int i = 1; i <= 10; ++i) printf("%d x %d = %d\n", n, i, n * i);
    return 0;
}""", "python": r"""
n = int(input())
for i in range(1, 11):
    print(f"{n} x {i} = {n * i}")""", "javascript": r"""
const n = parseInt(require("fs").readFileSync(0, "utf8"), 10);
for (let i = 1; i <= 10; i++) console.log(`${n} x ${i} = ${n * i}`);""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
for ($i = 1; $i <= 10; $i++) echo "$n x $i = ", $n * $i, "\n";"""}),

    ch("chiffres", 1, "mini", "Somme des chiffres", "boucles",
       "Lisez un entier positif (jusqu'à 18 chiffres) et affichez la somme de ses chiffres.",
       [("123", "6"), ("9", "9"), ("0", "0"), ("999999999999999999", "162"), ("100000", "1"), ("4071", "12")],
       ["Le dernier chiffre de n est n % 10.", "Divisez n par 10 pour enlever le dernier chiffre, jusqu'à ce qu'il vaille 0.",
        "On peut aussi lire le nombre comme du texte et additionner chaque caractère (c - '0')."],
       {"cpp": r"""
#include <iostream>
int main() {
    long long n;
    std::cin >> n;
    int s = 0;
    while (n > 0) { s += n % 10; n /= 10; }
    std::cout << s << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    long long n;
    if (scanf("%lld", &n) != 1) return 1;
    int s = 0;
    while (n > 0) { s += n % 10; n /= 10; }
    printf("%d\n", s);
    return 0;
}""", "python": r"""
print(sum(int(c) for c in input().strip()))""", "javascript": r"""
const s = require("fs").readFileSync(0, "utf8").trim();
let t = 0;
for (const c of s) t += c.charCodeAt(0) - 48;
console.log(t);""", "php": r"""
<?php
$s = trim(fgets(STDIN));
echo array_sum(str_split($s)), "\n";"""}),

    ch("fact", 1, "mini", "Factorielle", "boucles",
       "Lisez n (entre 0 et 20) et affichez n! = 1 × 2 × … × n (0! vaut 1).",
       [("5", "120"), ("0", "1"), ("1", "1"), ("10", "3628800"), ("20", "2432902008176640000")],
       ["Partez de 1 et multipliez par chaque nombre de 2 à n.", "20! est énorme : il faut un entier 64 bits (long long).",
        "JavaScript : les Number perdent en précision au-delà de 2^53, utilisez BigInt (1n, 2n…)."],
       {"cpp": r"""
#include <iostream>
int main() {
    int n;
    std::cin >> n;
    unsigned long long f = 1;
    for (int i = 2; i <= n; ++i) f *= i;
    std::cout << f << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 1;
    unsigned long long f = 1;
    for (int i = 2; i <= n; ++i) f *= i;
    printf("%llu\n", f);
    return 0;
}""", "python": r"""
f = 1
for i in range(2, int(input()) + 1):
    f *= i
print(f)""", "javascript": r"""
const n = parseInt(require("fs").readFileSync(0, "utf8"), 10);
let f = 1n;
for (let i = 2n; i <= BigInt(n); i++) f *= i;
console.log(f.toString());""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
$f = 1;
for ($i = 2; $i <= $n; $i++) $f *= $i;
echo $f, "\n";"""}),

    ch("sapin", 1, "mini", "Le sapin", "boucles imbriquées",
       "Lisez n (1 à 50) et dessinez un sapin de n étages : la ligne i (de 1 à n) contient n - i espaces puis 2i - 1 étoiles. "
       "Terminez par un tronc : n - 1 espaces puis « | ». Les espaces en fin de ligne sont ignorés.",
       [("3", _sapin(3)), ("1", _sapin(1)), ("5", _sapin(5)), ("12", _sapin(12)), ("50", _sapin(50))],
       ["Une boucle pour les lignes, et dans chaque ligne une boucle pour les espaces puis une pour les étoiles.",
        "Ligne i : n - i espaces, 2 × i - 1 étoiles.",
        "Raccourcis : \" \" * k en Python, \" \".repeat(k) en JS, str_repeat(\" \", k) en PHP, std::string(k, ' ') en C++."],
       {"cpp": r"""
#include <iostream>
#include <string>
int main() {
    int n;
    std::cin >> n;
    for (int i = 1; i <= n; ++i) std::cout << std::string(n - i, ' ') << std::string(2 * i - 1, '*') << "\n";
    std::cout << std::string(n - 1, ' ') << "|\n";
}""", "c": r"""
#include <stdio.h>
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 1;
    for (int i = 1; i <= n; ++i) {
        for (int k = 0; k < n - i; ++k) putchar(' ');
        for (int k = 0; k < 2 * i - 1; ++k) putchar('*');
        putchar('\n');
    }
    for (int k = 0; k < n - 1; ++k) putchar(' ');
    puts("|");
    return 0;
}""", "python": r"""
n = int(input())
for i in range(1, n + 1):
    print(" " * (n - i) + "*" * (2 * i - 1))
print(" " * (n - 1) + "|")""", "javascript": r"""
const n = parseInt(require("fs").readFileSync(0, "utf8"), 10);
for (let i = 1; i <= n; i++) console.log(" ".repeat(n - i) + "*".repeat(2 * i - 1));
console.log(" ".repeat(n - 1) + "|");""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
for ($i = 1; $i <= $n; $i++) echo str_repeat(" ", $n - $i), str_repeat("*", 2 * $i - 1), "\n";
echo str_repeat(" ", $n - 1), "|\n";"""}),

    ch("diviseurs", 1, "mini", "Tous les diviseurs", "boucles",
       "Lisez n (1 ≤ n ≤ 10^12) et affichez tous ses diviseurs dans l'ordre croissant, séparés par des espaces.",
       [("12", "1 2 3 4 6 12"), ("1", "1"), ("13", "1 13"), ("36", "1 2 3 4 6 9 12 18 36"), ("999999999989", "1 999999999989"),
        ("1000000000000", _DIV_1E12)],
       ["Tester tous les nombres de 1 à n est trop lent pour 10^12.",
        "Les diviseurs vont par paires : si d divise n, n / d aussi. Il suffit d'aller jusqu'à √n (tant que d × d ≤ n).",
        "Rangez les petits diviseurs dans un tableau et les grands dans un autre, à afficher à l'envers. Attention aux carrés parfaits (36 = 6 × 6)."],
       {"cpp": r"""
#include <iostream>
#include <vector>
int main() {
    long long n;
    std::cin >> n;
    std::vector<long long> a, b;
    for (long long d = 1; d * d <= n; ++d)
        if (n % d == 0) { a.push_back(d); if (d != n / d) b.push_back(n / d); }
    for (auto it = b.rbegin(); it != b.rend(); ++it) a.push_back(*it);
    for (size_t i = 0; i < a.size(); ++i) std::cout << (i ? " " : "") << a[i];
    std::cout << "\n";
}""", "c": r"""
#include <stdio.h>
int main(void) {
    long long n;
    static long long a[8000], b[8000];
    int na = 0, nb = 0;
    if (scanf("%lld", &n) != 1) return 1;
    for (long long d = 1; d * d <= n; ++d)
        if (n % d == 0) { a[na++] = d; if (d != n / d) b[nb++] = n / d; }
    for (int i = 0; i < na; ++i) printf(i ? " %lld" : "%lld", a[i]);
    for (int i = nb - 1; i >= 0; --i) printf(" %lld", b[i]);
    printf("\n");
    return 0;
}""", "python": r"""
n = int(input())
a, b = [], []
d = 1
while d * d <= n:
    if n % d == 0:
        a.append(d)
        if d != n // d:
            b.append(n // d)
    d += 1
print(*(a + b[::-1]))""", "javascript": r"""
const n = Number(require("fs").readFileSync(0, "utf8").trim());
const a = [], b = [];
for (let d = 1; d * d <= n; d++)
  if (n % d === 0) { a.push(d); if (d !== n / d) b.push(n / d); }
console.log(a.concat(b.reverse()).join(" "));""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
$a = []; $b = [];
for ($d = 1; $d * $d <= $n; $d++)
    if ($n % $d === 0) { $a[] = $d; if ($d !== intdiv($n, $d)) $b[] = intdiv($n, $d); }
echo implode(" ", array_merge($a, array_reverse($b))), "\n";"""}, time=2),

    ch("collatz", 1, "mini", "La conjecture de Syracuse", "boucles",
       "Lisez n (1 ≤ n ≤ 10^9). Tant que n ≠ 1 : s'il est pair, divisez-le par 2, sinon remplacez-le par 3n + 1. "
       "Affichez le nombre d'étapes pour arriver à 1.",
       [("6", "8"), ("1", "0"), ("27", "111"), ("837799", "524"), ("1000000000", "100"), ("670617279", "986")],
       ["Une boucle while (n != 1) avec un compteur.",
        "La suite monte parfois très haut : partant de 670617279, elle dépasse 2^32. Utilisez un entier 64 bits.",
        "Pair : n % 2 == 0 ; la division entière : n / 2 (C, C++, JS avec Math.floor), n // 2 (Python), intdiv (PHP)."],
       {"cpp": r"""
#include <iostream>
int main() {
    long long n;
    std::cin >> n;
    int s = 0;
    while (n != 1) { n = n % 2 == 0 ? n / 2 : 3 * n + 1; ++s; }
    std::cout << s << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    long long n;
    if (scanf("%lld", &n) != 1) return 1;
    int s = 0;
    while (n != 1) { n = n % 2 == 0 ? n / 2 : 3 * n + 1; ++s; }
    printf("%d\n", s);
    return 0;
}""", "python": r"""
n = int(input())
s = 0
while n != 1:
    n = n // 2 if n % 2 == 0 else 3 * n + 1
    s += 1
print(s)""", "javascript": r"""
let n = Number(require("fs").readFileSync(0, "utf8").trim()), s = 0;
while (n !== 1) { n = n % 2 === 0 ? n / 2 : 3 * n + 1; s++; }
console.log(s);""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
$s = 0;
while ($n !== 1) { $n = $n % 2 === 0 ? intdiv($n, 2) : 3 * $n + 1; $s++; }
echo $s, "\n";"""}),

    ch("binaire", 1, "mini", "En binaire", "boucles",
       "Lisez n (0 ≤ n ≤ 10^18) et affichez son écriture en base 2, sans zéros inutiles devant. "
       "Écrivez la conversion vous-même (pas de fonction toute faite).",
       [("5", "101"), ("0", "0"), ("1", "1"), ("255", "11111111"), ("1024", "10000000000"),
        ("1000000000000000000", "110111100000101101101011001110100111011001000000000000000000")],
       ["Le dernier bit de n est n % 2 ; n / 2 enlève ce bit.",
        "Les bits sortent du plus faible au plus fort : construisez la chaîne puis inversez-la.",
        "Le cas n = 0 doit afficher « 0 ». En JavaScript, 10^18 dépasse la précision des Number : BigInt."],
       {"cpp": r"""
#include <iostream>
#include <string>
#include <algorithm>
int main() {
    unsigned long long n;
    std::cin >> n;
    std::string s;
    do { s += char('0' + n % 2); n /= 2; } while (n > 0);
    std::reverse(s.begin(), s.end());
    std::cout << s << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    unsigned long long n;
    char s[70];
    int k = 0;
    if (scanf("%llu", &n) != 1) return 1;
    do { s[k++] = (char)('0' + n % 2); n /= 2; } while (n > 0);
    while (k > 0) putchar(s[--k]);
    putchar('\n');
    return 0;
}""", "python": r"""
n = int(input())
s = ""
while True:
    s = str(n % 2) + s
    n //= 2
    if n == 0:
        break
print(s)""", "javascript": r"""
let n = BigInt(require("fs").readFileSync(0, "utf8").trim());
let s = "";
do { s = String(n % 2n) + s; n /= 2n; } while (n > 0n);
console.log(s);""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
$s = "";
do { $s = ($n % 2) . $s; $n = intdiv($n, 2); } while ($n > 0);
echo $s, "\n";""", }, banned={"python": [r"\bbin\s*\(", r"format\s*\(.*['\"]b['\"]", r":b\}"], "javascript": [r"toString\s*\(\s*2\s*\)"],
                            "php": [r"\bdecbin\b", r"base_convert", r"%b"], "cpp": [r"bitset"]}),

    ch("devine", 1, "mini", "Devine le nombre", "boucles",
       "Ligne 1 : le nombre secret. Puis une proposition par ligne, jusqu'à la bonne (elle arrive forcément). "
       "Pour chaque mauvaise proposition, affichez « plus » si le secret est plus grand, « moins » sinon. "
       "Pour la bonne, affichez « trouvé en k coups » (« trouvé en 1 coup » s'il n'a fallu qu'un essai).",
       [("42\n50\n25\n42", "moins\nplus\ntrouvé en 3 coups"), ("7\n7", "trouvé en 1 coup"), ("1\n100\n50\n2\n1", "moins\nmoins\nmoins\ntrouvé en 4 coups"),
        ("-5\n0\n-10\n-5", "moins\nplus\ntrouvé en 3 coups"), ("500\n1\n1000\n500\n12", "plus\nmoins\ntrouvé en 3 coups")],
       ["Lisez le secret, puis lisez les propositions dans une boucle.", "Arrêtez la boucle (break) dès que la proposition est la bonne : la suite de l'entrée est ignorée.",
        "Accord : « coup » au singulier si k vaut 1."],
       {"cpp": r"""
#include <iostream>
int main() {
    long long s, x;
    std::cin >> s;
    int k = 0;
    while (std::cin >> x) {
        ++k;
        if (x == s) { std::cout << "trouvé en " << k << (k == 1 ? " coup" : " coups") << "\n"; break; }
        std::cout << (s > x ? "plus" : "moins") << "\n";
    }
}""", "c": r"""
#include <stdio.h>
int main(void) {
    long long s, x;
    int k = 0;
    if (scanf("%lld", &s) != 1) return 1;
    while (scanf("%lld", &x) == 1) {
        ++k;
        if (x == s) { printf("trouvé en %d %s\n", k, k == 1 ? "coup" : "coups"); break; }
        puts(s > x ? "plus" : "moins");
    }
    return 0;
}""", "python": r"""
s = int(input())
k = 0
while True:
    x = int(input())
    k += 1
    if x == s:
        print(f"trouvé en {k} {'coup' if k == 1 else 'coups'}")
        break
    print("plus" if s > x else "moins")""", "javascript": r"""
const v = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
const s = v[0];
for (let k = 1; k < v.length; k++) {
  if (v[k] === s) { console.log(`trouvé en ${k} ${k === 1 ? "coup" : "coups"}`); break; }
  console.log(s > v[k] ? "plus" : "moins");
}""", "php": r"""
<?php
$s = (int) trim(fgets(STDIN));
$k = 0;
while (($l = fgets(STDIN)) !== false) {
    $x = (int) trim($l);
    $k++;
    if ($x === $s) { echo "trouvé en $k ", $k === 1 ? "coup" : "coups", "\n"; break; }
    echo $s > $x ? "plus" : "moins", "\n";
}"""}),

    ch("forgecode", 1, "exam", "Examen : ForgeCode", "boucles",
       "Lisez n. Pour chaque nombre de 1 à n, affichez « Forge » s'il est divisible par 3, « Code » s'il est divisible par 5, "
       "« ForgeCode » s'il est divisible par les deux, sinon le nombre lui-même. Contrainte : 30 lignes de code au plus.",
       [("5", _forgecode(5)), ("15", _forgecode(15)), ("1", "1"), ("100", _forgecode(100)), ("3000", _forgecode(3000))],
       ["Testez d'abord le cas « divisible par 3 ET par 5 ».", "Divisible par 3 et 5 = divisible par 15.",
        "L'ordre des tests compte : 15, puis 3, puis 5, puis le nombre."],
       {"cpp": r"""
#include <iostream>
int main() {
    int n;
    std::cin >> n;
    for (int i = 1; i <= n; ++i) {
        if (i % 15 == 0) std::cout << "ForgeCode\n";
        else if (i % 3 == 0) std::cout << "Forge\n";
        else if (i % 5 == 0) std::cout << "Code\n";
        else std::cout << i << "\n";
    }
}""", "c": r"""
#include <stdio.h>
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 1;
    for (int i = 1; i <= n; ++i) {
        if (i % 15 == 0) puts("ForgeCode");
        else if (i % 3 == 0) puts("Forge");
        else if (i % 5 == 0) puts("Code");
        else printf("%d\n", i);
    }
    return 0;
}""", "python": r"""
for i in range(1, int(input()) + 1):
    if i % 15 == 0:
        print("ForgeCode")
    elif i % 3 == 0:
        print("Forge")
    elif i % 5 == 0:
        print("Code")
    else:
        print(i)""", "javascript": r"""
const n = parseInt(require("fs").readFileSync(0, "utf8"), 10);
const out = [];
for (let i = 1; i <= n; i++) out.push(i % 15 === 0 ? "ForgeCode" : i % 3 === 0 ? "Forge" : i % 5 === 0 ? "Code" : String(i));
console.log(out.join("\n"));""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
for ($i = 1; $i <= $n; $i++)
    echo $i % 15 === 0 ? "ForgeCode" : ($i % 3 === 0 ? "Forge" : ($i % 5 === 0 ? "Code" : $i)), "\n";"""}, minutes=20, max_lines=30),
]
