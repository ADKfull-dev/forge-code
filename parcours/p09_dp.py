# -*- coding: utf-8 -*-
"""Palier 9 — Programmation dynamique et retour sur trace : les classiques des entretiens techniques."""
from .base import ch, lines


def _rand(n, lo, hi, seed=1):
    x, out = seed, []
    for _ in range(n):
        x = (x * 6364136223846793005 + 1442695040888963407) % 2 ** 64
        out.append(lo + (x >> 33) % (hi - lo + 1))
    return out


def _mot(n, seed, alpha="abcd"):
    return "".join(alpha[x % len(alpha)] for x in _rand(n, 0, 10 ** 6, seed))


def _sudoku(p):
    p = p.replace("0", ".")
    return lines(p[i:i + 9] for i in range(0, 81, 9))


def _grille(h, w, seed, pct):
    r = _rand(h * w, 0, 99, seed)
    g = [["#" if r[i * w + j] < pct else "." for j in range(w)] for i in range(h)]
    g[0][0] = g[h - 1][w - 1] = "."
    return f"{h} {w}\n" + lines("".join(x) for x in g)


def _dico(seed):
    syl = ["for", "ge", "co", "de", "pro", "gram", "me", "ur", "a", "b", "ab", "ba", "ra", "ma", "tion", "info", "r", "m"]
    mots = sorted(set(syl + [syl[a % 18] + syl[b % 18] for a, b in zip(_rand(300, 0, 10 ** 6, seed), _rand(300, 0, 10 ** 6, seed + 1))]))
    texte = "".join(syl[x % 18] for x in _rand(3000, 0, 10 ** 6, seed + 2))
    return f"{len(mots)}\n" + " ".join(mots) + "\n" + texte


_SUDOKUS = ["53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79",
            "003020600900305001001806400008102900700000008006708200002609500800203009005010300",
            "000000907000420180000705026100904000050000040000507009920108000034059000507000000",
            "100920000524010000000000070050008102000000000402700090060000000000030945000071006",
            "000900002050123400030000160908000000070000090000000205091000050007439020400007000",
            "001900003900700160030005007050000009004302600200000070600100030042007006500006800",
            "043080250600000000000001094900004070000608000010200003820500000000000005034090710"]

