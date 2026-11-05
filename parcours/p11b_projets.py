# -*- coding: utf-8 -*-
"""Palier 11 (2/2) — Projets d'ingénieur : parseur JSON, mini-SQL, tableur, interpréteur (examen final)."""
import json

from .base import ch, lines


def _rand(n, lo, hi, seed=1):
    x, out = seed, []
    for _ in range(n):
        x = (x * 6364136223846793005 + 1442695040888963407) % 2 ** 64
        out.append(lo + (x >> 33) % (hi - lo + 1))
    return out


# ---------------------------------------------------------------- JSON
_J1 = """5
$.nom
$.age
$.langages[1]
$.adresse.ville
$.inconnu
{"nom": "Ada", "age": 36, "langages": ["C", "Python", "JS"], "adresse": {"ville": "Paris", "cp": "75001"}}"""

_J2 = r"""10
$
$.a
$.a[1]
$.a[2].b
$.a[2].c
$.a[3]
$.vide
$.s
$.a.b
$.u
{
  "a": [1, -2.5e3, {"b": true, "c": null}],
  "vide": {},
  "s": "guillemet \" barre \\ slash \/ tab\tfin",
  "u": "café €"
}"""


def _gros_json():
    r = _rand(20000, 0, 10 ** 6, 5)
    villes = ["Paris", "Lyon", "Nantes", "Lille", "Brest", "Nice", "Orléans", "Besançon"]
    doc = {"version": 3, "actif": True, "note": None, "utilisateurs": [
        {"id": i, "nom": f"user{i}", "ville": villes[r[i] % 8], "score": r[i] % 1000 - 500 + (r[i] % 7) / 4,
         "tags": [f"t{(r[i] >> k) % 13}" for k in range(r[i] % 4)], "profil": {"age": 18 + r[i] % 60, "vip": r[i] % 5 == 0}}
        for i in range(1500)]}
    q = []
    for i in range(300):
        u = r[3000 + i] % 1600
        q.append([f"$.utilisateurs[{u}].nom", f"$.utilisateurs[{u}].ville", f"$.utilisateurs[{u}].tags[1]", f"$.utilisateurs[{u}].profil",
                  f"$.utilisateurs[{u}].profil.age", f"$.utilisateurs[{u}].score", f"$.utilisateurs[{u}].profil.vip", "$.note", "$.utilisateurs", "$.version.x"][i % 10])
    return f"{len(q)}\n" + lines(q) + "\n" + json.dumps(doc, indent=1 if r[0] % 2 else None)


# ---------------------------------------------------------------- SQL
_TABLE = """nom,age,ville,salaire
ana,34,Paris,4200
bob,27,Lyon,3100
chloe,41,Paris,5300
dan,27,Nantes,2900
eve,35,Lyon,4700
---"""
_S1 = _TABLE + "\nSELECT * WHERE ville = Paris\nSELECT nom,salaire ORDER BY salaire DESC LIMIT 3\nSELECT nom WHERE age >= 30 ORDER BY nom"
_S2 = _TABLE + "\nSELECT nom,age ORDER BY age\nSELECT pays\nSELECT nom WHERE age < 20\nSELECT nom,ville ORDER BY ville DESC\nSELECT age WHERE nom != bob LIMIT 1\nSELECT nom WHERE salaire > 3000 ORDER BY age DESC LIMIT 2"


def _gros_sql():
    r = _rand(12000, 0, 10 ** 6, 11)
    prenoms = ["ana", "bob", "chloe", "dan", "eve", "farid", "gael", "hana", "ines", "jules", "karim", "lou"]
    villes = ["Paris", "Lyon", "Nantes", "Lille", "Brest", "Nice"]
    rows = [f"{prenoms[r[i] % 12]}{i},{18 + r[i] % 50},{villes[(r[i] >> 4) % 6]},{1500 + (r[i] >> 3) % 6000},{(r[i] >> 6) % 5}" for i in range(4000)]
    q = ["SELECT nom,salaire WHERE ville = Lyon ORDER BY salaire DESC LIMIT 20", "SELECT * WHERE age < 20 ORDER BY nom LIMIT 15",
         "SELECT ville,nom ORDER BY ville LIMIT 30", "SELECT nom WHERE equipe = 3 ORDER BY age DESC LIMIT 25", "SELECT nom,age WHERE salaire >= 7400",
         "SELECT nom WHERE ville != Paris ORDER BY salaire LIMIT 10", "SELECT salaire,nom WHERE nom > zz", "SELECT nom WHERE age <= 18 ORDER BY equipe DESC LIMIT 12",
         "SELECT prime", "SELECT nom ORDER BY ville DESC LIMIT 5", "SELECT * WHERE ville = Nice ORDER BY age LIMIT 8"]
    return "nom,age,ville,salaire,equipe\n" + lines(rows) + "\n---\n" + lines(q)


# ---------------------------------------------------------------- tableur
_T1 = """A1 = 5
A2 = A1 * 2
B1 = (A1 + A2) / 2
B2 = C1 + 1
C1 = B2 * 2
C2 = Z9 + 1
D1 = A1 / (A2 - 10)
D2 = -A1 + 100"""
_T2 = """B10 = B9 + 1
B9 = 7
AA1 = B10 * B10 - -3
Z1 = AA1 / 4
A3 = X1 + A4
A4 = A3
C1 = 1 / 0 + Q7
C2 = Q7 + 1 / 0
C3 = 10 - 2 - 3
C4 = -(2 + 3) * -2"""


def _gros_tableur():
    out = ["A1 = 1"] + [f"A{i} = A{i - 1} + {i % 7}" for i in range(2, 1001)]
    r = _rand(3100, 0, 10 ** 6, 17)
    for i in range(1, 1001):
        a, b = r[i] % 1000 + 1, r[1000 + i] % 1000 + 1
        out.append(f"B{i} = (A{a} - A{b}) * {r[2000 + i] % 5} / {r[i] % 4}")
    out += ["C1 = C2", "C2 = C3 + A5", "C3 = C1", "C4 = C3 + 1", "C5 = A1000 * 3"]
    return lines(out)


# ---------------------------------------------------------------- interpréteur
_P1 = """x = 5
y = x * 2 + 1
print y
while x > 0
  print x
  x = x - 1
end
if y == 11
  print 1
else
  print 0
end"""
_P2 = """a = 10
print a / 3
print -a % 3
print a / (a - 10)
print 999"""
_P3 = """# commentaire
somme = 0
i = 1

while i <= 100
  somme = somme + i
  i = i + 1
end
print somme
print 3 < 5
print (2 + 3) * (4 - 6) >= -10
print inconnue"""
_P4 = """# nombres premiers inférieurs à 2000 : combien, et leur somme
n = 2
nb = 0
total = 0
while n < 2000
  d = 2
  premier = 1
  while d * d <= n
    if n % d == 0
      premier = 0
      d = n
    end
    d = d + 1
  end
  if premier
    nb = nb + 1
    total = total + n
  end
  n = n + 1
end
print nb
print total"""
_P5 = """# ForgeCode codé en nombres : -3 pour Forge, -5 pour Code, -15 pour les deux
i = 1
while i <= 30
  if i % 15 == 0
    print -15
  else
    if i % 3 == 0
      print -3
    else
      if i % 5 == 0
        print -5
      else
        print i
      end
    end
  end
  i = i + 1
end"""
_P6 = """# suite de Syracuse la plus longue sous 1000
best = 0
arg = 0
n = 1
while n < 1000
  x = n
  k = 0
  while x != 1
    if x % 2 == 0
      x = x / 2
    else
      x = 3 * x + 1
    end
    k = k + 1
  end
  if k > best
    best = k
    arg = n
  end
  n = n + 1
end
print arg
print best
print 7 / -2
print -7 % 2
print 1 - 2 - 3
print 2 * -(3 + 4)
print 5 != 5
print 5 == 5 * 1"""


