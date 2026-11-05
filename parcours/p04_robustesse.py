# -*- coding: utf-8 -*-
"""Palier 4 — Robustesse et débogage : cas limites, débordements, arrondis, dates, parsing, corriger le code d'un autre."""
import re

from .base import ch, lines

# ---------------------------------------------------------------- références (servent à calculer les sorties attendues)
_BUG_NOTE = " Le code de départ (fourni en C, C++, Python, JavaScript et PHP) contient des bugs : trouvez-les et corrigez-les."


def _cents(s):
    neg = s.startswith("-")
    s = s.lstrip("+-")
    e, _, d = s.partition(".")
    v = int(e) * 100 + int((d + "00")[:2])
    return -v if neg else v


def _fmt(c):
    return ("-" if c < 0 else "") + f"{abs(c) // 100}.{abs(c) % 100:02d}"


def _tva(inp):
    L = inp.split("\n")
    n, taux = L[0].split()
    e, _, d = taux.partition(".")
    tm = int(e) * 1000 + int((d + "000")[:3])
    ht = sum(int(q) * _cents(p) for q, p in (l.split() for l in L[1:int(n) + 1]))
    tva = (ht * tm + 50000) // 100000
    return f"HT: {_fmt(ht)}\nTVA: {_fmt(tva)}\nTTC: {_fmt(ht + tva)}"


def _csv(inp):
    out = []
    for line in inp.split("\n")[1:]:
        f, i, cur = [], 0, ""
        while True:
            if i < len(line) and line[i] == '"':
                i += 1
                while i < len(line):
                    if line[i] == '"' and i + 1 < len(line) and line[i + 1] == '"':
                        cur += '"'
                        i += 2
                    elif line[i] == '"':
                        i += 1
                        break
                    else:
                        cur += line[i]
                        i += 1
            while i < len(line) and line[i] != ",":
                cur += line[i]
                i += 1
            f.append(cur)
            cur = ""
            if i >= len(line):
                break
            i += 1
        out.append(" ".join(f"[{x}]" for x in f))
    return lines(out)


def _valid(inp):
    out = []
    for s in inp.split("\n")[1:]:
        ok = re.fullmatch(r"[+-]?(0|[1-9][0-9]{0,10})", s) and -2 ** 31 <= int(s) < 2 ** 31
        out.append(f"ok {int(s)}" if ok else "invalide")
    return lines(out)


def _jours_mois(a, m):
    return [31, 29 if (a % 4 == 0 and a % 100 != 0) or a % 400 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]


def _releve(inp):
    mois, bad, nb = {}, 0, 0
    for l in inp.split("\n"):
        if not l.strip():
            continue
        p = l.split(";")
        ok = len(p) == 3 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p[0]) and re.fullmatch(r"[+-]?\d+(\.\d{1,2})?", p[1]) and p[2].strip()
        if ok:
            a, m, j = map(int, p[0].split("-"))
            ok = 1 <= m <= 12 and 1 <= j <= _jours_mois(a, m)
        if not ok:
            bad += 1
            continue
        nb += 1
        mois[p[0][:7]] = mois.get(p[0][:7], 0) + _cents(p[1])
    out = [f"{k} : {_fmt(v)}" for k, v in sorted(mois.items())]
    return lines(out + [f"Solde : {_fmt(sum(mois.values()))}", f"Opérations : {nb}", f"Lignes invalides : {bad}"])


_T1 = "3 20\n2 19.99\n1 5\n10 0.5"
_T2 = "1 5.5\n1 1.00"
_T3 = "4 19.6\n3 0.1\n7 12.34\n1 999.99\n100 0.07"
_T4 = "2 0\n5 3.3\n1 0.01"
_T5 = "3 2.1\n1000000 999\n1 0.05\n3 1234.5"
_T6 = "5 5.5\n1 0.1\n1 0.2\n1 0.3\n1 0.4\n1 0.9"
_TB = f"200 8.5\n" + lines(f"{(i * 7) % 13 + 1} {(i * 37) % 5000 // 100}.{(i * 37) % 100:02d}" for i in range(200))

_C1 = '3\nnom,age,ville\n"Dupont, Jean",42,Paris\nsimple,,fin'
_C2 = '2\n"il a dit ""bonjour""",x\n,,'
_C3 = '4\n"a,b,c"\n""\n"x""y","",z\nsans guillemets , espaces gardés '
_C4 = '3\n"",""\n"début"fin,"mi,lieu"\nun'

_V1 = "6\n42\n-17\n+8\n007\n12a\n"
_V2 = "8\n2147483647\n2147483648\n-2147483648\n-2147483649\n0\n-0\n+0\n99999999999999999999999"
_V3 = "7\n 12\n12 \n+\n-\n--1\n1e3\n00"

_R1 = "2024-01-05;-12.50;Boulangerie\n2024-01-06;1500;Salaire\n2024-02-30;10;Date impossible\n2024-02-29;-3.1;Bissextile\nabc;1;x"
_R2 = "2023-12-31;+0.05;a\n2023-12-31;-0.05;b\n2023-02-29;5;faux\n2023-13-01;5;faux\n2023-11-10;12.345;trop de décimales\n\n2023-11-10;-7;ok\n2023-11-10;8;\n2023-11-10;8;x;y"
_R3 = lines(f"{2020 + i % 5}-{i % 12 + 1:02d}-{i % 28 + 1:02d};{'-' if i % 3 == 0 else ''}{(i * 97) % 10000}.{i % 100:02d};op {i}" for i in range(3000)) \
    + "\n2021-04-31;1;x\n2021-4-01;1;x\n2021-04-01;1,5;x\n2021-04-01;.5;x\n2021-04-01;5.;x"

_BUG_ECART = {
    "python": r"""
# Plus grand écart — ce programme contient 2 bugs : trouvez-les !
n = int(input())
v = list(map(int, input().split()))
plus_grand = 0
plus_petit = 0
for i in range(1, n):
    if v[i] > plus_grand:
        plus_grand = v[i]
    if v[i] < plus_petit:
        plus_petit = v[i]
print(plus_grand - plus_petit)""",
    "c": r"""
// Plus grand écart — ce programme contient 2 bugs : trouvez-les !
#include <stdio.h>
int main(void) {
    int n;
    long long v[100000];
    if (scanf("%d", &n) != 1) return 1;
    for (int i = 0; i < n; ++i) if (scanf("%lld", &v[i]) != 1) return 1;
    long long plus_grand = 0, plus_petit = 0;
    for (int i = 1; i < n; ++i) {
        if (v[i] > plus_grand) plus_grand = v[i];
        if (v[i] < plus_petit) plus_petit = v[i];
    }
    printf("%lld\n", plus_grand - plus_petit);
    return 0;
}""",
    "cpp": r"""
// Plus grand écart — ce programme contient 2 bugs : trouvez-les !
#include <iostream>
#include <vector>
int main() {
    int n;
    std::cin >> n;
    std::vector<long long> v(n);
    for (auto& x : v) std::cin >> x;
    long long plus_grand = 0, plus_petit = 0;
    for (int i = 1; i < n; ++i) {
        if (v[i] > plus_grand) plus_grand = v[i];
        if (v[i] < plus_petit) plus_petit = v[i];
    }
    std::cout << plus_grand - plus_petit << std::endl;
}""",
    "javascript": r"""
// Plus grand écart — ce programme contient 2 bugs : trouvez-les !
const [n, ...v] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
let plusGrand = 0, plusPetit = 0;
for (let i = 1; i < n; i++) {
  if (v[i] > plusGrand) plusGrand = v[i];
  if (v[i] < plusPetit) plusPetit = v[i];
}
console.log(plusGrand - plusPetit);""",
    "php": r"""
<?php
// Plus grand écart — ce programme contient 2 bugs : trouvez-les !
$n = (int) trim(fgets(STDIN));
$v = array_map('intval', explode(' ', trim(fgets(STDIN))));
$plusGrand = 0;
$plusPetit = 0;
for ($i = 1; $i < $n; $i++) {
    if ($v[$i] > $plusGrand) $plusGrand = $v[$i];
    if ($v[$i] < $plusPetit) $plusPetit = $v[$i];
}
echo $plusGrand - $plusPetit, "\n";""",
}

