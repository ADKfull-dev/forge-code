# -*- coding: utf-8 -*-
"""Palier 11 (1/2) — Projets d'ingénieur : calculatrice, grands entiers, machine virtuelle, compression, arbres."""
from .base import ch, lines


def _rand(n, lo, hi, seed=1):
    x, out = seed, []
    for _ in range(n):
        x = (x * 6364136223846793005 + 1442695040888963407) % 2 ** 64
        out.append(lo + (x >> 33) % (hi - lo + 1))
    return out


def _chiffres(n, seed):
    d = _rand(n, 0, 9, seed)
    d[0] = d[0] or 7
    return "".join(map(str, d))


_VM_FACT = """PUSH 1
PUSH 10
boucle:
DUP
JZ fin
DUP
ROT
MUL
SWAP
PUSH 1
SUB
JMP boucle
fin:
POP
PRINT"""

_VM_CPT = """PUSH 5
debut:
DUP
PRINT
PUSH 1
SUB
DUP
JNZ debut
POP
PUSH 42
PRINT
HALT
PUSH 7
PRINT"""

_VM_ERR = """PUSH 7
PUSH 0
DIV
PRINT"""

_VM_PGCD = """PUSH 1071
PUSH 462
tant_que:
DUP
JZ fini
DUP
ROT
SWAP
MOD
JMP tant_que
fini:
POP
PRINT
PUSH -7
PUSH 2
DIV
PRINT
PUSH -7
PUSH 2
MOD
PRINT
ADD"""

_VM_CARRES = """PUSH 0
PUSH 20
boucle:
DUP
JZ fin
DUP
DUP
MUL
ROT
ADD
SWAP
PUSH 1
SUB
JMP boucle
fin:
POP
PRINT"""

_VM_LT = """PUSH 0
b:
DUP
PUSH 10
LT
JZ f
DUP
PUSH 5
LT
JZ saute
DUP
PRINT
saute:
PUSH 1
ADD
JMP b
f:
HALT"""