DEFIS = [
    ch("json", 11, "mini", "Le lecteur JSON", "analyse syntaxique",
       "Ligne 1 : q. Puis q chemins, puis un document JSON (sur une ou plusieurs lignes). Un chemin part de la racine « $ » et enchaîne des clés "
       "« .clé » et des indices « [i] » (à partir de 0). Pour chaque chemin, affichez la valeur : une chaîne sans ses guillemets (échappements "
       "\\\" \\\\ \\/ \\n \\t et \\uXXXX décodés, en UTF-8), un nombre tel qu'il est écrit, true / false / null, « objet (k clés) », « tableau (k éléments) », "
       "ou « introuvable ». Contrainte : écrivez l'analyseur vous-même (pas de bibliothèque JSON).",
       [_J1, _J2, _gros_json],
       ["Analyse par descente récursive : une fonction « valeur » qui regarde le premier caractère ({, [, \", chiffre ou -, t/f/n) et appelle la bonne fonction.",
        "Représentez chaque valeur par un nœud : son type, son texte (nombres, chaînes, littéraux) et ses enfants (liste de (clé, nœud) pour un objet, liste de nœuds pour un tableau).",
        "\\uXXXX : lisez 4 chiffres hexadécimaux, puis encodez le point de code en UTF-8 (1, 2 ou 3 octets). Sautez les espaces et retours à la ligne entre les éléments."],
       {"python": r"""
import sys

def blancs(s, i):
    while i < len(s) and s[i] in " \t\r\n":
        i += 1
    return i

def chaine(s, i):                    # s[i] == '"'
    i += 1
    out = []
    while s[i] != '"':
        if s[i] == "\\":
            e = s[i + 1]
            if e == "u":
                out.append(chr(int(s[i + 2:i + 6], 16)))
                i += 6
                continue
            out.append({"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f"}.get(e, e))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out), i + 1

def valeur(s, i):
    i = blancs(s, i)
    c = s[i]
    if c == "{":
        obj, i = {}, blancs(s, i + 1)
        if s[i] == "}":
            return ("objet", obj), i + 1
        while True:
            k, i = chaine(s, blancs(s, i))
            i = blancs(s, i) + 1                     # ':'
            obj[k], i = valeur(s, i)
            i = blancs(s, i)
            if s[i] == "}":
                return ("objet", obj), i + 1
            i += 1                                   # ','
    if c == "[":
        tab, i = [], blancs(s, i + 1)
        if s[i] == "]":
            return ("tableau", tab), i + 1
        while True:
            v, i = valeur(s, i)
            tab.append(v)
            i = blancs(s, i)
            if s[i] == "]":
                return ("tableau", tab), i + 1
            i += 1
    if c == '"':
        t, i = chaine(s, i)
        return ("chaine", t), i
    j = i
    while j < len(s) and s[j] not in ",]} \t\r\n":
        j += 1
    return ("brut", s[i:j]), j

def suit(n, chemin):
    i = 1
    while i < len(chemin):
        if chemin[i] == ".":
            j = i + 1
            while j < len(chemin) and chemin[j] not in ".[":
                j += 1
            if n[0] != "objet" or chemin[i + 1:j] not in n[1]:
                return None
            n, i = n[1][chemin[i + 1:j]], j
        else:
            j = chemin.index("]", i)
            k = int(chemin[i + 1:j])
            if n[0] != "tableau" or k >= len(n[1]):
                return None
            n, i = n[1][k], j + 1
    return n

L = sys.stdin.read().split("\n")
q = int(L[0])
racine, _ = valeur("\n".join(L[q + 1:]), 0)
for chemin in L[1:q + 1]:
    n = suit(racine, chemin.strip())
    if n is None:
        print("introuvable")
    elif n[0] == "objet":
        print(f"objet ({len(n[1])} clés)")
    elif n[0] == "tableau":
        print(f"tableau ({len(n[1])} éléments)")
    else:
        print(n[1])""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
enum { OBJET, TABLEAU, CHAINE, BRUT };
typedef struct Noeud { int type, nb, cap; char *texte; char **cles; struct Noeud **enf; } Noeud;
static char *s;
static size_t i;
static void blancs(void) { while (s[i] == ' ' || s[i] == '\t' || s[i] == '\r' || s[i] == '\n') ++i; }
static void ajoute(Noeud *n, char *cle, Noeud *e) {
    if (n->nb == n->cap) {
        n->cap = n->cap ? 2 * n->cap : 4;
        n->enf = realloc(n->enf, sizeof *n->enf * n->cap);
        n->cles = realloc(n->cles, sizeof *n->cles * n->cap);
    }
    n->cles[n->nb] = cle;
    n->enf[n->nb++] = e;
}
static char *chaine(void) {                     /* s[i] == '"' */
    size_t cap = 16, k = 0;
    char *r = malloc(cap);
    ++i;
    while (s[i] != '"') {
        if (k + 4 >= cap) r = realloc(r, cap *= 2);
        if (s[i] != '\\') { r[k++] = s[i++]; continue; }
        char e = s[i + 1];
        i += 2;
        if (e == 'u') {
            char h[5] = {s[i], s[i + 1], s[i + 2], s[i + 3], 0};
            unsigned cp = (unsigned)strtoul(h, NULL, 16);
            i += 4;
            if (cp < 0x80) r[k++] = (char)cp;
            else if (cp < 0x800) { r[k++] = (char)(0xC0 | cp >> 6); r[k++] = (char)(0x80 | (cp & 0x3F)); }
            else { r[k++] = (char)(0xE0 | cp >> 12); r[k++] = (char)(0x80 | ((cp >> 6) & 0x3F)); r[k++] = (char)(0x80 | (cp & 0x3F)); }
        } else r[k++] = e == 'n' ? '\n' : e == 't' ? '\t' : e == 'r' ? '\r' : e == 'b' ? '\b' : e == 'f' ? '\f' : e;
    }
    ++i;
    r[k] = '\0';
    return r;
}
static Noeud *valeur(void) {
    Noeud *n = calloc(1, sizeof *n);
    blancs();
    char c = s[i];
    if (c == '{' || c == '[') {
        n->type = c == '{' ? OBJET : TABLEAU;
        ++i;
        blancs();
        if (s[i] == (c == '{' ? '}' : ']')) { ++i; return n; }
        for (;;) {
            char *cle = NULL;
            if (c == '{') { blancs(); cle = chaine(); blancs(); ++i; }
            ajoute(n, cle, valeur());
            blancs();
            if (s[i++] != ',') return n;
        }
    }
    if (c == '"') { n->type = CHAINE; n->texte = chaine(); return n; }
    size_t j = i;
    while (s[j] && !strchr(",]} \t\r\n", s[j])) ++j;
    n->type = BRUT;
    n->texte = malloc(j - i + 1);
    memcpy(n->texte, s + i, j - i);
    n->texte[j - i] = '\0';
    i = j;
    return n;
}
static Noeud *suit(Noeud *n, const char *p) {
    for (size_t k = 1; p[k];) {
        if (p[k] == '.') {
            size_t j = k + 1;
            while (p[j] && p[j] != '.' && p[j] != '[') ++j;
            if (n->type != OBJET) return NULL;
            Noeud *e = NULL;
            for (int m = 0; m < n->nb; ++m) if (strlen(n->cles[m]) == j - k - 1 && !strncmp(n->cles[m], p + k + 1, j - k - 1)) e = n->enf[m];
            if (!e) return NULL;
            n = e;
            k = j;
        } else {
            int idx = atoi(p + k + 1);
            if (n->type != TABLEAU || idx >= n->nb) return NULL;
            n = n->enf[idx];
            k = (size_t)(strchr(p + k, ']') - p) + 1;
        }
    }
    return n;
}
int main(void) {
    int q;
    static char chemins[2000][256];
    char l[256];
    if (!fgets(l, sizeof l, stdin) || sscanf(l, "%d", &q) != 1) return 1;
    for (int k = 0; k < q; ++k) {
        if (!fgets(chemins[k], sizeof chemins[k], stdin)) return 1;
        chemins[k][strcspn(chemins[k], "\r\n")] = '\0';
    }
    size_t cap = 1 << 16, len = 0, lu;
    s = malloc(cap);
    while ((lu = fread(s + len, 1, cap - len - 1, stdin)) > 0) { len += lu; if (len + 1 >= cap) s = realloc(s, cap *= 2); }
    s[len] = '\0';
    i = 0;
    Noeud *racine = valeur();
    for (int k = 0; k < q; ++k) {
        Noeud *n = suit(racine, chemins[k]);
        if (!n) puts("introuvable");
        else if (n->type == OBJET) printf("objet (%d clés)\n", n->nb);
        else if (n->type == TABLEAU) printf("tableau (%d éléments)\n", n->nb);
        else puts(n->texte);
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <iterator>
#include <memory>
#include <string>
#include <vector>
struct Noeud {
    enum Type { OBJET, TABLEAU, CHAINE, BRUT } type;
    std::string texte;
    std::vector<std::pair<std::string, std::unique_ptr<Noeud>>> enfants;   // clé vide pour un tableau
};
class Analyseur {
    const std::string& s;
    size_t i = 0;
    void blancs() { while (i < s.size() && (s[i] == ' ' || s[i] == '\t' || s[i] == '\r' || s[i] == '\n')) ++i; }
    std::string chaine() {
        std::string r;
        ++i;
        while (s[i] != '"') {
            if (s[i] != '\\') { r += s[i++]; continue; }
            char e = s[i + 1];
            i += 2;
            if (e == 'u') {
                unsigned cp = std::stoul(s.substr(i, 4), nullptr, 16);
                i += 4;
                if (cp < 0x80) r += char(cp);
                else if (cp < 0x800) { r += char(0xC0 | cp >> 6); r += char(0x80 | (cp & 0x3F)); }
                else { r += char(0xE0 | cp >> 12); r += char(0x80 | ((cp >> 6) & 0x3F)); r += char(0x80 | (cp & 0x3F)); }
            } else r += e == 'n' ? '\n' : e == 't' ? '\t' : e == 'r' ? '\r' : e == 'b' ? '\b' : e == 'f' ? '\f' : e;
        }
        ++i;
        return r;
    }
public:
    explicit Analyseur(const std::string& src) : s(src) {}
    std::unique_ptr<Noeud> valeur() {
        auto n = std::make_unique<Noeud>();
        blancs();
        char c = s[i];
        if (c == '{' || c == '[') {
            n->type = c == '{' ? Noeud::OBJET : Noeud::TABLEAU;
            ++i;
            blancs();
            if (s[i] == (c == '{' ? '}' : ']')) { ++i; return n; }
            for (;;) {
                std::string cle;
                if (c == '{') { blancs(); cle = chaine(); blancs(); ++i; }
                n->enfants.emplace_back(cle, valeur());
                blancs();
                if (s[i++] != ',') return n;
            }
        }
        if (c == '"') { n->type = Noeud::CHAINE; n->texte = chaine(); return n; }
        size_t j = i;
        while (j < s.size() && std::string(",]} \t\r\n").find(s[j]) == std::string::npos) ++j;
        n->type = Noeud::BRUT;
        n->texte = s.substr(i, j - i);
        i = j;
        return n;
    }
};
const Noeud* suit(const Noeud* n, const std::string& p) {
    for (size_t k = 1; k < p.size();) {
        if (p[k] == '.') {
            size_t j = p.find_first_of(".[", k + 1);
            if (j == std::string::npos) j = p.size();
            std::string cle = p.substr(k + 1, j - k - 1);
            if (n->type != Noeud::OBJET) return nullptr;
            const Noeud* e = nullptr;
            for (auto& [c, f] : n->enfants) if (c == cle) e = f.get();
            if (!e) return nullptr;
            n = e;
            k = j;
        } else {
            size_t j = p.find(']', k);
            size_t idx = std::stoul(p.substr(k + 1, j - k - 1));
            if (n->type != Noeud::TABLEAU || idx >= n->enfants.size()) return nullptr;
            n = n->enfants[idx].second.get();
            k = j + 1;
        }
    }
    return n;
}
int main() {
    std::string l;
    std::getline(std::cin, l);
    int q = std::stoi(l);
    std::vector<std::string> chemins(q);
    for (auto& c : chemins) { std::getline(std::cin, c); if (!c.empty() && c.back() == '\r') c.pop_back(); }
    std::string doc((std::istreambuf_iterator<char>(std::cin)), std::istreambuf_iterator<char>());
    Analyseur a(doc);
    auto racine = a.valeur();
    for (auto& c : chemins) {
        const Noeud* n = suit(racine.get(), c);
        if (!n) std::cout << "introuvable\n";
        else if (n->type == Noeud::OBJET) std::cout << "objet (" << n->enfants.size() << " clés)\n";
        else if (n->type == Noeud::TABLEAU) std::cout << "tableau (" << n->enfants.size() << " éléments)\n";
        else std::cout << n->texte << "\n";
    }
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const q = Number(L[0]), s = L.slice(q + 1).join("\n");
let i = 0;
const blancs = () => { while (" \t\r\n".includes(s[i]) && i < s.length) i++; };
const chaine = () => {
  let r = "";
  i++;
  while (s[i] !== '"') {
    if (s[i] !== "\\") { r += s[i++]; continue; }
    const e = s[i + 1];
    i += 2;
    if (e === "u") { r += String.fromCharCode(parseInt(s.slice(i, i + 4), 16)); i += 4; }
    else r += { n: "\n", t: "\t", r: "\r", b: "\b", f: "\f" }[e] || e;
  }
  i++;
  return r;
};
const valeur = () => {
  blancs();
  const c = s[i];
  if (c === "{" || c === "[") {
    const n = { type: c === "{" ? "objet" : "tableau", enf: c === "{" ? new Map() : [] };
    i++;
    blancs();
    if (s[i] === (c === "{" ? "}" : "]")) { i++; return n; }
    for (;;) {
      if (c === "{") { blancs(); const k = chaine(); blancs(); i++; n.enf.set(k, valeur()); }
      else n.enf.push(valeur());
      blancs();
      if (s[i++] !== ",") return n;
    }
  }
  if (c === '"') return { type: "texte", texte: chaine() };
  const j = i;
  while (i < s.length && !",]} \t\r\n".includes(s[i])) i++;
  return { type: "texte", texte: s.slice(j, i) };
};
const suit = (n, p) => {
  for (let k = 1; k < p.length;) {
    if (p[k] === ".") {
      let j = k + 1;
      while (j < p.length && p[j] !== "." && p[j] !== "[") j++;
      const cle = p.slice(k + 1, j);
      if (n.type !== "objet" || !n.enf.has(cle)) return null;
      n = n.enf.get(cle);
      k = j;
    } else {
      const j = p.indexOf("]", k), idx = Number(p.slice(k + 1, j));
      if (n.type !== "tableau" || idx >= n.enf.length) return null;
      n = n.enf[idx];
      k = j + 1;
    }
  }
  return n;
};
const racine = valeur(), out = [];
for (let k = 1; k <= q; k++) {
  const n = suit(racine, L[k].trim());
  if (!n) out.push("introuvable");
  else if (n.type === "objet") out.push(`objet (${n.enf.size} clés)`);
  else if (n.type === "tableau") out.push(`tableau (${n.enf.length} éléments)`);
  else out.push(n.texte);
}
console.log(out.join("\n"));""", "php": r"""
<?php
$q = (int) trim(fgets(STDIN));
$chemins = [];
for ($k = 0; $k < $q; $k++) $chemins[] = trim(fgets(STDIN));
$s = stream_get_contents(STDIN);
$i = 0;
function blancs(string $s, int &$i): void { while ($i < strlen($s) && strpos(" \t\r\n", $s[$i]) !== false) $i++; }
function utf8(int $cp): string {
    if ($cp < 0x80) return chr($cp);
    if ($cp < 0x800) return chr(0xC0 | $cp >> 6) . chr(0x80 | ($cp & 0x3F));
    return chr(0xE0 | $cp >> 12) . chr(0x80 | (($cp >> 6) & 0x3F)) . chr(0x80 | ($cp & 0x3F));
}
function chaine(string $s, int &$i): string {
    $r = '';
    $i++;
    while ($s[$i] !== '"') {
        if ($s[$i] !== '\\') { $r .= $s[$i++]; continue; }
        $e = $s[$i + 1];
        $i += 2;
        if ($e === 'u') { $r .= utf8(hexdec(substr($s, $i, 4))); $i += 4; }
        else $r .= ['n' => "\n", 't' => "\t", 'r' => "\r", 'b' => "\x08", 'f' => "\f"][$e] ?? $e;
    }
    $i++;
    return $r;
}
function valeur(string $s, int &$i): array {
    blancs($s, $i);
    $c = $s[$i];
    if ($c === '{' || $c === '[') {
        $n = ['type' => $c === '{' ? 'objet' : 'tableau', 'cles' => [], 'enf' => []];
        $i++;
        blancs($s, $i);
        if ($s[$i] === ($c === '{' ? '}' : ']')) { $i++; return $n; }
        for (;;) {
            if ($c === '{') { blancs($s, $i); $n['cles'][] = chaine($s, $i); blancs($s, $i); $i++; }
            $n['enf'][] = valeur($s, $i);
            blancs($s, $i);
            if ($s[$i++] !== ',') return $n;
        }
    }
    if ($c === '"') return ['type' => 'texte', 'texte' => chaine($s, $i)];
    $j = $i;
    while ($i < strlen($s) && strpos(",]} \t\r\n", $s[$i]) === false) $i++;
    return ['type' => 'texte', 'texte' => substr($s, $j, $i - $j)];
}
function suit(array $n, string $p): ?array {
    for ($k = 1, $l = strlen($p); $k < $l;) {
        if ($p[$k] === '.') {
            $j = $k + 1;
            while ($j < $l && $p[$j] !== '.' && $p[$j] !== '[') $j++;
            $cle = substr($p, $k + 1, $j - $k - 1);
            if ($n['type'] !== 'objet') return null;
            $idx = array_search($cle, $n['cles'], true);
            if ($idx === false) return null;
            $n = $n['enf'][$idx];
            $k = $j;
        } else {
            $j = strpos($p, ']', $k);
            $idx = (int) substr($p, $k + 1, $j - $k - 1);
            if ($n['type'] !== 'tableau' || $idx >= count($n['enf'])) return null;
            $n = $n['enf'][$idx];
            $k = $j + 1;
        }
    }
    return $n;
}
$racine = valeur($s, $i);
foreach ($chemins as $c) {
    $n = suit($racine, $c);
    if ($n === null) echo "introuvable\n";
    elseif ($n['type'] === 'objet') echo "objet (", count($n['enf']), " clés)\n";
    elseif ($n['type'] === 'tableau') echo "tableau (", count($n['enf']), " éléments)\n";
    else echo $n['texte'], "\n";
}"""}, time=3, banned={"python": [r"\bjson\b", r"\beval\b", r"\bast\b"], "javascript": [r"JSON\.parse", r"\beval\b", r"Function\s*\("], "php": [r"json_decode", r"\beval\b"]}),

    ch("mini-sql", 11, "mini", "La base de données", "requêtes",
       "L'entrée commence par une table : une ligne d'en-tête (noms de colonnes séparés par des virgules), des lignes de valeurs, puis une ligne « --- ». "
       "Chaque colonne est soit entièrement numérique (entiers), soit textuelle. Viennent ensuite des requêtes, une par ligne : "
       "« SELECT colonnes [WHERE col op valeur] [ORDER BY col [DESC]] [LIMIT n] » où colonnes est « * » ou une liste « a,b », et op l'un de = != < > <= >= "
       "(comparaison numérique si les deux valeurs sont des entiers, sinon comparaison de texte). Le tri est stable (à égalité, l'ordre de la table est "
       "gardé, même en DESC). Pour chaque requête, affichez l'en-tête des colonnes choisies, les lignes, puis « (k ligne) » ou « (k lignes) » (k ≥ 2). "
       "Une colonne inconnue donne « erreur: colonne inconnue X » à la place.",
       [_S1, _S2, _gros_sql],
       ["Séparez le travail : lire la table (liste de lignes, chaque ligne une liste de valeurs), analyser la requête (découper par mots), puis l'exécuter.",
        "Exécution dans l'ordre logique : filtrer (WHERE), trier (ORDER BY, tri stable), couper (LIMIT), puis projeter (SELECT).",
        "Une fonction compare(a, b) : numérique si les deux sont des entiers, texte sinon. Pour un tri DESC stable, inversez la comparaison (pas le résultat du tri)."],
       {"python": r"""
import sys
from functools import cmp_to_key

def entier(x):
    return x.lstrip("-").isdigit() and x.count("-") <= 1 and not x.endswith("-")

def compare(a, b):
    if entier(a) and entier(b):
        a, b = int(a), int(b)
    return (a > b) - (a < b)

L = sys.stdin.read().split("\n")
entete = L[0].strip().split(",")
k = 1
table = []
while L[k].strip() != "---":
    table.append(L[k].strip().split(","))
    k += 1
OPS = {"=": lambda c: c == 0, "!=": lambda c: c != 0, "<": lambda c: c < 0, ">": lambda c: c > 0, "<=": lambda c: c <= 0, ">=": lambda c: c >= 0}
for req in L[k + 1:]:
    t = req.split()
    if not t:
        continue
    cols = entete if t[1] == "*" else t[1].split(",")
    where = order = limit = None
    desc = False
    i = 2
    while i < len(t):
        if t[i] == "WHERE":
            where = (t[i + 1], t[i + 2], t[i + 3])
            i += 4
        elif t[i] == "ORDER":
            order = t[i + 2]
            i += 3
            if i < len(t) and t[i] in ("DESC", "ASC"):
                desc = t[i] == "DESC"
                i += 1
        else:
            limit = int(t[i + 1])
            i += 2
    inconnue = next((c for c in cols + ([where[0]] if where else []) + ([order] if order else []) if c not in entete), None)
    if inconnue:
        print(f"erreur: colonne inconnue {inconnue}")
        continue
    lignes = table
    if where:
        j = entete.index(where[0])
        lignes = [l for l in lignes if OPS[where[1]](compare(l[j], where[2]))]
    if order:
        j = entete.index(order)
        s = -1 if desc else 1
        lignes = sorted(lignes, key=cmp_to_key(lambda a, b: s * compare(a[j], b[j])))
    if limit is not None:
        lignes = lignes[:limit]
    idx = [entete.index(c) for c in cols]
    print(",".join(cols))
    for l in lignes:
        print(",".join(l[j] for j in idx))
    print(f"({len(lignes)} {'lignes' if len(lignes) > 1 else 'ligne'})")""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define MC 16
static char entete[MC][32], table[5000][MC][32];
static int nc = 0, nl = 0, ordre_col, ordre_sens;
static int entier(const char *x) {
    if (*x == '-') ++x;
    if (!*x) return 0;
    for (; *x; ++x) if (*x < '0' || *x > '9') return 0;
    return 1;
}
static int compare(const char *a, const char *b) {
    if (entier(a) && entier(b)) { long long x = atoll(a), y = atoll(b); return (x > y) - (x < y); }
    int c = strcmp(a, b);
    return (c > 0) - (c < 0);
}
static int colonne(const char *n) { for (int i = 0; i < nc; ++i) if (!strcmp(entete[i], n)) return i; return -1; }
static int decoupe(char *l, char sep, char out[][32]) {
    int n = 0;
    for (char *t = strtok(l, sep == ',' ? ",\r\n" : " \r\n"); t; t = strtok(NULL, sep == ',' ? ",\r\n" : " \r\n")) snprintf(out[n++], 32, "%s", t);
    return n;
}
/* tri fusion (stable) d'indices de lignes */
static int tmp[5000];
static void trie(int *v, int n) {
    if (n < 2) return;
    int m = n / 2;
    trie(v, m); trie(v + m, n - m);
    int i = 0, j = m, k = 0;
    while (i < m && j < n) tmp[k++] = ordre_sens * compare(table[v[j]][ordre_col], table[v[i]][ordre_col]) < 0 ? v[j++] : v[i++];
    while (i < m) tmp[k++] = v[i++];
    while (j < n) tmp[k++] = v[j++];
    memcpy(v, tmp, sizeof *v * n);
}
int main(void) {
    char l[1024], mots[32][32];
    if (!fgets(l, sizeof l, stdin)) return 1;
    nc = decoupe(l, ',', entete);
    while (fgets(l, sizeof l, stdin) && strncmp(l, "---", 3)) decoupe(l, ',', table[nl++]);
    while (fgets(l, sizeof l, stdin)) {
        int nm = decoupe(l, ' ', mots);
        if (nm < 2) continue;
        char cols[MC][32];
        int ncols = !strcmp(mots[1], "*") ? nc : 0;
        if (ncols) memcpy(cols, entete, sizeof cols);
        else { char tmpc[64]; snprintf(tmpc, sizeof tmpc, "%s", mots[1]); ncols = decoupe(tmpc, ',', cols); }
        const char *wc = NULL, *wo = NULL, *wv = NULL, *oc = NULL;
        int desc = 0, limite = -1;
        for (int i = 2; i < nm;) {
            if (!strcmp(mots[i], "WHERE")) { wc = mots[i + 1]; wo = mots[i + 2]; wv = mots[i + 3]; i += 4; }
            else if (!strcmp(mots[i], "ORDER")) {
                oc = mots[i + 2]; i += 3;
                if (i < nm && (!strcmp(mots[i], "DESC") || !strcmp(mots[i], "ASC"))) desc = !strcmp(mots[i++], "DESC");
            } else { limite = atoi(mots[i + 1]); i += 2; }
        }
        const char *inconnue = NULL;
        for (int c = 0; c < ncols && !inconnue; ++c) if (colonne(cols[c]) < 0) inconnue = cols[c];
        if (!inconnue && wc && colonne(wc) < 0) inconnue = wc;
        if (!inconnue && oc && colonne(oc) < 0) inconnue = oc;
        if (inconnue) { printf("erreur: colonne inconnue %s\n", inconnue); continue; }
        static int sel[5000];
        int ns = 0;
        for (int r = 0; r < nl; ++r) {
            if (wc) {
                int c = compare(table[r][colonne(wc)], wv);
                int ok = !strcmp(wo, "=") ? c == 0 : !strcmp(wo, "!=") ? c != 0 : !strcmp(wo, "<") ? c < 0 : !strcmp(wo, ">") ? c > 0 : !strcmp(wo, "<=") ? c <= 0 : c >= 0;
                if (!ok) continue;
            }
            sel[ns++] = r;
        }
        if (oc) { ordre_col = colonne(oc); ordre_sens = desc ? -1 : 1; trie(sel, ns); }
        if (limite >= 0 && ns > limite) ns = limite;
        for (int c = 0; c < ncols; ++c) printf(c ? ",%s" : "%s", cols[c]);
        printf("\n");
        for (int k = 0; k < ns; ++k) {
            for (int c = 0; c < ncols; ++c) printf(c ? ",%s" : "%s", table[sel[k]][colonne(cols[c])]);
            printf("\n");
        }
        printf("(%d %s)\n", ns, ns > 1 ? "lignes" : "ligne");
    }
    return 0;
}""", "cpp": r"""
#include <algorithm>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
using Ligne = std::vector<std::string>;
Ligne decoupe(const std::string& s, char sep) {
    Ligne r;
    std::string t;
    std::istringstream in(s);
    while (std::getline(in, t, sep)) { if (!t.empty() && t.back() == '\r') t.pop_back(); if (!t.empty()) r.push_back(t); }
    return r;
}
bool entier(const std::string& x) {
    size_t d = x[0] == '-' ? 1 : 0;
    return x.size() > d && x.find_first_not_of("0123456789", d) == std::string::npos;
}
int compare(const std::string& a, const std::string& b) {
    if (entier(a) && entier(b)) { long long x = std::stoll(a), y = std::stoll(b); return (x > y) - (x < y); }
    return (a > b) - (a < b);
}
int main() {
    std::string l;
    std::getline(std::cin, l);
    Ligne entete = decoupe(l, ',');
    std::vector<Ligne> table;
    while (std::getline(std::cin, l) && l.rfind("---", 0) != 0) table.push_back(decoupe(l, ','));
    auto colonne = [&](const std::string& n) { return (int)(std::find(entete.begin(), entete.end(), n) - entete.begin()); };
    while (std::getline(std::cin, l)) {
        Ligne t = decoupe(l, ' ');
        if (t.size() < 2) continue;
        Ligne cols = t[1] == "*" ? entete : decoupe(t[1], ',');
        std::string wc, wo, wv, oc;
        bool desc = false;
        long limite = -1;
        for (size_t i = 2; i < t.size();) {
            if (t[i] == "WHERE") { wc = t[i + 1]; wo = t[i + 2]; wv = t[i + 3]; i += 4; }
            else if (t[i] == "ORDER") { oc = t[i + 2]; i += 3; if (i < t.size() && (t[i] == "DESC" || t[i] == "ASC")) desc = t[i++] == "DESC"; }
            else { limite = std::stol(t[i + 1]); i += 2; }
        }
        Ligne verif = cols;
        if (!wc.empty()) verif.push_back(wc);
        if (!oc.empty()) verif.push_back(oc);
        auto inconnue = std::find_if(verif.begin(), verif.end(), [&](const std::string& c) { return colonne(c) == (int)entete.size(); });
        if (inconnue != verif.end()) { std::cout << "erreur: colonne inconnue " << *inconnue << "\n"; continue; }
        std::vector<const Ligne*> sel;
        for (auto& r : table) {
            if (!wc.empty()) {
                int c = compare(r[colonne(wc)], wv);
                bool ok = wo == "=" ? c == 0 : wo == "!=" ? c != 0 : wo == "<" ? c < 0 : wo == ">" ? c > 0 : wo == "<=" ? c <= 0 : c >= 0;
                if (!ok) continue;
            }
            sel.push_back(&r);
        }
        if (!oc.empty()) {
            int j = colonne(oc), s = desc ? -1 : 1;
            std::stable_sort(sel.begin(), sel.end(), [&](const Ligne* a, const Ligne* b) { return s * compare((*a)[j], (*b)[j]) < 0; });
        }
        if (limite >= 0 && (long)sel.size() > limite) sel.resize(limite);
        for (size_t c = 0; c < cols.size(); ++c) std::cout << (c ? "," : "") << cols[c];
        std::cout << "\n";
        for (auto r : sel) {
            for (size_t c = 0; c < cols.size(); ++c) std::cout << (c ? "," : "") << (*r)[colonne(cols[c])];
            std::cout << "\n";
        }
        std::cout << "(" << sel.size() << (sel.size() > 1 ? " lignes)" : " ligne)") << "\n";
    }
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n").map(l => l.replace(/\r$/, ""));
const entete = L[0].trim().split(",");
let k = 1;
const table = [];
while (L[k].trim() !== "---") table.push(L[k++].trim().split(","));
const entier = x => /^-?\d+$/.test(x);
const compare = (a, b) => {
  if (entier(a) && entier(b)) { const x = Number(a), y = Number(b); return (x > y) - (x < y); }
  return a > b ? 1 : a < b ? -1 : 0;
};
const OPS = { "=": c => c === 0, "!=": c => c !== 0, "<": c => c < 0, ">": c => c > 0, "<=": c => c <= 0, ">=": c => c >= 0 };
const out = [];
for (const req of L.slice(k + 1)) {
  const t = req.trim().split(/\s+/);
  if (t.length < 2) continue;
  const cols = t[1] === "*" ? entete : t[1].split(",");
  let where = null, order = null, desc = false, limite = null;
  for (let i = 2; i < t.length;) {
    if (t[i] === "WHERE") { where = t.slice(i + 1, i + 4); i += 4; }
    else if (t[i] === "ORDER") { order = t[i + 2]; i += 3; if (t[i] === "DESC" || t[i] === "ASC") desc = t[i++] === "DESC"; }
    else { limite = Number(t[i + 1]); i += 2; }
  }
  const inconnue = [...cols, ...(where ? [where[0]] : []), ...(order ? [order] : [])].find(c => !entete.includes(c));
  if (inconnue) { out.push(`erreur: colonne inconnue ${inconnue}`); continue; }
  let lignes = table;
  if (where) { const j = entete.indexOf(where[0]); lignes = lignes.filter(l => OPS[where[1]](compare(l[j], where[2]))); }
  if (order) { const j = entete.indexOf(order), s = desc ? -1 : 1; lignes = [...lignes].sort((a, b) => s * compare(a[j], b[j])); }
  if (limite !== null) lignes = lignes.slice(0, limite);
  const idx = cols.map(c => entete.indexOf(c));
  out.push(cols.join(","), ...lignes.map(l => idx.map(j => l[j]).join(",")), `(${lignes.length} ${lignes.length > 1 ? "lignes" : "ligne"})`);
}
console.log(out.join("\n"));""", "php": r"""
<?php
$entete = explode(',', trim(fgets(STDIN)));
$table = [];
while (($l = fgets(STDIN)) !== false && trim($l) !== '---') $table[] = explode(',', trim($l));
function entier(string $x): bool { return (bool) preg_match('/^-?\d+$/', $x); }
function compare(string $a, string $b): int {
    if (entier($a) && entier($b)) return (int) $a <=> (int) $b;
    return strcmp($a, $b) <=> 0;
}
while (($l = fgets(STDIN)) !== false) {
    $t = preg_split('/\s+/', trim($l));
    if (count($t) < 2) continue;
    $cols = $t[1] === '*' ? $entete : explode(',', $t[1]);
    $where = $order = $limite = null;
    $desc = false;
    for ($i = 2; $i < count($t);) {
        if ($t[$i] === 'WHERE') { $where = array_slice($t, $i + 1, 3); $i += 4; }
        elseif ($t[$i] === 'ORDER') {
            $order = $t[$i + 2]; $i += 3;
            if (isset($t[$i]) && ($t[$i] === 'DESC' || $t[$i] === 'ASC')) $desc = $t[$i++] === 'DESC';
        } else { $limite = (int) $t[$i + 1]; $i += 2; }
    }
    $verif = array_merge($cols, $where ? [$where[0]] : [], $order ? [$order] : []);
    $inconnue = null;
    foreach ($verif as $c) if (!in_array($c, $entete, true)) { $inconnue = $c; break; }
    if ($inconnue !== null) { echo "erreur: colonne inconnue $inconnue\n"; continue; }
    $lignes = $table;
    if ($where) {
        $j = array_search($where[0], $entete, true);
        $lignes = array_values(array_filter($lignes, function ($r) use ($j, $where) {
            $c = compare($r[$j], $where[2]);
            return match ($where[1]) { '=' => $c === 0, '!=' => $c !== 0, '<' => $c < 0, '>' => $c > 0, '<=' => $c <= 0, default => $c >= 0 };
        }));
    }
    if ($order) {
        $j = array_search($order, $entete, true);
        $s = $desc ? -1 : 1;
        usort($lignes, fn($a, $b) => $s * compare($a[$j], $b[$j]));     // usort est stable depuis PHP 8
    }
    if ($limite !== null) $lignes = array_slice($lignes, 0, $limite);
    $idx = array_map(fn($c) => array_search($c, $entete, true), $cols);
    echo implode(',', $cols), "\n";
    foreach ($lignes as $r) echo implode(',', array_map(fn($j) => $r[$j], $idx)), "\n";
    $n = count($lignes);
    echo "($n ", $n > 1 ? "lignes" : "ligne", ")\n";
}"""}, time=3),

    ch("tableur", 11, "mini", "Le moteur de tableur", "graphes et évaluation",
       "Chaque ligne définit une cellule : « A1 = expression », avec des entiers, des références à d'autres cellules (lettres majuscules puis numéro de "
       "ligne), + - * / (division entière tronquée vers zéro), des parenthèses et le moins unaire. Évaluez chaque cellule, dans l'ordre d'affichage : par "
       "colonne (A … Z, AA …) puis par numéro de ligne. Affichez « A1 = valeur ». Erreurs : « #REF » (cellule non définie), « #DIV0 » (division par zéro), "
       "« #CYCLE » (dépendance circulaire). Une expression est évaluée de gauche à droite et prend la première erreur rencontrée (le reste n'est pas évalué).",
       [_T1, _T2, _gros_tableur],
       ["Évaluation récursive avec mémoïsation : pour calculer une cellule, calculez d'abord celles dont elle dépend, et retenez chaque résultat.",
        "Détection des cycles : marquez une cellule « en cours » pendant son calcul ; tomber sur une cellule « en cours » signifie un cycle → #CYCLE.",
        "Une chaîne de 1 000 cellules donne une récursion profonde : en Python, pensez à sys.setrecursionlimit. Triez les noms par (longueur des lettres, lettres, numéro)."],
       {"python": r"""
import re
import sys
sys.setrecursionlimit(100000)
formules = {}
for l in sys.stdin.read().split("\n"):
    if "=" in l:
        nom, expr = l.split("=", 1)
        formules[nom.strip()] = re.findall(r"[A-Z]+[0-9]+|\d+|[-+*/()]", expr)
valeurs, etat = {}, {}

class Err(Exception):
    pass

def cellule(nom):
    if nom not in formules:
        raise Err("#REF")
    if etat.get(nom) == 2:
        if isinstance(valeurs[nom], str):
            raise Err(valeurs[nom])
        return valeurs[nom]
    if etat.get(nom) == 1:
        raise Err("#CYCLE")
    etat[nom] = 1
    toks, pos = formules[nom], [0]

    def facteur():
        t = toks[pos[0]]
        pos[0] += 1
        if t == "-":
            return -facteur()
        if t == "(":
            v = somme()
            pos[0] += 1
            return v
        return int(t) if t.isdigit() else cellule(t)

    def produit():
        v = facteur()
        while pos[0] < len(toks) and toks[pos[0]] in "*/":
            o = toks[pos[0]]
            pos[0] += 1
            r = facteur()
            if o == "*":
                v *= r
            elif r == 0:
                raise Err("#DIV0")
            else:
                q = abs(v) // abs(r)
                v = q if (v < 0) == (r < 0) else -q
        return v

    def somme():
        v = produit()
        while pos[0] < len(toks) and toks[pos[0]] in "+-":
            o = toks[pos[0]]
            pos[0] += 1
            r = produit()
            v = v + r if o == "+" else v - r
        return v

    try:
        valeurs[nom] = somme()
    except Err as e:
        valeurs[nom] = e.args[0]
    etat[nom] = 2
    if isinstance(valeurs[nom], str):
        raise Err(valeurs[nom])
    return valeurs[nom]

def cle(nom):
    lettres = re.match(r"[A-Z]+", nom).group()
    return (len(lettres), lettres, int(nom[len(lettres):]))

for nom in sorted(formules, key=cle):
    try:
        cellule(nom)
    except Err:
        pass
    print(f"{nom} = {valeurs[nom]}")""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#define MAXC 4000
typedef struct { char nom[16]; char tok[64][16]; int nt, etat, err; long long val; } Cellule;
static Cellule c[MAXC];
static int nc = 0;
static const char *ERR[] = {"", "#REF", "#DIV0", "#CYCLE"};
static int trouve(const char *n) { for (int i = 0; i < nc; ++i) if (!strcmp(c[i].nom, n)) return i; return -1; }
static long long eval_cellule(int k, int *err);
typedef struct { Cellule *x; int pos; int *err; } Ctx;
static long long somme(Ctx *t);
static long long facteur(Ctx *t) {
    const char *s = t->x->tok[t->pos++];
    if (!strcmp(s, "-")) { long long v = facteur(t); return -v; }
    if (!strcmp(s, "(")) { long long v = somme(t); t->pos++; return v; }
    if (isdigit((unsigned char)s[0])) return atoll(s);
    int k = trouve(s);
    if (k < 0) { *t->err = 1; return 0; }
    return eval_cellule(k, t->err);
}
static long long produit(Ctx *t) {
    long long v = facteur(t);
    while (!*t->err && t->pos < t->x->nt && (t->x->tok[t->pos][0] == '*' || t->x->tok[t->pos][0] == '/')) {
        char o = t->x->tok[t->pos++][0];
        long long r = facteur(t);
        if (*t->err) return 0;
        if (o == '*') v *= r;
        else if (r == 0) { *t->err = 2; return 0; }
        else v /= r;
    }
    return v;
}
static long long somme(Ctx *t) {
    long long v = produit(t);
    while (!*t->err && t->pos < t->x->nt && (t->x->tok[t->pos][0] == '+' || (t->x->tok[t->pos][0] == '-' && !t->x->tok[t->pos][1]))) {
        char o = t->x->tok[t->pos++][0];
        long long r = produit(t);
        if (*t->err) return 0;
        v = o == '+' ? v + r : v - r;
    }
    return v;
}
static long long eval_cellule(int k, int *err) {
    Cellule *x = &c[k];
    if (x->etat == 2) { *err = x->err; return x->val; }
    if (x->etat == 1) { *err = 3; return 0; }
    x->etat = 1;
    int e = 0;
    Ctx t = {x, 0, &e};
    long long v = somme(&t);
    x->etat = 2; x->err = e; x->val = e ? 0 : v;
    *err = e;
    return x->val;
}
static int ordre(const void *a, const void *b) {
    const char *p = ((const Cellule *)a)->nom, *q = ((const Cellule *)b)->nom;
    size_t lp = strspn(p, "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), lq = strspn(q, "ABCDEFGHIJKLMNOPQRSTUVWXYZ");
    if (lp != lq) return lp < lq ? -1 : 1;
    int s = strncmp(p, q, lp);
    if (s) return s;
    return atoi(p + lp) - atoi(q + lq);
}
int main(void) {
    char l[1024];
    while (fgets(l, sizeof l, stdin)) {
        char *eg = strchr(l, '=');
        if (!eg) continue;
        *eg = '\0';
        Cellule *x = &c[nc++];
        sscanf(l, "%15s", x->nom);
        for (char *p = eg + 1; *p;) {
            if (isspace((unsigned char)*p)) { ++p; continue; }
            int n = 0;
            if (isalnum((unsigned char)*p)) while (isalnum((unsigned char)*p) && n < 15) x->tok[x->nt][n++] = *p++;
            else x->tok[x->nt][n++] = *p++;
            x->tok[x->nt++][n] = '\0';
        }
    }
    qsort(c, nc, sizeof *c, ordre);
    for (int k = 0; k < nc; ++k) {
        int e = 0;
        long long v = eval_cellule(k, &e);
        if (c[k].err) printf("%s = %s\n", c[k].nom, ERR[c[k].err]);
        else printf("%s = %lld\n", c[k].nom, v);
    }
    return 0;
}""", "cpp": r"""
#include <algorithm>
#include <cctype>
#include <iostream>
#include <map>
#include <string>
#include <vector>
struct Erreur { std::string code; };
struct Cellule { std::vector<std::string> toks; int etat = 0; long long val = 0; std::string err; };
std::map<std::string, Cellule> cellules;
long long evalue(const std::string& nom);
struct Expr {
    const std::vector<std::string>& t;
    size_t p = 0;
    long long facteur() {
        const std::string& s = t[p++];
        if (s == "-") return -facteur();
        if (s == "(") { long long v = somme(); ++p; return v; }
        if (std::isdigit((unsigned char)s[0])) return std::stoll(s);
        return evalue(s);
    }
    long long produit() {
        long long v = facteur();
        while (p < t.size() && (t[p] == "*" || t[p] == "/")) {
            std::string o = t[p++];
            long long r = facteur();
            if (o == "*") v *= r;
            else if (r == 0) throw Erreur{"#DIV0"};
            else v /= r;
        }
        return v;
    }
    long long somme() {
        long long v = produit();
        while (p < t.size() && (t[p] == "+" || t[p] == "-")) {
            std::string o = t[p++];
            long long r = produit();
            v = o == "+" ? v + r : v - r;
        }
        return v;
    }
};
long long evalue(const std::string& nom) {
    auto it = cellules.find(nom);
    if (it == cellules.end()) throw Erreur{"#REF"};
    Cellule& c = it->second;
    if (c.etat == 1) throw Erreur{"#CYCLE"};
    if (c.etat == 0) {
        c.etat = 1;
        try { Expr e{c.toks}; c.val = e.somme(); } catch (const Erreur& e) { c.err = e.code; }
        c.etat = 2;
    }
    if (!c.err.empty()) throw Erreur{c.err};
    return c.val;
}
int main() {
    std::string l;
    while (std::getline(std::cin, l)) {
        size_t eg = l.find('=');
        if (eg == std::string::npos) continue;
        std::string nom;
        for (char ch : l.substr(0, eg)) if (!std::isspace((unsigned char)ch)) nom += ch;
        Cellule& c = cellules[nom];
        for (size_t i = eg + 1; i < l.size();) {
            if (std::isspace((unsigned char)l[i])) { ++i; continue; }
            size_t j = i;
            if (std::isalnum((unsigned char)l[i])) while (j < l.size() && std::isalnum((unsigned char)l[j])) ++j;
            else ++j;
            c.toks.push_back(l.substr(i, j - i));
            i = j;
        }
    }
    std::vector<std::string> noms;
    for (auto& [n, c] : cellules) noms.push_back(n);
    auto cle = [](const std::string& n) {
        size_t k = n.find_first_of("0123456789");
        return std::make_tuple(k, n.substr(0, k), std::stol(n.substr(k)));
    };
    std::sort(noms.begin(), noms.end(), [&](const std::string& a, const std::string& b) { return cle(a) < cle(b); });
    for (auto& n : noms) {
        try { evalue(n); } catch (const Erreur&) {}
        const Cellule& c = cellules[n];
        std::cout << n << " = " << (c.err.empty() ? std::to_string(c.val) : c.err) << "\n";
    }
}""", "javascript": r"""
const formules = new Map();
for (const l of require("fs").readFileSync(0, "utf8").split("\n")) {
  const eg = l.indexOf("=");
  if (eg < 0) continue;
  formules.set(l.slice(0, eg).trim(), l.slice(eg + 1).match(/[A-Z]+[0-9]+|\d+|[-+*\/()]/g) || []);
}
const valeurs = new Map(), etat = new Map();
class Err { constructor(code) { this.code = code; } }
const cellule = nom => {
  if (!formules.has(nom)) throw new Err("#REF");
  if (etat.get(nom) === 1) throw new Err("#CYCLE");
  if (etat.get(nom) !== 2) {
    etat.set(nom, 1);
    const t = formules.get(nom);
    let p = 0;
    const facteur = () => {
      const s = t[p++];
      if (s === "-") return -facteur();
      if (s === "(") { const v = somme(); p++; return v; }
      return /^\d+$/.test(s) ? BigInt(s) : cellule(s);
    };
    const produit = () => {
      let v = facteur();
      while (t[p] === "*" || t[p] === "/") {
        const o = t[p++], r = facteur();
        if (o === "*") v *= r;
        else if (r === 0n) throw new Err("#DIV0");
        else v /= r;
      }
      return v;
    };
    const somme = () => {
      let v = produit();
      while (t[p] === "+" || t[p] === "-") { const o = t[p++], r = produit(); v = o === "+" ? v + r : v - r; }
      return v;
    };
    try { valeurs.set(nom, somme()); } catch (e) { if (!(e instanceof Err)) throw e; valeurs.set(nom, e.code); }
    etat.set(nom, 2);
  }
  const v = valeurs.get(nom);
  if (typeof v === "string") throw new Err(v);
  return v;
};
const cle = n => { const l = n.match(/^[A-Z]+/)[0]; return [l.length, l, Number(n.slice(l.length))]; };
const noms = [...formules.keys()].sort((a, b) => {
  const x = cle(a), y = cle(b);
  return x[0] - y[0] || (x[1] < y[1] ? -1 : x[1] > y[1] ? 1 : 0) || x[2] - y[2];
});
const out = [];
for (const n of noms) {
  try { cellule(n); } catch (e) { if (!(e instanceof Err)) throw e; }
  out.push(`${n} = ${valeurs.get(n)}`);
}
console.log(out.join("\n"));""", "php": r"""
<?php
$formules = [];
while (($l = fgets(STDIN)) !== false) {
    $eg = strpos($l, '=');
    if ($eg === false) continue;
    preg_match_all('/[A-Z]+[0-9]+|\d+|[-+*\/()]/', substr($l, $eg + 1), $m);
    $formules[trim(substr($l, 0, $eg))] = $m[0];
}
$valeurs = []; $etat = [];
class Err extends Exception {}
function cellule(string $nom) {
    global $formules, $valeurs, $etat;
    if (!isset($formules[$nom])) throw new Err('#REF');
    if (($etat[$nom] ?? 0) === 1) throw new Err('#CYCLE');
    if (($etat[$nom] ?? 0) === 0) {
        $etat[$nom] = 1;
        $t = $formules[$nom];
        $p = 0;
        $facteur = null; $produit = null; $somme = null;
        $facteur = function () use (&$t, &$p, &$facteur, &$somme) {
            $s = $t[$p++];
            if ($s === '-') return -$facteur();
            if ($s === '(') { $v = $somme(); $p++; return $v; }
            return ctype_digit($s) ? (int) $s : cellule($s);
        };
        $produit = function () use (&$t, &$p, &$facteur) {
            $v = $facteur();
            while (isset($t[$p]) && ($t[$p] === '*' || $t[$p] === '/')) {
                $o = $t[$p++];
                $r = $facteur();
                if ($o === '*') $v *= $r;
                elseif ($r === 0) throw new Err('#DIV0');
                else $v = intdiv($v, $r);
            }
            return $v;
        };
        $somme = function () use (&$t, &$p, &$produit) {
            $v = $produit();
            while (isset($t[$p]) && ($t[$p] === '+' || $t[$p] === '-')) { $o = $t[$p++]; $r = $produit(); $v = $o === '+' ? $v + $r : $v - $r; }
            return $v;
        };
        try { $valeurs[$nom] = $somme(); } catch (Err $e) { $valeurs[$nom] = $e->getMessage(); }
        $etat[$nom] = 2;
    }
    if (is_string($valeurs[$nom])) throw new Err($valeurs[$nom]);
    return $valeurs[$nom];
}
$noms = array_keys($formules);
usort($noms, function ($a, $b) {
    preg_match('/^([A-Z]+)(\d+)$/', $a, $x);
    preg_match('/^([A-Z]+)(\d+)$/', $b, $y);
    return [strlen($x[1]), $x[1], (int) $x[2]] <=> [strlen($y[1]), $y[1], (int) $y[2]];
});
foreach ($noms as $n) {
    try { cellule($n); } catch (Err $e) {}
    echo "$n = {$valeurs[$n]}\n";
}"""}, time=3),

    ch("interpreteur", 11, "exam", "Examen final : l'interpréteur", "langages",
       "Écrivez l'interpréteur d'un petit langage. Chaque ligne est une instruction : « nom = expression », « print expression », « if expression » / « else » / "
       "« end », « while expression » / « end » (les blocs peuvent s'imbriquer ; l'indentation ne compte pas). Lignes vides et commentaires « # … » ignorés. "
       "Expressions : entiers, variables, + - * / % (division tronquée vers zéro, reste du signe du dividende), parenthèses, moins unaire, et au plus une "
       "comparaison == != < > <= >= (qui vaut 1 ou 0). Une condition est vraie si elle est non nulle. Erreurs : « erreur ligne n: variable inconnue x » ou "
       "« erreur ligne n: division par zéro » (n compté à partir de 1, lignes vides comprises), puis arrêt du programme.",
       [_P1, _P2, _P3, _P4, _P5, _P6, "print 1\nprint x + 1\nprint 2"],
       ["Deux étapes : l'analyse (transformer les lignes en arbre d'instructions, les blocs if/while contenant leurs sous-instructions) puis l'exécution.",
        "Pour les blocs, une fonction « bloc(i) » lit des instructions jusqu'à « else » ou « end » et renvoie où elle s'est arrêtée : une récursion naturelle.",
        "Évaluez les expressions par descente récursive (comparaison > somme > produit > unaire > atome), sur une liste de lexèmes préparée une fois pour toutes."],
       {"python": r"""
import re
import sys

class Erreur(Exception):
    pass

lignes = sys.stdin.read().split("\n")
LEX = re.compile(r"\d+|[a-z_][a-z0-9_]*|==|!=|<=|>=|[-+*/%()<>]")

def analyse(i, fin):
    # renvoie (instructions, indice de la ligne qui a arrêté le bloc)
    instrs = []
    while i < len(lignes):
        l = lignes[i].strip()
        mot = l.split()[0] if l else ""
        if not l or l.startswith("#"):
            i += 1
        elif mot in fin:
            return instrs, i
        elif mot == "print":
            instrs.append(("print", i + 1, LEX.findall(l[5:])))
            i += 1
        elif mot in ("if", "while"):
            ligne = i + 1
            cond = LEX.findall(l[len(mot):])
            corps, i = analyse(i + 1, ("else", "end"))
            sinon = []
            if mot == "if" and lignes[i].strip() == "else":
                sinon, i = analyse(i + 1, ("end",))
            instrs.append((mot, ligne, cond, corps, sinon))
            i += 1
        else:
            nom, expr = l.split("=", 1)
            instrs.append(("=", i + 1, nom.strip(), LEX.findall(expr)))
            i += 1
    return instrs, i

variables = {}

def evalue(t, ligne):
    pos = [0]

    def voir():
        return t[pos[0]] if pos[0] < len(t) else None

    def prendre():
        pos[0] += 1
        return t[pos[0] - 1]

    def atome():
        x = prendre()
        if x == "-":
            return -atome()
        if x == "(":
            v = comparaison()
            prendre()
            return v
        if x.isdigit():
            return int(x)
        if x not in variables:
            raise Erreur(f"erreur ligne {ligne}: variable inconnue {x}")
        return variables[x]

    def produit():
        v = atome()
        while voir() in ("*", "/", "%"):
            o, r = prendre(), atome()
            if o == "*":
                v *= r
                continue
            if r == 0:
                raise Erreur(f"erreur ligne {ligne}: division par zéro")
            q = abs(v) // abs(r)
            q = q if (v < 0) == (r < 0) else -q
            v = q if o == "/" else v - r * q
        return v

    def somme():
        v = produit()
        while voir() in ("+", "-"):
            o, r = prendre(), produit()
            v = v + r if o == "+" else v - r
        return v

    def comparaison():
        v = somme()
        if voir() in ("==", "!=", "<", ">", "<=", ">="):
            o, r = prendre(), somme()
            v = int({"==": v == r, "!=": v != r, "<": v < r, ">": v > r, "<=": v <= r, ">=": v >= r}[o])
        return v

    return comparaison()

def execute(instrs, out):
    for ins in instrs:
        if ins[0] == "print":
            out.append(str(evalue(ins[2], ins[1])))
        elif ins[0] == "=":
            variables[ins[2]] = evalue(ins[3], ins[1])
        elif ins[0] == "if":
            execute(ins[3] if evalue(ins[2], ins[1]) else ins[4], out)
        else:
            while evalue(ins[2], ins[1]):
                execute(ins[3], out)

programme, _ = analyse(0, ())
sortie = []
try:
    execute(programme, sortie)
except Erreur as e:
    sortie.append(str(e))
print("\n".join(sortie))""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#define MAXL 2000
/* une instruction par ligne utile ; « saut » relie if → else/end, else → end, while ↔ end */
typedef struct { int type, ligne, nt, saut; char var[32]; char tok[64][24]; } Instr;
enum { PRINT, AFFECT, IF, ELSE, WHILE, END };
static Instr prog[MAXL];
static int np = 0;
static char noms[200][32];
static long long vals[200];
static int nv = 0, err = 0;
static char msg[128];
static void lexe(const char *s, Instr *x) {
    while (*s) {
        if (isspace((unsigned char)*s)) { ++s; continue; }
        int n = 0;
        if (isalnum((unsigned char)*s) || *s == '_') while (isalnum((unsigned char)*s) || *s == '_') x->tok[x->nt][n++] = *s++;
        else if (strchr("=!<>", *s) && s[1] == '=') { x->tok[x->nt][n++] = *s++; x->tok[x->nt][n++] = *s++; }
        else x->tok[x->nt][n++] = *s++;
        x->tok[x->nt++][n] = '\0';
    }
}
static Instr *cur;
static int pos;
static const char *voir(void) { return pos < cur->nt ? cur->tok[pos] : ""; }
static long long comparaison(void);
static long long atome(void) {
    if (err) return 0;
    const char *x = cur->tok[pos++];
    if (!strcmp(x, "-")) return -atome();
    if (!strcmp(x, "(")) { long long v = comparaison(); ++pos; return v; }
    if (isdigit((unsigned char)x[0])) return atoll(x);
    for (int i = 0; i < nv; ++i) if (!strcmp(noms[i], x)) return vals[i];
    err = 1;
    snprintf(msg, sizeof msg, "erreur ligne %d: variable inconnue %s", cur->ligne, x);
    return 0;
}
static long long produit(void) {
    long long v = atome();
    while (!err && (!strcmp(voir(), "*") || !strcmp(voir(), "/") || !strcmp(voir(), "%"))) {
        char o = cur->tok[pos++][0];
        long long r = atome();
        if (err) return 0;
        if (o == '*') v *= r;
        else if (r == 0) { err = 1; snprintf(msg, sizeof msg, "erreur ligne %d: division par zéro", cur->ligne); return 0; }
        else v = o == '/' ? v / r : v % r;
    }
    return v;
}
static long long somme(void) {
    long long v = produit();
    while (!err && (!strcmp(voir(), "+") || !strcmp(voir(), "-"))) {
        char o = cur->tok[pos++][0];
        long long r = produit();
        v = o == '+' ? v + r : v - r;
    }
    return v;
}
static long long comparaison(void) {
    long long v = somme();
    const char *o = voir();
    if (!err && (!strcmp(o, "==") || !strcmp(o, "!=") || !strcmp(o, "<") || !strcmp(o, ">") || !strcmp(o, "<=") || !strcmp(o, ">="))) {
        char op[3];
        strcpy(op, o);
        ++pos;
        long long r = somme();
        v = !strcmp(op, "==") ? v == r : !strcmp(op, "!=") ? v != r : !strcmp(op, "<") ? v < r : !strcmp(op, ">") ? v > r : !strcmp(op, "<=") ? v <= r : v >= r;
    }
    return v;
}
static long long evalue(Instr *x) { cur = x; pos = 0; return comparaison(); }
int main(void) {
    static char l[1024];
    int pile[MAXL], np_pile = 0, num = 0;
    while (fgets(l, sizeof l, stdin)) {
        ++num;
        char *s = l;
        while (isspace((unsigned char)*s)) ++s;
        s[strcspn(s, "\r\n")] = '\0';
        if (!*s || *s == '#') continue;
        Instr *x = &prog[np];
        x->ligne = num;
        char mot[32] = "";
        sscanf(s, "%31s", mot);
        if (!strcmp(mot, "print")) { x->type = PRINT; lexe(s + 5, x); }
        else if (!strcmp(mot, "if")) { x->type = IF; lexe(s + 2, x); pile[np_pile++] = np; }
        else if (!strcmp(mot, "while")) { x->type = WHILE; lexe(s + 5, x); pile[np_pile++] = np; }
        else if (!strcmp(mot, "else")) { x->type = ELSE; prog[pile[np_pile - 1]].saut = np; pile[np_pile - 1] = np; }
        else if (!strcmp(mot, "end")) {
            x->type = END;
            int o = pile[--np_pile];
            prog[o].saut = np;
            x->saut = prog[o].type == WHILE ? o : -1;      /* fin de boucle : on remonte au while */
        } else {
            char *eg = strchr(s, '=');
            x->type = AFFECT;
            *eg = '\0';
            sscanf(s, "%31s", x->var);
            lexe(eg + 1, x);
        }
        ++np;
    }
    for (int pc = 0; pc < np && !err;) {
        Instr *x = &prog[pc];
        if (x->type == PRINT) { long long v = evalue(x); if (!err) printf("%lld\n", v); ++pc; }
        else if (x->type == AFFECT) {
            long long v = evalue(x);
            if (err) break;
            int i = 0;
            while (i < nv && strcmp(noms[i], x->var)) ++i;
            if (i == nv) strcpy(noms[nv++], x->var);
            vals[i] = v;
            ++pc;
        } else if (x->type == IF || x->type == WHILE) { long long v = evalue(x); if (err) break; pc = v ? pc + 1 : x->saut + 1; }
        else if (x->type == ELSE) pc = x->saut + 1;
        else pc = x->saut >= 0 ? x->saut : pc + 1;
    }
    if (err) puts(msg);
    return 0;
}""", "cpp": r"""
#include <cctype>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <vector>
struct Erreur { std::string msg; };
struct Instr {
    std::string type, var;
    int ligne = 0;
    std::vector<std::string> expr;
    std::vector<Instr> corps, sinon;
};
std::vector<std::string> lignes;
std::map<std::string, long long> vars;
std::vector<std::string> lexe(const std::string& s) {
    std::vector<std::string> t;
    for (size_t i = 0; i < s.size();) {
        if (std::isspace((unsigned char)s[i])) { ++i; continue; }
        size_t j = i;
        if (std::isalnum((unsigned char)s[i]) || s[i] == '_') while (j < s.size() && (std::isalnum((unsigned char)s[j]) || s[j] == '_')) ++j;
        else if (std::string("=!<>").find(s[i]) != std::string::npos && i + 1 < s.size() && s[i + 1] == '=') j += 2;
        else ++j;
        t.push_back(s.substr(i, j - i));
        i = j;
    }
    return t;
}
std::string premier_mot(const std::string& l) { std::istringstream in(l); std::string m; in >> m; return m; }
std::string nettoie(std::string l) {
    while (!l.empty() && std::isspace((unsigned char)l.back())) l.pop_back();
    size_t d = l.find_first_not_of(" \t");
    return d == std::string::npos ? "" : l.substr(d);
}
std::vector<Instr> analyse(size_t& i, const std::vector<std::string>& fin) {
    std::vector<Instr> r;
    while (i < lignes.size()) {
        std::string l = nettoie(lignes[i]), m = premier_mot(l);
        if (l.empty() || l[0] == '#') { ++i; continue; }
        for (auto& f : fin) if (m == f) return r;
        Instr x;
        x.ligne = (int)i + 1;
        if (m == "print") { x.type = "print"; x.expr = lexe(l.substr(5)); ++i; }
        else if (m == "if" || m == "while") {
            x.type = m;
            x.expr = lexe(l.substr(m.size()));
            ++i;
            x.corps = analyse(i, {"else", "end"});
            if (m == "if" && nettoie(lignes[i]) == "else") { ++i; x.sinon = analyse(i, {"end"}); }
            ++i;
        } else {
            size_t eg = l.find('=');
            x.type = "=";
            std::istringstream(l.substr(0, eg)) >> x.var;
            x.expr = lexe(l.substr(eg + 1));
            ++i;
        }
        r.push_back(std::move(x));
    }
    return r;
}
struct Eval {
    const std::vector<std::string>& t;
    int ligne;
    size_t p = 0;
    std::string voir() { return p < t.size() ? t[p] : ""; }
    long long atome() {
        std::string x = t[p++];
        if (x == "-") return -atome();
        if (x == "(") { long long v = comparaison(); ++p; return v; }
        if (std::isdigit((unsigned char)x[0])) return std::stoll(x);
        auto it = vars.find(x);
        if (it == vars.end()) throw Erreur{"erreur ligne " + std::to_string(ligne) + ": variable inconnue " + x};
        return it->second;
    }
    long long produit() {
        long long v = atome();
        while (voir() == "*" || voir() == "/" || voir() == "%") {
            std::string o = t[p++];
            long long r = atome();
            if (o == "*") v *= r;
            else if (r == 0) throw Erreur{"erreur ligne " + std::to_string(ligne) + ": division par zéro"};
            else v = o == "/" ? v / r : v % r;
        }
        return v;
    }
    long long somme() {
        long long v = produit();
        while (voir() == "+" || voir() == "-") { std::string o = t[p++]; long long r = produit(); v = o == "+" ? v + r : v - r; }
        return v;
    }
    long long comparaison() {
        long long v = somme();
        std::string o = voir();
        if (o == "==" || o == "!=" || o == "<" || o == ">" || o == "<=" || o == ">=") {
            ++p;
            long long r = somme();
            v = o == "==" ? v == r : o == "!=" ? v != r : o == "<" ? v < r : o == ">" ? v > r : o == "<=" ? v <= r : v >= r;
        }
        return v;
    }
};
long long evalue(const Instr& x) { Eval e{x.expr, x.ligne}; return e.comparaison(); }
void execute(const std::vector<Instr>& b) {
    for (auto& x : b) {
        if (x.type == "print") std::cout << evalue(x) << "\n";
        else if (x.type == "=") vars[x.var] = evalue(x);
        else if (x.type == "if") execute(evalue(x) ? x.corps : x.sinon);
        else while (evalue(x)) execute(x.corps);
    }
}
int main() {
    std::string l;
    while (std::getline(std::cin, l)) lignes.push_back(l);
    size_t i = 0;
    auto prog = analyse(i, {});
    try { execute(prog); } catch (const Erreur& e) { std::cout << e.msg << "\n"; }
}""", "javascript": r"""
const lignes = require("fs").readFileSync(0, "utf8").split("\n");
const LEX = /\d+|[a-z_][a-z0-9_]*|==|!=|<=|>=|[-+*\/%()<>]/g;
const lexe = s => s.match(LEX) || [];
class Erreur { constructor(msg) { this.msg = msg; } }
let i = 0;
const analyse = fin => {
  const r = [];
  while (i < lignes.length) {
    const l = lignes[i].trim(), m = l.split(/\s+/)[0];
    if (!l || l.startsWith("#")) { i++; continue; }
    if (fin.includes(m)) return r;
    const x = { ligne: i + 1 };
    if (m === "print") { x.type = "print"; x.expr = lexe(l.slice(5)); i++; }
    else if (m === "if" || m === "while") {
      x.type = m;
      x.expr = lexe(l.slice(m.length));
      i++;
      x.corps = analyse(["else", "end"]);
      x.sinon = [];
      if (m === "if" && lignes[i].trim() === "else") { i++; x.sinon = analyse(["end"]); }
      i++;
    } else {
      const eg = l.indexOf("=");
      x.type = "=";
      x.var = l.slice(0, eg).trim();
      x.expr = lexe(l.slice(eg + 1));
      i++;
    }
    r.push(x);
  }
  return r;
};
const vars = new Map();
const evalue = x => {
  const t = x.expr;
  let p = 0;
  const atome = () => {
    const s = t[p++];
    if (s === "-") return -atome();
    if (s === "(") { const v = comparaison(); p++; return v; }
    if (/^\d/.test(s)) return BigInt(s);
    if (!vars.has(s)) throw new Erreur(`erreur ligne ${x.ligne}: variable inconnue ${s}`);
    return vars.get(s);
  };
  const produit = () => {
    let v = atome();
    while (t[p] === "*" || t[p] === "/" || t[p] === "%") {
      const o = t[p++], r = atome();
      if (o === "*") v *= r;
      else if (r === 0n) throw new Erreur(`erreur ligne ${x.ligne}: division par zéro`);
      else v = o === "/" ? v / r : v % r;
    }
    return v;
  };
  const somme = () => {
    let v = produit();
    while (t[p] === "+" || t[p] === "-") { const o = t[p++], r = produit(); v = o === "+" ? v + r : v - r; }
    return v;
  };
  const comparaison = () => {
    let v = somme();
    const o = t[p];
    if (["==", "!=", "<", ">", "<=", ">="].includes(o)) {
      p++;
      const r = somme();
      v = ({ "==": v === r, "!=": v !== r, "<": v < r, ">": v > r, "<=": v <= r, ">=": v >= r })[o] ? 1n : 0n;
    }
    return v;
  };
  return comparaison();
};
const out = [];
const execute = b => {
  for (const x of b) {
    if (x.type === "print") out.push(evalue(x).toString());
    else if (x.type === "=") vars.set(x.var, evalue(x));
    else if (x.type === "if") execute(evalue(x) !== 0n ? x.corps : x.sinon);
    else while (evalue(x) !== 0n) execute(x.corps);
  }
};
const prog = analyse([]);
try { execute(prog); } catch (e) { if (!(e instanceof Erreur)) throw e; out.push(e.msg); }
console.log(out.join("\n"));""", "php": r"""
<?php
$lignes = explode("\n", stream_get_contents(STDIN));
class Erreur extends Exception {}
function lexe(string $s): array { preg_match_all('/\d+|[a-z_][a-z0-9_]*|==|!=|<=|>=|[-+*\/%()<>]/', $s, $m); return $m[0]; }
function analyse(array $lignes, int &$i, array $fin): array {
    $r = [];
    while ($i < count($lignes)) {
        $l = trim($lignes[$i]);
        $m = $l === '' ? '' : preg_split('/\s+/', $l)[0];
        if ($l === '' || $l[0] === '#') { $i++; continue; }
        if (in_array($m, $fin, true)) return $r;
        $x = ['ligne' => $i + 1];
        if ($m === 'print') { $x['type'] = 'print'; $x['expr'] = lexe(substr($l, 5)); $i++; }
        elseif ($m === 'if' || $m === 'while') {
            $x['type'] = $m;
            $x['expr'] = lexe(substr($l, strlen($m)));
            $i++;
            $x['corps'] = analyse($lignes, $i, ['else', 'end']);
            $x['sinon'] = [];
            if ($m === 'if' && trim($lignes[$i]) === 'else') { $i++; $x['sinon'] = analyse($lignes, $i, ['end']); }
            $i++;
        } else {
            $eg = strpos($l, '=');
            $x['type'] = '=';
            $x['var'] = trim(substr($l, 0, $eg));
            $x['expr'] = lexe(substr($l, $eg + 1));
            $i++;
        }
        $r[] = $x;
    }
    return $r;
}
class Evaluateur {
    private int $p = 0;
    public function __construct(private array $t, private int $ligne, private array $vars) {}
    private function voir(): string { return $this->t[$this->p] ?? ''; }
    private function atome(): int {
        $s = $this->t[$this->p++];
        if ($s === '-') return -$this->atome();
        if ($s === '(') { $v = $this->comparaison(); $this->p++; return $v; }
        if (ctype_digit($s)) return (int) $s;
        if (!array_key_exists($s, $this->vars)) throw new Erreur("erreur ligne {$this->ligne}: variable inconnue $s");
        return $this->vars[$s];
    }
    private function produit(): int {
        $v = $this->atome();
        while (in_array($this->voir(), ['*', '/', '%'], true)) {
            $o = $this->t[$this->p++];
            $r = $this->atome();
            if ($o === '*') { $v *= $r; continue; }
            if ($r === 0) throw new Erreur("erreur ligne {$this->ligne}: division par zéro");
            $v = $o === '/' ? intdiv($v, $r) : $v % $r;
        }
        return $v;
    }
    private function somme(): int {
        $v = $this->produit();
        while (in_array($this->voir(), ['+', '-'], true)) { $o = $this->t[$this->p++]; $r = $this->produit(); $v = $o === '+' ? $v + $r : $v - $r; }
        return $v;
    }
    public function comparaison(): int {
        $v = $this->somme();
        $o = $this->voir();
        if (in_array($o, ['==', '!=', '<', '>', '<=', '>='], true)) {
            $this->p++;
            $r = $this->somme();
            $v = (int) match ($o) { '==' => $v === $r, '!=' => $v !== $r, '<' => $v < $r, '>' => $v > $r, '<=' => $v <= $r, '>=' => $v >= $r };
        }
        return $v;
    }
}
$vars = [];
function evalue(array $x, array &$vars): int { return (new Evaluateur($x['expr'], $x['ligne'], $vars))->comparaison(); }
function execute(array $b, array &$vars): void {
    foreach ($b as $x) {
        if ($x['type'] === 'print') echo evalue($x, $vars), "\n";
        elseif ($x['type'] === '=') $vars[$x['var']] = evalue($x, $vars);
        elseif ($x['type'] === 'if') execute(evalue($x, $vars) ? $x['corps'] : $x['sinon'], $vars);
        else while (evalue($x, $vars)) execute($x['corps'], $vars);
    }
}
$i = 0;
$prog = analyse($lignes, $i, []);
try { execute($prog, $vars); } catch (Erreur $e) { echo $e->getMessage(), "\n"; }"""}, minutes=90, time=3),
]
