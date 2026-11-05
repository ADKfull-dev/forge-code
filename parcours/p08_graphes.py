# -*- coding: utf-8 -*-
"""Palier 8 — Graphes et réseaux : parcours, plus courts chemins, dépendances, arbres couvrants."""
from .base import ch, lines


def _rand(n, lo, hi, seed=1):
    x, out = seed, []
    for _ in range(n):
        x = (x * 6364136223846793005 + 1442695040888963407) % 2 ** 64
        out.append(lo + (x >> 33) % (hi - lo + 1))
    return out


_MAZE = "\n".join(["S" + "." * 199] + ["." * 200] * 198 + ["." * 199 + "E"])
_ZIG = "\n".join(["S.#....", "#.#.##.", "#...#..", "####.#.", "E.....#"])


def _serpent(h, w):
    """Labyrinthe en serpent : un seul long couloir."""
    g = [["." for _ in range(w)] for _ in range(h)]
    for i in range(1, h, 2):
        for j in range(w):
            g[i][j] = "#"
        g[i][w - 1 if i % 4 == 1 else 0] = "."
    g[0][0], g[h - 1][w - 1 if (h - 1) % 4 == 0 else 0] = "S", "E"
    return f"{h} {w}\n" + lines("".join(r) for r in g)


def _graphe(n, m, seed, poids=None):
    a, b = _rand(m, 1, n, seed), _rand(m, 1, n, seed + 1)
    if poids:
        w = _rand(m, poids[0], poids[1], seed + 2)
        return lines(f"{x} {y} {z}" for x, y, z in zip(a, b, w))
    return lines(f"{x} {y}" for x, y in zip(a, b))


def _arbre(n, seed):
    p = _rand(n - 1, 0, 10 ** 9, seed)
    return lines(f"{i + 2} {p[i] % (i + 1) + 1 if i % 50 else i + 1}" for i in range(n - 1))


def _dag(n, m, seed):
    a, b = _rand(m, 1, n, seed), _rand(m, 1, n, seed + 1)
    return lines(f"{min(x, y)} {max(x, y)}" if x != y else f"{x} {x % n + 1}" if x < n else f"1 {n}" for x, y in zip(a, b))


def _iles(h, w, seed, p):
    r = _rand(h * w, 0, 99, seed)
    return f"{h} {w}\n" + lines("".join("#" if r[i * w + j] < p else "." for j in range(w)) for i in range(h))


def _metro():
    r = _rand(4000, 0, 10 ** 9, 77)
    st = [f"S{i}" for i in range(300)]
    out, k = [], 0
    for li in range(25):
        n = 8 + r[k] % 20
        k += 1
        seq = [st[r[k + j] % 300] for j in range(n)]
        k += n
        toks = [f"L{li}", seq[0]]
        for s in seq[1:]:
            toks += [str(1 + r[k] % 9), s]
            k += 1
        out.append(" ".join(toks))
    q = [f"{st[r[k + 2 * i] % 300]} {st[r[k + 2 * i + 1] % 300]}" for i in range(150)]
    return f"25 4\n" + lines(out) + f"\n{len(q)}\n" + lines(q)