DEFIS = [
    ch("monnaie", 9, "mini", "Rendu de monnaie optimal", "programmation dynamique",
       "Ligne 1 : k (nombre de types de pièces) et un montant M (jusqu'à 100 000). Ligne 2 : les k valeurs des pièces. "
       "Avec autant de pièces de chaque type que voulu, affichez le nombre minimal de pièces pour faire exactement M, ou -1.",
       [("3 11\n1 2 5", "3"), ("1 3\n2", "-1"), ("3 6\n1 3 4", "2"), ("2 0\n1 2", "0"), ("3 30\n25 10 1", "3"), ("4 99999\n7 13 29 101", "995")],
       ["Prendre toujours la plus grosse pièce ne marche pas (6 avec 1, 3, 4 : 4+1+1 au lieu de 3+3).",
        "Programmation dynamique : best[m] = nombre minimal de pièces pour faire m.", "best[0] = 0 ; best[m] = min(best[m - p] + 1) pour chaque pièce p ≤ m."],
       {"cpp": r"""
#include <iostream>
#include <vector>
int main() {
    int k, m;
    std::cin >> k >> m;
    std::vector<int> c(k);
    for (auto& x : c) std::cin >> x;
    const int INF = 1 << 30;
    std::vector<int> b(m + 1, INF);
    b[0] = 0;
    for (int v = 1; v <= m; ++v)
        for (int p : c) if (p <= v && b[v - p] + 1 < b[v]) b[v] = b[v - p] + 1;
    std::cout << (b[m] >= INF ? -1 : b[m]) << std::endl;
}""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
int main(void) {
    int k, m, c[100];
    if (scanf("%d %d", &k, &m) != 2) return 1;
    for (int i = 0; i < k; ++i) if (scanf("%d", &c[i]) != 1) return 1;
    int *b = malloc(sizeof *b * (m + 1));
    b[0] = 0;
    for (int v = 1; v <= m; ++v) {
        b[v] = -1;
        for (int i = 0; i < k; ++i)
            if (c[i] <= v && b[v - c[i]] >= 0 && (b[v] < 0 || b[v - c[i]] + 1 < b[v])) b[v] = b[v - c[i]] + 1;
    }
    printf("%d\n", b[m]);
    free(b);
    return 0;
}""", "python": r"""
k, m = map(int, input().split())
c = list(map(int, input().split()))
INF = float("inf")
b = [0] + [INF] * m
for v in range(1, m + 1):
    b[v] = min((b[v - p] + 1 for p in c if p <= v), default=INF)
print(-1 if b[m] == INF else b[m])""", "javascript": r"""
const [k, m, ...c] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
const b = new Int32Array(m + 1).fill(-1);
b[0] = 0;
for (let v = 1; v <= m; v++)
  for (const p of c) if (p <= v && b[v - p] >= 0 && (b[v] < 0 || b[v - p] + 1 < b[v])) b[v] = b[v - p] + 1;
console.log(b[m]);""", "php": r"""
<?php
[$k, $m] = array_map('intval', explode(' ', trim(fgets(STDIN))));
$c = array_map('intval', explode(' ', trim(fgets(STDIN))));
$b = array_fill(0, $m + 1, -1);
$b[0] = 0;
for ($v = 1; $v <= $m; $v++)
    foreach ($c as $p) if ($p <= $v && $b[$v - $p] >= 0 && ($b[$v] < 0 || $b[$v - $p] + 1 < $b[$v])) $b[$v] = $b[$v - $p] + 1;
echo $b[$m], "\n";"""}, time=3),

    ch("escaliers", 9, "mini", "L'escalier", "programmation dynamique",
       "On monte un escalier de n marches (0 ≤ n ≤ 1 000 000) en faisant des pas de 1, 2 ou 3 marches. Combien y a-t-il de façons de monter ? "
       "Affichez le résultat modulo 1 000 000 007.",
       [("4", "7"), ("0", "1"), ("1", "1"), ("2", "2"), ("3", "4"), "50", "1000", "1000000"],
       ["Pour arriver à la marche n, le dernier pas vient de n-1, n-2 ou n-3.",
        "f(n) = f(n-1) + f(n-2) + f(n-3), avec f(0) = 1 et f(négatif) = 0.",
        "La récursion directe explose : remplissez un tableau (ou gardez les trois dernières valeurs), en prenant le modulo à chaque étape."],
       {"python": r"""
M = 1_000_000_007
n = int(input())
a, b, c = 1, 0, 0          # f(i), f(i-1), f(i-2)
for _ in range(n):
    a, b, c = (a + b + c) % M, a, b
print(a)""", "c": r"""
#include <stdio.h>
int main(void) {
    const long long M = 1000000007LL;
    long long n, a = 1, b = 0, c = 0;
    if (scanf("%lld", &n) != 1) return 1;
    for (long long i = 0; i < n; ++i) { long long t = (a + b + c) % M; c = b; b = a; a = t; }
    printf("%lld\n", a);
    return 0;
}""", "cpp": r"""
#include <iostream>
int main() {
    const long long M = 1000000007LL;
    long long n, a = 1, b = 0, c = 0;
    std::cin >> n;
    for (long long i = 0; i < n; ++i) { long long t = (a + b + c) % M; c = b; b = a; a = t; }
    std::cout << a << "\n";
}""", "javascript": r"""
const M = 1000000007;
const n = Number(require("fs").readFileSync(0, "utf8").trim());
let a = 1, b = 0, c = 0;
for (let i = 0; i < n; i++) [a, b, c] = [(a + b + c) % M, a, b];
console.log(a);""", "php": r"""
<?php
$M = 1000000007;
$n = (int) trim(fgets(STDIN));
$a = 1; $b = 0; $c = 0;
for ($i = 0; $i < $n; $i++) { $t = ($a + $b + $c) % $M; $c = $b; $b = $a; $a = $t; }
echo $a, "\n";"""}),

    ch("sac-a-dos", 9, "mini", "Le sac à dos", "programmation dynamique",
       "Ligne 1 : n objets (jusqu'à 100) et la capacité W du sac (jusqu'à 10 000). Puis n lignes « poids valeur » (valeur jusqu'à 10^9). "
       "Chaque objet peut être pris au plus une fois. Affichez la plus grande valeur totale possible sans dépasser W.",
       [("3 50\n10 60\n20 100\n30 120", "220"), ("1 5\n6 100", "0"), ("4 7\n1 1\n3 4\n4 5\n5 7", "9"),
        lambda: "100 10000\n" + lines(f"{p} {v}" for p, v in zip(_rand(100, 1, 1000, 3), _rand(100, 1, 10 ** 9, 5))),
        lambda: "100 10000\n" + lines(f"{p} {v}" for p, v in zip(_rand(100, 50, 300, 7), _rand(100, 1, 1000, 9)))],
       ["Essayer tous les sous-ensembles (2^100) est impossible ; prendre les objets « les plus rentables » d'abord ne marche pas toujours.",
        "best[c] = meilleure valeur avec une capacité c, en ne considérant que les objets déjà vus.",
        "Pour chaque objet (p, v), parcourez c de W jusqu'à p en DESCENDANT : best[c] = max(best[c], best[c - p] + v). Descendre évite de prendre l'objet deux fois."],
       {"python": r"""
import sys
d = sys.stdin.read().split()
n, W = int(d[0]), int(d[1])
best = [0] * (W + 1)
for i in range(n):
    p, v = int(d[2 + 2 * i]), int(d[3 + 2 * i])
    for c in range(W, p - 1, -1):
        if best[c - p] + v > best[c]:
            best[c] = best[c - p] + v
print(best[W])""", "c": r"""
#include <stdio.h>
static long long best[10005];
int main(void) {
    int n, W;
    if (scanf("%d %d", &n, &W) != 2) return 1;
    for (int i = 0; i < n; ++i) {
        int p;
        long long v;
        if (scanf("%d %lld", &p, &v) != 2) return 1;
        for (int c = W; c >= p; --c) if (best[c - p] + v > best[c]) best[c] = best[c - p] + v;
    }
    printf("%lld\n", best[W]);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <vector>
#include <algorithm>
int main() {
    int n, W;
    std::cin >> n >> W;
    std::vector<long long> best(W + 1, 0);
    for (int i = 0; i < n; ++i) {
        int p;
        long long v;
        std::cin >> p >> v;
        for (int c = W; c >= p; --c) best[c] = std::max(best[c], best[c - p] + v);
    }
    std::cout << best[W] << "\n";
}""", "javascript": r"""
const d = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
const n = d[0], W = d[1], best = new Float64Array(W + 1);
for (let i = 0; i < n; i++) {
  const p = d[2 + 2 * i], v = d[3 + 2 * i];
  for (let c = W; c >= p; c--) if (best[c - p] + v > best[c]) best[c] = best[c - p] + v;
}
console.log(best[W]);""", "php": r"""
<?php
$d = array_map('intval', preg_split('/\s+/', trim(stream_get_contents(STDIN))));
[$n, $W] = $d;
$best = array_fill(0, $W + 1, 0);
for ($i = 0; $i < $n; $i++) {
    $p = $d[2 + 2 * $i]; $v = $d[3 + 2 * $i];
    for ($c = $W; $c >= $p; $c--) if ($best[$c - $p] + $v > $best[$c]) $best[$c] = $best[$c - $p] + $v;
}
echo $best[$W], "\n";"""}, time=3),

    ch("lcs", 9, "mini", "La plus longue sous-séquence commune", "programmation dynamique",
       "Deux lignes : deux chaînes de lettres (jusqu'à 1 000 caractères chacune). Affichez la longueur de leur plus longue sous-séquence commune "
       "(des caractères pris dans l'ordre, pas forcément consécutifs : « ace » est une sous-séquence de « abcde »).",
       [("abcde\nace", "3"), ("abc\ndef", "0"), ("forgecode\ncodeforge", "5"), ("a\na", "1"), lambda: _mot(1000, 3) + "\n" + _mot(1000, 5), lambda: "a" * 1000 + "\n" + "a" * 999 + "b"],
       ["L[i][j] = longueur de la LCS des i premiers caractères de A et des j premiers de B.",
        "Si A[i-1] == B[j-1] : L[i][j] = L[i-1][j-1] + 1. Sinon : L[i][j] = max(L[i-1][j], L[i][j-1]).",
        "Deux lignes du tableau suffisent (la précédente et la courante) : moins de mémoire, et plus rapide."],
       {"python": r"""
a = input().strip()
b = input().strip()
prec = [0] * (len(b) + 1)
for x in a:
    cur = [0]
    for j, y in enumerate(b):
        cur.append(prec[j] + 1 if x == y else max(prec[j + 1], cur[j]))
    prec = cur
print(prec[-1])""", "c": r"""
#include <stdio.h>
#include <string.h>
static int prec[1005], cur[1005];
int main(void) {
    static char a[1005], b[1005];
    if (scanf("%1004s %1004s", a, b) != 2) return 1;
    int n = (int)strlen(a), m = (int)strlen(b);
    for (int i = 1; i <= n; ++i) {
        cur[0] = 0;
        for (int j = 1; j <= m; ++j)
            cur[j] = a[i - 1] == b[j - 1] ? prec[j - 1] + 1 : (prec[j] > cur[j - 1] ? prec[j] : cur[j - 1]);
        memcpy(prec, cur, sizeof(int) * (m + 1));
    }
    printf("%d\n", prec[m]);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
int main() {
    std::string a, b;
    std::cin >> a >> b;
    std::vector<int> prec(b.size() + 1, 0), cur(b.size() + 1, 0);
    for (char x : a) {
        for (size_t j = 1; j <= b.size(); ++j) cur[j] = x == b[j - 1] ? prec[j - 1] + 1 : std::max(prec[j], cur[j - 1]);
        std::swap(prec, cur);
    }
    std::cout << prec[b.size()] << "\n";
}""", "javascript": r"""
const [a, b] = require("fs").readFileSync(0, "utf8").trim().split(/\s+/);
let prec = new Int32Array(b.length + 1), cur = new Int32Array(b.length + 1);
for (let i = 0; i < a.length; i++) {
  for (let j = 1; j <= b.length; j++) cur[j] = a[i] === b[j - 1] ? prec[j - 1] + 1 : Math.max(prec[j], cur[j - 1]);
  [prec, cur] = [cur, prec];
}
console.log(prec[b.length]);""", "php": r"""
<?php
$a = trim(fgets(STDIN));
$b = trim(fgets(STDIN));
$m = strlen($b);
$prec = array_fill(0, $m + 1, 0);
for ($i = 0, $n = strlen($a); $i < $n; $i++) {
    $cur = [0];
    $x = $a[$i];
    for ($j = 1; $j <= $m; $j++) $cur[$j] = $x === $b[$j - 1] ? $prec[$j - 1] + 1 : max($prec[$j], $cur[$j - 1]);
    $prec = $cur;
}
echo $prec[$m], "\n";"""}, time=3),

    ch("levenshtein", 9, "mini", "La distance d'édition", "programmation dynamique",
       "Deux lignes : deux mots (jusqu'à 1 000 caractères). Affichez le nombre minimal d'opérations pour transformer le premier en le second, "
       "une opération étant l'insertion, la suppression ou le remplacement d'un caractère (distance de Levenshtein). Un mot peut être vide.",
       [("chat\nchien", "3"), ("forge\nforge", "0"), ("kitten\nsitting", "3"), ("\nabc", "3"), ("abc\n", "3"), ("intention\nexecution", "5"),
        lambda: _mot(1000, 11) + "\n" + _mot(900, 13)],
       ["D[i][j] = distance entre les i premiers caractères de A et les j premiers de B. D[i][0] = i, D[0][j] = j.",
        "Si A[i-1] == B[j-1] : D[i][j] = D[i-1][j-1]. Sinon : 1 + min(D[i-1][j] (suppression), D[i][j-1] (insertion), D[i-1][j-1] (remplacement)).",
        "Attention à la lecture : une ligne peut être vide (lisez les lignes, pas les « mots »)."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
a, b = L[0].strip(), L[1].strip() if len(L) > 1 else ""
prec = list(range(len(b) + 1))
for i, x in enumerate(a, 1):
    cur = [i]
    for j, y in enumerate(b, 1):
        cur.append(prec[j - 1] if x == y else 1 + min(prec[j], cur[j - 1], prec[j - 1]))
    prec = cur
print(prec[-1])""", "c": r"""
#include <stdio.h>
#include <string.h>
static int prec[1005], cur[1005];
int main(void) {
    static char a[1010] = "", b[1010] = "";
    if (!fgets(a, sizeof a, stdin)) a[0] = '\0';
    if (!fgets(b, sizeof b, stdin)) b[0] = '\0';
    a[strcspn(a, "\r\n")] = '\0';
    b[strcspn(b, "\r\n")] = '\0';
    int n = (int)strlen(a), m = (int)strlen(b);
    for (int j = 0; j <= m; ++j) prec[j] = j;
    for (int i = 1; i <= n; ++i) {
        cur[0] = i;
        for (int j = 1; j <= m; ++j) {
            if (a[i - 1] == b[j - 1]) cur[j] = prec[j - 1];
            else {
                int x = prec[j] < cur[j - 1] ? prec[j] : cur[j - 1];
                cur[j] = 1 + (x < prec[j - 1] ? x : prec[j - 1]);
            }
        }
        memcpy(prec, cur, sizeof(int) * (m + 1));
    }
    printf("%d\n", prec[m]);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
int main() {
    std::string a, b;
    std::getline(std::cin, a);
    std::getline(std::cin, b);
    std::vector<int> prec(b.size() + 1), cur(b.size() + 1);
    for (size_t j = 0; j <= b.size(); ++j) prec[j] = (int)j;
    for (size_t i = 1; i <= a.size(); ++i) {
        cur[0] = (int)i;
        for (size_t j = 1; j <= b.size(); ++j)
            cur[j] = a[i - 1] == b[j - 1] ? prec[j - 1] : 1 + std::min({prec[j], cur[j - 1], prec[j - 1]});
        std::swap(prec, cur);
    }
    std::cout << prec[b.size()] << "\n";
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const a = (L[0] || "").trim(), b = (L[1] || "").trim();
let prec = Int32Array.from({ length: b.length + 1 }, (_, j) => j), cur = new Int32Array(b.length + 1);
for (let i = 1; i <= a.length; i++) {
  cur[0] = i;
  for (let j = 1; j <= b.length; j++)
    cur[j] = a[i - 1] === b[j - 1] ? prec[j - 1] : 1 + Math.min(prec[j], cur[j - 1], prec[j - 1]);
  [prec, cur] = [cur, prec];
}
console.log(prec[b.length]);""", "php": r"""
<?php
$a = trim((string) fgets(STDIN));
$b = trim((string) fgets(STDIN));
$m = strlen($b);
$prec = range(0, $m);
for ($i = 1, $n = strlen($a); $i <= $n; $i++) {
    $cur = [$i];
    for ($j = 1; $j <= $m; $j++)
        $cur[$j] = $a[$i - 1] === $b[$j - 1] ? $prec[$j - 1] : 1 + min($prec[$j], $cur[$j - 1], $prec[$j - 1]);
    $prec = $cur;
}
echo $prec[$m], "\n";"""}, time=3),

    ch("lis", 9, "mini", "La plus longue suite croissante", "programmation dynamique",
       "Ligne 1 : n (jusqu'à 200 000). Ligne 2 : n entiers. Affichez la longueur de la plus longue sous-suite STRICTEMENT croissante "
       "(éléments pris dans l'ordre, pas forcément consécutifs).",
       [("8\n10 9 2 5 3 7 101 18", "4"), ("5\n5 4 3 2 1", "1"), ("6\n1 1 1 1 1 1", "1"), ("1\n42", "1"),
        lambda: "200000\n" + " ".join(map(str, _rand(200000, -10 ** 9, 10 ** 9, 17))), lambda: "200000\n" + " ".join(map(str, range(200000)))],
       ["La DP classique en n² (L[i] = 1 + max L[j] pour j < i avec a[j] < a[i]) est trop lente pour 200 000 éléments.",
        "Tenez un tableau « fins » : fins[k] = plus petite valeur qui termine une suite croissante de longueur k + 1. Il reste toujours trié.",
        "Pour chaque x : cherchez par dichotomie la première case ≥ x et remplacez-la par x (ou ajoutez x à la fin). La réponse est la taille de « fins »."],
       {"python": r"""
import sys
from bisect import bisect_left
L = sys.stdin.read().split("\n")
fins = []
for x in map(int, L[1].split()):
    i = bisect_left(fins, x)
    if i == len(fins):
        fins.append(x)
    else:
        fins[i] = x
print(len(fins))""", "c": r"""
#include <stdio.h>
static long long fins[200005];
int main(void) {
    int n, k = 0;
    if (scanf("%d", &n) != 1) return 1;
    for (int i = 0; i < n; ++i) {
        long long x;
        if (scanf("%lld", &x) != 1) return 1;
        int lo = 0, hi = k;
        while (lo < hi) { int m = (lo + hi) / 2; if (fins[m] < x) lo = m + 1; else hi = m; }
        fins[lo] = x;
        if (lo == k) ++k;
    }
    printf("%d\n", k);
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
    std::vector<long long> fins;
    for (int i = 0; i < n; ++i) {
        long long x;
        std::cin >> x;
        auto it = std::lower_bound(fins.begin(), fins.end(), x);
        if (it == fins.end()) fins.push_back(x); else *it = x;
    }
    std::cout << fins.size() << "\n";
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const fins = [];
for (const s of L[1].trim().split(" ")) {
  const x = Number(s);
  let lo = 0, hi = fins.length;
  while (lo < hi) { const m = (lo + hi) >> 1; if (fins[m] < x) lo = m + 1; else hi = m; }
  fins[lo] = x;
}
console.log(fins.length);""", "php": r"""
<?php
fgets(STDIN);
$fins = [];
$k = 0;
foreach (explode(' ', trim(fgets(STDIN))) as $s) {
    $x = (int) $s;
    $lo = 0; $hi = $k;
    while ($lo < $hi) { $m = ($lo + $hi) >> 1; if ($fins[$m] < $x) $lo = $m + 1; else $hi = $m; }
    $fins[$lo] = $x;
    if ($lo === $k) $k++;
}
echo $k, "\n";"""}, time=3),

    ch("reines", 9, "mini", "Les n reines", "retour sur trace",
       "Lisez n (1 à 11). De combien de façons peut-on placer n reines sur un échiquier n × n sans qu'aucune ne puisse en prendre une autre "
       "(ni sur la même ligne, ni la même colonne, ni la même diagonale) ?",
       [("4", "2"), ("1", "1"), ("2", "0"), ("3", "0"), ("6", "4"), ("8", "92"), ("10", "724"), ("11", "2680")],
       ["Placez les reines ligne par ligne : une seule reine par ligne, forcément.",
        "Retour sur trace : pour la ligne i, essayez chaque colonne libre ; si c'est sûr, placez la reine, passez à la ligne i + 1, puis retirez-la.",
        "Pour tester en O(1) : trois tableaux de booléens, les colonnes, les diagonales (ligne + colonne) et les anti-diagonales (ligne - colonne + n)."],
       {"python": r"""
n = int(input())
col, d1, d2 = [False] * n, [False] * (2 * n), [False] * (2 * n)

def place(i):
    if i == n:
        return 1
    total = 0
    for c in range(n):
        if not col[c] and not d1[i + c] and not d2[i - c + n]:
            col[c] = d1[i + c] = d2[i - c + n] = True
            total += place(i + 1)
            col[c] = d1[i + c] = d2[i - c + n] = False
    return total

print(place(0))""", "c": r"""
#include <stdio.h>
static int n, col[32], d1[64], d2[64];
static long long place(int i) {
    if (i == n) return 1;
    long long t = 0;
    for (int c = 0; c < n; ++c)
        if (!col[c] && !d1[i + c] && !d2[i - c + n]) {
            col[c] = d1[i + c] = d2[i - c + n] = 1;
            t += place(i + 1);
            col[c] = d1[i + c] = d2[i - c + n] = 0;
        }
    return t;
}
int main(void) {
    if (scanf("%d", &n) != 1) return 1;
    printf("%lld\n", place(0));
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <vector>
int n;
std::vector<bool> col, d1, d2;
long long place(int i) {
    if (i == n) return 1;
    long long t = 0;
    for (int c = 0; c < n; ++c)
        if (!col[c] && !d1[i + c] && !d2[i - c + n]) {
            col[c] = d1[i + c] = d2[i - c + n] = true;
            t += place(i + 1);
            col[c] = d1[i + c] = d2[i - c + n] = false;
        }
    return t;
}
int main() {
    std::cin >> n;
    col.assign(n, false); d1.assign(2 * n, false); d2.assign(2 * n, false);
    std::cout << place(0) << "\n";
}""", "javascript": r"""
const n = Number(require("fs").readFileSync(0, "utf8").trim());
const col = new Uint8Array(n), d1 = new Uint8Array(2 * n), d2 = new Uint8Array(2 * n);
const place = i => {
  if (i === n) return 1;
  let t = 0;
  for (let c = 0; c < n; c++)
    if (!col[c] && !d1[i + c] && !d2[i - c + n]) {
      col[c] = d1[i + c] = d2[i - c + n] = 1;
      t += place(i + 1);
      col[c] = d1[i + c] = d2[i - c + n] = 0;
    }
  return t;
};
console.log(place(0));""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
$col = array_fill(0, $n, false);
$d1 = array_fill(0, 2 * $n, false);
$d2 = array_fill(0, 2 * $n, false);
function place(int $i, int $n, array &$col, array &$d1, array &$d2): int {
    if ($i === $n) return 1;
    $t = 0;
    for ($c = 0; $c < $n; $c++)
        if (!$col[$c] && !$d1[$i + $c] && !$d2[$i - $c + $n]) {
            $col[$c] = $d1[$i + $c] = $d2[$i - $c + $n] = true;
            $t += place($i + 1, $n, $col, $d1, $d2);
            $col[$c] = $d1[$i + $c] = $d2[$i - $c + $n] = false;
        }
    return $t;
}
echo place(0, $n, $col, $d1, $d2), "\n";"""}, time=3),

    ch("sudoku", 9, "mini", "Le solveur de sudoku", "retour sur trace",
       "Lisez une grille de sudoku : 9 lignes de 9 caractères (chiffres, « . » pour une case vide). Elle a une solution unique : affichez la grille "
       "complétée, au même format. Chaque ligne, colonne et carré 3 × 3 doit contenir les chiffres de 1 à 9 exactement une fois.",
       [_sudoku(p) for p in _SUDOKUS],
       ["Retour sur trace : trouvez une case vide, essayez chaque chiffre possible, continuez récursivement, et revenez en arrière en cas d'impasse.",
        "Tenez trois tableaux « déjà utilisé » (lignes, colonnes, carrés) pour tester un chiffre en O(1). Carré de la case (l, c) : (l / 3) × 3 + c / 3.",
        "Astuce qui accélère énormément : remplissez d'abord la case vide qui a le MOINS de chiffres possibles."],
       {"python": r"""
g = [list(input().strip()) for _ in range(9)]
lig = [set() for _ in range(9)]
col = [set() for _ in range(9)]
car = [set() for _ in range(9)]
vides = []
for i in range(9):
    for j in range(9):
        if g[i][j] == ".":
            vides.append((i, j))
        else:
            lig[i].add(g[i][j])
            col[j].add(g[i][j])
            car[i // 3 * 3 + j // 3].add(g[i][j])

def resout():
    if not vides:
        return True
    # la case la plus contrainte d'abord
    k = max(range(len(vides)), key=lambda k: len(lig[vides[k][0]] | col[vides[k][1]] | car[vides[k][0] // 3 * 3 + vides[k][1] // 3]))
    i, j = vides.pop(k)
    b = i // 3 * 3 + j // 3
    for d in "123456789":
        if d not in lig[i] and d not in col[j] and d not in car[b]:
            g[i][j] = d
            lig[i].add(d); col[j].add(d); car[b].add(d)
            if resout():
                return True
            lig[i].discard(d); col[j].discard(d); car[b].discard(d)
    g[i][j] = "."
    vides.insert(k, (i, j))
    return False

resout()
print("\n".join("".join(r) for r in g))""", "c": r"""
#include <stdio.h>
static char g[9][12];
static int lig[9][10], col[9][10], car[9][10];
static int resout(void) {
    int bi = -1, bj = -1, bn = 10;
    for (int i = 0; i < 9; ++i)
        for (int j = 0; j < 9; ++j) {
            if (g[i][j] != '.') continue;
            int n = 0, b = i / 3 * 3 + j / 3;
            for (int d = 1; d <= 9; ++d) n += !lig[i][d] && !col[j][d] && !car[b][d];
            if (n < bn) { bn = n; bi = i; bj = j; }
        }
    if (bi < 0) return 1;
    int b = bi / 3 * 3 + bj / 3;
    for (int d = 1; d <= 9; ++d) {
        if (lig[bi][d] || col[bj][d] || car[b][d]) continue;
        g[bi][bj] = (char)('0' + d);
        lig[bi][d] = col[bj][d] = car[b][d] = 1;
        if (resout()) return 1;
        lig[bi][d] = col[bj][d] = car[b][d] = 0;
    }
    g[bi][bj] = '.';
    return 0;
}
int main(void) {
    for (int i = 0; i < 9; ++i) {
        if (scanf("%11s", g[i]) != 1) return 1;
        for (int j = 0; j < 9; ++j)
            if (g[i][j] != '.') { int d = g[i][j] - '0'; lig[i][d] = col[j][d] = car[i / 3 * 3 + j / 3][d] = 1; }
    }
    resout();
    for (int i = 0; i < 9; ++i) puts(g[i]);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
#include <array>
std::array<std::string, 9> g;
bool lig[9][10], col[9][10], car[9][10];
bool resout() {
    int bi = -1, bj = -1, bn = 10;
    for (int i = 0; i < 9; ++i)
        for (int j = 0; j < 9; ++j) {
            if (g[i][j] != '.') continue;
            int n = 0, b = i / 3 * 3 + j / 3;
            for (int d = 1; d <= 9; ++d) n += !lig[i][d] && !col[j][d] && !car[b][d];
            if (n < bn) { bn = n; bi = i; bj = j; }
        }
    if (bi < 0) return true;
    int b = bi / 3 * 3 + bj / 3;
    for (int d = 1; d <= 9; ++d) {
        if (lig[bi][d] || col[bj][d] || car[b][d]) continue;
        g[bi][bj] = char('0' + d);
        lig[bi][d] = col[bj][d] = car[b][d] = true;
        if (resout()) return true;
        lig[bi][d] = col[bj][d] = car[b][d] = false;
    }
    g[bi][bj] = '.';
    return false;
}
int main() {
    for (int i = 0; i < 9; ++i) {
        std::cin >> g[i];
        for (int j = 0; j < 9; ++j)
            if (g[i][j] != '.') { int d = g[i][j] - '0'; lig[i][d] = col[j][d] = car[i / 3 * 3 + j / 3][d] = true; }
    }
    resout();
    for (auto& r : g) std::cout << r << "\n";
}""", "javascript": r"""
const g = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).slice(0, 9).map(l => [...l]);
const lig = Array.from({ length: 9 }, () => new Uint8Array(10));
const col = Array.from({ length: 9 }, () => new Uint8Array(10));
const car = Array.from({ length: 9 }, () => new Uint8Array(10));
for (let i = 0; i < 9; i++)
  for (let j = 0; j < 9; j++)
    if (g[i][j] !== ".") { const d = Number(g[i][j]); lig[i][d] = col[j][d] = car[Math.floor(i / 3) * 3 + Math.floor(j / 3)][d] = 1; }
const resout = () => {
  let bi = -1, bj = -1, bn = 10;
  for (let i = 0; i < 9; i++)
    for (let j = 0; j < 9; j++) {
      if (g[i][j] !== ".") continue;
      const b = Math.floor(i / 3) * 3 + Math.floor(j / 3);
      let n = 0;
      for (let d = 1; d <= 9; d++) n += !lig[i][d] && !col[j][d] && !car[b][d] ? 1 : 0;
      if (n < bn) { bn = n; bi = i; bj = j; }
    }
  if (bi < 0) return true;
  const b = Math.floor(bi / 3) * 3 + Math.floor(bj / 3);
  for (let d = 1; d <= 9; d++) {
    if (lig[bi][d] || col[bj][d] || car[b][d]) continue;
    g[bi][bj] = String(d);
    lig[bi][d] = col[bj][d] = car[b][d] = 1;
    if (resout()) return true;
    lig[bi][d] = col[bj][d] = car[b][d] = 0;
  }
  g[bi][bj] = ".";
  return false;
};
resout();
console.log(g.map(r => r.join("")).join("\n"));""", "php": r"""
<?php
$g = [];
$lig = $col = $car = array_fill(0, 9, array_fill(0, 10, false));
for ($i = 0; $i < 9; $i++) {
    $g[] = trim(fgets(STDIN));
    for ($j = 0; $j < 9; $j++)
        if ($g[$i][$j] !== '.') { $d = (int) $g[$i][$j]; $lig[$i][$d] = $col[$j][$d] = $car[intdiv($i, 3) * 3 + intdiv($j, 3)][$d] = true; }
}
function resout(array &$g, array &$lig, array &$col, array &$car): bool {
    $bi = -1; $bj = -1; $bn = 10;
    for ($i = 0; $i < 9; $i++)
        for ($j = 0; $j < 9; $j++) {
            if ($g[$i][$j] !== '.') continue;
            $b = intdiv($i, 3) * 3 + intdiv($j, 3);
            $n = 0;
            for ($d = 1; $d <= 9; $d++) if (!$lig[$i][$d] && !$col[$j][$d] && !$car[$b][$d]) $n++;
            if ($n < $bn) { $bn = $n; $bi = $i; $bj = $j; }
        }
    if ($bi < 0) return true;
    $b = intdiv($bi, 3) * 3 + intdiv($bj, 3);
    for ($d = 1; $d <= 9; $d++) {
        if ($lig[$bi][$d] || $col[$bj][$d] || $car[$b][$d]) continue;
        $g[$bi][$bj] = (string) $d;
        $lig[$bi][$d] = $col[$bj][$d] = $car[$b][$d] = true;
        if (resout($g, $lig, $col, $car)) return true;
        $lig[$bi][$d] = $col[$bj][$d] = $car[$b][$d] = false;
    }
    $g[$bi][$bj] = '.';
    return false;
}
resout($g, $lig, $col, $car);
echo implode("\n", $g), "\n";"""}, time=3),

    ch("chemins", 9, "mini", "Les chemins dans la grille", "programmation dynamique",
       "Ligne 1 : h et w (jusqu'à 500). Puis une grille de h lignes de w caractères (« # » bloqué, « . » libre). En partant du coin en haut à "
       "gauche et en n'allant que vers la droite ou vers le bas, combien de chemins mènent au coin en bas à droite ? Affichez-le modulo 1 000 000 007.",
       [("3 3\n...\n.#.\n...", "2"), ("2 2\n.#\n#.", "0"), ("1 1\n.", "1"), ("3 4\n....\n....\n....", "10"), lambda: _grille(500, 500, 5, 8), lambda: _grille(400, 500, 7, 25)],
       ["Le nombre de chemins jusqu'à une case = celui jusqu'à la case du dessus + celui jusqu'à la case de gauche.",
        "Case bloquée : 0 chemin. Case de départ : 1 chemin (si elle est libre).",
        "Remplissez le tableau ligne par ligne, de gauche à droite, en prenant le modulo à chaque addition."],
       {"python": r"""
import sys
M = 1_000_000_007
L = sys.stdin.read().split("\n")
h, w = map(int, L[0].split())
prec = [0] * w
for i in range(h):
    l = L[1 + i]
    cur = [0] * w
    for j in range(w):
        if l[j] == "#":
            continue
        if i == 0 and j == 0:
            cur[j] = 1
        else:
            cur[j] = (prec[j] + (cur[j - 1] if j else 0)) % M
    prec = cur
print(prec[w - 1])""", "c": r"""
#include <stdio.h>
static char g[505][505];
static long long p[505][505];
int main(void) {
    const long long M = 1000000007LL;
    int h, w;
    if (scanf("%d %d", &h, &w) != 2) return 1;
    for (int i = 0; i < h; ++i) if (scanf("%504s", g[i]) != 1) return 1;
    for (int i = 0; i < h; ++i)
        for (int j = 0; j < w; ++j) {
            if (g[i][j] == '#') { p[i][j] = 0; continue; }
            if (i == 0 && j == 0) { p[i][j] = 1; continue; }
            p[i][j] = ((i ? p[i - 1][j] : 0) + (j ? p[i][j - 1] : 0)) % M;
        }
    printf("%lld\n", p[h - 1][w - 1]);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
#include <vector>
int main() {
    const long long M = 1000000007LL;
    int h, w;
    std::cin >> h >> w;
    std::vector<std::string> g(h);
    for (auto& r : g) std::cin >> r;
    std::vector<std::vector<long long>> p(h, std::vector<long long>(w, 0));
    for (int i = 0; i < h; ++i)
        for (int j = 0; j < w; ++j) {
            if (g[i][j] == '#') continue;
            if (i == 0 && j == 0) { p[i][j] = 1; continue; }
            p[i][j] = ((i ? p[i - 1][j] : 0) + (j ? p[i][j - 1] : 0)) % M;
        }
    std::cout << p[h - 1][w - 1] << "\n";
}""", "javascript": r"""
const M = 1000000007;
const L = require("fs").readFileSync(0, "utf8").split("\n");
const [h, w] = L[0].trim().split(/\s+/).map(Number);
let prec = new Float64Array(w);
for (let i = 0; i < h; i++) {
  const l = L[1 + i], cur = new Float64Array(w);
  for (let j = 0; j < w; j++) {
    if (l[j] === "#") continue;
    cur[j] = i === 0 && j === 0 ? 1 : (prec[j] + (j ? cur[j - 1] : 0)) % M;
  }
  prec = cur;
}
console.log(prec[w - 1]);""", "php": r"""
<?php
$M = 1000000007;
[$h, $w] = array_map('intval', explode(' ', trim(fgets(STDIN))));
$prec = array_fill(0, $w, 0);
for ($i = 0; $i < $h; $i++) {
    $l = trim(fgets(STDIN));
    $cur = array_fill(0, $w, 0);
    for ($j = 0; $j < $w; $j++) {
        if ($l[$j] === '#') continue;
        $cur[$j] = ($i === 0 && $j === 0) ? 1 : ($prec[$j] + ($j ? $cur[$j - 1] : 0)) % $M;
    }
    $prec = $cur;
}
echo $prec[$w - 1], "\n";"""}, time=3),

    ch("decoupage", 9, "exam", "Examen : découper le texte", "programmation dynamique",
       "Ligne 1 : k. Ligne 2 : k mots de dictionnaire (minuscules, 20 lettres au plus). Ligne 3 : un texte sans espaces (jusqu'à 10 000 lettres). "
       "On veut découper le texte en mots du dictionnaire. Affichez « mots: m » (le nombre minimal de mots d'un découpage) puis "
       "« découpages: d » (le nombre de découpages différents, modulo 1 000 000 007), ou « impossible » s'il n'en existe aucun.",
       ["5\nforge code for ge co\nforgecode", "3\na b ab\nabba", "2\nchat chien\nchatchienchat", "2\nab cd\nabc", "3\na aa aaa\n" + "a" * 5000, _dico(3), _dico(9)],
       ["best[i] = nombre minimal de mots pour découper les i premières lettres ; nb[i] = nombre de découpages de ces i lettres.",
        "Pour chaque position i, essayez chaque longueur L (1 à 20) : si texte[i-L:i] est un mot du dictionnaire (ensemble), best[i] = min(best[i], best[i-L] + 1) et nb[i] += nb[i-L].",
        "best[0] = 0 et nb[0] = 1. Si best[n] est infini, c'est impossible. Pensez au modulo pour nb."],
       {"python": r"""
import sys
M = 1_000_000_007
L = sys.stdin.read().split("\n")
dico = set(L[1].split())
t = L[2].strip()
n = len(t)
INF = float("inf")
best, nb = [0] + [INF] * n, [1] + [0] * n
for i in range(1, n + 1):
    for l in range(1, min(20, i) + 1):
        j = i - l
        if best[j] != INF and t[j:i] in dico:
            best[i] = min(best[i], best[j] + 1)
            nb[i] = (nb[i] + nb[j]) % M
if best[n] == INF:
    print("impossible")
else:
    print(f"mots: {best[n]}")
    print(f"découpages: {nb[n]}")""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static char mots[5000][24], texte[10010];
static int nm;
static int best[10010];
static long long nb[10010];
static int cmp(const void *a, const void *b) { return strcmp((const char *)a, (const char *)b); }
static int existe(const char *s, int l) {
    char k[24];
    memcpy(k, s, l);
    k[l] = '\0';
    return bsearch(k, mots, nm, sizeof mots[0], cmp) != NULL;
}
int main(void) {
    const long long M = 1000000007LL;
    if (scanf("%d", &nm) != 1) return 1;
    for (int i = 0; i < nm; ++i) if (scanf("%23s", mots[i]) != 1) return 1;
    if (scanf("%10009s", texte) != 1) return 1;
    qsort(mots, nm, sizeof mots[0], cmp);
    int n = (int)strlen(texte);
    best[0] = 0; nb[0] = 1;
    for (int i = 1; i <= n; ++i) {
        best[i] = -1; nb[i] = 0;
        for (int l = 1; l <= 20 && l <= i; ++l) {
            int j = i - l;
            if (best[j] < 0 || !existe(texte + j, l)) continue;
            if (best[i] < 0 || best[j] + 1 < best[i]) best[i] = best[j] + 1;
            nb[i] = (nb[i] + nb[j]) % M;
        }
    }
    if (best[n] < 0) puts("impossible");
    else printf("mots: %d\ndécoupages: %lld\n", best[n], nb[n]);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
#include <unordered_set>
#include <vector>
int main() {
    const long long M = 1000000007LL;
    int k;
    std::cin >> k;
    std::unordered_set<std::string> dico;
    for (int i = 0; i < k; ++i) { std::string w; std::cin >> w; dico.insert(w); }
    std::string t;
    std::cin >> t;
    int n = (int)t.size();
    std::vector<int> best(n + 1, -1);
    std::vector<long long> nb(n + 1, 0);
    best[0] = 0; nb[0] = 1;
    for (int i = 1; i <= n; ++i)
        for (int l = 1; l <= 20 && l <= i; ++l) {
            int j = i - l;
            if (best[j] < 0 || !dico.count(t.substr(j, l))) continue;
            if (best[i] < 0 || best[j] + 1 < best[i]) best[i] = best[j] + 1;
            nb[i] = (nb[i] + nb[j]) % M;
        }
    if (best[n] < 0) std::cout << "impossible\n";
    else std::cout << "mots: " << best[n] << "\ndécoupages: " << nb[n] << "\n";
}""", "javascript": r"""
const M = 1000000007;
const L = require("fs").readFileSync(0, "utf8").split("\n");
const dico = new Set(L[1].trim().split(/\s+/)), t = L[2].trim(), n = t.length;
const best = new Int32Array(n + 1).fill(-1), nb = new Float64Array(n + 1);
best[0] = 0; nb[0] = 1;
for (let i = 1; i <= n; i++)
  for (let l = 1; l <= 20 && l <= i; l++) {
    const j = i - l;
    if (best[j] < 0 || !dico.has(t.slice(j, i))) continue;
    if (best[i] < 0 || best[j] + 1 < best[i]) best[i] = best[j] + 1;
    nb[i] = (nb[i] + nb[j]) % M;
  }
console.log(best[n] < 0 ? "impossible" : `mots: ${best[n]}\ndécoupages: ${nb[n]}`);""", "php": r"""
<?php
$M = 1000000007;
fgets(STDIN);
$dico = array_flip(preg_split('/\s+/', trim(fgets(STDIN))));
$t = trim(fgets(STDIN));
$n = strlen($t);
$best = array_fill(0, $n + 1, -1);
$nb = array_fill(0, $n + 1, 0);
$best[0] = 0; $nb[0] = 1;
for ($i = 1; $i <= $n; $i++)
    for ($l = 1; $l <= 20 && $l <= $i; $l++) {
        $j = $i - $l;
        if ($best[$j] < 0 || !isset($dico[substr($t, $j, $l)])) continue;
        if ($best[$i] < 0 || $best[$j] + 1 < $best[$i]) $best[$i] = $best[$j] + 1;
        $nb[$i] = ($nb[$i] + $nb[$j]) % $M;
    }
echo $best[$n] < 0 ? "impossible\n" : "mots: {$best[$n]}\ndécoupages: {$nb[$n]}\n";"""}, minutes=50, time=3),
]
