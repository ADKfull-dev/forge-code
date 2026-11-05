# -*- coding: utf-8 -*-
"""Palier 2 — Tableaux et chaînes : parcours, manipulation de texte, matrices."""
from .base import ch, lines

_R = [(i * 7919) % 1000 - 500 for i in range(1, 1501)]           # valeurs avec beaucoup de doublons


def _uniq(v):
    seen, out = set(), []
    for x in v:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return " ".join(map(str, out))


_M = [[(i * 31 + j * 17) % 100 - 50 for j in range(40)] for i in range(25)]

DEFIS = [
    ch("inverse", 2, "mini", "À l'envers", "chaînes",
       "Lisez une ligne de texte (caractères ASCII) et affichez-la à l'envers.",
       [("abc", "cba"), ("Forge Code", "edoC egroF"), ("a", "a"), ("radar", "radar"), ("12345 678", "876 54321")],
       ["Parcourez la chaîne du dernier caractère au premier.", "C : échangez s[i] et s[n-1-i] jusqu'au milieu. C++ : std::reverse.",
        "Python : s[::-1]. JavaScript : [...s].reverse().join(\"\"). PHP : strrev($s)."],
       {"cpp": r"""
#include <iostream>
#include <string>
#include <algorithm>
int main() {
    std::string s;
    std::getline(std::cin, s);
    std::reverse(s.begin(), s.end());
    std::cout << s << std::endl;
}""", "c": r"""
#include <stdio.h>
#include <string.h>
int main(void) {
    char s[4096] = "";
    if (!fgets(s, sizeof s, stdin)) return 0;
    s[strcspn(s, "\r\n")] = '\0';
    size_t n = strlen(s);
    for (size_t i = 0; i < n / 2; ++i) { char t = s[i]; s[i] = s[n - 1 - i]; s[n - 1 - i] = t; }
    puts(s);
    return 0;
}""", "python": r"""
print(input()[::-1])""", "javascript": r"""
const s = require("fs").readFileSync(0, "utf8").split("\n")[0];
console.log([...s].reverse().join(""));""", "php": r"""
<?php
echo strrev(rtrim(fgets(STDIN), "\r\n")), "\n";"""}),

    ch("moyenne", 2, "mini", "Moyenne", "tableaux",
       "Ligne 1 : n (au moins 1). Ligne 2 : n entiers. Affichez leur moyenne avec exactement 2 décimales.",
       [("2\n1 2", "1.50"), ("3\n1 2 2", "1.67"), ("1\n5", "5.00"), ("4\n-1 -2 -3 -4", "-2.50"), ("5\n10 20 30 40 51", "30.20")],
       ["Additionnez les n nombres puis divisez par n.", "Attention : la division de deux entiers donne un entier en C/C++ ; convertissez en double.",
        "Deux décimales : printf(\"%.2f\"), f\"{m:.2f}\", m.toFixed(2)."],
       {"cpp": r"""
#include <iostream>
#include <iomanip>
int main() {
    int n;
    std::cin >> n;
    long long s = 0;
    for (int i = 0; i < n; ++i) { long long x; std::cin >> x; s += x; }
    std::cout << std::fixed << std::setprecision(2) << (double)s / n << std::endl;
}""", "c": r"""
#include <stdio.h>
int main(void) {
    int n;
    long long s = 0, x;
    if (scanf("%d", &n) != 1) return 1;
    for (int i = 0; i < n; ++i) if (scanf("%lld", &x) == 1) s += x;
    printf("%.2f\n", (double)s / n);
    return 0;
}""", "python": r"""
n = int(input())
v = list(map(int, input().split()))
print(f"{sum(v) / n:.2f}")""", "javascript": r"""
const [n, ...v] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
console.log((v.reduce((a, b) => a + b, 0) / n).toFixed(2));""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
$v = array_map('intval', explode(' ', trim(fgets(STDIN))));
printf("%.2f\n", array_sum($v) / $n);"""}),

    ch("voyelles", 2, "mini", "Compter les voyelles", "chaînes",
       "Lisez une ligne et affichez le nombre de voyelles (a e i o u y, majuscules comprises).",
       [("Bonjour", "3"), ("FORGE CODE", "4"), ("xyz", "1"), ("rythme", "2"), ("AEIOUY aeiouy", "12"), ("123 !", "0")],
       ["Parcourez chaque caractère.", "Mettez le caractère en minuscule avant de le comparer (tolower, lower(), toLowerCase(), strtolower).",
        "Vérifiez s'il appartient à la chaîne \"aeiouy\" (strchr en C, in en Python, includes en JS, str_contains en PHP)."],
       {"cpp": r"""
#include <iostream>
#include <string>
#include <cctype>
int main() {
    std::string s;
    std::getline(std::cin, s);
    int n = 0;
    for (char c : s) if (std::string("aeiouy").find(std::tolower((unsigned char)c)) != std::string::npos) ++n;
    std::cout << n << std::endl;
}""", "c": r"""
#include <stdio.h>
#include <string.h>
#include <ctype.h>
int main(void) {
    char s[4096] = "";
    if (!fgets(s, sizeof s, stdin)) return 0;
    int n = 0;
    for (char *p = s; *p && *p != '\n'; ++p) {
        int c = tolower((unsigned char)*p);
        if (c && strchr("aeiouy", c)) ++n;
    }
    printf("%d\n", n);
    return 0;
}""", "python": r"""
print(sum(c in "aeiouy" for c in input().lower()))""", "javascript": r"""
const s = require("fs").readFileSync(0, "utf8").split("\n")[0].toLowerCase();
console.log([...s].filter(c => "aeiouy".includes(c)).length);""", "php": r"""
<?php
$s = strtolower(rtrim(fgets(STDIN), "\r\n"));
$n = 0;
foreach (str_split($s) as $c) if ($c !== "" && str_contains("aeiouy", $c)) $n++;
echo $n, "\n";"""}),

    ch("palindrome", 2, "mini", "Palindrome", "chaînes",
       "Lisez une ligne. En ignorant les espaces et les majuscules, se lit-elle pareil dans les deux sens ? Affichez « oui » ou « non ».",
       [("Radar", "oui"), ("Forge", "non"), ("Esope reste ici et se repose", "oui"), ("a", "oui"), ("ab", "non"), ("Never odd or even", "oui")],
       ["Construisez d'abord une version nettoyée : sans espaces, en minuscules.", "Comparez-la avec son inverse.",
        "Ou comparez les caractères deux à deux depuis les deux bouts, avec deux indices qui se rapprochent."],
       {"cpp": r"""
#include <iostream>
#include <string>
#include <cctype>
int main() {
    std::string s, t;
    std::getline(std::cin, s);
    for (char c : s) if (c != ' ') t += std::tolower((unsigned char)c);
    std::string r(t.rbegin(), t.rend());
    std::cout << (t == r ? "oui" : "non") << std::endl;
}""", "c": r"""
#include <stdio.h>
#include <ctype.h>
int main(void) {
    char s[4096] = "", t[4096];
    int n = 0;
    if (!fgets(s, sizeof s, stdin)) return 0;
    for (char *p = s; *p && *p != '\n' && *p != '\r'; ++p) if (*p != ' ') t[n++] = (char)tolower((unsigned char)*p);
    int ok = 1;
    for (int i = 0, j = n - 1; i < j; ++i, --j) if (t[i] != t[j]) { ok = 0; break; }
    puts(ok ? "oui" : "non");
    return 0;
}""", "python": r"""
t = input().replace(" ", "").lower()
print("oui" if t == t[::-1] else "non")""", "javascript": r"""
const t = require("fs").readFileSync(0, "utf8").split("\n")[0].replace(/ /g, "").toLowerCase();
console.log(t === [...t].reverse().join("") ? "oui" : "non");""", "php": r"""
<?php
$t = strtolower(str_replace(" ", "", rtrim(fgets(STDIN), "\r\n")));
echo $t === strrev($t) ? "oui" : "non", "\n";"""}),

    ch("majuscules", 2, "mini", "Titre de livre", "chaînes",
       "Lisez une ligne (ASCII). Mettez la première lettre de chaque mot en majuscule et toutes les autres en minuscules. "
       "Un mot commence en début de ligne ou juste après une espace ; les espaces sont conservées telles quelles.",
       [("le chat noir", "Le Chat Noir"), ("BONJOUR tout LE monde", "Bonjour Tout Le Monde"), ("a", "A"), ("forge-code est top", "Forge-code Est Top"),
        ("  deux  espaces", "  Deux  Espaces"), ("123 abc", "123 Abc"), ("x Y z", "X Y Z")],
       ["Parcourez les caractères en retenant le précédent.", "Si le caractère précédent est une espace (ou s'il n'y en a pas), passez en majuscule, sinon en minuscule.",
        "toupper/tolower (C, C++), upper()/lower() (Python), toUpperCase()/toLowerCase() (JS), strtoupper/strtolower (PHP)."],
       {"cpp": r"""
#include <iostream>
#include <string>
#include <cctype>
int main() {
    std::string s;
    std::getline(std::cin, s);
    for (size_t i = 0; i < s.size(); ++i) {
        unsigned char c = s[i];
        s[i] = (i == 0 || s[i - 1] == ' ') ? std::toupper(c) : std::tolower(c);
    }
    std::cout << s << std::endl;
}""", "c": r"""
#include <stdio.h>
#include <string.h>
#include <ctype.h>
int main(void) {
    char s[4096] = "";
    if (!fgets(s, sizeof s, stdin)) return 0;
    s[strcspn(s, "\r\n")] = '\0';
    for (size_t i = 0; s[i]; ++i) {
        unsigned char c = (unsigned char)s[i];
        s[i] = (char)((i == 0 || s[i - 1] == ' ') ? toupper(c) : tolower(c));
    }
    puts(s);
    return 0;
}""", "python": r"""
s = input()
out = []
for i, c in enumerate(s):
    out.append(c.upper() if i == 0 or s[i - 1] == " " else c.lower())
print("".join(out))""", "javascript": r"""
const s = require("fs").readFileSync(0, "utf8").split("\n")[0];
let r = "";
for (let i = 0; i < s.length; i++) r += i === 0 || s[i - 1] === " " ? s[i].toUpperCase() : s[i].toLowerCase();
console.log(r);""", "php": r"""
<?php
$s = rtrim(fgets(STDIN), "\r\n");
$r = "";
for ($i = 0; $i < strlen($s); $i++) $r .= ($i === 0 || $s[$i - 1] === " ") ? strtoupper($s[$i]) : strtolower($s[$i]);
echo $r, "\n";"""}),

    ch("rotation", 2, "mini", "Rotation", "tableaux",
       "Ligne 1 : n (au moins 1) et k. Ligne 2 : n entiers. Décalez le tableau de k positions vers la droite "
       "(les éléments qui sortent à droite reviennent à gauche). k peut être négatif (décalage vers la gauche) ou bien plus grand que n.",
       [("5 2\n1 2 3 4 5", "4 5 1 2 3"), ("5 -1\n1 2 3 4 5", "2 3 4 5 1"), ("3 1000000000\n1 2 3", "3 1 2"), ("1 5\n9", "9"),
        ("4 0\n4 3 2 1", "4 3 2 1"), ("6 -8\n1 2 3 4 5 6", "3 4 5 6 1 2"), ("7 7\n1 2 3 4 5 6 7", "1 2 3 4 5 6 7")],
       ["Décaler de n positions ne change rien : ramenez k entre 0 et n - 1 avec un modulo.",
        "Attention au modulo d'un nombre négatif : ((k % n) + n) % n est toujours positif.",
        "L'élément d'indice i arrive à l'indice (i + k) mod n ; ou bien : résultat[i] = a[(i - k + n) mod n]."],
       {"cpp": r"""
#include <iostream>
#include <vector>
int main() {
    long long n, k;
    std::cin >> n >> k;
    std::vector<long long> a(n);
    for (auto& x : a) std::cin >> x;
    long long s = ((k % n) + n) % n;
    for (long long i = 0; i < n; ++i) std::cout << (i ? " " : "") << a[(i - s + n) % n];
    std::cout << "\n";
}""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
int main(void) {
    long long n, k;
    if (scanf("%lld %lld", &n, &k) != 2) return 1;
    long long *a = malloc(sizeof *a * n);
    for (long long i = 0; i < n; ++i) if (scanf("%lld", &a[i]) != 1) return 1;
    long long s = ((k % n) + n) % n;
    for (long long i = 0; i < n; ++i) printf(i ? " %lld" : "%lld", a[(i - s + n) % n]);
    printf("\n");
    free(a);
    return 0;
}""", "python": r"""
n, k = map(int, input().split())
a = input().split()
s = k % n
print(*(a[-s:] + a[:-s]) if s else a)""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const [n, k] = L[0].trim().split(/\s+/).map(Number);
const a = L[1].trim().split(/\s+/);
const s = ((k % n) + n) % n;
console.log(a.map((_, i) => a[(i - s + n) % n]).join(" "));""", "php": r"""
<?php
[$n, $k] = array_map('intval', explode(' ', trim(fgets(STDIN))));
$a = explode(' ', trim(fgets(STDIN)));
$s = (($k % $n) + $n) % $n;
$r = [];
for ($i = 0; $i < $n; $i++) $r[] = $a[($i - $s + $n) % $n];
echo implode(' ', $r), "\n";"""}),

    ch("doublons", 2, "mini", "Sans doublons", "tableaux",
       "Ligne 1 : n (1 à 1500). Ligne 2 : n entiers. Affichez les valeurs distinctes dans l'ordre de leur première apparition.",
       [("7\n3 1 3 2 1 5 3", "3 1 2 5"), ("1\n4", "4"), ("5\n-1 -1 -1 -1 -1", "-1"), ("6\n1 2 3 4 5 6", "1 2 3 4 5 6"),
        (f"{len(_R)}\n" + " ".join(map(str, _R)), _uniq(_R))],
       ["Pour chaque valeur, demandez-vous : l'ai-je déjà vue avant ?", "Première méthode : comparer avec tous les éléments précédents (deux boucles).",
        "Plus rapide : un ensemble des valeurs déjà vues (set en Python/C++, Set en JS, tableau associatif en PHP)."],
       {"cpp": r"""
#include <iostream>
#include <unordered_set>
int main() {
    int n;
    std::cin >> n;
    std::unordered_set<long long> vu;
    bool first = true;
    for (int i = 0; i < n; ++i) {
        long long x;
        std::cin >> x;
        if (vu.insert(x).second) { std::cout << (first ? "" : " ") << x; first = false; }
    }
    std::cout << "\n";
}""", "c": r"""
#include <stdio.h>
int main(void) {
    int n, m = 0;
    static long long a[2000], u[2000];
    if (scanf("%d", &n) != 1) return 1;
    for (int i = 0; i < n; ++i) if (scanf("%lld", &a[i]) != 1) return 1;
    for (int i = 0; i < n; ++i) {
        int dej = 0;
        for (int j = 0; j < m; ++j) if (u[j] == a[i]) { dej = 1; break; }
        if (!dej) u[m++] = a[i];
    }
    for (int i = 0; i < m; ++i) printf(i ? " %lld" : "%lld", u[i]);
    printf("\n");
    return 0;
}""", "python": r"""
input()
vu, out = set(), []
for x in input().split():
    if x not in vu:
        vu.add(x)
        out.append(x)
print(*out)""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
console.log([...new Set(L[1].trim().split(/\s+/).map(Number))].join(" "));""", "php": r"""
<?php
fgets(STDIN);
$vu = []; $out = [];
foreach (explode(' ', trim(fgets(STDIN))) as $x) {
    $x = (int) $x;
    if (!isset($vu[$x])) { $vu[$x] = true; $out[] = $x; }
}
echo implode(' ', $out), "\n";"""}),

    ch("transposee", 2, "mini", "Matrice transposée", "matrices",
       "Ligne 1 : h et w. Puis h lignes de w entiers. Affichez la transposée : w lignes de h entiers (la ligne i est l'ancienne colonne i).",
       [("2 3\n1 2 3\n4 5 6", "1 4\n2 5\n3 6"), ("1 1\n7", "7"), ("3 1\n1\n2\n3", "1 2 3"), ("1 4\n9 8 7 6", "9\n8\n7\n6"),
        ("25 40\n" + lines(" ".join(map(str, r)) for r in _M), lines(" ".join(str(_M[i][j]) for i in range(25)) for j in range(40)))],
       ["Stockez la matrice dans un tableau à deux dimensions m[i][j].", "La transposée t vérifie t[j][i] = m[i][j].",
        "Pour l'afficher : boucle sur les colonnes j, puis sur les lignes i."],
       {"cpp": r"""
#include <iostream>
#include <vector>
int main() {
    int h, w;
    std::cin >> h >> w;
    std::vector<std::vector<long long>> m(h, std::vector<long long>(w));
    for (auto& r : m) for (auto& x : r) std::cin >> x;
    for (int j = 0; j < w; ++j) {
        for (int i = 0; i < h; ++i) std::cout << (i ? " " : "") << m[i][j];
        std::cout << "\n";
    }
}""", "c": r"""
#include <stdio.h>
int main(void) {
    int h, w;
    static long long m[200][200];
    if (scanf("%d %d", &h, &w) != 2) return 1;
    for (int i = 0; i < h; ++i) for (int j = 0; j < w; ++j) if (scanf("%lld", &m[i][j]) != 1) return 1;
    for (int j = 0; j < w; ++j) {
        for (int i = 0; i < h; ++i) printf(i ? " %lld" : "%lld", m[i][j]);
        printf("\n");
    }
    return 0;
}""", "python": r"""
h, w = map(int, input().split())
m = [input().split() for _ in range(h)]
for j in range(w):
    print(" ".join(m[i][j] for i in range(h)))""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const [h, w] = L[0].trim().split(/\s+/).map(Number);
const m = L.slice(1, h + 1).map(l => l.trim().split(/\s+/));
for (let j = 0; j < w; j++) console.log(m.map(r => r[j]).join(" "));""", "php": r"""
<?php
[$h, $w] = array_map('intval', explode(' ', trim(fgets(STDIN))));
$m = [];
for ($i = 0; $i < $h; $i++) $m[] = explode(' ', trim(fgets(STDIN)));
for ($j = 0; $j < $w; $j++) echo implode(' ', array_column($m, $j)), "\n";"""}),

    ch("motlong", 2, "mini", "Le mot le plus long", "chaînes",
       "Lisez une ligne de mots (lettres ASCII) séparés par une ou plusieurs espaces. Affichez le mot le plus long et sa longueur, "
       "« mot longueur ». En cas d'égalité, gardez le premier.",
       [("le chat mange", "mange 5"), ("anticonstitutionnellement est long", "anticonstitutionnellement 25"), ("a", "a 1"),
        ("un deux six", "deux 4"), ("  espaces   multiples  ici ", "multiples 9"), ("abc def ghi", "abc 3")],
       ["Découpez la ligne en mots.", "Gardez le meilleur mot vu jusqu'ici ; remplacez-le seulement si le nouveau est STRICTEMENT plus long.",
        "Plusieurs espaces d'affilée : split() sans argument en Python, split(/\\s+/) après trim() en JS, preg_split en PHP, >> en C++, strtok en C."],
       {"cpp": r"""
#include <iostream>
#include <sstream>
#include <string>
int main() {
    std::string line, w, best;
    std::getline(std::cin, line);
    std::istringstream in(line);
    while (in >> w) if (w.size() > best.size()) best = w;
    std::cout << best << " " << best.size() << std::endl;
}""", "c": r"""
#include <stdio.h>
#include <string.h>
int main(void) {
    char s[4096] = "", best[4096] = "";
    if (!fgets(s, sizeof s, stdin)) return 0;
    for (char *w = strtok(s, " \r\n"); w; w = strtok(NULL, " \r\n"))
        if (strlen(w) > strlen(best)) strcpy(best, w);
    printf("%s %zu\n", best, strlen(best));
    return 0;
}""", "python": r"""
best = ""
for w in input().split():
    if len(w) > len(best):
        best = w
print(best, len(best))""", "javascript": r"""
const ws = require("fs").readFileSync(0, "utf8").split("\n")[0].trim().split(/\s+/);
let best = "";
for (const w of ws) if (w.length > best.length) best = w;
console.log(`${best} ${best.length}`);""", "php": r"""
<?php
$best = "";
foreach (preg_split('/\s+/', trim(fgets(STDIN))) as $w) if (strlen($w) > strlen($best)) $best = $w;
echo $best, " ", strlen($best), "\n";"""}),

    ch("stats", 2, "exam", "Examen : statistiques", "tableaux",
       "Ligne 1 : n (au moins 1). Ligne 2 : n entiers (jusqu'à un milliard chacun). Affichez sur quatre lignes : "
       "« min: a », « max: b », « somme: s », puis « au-dessus: k » où k est le nombre de valeurs strictement supérieures à la moyenne.",
       [("5\n1 2 3 4 5", "min: 1\nmax: 5\nsomme: 15\nau-dessus: 2"), ("1\n7", "min: 7\nmax: 7\nsomme: 7\nau-dessus: 0"),
        ("4\n-5 10 0 3", "min: -5\nmax: 10\nsomme: 8\nau-dessus: 2"),
        ("6\n1000000000 1000000000 1000000000 1 1 1", "min: 1\nmax: 1000000000\nsomme: 3000000003\nau-dessus: 3"),
        ("3\n2 2 2", "min: 2\nmax: 2\nsomme: 6\nau-dessus: 0"), ("5\n-3 -3 -3 -3 -2", "min: -3\nmax: -2\nsomme: -14\nau-dessus: 1")],
       ["Gardez toutes les valeurs dans un tableau : il faut les reparcourir après avoir calculé la moyenne.",
        "La somme peut dépasser 2 milliards (long long en C/C++).", "Pour éviter les nombres à virgule : x > somme / n  ⇔  x × n > somme."],
       {"cpp": r"""
#include <iostream>
#include <vector>
#include <algorithm>
int main() {
    int n;
    std::cin >> n;
    std::vector<long long> v(n);
    long long s = 0;
    for (auto& x : v) { std::cin >> x; s += x; }
    int k = 0;
    for (auto x : v) if (x * n > s) ++k;
    std::cout << "min: " << *std::min_element(v.begin(), v.end()) << "\n"
              << "max: " << *std::max_element(v.begin(), v.end()) << "\n"
              << "somme: " << s << "\n" << "au-dessus: " << k << "\n";
}""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 1;
    long long *v = malloc(sizeof *v * n), s = 0;
    for (int i = 0; i < n; ++i) { if (scanf("%lld", &v[i]) != 1) return 1; s += v[i]; }
    long long mn = v[0], mx = v[0];
    int k = 0;
    for (int i = 0; i < n; ++i) {
        if (v[i] < mn) mn = v[i];
        if (v[i] > mx) mx = v[i];
        if (v[i] * n > s) ++k;
    }
    printf("min: %lld\nmax: %lld\nsomme: %lld\nau-dessus: %d\n", mn, mx, s, k);
    free(v);
    return 0;
}""", "python": r"""
n = int(input())
v = list(map(int, input().split()))
s = sum(v)
print(f"min: {min(v)}")
print(f"max: {max(v)}")
print(f"somme: {s}")
print(f"au-dessus: {sum(x * n > s for x in v)}")""", "javascript": r"""
const [n, ...v] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
const s = v.reduce((a, b) => a + b, 0);
console.log(`min: ${Math.min(...v)}\nmax: ${Math.max(...v)}\nsomme: ${s}\nau-dessus: ${v.filter(x => x * n > s).length}`);""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
$v = array_map('intval', explode(' ', trim(fgets(STDIN))));
$s = array_sum($v);
echo "min: ", min($v), "\nmax: ", max($v), "\nsomme: $s\nau-dessus: ", count(array_filter($v, fn($x) => $x * $n > $s)), "\n";"""}, minutes=25),
]