DEFIS = [
    ch("labyrinthe", 8, "mini", "Labyrinthe", "parcours en largeur",
       "Ligne 1 : h et w. Puis h lignes de w caractères : S départ, E sortie, # mur, . libre. "
       "En se déplaçant d'une case vers le haut, le bas, la gauche ou la droite, affichez le nombre minimal de pas de S à E, ou -1 si c'est impossible.",
       [("3 4\nS..#\n.#..\n...E", "5"), ("3 3\nS#E\n.#.\n.#.", "-1"), ("1 2\nSE", "1"), ("5 7\n" + _ZIG, "-1"),
        ("5 7\n" + _ZIG.replace("####.#.", "####...").replace("E.....#", "E......"), "20"), ("200 200\n" + _MAZE, "398"), lambda: _serpent(201, 199)],
       ["Parcours en largeur (BFS) : on explore les cases par distance croissante.", "Une file : on y met S, puis chaque voisin libre non visité avec distance + 1.",
        "Un tableau de distances initialisé à -1 sert aussi à marquer les cases visitées. Pas de récursion : la pile exploserait sur un long couloir."],
       {"cpp": r"""
#include <iostream>
#include <vector>
#include <string>
#include <queue>
int main() {
    int h, w;
    std::cin >> h >> w;
    std::vector<std::string> g(h);
    for (auto& r : g) std::cin >> r;
    std::vector<std::vector<int>> d(h, std::vector<int>(w, -1));
    std::queue<std::pair<int, int>> q;
    for (int i = 0; i < h; ++i) for (int j = 0; j < w; ++j) if (g[i][j] == 'S') { d[i][j] = 0; q.push({i, j}); }
    int dy[] = {1, -1, 0, 0}, dx[] = {0, 0, 1, -1};
    while (!q.empty()) {
        auto [y, x] = q.front(); q.pop();
        if (g[y][x] == 'E') { std::cout << d[y][x] << std::endl; return 0; }
        for (int k = 0; k < 4; ++k) {
            int ny = y + dy[k], nx = x + dx[k];
            if (ny >= 0 && ny < h && nx >= 0 && nx < w && g[ny][nx] != '#' && d[ny][nx] < 0) { d[ny][nx] = d[y][x] + 1; q.push({ny, nx}); }
        }
    }
    std::cout << -1 << std::endl;
}""", "c": r"""
#include <stdio.h>
static char g[1005][1005];
static int d[1005][1005], qy[1000005], qx[1000005];
int main(void) {
    int h, w, deb = 0, fin = 0;
    if (scanf("%d %d", &h, &w) != 2) return 1;
    for (int i = 0; i < h; ++i) {
        if (scanf("%1004s", g[i]) != 1) return 1;
        for (int j = 0; j < w; ++j) { d[i][j] = -1; if (g[i][j] == 'S') { d[i][j] = 0; qy[fin] = i; qx[fin++] = j; } }
    }
    const int dy[] = {1, -1, 0, 0}, dx[] = {0, 0, 1, -1};
    while (deb < fin) {
        int y = qy[deb], x = qx[deb++];
        if (g[y][x] == 'E') { printf("%d\n", d[y][x]); return 0; }
        for (int k = 0; k < 4; ++k) {
            int ny = y + dy[k], nx = x + dx[k];
            if (ny >= 0 && ny < h && nx >= 0 && nx < w && g[ny][nx] != '#' && d[ny][nx] < 0) { d[ny][nx] = d[y][x] + 1; qy[fin] = ny; qx[fin++] = nx; }
        }
    }
    puts("-1");
    return 0;
}""", "python": r"""
from collections import deque
h, w = map(int, input().split())
g = [input() for _ in range(h)]
d = [[-1] * w for _ in range(h)]
q = deque()
for i in range(h):
    for j in range(w):
        if g[i][j] == "S":
            d[i][j] = 0
            q.append((i, j))
res = -1
while q:
    y, x = q.popleft()
    if g[y][x] == "E":
        res = d[y][x]
        break
    for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
        if 0 <= ny < h and 0 <= nx < w and g[ny][nx] != "#" and d[ny][nx] < 0:
            d[ny][nx] = d[y][x] + 1
            q.append((ny, nx))
print(res)""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const [h, w] = L[0].trim().split(/\s+/).map(Number);
const g = L.slice(1, h + 1).map(l => l.trim());
const d = new Int32Array(h * w).fill(-1), q = new Int32Array(h * w);
let deb = 0, fin = 0, res = -1;
for (let i = 0; i < h; i++) for (let j = 0; j < w; j++) if (g[i][j] === "S") { d[i * w + j] = 0; q[fin++] = i * w + j; }
while (deb < fin) {
  const c = q[deb++], y = Math.floor(c / w), x = c % w;
  if (g[y][x] === "E") { res = d[c]; break; }
  for (const [ny, nx] of [[y + 1, x], [y - 1, x], [y, x + 1], [y, x - 1]]) {
    if (ny >= 0 && ny < h && nx >= 0 && nx < w && g[ny][nx] !== "#" && d[ny * w + nx] < 0) { d[ny * w + nx] = d[c] + 1; q[fin++] = ny * w + nx; }
  }
}
console.log(res);""", "php": r"""
<?php
[$h, $w] = array_map('intval', explode(' ', trim(fgets(STDIN))));
$g = [];
for ($i = 0; $i < $h; $i++) $g[] = trim(fgets(STDIN));
$d = array_fill(0, $h * $w, -1);
$q = new SplQueue();
for ($i = 0; $i < $h; $i++) for ($j = 0; $j < $w; $j++) if ($g[$i][$j] === 'S') { $d[$i * $w + $j] = 0; $q->enqueue($i * $w + $j); }
$res = -1;
while (!$q->isEmpty()) {
    $c = $q->dequeue();
    $y = intdiv($c, $w); $x = $c % $w;
    if ($g[$y][$x] === 'E') { $res = $d[$c]; break; }
    foreach ([[$y + 1, $x], [$y - 1, $x], [$y, $x + 1], [$y, $x - 1]] as [$ny, $nx]) {
        if ($ny >= 0 && $ny < $h && $nx >= 0 && $nx < $w && $g[$ny][$nx] !== '#' && $d[$ny * $w + $nx] < 0) { $d[$ny * $w + $nx] = $d[$c] + 1; $q->enqueue($ny * $w + $nx); }
    }
}
echo $res, "\n";"""}),

    ch("composantes", 8, "mini", "Composantes connexes", "union-find",
       "Ligne 1 : n sommets (numérotés de 1 à n) et m arêtes (jusqu'à 200 000 chacun). Puis m lignes « u v » (arête non orientée). "
       "Affichez le nombre de composantes connexes (groupes de sommets reliés entre eux).",
       ["5 3\n1 2\n2 3\n4 5", "4 0", "3 3\n1 2\n2 3\n3 1", lambda: "200000 150000\n" + _graphe(200000, 150000, 3), lambda: "200000 199999\n" + lines(f"{i} {i + 1}" for i in range(1, 200000))],
       ["Idée 1 : parcours (BFS) depuis chaque sommet non visité ; chaque nouveau départ est une nouvelle composante. Attention à la récursion trop profonde.",
        "Idée 2, élégante : union-find. Chaque sommet a un « parent » ; « trouve » remonte jusqu'au représentant, « unit » relie deux représentants.",
        "Chaque union réussie (deux représentants différents) fait perdre une composante : réponse = n - unions réussies. Compression de chemin : O(presque 1)."],
       {"python": r"""
import sys
data = sys.stdin.buffer.read().split()
n, m = int(data[0]), int(data[1])
parent = list(range(n + 1))

def trouve(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x

comp = n
for i in range(m):
    a, b = trouve(int(data[2 + 2 * i])), trouve(int(data[3 + 2 * i]))
    if a != b:
        parent[a] = b
        comp -= 1
print(comp)""", "c": r"""
#include <stdio.h>
static int parent[200005];
static int trouve(int x) {
    while (parent[x] != x) { parent[x] = parent[parent[x]]; x = parent[x]; }
    return x;
}
int main(void) {
    int n, m;
    if (scanf("%d %d", &n, &m) != 2) return 1;
    for (int i = 0; i <= n; ++i) parent[i] = i;
    int comp = n;
    while (m-- > 0) {
        int u, v;
        if (scanf("%d %d", &u, &v) != 2) return 1;
        int a = trouve(u), b = trouve(v);
        if (a != b) { parent[a] = b; --comp; }
    }
    printf("%d\n", comp);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <numeric>
#include <vector>
struct UnionFind {
    std::vector<int> p;
    explicit UnionFind(int n) : p(n) { std::iota(p.begin(), p.end(), 0); }
    int trouve(int x) { while (p[x] != x) x = p[x] = p[p[x]]; return x; }
    bool unit(int a, int b) { a = trouve(a); b = trouve(b); if (a == b) return false; p[a] = b; return true; }
};
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n, m;
    std::cin >> n >> m;
    UnionFind uf(n + 1);
    int comp = n;
    for (int i = 0; i < m; ++i) { int u, v; std::cin >> u >> v; comp -= uf.unit(u, v); }
    std::cout << comp << "\n";
}""", "javascript": r"""
const d = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
const n = d[0], m = d[1], parent = new Int32Array(n + 1).map((_, i) => i);
const trouve = x => { while (parent[x] !== x) { parent[x] = parent[parent[x]]; x = parent[x]; } return x; };
let comp = n;
for (let i = 0; i < m; i++) {
  const a = trouve(d[2 + 2 * i]), b = trouve(d[3 + 2 * i]);
  if (a !== b) { parent[a] = b; comp--; }
}
console.log(comp);""", "php": r"""
<?php
[$n, $m] = array_map('intval', explode(' ', trim(fgets(STDIN))));
$parent = range(0, $n);
function trouve(array &$p, int $x): int {
    while ($p[$x] !== $x) { $p[$x] = $p[$p[$x]]; $x = $p[$x]; }
    return $x;
}
$comp = $n;
for ($i = 0; $i < $m; $i++) {
    [$u, $v] = explode(' ', trim(fgets(STDIN)));
    $a = trouve($parent, (int) $u);
    $b = trouve($parent, (int) $v);
    if ($a !== $b) { $parent[$a] = $b; $comp--; }
}
echo $comp, "\n";"""}),

    ch("dijkstra", 8, "mini", "Le plus court chemin", "Dijkstra",
       "Ligne 1 : n, m, s et t (jusqu'à 100 000 sommets et 200 000 arêtes). Puis m lignes « u v w » : une route à double sens de longueur w "
       "(0 ≤ w ≤ 10^9). Affichez la longueur du plus court chemin de s à t, ou -1 s'il n'y en a pas.",
       ["4 4 1 4\n1 2 1\n2 4 5\n1 3 2\n3 4 1", "3 1 1 3\n1 2 7", "2 1 2 2\n1 2 3", lambda: "100000 200000 1 100000\n" + _graphe(100000, 200000, 11, (0, 10 ** 9)),
        lambda: "100000 99999 1 100000\n" + lines(f"{i} {i + 1} 1000000000" for i in range(1, 100000))],
       ["Un parcours en largeur ne suffit plus : les arêtes n'ont pas toutes la même longueur.",
        "Dijkstra : on retire toujours le sommet non traité de plus petite distance (file de priorité), puis on « relâche » ses arêtes.",
        "Ignorez une entrée de la file si sa distance est plus grande que la distance connue (entrée périmée). Les distances atteignent 10^14 : 64 bits."],
       {"python": r"""
import heapq
import sys
data = sys.stdin.buffer.read().split()
n, m, s, t = map(int, data[:4])
adj = [[] for _ in range(n + 1)]
for i in range(m):
    u, v, w = int(data[4 + 3 * i]), int(data[5 + 3 * i]), int(data[6 + 3 * i])
    adj[u].append((v, w))
    adj[v].append((u, w))
INF = float("inf")
dist = [INF] * (n + 1)
dist[s] = 0
tas = [(0, s)]
while tas:
    d, u = heapq.heappop(tas)
    if d > dist[u]:
        continue
    if u == t:
        break
    for v, w in adj[u]:
        if d + w < dist[v]:
            dist[v] = d + w
            heapq.heappush(tas, (d + w, v))
print(dist[t] if dist[t] < INF else -1)""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
typedef struct { long long d; int u; } Elt;
static int tete[100005], suiv[400005], vers[400005];
static long long poids[400005], dist[100005];
static Elt tas[400005];
static int nt = 0;
static void pousse(long long d, int u) {
    int i = nt++;
    tas[i] = (Elt){d, u};
    while (i && tas[(i - 1) / 2].d > tas[i].d) { Elt x = tas[i]; tas[i] = tas[(i - 1) / 2]; tas[(i - 1) / 2] = x; i = (i - 1) / 2; }
}
static Elt retire(void) {
    Elt r = tas[0];
    tas[0] = tas[--nt];
    for (int i = 0;;) {
        int g = 2 * i + 1, d = g + 1, m = i;
        if (g < nt && tas[g].d < tas[m].d) m = g;
        if (d < nt && tas[d].d < tas[m].d) m = d;
        if (m == i) break;
        Elt x = tas[i]; tas[i] = tas[m]; tas[m] = x;
        i = m;
    }
    return r;
}
int main(void) {
    int n, m, s, t, k = 0;
    if (scanf("%d %d %d %d", &n, &m, &s, &t) != 4) return 1;
    for (int i = 0; i <= n; ++i) { tete[i] = -1; dist[i] = -1; }
    for (int i = 0; i < m; ++i) {
        int u, v;
        long long w;
        if (scanf("%d %d %lld", &u, &v, &w) != 3) return 1;
        vers[k] = v; poids[k] = w; suiv[k] = tete[u]; tete[u] = k++;
        vers[k] = u; poids[k] = w; suiv[k] = tete[v]; tete[v] = k++;
    }
    dist[s] = 0;
    pousse(0, s);
    while (nt) {
        Elt e = retire();
        if (e.d > dist[e.u]) continue;
        if (e.u == t) break;
        for (int a = tete[e.u]; a >= 0; a = suiv[a]) {
            long long nd = e.d + poids[a];
            if (dist[vers[a]] < 0 || nd < dist[vers[a]]) { dist[vers[a]] = nd; pousse(nd, vers[a]); }
        }
    }
    printf("%lld\n", dist[t]);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <queue>
#include <vector>
#include <functional>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n, m, s, t;
    std::cin >> n >> m >> s >> t;
    std::vector<std::vector<std::pair<int, long long>>> adj(n + 1);
    for (int i = 0; i < m; ++i) { int u, v; long long w; std::cin >> u >> v >> w; adj[u].push_back({v, w}); adj[v].push_back({u, w}); }
    const long long INF = 4e18;
    std::vector<long long> dist(n + 1, INF);
    std::priority_queue<std::pair<long long, int>, std::vector<std::pair<long long, int>>, std::greater<>> pq;
    dist[s] = 0;
    pq.push({0, s});
    while (!pq.empty()) {
        auto [d, u] = pq.top();
        pq.pop();
        if (d > dist[u]) continue;
        if (u == t) break;
        for (auto [v, w] : adj[u]) if (d + w < dist[v]) { dist[v] = d + w; pq.push({dist[v], v}); }
    }
    std::cout << (dist[t] == INF ? -1 : dist[t]) << "\n";
}""", "javascript": r"""
const d = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
const [n, m, s, t] = d;
const tete = new Int32Array(n + 1).fill(-1), suiv = new Int32Array(2 * m), vers = new Int32Array(2 * m), poids = new Float64Array(2 * m);
for (let i = 0, k = 0; i < m; i++) {
  const u = d[4 + 3 * i], v = d[5 + 3 * i], w = d[6 + 3 * i];
  vers[k] = v; poids[k] = w; suiv[k] = tete[u]; tete[u] = k++;
  vers[k] = u; poids[k] = w; suiv[k] = tete[v]; tete[v] = k++;
}
// tas binaire de paires (distance, sommet)
const hd = [], hu = [];
const pousse = (dd, u) => {
  let i = hd.length;
  hd.push(dd); hu.push(u);
  while (i > 0) {
    const p = (i - 1) >> 1;
    if (hd[p] <= hd[i]) break;
    [hd[p], hd[i]] = [hd[i], hd[p]]; [hu[p], hu[i]] = [hu[i], hu[p]];
    i = p;
  }
};
const retire = () => {
  const r = [hd[0], hu[0]], ld = hd.pop(), lu = hu.pop();
  if (hd.length) {
    hd[0] = ld; hu[0] = lu;
    for (let i = 0; ;) {
      const g = 2 * i + 1, dr = g + 1;
      let mm = i;
      if (g < hd.length && hd[g] < hd[mm]) mm = g;
      if (dr < hd.length && hd[dr] < hd[mm]) mm = dr;
      if (mm === i) break;
      [hd[mm], hd[i]] = [hd[i], hd[mm]]; [hu[mm], hu[i]] = [hu[i], hu[mm]];
      i = mm;
    }
  }
  return r;
};
const dist = new Float64Array(n + 1).fill(Infinity);
dist[s] = 0;
pousse(0, s);
while (hd.length) {
  const [dd, u] = retire();
  if (dd > dist[u]) continue;
  if (u === t) break;
  for (let a = tete[u]; a >= 0; a = suiv[a]) {
    const nd = dd + poids[a];
    if (nd < dist[vers[a]]) { dist[vers[a]] = nd; pousse(nd, vers[a]); }
  }
}
console.log(dist[t] === Infinity ? -1 : dist[t]);""", "php": r"""
<?php
$d = array_map('intval', preg_split('/\s+/', trim(stream_get_contents(STDIN))));
[$n, $m, $s, $t] = $d;
$adj = array_fill(0, $n + 1, []);
for ($i = 0; $i < $m; $i++) {
    [$u, $v, $w] = [$d[4 + 3 * $i], $d[5 + 3 * $i], $d[6 + 3 * $i]];
    $adj[$u][] = [$v, $w];
    $adj[$v][] = [$u, $w];
}
$dist = array_fill(0, $n + 1, -1);
$dist[$s] = 0;
$pq = new SplPriorityQueue();
$pq->setExtractFlags(SplPriorityQueue::EXTR_BOTH);
$pq->insert($s, 0);
while (!$pq->isEmpty()) {
    ['data' => $u, 'priority' => $p] = $pq->extract();
    $du = -$p;
    if ($du > $dist[$u]) continue;
    if ($u === $t) break;
    foreach ($adj[$u] as [$v, $w]) {
        if ($dist[$v] < 0 || $du + $w < $dist[$v]) { $dist[$v] = $du + $w; $pq->insert($v, -$dist[$v]); }
    }
}
echo $dist[$t], "\n";"""}, time=3),

    ch("dependances", 8, "mini", "L'ordre des tâches", "tri topologique",
       "Ligne 1 : n tâches (numérotées de 1 à n) et m contraintes (jusqu'à 100 000 chacun). Puis m lignes « a b » : a doit être faite avant b. "
       "Affichez un ordre de toutes les tâches qui respecte les contraintes ; s'il y en a plusieurs, le plus petit dans l'ordre lexicographique "
       "(à chaque étape, la tâche disponible de plus petit numéro). S'il y a un cycle, affichez « CYCLE ».",
       ["5 4\n1 3\n2 3\n3 5\n4 5", "3 3\n1 2\n2 3\n3 1", "4 0", "3 2\n3 1\n3 2", lambda: "100000 100000\n" + _dag(100000, 100000, 5), "6 6\n1 2\n2 3\n3 4\n4 5\n5 6\n6 2"],
       ["Algorithme de Kahn : comptez pour chaque tâche combien de tâches doivent la précéder (degré entrant).",
        "Les tâches de degré 0 sont disponibles. Prenez la plus petite (file de priorité), ajoutez-la à l'ordre, et diminuez le degré de ses successeurs.",
        "Si l'on n'a pas pu placer les n tâches, c'est qu'il reste un cycle."],
       {"python": r"""
import heapq
import sys
data = sys.stdin.buffer.read().split()
n, m = int(data[0]), int(data[1])
succ = [[] for _ in range(n + 1)]
deg = [0] * (n + 1)
for i in range(m):
    a, b = int(data[2 + 2 * i]), int(data[3 + 2 * i])
    succ[a].append(b)
    deg[b] += 1
dispo = [i for i in range(1, n + 1) if deg[i] == 0]
heapq.heapify(dispo)
ordre = []
while dispo:
    u = heapq.heappop(dispo)
    ordre.append(u)
    for v in succ[u]:
        deg[v] -= 1
        if deg[v] == 0:
            heapq.heappush(dispo, v)
print(" ".join(map(str, ordre)) if len(ordre) == n else "CYCLE")""", "c": r"""
#include <stdio.h>
static int tete[100005], suiv[100005], vers[100005], deg[100005], tas[100005], ordre[100005];
static int nt = 0;
static void pousse(int x) {
    int i = nt++;
    tas[i] = x;
    while (i && tas[(i - 1) / 2] > tas[i]) { int t = tas[i]; tas[i] = tas[(i - 1) / 2]; tas[(i - 1) / 2] = t; i = (i - 1) / 2; }
}
static int retire(void) {
    int r = tas[0];
    tas[0] = tas[--nt];
    for (int i = 0;;) {
        int g = 2 * i + 1, d = g + 1, m = i;
        if (g < nt && tas[g] < tas[m]) m = g;
        if (d < nt && tas[d] < tas[m]) m = d;
        if (m == i) break;
        int t = tas[i]; tas[i] = tas[m]; tas[m] = t;
        i = m;
    }
    return r;
}
int main(void) {
    int n, m, k = 0;
    if (scanf("%d %d", &n, &m) != 2) return 1;
    for (int i = 0; i <= n; ++i) tete[i] = -1;
    for (int i = 0; i < m; ++i) {
        int a, b;
        if (scanf("%d %d", &a, &b) != 2) return 1;
        vers[i] = b; suiv[i] = tete[a]; tete[a] = i;
        deg[b]++;
    }
    for (int i = 1; i <= n; ++i) if (!deg[i]) pousse(i);
    while (nt) {
        int u = retire();
        ordre[k++] = u;
        for (int a = tete[u]; a >= 0; a = suiv[a]) if (--deg[vers[a]] == 0) pousse(vers[a]);
    }
    if (k < n) { puts("CYCLE"); return 0; }
    for (int i = 0; i < n; ++i) printf(i ? " %d" : "%d", ordre[i]);
    printf("\n");
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <queue>
#include <vector>
#include <functional>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n, m;
    std::cin >> n >> m;
    std::vector<std::vector<int>> succ(n + 1);
    std::vector<int> deg(n + 1, 0), ordre;
    for (int i = 0; i < m; ++i) { int a, b; std::cin >> a >> b; succ[a].push_back(b); ++deg[b]; }
    std::priority_queue<int, std::vector<int>, std::greater<int>> dispo;
    for (int i = 1; i <= n; ++i) if (!deg[i]) dispo.push(i);
    while (!dispo.empty()) {
        int u = dispo.top();
        dispo.pop();
        ordre.push_back(u);
        for (int v : succ[u]) if (--deg[v] == 0) dispo.push(v);
    }
    if ((int)ordre.size() < n) { std::cout << "CYCLE\n"; return 0; }
    for (int i = 0; i < n; ++i) std::cout << (i ? " " : "") << ordre[i];
    std::cout << "\n";
}""", "javascript": r"""
const d = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
const n = d[0], m = d[1];
const succ = Array.from({ length: n + 1 }, () => []), deg = new Int32Array(n + 1);
for (let i = 0; i < m; i++) { succ[d[2 + 2 * i]].push(d[3 + 2 * i]); deg[d[3 + 2 * i]]++; }
const tas = [];
const pousse = x => {
  let i = tas.length;
  tas.push(x);
  while (i > 0 && tas[(i - 1) >> 1] > tas[i]) { const p = (i - 1) >> 1; [tas[p], tas[i]] = [tas[i], tas[p]]; i = p; }
};
const retire = () => {
  const r = tas[0], x = tas.pop();
  if (tas.length) {
    tas[0] = x;
    for (let i = 0; ;) {
      const g = 2 * i + 1, dr = g + 1;
      let mm = i;
      if (g < tas.length && tas[g] < tas[mm]) mm = g;
      if (dr < tas.length && tas[dr] < tas[mm]) mm = dr;
      if (mm === i) break;
      [tas[mm], tas[i]] = [tas[i], tas[mm]];
      i = mm;
    }
  }
  return r;
};
for (let i = 1; i <= n; i++) if (!deg[i]) pousse(i);
const ordre = [];
while (tas.length) {
  const u = retire();
  ordre.push(u);
  for (const v of succ[u]) if (--deg[v] === 0) pousse(v);
}
console.log(ordre.length < n ? "CYCLE" : ordre.join(" "));""", "php": r"""
<?php
$d = array_map('intval', preg_split('/\s+/', trim(stream_get_contents(STDIN))));
[$n, $m] = $d;
$succ = array_fill(0, $n + 1, []);
$deg = array_fill(0, $n + 1, 0);
for ($i = 0; $i < $m; $i++) { $succ[$d[2 + 2 * $i]][] = $d[3 + 2 * $i]; $deg[$d[3 + 2 * $i]]++; }
$dispo = new SplMinHeap();
for ($i = 1; $i <= $n; $i++) if ($deg[$i] === 0) $dispo->insert($i);
$ordre = [];
while (!$dispo->isEmpty()) {
    $u = $dispo->extract();
    $ordre[] = $u;
    foreach ($succ[$u] as $v) if (--$deg[$v] === 0) $dispo->insert($v);
}
echo count($ordre) < $n ? "CYCLE" : implode(' ', $ordre), "\n";"""}),

    ch("biparti", 8, "mini", "Deux équipes", "coloration",
       "Ligne 1 : n personnes et m inimitiés (jusqu'à 200 000). Puis m lignes « u v » : u et v refusent d'être dans la même équipe. "
       "Peut-on répartir tout le monde en deux équipes ? Affichez « oui » ou « non ». (Le graphe peut avoir plusieurs morceaux.)",
       ["4 4\n1 2\n2 3\n3 4\n4 1", "3 3\n1 2\n2 3\n3 1", "5 0", "6 4\n1 2\n3 4\n5 6\n2 3", lambda: "200000 199999\n" + lines(f"{i} {i + 1}" for i in range(1, 200000)),
        lambda: "200000 200000\n" + lines(f"{i} {i + 1}" for i in range(1, 200000)) + "\n1 199999"],
       ["Colorez les sommets avec deux couleurs : chaque arête doit relier deux couleurs différentes.",
        "BFS depuis chaque sommet non coloré : coloriez-le 0, ses voisins 1, leurs voisins 0…",
        "Si une arête relie deux sommets de même couleur, c'est impossible (il y a un cycle de longueur impaire)."],
       {"python": r"""
import sys
from collections import deque
data = sys.stdin.buffer.read().split()
n, m = int(data[0]), int(data[1])
adj = [[] for _ in range(n + 1)]
for i in range(m):
    u, v = int(data[2 + 2 * i]), int(data[3 + 2 * i])
    adj[u].append(v)
    adj[v].append(u)
coul = [-1] * (n + 1)
ok = True
for s in range(1, n + 1):
    if coul[s] >= 0 or not ok:
        continue
    coul[s] = 0
    q = deque([s])
    while q and ok:
        u = q.popleft()
        for v in adj[u]:
            if coul[v] < 0:
                coul[v] = 1 - coul[u]
                q.append(v)
            elif coul[v] == coul[u]:
                ok = False
                break
print("oui" if ok else "non")""", "c": r"""
#include <stdio.h>
static int tete[200005], suiv[400005], vers[400005], coul[200005], file[200005];
int main(void) {
    int n, m, k = 0;
    if (scanf("%d %d", &n, &m) != 2) return 1;
    for (int i = 0; i <= n; ++i) { tete[i] = -1; coul[i] = -1; }
    for (int i = 0; i < m; ++i) {
        int u, v;
        if (scanf("%d %d", &u, &v) != 2) return 1;
        vers[k] = v; suiv[k] = tete[u]; tete[u] = k++;
        vers[k] = u; suiv[k] = tete[v]; tete[v] = k++;
    }
    int ok = 1;
    for (int s = 1; s <= n && ok; ++s) {
        if (coul[s] >= 0) continue;
        int deb = 0, fin = 0;
        coul[s] = 0;
        file[fin++] = s;
        while (deb < fin && ok) {
            int u = file[deb++];
            for (int a = tete[u]; a >= 0; a = suiv[a]) {
                int v = vers[a];
                if (coul[v] < 0) { coul[v] = 1 - coul[u]; file[fin++] = v; }
                else if (coul[v] == coul[u]) { ok = 0; break; }
            }
        }
    }
    puts(ok ? "oui" : "non");
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <queue>
#include <vector>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n, m;
    std::cin >> n >> m;
    std::vector<std::vector<int>> adj(n + 1);
    for (int i = 0; i < m; ++i) { int u, v; std::cin >> u >> v; adj[u].push_back(v); adj[v].push_back(u); }
    std::vector<int> coul(n + 1, -1);
    bool ok = true;
    for (int s = 1; s <= n && ok; ++s) {
        if (coul[s] >= 0) continue;
        coul[s] = 0;
        std::queue<int> q;
        q.push(s);
        while (!q.empty() && ok) {
            int u = q.front();
            q.pop();
            for (int v : adj[u]) {
                if (coul[v] < 0) { coul[v] = 1 - coul[u]; q.push(v); }
                else if (coul[v] == coul[u]) { ok = false; break; }
            }
        }
    }
    std::cout << (ok ? "oui" : "non") << "\n";
}""", "javascript": r"""
const d = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
const n = d[0], m = d[1];
const adj = Array.from({ length: n + 1 }, () => []);
for (let i = 0; i < m; i++) { adj[d[2 + 2 * i]].push(d[3 + 2 * i]); adj[d[3 + 2 * i]].push(d[2 + 2 * i]); }
const coul = new Int8Array(n + 1).fill(-1), file = new Int32Array(n + 1);
let ok = true;
for (let s = 1; s <= n && ok; s++) {
  if (coul[s] >= 0) continue;
  let deb = 0, fin = 0;
  coul[s] = 0;
  file[fin++] = s;
  while (deb < fin && ok) {
    const u = file[deb++];
    for (const v of adj[u]) {
      if (coul[v] < 0) { coul[v] = 1 - coul[u]; file[fin++] = v; }
      else if (coul[v] === coul[u]) { ok = false; break; }
    }
  }
}
console.log(ok ? "oui" : "non");""", "php": r"""
<?php
$d = array_map('intval', preg_split('/\s+/', trim(stream_get_contents(STDIN))));
[$n, $m] = $d;
$adj = array_fill(0, $n + 1, []);
for ($i = 0; $i < $m; $i++) { $adj[$d[2 + 2 * $i]][] = $d[3 + 2 * $i]; $adj[$d[3 + 2 * $i]][] = $d[2 + 2 * $i]; }
$coul = array_fill(0, $n + 1, -1);
$ok = true;
for ($s = 1; $s <= $n && $ok; $s++) {
    if ($coul[$s] >= 0) continue;
    $coul[$s] = 0;
    $file = [$s];
    for ($k = 0; $k < count($file) && $ok; $k++) {
        $u = $file[$k];
        foreach ($adj[$u] as $v) {
            if ($coul[$v] < 0) { $coul[$v] = 1 - $coul[$u]; $file[] = $v; }
            elseif ($coul[$v] === $coul[$u]) { $ok = false; break; }
        }
    }
}
echo $ok ? "oui" : "non", "\n";"""}),

    ch("reseau", 8, "mini", "Le réseau le moins cher", "arbre couvrant",
       "Ligne 1 : n villes et m câbles possibles (jusqu'à 200 000). Puis m lignes « u v c » : relier u et v coûte c. Affichez le coût minimal "
       "pour que toutes les villes soient reliées (directement ou non), ou -1 si c'est impossible.",
       ["4 5\n1 2 1\n2 3 4\n3 4 2\n1 4 3\n1 3 5", "3 1\n1 2 5", "1 0", lambda: "100000 200000\n" + _graphe(100000, 200000, 21, (1, 10 ** 9)),
        "5 7\n1 2 10\n1 3 10\n2 3 1\n3 4 1\n4 5 1\n5 3 1\n2 4 0"],
       ["Algorithme de Kruskal : triez les câbles du moins cher au plus cher.",
        "Prenez chaque câble s'il relie deux groupes de villes encore séparés (union-find), sinon ignorez-le (il ferait un cycle).",
        "Si à la fin vous n'avez pas pris n - 1 câbles, les villes ne peuvent pas toutes être reliées. Le coût total dépasse 2^31."],
       {"python": r"""
import sys
data = sys.stdin.buffer.read().split()
n, m = int(data[0]), int(data[1])
aretes = sorted((int(data[4 + 3 * i]), int(data[2 + 3 * i]), int(data[3 + 3 * i])) for i in range(m))
parent = list(range(n + 1))

def trouve(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x

cout, pris = 0, 0
for c, u, v in aretes:
    a, b = trouve(u), trouve(v)
    if a != b:
        parent[a] = b
        cout += c
        pris += 1
print(cout if pris == n - 1 else -1)""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
typedef struct { int u, v; long long c; } Arete;
static Arete a[200005];
static int parent[200005];
static int cmp(const void *x, const void *y) { long long p = ((const Arete *)x)->c, q = ((const Arete *)y)->c; return (p > q) - (p < q); }
static int trouve(int x) { while (parent[x] != x) { parent[x] = parent[parent[x]]; x = parent[x]; } return x; }
int main(void) {
    int n, m;
    if (scanf("%d %d", &n, &m) != 2) return 1;
    for (int i = 0; i < m; ++i) if (scanf("%d %d %lld", &a[i].u, &a[i].v, &a[i].c) != 3) return 1;
    for (int i = 0; i <= n; ++i) parent[i] = i;
    qsort(a, m, sizeof *a, cmp);
    long long cout = 0;
    int pris = 0;
    for (int i = 0; i < m; ++i) {
        int x = trouve(a[i].u), y = trouve(a[i].v);
        if (x != y) { parent[x] = y; cout += a[i].c; ++pris; }
    }
    printf("%lld\n", pris == n - 1 ? cout : -1);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <tuple>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n, m;
    std::cin >> n >> m;
    std::vector<std::tuple<long long, int, int>> a(m);
    for (auto& [c, u, v] : a) std::cin >> u >> v >> c;
    std::sort(a.begin(), a.end());
    std::vector<int> p(n + 1);
    std::iota(p.begin(), p.end(), 0);
    auto trouve = [&](int x) { while (p[x] != x) x = p[x] = p[p[x]]; return x; };
    long long cout = 0;
    int pris = 0;
    for (auto& [c, u, v] : a) {
        int x = trouve(u), y = trouve(v);
        if (x != y) { p[x] = y; cout += c; ++pris; }
    }
    std::cout << (pris == n - 1 ? cout : -1) << "\n";
}""", "javascript": r"""
const d = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
const n = d[0], m = d[1];
const idx = Array.from({ length: m }, (_, i) => i).sort((x, y) => d[4 + 3 * x] - d[4 + 3 * y]);
const parent = new Int32Array(n + 1).map((_, i) => i);
const trouve = x => { while (parent[x] !== x) { parent[x] = parent[parent[x]]; x = parent[x]; } return x; };
let cout = 0, pris = 0;
for (const i of idx) {
  const a = trouve(d[2 + 3 * i]), b = trouve(d[3 + 3 * i]);
  if (a !== b) { parent[a] = b; cout += d[4 + 3 * i]; pris++; }
}
console.log(pris === n - 1 ? cout : -1);""", "php": r"""
<?php
$d = array_map('intval', preg_split('/\s+/', trim(stream_get_contents(STDIN))));
[$n, $m] = $d;
$a = [];
for ($i = 0; $i < $m; $i++) $a[] = [$d[4 + 3 * $i], $d[2 + 3 * $i], $d[3 + 3 * $i]];
usort($a, fn($x, $y) => $x[0] <=> $y[0]);
$parent = range(0, $n);
function trouve(array &$p, int $x): int { while ($p[$x] !== $x) { $p[$x] = $p[$p[$x]]; $x = $p[$x]; } return $x; }
$cout = 0; $pris = 0;
foreach ($a as [$c, $u, $v]) {
    $x = trouve($parent, $u);
    $y = trouve($parent, $v);
    if ($x !== $y) { $parent[$x] = $y; $cout += $c; $pris++; }
}
echo $pris === $n - 1 ? $cout : -1, "\n";"""}, time=3),

    ch("iles", 8, "mini", "L'archipel", "parcours",
       "Ligne 1 : h et w (jusqu'à 500). Puis une carte de h lignes de w caractères : « # » terre, « . » eau. Une île est un groupe de cases de terre "
       "reliées par les côtés (pas en diagonale). Affichez « îles: k » puis « plus grande: s » (nombre de cases de la plus grande île, 0 s'il n'y en a pas).",
       ["4 5\n##..#\n#...#\n..#..\n.....", "2 2\n..\n..", "3 3\n#.#\n.#.\n#.#", lambda: _iles(500, 500, 3, 55), lambda: _iles(300, 400, 9, 45)],
       ["Parcourez la carte ; chaque case de terre pas encore visitée est le début d'une nouvelle île.",
        "Depuis cette case, explorez toute l'île (BFS ou DFS avec une pile explicite) en marquant les cases visitées et en les comptant.",
        "Évitez la récursion : une île de 100 000 cases ferait déborder la pile d'appels."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
h, w = map(int, L[0].split())
g = [bytearray(l.strip(), "ascii") for l in L[1:h + 1]]
nb, best = 0, 0
for i in range(h):
    for j in range(w):
        if g[i][j] != 35:
            continue
        nb += 1
        g[i][j] = 46
        pile, taille = [(i, j)], 0
        while pile:
            y, x = pile.pop()
            taille += 1
            for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= ny < h and 0 <= nx < w and g[ny][nx] == 35:
                    g[ny][nx] = 46
                    pile.append((ny, nx))
        best = max(best, taille)
print(f"îles: {nb}")
print(f"plus grande: {best}")""", "c": r"""
#include <stdio.h>
static char g[505][505];
static int py[250005], px[250005];
int main(void) {
    int h, w, nb = 0, best = 0;
    const int dy[] = {1, -1, 0, 0}, dx[] = {0, 0, 1, -1};
    if (scanf("%d %d", &h, &w) != 2) return 1;
    for (int i = 0; i < h; ++i) if (scanf("%504s", g[i]) != 1) return 1;
    for (int i = 0; i < h; ++i)
        for (int j = 0; j < w; ++j) {
            if (g[i][j] != '#') continue;
            ++nb;
            int n = 0, taille = 0;
            g[i][j] = '.';
            py[n] = i; px[n++] = j;
            while (n) {
                int y = py[--n], x = px[n];
                ++taille;
                for (int k = 0; k < 4; ++k) {
                    int ny = y + dy[k], nx = x + dx[k];
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w && g[ny][nx] == '#') { g[ny][nx] = '.'; py[n] = ny; px[n++] = nx; }
                }
            }
            if (taille > best) best = taille;
        }
    printf("îles: %d\nplus grande: %d\n", nb, best);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
int main() {
    int h, w, nb = 0, best = 0;
    std::cin >> h >> w;
    std::vector<std::string> g(h);
    for (auto& r : g) std::cin >> r;
    const int dy[] = {1, -1, 0, 0}, dx[] = {0, 0, 1, -1};
    std::vector<std::pair<int, int>> pile;
    for (int i = 0; i < h; ++i)
        for (int j = 0; j < w; ++j) {
            if (g[i][j] != '#') continue;
            ++nb;
            int taille = 0;
            g[i][j] = '.';
            pile.push_back({i, j});
            while (!pile.empty()) {
                auto [y, x] = pile.back();
                pile.pop_back();
                ++taille;
                for (int k = 0; k < 4; ++k) {
                    int ny = y + dy[k], nx = x + dx[k];
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w && g[ny][nx] == '#') { g[ny][nx] = '.'; pile.push_back({ny, nx}); }
                }
            }
            best = std::max(best, taille);
        }
    std::cout << "îles: " << nb << "\nplus grande: " << best << "\n";
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const [h, w] = L[0].trim().split(/\s+/).map(Number);
const g = new Uint8Array(h * w);
for (let i = 0; i < h; i++) { const l = L[i + 1]; for (let j = 0; j < w; j++) g[i * w + j] = l[j] === "#" ? 1 : 0; }
const pile = new Int32Array(h * w);
let nb = 0, best = 0;
for (let c = 0; c < h * w; c++) {
  if (!g[c]) continue;
  nb++;
  let n = 0, taille = 0;
  g[c] = 0;
  pile[n++] = c;
  while (n) {
    const u = pile[--n], y = Math.floor(u / w), x = u % w;
    taille++;
    if (y + 1 < h && g[u + w]) { g[u + w] = 0; pile[n++] = u + w; }
    if (y > 0 && g[u - w]) { g[u - w] = 0; pile[n++] = u - w; }
    if (x + 1 < w && g[u + 1]) { g[u + 1] = 0; pile[n++] = u + 1; }
    if (x > 0 && g[u - 1]) { g[u - 1] = 0; pile[n++] = u - 1; }
  }
  if (taille > best) best = taille;
}
console.log(`îles: ${nb}\nplus grande: ${best}`);""", "php": r"""
<?php
[$h, $w] = array_map('intval', explode(' ', trim(fgets(STDIN))));
$g = '';
for ($i = 0; $i < $h; $i++) $g .= trim(fgets(STDIN));
$nb = 0; $best = 0;
for ($c = 0, $t = $h * $w; $c < $t; $c++) {
    if ($g[$c] !== '#') continue;
    $nb++;
    $g[$c] = '.';
    $pile = [$c];
    $taille = 0;
    while ($pile) {
        $u = array_pop($pile);
        $taille++;
        $x = $u % $w;
        if ($u + $w < $t && $g[$u + $w] === '#') { $g[$u + $w] = '.'; $pile[] = $u + $w; }
        if ($u - $w >= 0 && $g[$u - $w] === '#') { $g[$u - $w] = '.'; $pile[] = $u - $w; }
        if ($x + 1 < $w && $g[$u + 1] === '#') { $g[$u + 1] = '.'; $pile[] = $u + 1; }
        if ($x > 0 && $g[$u - 1] === '#') { $g[$u - 1] = '.'; $pile[] = $u - 1; }
    }
    if ($taille > $best) $best = $taille;
}
echo "îles: $nb\nplus grande: $best\n";"""}, time=3),

    ch("diametre", 8, "mini", "Le diamètre de l'arbre", "arbres",
       "Ligne 1 : n (jusqu'à 200 000). Puis n - 1 lignes « u v » : les arêtes d'un arbre (graphe connexe sans cycle) sur les sommets 1 à n. "
       "Affichez le diamètre : le plus grand nombre d'arêtes sur un chemin entre deux sommets.",
       ["5\n1 2\n1 3\n3 4\n3 5", "1", "2\n1 2", "7\n1 2\n2 3\n3 4\n2 5\n5 6\n6 7", lambda: "200000\n" + _arbre(200000, 7), lambda: "200000\n" + lines(f"{i} {i + 1}" for i in range(1, 200000))],
       ["Astuce célèbre : partez de n'importe quel sommet et trouvez le sommet A le plus éloigné (BFS).",
        "Puis, depuis A, trouvez le sommet le plus éloigné : cette distance est le diamètre.",
        "Deux BFS suffisent : O(n). Pas de récursion (un arbre « en ligne » a 200 000 niveaux)."],
       {"python": r"""
import sys
from collections import deque
data = sys.stdin.buffer.read().split()
n = int(data[0])
adj = [[] for _ in range(n + 1)]
for i in range(n - 1):
    u, v = int(data[1 + 2 * i]), int(data[2 + 2 * i])
    adj[u].append(v)
    adj[v].append(u)

def bfs(s):
    d = [-1] * (n + 1)
    d[s] = 0
    q = deque([s])
    loin = s
    while q:
        u = q.popleft()
        if d[u] > d[loin]:
            loin = u
        for v in adj[u]:
            if d[v] < 0:
                d[v] = d[u] + 1
                q.append(v)
    return loin, d[loin]

a, _ = bfs(1)
print(bfs(a)[1])""", "c": r"""
#include <stdio.h>
static int tete[200005], suiv[400005], vers[400005], d[200005], file[200005];
static int n;
static int bfs(int s, int *loin) {
    for (int i = 1; i <= n; ++i) d[i] = -1;
    int deb = 0, fin = 0;
    d[s] = 0;
    file[fin++] = s;
    *loin = s;
    while (deb < fin) {
        int u = file[deb++];
        if (d[u] > d[*loin]) *loin = u;
        for (int a = tete[u]; a >= 0; a = suiv[a]) if (d[vers[a]] < 0) { d[vers[a]] = d[u] + 1; file[fin++] = vers[a]; }
    }
    return d[*loin];
}
int main(void) {
    int k = 0, a;
    if (scanf("%d", &n) != 1) return 1;
    for (int i = 0; i <= n; ++i) tete[i] = -1;
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        if (scanf("%d %d", &u, &v) != 2) return 1;
        vers[k] = v; suiv[k] = tete[u]; tete[u] = k++;
        vers[k] = u; suiv[k] = tete[v]; tete[v] = k++;
    }
    bfs(1, &a);
    printf("%d\n", bfs(a, &a));
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <queue>
#include <vector>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n;
    std::cin >> n;
    std::vector<std::vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; ++i) { int u, v; std::cin >> u >> v; adj[u].push_back(v); adj[v].push_back(u); }
    auto bfs = [&](int s) {
        std::vector<int> d(n + 1, -1);
        std::queue<int> q;
        d[s] = 0;
        q.push(s);
        int loin = s;
        while (!q.empty()) {
            int u = q.front();
            q.pop();
            if (d[u] > d[loin]) loin = u;
            for (int v : adj[u]) if (d[v] < 0) { d[v] = d[u] + 1; q.push(v); }
        }
        return std::pair{loin, d[loin]};
    };
    std::cout << bfs(bfs(1).first).second << "\n";
}""", "javascript": r"""
const d = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
const n = d[0];
const adj = Array.from({ length: n + 1 }, () => []);
for (let i = 0; i < n - 1; i++) { adj[d[1 + 2 * i]].push(d[2 + 2 * i]); adj[d[2 + 2 * i]].push(d[1 + 2 * i]); }
const bfs = s => {
  const dist = new Int32Array(n + 1).fill(-1), file = new Int32Array(n);
  let deb = 0, fin = 0, loin = s;
  dist[s] = 0;
  file[fin++] = s;
  while (deb < fin) {
    const u = file[deb++];
    if (dist[u] > dist[loin]) loin = u;
    for (const v of adj[u]) if (dist[v] < 0) { dist[v] = dist[u] + 1; file[fin++] = v; }
  }
  return [loin, dist[loin]];
};
console.log(bfs(bfs(1)[0])[1]);""", "php": r"""
<?php
$d = array_map('intval', preg_split('/\s+/', trim(stream_get_contents(STDIN))));
$n = $d[0];
$adj = array_fill(0, $n + 1, []);
for ($i = 0; $i < $n - 1; $i++) { $adj[$d[1 + 2 * $i]][] = $d[2 + 2 * $i]; $adj[$d[2 + 2 * $i]][] = $d[1 + 2 * $i]; }
function bfs(array &$adj, int $n, int $s): array {
    $dist = array_fill(0, $n + 1, -1);
    $dist[$s] = 0;
    $file = [$s];
    $loin = $s;
    for ($k = 0; $k < count($file); $k++) {
        $u = $file[$k];
        if ($dist[$u] > $dist[$loin]) $loin = $u;
        foreach ($adj[$u] as $v) if ($dist[$v] < 0) { $dist[$v] = $dist[$u] + 1; $file[] = $v; }
    }
    return [$loin, $dist[$loin]];
}
[$a] = bfs($adj, $n, 1);
echo bfs($adj, $n, $a)[1], "\n";"""}, time=3),

    ch("cavalier", 8, "mini", "Le cavalier", "parcours en largeur",
       "Ligne 1 : n (taille de l'échiquier n × n, jusqu'à 300). Ligne 2 : la case de départ et la case d'arrivée « l1 c1 l2 c2 » (de 1 à n). "
       "Affichez le nombre minimal de sauts de cavalier (en L : 2 cases dans un sens, 1 dans l'autre) pour aller de l'une à l'autre, ou -1.",
       ["8\n1 1 8 8", "8\n1 1 1 1", "3\n1 1 2 2", "2\n1 1 2 2", "300\n1 1 300 300", "300\n150 150 1 300", "1\n1 1 1 1"],
       ["Chaque case est un sommet ; deux cases sont reliées si un saut de cavalier permet de passer de l'une à l'autre.",
        "Les 8 sauts possibles : (±1, ±2) et (±2, ±1). Un BFS depuis le départ donne le nombre minimal de sauts.",
        "Sur un petit échiquier (n ≤ 3), certaines cases sont inaccessibles : le BFS s'en rend compte tout seul."],
       {"python": r"""
from collections import deque
n = int(input())
l1, c1, l2, c2 = (int(x) - 1 for x in input().split())
d = [[-1] * n for _ in range(n)]
d[l1][c1] = 0
q = deque([(l1, c1)])
SAUTS = ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1))
while q:
    y, x = q.popleft()
    if (y, x) == (l2, c2):
        break
    for dy, dx in SAUTS:
        ny, nx = y + dy, x + dx
        if 0 <= ny < n and 0 <= nx < n and d[ny][nx] < 0:
            d[ny][nx] = d[y][x] + 1
            q.append((ny, nx))