_BUG_AGE = {
    "python": r"""
# L'âge exact — ce programme contient 2 bugs : trouvez-les !
jn, mn, an = map(int, input().split("/"))
ja, ma, aa = map(int, input().split("/"))
age = aa - an
if ma < mn or ja < jn:
    age = age - 1
print(f"{age} ans")""",
    "c": r"""
// L'âge exact — ce programme contient 2 bugs : trouvez-les !
#include <stdio.h>
int main(void) {
    int jn, mn, an, ja, ma, aa;
    if (scanf("%d/%d/%d %d/%d/%d", &jn, &mn, &an, &ja, &ma, &aa) != 6) return 1;
    int age = aa - an;
    if (ma < mn || ja < jn) age = age - 1;
    printf("%d ans\n", age);
    return 0;
}""",
    "cpp": r"""
// L'âge exact — ce programme contient 2 bugs : trouvez-les !
#include <iostream>
int main() {
    int jn, mn, an, ja, ma, aa;
    char s;
    std::cin >> jn >> s >> mn >> s >> an >> ja >> s >> ma >> s >> aa;
    int age = aa - an;
    if (ma < mn || ja < jn) age = age - 1;
    std::cout << age << " ans" << std::endl;
}""",
    "javascript": r"""
// L'âge exact — ce programme contient 2 bugs : trouvez-les !
const [n, a] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(l => l.split("/").map(Number));
const [jn, mn, an] = n, [ja, ma, aa] = a;
let age = aa - an;
if (ma < mn || ja < jn) age = age - 1;
console.log(`${age} ans`);""",
    "php": r"""
<?php
// L'âge exact — ce programme contient 2 bugs : trouvez-les !
[$jn, $mn, $an] = array_map('intval', explode('/', trim(fgets(STDIN))));
[$ja, $ma, $aa] = array_map('intval', explode('/', trim(fgets(STDIN))));
$age = $aa - $an;
if ($ma < $mn || $ja < $jn) $age = $age - 1;
echo "$age ans\n";""",
}

