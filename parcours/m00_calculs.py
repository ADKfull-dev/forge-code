# -*- coding: utf-8 -*-
"""Filière Mathématicien, palier 0 — Premiers calculs : puissances, divisibilité, diviseurs, PGCD, PPCM, fractions, binaire.

Palier d'entrée : un seul nombre ou une seule paire par test, des notions expliquées dans l'énoncé avec un exemple.
"""
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


_PA1 = lambda: "100\n" + lines(_rnd(97, 1, 10 ** 9, 53) + [33550336, 999999937, 735134400])
_PA2 = lambda: "100\n" + lines(_rnd(100, 999000000, 10 ** 9, 59))
_PA3 = lambda: "30\n" + lines(range(1, 31))


DEFIS = [
    ch("math-carre", 0, "mini", "Carré et cube", "puissances",
       "Le carré d'un nombre n, c'est n × n. Son cube, c'est n × n × n.\n"
       "Par exemple, le carré de 3 est 9 et son cube est 27.\n\n"
       "Entrée : un entier n, entre −1000 et 1000.\n"
       "Sortie : le carré de n, un espace, puis le cube de n.\n\n"
       "Exemple : pour 3, affichez « 9 27 ». Pour −2, affichez « 4 -8 » : un nombre négatif a un carré positif et un cube négatif.",
       [("3", "9 27"), ("-2", "4 -8"), ("0", "0 0"), ("1", "1 1"), ("1000", "1000000 1000000000"),
        ("-1000", "1000000 -1000000000"), ("7", "49 343")],
       ["Lisez n, puis calculez n * n et n * n * n.",
        "Affichez les deux résultats sur la même ligne, séparés par un seul espace.",
        "1000³ = 1 000 000 000 : cela tient encore dans un int, mais un long long ne coûte rien en C et C++."],
       {"cpp": r"""
#include <iostream>
int main() {
    long long n;
    std::cin >> n;
    std::cout << n * n << " " << n * n * n << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    long long n;
    if (scanf("%lld", &n) != 1) return 1;
    printf("%lld %lld\n", n * n, n * n * n);
    return 0;
}""", "python": r"""
n = int(input())
print(n * n, n * n * n)""", "javascript": r"""
const n = Number(require("fs").readFileSync(0, "utf8").trim());
console.log(`${n * n} ${n * n * n}`);""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
echo $n * $n, " ", $n * $n * $n, "\n";"""}),

    ch("math-diviseur", 0, "mini", "Est-ce un diviseur ?", "divisibilité",
       "On dit que b divise a quand la division de a par b tombe juste, c'est-à-dire quand le reste vaut 0.\n"
       "Par exemple, 3 divise 12 car 12 = 3 × 4. En revanche, 5 ne divise pas 12 car 12 = 5 × 2 + 2 : il reste 2.\n\n"
       "Entrée : deux entiers a et b sur une ligne, séparés par un espace (1 ≤ a ≤ 10^9 et 1 ≤ b ≤ 10^9).\n"
       "Sortie : OUI si b divise a, NON sinon.\n\n"
       "Exemple : « 12 3 » donne OUI, « 12 5 » donne NON.",
       [("12 3", "OUI"), ("12 5", "NON"), ("7 7", "OUI"), ("1 1000000000", "NON"), ("1000000000 1", "OUI"),
        ("999999999 333333333", "OUI"), ("1000000000 3", "NON")],
       ["L'opérateur % donne le reste d'une division : 12 % 5 vaut 2 et 12 % 3 vaut 0.",
        "b divise a exactement quand a % b == 0.",
        "Affichez OUI ou NON en majuscules, sans accent ni ponctuation."],
       {"cpp": r"""
#include <iostream>
int main() {
    long long a, b;
    std::cin >> a >> b;
    std::cout << (a % b == 0 ? "OUI" : "NON") << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    long long a, b;
    if (scanf("%lld %lld", &a, &b) != 2) return 1;
    puts(a % b == 0 ? "OUI" : "NON");
    return 0;
}""", "python": r"""
a, b = map(int, input().split())
print("OUI" if a % b == 0 else "NON")""", "javascript": r"""
const [a, b] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
console.log(a % b === 0 ? "OUI" : "NON");""", "php": r"""
<?php
[$a, $b] = array_map('intval', preg_split('/\s+/', trim(fgets(STDIN))));
echo $a % $b === 0 ? "OUI" : "NON", "\n";"""}),

    ch("math-division", 0, "mini", "Quotient et reste", "division euclidienne",
       "Diviser a par b, c'est trouver combien de fois b « rentre » dans a (le quotient q) et ce qu'il reste (le reste r).\n"
       "On a toujours a = b × q + r, avec un reste r compris entre 0 et b − 1.\n"
       "Par exemple, 17 = 5 × 3 + 2 : le quotient de 17 par 5 est 3 et le reste est 2.\n\n"
       "Entrée : deux entiers a et b sur une ligne (0 ≤ a ≤ 10^18 et 1 ≤ b ≤ 10^18).\n"
       "Sortie : le quotient q, un espace, puis le reste r.\n\n"
       "Exemple : « 17 5 » donne « 3 2 ». « 3 10 » donne « 0 3 », car 10 ne rentre aucune fois dans 3.",
       [("17 5", "3 2"), ("3 10", "0 3"), ("20 4", "5 0"), ("0 7", "0 0"),
        ("1000000000000000000 3", "333333333333333333 1"),
        ("999999999999999999 1000000000000000000", "0 999999999999999999"),
        ("123456789012345678 1000", "123456789012345 678")],
       ["Entre deux entiers, / donne le quotient (en C, C++ et Java) et % donne le reste. En Python, le quotient s'écrit //.",
        "Les nombres vont jusqu'à 10^18 : un int ne suffit pas, prenez un long long en C et C++.",
        "En JavaScript, les nombres ordinaires perdent en précision au-delà de 9 × 10^15 : utilisez BigInt."],
       {"cpp": r"""
#include <iostream>
int main() {
    long long a, b;
    std::cin >> a >> b;
    std::cout << a / b << " " << a % b << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    long long a, b;
    if (scanf("%lld %lld", &a, &b) != 2) return 1;
    printf("%lld %lld\n", a / b, a % b);
    return 0;
}""", "python": r"""
a, b = map(int, input().split())
print(a // b, a % b)""", "javascript": r"""
const [a, b] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(BigInt);
console.log(`${a / b} ${a % b}`);""", "php": r"""
<?php
[$a, $b] = array_map('intval', preg_split('/\s+/', trim(fgets(STDIN))));
echo intdiv($a, $b), " ", $a % $b, "\n";"""}),

    ch("math-chiffres", 0, "mini", "Les chiffres d'un nombre", "chiffres",
       "Le nombre 2024 s'écrit avec 4 chiffres : 2, 0, 2 et 4. La somme de ses chiffres vaut 2 + 0 + 2 + 4 = 8.\n\n"
       "Entrée : un entier n (0 ≤ n ≤ 10^18), écrit sans zéro inutile au début.\n"
       "Sortie : le nombre de chiffres de n, un espace, puis la somme de ses chiffres.\n\n"
       "Exemple : « 2024 » donne « 4 8 ». Attention, 0 s'écrit avec un chiffre : « 0 » donne « 1 0 ».",
       [("2024", "4 8"), ("0", "1 0"), ("7", "1 7"), ("102030", "6 6"),
        ("1000000000000000000", "19 1"), ("999999999999999999", "18 162")],
       ["Méthode du calcul : n % 10 donne le dernier chiffre, et n / 10 (division entière) le retire. Recommencez jusqu'à 0.",
        "Méthode du texte : lisez n comme une chaîne de caractères, sa longueur est le nombre de chiffres.",
        "Avec la méthode du calcul, 0 est un cas à part : la boucle ne tourne pas, alors qu'il faut compter un chiffre."],
       {"cpp": r"""
#include <iostream>
#include <string>
int main() {
    std::string s;
    std::cin >> s;
    int somme = 0;
    for (char c : s) somme += c - '0';
    std::cout << s.size() << " " << somme << std::endl;
}""", "c": r"""
#include <stdio.h>
#include <string.h>
int main(void) {
    char s[64];
    if (scanf("%63s", s) != 1) return 1;
    int somme = 0;
    for (size_t i = 0; s[i]; i++) somme += s[i] - '0';
    printf("%zu %d\n", strlen(s), somme);
    return 0;
}""", "python": r"""
s = input().strip()
print(len(s), sum(int(c) for c in s))""", "javascript": r"""
const s = require("fs").readFileSync(0, "utf8").trim();
let somme = 0;
for (const c of s) somme += Number(c);
console.log(`${s.length} ${somme}`);""", "php": r"""
<?php
$s = trim(fgets(STDIN));
echo strlen($s), " ", array_sum(str_split($s)), "\n";"""}),

    ch("math-diviseurs", 0, "mini", "Tous les diviseurs", "diviseurs",
       "Les diviseurs de n sont tous les entiers de 1 à n qui divisent n (la division tombe juste).\n"
       "Par exemple, les diviseurs de 12 sont 1, 2, 3, 4, 6 et 12 : il y en a 6.\n\n"
       "Entrée : un entier n (1 ≤ n ≤ 10^6).\n"
       "Sortie : sur une première ligne, les diviseurs de n du plus petit au plus grand, séparés par des espaces. "
       "Sur une deuxième ligne, le nombre de diviseurs.\n\n"
       "Exemple : pour 12, affichez « 1 2 3 4 6 12 » puis « 6 ».",
       [("12", "1 2 3 4 6 12\n6"), ("7", "1 7\n2"), ("1", "1\n1"), ("36", "1 2 3 4 6 9 12 18 36\n9"),
        ("999983", "1 999983\n2"), ("720720", None), ("1000000", None)],
       ["Essayez tous les entiers i de 1 à n, et gardez ceux pour lesquels n % i == 0.",
        "Rangez les diviseurs trouvés dans une liste : vous aurez ainsi la ligne à afficher et leur nombre.",
        "Tester jusqu'à un million de valeurs est rapide pour un ordinateur : pas besoin d'astuce ici."],
       {"cpp": r"""
#include <iostream>
#include <vector>
int main() {
    long long n;
    std::cin >> n;
    std::vector<long long> d;
    for (long long i = 1; i <= n; i++)
        if (n % i == 0) d.push_back(i);
    for (size_t k = 0; k < d.size(); k++) std::cout << (k ? " " : "") << d[k];
    std::cout << "\n" << d.size() << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    long n;
    if (scanf("%ld", &n) != 1) return 1;
    int nb = 0;
    for (long i = 1; i <= n; i++)
        if (n % i == 0) printf(nb++ ? " %ld" : "%ld", i);
    printf("\n%d\n", nb);
    return 0;
}""", "python": r"""
n = int(input())
d = [i for i in range(1, n + 1) if n % i == 0]
print(*d)
print(len(d))""", "javascript": r"""
const n = Number(require("fs").readFileSync(0, "utf8").trim());
const d = [];
for (let i = 1; i <= n; i++) if (n % i === 0) d.push(i);
console.log(d.join(" "));
console.log(d.length);""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
$d = [];
for ($i = 1; $i <= $n; $i++) if ($n % $i === 0) $d[] = $i;
echo implode(" ", $d), "\n", count($d), "\n";"""}),

    ch("math-pgcd", 0, "mini", "Le PGCD", "PGCD",
       "Le PGCD (plus grand commun diviseur) de a et b est le plus grand entier qui divise à la fois a et b.\n"
       "Par exemple, les diviseurs de 12 sont 1, 2, 3, 4, 6, 12 et ceux de 18 sont 1, 2, 3, 6, 9, 18. "
       "Le plus grand qu'ils ont en commun est 6 : PGCD(12, 18) = 6.\n\n"
       "Entrée : deux entiers a et b sur une ligne (1 ≤ a ≤ 10^18 et 1 ≤ b ≤ 10^18).\n"
       "Sortie : le PGCD de a et b.\n\n"
       "Exemple : « 12 18 » donne 6. « 17 5 » donne 1 : ces deux nombres n'ont que 1 comme diviseur commun.",
       [("12 18", "6"), ("17 5", "1"), ("100 100", "100"), ("1 999", "1"),
        ("1000000000000000000 999999999999999999", "1"),
        ("123456789000000000 987654321000000000", "9000000000"),
        ("600000000000000000 400000000000000000", "200000000000000000")],
       ["Avec des nombres jusqu'à 10^18, essayer tous les diviseurs un par un serait beaucoup trop long : il faut une méthode.",
        "L'algorithme d'Euclide : PGCD(a, b) = PGCD(b, a % b). Par exemple PGCD(18, 12) = PGCD(12, 6) = PGCD(6, 0).",
        "On s'arrête quand le deuxième nombre vaut 0 : le PGCD est alors le premier. En boucle : tant que b ≠ 0, (a, b) devient (b, a % b)."],
       {"cpp": r"""
#include <iostream>
int main() {
    long long a, b;
    std::cin >> a >> b;
    while (b != 0) {
        long long r = a % b;
        a = b;
        b = r;
    }
    std::cout << a << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    long long a, b;
    if (scanf("%lld %lld", &a, &b) != 2) return 1;
    while (b != 0) {
        long long r = a % b;
        a = b;
        b = r;
    }
    printf("%lld\n", a);
    return 0;
}""", "python": r"""
a, b = map(int, input().split())
while b != 0:
    a, b = b, a % b
print(a)""", "javascript": r"""
let [a, b] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(BigInt);
while (b !== 0n) [a, b] = [b, a % b];
console.log(String(a));""", "php": r"""
<?php
[$a, $b] = array_map('intval', preg_split('/\s+/', trim(fgets(STDIN))));
while ($b !== 0) [$a, $b] = [$b, $a % $b];
echo $a, "\n";"""}),

    ch("math-ppcm", 0, "mini", "Le PPCM", "PPCM",
       "Le PPCM (plus petit commun multiple) de a et b est le plus petit entier positif qui est à la fois un multiple de a et un multiple de b.\n"
       "Par exemple, les multiples de 4 sont 4, 8, 12, 16… et ceux de 6 sont 6, 12, 18… Le premier en commun est 12 : PPCM(4, 6) = 12.\n\n"
       "Entrée : deux entiers a et b sur une ligne (1 ≤ a ≤ 10^9 et 1 ≤ b ≤ 10^9).\n"
       "Sortie : le PPCM de a et b.\n\n"
       "Exemple : « 4 6 » donne 12. « 5 7 » donne 35.",
       [("4 6", "12"), ("5 7", "35"), ("12 12", "12"), ("1 1", "1"), ("6 1000000000", "3000000000"),
        ("1000000000 999999999", "999999999000000000"), ("999999937 999999929", None)],
       ["Il existe une formule qui relie les deux : PGCD(a, b) × PPCM(a, b) = a × b.",
        "Donc PPCM(a, b) = a × b / PGCD(a, b). Reprenez l'algorithme d'Euclide du défi précédent pour le PGCD.",
        "Le résultat peut atteindre 10^18 : utilisez un long long (ou BigInt en JavaScript), et divisez avant de multiplier : a / PGCD × b."],
       {"cpp": r"""
#include <iostream>
long long pgcd(long long a, long long b) {
    while (b != 0) {
        long long r = a % b;
        a = b;
        b = r;
    }
    return a;
}
int main() {
    long long a, b;
    std::cin >> a >> b;
    std::cout << a / pgcd(a, b) * b << std::endl;
}""", "c": r"""
#include <stdio.h>
long long pgcd(long long a, long long b) {
    while (b != 0) {
        long long r = a % b;
        a = b;
        b = r;
    }
    return a;
}
int main(void) {
    long long a, b;
    if (scanf("%lld %lld", &a, &b) != 2) return 1;
    printf("%lld\n", a / pgcd(a, b) * b);
    return 0;
}""", "python": r"""
def pgcd(a, b):
    while b != 0:
        a, b = b, a % b
    return a


a, b = map(int, input().split())
print(a // pgcd(a, b) * b)""", "javascript": r"""
const pgcd = (a, b) => { while (b !== 0n) [a, b] = [b, a % b]; return a; };
const [a, b] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(BigInt);
console.log(String(a / pgcd(a, b) * b));""", "php": r"""
<?php
function pgcd($a, $b) {
    while ($b !== 0) [$a, $b] = [$b, $a % $b];
    return $a;
}
[$a, $b] = array_map('intval', preg_split('/\s+/', trim(fgets(STDIN))));
echo intdiv($a, pgcd($a, $b)) * $b, "\n";"""}),

    ch("math-fraction", 0, "mini", "Simplifier une fraction", "fractions",
       "Une fraction p/q est irréductible quand on ne peut plus la simplifier : p et q n'ont plus de diviseur commun à part 1.\n"
       "Pour simplifier, on divise p et q par leur PGCD. Par exemple, PGCD(6, 8) = 2, donc 6/8 = 3/4.\n\n"
       "Entrée : deux entiers p et q sur une ligne, le numérateur puis le dénominateur (1 ≤ p ≤ 10^9 et 1 ≤ q ≤ 10^9).\n"
       "Sortie : la fraction simplifiée, écrite « p/q » sans espace. Si le dénominateur devient 1, affichez seulement le numérateur.\n\n"
       "Exemple : « 6 8 » donne « 3/4 ». « 10 5 » donne « 2 », car 10/5 = 2/1 = 2.",
       [("6 8", "3/4"), ("10 5", "2"), ("7 13", "7/13"), ("1 1", "1"), ("5 1000000000", "1/200000000"),
        ("1000000000 999999999", "1000000000/999999999"), ("123456789 987654321", "13717421/109739369")],
       ["Calculez g = PGCD(p, q) avec l'algorithme d'Euclide.",
        "Divisez p et q par g : la fraction obtenue est irréductible.",
        "Avant d'afficher, regardez si le nouveau dénominateur vaut 1 : dans ce cas, n'affichez que le numérateur."],
       {"cpp": r"""
#include <iostream>
long long pgcd(long long a, long long b) {
    while (b != 0) {
        long long r = a % b;
        a = b;
        b = r;
    }
    return a;
}
int main() {
    long long p, q;
    std::cin >> p >> q;
    long long g = pgcd(p, q);
    p /= g;
    q /= g;
    if (q == 1) std::cout << p << std::endl;
    else std::cout << p << "/" << q << std::endl;
}""", "c": r"""
#include <stdio.h>
long long pgcd(long long a, long long b) {
    while (b != 0) {
        long long r = a % b;
        a = b;
        b = r;
    }
    return a;
}
int main(void) {
    long long p, q;
    if (scanf("%lld %lld", &p, &q) != 2) return 1;
    long long g = pgcd(p, q);
    p /= g;
    q /= g;
    if (q == 1) printf("%lld\n", p);
    else printf("%lld/%lld\n", p, q);
    return 0;
}""", "python": r"""
def pgcd(a, b):
    while b != 0:
        a, b = b, a % b
    return a


p, q = map(int, input().split())
g = pgcd(p, q)
p, q = p // g, q // g
print(p if q == 1 else f"{p}/{q}")""", "javascript": r"""
const pgcd = (a, b) => { while (b !== 0) [a, b] = [b, a % b]; return a; };
let [p, q] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
const g = pgcd(p, q);
p /= g;
q /= g;
console.log(q === 1 ? String(p) : `${p}/${q}`);""", "php": r"""
<?php
function pgcd($a, $b) {
    while ($b !== 0) [$a, $b] = [$b, $a % $b];
    return $a;
}
[$p, $q] = array_map('intval', preg_split('/\s+/', trim(fgets(STDIN))));
$g = pgcd($p, $q);
$p = intdiv($p, $g);
$q = intdiv($q, $g);
echo $q === 1 ? $p : "$p/$q", "\n";"""}),

    ch("math-binaire", 0, "mini", "Écrire en binaire", "bases de numération",
       "En binaire (base 2), on écrit les nombres avec seulement des 0 et des 1. Chaque chiffre vaut une puissance de 2 : "
       "1, 2, 4, 8, 16… de droite à gauche.\n"
       "Par exemple, 13 = 8 + 4 + 1 s'écrit 1101 en binaire.\n"
       "Méthode : on divise n par 2 et on note le reste (0 ou 1), puis on recommence avec le quotient jusqu'à arriver à 0. "
       "Les restes lus à l'envers forment l'écriture binaire. Pour 13 : restes 1, 0, 1, 1, donc 1101.\n\n"
       "Entrée : un entier n (0 ≤ n ≤ 10^18).\n"
       "Sortie : l'écriture binaire de n, sans zéro inutile au début.\n\n"
       "Exemple : « 13 » donne « 1101 ». « 0 » donne « 0 ». "
       "Les fonctions toutes faites de conversion en binaire sont interdites : à vous d'écrire la méthode !",
       [("13", "1101"), ("0", "0"), ("1", "1"), ("2", "10"), ("255", "11111111"), ("1024", "10000000000"),
        ("1000000000000000000", None), ("999999999999999999", None)],
       ["n % 2 donne le dernier chiffre binaire (le reste), et n / 2 (division entière) le retire.",
        "Les restes sortent de droite à gauche : ajoutez chaque nouveau chiffre au début de votre texte, ou retournez le texte à la fin.",
        "0 est un cas à part : la boucle « tant que n > 0 » ne tourne pas du tout, il faut afficher « 0 » vous-même."],
       {"cpp": r"""
#include <algorithm>
#include <iostream>
#include <string>
int main() {
    long long n;
    std::cin >> n;
    if (n == 0) {
        std::cout << 0 << std::endl;
        return 0;
    }
    std::string s;
    while (n > 0) {
        s += char('0' + n % 2);
        n /= 2;
    }
    std::reverse(s.begin(), s.end());
    std::cout << s << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    long long n;
    if (scanf("%lld", &n) != 1) return 1;
    char s[70];
    int i = 69;
    s[i] = '\0';
    do {
        s[--i] = (char) ('0' + n % 2);
        n /= 2;
    } while (n > 0);
    puts(s + i);
    return 0;
}""", "python": r"""
n = int(input())
s = ""
while n > 0:
    s = str(n % 2) + s
    n //= 2
print(s or "0")""", "javascript": r"""
let n = BigInt(require("fs").readFileSync(0, "utf8").trim());
let s = "";
while (n > 0n) {
    s = String(n % 2n) + s;
    n /= 2n;
}
console.log(s || "0");""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
$s = "";
while ($n > 0) {
    $s = ($n % 2) . $s;
    $n = intdiv($n, 2);
}
echo $s === "" ? "0" : $s, "\n";"""},
       banned={"python": [r"\bbin\s*\(", r"\bformat\s*\(", r":b\}", r":0\d*b\}"], "javascript": [r"toString\s*\(\s*2\s*\)"],
               "php": [r"\bdecbin\b", r"\bbase_convert\b", r"%b"], "cpp": [r"\bbitset\b"], "c": [r"%b"]}),

    ch("math-parfaits", 0, "exam", "Examen : nombres parfaits", "diviseurs",
       "Pour un entier n, notons s(n) la somme de ses diviseurs autres que n lui-même.\n"
       "Par exemple, les diviseurs de 12 autres que 12 sont 1, 2, 3, 4 et 6, donc s(12) = 16.\n"
       "On dit que n est :\n"
       "• PARFAIT si s(n) = n (par exemple 6 = 1 + 2 + 3) ;\n"
       "• ABONDANT si s(n) > n (par exemple 12, car 16 > 12) ;\n"
       "• DEFICIENT si s(n) < n (par exemple 8, car 1 + 2 + 4 = 7 < 8).\n\n"
       "Entrée : un entier T (1 ≤ T ≤ 100) sur la première ligne, puis T lignes contenant chacune un entier n (1 ≤ n ≤ 10^9).\n"
       "Sortie : pour chaque n, une ligne « n s(n) VERDICT ».\n\n"
       "Exemple : pour 12, affichez « 12 16 ABONDANT ». Pour 1, affichez « 1 0 DEFICIENT » : 1 n'a aucun autre diviseur que lui-même.",
       [("3\n6\n12\n8", "6 6 PARFAIT\n12 16 ABONDANT\n8 7 DEFICIENT"),
        ("4\n1\n28\n496\n945", "1 0 DEFICIENT\n28 28 PARFAIT\n496 496 PARFAIT\n945 975 ABONDANT"),
        _PA3, _PA1, _PA2],
       ["Pour n jusqu'à 10^9, tester tous les entiers de 1 à n serait trop lent : 100 nombres × 1 milliard d'essais…",
        "Les diviseurs vont par paires : si i divise n, alors n / i aussi. Il suffit donc de tester i de 1 jusqu'à √n (tant que i × i ≤ n).",
        "Pour chaque i qui divise n, ajoutez i et n / i, mais une seule fois si i = n / i. Retirez n à la fin. "
        "La somme peut dépasser 2 milliards : prenez un long long en C et C++."],
       {"cpp": r"""
#include <iostream>
int main() {
    int t;
    std::cin >> t;
    while (t--) {
        long long n, s = 0;
        std::cin >> n;
        for (long long i = 1; i * i <= n; i++)
            if (n % i == 0) {
                s += i;
                if (i != n / i) s += n / i;
            }
        s -= n;
        std::cout << n << " " << s << " " << (s == n ? "PARFAIT" : s > n ? "ABONDANT" : "DEFICIENT") << "\n";
    }
}""", "c": r"""
#include <stdio.h>
int main(void) {
    int t;
    if (scanf("%d", &t) != 1) return 1;
    while (t--) {
        long long n, s = 0;
        if (scanf("%lld", &n) != 1) return 1;
        for (long long i = 1; i * i <= n; i++)
            if (n % i == 0) {
                s += i;
                if (i != n / i) s += n / i;
            }
        s -= n;
        printf("%lld %lld %s\n", n, s, s == n ? "PARFAIT" : s > n ? "ABONDANT" : "DEFICIENT");
    }
    return 0;
}""", "python": r"""
import sys

d = sys.stdin.read().split()
out = []
for x in d[1:1 + int(d[0])]:
    n = int(x)
    s, i = 0, 1
    while i * i <= n:
        if n % i == 0:
            s += i
            if i != n // i:
                s += n // i
        i += 1
    s -= n
    out.append(f"{n} {s} {'PARFAIT' if s == n else 'ABONDANT' if s > n else 'DEFICIENT'}")
print("\n".join(out))""", "javascript": r"""
const d = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
const out = [];
for (let k = 1; k <= d[0]; k++) {
    const n = d[k];
    let s = 0;
    for (let i = 1; i * i <= n; i++)
        if (n % i === 0) {
            s += i;
            if (i !== n / i) s += n / i;
        }
    s -= n;
    out.push(`${n} ${s} ${s === n ? "PARFAIT" : s > n ? "ABONDANT" : "DEFICIENT"}`);
}
console.log(out.join("\n"));""", "php": r"""
<?php
$d = preg_split('/\s+/', trim(stream_get_contents(STDIN)));
$out = [];
for ($k = 1; $k <= (int) $d[0]; $k++) {
    $n = (int) $d[$k];
    $s = 0;
    for ($i = 1; $i * $i <= $n; $i++)
        if ($n % $i === 0) {
            $s += $i;
            if ($i !== intdiv($n, $i)) $s += intdiv($n, $i);
        }
    $s -= $n;
    $out[] = "$n $s " . ($s === $n ? "PARFAIT" : ($s > $n ? "ABONDANT" : "DEFICIENT"));
}
echo implode("\n", $out), "\n";"""}, minutes=30, time=3),
]