DEFIS = [
    ch("calculatrice", 11, "mini", "La calculatrice", "analyse syntaxique",
       "Lisez une expression avec des entiers, + - * /, des parenthèses, des espaces et le moins unaire (ex. « -(2 + 3) * 2 »). "
       "Affichez son résultat. Les divisions tombent toujours juste. Contrainte : sans eval.",
       [("1 + 2 * 3", "7"), ("(1 + 2) * 3", "9"), ("10 / 2 - 3", "2"), ("2 * (3 + 4) * 5 - 6 / 3", "68"), ("-4 + 10", "6"),
        ("((7))", "7"), ("100 - 2 - 3", "95"), ("-(2 + 3) * 2", "-10"), ("2*3*4/8-1", "2"), ("1000000 * 1000000 - 1", "999999999999")],
       ["Découpez le problème en fonctions : expression (+ -), terme (* /), facteur (nombre, parenthèses, moins unaire).",
        "Chaque fonction appelle la suivante : c'est une « descente récursive ».",
        "Attention à l'associativité : 100 - 2 - 3 se calcule de gauche à droite (boucle, pas récursion à droite)."],
       {"cpp": r"""
#include <iostream>
#include <string>
#include <cctype>
std::string s;
size_t i = 0;
void sp() { while (i < s.size() && s[i] == ' ') ++i; }
long long expr();
long long fact() {
    sp();
    if (s[i] == '-') { ++i; return -fact(); }
    if (s[i] == '(') { ++i; long long v = expr(); sp(); ++i; return v; }
    long long v = 0;
    while (i < s.size() && std::isdigit((unsigned char)s[i])) v = v * 10 + (s[i++] - '0');
    return v;
}
long long term() {
    long long v = fact();
    for (;;) { sp(); if (i < s.size() && (s[i] == '*' || s[i] == '/')) { char o = s[i++]; long long r = fact(); v = o == '*' ? v * r : v / r; } else return v; }
}
long long expr() {
    long long v = term();
    for (;;) { sp(); if (i < s.size() && (s[i] == '+' || s[i] == '-')) { char o = s[i++]; long long r = term(); v = o == '+' ? v + r : v - r; } else return v; }
}
int main() {
    std::getline(std::cin, s);
    std::cout << expr() << std::endl;
}""", "c": r"""
#include <stdio.h>
#include <string.h>
#include <ctype.h>
static char s[4096];
static size_t i = 0;
static void sp(void) { while (s[i] == ' ') ++i; }
static long long expr(void);
static long long fact(void) {
    sp();
    if (s[i] == '-') { ++i; return -fact(); }
    if (s[i] == '(') { ++i; long long v = expr(); sp(); ++i; return v; }
    long long v = 0;
    while (isdigit((unsigned char)s[i])) v = v * 10 + (s[i++] - '0');
    return v;
}
static long long term(void) {
    long long v = fact();
    for (;;) { sp(); if (s[i] == '*' || s[i] == '/') { char o = s[i++]; long long r = fact(); v = o == '*' ? v * r : v / r; } else return v; }
}
static long long expr(void) {
    long long v = term();
    for (;;) { sp(); if (s[i] == '+' || s[i] == '-') { char o = s[i++]; long long r = term(); v = o == '+' ? v + r : v - r; } else return v; }
}
int main(void) {
    if (!fgets(s, sizeof s, stdin)) return 1;
    s[strcspn(s, "\r\n")] = '\0';
    printf("%lld\n", expr());
    return 0;
}""", "python": r"""
s = input().replace(" ", "")
i = 0

def fact():
    global i
    if s[i] == "-":
        i += 1
        return -fact()
    if s[i] == "(":
        i += 1
        v = expr()
        i += 1
        return v
    j = i
    while i < len(s) and s[i].isdigit():
        i += 1
    return int(s[j:i])

def term():
    global i
    v = fact()
    while i < len(s) and s[i] in "*/":
        o = s[i]
        i += 1
        r = fact()
        v = v * r if o == "*" else v // r
    return v

def expr():
    global i
    v = term()
    while i < len(s) and s[i] in "+-":
        o = s[i]
        i += 1
        r = term()
        v = v + r if o == "+" else v - r
    return v

print(expr())""", "javascript": r"""
const s = require("fs").readFileSync(0, "utf8").split("\n")[0].replace(/\s+/g, "");
let i = 0;
const fact = () => {
  if (s[i] === "-") { i++; return -fact(); }
  if (s[i] === "(") { i++; const v = expr(); i++; return v; }
  const j = i;
  while (i < s.length && s[i] >= "0" && s[i] <= "9") i++;
  return BigInt(s.slice(j, i));
};
const term = () => {
  let v = fact();
  while (s[i] === "*" || s[i] === "/") { const o = s[i++], r = fact(); v = o === "*" ? v * r : v / r; }
  return v;
};
const expr = () => {
  let v = term();
  while (s[i] === "+" || s[i] === "-") { const o = s[i++], r = term(); v = o === "+" ? v + r : v - r; }
  return v;
};
console.log(expr().toString());""", "php": r"""
<?php
$s = str_replace(' ', '', trim(fgets(STDIN)));
$i = 0;
function fact(): int {
    global $s, $i;
    if ($s[$i] === '-') { $i++; return -fact(); }
    if ($s[$i] === '(') { $i++; $v = expr(); $i++; return $v; }
    $j = $i;
    while ($i < strlen($s) && ctype_digit($s[$i])) $i++;
    return (int) substr($s, $j, $i - $j);
}
function term(): int {
    global $s, $i;
    $v = fact();
    while ($i < strlen($s) && ($s[$i] === '*' || $s[$i] === '/')) { $o = $s[$i++]; $r = fact(); $v = $o === '*' ? $v * $r : intdiv($v, $r); }
    return $v;
}
function expr(): int {
    global $s, $i;
    $v = term();
    while ($i < strlen($s) && ($s[$i] === '+' || $s[$i] === '-')) { $o = $s[$i++]; $r = term(); $v = $o === '+' ? $v + $r : $v - $r; }
    return $v;
}
echo expr(), "\n";"""}, banned={"*": [r"\beval\s*\(", r"\bexec\s*\("], "javascript": [r"Function\s*\("]}),

    ch("grands-entiers", 11, "mini", "Les grands entiers", "arithmétique multiprécision",
       "Deux lignes : deux entiers positifs ou nuls a et b, jusqu'à 1 000 chiffres. Affichez « somme: a+b », « différence: a-b » (avec un - si "
       "négatif) et « produit: a×b », sans zéros inutiles devant. Contrainte : pas de type « grand entier » tout fait (écrivez les opérations de l'école).",
       [("123\n456", "somme: 579\ndifférence: -333\nproduit: 56088"), ("99999999999999999999\n1", "somme: 100000000000000000000\ndifférence: 99999999999999999998\nproduit: 99999999999999999999"),
        "0\n0", "1000\n1000", "12345678901234567890123456789\n98765432109876543210", lambda: _chiffres(1000, 3) + "\n" + _chiffres(1000, 5),
        lambda: _chiffres(1000, 7) + "\n" + _chiffres(3, 9)],
       ["Représentez chaque nombre par un tableau de chiffres, du chiffre des unités au plus fort (on lit la chaîne à l'envers).",
        "Addition et soustraction : chiffre par chiffre avec une retenue. Pour a - b avec a < b, calculez b - a et ajoutez le signe (comparez d'abord longueurs puis chiffres).",
        "Multiplication : r[i + j] += a[i] × b[j] pour tous i, j, puis propagez les retenues. Supprimez enfin les zéros de tête (en gardant au moins « 0 »)."],
       {"python": r"""
def lire(s):
    return [ord(c) - 48 for c in reversed(s.strip())]

def texte(v):
    while len(v) > 1 and v[-1] == 0:
        v.pop()
    return "".join(chr(d + 48) for d in reversed(v))

def plus_petit(a, b):
    a, b = texte(a[:]), texte(b[:])
    return (len(a), a) < (len(b), b)

def somme(a, b):
    r, ret = [], 0
    for i in range(max(len(a), len(b))):
        t = (a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0) + ret
        r.append(t % 10)
        ret = t // 10
    if ret:
        r.append(ret)
    return r

def diff(a, b):          # a >= b
    r, ret = [], 0
    for i in range(len(a)):
        t = a[i] - (b[i] if i < len(b) else 0) - ret
        ret = 1 if t < 0 else 0
        r.append(t + 10 if t < 0 else t)
    return r

def produit(a, b):
    r = [0] * (len(a) + len(b))
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            r[i + j] += x * y
    for k in range(len(r) - 1):
        r[k + 1] += r[k] // 10
        r[k] %= 10
    return r

a, b = lire(input()), lire(input())
print(f"somme: {texte(somme(a, b))}")
print(f"différence: {'-' + texte(diff(b, a)) if plus_petit(a, b) else texte(diff(a, b))}")
print(f"produit: {texte(produit(a, b))}")""", "c": r"""
#include <stdio.h>
#include <string.h>
static char sa[1100], sb[1100];
static int a[1100], b[1100], r[2300];
static int la, lb;
static void aff(const char *nom, const int *v, int n, int neg) {
    while (n > 1 && v[n - 1] == 0) --n;
    printf("%s: %s", nom, neg ? "-" : "");
    for (int i = n - 1; i >= 0; --i) putchar('0' + v[i]);
    putchar('\n');
}
static int longueur(const int *v, int n) { while (n > 1 && v[n - 1] == 0) --n; return n; }
static int compare(void) {           /* -1 si a < b, 0 si égaux, 1 sinon */
    int na = longueur(a, la), nb = longueur(b, lb);
    if (na != nb) return na < nb ? -1 : 1;
    for (int i = na - 1; i >= 0; --i) if (a[i] != b[i]) return a[i] < b[i] ? -1 : 1;
    return 0;
}
static int soustrait(const int *x, int lx, const int *y, int ly, int *res) {
    int ret = 0;
    for (int i = 0; i < lx; ++i) {
        int t = x[i] - (i < ly ? y[i] : 0) - ret;
        ret = t < 0;
        res[i] = t < 0 ? t + 10 : t;
    }
    return lx;
}
int main(void) {
    if (scanf("%1099s %1099s", sa, sb) != 2) return 1;
    la = (int)strlen(sa); lb = (int)strlen(sb);
    for (int i = 0; i < la; ++i) a[i] = sa[la - 1 - i] - '0';
    for (int i = 0; i < lb; ++i) b[i] = sb[lb - 1 - i] - '0';
    int n = la > lb ? la : lb, ret = 0;
    for (int i = 0; i < n; ++i) { int t = a[i] + b[i] + ret; r[i] = t % 10; ret = t / 10; }
    r[n] = ret;
    aff("somme", r, n + 1, 0);
    memset(r, 0, sizeof r);
    if (compare() < 0) aff("différence", r, soustrait(b, lb, a, la, r), 1);
    else aff("différence", r, soustrait(a, la, b, lb, r), 0);
    memset(r, 0, sizeof r);
    for (int i = 0; i < la; ++i) for (int j = 0; j < lb; ++j) r[i + j] += a[i] * b[j];
    for (int k = 0; k < la + lb - 1; ++k) { r[k + 1] += r[k] / 10; r[k] %= 10; }
    aff("produit", r, la + lb, 0);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
using Nombre = std::vector<int>;                 // chiffres, unités d'abord
Nombre lire(const std::string& s) { Nombre v; for (auto it = s.rbegin(); it != s.rend(); ++it) v.push_back(*it - '0'); return v; }
void normalise(Nombre& v) { while (v.size() > 1 && v.back() == 0) v.pop_back(); }
std::string texte(Nombre v) { normalise(v); std::string s; for (auto it = v.rbegin(); it != v.rend(); ++it) s += char('0' + *it); return s; }
bool plus_petit(Nombre a, Nombre b) {
    normalise(a); normalise(b);
    if (a.size() != b.size()) return a.size() < b.size();
    return std::lexicographical_compare(a.rbegin(), a.rend(), b.rbegin(), b.rend());
}
Nombre somme(const Nombre& a, const Nombre& b) {
    Nombre r;
    int ret = 0;
    for (size_t i = 0; i < std::max(a.size(), b.size()); ++i) {
        int t = (i < a.size() ? a[i] : 0) + (i < b.size() ? b[i] : 0) + ret;
        r.push_back(t % 10);
        ret = t / 10;
    }
    if (ret) r.push_back(ret);
    return r;
}
Nombre diff(const Nombre& a, const Nombre& b) {
    Nombre r;
    int ret = 0;
    for (size_t i = 0; i < a.size(); ++i) {
        int t = a[i] - (i < b.size() ? b[i] : 0) - ret;
        ret = t < 0;
        r.push_back(t < 0 ? t + 10 : t);
    }
    return r;
}
Nombre produit(const Nombre& a, const Nombre& b) {
    Nombre r(a.size() + b.size(), 0);
    for (size_t i = 0; i < a.size(); ++i) for (size_t j = 0; j < b.size(); ++j) r[i + j] += a[i] * b[j];
    for (size_t k = 0; k + 1 < r.size(); ++k) { r[k + 1] += r[k] / 10; r[k] %= 10; }
    return r;
}
int main() {
    std::string x, y;
    std::cin >> x >> y;
    Nombre a = lire(x), b = lire(y);
    std::cout << "somme: " << texte(somme(a, b)) << "\n";
    std::cout << "différence: " << (plus_petit(a, b) ? "-" + texte(diff(b, a)) : texte(diff(a, b))) << "\n";
    std::cout << "produit: " << texte(produit(a, b)) << "\n";
}""", "javascript": r"""
const [x, y] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/);
const lire = s => [...s].reverse().map(c => c.charCodeAt(0) - 48);
const texte = v => { v = v.slice(); while (v.length > 1 && v[v.length - 1] === 0) v.pop(); return v.reverse().join(""); };
const plusPetit = (a, b) => { const p = texte(a), q = texte(b); return p.length !== q.length ? p.length < q.length : p < q; };
const somme = (a, b) => {
  const r = [];
  let ret = 0;
  for (let i = 0; i < Math.max(a.length, b.length); i++) { const t = (a[i] || 0) + (b[i] || 0) + ret; r.push(t % 10); ret = Math.floor(t / 10); }
  if (ret) r.push(ret);
  return r;
};
const diff = (a, b) => {
  const r = [];
  let ret = 0;
  for (let i = 0; i < a.length; i++) { const t = a[i] - (b[i] || 0) - ret; ret = t < 0 ? 1 : 0; r.push(t < 0 ? t + 10 : t); }
  return r;
};
const produit = (a, b) => {
  const r = new Array(a.length + b.length).fill(0);
  for (let i = 0; i < a.length; i++) for (let j = 0; j < b.length; j++) r[i + j] += a[i] * b[j];
  for (let k = 0; k + 1 < r.length; k++) { r[k + 1] += Math.floor(r[k] / 10); r[k] %= 10; }
  return r;
};
const a = lire(x), b = lire(y);
console.log(`somme: ${texte(somme(a, b))}`);
console.log(`différence: ${plusPetit(a, b) ? "-" + texte(diff(b, a)) : texte(diff(a, b))}`);
console.log(`produit: ${texte(produit(a, b))}`);""", "php": r"""
<?php
function lire(string $s): array { return array_map(fn($c) => ord($c) - 48, array_reverse(str_split($s))); }
function texte(array $v): string { while (count($v) > 1 && end($v) === 0) array_pop($v); return implode('', array_reverse($v)); }
function plusPetit(array $a, array $b): bool { $p = texte($a); $q = texte($b); return strlen($p) !== strlen($q) ? strlen($p) < strlen($q) : strcmp($p, $q) < 0; }
function somme(array $a, array $b): array {
    $r = []; $ret = 0;
    for ($i = 0; $i < max(count($a), count($b)); $i++) { $t = ($a[$i] ?? 0) + ($b[$i] ?? 0) + $ret; $r[] = $t % 10; $ret = intdiv($t, 10); }
    if ($ret) $r[] = $ret;
    return $r;
}
function diff(array $a, array $b): array {
    $r = []; $ret = 0;
    for ($i = 0; $i < count($a); $i++) { $t = $a[$i] - ($b[$i] ?? 0) - $ret; $ret = $t < 0 ? 1 : 0; $r[] = $t < 0 ? $t + 10 : $t; }
    return $r;
}
function produit(array $a, array $b): array {
    $r = array_fill(0, count($a) + count($b), 0);
    foreach ($a as $i => $x) foreach ($b as $j => $y) $r[$i + $j] += $x * $y;
    for ($k = 0; $k + 1 < count($r); $k++) { $r[$k + 1] += intdiv($r[$k], 10); $r[$k] %= 10; }
    return $r;
}
$a = lire(trim(fgets(STDIN)));
$b = lire(trim(fgets(STDIN)));
echo "somme: ", texte(somme($a, $b)), "\n";
echo "différence: ", plusPetit($a, $b) ? "-" . texte(diff($b, $a)) : texte(diff($a, $b)), "\n";
echo "produit: ", texte(produit($a, $b)), "\n";"""}, time=3,
       banned={"python": [r"\bint\s*\(", r"\bdecimal\b", r"\beval\b"], "javascript": [r"BigInt", r"\d+n\b"], "php": [r"\bbc[a-z]+\s*\(", r"\bgmp_"]}),

    ch("machine-virtuelle", 11, "mini", "La machine virtuelle à pile", "interprétation",
       "Chaque ligne de l'entrée est une instruction d'une machine à pile (entiers 64 bits) : PUSH n, POP, DUP, SWAP (échange les deux du haut), "
       "ROT (fait remonter le 3e élément en haut : a b c → b c a), ADD, SUB, MUL, DIV, MOD (sur « a b » : a op b, division tronquée vers zéro, "
       "reste du signe de a), LT (1 si a < b, sinon 0), PRINT (dépile et affiche), JMP étiquette, JZ / JNZ étiquette (dépile, saute si nul / non nul), "
       "HALT, et des étiquettes « nom: ». Exécutez le programme. En cas d'erreur, affichez « erreur ligne k: pile vide » ou « erreur ligne k: division "
       "par zéro » (k à partir de 1) et arrêtez.",
       [_VM_CPT, _VM_ERR, _VM_FACT, _VM_PGCD, _VM_CARRES, _VM_LT, "PRINT", "PUSH 3\nPUSH 4\nSWAP\nSUB\nPRINT\nPUSH 5\nPUSH 6\nPUSH 7\nROT\nPRINT\nPRINT\nPRINT"],
       ["Lisez tout le programme d'abord : une liste d'instructions, et un dictionnaire étiquette → numéro d'instruction.",
        "Un compteur de programme (pc) indique l'instruction courante ; il avance de 1, sauf lors d'un saut réussi.",
        "Avant chaque opération, vérifiez qu'il y a assez d'éléments sur la pile. Pour ROT : retirez le 3e élément depuis le haut et remettez-le au sommet."],
       {"python": r"""
import sys
prog = [l.strip() for l in sys.stdin.read().split("\n")]
etiq = {l[:-1]: i for i, l in enumerate(prog) if l.endswith(":")}
pile, pc, out = [], 0, []
BESOIN = {"POP": 1, "DUP": 1, "SWAP": 2, "ROT": 3, "ADD": 2, "SUB": 2, "MUL": 2, "DIV": 2, "MOD": 2, "LT": 2, "PRINT": 1, "JZ": 1, "JNZ": 1}
while pc < len(prog):
    l = prog[pc]
    pc += 1
    if not l or l.endswith(":"):
        continue
    op, *arg = l.split()
    if len(pile) < BESOIN.get(op, 0):
        out.append(f"erreur ligne {pc}: pile vide")
        break
    if op == "PUSH":
        pile.append(int(arg[0]))
    elif op == "POP":
        pile.pop()
    elif op == "DUP":
        pile.append(pile[-1])
    elif op == "SWAP":
        pile[-1], pile[-2] = pile[-2], pile[-1]
    elif op == "ROT":
        pile.append(pile.pop(-3))
    elif op in ("ADD", "SUB", "MUL", "DIV", "MOD", "LT"):
        b, a = pile.pop(), pile.pop()
        if op in ("DIV", "MOD") and b == 0:
            out.append(f"erreur ligne {pc}: division par zéro")
            break
        q = abs(a) // abs(b) * (1 if (a < 0) == (b < 0) else -1) if b else 0
        pile.append({"ADD": a + b, "SUB": a - b, "MUL": a * b, "DIV": q, "MOD": a - b * q, "LT": int(a < b)}[op])
    elif op == "PRINT":
        out.append(str(pile.pop()))
    elif op == "JMP":
        pc = etiq[arg[0]]
    elif op in ("JZ", "JNZ"):
        v = pile.pop()
        if (v == 0) == (op == "JZ"):
            pc = etiq[arg[0]]
    elif op == "HALT":
        break
print("\n".join(out))""", "c": r"""
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
static char prog[2000][64], op[2000][16], arg[2000][48];
static long long pile[100000];
int main(void) {
    int n = 0, t = 0;
    while (n < 2000 && fgets(prog[n], sizeof prog[n], stdin)) {
        prog[n][strcspn(prog[n], "\r\n")] = '\0';
        op[n][0] = arg[n][0] = '\0';
        sscanf(prog[n], "%15s %47s", op[n], arg[n]);
        ++n;
    }
    for (int pc = 0; pc < n;) {
        int ligne = pc + 1;
        char *o = op[pc], *a = arg[pc];
        size_t lo = strlen(o);
        ++pc;
        if (lo == 0 || o[lo - 1] == ':') continue;
        int besoin = !strcmp(o, "ROT") ? 3 : (!strcmp(o, "SWAP") || !strcmp(o, "ADD") || !strcmp(o, "SUB") || !strcmp(o, "MUL") || !strcmp(o, "DIV") || !strcmp(o, "MOD") || !strcmp(o, "LT")) ? 2
                   : (!strcmp(o, "POP") || !strcmp(o, "DUP") || !strcmp(o, "PRINT") || !strcmp(o, "JZ") || !strcmp(o, "JNZ")) ? 1 : 0;
        if (t < besoin) { printf("erreur ligne %d: pile vide\n", ligne); return 0; }
        if (!strcmp(o, "PUSH")) pile[t++] = atoll(a);
        else if (!strcmp(o, "POP")) --t;
        else if (!strcmp(o, "DUP")) { pile[t] = pile[t - 1]; ++t; }
        else if (!strcmp(o, "SWAP")) { long long x = pile[t - 1]; pile[t - 1] = pile[t - 2]; pile[t - 2] = x; }
        else if (!strcmp(o, "ROT")) { long long x = pile[t - 3]; pile[t - 3] = pile[t - 2]; pile[t - 2] = pile[t - 1]; pile[t - 1] = x; }
        else if (besoin == 2) {
            long long b = pile[--t], x = pile[--t];
            if ((!strcmp(o, "DIV") || !strcmp(o, "MOD")) && b == 0) { printf("erreur ligne %d: division par zéro\n", ligne); return 0; }
            pile[t++] = !strcmp(o, "ADD") ? x + b : !strcmp(o, "SUB") ? x - b : !strcmp(o, "MUL") ? x * b : !strcmp(o, "DIV") ? x / b : !strcmp(o, "MOD") ? x % b : x < b;
        } else if (!strcmp(o, "PRINT")) printf("%lld\n", pile[--t]);
        else if (!strcmp(o, "HALT")) break;
        else {
            int saute = !strcmp(o, "JMP");
            if (!saute) { long long v = pile[--t]; saute = (v == 0) == !strcmp(o, "JZ"); }
            if (saute) {
                char cible[64];
                snprintf(cible, sizeof cible, "%s:", a);
                for (int k = 0; k < n; ++k) if (!strcmp(op[k], cible)) { pc = k; break; }
            }
        }
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>
int main() {
    std::vector<std::string> ops, args;
    std::map<std::string, size_t> etiq;
    std::string l;
    while (std::getline(std::cin, l)) {
        std::istringstream in(l);
        std::string o, a;
        in >> o >> a;
        if (!o.empty() && o.back() == ':') etiq[o.substr(0, o.size() - 1)] = ops.size();
        ops.push_back(o);
        args.push_back(a);
    }
    const std::map<std::string, size_t> besoin = {{"POP", 1}, {"DUP", 1}, {"SWAP", 2}, {"ROT", 3}, {"ADD", 2}, {"SUB", 2}, {"MUL", 2},
                                                  {"DIV", 2}, {"MOD", 2}, {"LT", 2}, {"PRINT", 1}, {"JZ", 1}, {"JNZ", 1}};
    std::vector<long long> p;
    for (size_t pc = 0; pc < ops.size();) {
        size_t ligne = pc + 1;
        const std::string o = ops[pc], a = args[pc];
        ++pc;
        if (o.empty() || o.back() == ':') continue;
        auto it = besoin.find(o);
        if (it != besoin.end() && p.size() < it->second) { std::cout << "erreur ligne " << ligne << ": pile vide\n"; return 0; }
        auto depile = [&] { long long v = p.back(); p.pop_back(); return v; };
        if (o == "PUSH") p.push_back(std::stoll(a));
        else if (o == "POP") p.pop_back();
        else if (o == "DUP") p.push_back(p.back());
        else if (o == "SWAP") std::swap(p[p.size() - 1], p[p.size() - 2]);
        else if (o == "ROT") { long long x = p[p.size() - 3]; p.erase(p.end() - 3); p.push_back(x); }
        else if (o == "ADD" || o == "SUB" || o == "MUL" || o == "DIV" || o == "MOD" || o == "LT") {
            long long b = depile(), x = depile();
            if ((o == "DIV" || o == "MOD") && b == 0) { std::cout << "erreur ligne " << ligne << ": division par zéro\n"; return 0; }
            p.push_back(o == "ADD" ? x + b : o == "SUB" ? x - b : o == "MUL" ? x * b : o == "DIV" ? x / b : o == "MOD" ? x % b : x < b);
        } else if (o == "PRINT") std::cout << depile() << "\n";
        else if (o == "JMP") pc = etiq[a];
        else if (o == "JZ" || o == "JNZ") { long long v = depile(); if ((v == 0) == (o == "JZ")) pc = etiq[a]; }
        else if (o == "HALT") break;
    }
}""", "javascript": r"""
const prog = require("fs").readFileSync(0, "utf8").split("\n").map(l => l.trim().split(/\s+/));
const etiq = new Map();
prog.forEach(([o], i) => { if (o && o.endsWith(":")) etiq.set(o.slice(0, -1), i); });
const BESOIN = { POP: 1, DUP: 1, SWAP: 2, ROT: 3, ADD: 2, SUB: 2, MUL: 2, DIV: 2, MOD: 2, LT: 2, PRINT: 1, JZ: 1, JNZ: 1 };
const p = [], out = [];
for (let pc = 0; pc < prog.length;) {
  const [o, a] = prog[pc++];
  if (!o || o.endsWith(":")) continue;
  if (p.length < (BESOIN[o] || 0)) { out.push(`erreur ligne ${pc}: pile vide`); break; }
  if (o === "PUSH") p.push(BigInt(a));
  else if (o === "POP") p.pop();
  else if (o === "DUP") p.push(p[p.length - 1]);
  else if (o === "SWAP") { const x = p.pop(), y = p.pop(); p.push(x, y); }
  else if (o === "ROT") p.push(p.splice(p.length - 3, 1)[0]);
  else if (["ADD", "SUB", "MUL", "DIV", "MOD", "LT"].includes(o)) {
    const b = p.pop(), x = p.pop();
    if ((o === "DIV" || o === "MOD") && b === 0n) { out.push(`erreur ligne ${pc}: division par zéro`); break; }
    p.push(o === "ADD" ? x + b : o === "SUB" ? x - b : o === "MUL" ? x * b : o === "DIV" ? x / b : o === "MOD" ? x % b : x < b ? 1n : 0n);
  } else if (o === "PRINT") out.push(p.pop().toString());
  else if (o === "JMP") pc = etiq.get(a);
  else if (o === "JZ" || o === "JNZ") { const v = p.pop(); if ((v === 0n) === (o === "JZ")) pc = etiq.get(a); }
  else if (o === "HALT") break;
}
console.log(out.join("\n"));""", "php": r"""
<?php
$prog = [];
while (($l = fgets(STDIN)) !== false) $prog[] = preg_split('/\s+/', trim($l));
$etiq = [];
foreach ($prog as $i => $ins) if ($ins[0] !== '' && str_ends_with($ins[0], ':')) $etiq[substr($ins[0], 0, -1)] = $i;
$besoin = ['POP' => 1, 'DUP' => 1, 'SWAP' => 2, 'ROT' => 3, 'ADD' => 2, 'SUB' => 2, 'MUL' => 2, 'DIV' => 2, 'MOD' => 2, 'LT' => 2, 'PRINT' => 1, 'JZ' => 1, 'JNZ' => 1];
$p = [];
for ($pc = 0, $n = count($prog); $pc < $n;) {
    $o = $prog[$pc][0];
    $a = $prog[$pc][1] ?? '';
    $pc++;
    if ($o === '' || str_ends_with($o, ':')) continue;
    if (count($p) < ($besoin[$o] ?? 0)) { echo "erreur ligne $pc: pile vide\n"; break; }
    if ($o === 'PUSH') $p[] = (int) $a;
    elseif ($o === 'POP') array_pop($p);
    elseif ($o === 'DUP') $p[] = end($p);
    elseif ($o === 'SWAP') { $x = array_pop($p); $y = array_pop($p); array_push($p, $x, $y); }
    elseif ($o === 'ROT') { $x = array_splice($p, -3, 1)[0]; $p[] = $x; }
    elseif (in_array($o, ['ADD', 'SUB', 'MUL', 'DIV', 'MOD', 'LT'], true)) {
        $b = array_pop($p); $x = array_pop($p);
        if (($o === 'DIV' || $o === 'MOD') && $b === 0) { echo "erreur ligne $pc: division par zéro\n"; break; }
        $p[] = match ($o) { 'ADD' => $x + $b, 'SUB' => $x - $b, 'MUL' => $x * $b, 'DIV' => intdiv($x, $b), 'MOD' => $x % $b, 'LT' => $x < $b ? 1 : 0 };
    } elseif ($o === 'PRINT') echo array_pop($p), "\n";
    elseif ($o === 'JMP') $pc = $etiq[$a];
    elseif ($o === 'JZ' || $o === 'JNZ') { $v = array_pop($p); if (($v === 0) === ($o === 'JZ')) $pc = $etiq[$a]; }
    elseif ($o === 'HALT') break;
}"""}),

    ch("huffman", 11, "mini", "Compression de Huffman", "compression",
       "Lisez une ligne de texte ASCII (jusqu'à 100 000 caractères, non vide). Affichez « symboles: k » (nombre de caractères distincts) puis "
       "« bits: b », la taille du texte compressé avec un code de Huffman optimal (somme, pour chaque caractère, de sa fréquence × la longueur de son code). "
       "S'il n'y a qu'un seul symbole, son code fait 1 bit.",
       [("abracadabra", "symboles: 5\nbits: 23"), ("aaaa", "symboles: 1\nbits: 4"), "Forge Code, l'atelier du code !", "ab",
        lambda: "".join(chr(33 + x % 90) for x in _rand(100000, 0, 10 ** 6, 3)), lambda: "".join("aaaaaaaabbbbccd e"[x % 17] for x in _rand(100000, 0, 10 ** 6, 5))],
       ["Comptez la fréquence de chaque caractère.",
        "Huffman : tant qu'il reste au moins deux arbres, fusionnez les deux de plus petite fréquence (file de priorité).",
        "Astuce : le nombre total de bits est la somme des fréquences de tous les nœuds créés par les fusions. Pas besoin de construire les codes !"],
       {"python": r"""
import heapq
s = input()
freq = {}
for c in s:
    freq[c] = freq.get(c, 0) + 1
tas = list(freq.values())
heapq.heapify(tas)
bits = 0 if len(tas) > 1 else len(s)
while len(tas) > 1:
    a, b = heapq.heappop(tas), heapq.heappop(tas)
    bits += a + b
    heapq.heappush(tas, a + b)
print(f"symboles: {len(freq)}")
print(f"bits: {bits}")""", "c": r"""
#include <stdio.h>
#include <string.h>
static long long tas[300];
static int nt = 0;
static void pousse(long long x) {
    int i = nt++;
    tas[i] = x;
    while (i && tas[(i - 1) / 2] > tas[i]) { long long t = tas[i]; tas[i] = tas[(i - 1) / 2]; tas[(i - 1) / 2] = t; i = (i - 1) / 2; }
}
static long long retire(void) {
    long long r = tas[0];
    tas[0] = tas[--nt];
    for (int i = 0;;) {
        int g = 2 * i + 1, d = g + 1, m = i;
        if (g < nt && tas[g] < tas[m]) m = g;
        if (d < nt && tas[d] < tas[m]) m = d;
        if (m == i) break;
        long long t = tas[i]; tas[i] = tas[m]; tas[m] = t;
        i = m;
    }
    return r;
}
int main(void) {
    static char s[200005];
    long long freq[256] = {0};
    if (!fgets(s, sizeof s, stdin)) return 1;
    s[strcspn(s, "\r\n")] = '\0';
    size_t n = strlen(s);
    for (size_t i = 0; i < n; ++i) freq[(unsigned char)s[i]]++;
    int k = 0;
    for (int c = 0; c < 256; ++c) if (freq[c]) { pousse(freq[c]); ++k; }
    long long bits = k > 1 ? 0 : (long long)n;
    while (nt > 1) { long long a = retire(), b = retire(); bits += a + b; pousse(a + b); }
    printf("symboles: %d\nbits: %lld\n", k, bits);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <map>
#include <queue>
#include <string>
#include <vector>
#include <functional>
int main() {
    std::string s;
    std::getline(std::cin, s);
    std::map<char, long long> freq;
    for (char c : s) ++freq[c];
    std::priority_queue<long long, std::vector<long long>, std::greater<long long>> tas;
    for (auto& [c, f] : freq) tas.push(f);
    long long bits = tas.size() > 1 ? 0 : (long long)s.size();
    while (tas.size() > 1) {
        long long a = tas.top(); tas.pop();
        long long b = tas.top(); tas.pop();
        bits += a + b;
        tas.push(a + b);
    }
    std::cout << "symboles: " << freq.size() << "\nbits: " << bits << "\n";
}""", "javascript": r"""
const s = require("fs").readFileSync(0, "utf8").split("\n")[0].replace(/\r$/, "");
const freq = new Map();
for (const c of s) freq.set(c, (freq.get(c) || 0) + 1);
// au plus 128 symboles : une liste triée suffit comme file de priorité
const f = [...freq.values()].sort((a, b) => a - b);
let bits = f.length > 1 ? 0 : s.length;
while (f.length > 1) {
  const x = f.shift() + f.shift();
  bits += x;
  let i = 0;
  while (i < f.length && f[i] < x) i++;
  f.splice(i, 0, x);
}
console.log(`symboles: ${freq.size}\nbits: ${bits}`);""", "php": r"""
<?php
$s = rtrim((string) fgets(STDIN), "\r\n");
$freq = count_chars($s, 1);
$tas = new SplMinHeap();
foreach ($freq as $f) $tas->insert($f);
$bits = count($freq) > 1 ? 0 : strlen($s);
while (count($tas) > 1) {
    $x = $tas->extract() + $tas->extract();
    $bits += $x;
    $tas->insert($x);
}
echo "symboles: ", count($freq), "\nbits: $bits\n";"""}),

    ch("abr", 11, "mini", "L'arbre binaire de recherche", "arbres",
       "Ligne 1 : n (jusqu'à 100 000). Ligne 2 : n entiers distincts, à insérer dans cet ordre dans un arbre binaire de recherche (sans rééquilibrage : "
       "plus petit à gauche, plus grand à droite). Affichez « hauteur: h » (nombre d'arêtes du plus long chemin racine → feuille), puis « préfixe: … » "
       "(racine, sous-arbre gauche, sous-arbre droit) et « suffixe: … » (gauche, droit, racine).",
       [("7\n50 30 70 20 40 60 80", None), ("1\n5", None), ("5\n1 2 3 4 5", None), ("6\n10 5 1 7 40 50", None),
        lambda: "100000\n" + " ".join(map(str, sorted(set(_rand(130000, 1, 10 ** 9, 7)), key=lambda x: (x * 2654435761) % 2 ** 32)[:100000])),
        lambda: "2000\n" + " ".join(map(str, range(2000, 0, -1)))],
       ["Chaque nœud a une valeur, un enfant gauche et un enfant droit. Pour insérer, descendez depuis la racine en comparant jusqu'à trouver une place libre.",
        "Tableaux parallèles valeur[], gauche[], droite[] (indices, -1 = vide) : simple et rapide dans tous les langages.",
        "Un arbre « en ligne » (valeurs triées) a 2 000 niveaux : une récursion peut dépasser la limite (Python : 1 000). Utilisez des parcours avec une pile explicite."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
v = list(map(int, L[1].split()))
g, d = [-1] * len(v), [-1] * len(v)
haut = 0
for i in range(1, len(v)):
    c, prof = 0, 1
    while True:
        if v[i] < v[c]:
            if g[c] < 0:
                g[c] = i
                break
            c = g[c]
        else:
            if d[c] < 0:
                d[c] = i
                break
            c = d[c]
        prof += 1
    haut = max(haut, prof)
pre, pile = [], [0]
while pile:
    c = pile.pop()
    pre.append(v[c])
    if d[c] >= 0:
        pile.append(d[c])
    if g[c] >= 0:
        pile.append(g[c])
post, pile = [], [0]
while pile:                       # racine, droite, gauche… puis on inverse
    c = pile.pop()
    post.append(v[c])
    if g[c] >= 0:
        pile.append(g[c])
    if d[c] >= 0:
        pile.append(d[c])
post.reverse()
print(f"hauteur: {haut}")
print("préfixe:", *pre)
print("suffixe:", *post)""", "c": r"""
#include <stdio.h>
static long long v[100005];
static int g[100005], d[100005], pile[100005], post[100005];
int main(void) {
    int n, h = 0;
    if (scanf("%d", &n) != 1) return 1;
    for (int i = 0; i < n; ++i) { if (scanf("%lld", &v[i]) != 1) return 1; g[i] = d[i] = -1; }
    for (int i = 1; i < n; ++i) {
        int c = 0, prof = 1;
        for (;;) {
            int *fils = v[i] < v[c] ? &g[c] : &d[c];
            if (*fils < 0) { *fils = i; break; }
            c = *fils;
            ++prof;
        }
        if (prof > h) h = prof;
    }
    printf("hauteur: %d\npréfixe:", h);
    int t = 0;
    pile[t++] = 0;
    while (t) {
        int c = pile[--t];
        printf(" %lld", v[c]);
        if (d[c] >= 0) pile[t++] = d[c];
        if (g[c] >= 0) pile[t++] = g[c];
    }
    printf("\nsuffixe:");
    int np = 0;
    pile[t++] = 0;
    while (t) {
        int c = pile[--t];
        post[np++] = c;
        if (g[c] >= 0) pile[t++] = g[c];
        if (d[c] >= 0) pile[t++] = d[c];
    }
    for (int i = np - 1; i >= 0; --i) printf(" %lld", v[post[i]]);
    printf("\n");
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <vector>
#include <algorithm>
struct Noeud { long long val; int g = -1, d = -1; };
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n, h = 0;
    std::cin >> n;
    std::vector<Noeud> a(n);
    for (auto& x : a) std::cin >> x.val;
    for (int i = 1; i < n; ++i) {
        int c = 0, prof = 1;
        for (;; ++prof) {
            int& fils = a[i].val < a[c].val ? a[c].g : a[c].d;
            if (fils < 0) { fils = i; break; }
            c = fils;
        }
        h = std::max(h, prof);
    }
    std::cout << "hauteur: " << h << "\npréfixe:";
    std::vector<int> pile{0}, post;
    while (!pile.empty()) {
        int c = pile.back(); pile.pop_back();
        std::cout << " " << a[c].val;
        if (a[c].d >= 0) pile.push_back(a[c].d);
        if (a[c].g >= 0) pile.push_back(a[c].g);
    }
    std::cout << "\nsuffixe:";
    pile = {0};
    while (!pile.empty()) {
        int c = pile.back(); pile.pop_back();
        post.push_back(c);
        if (a[c].g >= 0) pile.push_back(a[c].g);
        if (a[c].d >= 0) pile.push_back(a[c].d);
    }
    for (auto it = post.rbegin(); it != post.rend(); ++it) std::cout << " " << a[*it].val;
    std::cout << "\n";
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const v = L[1].trim().split(/\s+/).map(Number), n = v.length;
const g = new Int32Array(n).fill(-1), d = new Int32Array(n).fill(-1);
let h = 0;
for (let i = 1; i < n; i++) {
  let c = 0, prof = 1;
  for (;; prof++) {
    if (v[i] < v[c]) { if (g[c] < 0) { g[c] = i; break; } c = g[c]; }
    else { if (d[c] < 0) { d[c] = i; break; } c = d[c]; }
  }
  if (prof > h) h = prof;
}
const pre = [], post = [];
let pile = [0];
while (pile.length) {
  const c = pile.pop();
  pre.push(v[c]);
  if (d[c] >= 0) pile.push(d[c]);
  if (g[c] >= 0) pile.push(g[c]);
}
pile = [0];
while (pile.length) {
  const c = pile.pop();
  post.push(v[c]);
  if (g[c] >= 0) pile.push(g[c]);
  if (d[c] >= 0) pile.push(d[c]);
}
console.log(`hauteur: ${h}\npréfixe: ${pre.join(" ")}\nsuffixe: ${post.reverse().join(" ")}`);""", "php": r"""
<?php
fgets(STDIN);
$v = array_map('intval', preg_split('/\s+/', trim(fgets(STDIN))));
$n = count($v);
$g = array_fill(0, $n, -1);
$d = array_fill(0, $n, -1);
$h = 0;
for ($i = 1; $i < $n; $i++) {
    $c = 0; $prof = 1;
    for (;; $prof++) {
        if ($v[$i] < $v[$c]) { if ($g[$c] < 0) { $g[$c] = $i; break; } $c = $g[$c]; }
        else { if ($d[$c] < 0) { $d[$c] = $i; break; } $c = $d[$c]; }
    }
    if ($prof > $h) $h = $prof;
}
$pre = []; $post = [];
$pile = [0];
while ($pile) {
    $c = array_pop($pile);
    $pre[] = $v[$c];
    if ($d[$c] >= 0) $pile[] = $d[$c];
    if ($g[$c] >= 0) $pile[] = $g[$c];
}
$pile = [0];
while ($pile) {
    $c = array_pop($pile);
    $post[] = $v[$c];
    if ($g[$c] >= 0) $pile[] = $g[$c];
    if ($d[$c] >= 0) $pile[] = $d[$c];
}
echo "hauteur: $h\npréfixe: ", implode(' ', $pre), "\nsuffixe: ", implode(' ', array_reverse($post)), "\n";"""}, time=3),

    ch("autocompletion", 11, "mini", "L'autocomplétion", "arbres préfixes",
       "Ligne 1 : n (jusqu'à 100 000), ligne 2 : n mots en minuscules (le dictionnaire, avec d'éventuels doublons à ignorer). Ligne 3 : q (jusqu'à 20 000), "
       "puis q préfixes. Pour chacun, affichez le nombre de mots distincts qui commencent par ce préfixe, suivi des 3 premiers dans l'ordre alphabétique.",
       [("7\nforge forger fort code codeur cobra forge\n4\nfor\nco\nz\ncodeur", "3 forge forger fort\n3 cobra code codeur\n0\n1 codeur"),
        "3\na ab abc\n3\na\nab\nabcd",
        lambda: "100000\n" + " ".join("".join("abcdefg"[y % 7] for y in _rand(1 + x % 8, 0, 10 ** 6, x)) for x in range(100000)) + "\n20000\n" + lines("".join("abcdefg"[y % 7] for y in _rand(1 + x % 4, 0, 10 ** 6, x * 3 + 1)) for x in range(20000))],
       ["Triez le dictionnaire (sans doublons) : tous les mots qui commencent par un préfixe forment alors un bloc contigu.",
        "Recherche dichotomique du premier mot ≥ préfixe, puis du premier mot ≥ préfixe + un caractère plus grand que toutes les lettres (ex. « { »).",
        "Autre approche classique : un arbre préfixe (trie), où chaque nœud retient le nombre de mots en dessous."],
       {"python": r"""
import sys
from bisect import bisect_left
L = sys.stdin.read().split("\n")
mots = sorted(set(L[1].split()))
out = []
for p in L[3:3 + int(L[2])]:
    p = p.strip()
    a, b = bisect_left(mots, p), bisect_left(mots, p + "{")
    out.append(" ".join([str(b - a)] + mots[a:min(b, a + 3)]))
print("\n".join(out))""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static char mots[100005][16];
static int cmp(const void *a, const void *b) { return strcmp((const char *)a, (const char *)b); }
static int borne(int n, const char *x) {        /* premier indice i tel que mots[i] >= x */
    int lo = 0, hi = n;
    while (lo < hi) { int m = (lo + hi) / 2; if (strcmp(mots[m], x) < 0) lo = m + 1; else hi = m; }
    return lo;
}
int main(void) {
    int n, q, m = 0;
    if (scanf("%d", &n) != 1) return 1;
    for (int i = 0; i < n; ++i) if (scanf("%15s", mots[i]) != 1) return 1;
    qsort(mots, n, sizeof mots[0], cmp);
    for (int i = 0; i < n; ++i) if (m == 0 || strcmp(mots[m - 1], mots[i])) strcpy(mots[m++], mots[i]);
    if (scanf("%d", &q) != 1) return 1;
    while (q-- > 0) {
        char p[32], p2[40];
        if (scanf("%30s", p) != 1) return 1;
        snprintf(p2, sizeof p2, "%s{", p);
        int a = borne(m, p), b = borne(m, p2);
        printf("%d", b - a);
        for (int i = a; i < b && i < a + 3; ++i) printf(" %s", mots[i]);
        printf("\n");
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
    int n, q;
    std::cin >> n;
    std::vector<std::string> mots(n);
    for (auto& w : mots) std::cin >> w;
    std::sort(mots.begin(), mots.end());
    mots.erase(std::unique(mots.begin(), mots.end()), mots.end());
    std::cin >> q;
    while (q-- > 0) {
        std::string p;
        std::cin >> p;
        auto a = std::lower_bound(mots.begin(), mots.end(), p), b = std::lower_bound(mots.begin(), mots.end(), p + "{");
        std::cout << b - a;
        for (auto it = a; it != b && it != a + 3; ++it) std::cout << " " << *it;
        std::cout << "\n";
    }
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const mots = [...new Set(L[1].trim().split(/\s+/))].sort();
const borne = x => { let lo = 0, hi = mots.length; while (lo < hi) { const m = (lo + hi) >> 1; if (mots[m] < x) lo = m + 1; else hi = m; } return lo; };
const out = [];
for (let k = 0; k < Number(L[2]); k++) {
  const p = L[3 + k].trim(), a = borne(p), b = borne(p + "{");
  out.push([b - a, ...mots.slice(a, Math.min(b, a + 3))].join(" "));
}
console.log(out.join("\n"));""", "php": r"""
<?php
fgets(STDIN);
$mots = array_values(array_unique(preg_split('/\s+/', trim(fgets(STDIN)))));
sort($mots, SORT_STRING);
$n = count($mots);
$borne = function (string $x) use ($mots, $n): int {
    $lo = 0; $hi = $n;
    while ($lo < $hi) { $m = ($lo + $hi) >> 1; if (strcmp($mots[$m], $x) < 0) $lo = $m + 1; else $hi = $m; }
    return $lo;
};
$q = (int) trim(fgets(STDIN));
$out = [];
for ($k = 0; $k < $q; $k++) {
    $p = trim(fgets(STDIN));
    $a = $borne($p); $b = $borne($p . '{');
    $out[] = implode(' ', array_merge([$b - $a], array_slice($mots, $a, min(3, $b - $a))));
}
echo implode("\n", $out), "\n";"""}, time=3),
]