print(d[l2][c2])""", "c": r"""
#include <stdio.h>
#include <string.h>
static int d[305][305], qy[90005], qx[90005];
int main(void) {
    int n, l1, c1, l2, c2, deb = 0, fin = 0;
    const int dy[] = {1, 2, -1, -2, 1, 2, -1, -2}, dx[] = {2, 1, 2, 1, -2, -1, -2, -1};
    if (scanf("%d %d %d %d %d", &n, &l1, &c1, &l2, &c2) != 5) return 1;
    memset(d, -1, sizeof d);
    --l1; --c1; --l2; --c2;
    d[l1][c1] = 0;
    qy[fin] = l1; qx[fin++] = c1;
    while (deb < fin) {
        int y = qy[deb], x = qx[deb++];
        if (y == l2 && x == c2) break;
        for (int k = 0; k < 8; ++k) {
            int ny = y + dy[k], nx = x + dx[k];
            if (ny >= 0 && ny < n && nx >= 0 && nx < n && d[ny][nx] < 0) { d[ny][nx] = d[y][x] + 1; qy[fin] = ny; qx[fin++] = nx; }
        }
    }
    printf("%d\n", d[l2][c2]);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <queue>
#include <vector>
int main() {
    int n, l1, c1, l2, c2;
    std::cin >> n >> l1 >> c1 >> l2 >> c2;
    --l1; --c1; --l2; --c2;
    std::vector<std::vector<int>> d(n, std::vector<int>(n, -1));
    std::queue<std::pair<int, int>> q;
    const int dy[] = {1, 2, -1, -2, 1, 2, -1, -2}, dx[] = {2, 1, 2, 1, -2, -1, -2, -1};
    d[l1][c1] = 0;
    q.push({l1, c1});
    while (!q.empty()) {
        auto [y, x] = q.front();
        q.pop();
        if (y == l2 && x == c2) break;
        for (int k = 0; k < 8; ++k) {
            int ny = y + dy[k], nx = x + dx[k];
            if (ny >= 0 && ny < n && nx >= 0 && nx < n && d[ny][nx] < 0) { d[ny][nx] = d[y][x] + 1; q.push({ny, nx}); }
        }
    }
    std::cout << d[l2][c2] << "\n";
}""", "javascript": r"""
const v = require("fs").readFileSync(0, "utf8").trim().split(/\s+/).map(Number);
const n = v[0], [l1, c1, l2, c2] = v.slice(1).map(x => x - 1);
const d = new Int32Array(n * n).fill(-1), q = new Int32Array(n * n);
const dy = [1, 2, -1, -2, 1, 2, -1, -2], dx = [2, 1, 2, 1, -2, -1, -2, -1];
let deb = 0, fin = 0;
d[l1 * n + c1] = 0;
q[fin++] = l1 * n + c1;
while (deb < fin) {
  const c = q[deb++], y = Math.floor(c / n), x = c % n;
  if (y === l2 && x === c2) break;
  for (let k = 0; k < 8; k++) {
    const ny = y + dy[k], nx = x + dx[k];
    if (ny >= 0 && ny < n && nx >= 0 && nx < n && d[ny * n + nx] < 0) { d[ny * n + nx] = d[c] + 1; q[fin++] = ny * n + nx; }
  }
}
console.log(d[l2 * n + c2]);""", "php": r"""
<?php
$n = (int) trim(fgets(STDIN));
[$l1, $c1, $l2, $c2] = array_map(fn($x) => (int) $x - 1, explode(' ', trim(fgets(STDIN))));
$d = array_fill(0, $n * $n, -1);
$d[$l1 * $n + $c1] = 0;
$q = [$l1 * $n + $c1];
$sauts = [[1, 2], [2, 1], [-1, 2], [-2, 1], [1, -2], [2, -1], [-1, -2], [-2, -1]];
for ($k = 0; $k < count($q); $k++) {
    $c = $q[$k];
    $y = intdiv($c, $n); $x = $c % $n;
    if ($y === $l2 && $x === $c2) break;
    foreach ($sauts as [$dy, $dx]) {
        $ny = $y + $dy; $nx = $x + $dx;
        if ($ny >= 0 && $ny < $n && $nx >= 0 && $nx < $n && $d[$ny * $n + $nx] < 0) { $d[$ny * $n + $nx] = $d[$c] + 1; $q[] = $ny * $n + $nx; }
    }
}
echo $d[$l2 * $n + $c2], "\n";"""}),

    ch("metro", 8, "exam", "Examen : le réseau de métro", "Dijkstra",
       "Ligne 1 : L (nombre de lignes de métro) et P (minutes perdues à chaque changement de ligne). Puis L lignes décrivant chacune une ligne : "
       "son nom, puis ses stations séparées par les minutes de trajet (« M1 Gare 3 Bastille 2 Nation » : Gare→Bastille 3 min, Bastille→Nation 2 min ; "
       "on peut rouler dans les deux sens). Puis q, et q trajets « A B ». Pour chacun, affichez la durée minimale en minutes (monter dans la "
       "première rame est gratuit, chaque changement de ligne coûte P), ou « impossible » (station inconnue ou non reliée). De A à A : 0.",
       ["2 5\nM1 Gare 3 Bastille 2 Nation\nM2 Bastille 1 Opera 4 Nation\n3\nGare Nation\nGare Opera\nOpera Gare",
        "2 10\nA x 1 y 1 z\nB z 1 w\n4\nx w\nx x\nw q\nq q", "3 0\nR a 5 b\nS b 5 c\nT a 20 c\n2\na c\nc a", _metro],
       ["Un même quai n'est pas le même « état » selon la ligne où l'on se trouve : un sommet du graphe = (station, ligne).",
        "Arêtes : rouler sur sa ligne jusqu'à la station voisine (durée du trajet), ou changer de ligne dans la même station (P minutes).",
        "Dijkstra depuis tous les états (A, ligne passant par A) à distance 0 ; la réponse est la plus petite distance d'un état (B, ligne quelconque)."],
       {"python": r"""
import heapq
import sys
L = sys.stdin.read().split("\n")
nl, pen = map(int, L[0].split())
adj = {}        # (station, ligne) -> [((station, ligne), minutes)]
lignes_de = {}  # station -> lignes qui la desservent
for l in L[1:nl + 1]:
    t = l.split()
    nom = t[0]
    for i in range(1, len(t), 2):
        lignes_de.setdefault(t[i], set()).add(nom)
        adj.setdefault((t[i], nom), [])
    for i in range(1, len(t) - 2, 2):
        a, m, b = (t[i], nom), int(t[i + 1]), (t[i + 2], nom)
        adj[a].append((b, m))
        adj[b].append((a, m))
for s, ls in lignes_de.items():
    for x in ls:
        for y in ls:
            if x != y:
                adj[(s, x)].append(((s, y), pen))
q = int(L[nl + 1])
for l in L[nl + 2:nl + 2 + q]:
    a, b = l.split()
    if a not in lignes_de or b not in lignes_de:
        print("impossible")
        continue
    dist = {(a, x): 0 for x in lignes_de[a]}
    tas = [(0, a, x) for x in lignes_de[a]]
    res = None
    while tas:
        d, s, li = heapq.heappop(tas)
        if d > dist[(s, li)]:
            continue
        if s == b:
            res = d
            break
        for v, m in adj[(s, li)]:
            if d + m < dist.get(v, float("inf")):
                dist[v] = d + m
                heapq.heappush(tas, (d + m, v[0], v[1]))
    print("impossible" if res is None else res)""", "c": r"""
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
/* états = (station, ligne) numérotés ; arêtes en listes chaînées ; tas binaire pour Dijkstra */
#define MS 20000
#define MA 400000
static char noms[MS][32];
static int ns = 0, nst = 0, ne = 0;
static int st_station[MS], st_ligne[MS], tete[MS], suiv[MA], vers[MA], cout_a[MA];
static long long dist[MS];
typedef struct { long long d; int u; } Elt;
static Elt tas[MA];
static int nt;
static int station(const char *s, int creer) {
    for (int i = 0; i < ns; ++i) if (!strcmp(noms[i], s)) return i;
    if (!creer) return -1;
    strcpy(noms[ns], s);
    return ns++;
}
static int etat(int s, int l) {
    for (int i = 0; i < nst; ++i) if (st_station[i] == s && st_ligne[i] == l) return i;
    st_station[nst] = s; st_ligne[nst] = l; tete[nst] = -1;
    return nst++;
}
static void arete(int a, int b, int c) { vers[ne] = b; cout_a[ne] = c; suiv[ne] = tete[a]; tete[a] = ne++; }
static void pousse(long long d, int u) {
    int i = nt++;
    tas[i] = (Elt){d, u};
    while (i && tas[(i - 1) / 2].d > tas[i].d) { Elt x = tas[i]; tas[i] = tas[(i - 1) / 2]; tas[(i - 1) / 2] = x; i = (i - 1) / 2; }
}
static Elt retire(void) {
    Elt r = tas[0];
    tas[0] = tas[--nt];
    for (int i = 0;;) {
        int g = 2 * i + 1, d = g + 1, m = i;
        if (g < nt && tas[g].d < tas[m].d) m = g;
        if (d < nt && tas[d].d < tas[m].d) m = d;
        if (m == i) break;
        Elt x = tas[i]; tas[i] = tas[m]; tas[m] = x;
        i = m;
    }
    return r;
}
int main(void) {
    int nl, pen, q;
    static char ligne[1 << 16];
    if (!fgets(ligne, sizeof ligne, stdin) || sscanf(ligne, "%d %d", &nl, &pen) != 2) return 1;
    for (int l = 0; l < nl; ++l) {
        if (!fgets(ligne, sizeof ligne, stdin)) return 1;
        strtok(ligne, " \r\n");
        int prec = -1, minutes = 0, pos = 0;
        for (char *t = strtok(NULL, " \r\n"); t; t = strtok(NULL, " \r\n"), ++pos) {
            if (pos % 2) { minutes = atoi(t); continue; }
            int e = etat(station(t, 1), l);
            if (prec >= 0) { arete(prec, e, minutes); arete(e, prec, minutes); }
            prec = e;
        }
    }
    for (int a = 0; a < nst; ++a)
        for (int b = 0; b < nst; ++b)
            if (a != b && st_station[a] == st_station[b]) arete(a, b, pen);
    if (!fgets(ligne, sizeof ligne, stdin) || sscanf(ligne, "%d", &q) != 1) return 1;
    while (q-- > 0) {
        char A[32], B[32];
        if (!fgets(ligne, sizeof ligne, stdin) || sscanf(ligne, "%31s %31s", A, B) != 2) return 1;
        int sa = station(A, 0), sb = station(B, 0);
        if (sa < 0 || sb < 0) { puts("impossible"); continue; }
        for (int i = 0; i < nst; ++i) dist[i] = -1;
        nt = 0;
        for (int i = 0; i < nst; ++i) if (st_station[i] == sa) { dist[i] = 0; pousse(0, i); }
        long long res = -1;
        while (nt) {
            Elt e = retire();
            if (e.d > dist[e.u]) continue;
            if (st_station[e.u] == sb) { res = e.d; break; }
            for (int a = tete[e.u]; a >= 0; a = suiv[a]) {
                long long nd = e.d + cout_a[a];
                if (dist[vers[a]] < 0 || nd < dist[vers[a]]) { dist[vers[a]] = nd; pousse(nd, vers[a]); }
            }
        }
        if (res < 0) puts("impossible"); else printf("%lld\n", res);
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <map>
#include <queue>
#include <set>
#include <sstream>
#include <string>
#include <vector>
#include <functional>
int main() {
    int nl, pen;
    std::string l;
    std::getline(std::cin, l);
    std::istringstream(l) >> nl >> pen;
    std::map<std::pair<std::string, int>, int> id;            // (station, ligne) → numéro d'état
    std::map<std::string, std::vector<int>> etats_de;         // station → ses états
    std::vector<std::vector<std::pair<int, long long>>> adj;
    auto etat = [&](const std::string& s, int li) {
        auto k = std::make_pair(s, li);
        auto it = id.find(k);
        if (it != id.end()) return it->second;
        int n = (int)adj.size();
        id[k] = n;
        adj.emplace_back();
        etats_de[s].push_back(n);
        return n;
    };
    for (int li = 0; li < nl; ++li) {
        std::getline(std::cin, l);
        std::istringstream in(l);
        std::string nom, s;
        long long m;
        in >> nom >> s;
        int prec = etat(s, li);
        while (in >> m >> s) {
            int e = etat(s, li);
            adj[prec].push_back({e, m});
            adj[e].push_back({prec, m});
            prec = e;
        }
    }
    for (auto& [s, v] : etats_de)
        for (int a : v) for (int b : v) if (a != b) adj[a].push_back({b, pen});
    int q;
    std::getline(std::cin, l);
    q = std::stoi(l);
    while (q-- > 0) {
        std::string A, B;
        std::getline(std::cin, l);
        std::istringstream(l) >> A >> B;
        if (!etats_de.count(A) || !etats_de.count(B)) { std::cout << "impossible\n"; continue; }
        std::set<int> cible(etats_de[B].begin(), etats_de[B].end());
        std::vector<long long> dist(adj.size(), -1);
        std::priority_queue<std::pair<long long, int>, std::vector<std::pair<long long, int>>, std::greater<>> pq;
        for (int e : etats_de[A]) { dist[e] = 0; pq.push({0, e}); }
        long long res = -1;
        while (!pq.empty()) {
            auto [d, u] = pq.top();
            pq.pop();
            if (d > dist[u]) continue;
            if (cible.count(u)) { res = d; break; }
            for (auto [v, m] : adj[u]) if (dist[v] < 0 || d + m < dist[v]) { dist[v] = d + m; pq.push({dist[v], v}); }
        }
        if (res < 0) std::cout << "impossible\n"; else std::cout << res << "\n";
    }
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const [nl, pen] = L[0].trim().split(/\s+/).map(Number);
const id = new Map(), etatsDe = new Map(), adj = [], station = [];
const etat = (s, li) => {
  const k = `${s}#${li}`;
  if (id.has(k)) return id.get(k);
  const n = adj.length;
  id.set(k, n); adj.push([]); station.push(s);
  if (!etatsDe.has(s)) etatsDe.set(s, []);
  etatsDe.get(s).push(n);
  return n;
};
for (let li = 0; li < nl; li++) {
  const t = L[1 + li].trim().split(/\s+/);
  let prec = etat(t[1], li);
  for (let i = 2; i + 1 < t.length; i += 2) {
    const e = etat(t[i + 1], li), m = Number(t[i]);
    adj[prec].push([e, m]); adj[e].push([prec, m]);
    prec = e;
  }
}
for (const v of etatsDe.values()) for (const a of v) for (const b of v) if (a !== b) adj[a].push([b, pen]);
const q = Number(L[nl + 1]), out = [];
for (let k = 0; k < q; k++) {
  const [A, B] = L[nl + 2 + k].trim().split(/\s+/);
  if (!etatsDe.has(A) || !etatsDe.has(B)) { out.push("impossible"); continue; }
  const dist = new Array(adj.length).fill(Infinity), fait = new Uint8Array(adj.length);
  const tas = [];   // petit graphe : une file triée par insertion binaire suffit
  const pousse = (d, u) => { let lo = 0, hi = tas.length; while (lo < hi) { const m = (lo + hi) >> 1; if (tas[m][0] > d) lo = m + 1; else hi = m; } tas.splice(lo, 0, [d, u]); };
  for (const e of etatsDe.get(A)) { dist[e] = 0; pousse(0, e); }
  let res = -1;
  while (tas.length) {
    const [d, u] = tas.pop();
    if (fait[u]) continue;
    fait[u] = 1;
    if (station[u] === B) { res = d; break; }
    for (const [v, m] of adj[u]) if (d + m < dist[v]) { dist[v] = d + m; pousse(dist[v], v); }
  }
  out.push(res < 0 ? "impossible" : res);
}
console.log(out.join("\n"));""", "php": r"""
<?php
[$nl, $pen] = array_map('intval', preg_split('/\s+/', trim(fgets(STDIN))));
$id = []; $etatsDe = []; $adj = []; $station = [];
$etat = function (string $s, int $li) use (&$id, &$etatsDe, &$adj, &$station): int {
    $k = "$s#$li";
    if (isset($id[$k])) return $id[$k];
    $n = count($adj);
    $id[$k] = $n; $adj[] = []; $station[] = $s;
    $etatsDe[$s][] = $n;
    return $n;
};
for ($li = 0; $li < $nl; $li++) {
    $t = preg_split('/\s+/', trim(fgets(STDIN)));
    $prec = $etat($t[1], $li);
    for ($i = 2; $i + 1 < count($t); $i += 2) {
        $e = $etat($t[$i + 1], $li);
        $adj[$prec][] = [$e, (int) $t[$i]];
        $adj[$e][] = [$prec, (int) $t[$i]];
        $prec = $e;
    }
}
foreach ($etatsDe as $v) foreach ($v as $a) foreach ($v as $b) if ($a !== $b) $adj[$a][] = [$b, $pen];
$q = (int) trim(fgets(STDIN));
for ($k = 0; $k < $q; $k++) {
    [$A, $B] = preg_split('/\s+/', trim(fgets(STDIN)));
    if (!isset($etatsDe[$A]) || !isset($etatsDe[$B])) { echo "impossible\n"; continue; }
    $dist = array_fill(0, count($adj), PHP_INT_MAX);
    $pq = new SplPriorityQueue();
    $pq->setExtractFlags(SplPriorityQueue::EXTR_BOTH);
    foreach ($etatsDe[$A] as $e) { $dist[$e] = 0; $pq->insert($e, 0); }
    $res = -1;
    while (!$pq->isEmpty()) {
        ['data' => $u, 'priority' => $p] = $pq->extract();
        $d = -$p;
        if ($d > $dist[$u]) continue;
        if ($station[$u] === $B) { $res = $d; break; }
        foreach ($adj[$u] as [$v, $m]) if ($d + $m < $dist[$v]) { $dist[$v] = $d + $m; $pq->insert($v, -$dist[$v]); }
    }
    echo $res < 0 ? "impossible" : $res, "\n";
}"""}, minutes=60, time=3),
]