DEFIS = [
    ch("bug-ecart", 4, "mini", "Bug : le plus grand écart", "débogage",
       "Ligne 1 : n (au moins 1). Ligne 2 : n entiers (positifs ou négatifs). Affichez l'écart entre le plus grand et le plus petit." + _BUG_NOTE,
       [("3\n1 5 3", "4"), ("4\n-2 -9 -4 -7", "7"), ("1\n42", "0"), ("5\n10 20 30 40 50", "40"), ("3\n-5 0 5", "10"), ("2\n7 7", "0"),
        ("6\n1000000000000 -1000000000000 3 4 5 6", "2000000000000")],
       ["Exécutez le programme sur les exemples et comparez : lequel échoue, et pourquoi ?",
        "Que se passe-t-il si tous les nombres sont positifs ? Tous négatifs ? Quel élément n'est jamais regardé ?",
        "Initialisez le plus grand et le plus petit avec le PREMIER élément (pas 0), et parcourez bien tout le tableau."],
       {"python": r"""
n = int(input())
v = list(map(int, input().split()))
plus_grand = v[0]
plus_petit = v[0]
for i in range(n):
    if v[i] > plus_grand:
        plus_grand = v[i]
    if v[i] < plus_petit:
        plus_petit = v[i]
print(plus_grand - plus_petit)""", "c": r"""
#include <stdio.h>
int main(void) {
    int n;
    static long long v[100000];
    if (scanf("%d", &n) != 1) return 1;
    for (int i = 0; i < n; ++i) if (scanf("%lld", &v[i]) != 1) return 1;
    long long plus_grand = v[0], plus_petit = v[0];
    for (int i = 0; i < n; ++i) {
        if (v[i] > plus_grand) plus_grand = v[i];
        if (v[i] < plus_petit) plus_petit = v[i];
    }
    printf("%lld\n", plus_grand - plus_petit);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <vector>
int main() {
    int n;
    std::cin >> n;
    std::vector<long long> v(n);
    for (auto& x : v) std::cin >> x;
    long long plus_grand = v[0], plus_petit = v[0];
    for (int i = 0; i < n; ++i) {
        if (v[i] > plus_grand) plus_grand = v[i];
        if (v[i] < plus_petit) plus_petit = v[i];
    }
    std::cout << plus_grand - plus_petit << std::endl;
}""", "javascript": r"""
const [n, ...v] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
let plusGrand = v[0], plusPetit = v[0];
for (let i = 0; i < n; i++) {
  if (v[i] > plusGrand) plusGrand = v[i];
  if (v[i] < plusPetit) plusPetit = v[i];
}
console.log(plusGrand - plusPetit);""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
$v = array_map('intval', explode(' ', trim(fgets(STDIN))));
$plusGrand = $v[0];
$plusPetit = $v[0];
for ($i = 0; $i < $n; $i++) {
    if ($v[$i] > $plusGrand) $plusGrand = $v[$i];
    if ($v[$i] < $plusPetit) $plusPetit = $v[$i];
}
echo $plusGrand - $plusPetit, "\n";"""}, tag="debug", starter=_BUG_ECART),

    ch("bug-age", 4, "mini", "Bug : l'âge exact", "débogage",
       "Ligne 1 : une date de naissance JJ/MM/AAAA. Ligne 2 : la date du jour, même format. Affichez l'âge en années révolues : "
       "« 0 an », « 1 an », puis « 2 ans », « 3 ans »… (l'anniversaire compte le jour même)." + _BUG_NOTE,
       [("15/06/2000\n10/08/2024", "24 ans"), ("15/06/2000\n14/06/2024", "23 ans"), ("15/06/2000\n15/06/2024", "24 ans"), ("01/01/2023\n31/12/2023", "0 an"),
        ("29/02/2000\n28/02/2001", "0 an"), ("29/02/2000\n01/03/2001", "1 an"), ("31/12/1950\n01/01/2026", "75 ans"), ("20/03/2010\n19/04/2026", "16 ans")],
       ["Testez une naissance le 15/06 et un « aujourd'hui » le 10/08 : l'anniversaire est passé, et pourtant…",
        "Le jour ne compte que si l'on est dans le MÊME mois que l'anniversaire.",
        "Pas encore d'anniversaire cette année ⇔ mois < mois_naissance, OU (même mois ET jour < jour_naissance). Et « an » au singulier pour 0 et 1."],
       {"python": r"""
jn, mn, an = map(int, input().split("/"))
ja, ma, aa = map(int, input().split("/"))
age = aa - an
if ma < mn or (ma == mn and ja < jn):
    age = age - 1
print(f"{age} {'an' if age < 2 else 'ans'}")""", "c": r"""
#include <stdio.h>
int main(void) {
    int jn, mn, an, ja, ma, aa;
    if (scanf("%d/%d/%d %d/%d/%d", &jn, &mn, &an, &ja, &ma, &aa) != 6) return 1;
    int age = aa - an;
    if (ma < mn || (ma == mn && ja < jn)) age = age - 1;
    printf("%d %s\n", age, age < 2 ? "an" : "ans");
    return 0;
}""", "cpp": r"""
#include <iostream>
int main() {
    int jn, mn, an, ja, ma, aa;
    char s;
    std::cin >> jn >> s >> mn >> s >> an >> ja >> s >> ma >> s >> aa;
    int age = aa - an;
    if (ma < mn || (ma == mn && ja < jn)) age = age - 1;
    std::cout << age << (age < 2 ? " an" : " ans") << std::endl;
}""", "javascript": r"""
const [n, a] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(l => l.split("/").map(Number));
const [jn, mn, an] = n, [ja, ma, aa] = a;
let age = aa - an;
if (ma < mn || (ma === mn && ja < jn)) age = age - 1;
console.log(`${age} ${age < 2 ? "an" : "ans"}`);""", "php": r"""
<?php
[$jn, $mn, $an] = array_map('intval', explode('/', trim(fgets(STDIN))));
[$ja, $ma, $aa] = array_map('intval', explode('/', trim(fgets(STDIN))));
$age = $aa - $an;
if ($ma < $mn || ($ma === $mn && $ja < $jn)) $age = $age - 1;
echo $age, $age < 2 ? " an" : " ans", "\n";"""}, tag="debug", starter=_BUG_AGE),

    ch("dates", 4, "mini", "Jours entre deux dates", "dates",
       "Deux dates AAAA-MM-JJ, une par ligne (années 1 à 9999, calendrier grégorien). Affichez le nombre de jours qui les séparent (toujours positif). "
       "Contrainte : sans bibliothèque de dates.",
       [("2024-01-01\n2024-12-31", "365"), ("2000-02-28\n2000-03-01", "2"), ("1900-02-28\n1900-03-01", "1"), ("2023-01-01\n2024-01-01", "365"),
        ("2024-01-01\n2025-01-01", "366"), ("0001-01-01\n9999-12-31", "3652058"), ("2026-09-28\n1969-07-21", "20888"), ("2026-09-28\n2026-09-28", "0")],
       ["Convertissez chaque date en un numéro de jour (nombre de jours depuis une origine fixe), puis faites la différence.",
        "Numéro du jour = jours des années entières précédentes + jours des mois entiers précédents de l'année + jour.",
        "Jours avant l'année a : 365 × (a - 1) + (a - 1)/4 - (a - 1)/100 + (a - 1)/400. N'oubliez pas le 29 février des années bissextiles."],
       {"cpp": r"""
#include <iostream>
#include <cstdio>
#include <string>
long long numero(const std::string& d) {
    int a, m, j;
    std::sscanf(d.c_str(), "%d-%d-%d", &a, &m, &j);
    const int jm[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    bool bis = (a % 4 == 0 && a % 100 != 0) || a % 400 == 0;
    long long p = a - 1, n = 365 * p + p / 4 - p / 100 + p / 400;
    for (int k = 1; k < m; ++k) n += jm[k - 1] + (k == 2 && bis);
    return n + j;
}
int main() {
    std::string a, b;
    std::cin >> a >> b;
    long long d = numero(a) - numero(b);
    std::cout << (d < 0 ? -d : d) << std::endl;
}""", "c": r"""
#include <stdio.h>
static long long numero(int a, int m, int j) {
    const int jm[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    int bis = (a % 4 == 0 && a % 100 != 0) || a % 400 == 0;
    long long p = a - 1, n = 365 * p + p / 4 - p / 100 + p / 400;
    for (int k = 1; k < m; ++k) n += jm[k - 1] + (k == 2 && bis);
    return n + j;
}
int main(void) {
    int a1, m1, j1, a2, m2, j2;
    if (scanf("%d-%d-%d %d-%d-%d", &a1, &m1, &j1, &a2, &m2, &j2) != 6) return 1;
    long long d = numero(a1, m1, j1) - numero(a2, m2, j2);
    printf("%lld\n", d < 0 ? -d : d);
    return 0;
}""", "python": r"""
def numero(d):
    a, m, j = map(int, d.split("-"))
    bis = (a % 4 == 0 and a % 100 != 0) or a % 400 == 0
    jm = [31, 29 if bis else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    p = a - 1
    return 365 * p + p // 4 - p // 100 + p // 400 + sum(jm[:m - 1]) + j

print(abs(numero(input().strip()) - numero(input().strip())))""", "javascript": r"""
const numero = d => {
  const [a, m, j] = d.split("-").map(Number);
  const bis = (a % 4 === 0 && a % 100 !== 0) || a % 400 === 0;
  const jm = [31, bis ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  const p = a - 1;
  let n = 365 * p + Math.floor(p / 4) - Math.floor(p / 100) + Math.floor(p / 400) + j;
  for (let k = 0; k < m - 1; k++) n += jm[k];
  return n;
};
const [a, b] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/);
console.log(Math.abs(numero(a) - numero(b)));""", "php": r"""
<?php
function numero(string $d): int {
    [$a, $m, $j] = array_map('intval', explode('-', $d));
    $bis = ($a % 4 === 0 && $a % 100 !== 0) || $a % 400 === 0;
    $jm = [31, $bis ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    $p = $a - 1;
    return 365 * $p + intdiv($p, 4) - intdiv($p, 100) + intdiv($p, 400) + array_sum(array_slice($jm, 0, $m - 1)) + $j;
}
$a = trim(fgets(STDIN));
$b = trim(fgets(STDIN));
echo abs(numero($a) - numero($b)), "\n";"""},
       banned={"python": [r"\bdatetime\b", r"\bcalendar\b", r"\btime\b"], "javascript": [r"\bDate\b"], "php": [r"DateTime", r"strtotime", r"mktime", r"gregoriantojd", r"date_"],
               "c": [r"mktime", r"timegm", r"<time\.h>"], "cpp": [r"chrono", r"mktime", r"<ctime>"]}),

    ch("tva", 4, "mini", "Facture sans erreur d'arrondi", "arrondis",
       "Ligne 1 : n et le taux de TVA en pourcentage (jusqu'à 3 décimales, ex. « 20 » ou « 5.5 »). Puis n lignes « quantité prix_unitaire », "
       "le prix ayant au plus 2 décimales (« 19.99 », « 5 », « 0.5 »). Affichez « HT: … », « TVA: … », « TTC: … » avec 2 décimales. "
       "La TVA = HT × taux / 100, arrondie au centime le plus proche (un demi-centime s'arrondit vers le haut).",
       [(_T1, _tva(_T1)), (_T2, _tva(_T2)), (_T3, _tva(_T3)), (_T4, _tva(_T4)), (_T5, _tva(_T5)), (_T6, _tva(_T6)), (_TB, _tva(_TB))],
       ["Les nombres à virgule (float/double) ne savent pas représenter 0.1 ou 0.055 exactement : 1.00 € à 5.5 % donnerait 0.05 au lieu de 0.06.",
        "Travaillez en entiers : les prix en centimes (« 19.99 » → 1999, « 0.5 » → 50) et le taux en millièmes de pourcent (« 5.5 » → 5500).",
        "TVA en centimes = (HT_centimes × taux_millièmes + 50000) / 100000 en division entière : le + 50000 fait l'arrondi au plus proche."],
       {"python": r"""
def centimes(s):
    e, _, d = s.partition(".")
    return int(e) * 100 + int((d + "00")[:2])

def fmt(c):
    return f"{c // 100}.{c % 100:02d}"

n, taux = input().split()
e, _, d = taux.partition(".")
tm = int(e) * 1000 + int((d + "000")[:3])
ht = 0
for _ in range(int(n)):
    q, p = input().split()
    ht += int(q) * centimes(p)
tva = (ht * tm + 50000) // 100000
print(f"HT: {fmt(ht)}")
print(f"TVA: {fmt(tva)}")
print(f"TTC: {fmt(ht + tva)}")""", "c": r"""
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
/* « 12.3 » avec k décimales → 1230 (k = 2) */
static long long fixe(const char *s, int k) {
    long long v = 0;
    int dec = -1;
    for (; *s; ++s) {
        if (*s == '.') { dec = 0; continue; }
        if (dec >= k) break;
        v = v * 10 + (*s - '0');
        if (dec >= 0) ++dec;
    }
    if (dec < 0) dec = 0;
    while (dec++ < k) v *= 10;
    return v;
}
int main(void) {
    int n;
    char taux[32], prix[32];
    long long q, ht = 0;
    if (scanf("%d %31s", &n, taux) != 2) return 1;
    long long tm = fixe(taux, 3);
    for (int i = 0; i < n; ++i) {
        if (scanf("%lld %31s", &q, prix) != 2) return 1;
        ht += q * fixe(prix, 2);
    }
    long long tva = (ht * tm + 50000) / 100000;
    printf("HT: %lld.%02lld\nTVA: %lld.%02lld\nTTC: %lld.%02lld\n", ht / 100, ht % 100, tva / 100, tva % 100, (ht + tva) / 100, (ht + tva) % 100);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <iomanip>
#include <string>
long long fixe(const std::string& s, int k) {
    auto p = s.find('.');
    std::string e = s.substr(0, p), d = p == std::string::npos ? "" : s.substr(p + 1);
    d = (d + std::string(k, '0')).substr(0, k);
    return std::stoll(e) * (k == 2 ? 100 : 1000) + std::stoll(d);
}
void aff(const char* nom, long long c) {
    std::cout << nom << ": " << c / 100 << "." << std::setw(2) << std::setfill('0') << c % 100 << "\n";
}
int main() {
    int n;
    std::string taux, prix;
    long long q, ht = 0;
    std::cin >> n >> taux;
    long long tm = fixe(taux, 3);
    for (int i = 0; i < n; ++i) { std::cin >> q >> prix; ht += q * fixe(prix, 2); }
    long long tva = (ht * tm + 50000) / 100000;
    aff("HT", ht); aff("TVA", tva); aff("TTC", ht + tva);
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const fixe = (s, k) => { const [e, d = ""] = s.split("."); return BigInt(e) * 10n ** BigInt(k) + BigInt((d + "000").slice(0, k)); };
const fmt = c => `${c / 100n}.${String(c % 100n).padStart(2, "0")}`;
const [n, taux] = L[0].trim().split(/\s+/);
const tm = fixe(taux, 3);
let ht = 0n;
for (let i = 1; i <= Number(n); i++) {
  const [q, p] = L[i].trim().split(/\s+/);
  ht += BigInt(q) * fixe(p, 2);
}
const tva = (ht * tm + 50000n) / 100000n;
console.log(`HT: ${fmt(ht)}\nTVA: ${fmt(tva)}\nTTC: ${fmt(ht + tva)}`);""", "php": r"""
<?php
function fixe(string $s, int $k): int {
    $p = explode('.', $s);
    return (int) $p[0] * 10 ** $k + (int) substr(($p[1] ?? '') . '000', 0, $k);
}
function fmt(int $c): string { return intdiv($c, 100) . '.' . sprintf('%02d', $c % 100); }
[$n, $taux] = explode(' ', trim(fgets(STDIN)));
$tm = fixe($taux, 3);
$ht = 0;
for ($i = 0; $i < (int) $n; $i++) {
    [$q, $p] = explode(' ', trim(fgets(STDIN)));
    $ht += (int) $q * fixe($p, 2);
}
$tva = intdiv($ht * $tm + 50000, 100000);
echo "HT: ", fmt($ht), "\nTVA: ", fmt($tva), "\nTTC: ", fmt($ht + $tva), "\n";"""}),

    ch("bases", 4, "mini", "Changement de base", "représentation",
       "Lisez « a b N » : un nombre N écrit en base a, à réécrire en base b (2 ≤ a, b ≤ 36 ; chiffres 0-9 puis A-Z en majuscules ; "
       "N ≤ 2^63 - 1). Contrainte : écrivez la conversion vous-même.",
       [("10 2 255", "11111111"), ("16 10 FF", "255"), ("2 16 101010", "2A"), ("36 10 ZZ", "1295"), ("7 3 0", "0"),
        ("10 36 9223372036854775807", "1Y2P0IJ32E8E7"), ("16 8 7FFFFFFFFFFFFFFF", "777777777777777777777"), ("3 5 2211201", "31241")],
       ["Deux étapes : lire N en base a pour obtenir sa valeur, puis écrire cette valeur en base b.",
        "Lecture (schéma de Horner) : valeur = valeur × a + chiffre, pour chaque chiffre de gauche à droite. 'A' vaut 10, 'Z' vaut 35.",
        "Écriture : les restes successifs de la division par b, du dernier au premier. En JavaScript, BigInt ; en PHP, base_convert perd en précision."],
       {"python": r"""
CH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
a, b, s = input().split()
a, b = int(a), int(b)
v = 0
for c in s:
    v = v * a + CH.index(c)
out = ""
while True:
    out = CH[v % b] + out
    v //= b
    if v == 0:
        break
print(out)""", "c": r"""
#include <stdio.h>
#include <string.h>
int main(void) {
    const char *CH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    int a, b;
    char s[80], out[80];
    if (scanf("%d %d %79s", &a, &b, s) != 3) return 1;
    unsigned long long v = 0;
    for (char *p = s; *p; ++p) v = v * a + (unsigned long long)(strchr(CH, *p) - CH);
    int k = 0;
    do { out[k++] = CH[v % b]; v /= b; } while (v > 0);
    while (k > 0) putchar(out[--k]);
    putchar('\n');
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
#include <algorithm>
int main() {
    const std::string CH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    int a, b;
    std::string s, out;
    std::cin >> a >> b >> s;
    unsigned long long v = 0;
    for (char c : s) v = v * a + CH.find(c);
    do { out += CH[v % b]; v /= b; } while (v > 0);
    std::reverse(out.begin(), out.end());
    std::cout << out << std::endl;
}""", "javascript": r"""
const CH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const [a, b, s] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/);
const A = BigInt(a), B = BigInt(b);
let v = 0n;
for (const c of s) v = v * A + BigInt(CH.indexOf(c));
let out = "";
do { out = CH[Number(v % B)] + out; v /= B; } while (v > 0n);
console.log(out);""", "php": r"""
<?php
$CH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
[$a, $b, $s] = explode(' ', trim(fgets(STDIN)));
$a = (int) $a; $b = (int) $b;
$v = 0;
foreach (str_split($s) as $c) $v = $v * $a + strpos($CH, $c);
$out = "";
do { $out = $CH[$v % $b] . $out; $v = intdiv($v, $b); } while ($v > 0);
echo $out, "\n";"""},
       banned={"python": [r"int\s*\([^()]*,"], "php": [r"base_convert", r"bindec", r"hexdec", r"octdec", r"intval\s*\([^()]*,", r"decbin|dechex|decoct"],
               "javascript": [r"parseInt\s*\([^()]*,", r"toString\s*\(\s*[^)\s]"], "c": [r"\bstrto"], "cpp": [r"\bsto(i|l|ll|ul|ull)\b", r"\bstrto", r"from_chars"]}),

    ch("debordement", 4, "mini", "Multiplication sous contrôle", "débordements",
       "Lisez deux entiers a et b qui tiennent chacun sur 64 bits signés (de -2^63 à 2^63 - 1). Affichez a × b si le résultat tient aussi "
       "sur 64 bits signés, sinon « DÉPASSEMENT ».",
       [("3 4", "12"), ("4294967296 4294967296", "DÉPASSEMENT"), ("-9223372036854775808 1", "-9223372036854775808"), ("-9223372036854775808 -1", "DÉPASSEMENT"),
        ("3037000499 3037000499", "9223372030926249001"), ("3037000500 3037000500", "DÉPASSEMENT"), ("0 -9223372036854775808", "0"),
        ("-4611686018427387904 2", "-9223372036854775808"), ("4611686018427387904 2", "DÉPASSEMENT"), ("-3037000500 3037000500", "DÉPASSEMENT")],
       ["En C/C++, un débordement de long long est un comportement indéfini : il faut le détecter AVANT de multiplier.",
        "Pour a, b > 0 : a × b déborde ⇔ a > MAX / b. Faites le même raisonnement pour chaque combinaison de signes (attention au sens des inégalités avec un négatif).",
        "Python a des entiers illimités : comparez aux bornes. PHP bascule en float quand ça déborde (is_int). JavaScript : BigInt et bornes."],
       {"python": r"""
a, b = map(int, input().split())
p = a * b
print(p if -2 ** 63 <= p < 2 ** 63 else "DÉPASSEMENT")""", "c": r"""
#include <stdio.h>
#include <limits.h>
static int deborde(long long a, long long b) {
    if (a == 0 || b == 0) return 0;
    if (a > 0) return b > 0 ? a > LLONG_MAX / b : b < LLONG_MIN / a;
    return b > 0 ? a < LLONG_MIN / b : a < LLONG_MAX / b;
}
int main(void) {
    long long a, b;
    if (scanf("%lld %lld", &a, &b) != 2) return 1;
    if (deborde(a, b)) puts("DÉPASSEMENT");
    else printf("%lld\n", a * b);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <limits>
bool deborde(long long a, long long b) {
    const long long MX = std::numeric_limits<long long>::max(), MN = std::numeric_limits<long long>::min();
    if (a == 0 || b == 0) return false;
    if (a > 0) return b > 0 ? a > MX / b : b < MN / a;
    return b > 0 ? a < MN / b : a < MX / b;
}
int main() {
    long long a, b;
    std::cin >> a >> b;
    if (deborde(a, b)) std::cout << "DÉPASSEMENT\n";
    else std::cout << a * b << "\n";
}""", "javascript": r"""
const [a, b] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(BigInt);
const p = a * b;
console.log(p >= -(2n ** 63n) && p < 2n ** 63n ? p.toString() : "DÉPASSEMENT");""", "php": r"""
<?php
[$a, $b] = array_map('intval', explode(' ', trim(fgets(STDIN))));
$p = $a * $b;
echo is_int($p) ? $p : "DÉPASSEMENT", "\n";"""}),

    ch("csv", 4, "mini", "Lire un CSV", "parsing",
       "Ligne 1 : n. Puis n lignes au format CSV : champs séparés par des virgules ; un champ peut être entre guillemets, il peut alors contenir "
       "des virgules, et « \"\" » y représente un guillemet. Pour chaque ligne, affichez chaque champ entre crochets, séparés par une espace "
       "(« [a] [b] »). Les champs vides comptent. Contrainte : pas de bibliothèque CSV.",
       [(_C1, _csv(_C1)), (_C2, _csv(_C2)), (_C3, _csv(_C3)), (_C4, _csv(_C4))],
       ["Un simple split(\",\") casse les champs entre guillemets : lisez la ligne caractère par caractère.",
        "Deux états : dans les guillemets ou non. Dans les guillemets, une virgule est un caractère normal ; « \"\" » donne un guillemet ; un « \" » seul ferme.",
        "Une ligne « a, » contient deux champs dont le second est vide. N'oubliez pas le dernier champ en fin de ligne."],
       {"python": r"""
n = int(input())
for _ in range(n):
    line = input()
    champs, i, cur = [], 0, ""
    while True:
        if i < len(line) and line[i] == '"':
            i += 1
            while i < len(line):
                if line[i] == '"' and i + 1 < len(line) and line[i + 1] == '"':
                    cur += '"'
                    i += 2
                elif line[i] == '"':
                    i += 1
                    break
                else:
                    cur += line[i]
                    i += 1
        while i < len(line) and line[i] != ",":
            cur += line[i]
            i += 1
        champs.append(cur)
        cur = ""
        if i >= len(line):
            break
        i += 1
    print(" ".join(f"[{c}]" for c in champs))""", "c": r"""
#include <stdio.h>
#include <string.h>
int main(void) {
    int n;
    static char l[1 << 16];
    if (!fgets(l, sizeof l, stdin) || sscanf(l, "%d", &n) != 1) return 1;
    while (n-- > 0) {
        if (!fgets(l, sizeof l, stdin)) l[0] = '\0';
        l[strcspn(l, "\r\n")] = '\0';
        size_t i = 0, len = strlen(l);
        int premier = 1;
        for (;;) {
            printf(premier ? "[" : " [");
            premier = 0;
            if (i < len && l[i] == '"') {
                ++i;
                while (i < len) {
                    if (l[i] == '"' && i + 1 < len && l[i + 1] == '"') { putchar('"'); i += 2; }
                    else if (l[i] == '"') { ++i; break; }
                    else putchar(l[i++]);
                }
            }
            while (i < len && l[i] != ',') putchar(l[i++]);
            putchar(']');
            if (i >= len) break;
            ++i;
        }
        putchar('\n');
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
#include <vector>
std::vector<std::string> champs(const std::string& l) {
    std::vector<std::string> f;
    std::string cur;
    size_t i = 0;
    for (;;) {
        if (i < l.size() && l[i] == '"') {
            ++i;
            while (i < l.size()) {
                if (l[i] == '"' && i + 1 < l.size() && l[i + 1] == '"') { cur += '"'; i += 2; }
                else if (l[i] == '"') { ++i; break; }
                else cur += l[i++];
            }
        }
        while (i < l.size() && l[i] != ',') cur += l[i++];
        f.push_back(cur);
        cur.clear();
        if (i >= l.size()) return f;
        ++i;
    }
}
int main() {
    int n;
    std::string l;
    std::getline(std::cin, l);
    n = std::stoi(l);
    while (n-- > 0) {
        std::getline(std::cin, l);
        auto f = champs(l);
        for (size_t k = 0; k < f.size(); ++k) std::cout << (k ? " [" : "[") << f[k] << "]";
        std::cout << "\n";
    }
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const champs = l => {
  const f = [];
  let i = 0, cur = "";
  for (;;) {
    if (l[i] === '"') {
      i++;
      while (i < l.length) {
        if (l[i] === '"' && l[i + 1] === '"') { cur += '"'; i += 2; }
        else if (l[i] === '"') { i++; break; }
        else cur += l[i++];
      }
    }
    while (i < l.length && l[i] !== ",") cur += l[i++];
    f.push(cur);
    cur = "";
    if (i >= l.length) return f;
    i++;
  }
};
const n = Number(L[0]);
const out = [];
for (let k = 1; k <= n; k++) out.push(champs((L[k] || "").replace(/\r$/, "")).map(c => `[${c}]`).join(" "));
console.log(out.join("\n"));""", "php": r"""
<?php
function champs(string $l): array {
    $f = []; $i = 0; $cur = ''; $n = strlen($l);
    for (;;) {
        if ($i < $n && $l[$i] === '"') {
            $i++;
            while ($i < $n) {
                if ($l[$i] === '"' && $i + 1 < $n && $l[$i + 1] === '"') { $cur .= '"'; $i += 2; }
                elseif ($l[$i] === '"') { $i++; break; }
                else $cur .= $l[$i++];
            }
        }
        while ($i < $n && $l[$i] !== ',') $cur .= $l[$i++];
        $f[] = $cur;
        $cur = '';
        if ($i >= $n) return $f;
        $i++;
    }
}
$n = (int) trim(fgets(STDIN));
for ($k = 0; $k < $n; $k++) {
    $l = rtrim((string) fgets(STDIN), "\r\n");
    echo implode(' ', array_map(fn($c) => "[$c]", champs($l))), "\n";
}"""}, banned={"python": [r"\bcsv\b"], "php": [r"str_getcsv", r"fgetcsv"]}),

    ch("validation", 4, "mini", "Saisie blindée", "validation",
       "Ligne 1 : n. Puis n lignes. Pour chacune, décidez si c'est un entier 32 bits valide : un signe + ou - facultatif, puis des chiffres, "
       "sans espace, sans zéro inutile devant (« 0 » seul est permis, « 007 » non), et compris entre -2147483648 et 2147483647. "
       "Affichez « ok v » (v sans le + et sans signe pour zéro) ou « invalide ».",
       [(_V1, _valid(_V1)), (_V2, _valid(_V2)), (_V3, _valid(_V3))],
       ["Lisez chaque ligne entière, sans la « nettoyer » : une espace au début ou à la fin la rend invalide.",
        "Vérifiez dans l'ordre : signe facultatif, au moins un chiffre, uniquement des chiffres, pas de 0 en tête (sauf « 0 »).",
        "Pour la plage, ne convertissez pas un nombre de 30 chiffres : trop de chiffres (plus de 10) ⇒ invalide ; sinon convertissez en 64 bits et comparez."],
       {"python": r"""
n = int(input())
for _ in range(n):
    s = input()
    c = s[1:] if s[:1] in ("+", "-") else s
    ok = c.isdigit() and c.isascii() and (c == "0" or c[0] != "0") and len(c) <= 10 and -2 ** 31 <= int(s) < 2 ** 31
    print(f"ok {int(s)}" if ok else "invalide")""", "c": r"""
#include <stdio.h>
#include <string.h>
int main(void) {
    int n;
    char s[256];
    if (!fgets(s, sizeof s, stdin) || sscanf(s, "%d", &n) != 1) return 1;
    while (n-- > 0) {
        if (!fgets(s, sizeof s, stdin)) s[0] = '\0';
        s[strcspn(s, "\r\n")] = '\0';
        const char *c = s;
        int neg = 0;
        if (*c == '+' || *c == '-') neg = *c++ == '-';
        size_t len = strlen(c);
        int ok = len >= 1 && len <= 10 && (len == 1 || c[0] != '0');
        long long v = 0;
        for (size_t i = 0; ok && i < len; ++i) {
            if (c[i] < '0' || c[i] > '9') ok = 0;
            else v = v * 10 + (c[i] - '0');
        }
        if (neg) v = -v;
        if (ok && v >= -2147483648LL && v <= 2147483647LL) printf("ok %lld\n", v);
        else puts("invalide");
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
int main() {
    std::string s;
    std::getline(std::cin, s);
    int n = std::stoi(s);
    while (n-- > 0) {
        if (!std::getline(std::cin, s)) s.clear();
        if (!s.empty() && s.back() == '\r') s.pop_back();
        std::string c = s;
        bool neg = false;
        if (!c.empty() && (c[0] == '+' || c[0] == '-')) { neg = c[0] == '-'; c = c.substr(1); }
        bool ok = !c.empty() && c.size() <= 10 && (c.size() == 1 || c[0] != '0');
        long long v = 0;
        for (char d : c) { if (d < '0' || d > '9') { ok = false; break; } v = v * 10 + (d - '0'); }
        if (neg) v = -v;
        if (ok && v >= -2147483648LL && v <= 2147483647LL) std::cout << "ok " << v << "\n";
        else std::cout << "invalide\n";
    }
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const n = Number(L[0]), out = [];
for (let k = 1; k <= n; k++) {
  const s = (L[k] || "").replace(/\r$/, "");
  const m = /^([+-]?)(0|[1-9][0-9]{0,9})$/.exec(s);
  const v = m ? Number(m[1] + m[2]) : NaN;
  out.push(m && v >= -2147483648 && v <= 2147483647 ? `ok ${v === 0 ? 0 : v}` : "invalide");
}
console.log(out.join("\n"));""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
for ($k = 0; $k < $n; $k++) {
    $s = rtrim((string) fgets(STDIN), "\r\n");
    if (preg_match('/^[+-]?(0|[1-9][0-9]{0,9})$/', $s)) {
        $v = (int) $s;
        if ($v >= -2147483648 && $v <= 2147483647) { echo "ok $v\n"; continue; }
    }
    echo "invalide\n";
}"""}),

    ch("horloge", 4, "mini", "L'horloge qui tourne", "arithmétique modulaire",
       "Ligne 1 : une heure HH:MM. Ligne 2 : un nombre de minutes m (positif ou négatif, jusqu'à ±10^12). Affichez l'heure qu'il sera "
       "(ou qu'il était) m minutes plus tard, au format HH:MM sur 24 heures.",
       [("23:30\n45", "00:15"), ("00:10\n-20", "23:50"), ("12:00\n1440", "12:00"), ("00:00\n0", "00:00"),
        ("05:05\n-1000000000000", "18:25"), ("23:59\n999999999999", "10:38"), ("08:15\n-1", "08:14")],
       ["Convertissez l'heure en minutes depuis minuit, ajoutez m, puis revenez en HH:MM.",
        "Une journée fait 1440 minutes : prenez le résultat modulo 1440.",
        "Le modulo d'un négatif est négatif en C/C++/JS/PHP : ((x % 1440) + 1440) % 1440. Et m dépasse 2^31 : 64 bits."],
       {"python": r"""
h, mi = map(int, input().split(":"))
x = (h * 60 + mi + int(input())) % 1440
print(f"{x // 60:02d}:{x % 60:02d}")""", "c": r"""
#include <stdio.h>
int main(void) {
    int h, mi;
    long long m;
    if (scanf("%d:%d %lld", &h, &mi, &m) != 3) return 1;
    long long x = ((h * 60 + mi + m % 1440) % 1440 + 1440) % 1440;
    printf("%02lld:%02lld\n", x / 60, x % 60);
    return 0;
}""", "cpp": r"""
#include <cstdio>
int main() {
    int h, mi;
    long long m;
    if (std::scanf("%d:%d %lld", &h, &mi, &m) != 3) return 1;
    long long x = ((h * 60 + mi + m % 1440) % 1440 + 1440) % 1440;
    std::printf("%02lld:%02lld\n", x / 60, x % 60);
}""", "javascript": r"""
const [t, m] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/);
const [h, mi] = t.split(":").map(Number);
const x = (((h * 60 + mi + Number(m) % 1440) % 1440) + 1440) % 1440;
console.log(`${String(Math.floor(x / 60)).padStart(2, "0")}:${String(x % 60).padStart(2, "0")}`);""", "php": r"""
<?php
[$h, $mi] = array_map('intval', explode(':', trim(fgets(STDIN))));
$m = (int) trim(fgets(STDIN));
$x = (($h * 60 + $mi + $m % 1440) % 1440 + 1440) % 1440;
printf("%02d:%02d\n", intdiv($x, 60), $x % 60);"""}),

    ch("releve", 4, "exam", "Examen : le relevé bancaire", "robustesse",
       "Chaque ligne de l'entrée (jusqu'à la fin) est une opération « AAAA-MM-JJ;montant;libellé ». Une ligne est valide si elle a exactement "
       "3 champs, une date réelle (mois 1 à 12, jour existant, années bissextiles comprises) au format exact, un montant au format "
       "[+|-]chiffres[.1 ou 2 chiffres] et un libellé non vide. Les lignes vides sont ignorées. Affichez pour chaque mois (ordre chronologique) "
       "« AAAA-MM : total », puis « Solde : total », « Opérations : k » et « Lignes invalides : j ». Totaux avec 2 décimales, signe - si négatif.",
       [(_R1, _releve(_R1)), (_R2, _releve(_R2)), (_R3, _releve(_R3))],
       ["Validez chaque morceau séparément, et comptez une ligne invalide dès qu'un morceau échoue.",
        "Montants en centimes entiers (« 12.5 » → 1250, « -3.1 » → -310) : aucune erreur d'arrondi possible.",
        "Un dictionnaire « AAAA-MM » → total, trié à la fin. Les expressions régulières aident beaucoup pour le format."],
       {"python": r"""
import re
import sys

def jours(a, m):
    bis = (a % 4 == 0 and a % 100 != 0) or a % 400 == 0
    return [31, 29 if bis else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]

def centimes(s):
    neg = s.startswith("-")
    e, _, d = s.lstrip("+-").partition(".")
    v = int(e) * 100 + int((d + "00")[:2])
    return -v if neg else v

def fmt(c):
    return ("-" if c < 0 else "") + f"{abs(c) // 100}.{abs(c) % 100:02d}"

mois, invalides, ops = {}, 0, 0
for l in sys.stdin.read().split("\n"):
    if not l.strip():
        continue
    p = l.split(";")
    ok = len(p) == 3 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p[0]) and re.fullmatch(r"[+-]?\d+(\.\d{1,2})?", p[1]) and p[2].strip()
    if ok:
        a, m, j = map(int, p[0].split("-"))
        ok = 1 <= m <= 12 and 1 <= j <= jours(a, m)
    if not ok:
        invalides += 1
        continue
    ops += 1
    mois[p[0][:7]] = mois.get(p[0][:7], 0) + centimes(p[1])
for k in sorted(mois):
    print(f"{k} : {fmt(mois[k])}")
print(f"Solde : {fmt(sum(mois.values()))}")
print(f"Opérations : {ops}")
print(f"Lignes invalides : {invalides}")""", "c": r"""
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>
typedef struct { char cle[8]; long long total; } Mois;
static Mois mois[2000];
static int nm = 0;
static int jours(int a, int m) {
    const int j[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    return j[m - 1] + (m == 2 && ((a % 4 == 0 && a % 100 != 0) || a % 400 == 0));
}
static int chiffres(const char *s, int n) { for (int i = 0; i < n; ++i) if (!isdigit((unsigned char)s[i])) return 0; return 1; }
static int date_ok(const char *d) {
    if (strlen(d) != 10 || d[4] != '-' || d[7] != '-' || !chiffres(d, 4) || !chiffres(d + 5, 2) || !chiffres(d + 8, 2)) return 0;
    int a = atoi(d), m = atoi(d + 5), j = atoi(d + 8);
    return m >= 1 && m <= 12 && j >= 1 && j <= jours(a, m);
}
/* montant → centimes ; renvoie 0 si le format est faux */
static int montant(const char *s, long long *c) {
    int neg = 0;
    if (*s == '+' || *s == '-') neg = *s++ == '-';
    long long e = 0, d = 0;
    int ne = 0, nd = 0;
    while (isdigit((unsigned char)*s)) { e = e * 10 + (*s++ - '0'); ++ne; }
    if (!ne) return 0;
    if (*s == '.') {
        ++s;
        while (isdigit((unsigned char)*s)) { d = d * 10 + (*s++ - '0'); ++nd; }
        if (nd < 1 || nd > 2) return 0;
        if (nd == 1) d *= 10;
    }
    if (*s) return 0;
    *c = (e * 100 + d) * (neg ? -1 : 1);
    return 1;
}
static int parcle(const void *a, const void *b) { return strcmp(((const Mois *)a)->cle, ((const Mois *)b)->cle); }
static void fmt(long long c) { printf("%s%lld.%02lld\n", c < 0 ? "-" : "", llabs(c) / 100, llabs(c) % 100); }
int main(void) {
    static char l[4096];
    int invalides = 0, ops = 0;
    while (fgets(l, sizeof l, stdin)) {
        l[strcspn(l, "\r\n")] = '\0';
        int vide = 1;
        for (char *p = l; *p; ++p) if (!isspace((unsigned char)*p)) vide = 0;
        if (vide) continue;
        char *champ[4];
        int n = 0;
        char *p = l;
        champ[n++] = p;
        for (; *p; ++p) if (*p == ';') { *p = '\0'; if (n < 4) champ[n++] = p + 1; else { n = 5; break; } }
        long long c;
        int lib = 0;
        if (n == 3) for (char *q = champ[2]; *q; ++q) if (!isspace((unsigned char)*q)) lib = 1;
        if (n != 3 || !date_ok(champ[0]) || !montant(champ[1], &c) || !lib) { ++invalides; continue; }
        ++ops;
        int i = 0;
        while (i < nm && strncmp(mois[i].cle, champ[0], 7) != 0) ++i;
        if (i == nm) { memcpy(mois[nm].cle, champ[0], 7); mois[nm].cle[7] = '\0'; mois[nm++].total = 0; }
        mois[i].total += c;
    }
    qsort(mois, nm, sizeof *mois, parcle);
    long long solde = 0;
    for (int i = 0; i < nm; ++i) { printf("%s : ", mois[i].cle); fmt(mois[i].total); solde += mois[i].total; }
    printf("Solde : "); fmt(solde);
    printf("Opérations : %d\nLignes invalides : %d\n", ops, invalides);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <map>
#include <regex>
#include <string>
#include <vector>
int jours(int a, int m) {
    const int j[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    return j[m - 1] + (m == 2 && ((a % 4 == 0 && a % 100 != 0) || a % 400 == 0));
}
std::string fmt(long long c) {
    long long a = c < 0 ? -c : c;
    std::string d = std::to_string(a % 100);
    return (c < 0 ? "-" : "") + std::to_string(a / 100) + "." + (d.size() < 2 ? "0" : "") + d;
}
int main() {
    const std::regex rd(R"(\d{4}-\d{2}-\d{2})"), rm(R"(([+-]?)(\d+)(?:\.(\d{1,2}))?)");
    std::map<std::string, long long> mois;
    int invalides = 0, ops = 0;
    std::string l;
    while (std::getline(std::cin, l)) {
        if (!l.empty() && l.back() == '\r') l.pop_back();
        if (l.find_first_not_of(" \t") == std::string::npos) continue;
        std::vector<std::string> p;
        size_t s = 0, e;
        while ((e = l.find(';', s)) != std::string::npos) { p.push_back(l.substr(s, e - s)); s = e + 1; }
        p.push_back(l.substr(s));
        std::smatch m;
        bool ok = p.size() == 3 && std::regex_match(p[0], rd) && std::regex_match(p[1], m, rm)
                  && p[2].find_first_not_of(" \t") != std::string::npos;
        if (ok) {
            int a = std::stoi(p[0].substr(0, 4)), mo = std::stoi(p[0].substr(5, 2)), j = std::stoi(p[0].substr(8, 2));
            ok = mo >= 1 && mo <= 12 && j >= 1 && j <= jours(a, mo);
        }
        if (!ok) { ++invalides; continue; }
        std::string d = m[3].str();
        while (d.size() < 2) d += '0';
        long long c = std::stoll(m[2].str()) * 100 + std::stoll(d);
        if (m[1].str() == "-") c = -c;
        ++ops;
        mois[p[0].substr(0, 7)] += c;
    }
    long long solde = 0;
    for (auto& [k, v] : mois) { std::cout << k << " : " << fmt(v) << "\n"; solde += v; }
    std::cout << "Solde : " << fmt(solde) << "\nOpérations : " << ops << "\nLignes invalides : " << invalides << "\n";
}""", "javascript": r"""
const jours = (a, m) => [31, (a % 4 === 0 && a % 100 !== 0) || a % 400 === 0 ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1];
const fmt = c => (c < 0 ? "-" : "") + `${Math.floor(Math.abs(c) / 100)}.${String(Math.abs(c) % 100).padStart(2, "0")}`;
const mois = new Map();
let invalides = 0, ops = 0;
for (const brut of require("fs").readFileSync(0, "utf8").split("\n")) {
  const l = brut.replace(/\r$/, "");
  if (!l.trim()) continue;
  const p = l.split(";");
  let ok = p.length === 3 && /^\d{4}-\d{2}-\d{2}$/.test(p[0]) && /^[+-]?\d+(\.\d{1,2})?$/.test(p[1]) && p[2].trim() !== "";
  if (ok) {
    const [a, m, j] = p[0].split("-").map(Number);
    ok = m >= 1 && m <= 12 && j >= 1 && j <= jours(a, m);
  }
  if (!ok) { invalides++; continue; }
  const [e, d = ""] = p[1].replace(/^[+-]/, "").split(".");
  let c = Number(e) * 100 + Number((d + "00").slice(0, 2));
  if (p[1][0] === "-") c = -c;
  ops++;
  const k = p[0].slice(0, 7);
  mois.set(k, (mois.get(k) || 0) + c);
}
const out = [];
let solde = 0;
for (const k of [...mois.keys()].sort()) { out.push(`${k} : ${fmt(mois.get(k))}`); solde += mois.get(k); }
out.push(`Solde : ${fmt(solde)}`, `Opérations : ${ops}`, `Lignes invalides : ${invalides}`);
console.log(out.join("\n"));""", "php": r"""
<?php
function jours(int $a, int $m): int {
    return [31, ($a % 4 === 0 && $a % 100 !== 0) || $a % 400 === 0 ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][$m - 1];
}
function fmt(int $c): string { return ($c < 0 ? '-' : '') . intdiv(abs($c), 100) . '.' . sprintf('%02d', abs($c) % 100); }
$mois = []; $invalides = 0; $ops = 0;
while (($l = fgets(STDIN)) !== false) {
    $l = rtrim($l, "\r\n");
    if (trim($l) === '') continue;
    $p = explode(';', $l);
    $ok = count($p) === 3 && preg_match('/^\d{4}-\d{2}-\d{2}$/', $p[0]) && preg_match('/^([+-]?)(\d+)(?:\.(\d{1,2}))?$/', $p[1], $m) && trim($p[2]) !== '';
    if ($ok) {
        [$a, $mo, $j] = array_map('intval', explode('-', $p[0]));
        $ok = $mo >= 1 && $mo <= 12 && $j >= 1 && $j <= jours($a, $mo);
    }
    if (!$ok) { $invalides++; continue; }
    $c = (int) $m[2] * 100 + (int) substr(($m[3] ?? '') . '00', 0, 2);
    if ($m[1] === '-') $c = -$c;
    $ops++;
    $k = substr($p[0], 0, 7);
    $mois[$k] = ($mois[$k] ?? 0) + $c;
}
ksort($mois);
foreach ($mois as $k => $v) echo "$k : ", fmt($v), "\n";
echo "Solde : ", fmt(array_sum($mois)), "\nOpérations : $ops\nLignes invalides : $invalides\n";"""}, minutes=45),
]
