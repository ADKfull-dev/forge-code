# -*- coding: utf-8 -*-
"""Palier 0 — Les bases : entrées/sorties, variables, types numériques, conditions."""
from .base import ch

DEFIS = [
    ch("bonjour", 0, "mini", "Bonjour", "entrées/sorties",
       "Lisez un prénom (toute une ligne, il peut contenir des espaces) et affichez « Bonjour, <prénom> ! ».",
       [("Alice", "Bonjour, Alice !"), ("Anne Marie", "Bonjour, Anne Marie !"), ("Bob", "Bonjour, Bob !"), ("Jean-Luc", "Bonjour, Jean-Luc !")],
       ["Lisez la ligne entière, pas seulement le premier mot.",
        "C : fgets(s, sizeof s, stdin). C++ : std::getline(std::cin, s). Python : input(). PHP : fgets(STDIN).",
        "Retirez le retour à la ligne final, et attention à l'espace avant le « ! »."],
       {"cpp": r"""
#include <iostream>
#include <string>
int main() {
    std::string s;
    std::getline(std::cin, s);
    std::cout << "Bonjour, " << s << " !" << std::endl;
}""", "c": r"""
#include <stdio.h>
#include <string.h>
int main(void) {
    char s[1024] = "";
    if (!fgets(s, sizeof s, stdin)) return 0;
    s[strcspn(s, "\r\n")] = '\0';
    printf("Bonjour, %s !\n", s);
    return 0;
}""", "python": r"""
print(f"Bonjour, {input()} !")""", "javascript": r"""
const s = require("fs").readFileSync(0, "utf8").split("\n")[0].replace(/\r$/, "");
console.log(`Bonjour, ${s} !`);""", "php": r"""
<?php
$s = rtrim(fgets(STDIN), "\r\n");
echo "Bonjour, $s !\n";"""}),

    ch("somme", 0, "mini", "Grande somme", "entrées/sorties",
       "Deux entiers a et b sur une ligne, séparés par un espace. Affichez a + b. Attention : les nombres peuvent dépasser 2 milliards.",
       [("2 3", "5"), ("-7 4", "-3"), ("3000000000 4000000000", "7000000000"), ("0 0", "0"), ("-1000000000000 1", "-999999999999")],
       ["Lisez deux nombres, additionnez-les.",
        "Un int s'arrête vers 2,1 milliards : en C et C++, utilisez long long (%lld avec scanf/printf).",
        "Python : a, b = map(int, input().split()). JavaScript : split(\" \").map(Number)."],
       {"cpp": r"""
#include <iostream>
int main() {
    long long a, b;
    std::cin >> a >> b;
    std::cout << a + b << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    long long a, b;
    if (scanf("%lld %lld", &a, &b) != 2) return 1;
    printf("%lld\n", a + b);
    return 0;
}""", "python": r"""
a, b = map(int, input().split())
print(a + b)""", "javascript": r"""
const [a, b] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(BigInt);
console.log(String(a + b));""", "php": r"""
<?php
[$a, $b] = array_map('intval', explode(' ', trim(fgets(STDIN))));
echo $a + $b, "\n";"""}),

    ch("parite", 0, "mini", "Pair ou impair", "conditions",
       "Lisez un entier n (il peut être négatif). Affichez « pair » ou « impair ».",
       [("4", "pair"), ("7", "impair"), ("-3", "impair"), ("0", "pair"), ("-10", "pair"), ("123456789", "impair")],
       ["Le reste de la division par 2 dit tout.", "Opérateur modulo : n % 2.",
        "En C, C++, JavaScript et PHP, -3 % 2 vaut -1 (pas 1) : testez plutôt « n % 2 == 0 »."],
       {"cpp": r"""
#include <iostream>
int main() {
    long long n;
    std::cin >> n;
    std::cout << (n % 2 == 0 ? "pair" : "impair") << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    long long n;
    if (scanf("%lld", &n) != 1) return 1;
    puts(n % 2 == 0 ? "pair" : "impair");
    return 0;
}""", "python": r"""
n = int(input())
print("pair" if n % 2 == 0 else "impair")""", "javascript": r"""
const n = parseInt(require("fs").readFileSync(0, "utf8"), 10);
console.log(n % 2 === 0 ? "pair" : "impair");""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
echo $n % 2 === 0 ? "pair" : "impair", "\n";"""}),

    ch("max3", 0, "mini", "Le plus grand", "conditions",
       "Trois entiers sur une ligne. Affichez le plus grand.",
       [("1 2 3", "3"), ("9 -2 4", "9"), ("-5 -1 -9", "-1"), ("7 7 2", "7"), ("0 0 0", "0")],
       ["Comparez les nombres deux à deux.", "Gardez le plus grand dans une variable et comparez-la au suivant.",
        "Raccourcis : std::max({a, b, c}) en C++, max(a, b, c) en Python et PHP, Math.max(a, b, c) en JavaScript."],
       {"cpp": r"""
#include <iostream>
#include <algorithm>
int main() {
    long long a, b, c;
    std::cin >> a >> b >> c;
    std::cout << std::max({a, b, c}) << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    long long a, b, c;
    if (scanf("%lld %lld %lld", &a, &b, &c) != 3) return 1;
    long long m = a;
    if (b > m) m = b;
    if (c > m) m = c;
    printf("%lld\n", m);
    return 0;
}""", "python": r"""
print(max(map(int, input().split())))""", "javascript": r"""
const v = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
console.log(Math.max(...v));""", "php": r"""
<?php
echo max(array_map('intval', explode(' ', trim(fgets(STDIN))))), "\n";"""}),

    ch("celsius", 0, "mini", "Thermomètre", "nombres à virgule",
       "Lisez une température en degrés Celsius (elle peut être négative ou à virgule, ex. « 36.6 ») et affichez-la en degrés Fahrenheit "
       "avec exactement une décimale. F = C × 9 / 5 + 32.",
       [("100", "212.0"), ("36.6", "97.9"), ("0", "32.0"), ("-40", "-40.0"), ("21.5", "70.7"), ("12.3", "54.1"), ("1000", "1832.0"), ("-273.15", "-459.7")],
       ["Lisez un nombre à virgule (double / float), pas un entier.",
        "Attention à l'ordre des opérations et à la division entière : 9 / 5 vaut 1 en C si les deux sont entiers ! Écrivez 9.0 / 5.",
        "Affichage à une décimale : printf(\"%.1f\"), f\"{f:.1f}\", toFixed(1), std::fixed << std::setprecision(1)."],
       {"cpp": r"""
#include <iostream>
#include <iomanip>
int main() {
    double c;
    std::cin >> c;
    std::cout << std::fixed << std::setprecision(1) << c * 9.0 / 5.0 + 32.0 << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    double c;
    if (scanf("%lf", &c) != 1) return 1;
    printf("%.1f\n", c * 9.0 / 5.0 + 32.0);
    return 0;
}""", "python": r"""
c = float(input())
print(f"{c * 9 / 5 + 32:.1f}")""", "javascript": r"""
const c = parseFloat(require("fs").readFileSync(0, "utf8"));
console.log((c * 9 / 5 + 32).toFixed(1));""", "php": r"""
<?php
$c = (float) trim(fgets(STDIN));
printf("%.1f\n", $c * 9 / 5 + 32);"""}),

    ch("chrono", 0, "mini", "Chronomètre", "arithmétique",
       "Lisez une durée en secondes (0 ≤ n < 360000) et affichez-la au format HH:MM:SS (deux chiffres par champ).",
       [("3661", "01:01:01"), ("0", "00:00:00"), ("59", "00:00:59"), ("86399", "23:59:59"), ("359999", "99:59:59"), ("7200", "02:00:00")],
       ["Une heure = 3600 secondes, une minute = 60 secondes.",
        "Heures : n / 3600 (division entière). Minutes : (n % 3600) / 60. Secondes : n % 60.",
        "Pour compléter avec un zéro : printf(\"%02d\"), f\"{h:02d}\", String(h).padStart(2, \"0\"), sprintf(\"%02d\")."],
       {"cpp": r"""
#include <cstdio>
int main() {
    long n;
    if (std::scanf("%ld", &n) != 1) return 1;
    std::printf("%02ld:%02ld:%02ld\n", n / 3600, n % 3600 / 60, n % 60);
}""", "c": r"""
#include <stdio.h>
int main(void) {
    long n;
    if (scanf("%ld", &n) != 1) return 1;
    printf("%02ld:%02ld:%02ld\n", n / 3600, n % 3600 / 60, n % 60);
    return 0;
}""", "python": r"""
n = int(input())
print(f"{n // 3600:02d}:{n % 3600 // 60:02d}:{n % 60:02d}")""", "javascript": r"""
const n = parseInt(require("fs").readFileSync(0, "utf8"), 10);
const p = x => String(x).padStart(2, "0");
console.log(`${p(Math.floor(n / 3600))}:${p(Math.floor(n % 3600 / 60))}:${p(n % 60)}`);""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
printf("%02d:%02d:%02d\n", intdiv($n, 3600), intdiv($n % 3600, 60), $n % 60);"""}),

    ch("bissextile", 0, "mini", "Année bissextile", "conditions",
       "Lisez une année et affichez « bissextile » ou « non bissextile ». Règle : divisible par 4, sauf les siècles, "
       "sauf les siècles divisibles par 400 (2000 est bissextile, 1900 non).",
       [("2024", "bissextile"), ("2023", "non bissextile"), ("1900", "non bissextile"), ("2000", "bissextile"), ("2100", "non bissextile"),
        ("1600", "bissextile"), ("4", "bissextile"), ("2026", "non bissextile")],
       ["Trois règles, à combiner avec et / ou.", "Bissextile ⇔ (divisible par 4 ET pas par 100) OU divisible par 400.",
        "Testez les cas 1900 et 2000 : ce sont les pièges."],
       {"cpp": r"""
#include <iostream>
int main() {
    long long a;
    std::cin >> a;
    bool b = (a % 4 == 0 && a % 100 != 0) || a % 400 == 0;
    std::cout << (b ? "bissextile" : "non bissextile") << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    long long a;
    if (scanf("%lld", &a) != 1) return 1;
    int b = (a % 4 == 0 && a % 100 != 0) || a % 400 == 0;
    puts(b ? "bissextile" : "non bissextile");
    return 0;
}""", "python": r"""
a = int(input())
print("bissextile" if (a % 4 == 0 and a % 100 != 0) or a % 400 == 0 else "non bissextile")""", "javascript": r"""
const a = parseInt(require("fs").readFileSync(0, "utf8"), 10);
console.log((a % 4 === 0 && a % 100 !== 0) || a % 400 === 0 ? "bissextile" : "non bissextile");""", "php": r"""
<?php
$a = (int) trim(fgets(STDIN));
echo ($a % 4 === 0 && $a % 100 !== 0) || $a % 400 === 0 ? "bissextile" : "non bissextile", "\n";"""}),

    ch("division", 0, "mini", "Division euclidienne", "arithmétique",
       "Lisez deux entiers a et b (b ≠ 0, jusqu'à mille milliards en valeur absolue). Affichez « q r », le quotient et le reste "
       "de la division euclidienne : a = b × q + r avec 0 ≤ r < |b| (le reste n'est jamais négatif, contrairement à l'opérateur %).",
       [("17 5", "3 2"), ("-17 5", "-4 3"), ("17 -5", "-3 2"), ("-17 -5", "4 3"), ("0 7", "0 0"), ("10 2", "5 0"),
        ("1000000000000 7", "142857142857 1"), ("-1000000000000 -7", "142857142858 6")],
       ["Calculez d'abord le reste r, puis déduisez q = (a - r) / b.",
        "Si le reste donné par % est négatif, ajoutez-lui |b|.",
        "Attention : en Python, % suit le signe du diviseur ; en C/JS/PHP, celui du dividende. Le plus sûr : r = a % |b|, puis corriger si r < 0."],
       {"cpp": r"""
#include <iostream>
#include <cstdlib>
int main() {
    long long a, b;
    std::cin >> a >> b;
    long long r = a % std::llabs(b);
    if (r < 0) r += std::llabs(b);
    std::cout << (a - r) / b << " " << r << std::endl;
}""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
int main(void) {
    long long a, b;
    if (scanf("%lld %lld", &a, &b) != 2) return 1;
    long long r = a % llabs(b);
    if (r < 0) r += llabs(b);
    printf("%lld %lld\n", (a - r) / b, r);
    return 0;
}""", "python": r"""
a, b = map(int, input().split())
r = a % abs(b)
print((a - r) // b, r)""", "javascript": r"""
const [a, b] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(BigInt);
const ab = b < 0n ? -b : b;
let r = a % ab;
if (r < 0n) r += ab;
console.log(`${(a - r) / b} ${r}`);""", "php": r"""
<?php
[$a, $b] = array_map('intval', explode(' ', trim(fgets(STDIN))));
$r = $a % abs($b);
if ($r < 0) $r += abs($b);
echo intdiv($a - $r, $b), " ", $r, "\n";"""}),

    ch("triangle", 0, "mini", "Quel triangle ?", "conditions",
       "Trois longueurs entières positives (jusqu'à un million). Affichez « impossible » si elles ne forment pas un vrai triangle "
       "(le plus grand côté doit être strictement plus petit que la somme des deux autres), sinon « équilatéral », « isocèle », "
       "« rectangle » (a² + b² = c²) ou « quelconque », dans cet ordre de priorité.",
       [("3 3 3", "équilatéral"), ("3 4 5", "rectangle"), ("5 5 8", "isocèle"), ("1 2 3", "impossible"), ("4 5 6", "quelconque"), ("10 1 1", "impossible"),
        ("13 5 12", "rectangle"), ("2 3 2", "isocèle"), ("600000 800000 1000000", "rectangle"), ("1000000 1000000 1999999", "isocèle")],
       ["Triez les trois côtés : le plus grand est alors c.",
        "Triangle impossible si a + b ≤ c (un triangle « plat » ne compte pas).",
        "Les carrés dépassent 2 milliards : utilisez des entiers 64 bits pour a² + b² = c²."],
       {"cpp": r"""
#include <iostream>
#include <algorithm>
int main() {
    long long t[3];
    std::cin >> t[0] >> t[1] >> t[2];
    std::sort(t, t + 3);
    long long a = t[0], b = t[1], c = t[2];
    if (a + b <= c) std::cout << "impossible";
    else if (a == c) std::cout << "équilatéral";
    else if (a == b || b == c) std::cout << "isocèle";
    else if (a * a + b * b == c * c) std::cout << "rectangle";
    else std::cout << "quelconque";
    std::cout << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    long long a, b, c, t;
    if (scanf("%lld %lld %lld", &a, &b, &c) != 3) return 1;
    if (a > b) { t = a; a = b; b = t; }
    if (b > c) { t = b; b = c; c = t; }
    if (a > b) { t = a; a = b; b = t; }
    if (a + b <= c) puts("impossible");
    else if (a == c) puts("équilatéral");
    else if (a == b || b == c) puts("isocèle");
    else if (a * a + b * b == c * c) puts("rectangle");
    else puts("quelconque");
    return 0;
}""", "python": r"""
a, b, c = sorted(map(int, input().split()))
if a + b <= c:
    print("impossible")
elif a == c:
    print("équilatéral")
elif a == b or b == c:
    print("isocèle")
elif a * a + b * b == c * c:
    print("rectangle")
else:
    print("quelconque")""", "javascript": r"""
const [a, b, c] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number).sort((x, y) => x - y);
let r;
if (a + b <= c) r = "impossible";
else if (a === c) r = "équilatéral";
else if (a === b || b === c) r = "isocèle";
else if (a * a + b * b === c * c) r = "rectangle";
else r = "quelconque";
console.log(r);""", "php": r"""
<?php
$t = array_map('intval', explode(' ', trim(fgets(STDIN))));
sort($t);
[$a, $b, $c] = $t;
if ($a + $b <= $c) echo "impossible";
elseif ($a === $c) echo "équilatéral";
elseif ($a === $b || $b === $c) echo "isocèle";
elseif ($a * $a + $b * $b === $c * $c) echo "rectangle";
else echo "quelconque";
echo "\n";"""}),

    ch("caisse", 0, "exam", "Examen : la caisse", "conditions",
       "Ligne 1 : le prix à payer (en centimes). Ligne 2 : la somme donnée par le client. "
       "Si la somme suffit, affichez « Rendu : X » (X en centimes), ou « Compte juste » si X vaut 0. Sinon, affichez « Il manque : Y ».",
       [("150\n200", "Rendu : 50"), ("300\n250", "Il manque : 50"), ("999\n999", "Compte juste"), ("1\n1000000", "Rendu : 999999"),
        ("5000\n0", "Il manque : 5000"), ("0\n0", "Compte juste"), ("4000000000\n5000000000", "Rendu : 1000000000")],
       ["Calculez la différence entre la somme donnée et le prix.", "Trois cas : différence positive, nulle ou négative.",
        "Pour « Il manque », affichez la valeur positive (prix - somme). Et les montants peuvent dépasser 2 milliards."],
       {"cpp": r"""
#include <iostream>
int main() {
    long long prix, donne;
    std::cin >> prix >> donne;
    long long d = donne - prix;
    if (d > 0) std::cout << "Rendu : " << d << std::endl;
    else if (d == 0) std::cout << "Compte juste" << std::endl;
    else std::cout << "Il manque : " << -d << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    long long prix, donne;
    if (scanf("%lld %lld", &prix, &donne) != 2) return 1;
    long long d = donne - prix;
    if (d > 0) printf("Rendu : %lld\n", d);
    else if (d == 0) puts("Compte juste");
    else printf("Il manque : %lld\n", -d);
    return 0;
}""", "python": r"""
prix = int(input())
donne = int(input())
d = donne - prix
if d > 0:
    print(f"Rendu : {d}")
elif d == 0:
    print("Compte juste")
else:
    print(f"Il manque : {-d}")""", "javascript": r"""
const [prix, donne] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
const d = donne - prix;
if (d > 0) console.log(`Rendu : ${d}`);
else if (d === 0) console.log("Compte juste");
else console.log(`Il manque : ${-d}`);""", "php": r"""
<?php
$prix = (int) trim(fgets(STDIN));
$donne = (int) trim(fgets(STDIN));
$d = $donne - $prix;
if ($d > 0) echo "Rendu : $d\n";
elseif ($d === 0) echo "Compte juste\n";
else echo "Il manque : ", -$d, "\n";"""}, minutes=15),
]
