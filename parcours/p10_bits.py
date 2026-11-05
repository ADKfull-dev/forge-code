# -*- coding: utf-8 -*-
"""Palier 10 — Bits, encodages et texte : bit à bit, chiffrement, compression, UTF-8, motifs."""
from .base import ch, lines


def _rand(n, lo, hi, seed=1):
    x, out = seed, []
    for _ in range(n):
        x = (x * 6364136223846793005 + 1442695040888963407) % 2 ** 64
        out.append(lo + (x >> 33) % (hi - lo + 1))
    return out


def _hex(s):
    return " ".join(f"{b:02X}" for b in s.encode("utf-8"))


_UTF = ["Aé€😀", "Forge Code", "ça marche à 100 %", "日本語", "🚀🔥👑", "ÿĀ߿ࠀ￿\U00010000\U0010ffff"]
_UTF_BAD = ["C3", "80", "C0 AF", "E0 80 AF", "ED A0 80", "F4 90 80 80", "F8 88 80 80 80", "E2 82", "41 C3 28", "FF"]
_B64 = ["Forge", "a", "ab", "abc", "Bonjour tout le monde !", "", "The quick brown fox jumps over the lazy dog 0123456789+/=", "~~~???>>>"]
_LUHN = ["4539 1488 0343 6467", "8273 1232 7352 0569", "0", "059", "79927398713", "79927398710", "4539 1488 0343 6468", "1234-5678", " 4 5 3 9 ", "00", "4111111111111111", "49927398716"]
_REGEX = [("abc", "xxabcxx"), ("^abc", "xxabc"), ("abc$", "xxabc"), ("a.c", "abc"), ("a.c", "ac"), ("ab*c", "ac"), ("ab*c", "abbbbc"), ("ab+c", "ac"), ("ab+c", "abbc"),
          ("colou?r", "color"), ("colou?r", "colour"), ("colou?r", "colouur"), ("^a.*z$", "abcz"), ("^a.*z$", "abczy"), ("^$", ""), ("x*", "abc"), ("^.+$", ""),
          ("^h.?llo w.+d$", "hello world"), ("^h.?llo w.+d$", "hllo wd"), ("a*a*a*b", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaab"), ("^[0-9]$", "[0-9]"), ("o+", "forge code"),
          ("^f.r.e c.d.$", "forge code"), ("z?z?z?", ""), ("^ab?c*d+e$", "adddde"), ("^ab?c*d+e$", "abcce")]


def _regex_in(pairs):
    return f"{len(pairs)}\n" + lines(f"{p}\n{t}" for p, t in pairs)


def _joker_in(motif, mots):
    return f"{motif}\n{len(mots)}\n" + lines(mots)


def _gros_joker():
    r = _rand(40 * 400, 0, 2, 5)
    mots = ["".join("abc"[r[i * 400 + j]] for j in range(400)) for i in range(40)]
    return _joker_in("a*b?c*a*c*b*a?c*b", mots)


DEFIS = [
    ch("bits", 10, "mini", "Jeux de bits", "bit à bit",
       "Ligne 1 : t. Puis t entiers n (0 ≤ n < 2^63). Pour chacun, affichez « p d h » : p le nombre de bits à 1, d « oui » si n est une puissance "
       "de 2 (sinon « non »), h la position du bit à 1 le plus fort (0 pour le bit des unités, -1 si n = 0). Contrainte : pas de fonction toute faite.",
       [("4\n5\n8\n0\n1", "2 non 2\n1 oui 3\n0 non -1\n1 oui 0"), ("2\n9223372036854775807\n4611686018427387904", "63 non 62\n1 oui 62"),
        "8\n255\n256\n1023\n1024\n6\n12345678901234\n3\n2",
        lambda: "1000\n" + lines(_rand(1000, 0, 2 ** 63 - 1, 3))],
       ["n & 1 donne le bit des unités ; n >> 1 décale n d'un bit vers la droite.",
        "Astuce : n & (n - 1) efface le bit à 1 le plus faible. Une puissance de 2 n'a qu'un seul bit à 1 : n > 0 et n & (n - 1) == 0.",
        "Pour le bit le plus fort : décalez vers la droite en comptant jusqu'à ce que n vaille 0. En JavaScript, BigInt (les opérateurs bit à bit des Number sont sur 32 bits !)."],
       {"python": r"""
t = int(input())
for _ in range(t):
    n = int(input())
    p, x = 0, n
    while x:
        x &= x - 1
        p += 1
    h, x = -1, n
    while x:
        x >>= 1
        h += 1
    print(p, "oui" if n > 0 and n & (n - 1) == 0 else "non", h)""", "c": r"""
#include <stdio.h>
int main(void) {
    int t;
    if (scanf("%d", &t) != 1) return 1;
    while (t-- > 0) {
        unsigned long long n, x;
        if (scanf("%llu", &n) != 1) return 1;
        int p = 0, h = -1;
        for (x = n; x; x &= x - 1) ++p;
        for (x = n; x; x >>= 1) ++h;
        printf("%d %s %d\n", p, n && !(n & (n - 1)) ? "oui" : "non", h);
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
int main() {
    int t;
    std::cin >> t;
    while (t-- > 0) {
        unsigned long long n, x;
        std::cin >> n;
        int p = 0, h = -1;
        for (x = n; x; x &= x - 1) ++p;
        for (x = n; x; x >>= 1) ++h;
        std::cout << p << (n && !(n & (n - 1)) ? " oui " : " non ") << h << "\n";
    }
}""", "javascript": r"""
const v = require("fs").readFileSync(0, "utf8").trim().split(/\s+/);
const out = [];
for (let i = 1; i <= Number(v[0]); i++) {
  const n = BigInt(v[i]);
  let p = 0, h = -1, x;
  for (x = n; x; x &= x - 1n) p++;
  for (x = n; x; x >>= 1n) h++;
  out.push(`${p} ${n > 0n && (n & (n - 1n)) === 0n ? "oui" : "non"} ${h}`);
}
console.log(out.join("\n"));""", "php": r"""
<?php
$t = (int) trim(fgets(STDIN));
for ($k = 0; $k < $t; $k++) {
    $n = (int) trim(fgets(STDIN));
    $p = 0; $h = -1;
    for ($x = $n; $x; $x &= $x - 1) $p++;
    for ($x = $n; $x; $x >>= 1) $h++;
    echo $p, " ", $n > 0 && ($n & ($n - 1)) === 0 ? "oui" : "non", " ", $h, "\n";
}"""}, banned={"python": [r"bit_count", r"bit_length", r"\bbin\s*\(", r"format\s*\("], "c": [r"__builtin"], "cpp": [r"__builtin", r"popcount", r"bit_width", r"bitset", r"countl"],
                "php": [r"decbin", r"substr_count"], "javascript": [r"toString\s*\(\s*2"]}),

    ch("cesar", 10, "mini", "Le chiffre de César", "chiffrement",
       "Ligne 1 : « C k » pour chiffrer ou « D k » pour déchiffrer, avec un décalage k (entier, éventuellement négatif ou très grand). Ligne 2 : un texte ASCII. "
       "Décalez chaque lettre de k positions dans l'alphabet (en bouclant après Z, majuscules et minuscules conservées) ; les autres caractères ne changent pas.",
       [("C 3\nBonjour, le monde !", "Erqmrxu, oh prqgh !"), ("D 3\nErqmrxu, oh prqgh !", "Bonjour, le monde !"), ("C 26\nForge", "Forge"),
        ("C -1\nabc XYZ", "zab WXY"), ("D 1000000001\nForge Code 2026", None), ("C 13\nThe Quick Brown Fox Jumps Over The Lazy Dog", None)],
       ["Pour une minuscule c : ((c - 'a' + k) mod 26) + 'a'. Même chose avec 'A' pour les majuscules.",
        "Déchiffrer, c'est chiffrer avec -k.", "Ramenez k entre 0 et 25 : ((k % 26) + 26) % 26, sinon le modulo d'un négatif vous jouera des tours."],
       {"python": r"""
m, k = input().split()
k = int(k) % 26
if m == "D":
    k = (26 - k) % 26
out = []
for c in input():
    if "a" <= c <= "z":
        out.append(chr((ord(c) - 97 + k) % 26 + 97))
    elif "A" <= c <= "Z":
        out.append(chr((ord(c) - 65 + k) % 26 + 65))
    else:
        out.append(c)
print("".join(out))""", "c": r"""
#include <stdio.h>
#include <string.h>
int main(void) {
    char m[4], s[4096] = "";
    long long k;
    if (scanf("%3s %lld", m, &k) != 2) return 1;
    int d = (int)(((k % 26) + 26) % 26);
    if (m[0] == 'D') d = (26 - d) % 26;
    getchar();
    if (!fgets(s, sizeof s, stdin)) s[0] = '\0';
    s[strcspn(s, "\r\n")] = '\0';
    for (char *p = s; *p; ++p) {
        if (*p >= 'a' && *p <= 'z') *p = (char)((*p - 'a' + d) % 26 + 'a');
        else if (*p >= 'A' && *p <= 'Z') *p = (char)((*p - 'A' + d) % 26 + 'A');
    }
    puts(s);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
int main() {
    std::string m, s;
    long long k;
    std::cin >> m >> k;
    std::getline(std::cin, s);
    std::getline(std::cin, s);
    int d = (int)(((k % 26) + 26) % 26);
    if (m == "D") d = (26 - d) % 26;
    for (char& c : s) {
        if (c >= 'a' && c <= 'z') c = char((c - 'a' + d) % 26 + 'a');
        else if (c >= 'A' && c <= 'Z') c = char((c - 'A' + d) % 26 + 'A');
    }
    std::cout << s << "\n";
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const [m, ks] = L[0].trim().split(/\s+/);
let d = ((Number(BigInt(ks) % 26n)) + 26) % 26;
if (m === "D") d = (26 - d) % 26;
const out = [...(L[1] || "").replace(/\r$/, "")].map(c => {
  const x = c.charCodeAt(0);
  if (x >= 97 && x <= 122) return String.fromCharCode((x - 97 + d) % 26 + 97);
  if (x >= 65 && x <= 90) return String.fromCharCode((x - 65 + d) % 26 + 65);
  return c;
});
console.log(out.join(""));""", "php": r"""
<?php
[$m, $k] = explode(' ', trim(fgets(STDIN)));
$d = (((int) $k % 26) + 26) % 26;
if ($m === 'D') $d = (26 - $d) % 26;
$s = rtrim((string) fgets(STDIN), "\r\n");
for ($i = 0; $i < strlen($s); $i++) {
    $x = ord($s[$i]);
    if ($x >= 97 && $x <= 122) $s[$i] = chr(($x - 97 + $d) % 26 + 97);
    elseif ($x >= 65 && $x <= 90) $s[$i] = chr(($x - 65 + $d) % 26 + 65);
}
echo $s, "\n";"""}),

    ch("vigenere", 10, "mini", "Le chiffre de Vigenère", "chiffrement",
       "Ligne 1 : « C clé » ou « D clé » (la clé est un mot de lettres). Ligne 2 : un texte ASCII. Chaque LETTRE du texte est décalée (comme César) de la "
       "position dans l'alphabet de la lettre de clé courante (a ou A = 0, b = 1…) ; la clé avance d'un cran à chaque lettre chiffrée et recommence au début. "
       "Les autres caractères restent tels quels et ne font pas avancer la clé.",
       [("C cle\nForge Code", "Hzvip Gqoi"), ("D cle\nHzvip Gqoi", "Forge Code"), ("C a\nRien ne change.", "Rien ne change."),
        ("C LEMON\nattack at dawn", "lxfopv ef rnhr"), ("D LeMoN\nlxfopv ef rnhr !", "attack at dawn !"), ("C zzz\nabc ABC xyz", None)],
       ["Gardez un indice j dans la clé, qui n'avance que lorsque le caractère traité est une lettre.",
        "Décalage = (clé[j mod longueur] en minuscule) - 'a'. Pour déchiffrer, décalez de 26 - décalage.",
        "Réutilisez votre fonction de décalage d'une lettre écrite pour César."],
       {"python": r"""
m, cle = input().split()
cle = cle.lower()
j, out = 0, []
for c in input():
    if c.isascii() and c.isalpha():
        d = ord(cle[j % len(cle)]) - 97
        if m == "D":
            d = (26 - d) % 26
        base = 97 if c.islower() else 65
        out.append(chr((ord(c) - base + d) % 26 + base))
        j += 1
    else:
        out.append(c)
print("".join(out))""", "c": r"""
#include <stdio.h>
#include <string.h>
#include <ctype.h>
int main(void) {
    char m[4], cle[256], s[4096] = "";
    if (scanf("%3s %255s", m, cle) != 2) return 1;
    getchar();
    if (!fgets(s, sizeof s, stdin)) s[0] = '\0';
    s[strcspn(s, "\r\n")] = '\0';
    size_t n = strlen(cle), j = 0;
    for (char *p = s; *p; ++p) {
        if (!isalpha((unsigned char)*p)) continue;
        int d = tolower((unsigned char)cle[j++ % n]) - 'a';
        if (m[0] == 'D') d = (26 - d) % 26;
        char base = islower((unsigned char)*p) ? 'a' : 'A';
        *p = (char)((*p - base + d) % 26 + base);
    }
    puts(s);
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
#include <cctype>
int main() {
    std::string m, cle, s;
    std::cin >> m >> cle;
    std::getline(std::cin, s);
    std::getline(std::cin, s);
    size_t j = 0;
    for (char& c : s) {
        if (!std::isalpha((unsigned char)c)) continue;
        int d = std::tolower((unsigned char)cle[j++ % cle.size()]) - 'a';
        if (m == "D") d = (26 - d) % 26;
        char base = std::islower((unsigned char)c) ? 'a' : 'A';
        c = char((c - base + d) % 26 + base);
    }
    std::cout << s << "\n";
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const [m, k] = L[0].trim().split(/\s+/), cle = k.toLowerCase();
let j = 0;
const out = [...(L[1] || "").replace(/\r$/, "")].map(c => {
  if (!/[a-zA-Z]/.test(c)) return c;
  let d = cle.charCodeAt(j++ % cle.length) - 97;
  if (m === "D") d = (26 - d) % 26;
  const base = c >= "a" ? 97 : 65;
  return String.fromCharCode((c.charCodeAt(0) - base + d) % 26 + base);
});
console.log(out.join(""));""", "php": r"""
<?php
[$m, $cle] = explode(' ', trim(fgets(STDIN)));
$cle = strtolower($cle);
$s = rtrim((string) fgets(STDIN), "\r\n");
$j = 0;
for ($i = 0; $i < strlen($s); $i++) {
    if (!ctype_alpha($s[$i])) continue;
    $d = ord($cle[$j++ % strlen($cle)]) - 97;
    if ($m === 'D') $d = (26 - $d) % 26;
    $base = ctype_lower($s[$i]) ? 97 : 65;
    $s[$i] = chr((ord($s[$i]) - $base + $d) % 26 + $base);
}
echo $s, "\n";"""}),

    ch("rle", 10, "mini", "Compression RLE", "compression",
       "Ligne 1 : « C » pour compresser ou « D » pour décompresser. Ligne 2 : le texte. Compresser : chaque suite de caractères identiques devient "
       "« nombre caractère » (« aaabcc » → « 3a1b2c »). Décompresser fait l'inverse (« 12a1b » → douze « a » puis « b »). Le texte d'origine ne contient pas de chiffres.",
       [("C\naaabcc", "3a1b2c"), ("D\n3a1b2c", "aaabcc"), ("C\nabc", "1a1b1c"), ("D\n12x1y", "xxxxxxxxxxxxy"), ("C\nWWWWWWWWWWWWBWWWWWWWWWWWWBBBWWWWWWWWWWWWWWWWWWWWWWWWBWWWWWWWWWWWWWW", None),
        ("C\n" + "z" * 1000 + "Z", "1000z1Z"), ("D\n1000z1Z", "z" * 1000 + "Z"), ("C\n  --  ", "2 2-2 ")],
       ["Compression : parcourez le texte en comptant combien de fois le caractère courant se répète ; à chaque changement, écrivez le compte et le caractère.",
        "Décompression : lisez les chiffres pour former un nombre (n = n × 10 + chiffre), puis le caractère qui suit : répétez-le n fois et remettez n à 0.",
        "N'oubliez pas la dernière suite en fin de ligne. Construisez le résultat dans un tampon plutôt que par concaténations répétées."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
m, s = L[0].strip(), L[1] if len(L) > 1 else ""
out = []
if m == "C":
    i = 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i]:
            j += 1
        out.append(f"{j - i}{s[i]}")
        i = j
else:
    n = 0
    for c in s:
        if c.isdigit():
            n = n * 10 + int(c)
        else:
            out.append(c * n)
            n = 0
print("".join(out))""", "c": r"""
#include <stdio.h>
#include <string.h>
int main(void) {
    char m[8];
    static char s[1 << 20];
    if (!fgets(m, sizeof m, stdin)) return 1;
    if (!fgets(s, sizeof s, stdin)) s[0] = '\0';
    s[strcspn(s, "\r\n")] = '\0';
    size_t len = strlen(s);
    if (m[0] == 'C') {
        for (size_t i = 0, j; i < len; i = j) {
            for (j = i; j < len && s[j] == s[i]; ++j) {}
            printf("%zu%c", j - i, s[i]);
        }
    } else {
        long n = 0;
        for (size_t i = 0; i < len; ++i) {
            if (s[i] >= '0' && s[i] <= '9') n = n * 10 + (s[i] - '0');
            else { while (n-- > 0) putchar(s[i]); n = 0; }
        }
    }
    putchar('\n');
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
int main() {
    std::string m, s, out;
    std::getline(std::cin, m);
    std::getline(std::cin, s);
    if (!s.empty() && s.back() == '\r') s.pop_back();
    if (m[0] == 'C') {
        for (size_t i = 0, j; i < s.size(); i = j) {
            for (j = i; j < s.size() && s[j] == s[i]; ++j) {}
            out += std::to_string(j - i) + s[i];
        }
    } else {
        size_t n = 0;
        for (char c : s) {
            if (c >= '0' && c <= '9') n = n * 10 + (c - '0');
            else { out.append(n, c); n = 0; }
        }
    }
    std::cout << out << "\n";
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const m = L[0].trim(), s = (L[1] || "").replace(/\r$/, "");
const out = [];
if (m === "C") {
  for (let i = 0, j; i < s.length; i = j) {
    for (j = i; j < s.length && s[j] === s[i]; j++);
    out.push(`${j - i}${s[i]}`);
  }
} else {
  let n = 0;
  for (const c of s) {
    if (c >= "0" && c <= "9") n = n * 10 + Number(c);
    else { out.push(c.repeat(n)); n = 0; }
  }
}
console.log(out.join(""));""", "php": r"""
<?php
$m = trim(fgets(STDIN));
$s = rtrim((string) fgets(STDIN), "\r\n");
$out = '';
$len = strlen($s);
if ($m === 'C') {
    for ($i = 0; $i < $len; $i = $j) {
        for ($j = $i; $j < $len && $s[$j] === $s[$i]; $j++);
        $out .= ($j - $i) . $s[$i];
    }
} else {
    $n = 0;
    for ($i = 0; $i < $len; $i++) {
        if (ctype_digit($s[$i])) $n = $n * 10 + (int) $s[$i];
        else { $out .= str_repeat($s[$i], $n); $n = 0; }
    }
}
echo $out, "\n";"""}),

    ch("base64", 10, "mini", "Base64", "encodage",
       "Ligne 1 : « E » (encoder) ou « D » (décoder). Ligne 2 : le texte ASCII à encoder, ou le Base64 à décoder. Base64 découpe les octets en "
       "paquets de 3 (24 bits), lus comme 4 groupes de 6 bits, chacun traduit par un caractère de « A-Z a-z 0-9 + / » ; on complète avec « = ». "
       "Contrainte : sans fonction Base64 toute faite.",
       [("E\nForge", "Rm9yZ2U="), ("D\nRm9yZ2U=", "Forge")] + [f"E\n{s}" for s in _B64] + ["D\nQm9uam91ciB0b3V0IGxlIG1vbmRlICE=", "D\nYWJj", "D\nYQ==", "D\nfn5+Pz8/Pj4+"],
       ["Encodage : pour chaque bloc de 3 octets a, b, c : n = a << 16 | b << 8 | c, puis les 4 indices (n >> 18) & 63, (n >> 12) & 63, (n >> 6) & 63, n & 63.",
        "Dernier bloc incomplet : 1 octet → 2 caractères + « == », 2 octets → 3 caractères + « = ».",
        "Décodage : l'inverse ; 4 caractères (sans les « = ») redonnent 3 octets, et chaque « = » retire un octet à la fin."],
       {"python": r"""
import sys
A = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
L = sys.stdin.read().split("\n")
m, s = L[0].strip(), L[1].rstrip("\r") if len(L) > 1 else ""
out = []
if m == "E":
    b = s.encode("latin-1")
    for i in range(0, len(b), 3):
        bloc = b[i:i + 3]
        n = int.from_bytes(bloc + b"\0" * (3 - len(bloc)), "big")
        car = [A[(n >> 18) & 63], A[(n >> 12) & 63], A[(n >> 6) & 63], A[n & 63]]
        out.append("".join(car[:len(bloc) + 1]) + "=" * (3 - len(bloc)))
    print("".join(out))
else:
    s = s.strip()
    octets = bytearray()
    for i in range(0, len(s), 4):
        bloc = s[i:i + 4]
        pad = bloc.count("=")
        n = 0
        for c in bloc:
            n = n * 64 + (0 if c == "=" else A.index(c))
        octets += n.to_bytes(3, "big")[:3 - pad]
    print(octets.decode("latin-1"))""", "c": r"""
#include <stdio.h>
#include <string.h>
static const char *A = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
int main(void) {
    char m[8];
    static char s[1 << 16];
    if (!fgets(m, sizeof m, stdin)) return 1;
    if (!fgets(s, sizeof s, stdin)) s[0] = '\0';
    s[strcspn(s, "\r\n")] = '\0';
    size_t len = strlen(s);
    if (m[0] == 'E') {
        for (size_t i = 0; i < len; i += 3) {
            size_t k = len - i < 3 ? len - i : 3;
            unsigned long n = 0;
            for (size_t j = 0; j < 3; ++j) n = n << 8 | (j < k ? (unsigned char)s[i + j] : 0);
            for (size_t j = 0; j < 4; ++j) putchar(j <= k ? A[(n >> (18 - 6 * j)) & 63] : '=');
        }
    } else {
        for (size_t i = 0; i < len; i += 4) {
            unsigned long n = 0;
            int pad = 0;
            for (size_t j = 0; j < 4; ++j) {
                char c = i + j < len ? s[i + j] : '=';
                if (c == '=') { ++pad; n <<= 6; }
                else n = n << 6 | (unsigned long)(strchr(A, c) - A);
            }
            for (int j = 0; j < 3 - pad; ++j) putchar((int)((n >> (16 - 8 * j)) & 255));
        }
    }
    putchar('\n');
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
int main() {
    const std::string A = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string m, s, out;
    std::getline(std::cin, m);
    std::getline(std::cin, s);
    if (!s.empty() && s.back() == '\r') s.pop_back();
    if (m[0] == 'E') {
        for (size_t i = 0; i < s.size(); i += 3) {
            size_t k = std::min<size_t>(3, s.size() - i);
            unsigned long n = 0;
            for (size_t j = 0; j < 3; ++j) n = n << 8 | (j < k ? (unsigned char)s[i + j] : 0);
            for (size_t j = 0; j < 4; ++j) out += j <= k ? A[(n >> (18 - 6 * j)) & 63] : '=';
        }
    } else {
        for (size_t i = 0; i < s.size(); i += 4) {
            unsigned long n = 0;
            int pad = 0;
            for (size_t j = 0; j < 4; ++j) {
                char c = i + j < s.size() ? s[i + j] : '=';
                if (c == '=') { ++pad; n <<= 6; } else n = n << 6 | A.find(c);
            }
            for (int j = 0; j < 3 - pad; ++j) out += char((n >> (16 - 8 * j)) & 255);
        }
    }
    std::cout << out << "\n";
}""", "javascript": r"""
const A = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
const L = require("fs").readFileSync(0, "utf8").split("\n");
const m = L[0].trim(), s = (L[1] || "").replace(/\r$/, "");
let out = "";
if (m === "E") {
  for (let i = 0; i < s.length; i += 3) {
    const k = Math.min(3, s.length - i);
    let n = 0;
    for (let j = 0; j < 3; j++) n = n * 256 + (j < k ? s.charCodeAt(i + j) : 0);
    for (let j = 0; j < 4; j++) out += j <= k ? A[(n >> (18 - 6 * j)) & 63] : "=";
  }
} else {
  for (let i = 0; i < s.length; i += 4) {
    let n = 0, pad = 0;
    for (let j = 0; j < 4; j++) {
      const c = s[i + j] || "=";
      if (c === "=") { pad++; n *= 64; } else n = n * 64 + A.indexOf(c);
    }
    for (let j = 0; j < 3 - pad; j++) out += String.fromCharCode((n >> (16 - 8 * j)) & 255);
  }
}
console.log(out);""", "php": r"""
<?php
$A = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
$m = trim(fgets(STDIN));
$s = rtrim((string) fgets(STDIN), "\r\n");
$out = '';
$len = strlen($s);
if ($m === 'E') {
    for ($i = 0; $i < $len; $i += 3) {
        $k = min(3, $len - $i);
        $n = 0;
        for ($j = 0; $j < 3; $j++) $n = $n << 8 | ($j < $k ? ord($s[$i + $j]) : 0);
        for ($j = 0; $j < 4; $j++) $out .= $j <= $k ? $A[($n >> (18 - 6 * $j)) & 63] : '=';
    }
} else {
    for ($i = 0; $i < $len; $i += 4) {
        $n = 0; $pad = 0;
        for ($j = 0; $j < 4; $j++) {
            $c = $i + $j < $len ? $s[$i + $j] : '=';
            if ($c === '=') { $pad++; $n <<= 6; } else $n = $n << 6 | strpos($A, $c);
        }
        for ($j = 0; $j < 3 - $pad; $j++) $out .= chr(($n >> (16 - 8 * $j)) & 255);
    }
}
echo $out, "\n";"""}, banned={"python": [r"base64", r"binascii", r"b64"], "javascript": [r"btoa", r"atob", r"Buffer", r"base64"], "php": [r"base64_"],
                             "c": [r"base64"], "cpp": [r"base64"]}),

    ch("utf8", 10, "mini", "Décodeur UTF-8", "encodage",
       "Chaque ligne contient des octets en hexadécimal (« C3 A9 41 »). Décodez-les en UTF-8 et affichez les points de code « U+00E9 U+0041 » "
       "(au moins 4 chiffres hexadécimaux, en majuscules), ou « invalide » si la suite d'octets n'est pas de l'UTF-8 correct : octet de "
       "continuation inattendu, séquence tronquée, encodage trop long (ex. C0 AF), point de code réservé aux substituts (D800-DFFF) ou au-delà de U+10FFFF.",
       [lines(_hex(s) for s in _UTF), lines(_UTF_BAD), lines(_hex(chr(c)) for c in range(0x20, 0x2000, 37)), "E2 82 AC F0 9F 98 80 C3 A9 20 7A"],
       ["Le premier octet indique la longueur : 0xxxxxxx (1 octet), 110xxxxx (2), 1110xxxx (3), 11110xxx (4). Les suivants sont de la forme 10xxxxxx.",
        "Point de code : les bits « x » du premier octet, puis 6 bits de chaque octet de continuation : cp = (cp << 6) | (octet & 0x3F).",
        "Encodage trop long : un point de code qui aurait tenu en moins d'octets (2 octets mais cp < 0x80, 3 mais < 0x800, 4 mais < 0x10000) est invalide."],
       {"python": r"""
import sys
for l in sys.stdin.read().split("\n"):
    if not l.strip():
        continue
    o = [int(x, 16) for x in l.split()]
    cps, i, ok = [], 0, True
    while i < len(o) and ok:
        b = o[i]
        if b < 0x80:
            n, cp, mini = 0, b, 0
        elif b >> 5 == 0b110:
            n, cp, mini = 1, b & 0x1F, 0x80
        elif b >> 4 == 0b1110:
            n, cp, mini = 2, b & 0x0F, 0x800
        elif b >> 3 == 0b11110:
            n, cp, mini = 3, b & 0x07, 0x10000
        else:
            ok = False
            break
        for k in range(1, n + 1):
            if i + k >= len(o) or o[i + k] >> 6 != 0b10:
                ok = False
                break
            cp = cp << 6 | (o[i + k] & 0x3F)
        if ok and (cp < mini or 0xD800 <= cp <= 0xDFFF or cp > 0x10FFFF):
            ok = False
        cps.append(cp)
        i += n + 1
    print(" ".join(f"U+{c:04X}" for c in cps) if ok else "invalide")""", "c": r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(void) {
    static char l[1 << 16];
    unsigned o[20000];
    while (fgets(l, sizeof l, stdin)) {
        int n = 0;
        for (char *t = strtok(l, " \r\n"); t; t = strtok(NULL, " \r\n")) o[n++] = (unsigned)strtoul(t, NULL, 16);
        if (n == 0) continue;
        static unsigned cps[20000];
        int nc = 0, ok = 1;
        for (int i = 0; i < n && ok;) {
            unsigned b = o[i], cp, mini;
            int k;
            if (b < 0x80) { k = 0; cp = b; mini = 0; }
            else if (b >> 5 == 6) { k = 1; cp = b & 0x1F; mini = 0x80; }
            else if (b >> 4 == 14) { k = 2; cp = b & 0x0F; mini = 0x800; }
            else if (b >> 3 == 30) { k = 3; cp = b & 0x07; mini = 0x10000; }
            else { ok = 0; break; }
            for (int j = 1; j <= k; ++j) {
                if (i + j >= n || o[i + j] >> 6 != 2) { ok = 0; break; }
                cp = cp << 6 | (o[i + j] & 0x3F);
            }
            if (ok && (cp < mini || (cp >= 0xD800 && cp <= 0xDFFF) || cp > 0x10FFFF)) ok = 0;
            cps[nc++] = cp;
            i += k + 1;
        }
        if (!ok) { puts("invalide"); continue; }
        for (int i = 0; i < nc; ++i) printf(i ? " U+%04X" : "U+%04X", cps[i]);
        printf("\n");
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <cstdio>
bool decode(const std::vector<unsigned>& o, std::vector<unsigned>& cps) {
    for (size_t i = 0; i < o.size();) {
        unsigned b = o[i], cp, mini;
        size_t k;
        if (b < 0x80) { k = 0; cp = b; mini = 0; }
        else if (b >> 5 == 6) { k = 1; cp = b & 0x1F; mini = 0x80; }
        else if (b >> 4 == 14) { k = 2; cp = b & 0x0F; mini = 0x800; }
        else if (b >> 3 == 30) { k = 3; cp = b & 0x07; mini = 0x10000; }
        else return false;
        for (size_t j = 1; j <= k; ++j) {
            if (i + j >= o.size() || o[i + j] >> 6 != 2) return false;
            cp = cp << 6 | (o[i + j] & 0x3F);
        }
        if (cp < mini || (cp >= 0xD800 && cp <= 0xDFFF) || cp > 0x10FFFF) return false;
        cps.push_back(cp);
        i += k + 1;
    }
    return true;
}
int main() {
    std::string l;
    while (std::getline(std::cin, l)) {
        std::istringstream in(l);
        std::vector<unsigned> o, cps;
        std::string t;
        while (in >> t) o.push_back((unsigned)std::stoul(t, nullptr, 16));
        if (o.empty()) continue;
        if (!decode(o, cps)) { std::cout << "invalide\n"; continue; }
        for (size_t i = 0; i < cps.size(); ++i) std::printf(i ? " U+%04X" : "U+%04X", cps[i]);
        std::printf("\n");
    }
}""", "javascript": r"""
const out = [];
for (const l of require("fs").readFileSync(0, "utf8").split("\n")) {
  if (!l.trim()) continue;
  const o = l.trim().split(/\s+/).map(x => parseInt(x, 16)), cps = [];
  let ok = true;
  for (let i = 0; i < o.length && ok;) {
    const b = o[i];
    let k, cp, mini;
    if (b < 0x80) [k, cp, mini] = [0, b, 0];
    else if (b >> 5 === 6) [k, cp, mini] = [1, b & 0x1f, 0x80];
    else if (b >> 4 === 14) [k, cp, mini] = [2, b & 0x0f, 0x800];
    else if (b >> 3 === 30) [k, cp, mini] = [3, b & 0x07, 0x10000];
    else { ok = false; break; }
    for (let j = 1; j <= k; j++) {
      if (i + j >= o.length || o[i + j] >> 6 !== 2) { ok = false; break; }
      cp = (cp << 6) | (o[i + j] & 0x3f);
    }
    if (ok && (cp < mini || (cp >= 0xd800 && cp <= 0xdfff) || cp > 0x10ffff)) ok = false;
    cps.push(cp);
    i += k + 1;
  }
  out.push(ok ? cps.map(c => "U+" + c.toString(16).toUpperCase().padStart(4, "0")).join(" ") : "invalide");
}
console.log(out.join("\n"));""", "php": r"""
<?php
while (($l = fgets(STDIN)) !== false) {
    if (trim($l) === '') continue;
    $o = array_map('hexdec', preg_split('/\s+/', trim($l)));
    $cps = [];
    $ok = true;
    $n = count($o);
    for ($i = 0; $i < $n && $ok;) {
        $b = $o[$i];
        if ($b < 0x80) [$k, $cp, $mini] = [0, $b, 0];
        elseif ($b >> 5 === 6) [$k, $cp, $mini] = [1, $b & 0x1F, 0x80];
        elseif ($b >> 4 === 14) [$k, $cp, $mini] = [2, $b & 0x0F, 0x800];
        elseif ($b >> 3 === 30) [$k, $cp, $mini] = [3, $b & 0x07, 0x10000];
        else { $ok = false; break; }
        for ($j = 1; $j <= $k; $j++) {
            if ($i + $j >= $n || $o[$i + $j] >> 6 !== 2) { $ok = false; break; }
            $cp = $cp << 6 | ($o[$i + $j] & 0x3F);
        }
        if ($ok && ($cp < $mini || ($cp >= 0xD800 && $cp <= 0xDFFF) || $cp > 0x10FFFF)) $ok = false;
        $cps[] = $cp;
        $i += $k + 1;
    }
    echo $ok ? implode(' ', array_map(fn($c) => sprintf('U+%04X', $c), $cps)) : 'invalide', "\n";
}"""}, banned={"python": [r"\.decode\s*\(", r"codecs"], "javascript": [r"TextDecoder", r"Buffer", r"decodeURI"], "php": [r"mb_", r"iconv", r"utf8_decode"]}),

    ch("joker", 10, "mini", "Les jokers", "motifs",
       "Ligne 1 : un motif avec des jokers : « ? » remplace exactement un caractère, « * » remplace n'importe quelle suite (même vide). Ligne 2 : k. "
       "Puis k mots. Pour chacun, affichez « oui » si le motif correspond au mot ENTIER, sinon « non ».",
       [_joker_in("f*e", ["forge", "fe", "forgee", "orge", "f", "foe"]), _joker_in("?o*?", ["code", "co", "c", "cod", "xox"]),
        _joker_in("*", ["", "tout", "*?"]), _joker_in("a?c*", ["abc", "ac", "abcd", "a?c", "xbc"]), _joker_in("**a**b**", ["ab", "xaxbx", "ba", "aab"]), _gros_joker],
       ["Un retour sur trace naïf peut devenir exponentiel avec plusieurs « * » : pensez programmation dynamique.",
        "M[i][j] = les i premiers caractères du motif correspondent-ils aux j premiers du mot ? M[0][0] = vrai.",
        "« * » : M[i][j] = M[i-1][j] (vide) ou M[i][j-1] (il avale un caractère de plus). « ? » ou caractère égal : M[i][j] = M[i-1][j-1]."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
p = L[0].rstrip("\r")
for w in L[2:2 + int(L[1])]:
    w = w.rstrip("\r")
    prec = [True] + [False] * len(w)
    for c in p:
        cur = [prec[0] and c == "*"] + [False] * len(w)
        for j in range(1, len(w) + 1):
            if c == "*":
                cur[j] = prec[j] or cur[j - 1]
            else:
                cur[j] = prec[j - 1] and (c == "?" or c == w[j - 1])
        prec = cur
    print("oui" if prec[len(w)] else "non")""", "c": r"""
#include <stdio.h>
#include <string.h>
static char p[1024], w[4096];
static unsigned char prec[4096], cur[4096];
int main(void) {
    int k;
    if (!fgets(p, sizeof p, stdin)) return 1;
    p[strcspn(p, "\r\n")] = '\0';
    if (!fgets(w, sizeof w, stdin) || sscanf(w, "%d", &k) != 1) return 1;
    while (k-- > 0) {
        if (!fgets(w, sizeof w, stdin)) w[0] = '\0';
        w[strcspn(w, "\r\n")] = '\0';
        int n = (int)strlen(w);
        memset(prec, 0, n + 1);
        prec[0] = 1;
        for (char *c = p; *c; ++c) {
            cur[0] = prec[0] && *c == '*';
            for (int j = 1; j <= n; ++j)
                cur[j] = *c == '*' ? (prec[j] || cur[j - 1]) : (prec[j - 1] && (*c == '?' || *c == w[j - 1]));
            memcpy(prec, cur, n + 1);
        }
        puts(prec[n] ? "oui" : "non");
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
#include <vector>
bool correspond(const std::string& p, const std::string& w) {
    std::vector<char> prec(w.size() + 1, 0), cur(w.size() + 1, 0);
    prec[0] = 1;
    for (char c : p) {
        cur[0] = prec[0] && c == '*';
        for (size_t j = 1; j <= w.size(); ++j)
            cur[j] = c == '*' ? (prec[j] || cur[j - 1]) : (prec[j - 1] && (c == '?' || c == w[j - 1]));
        prec = cur;
    }
    return prec[w.size()];
}
int main() {
    std::string p, w;
    std::getline(std::cin, p);
    std::getline(std::cin, w);
    int k = std::stoi(w);
    while (k-- > 0) {
        if (!std::getline(std::cin, w)) w.clear();
        std::cout << (correspond(p, w) ? "oui" : "non") << "\n";
    }
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n").map(l => l.replace(/\r$/, ""));
const p = L[0], out = [];
for (let k = 0; k < Number(L[1]); k++) {
  const w = L[2 + k] || "";
  let prec = new Uint8Array(w.length + 1), cur = new Uint8Array(w.length + 1);
  prec[0] = 1;
  for (const c of p) {
    cur[0] = prec[0] && c === "*" ? 1 : 0;
    for (let j = 1; j <= w.length; j++)
      cur[j] = c === "*" ? (prec[j] || cur[j - 1]) : (prec[j - 1] && (c === "?" || c === w[j - 1]) ? 1 : 0);
    [prec, cur] = [cur, prec];
  }
  out.push(prec[w.length] ? "oui" : "non");
}
console.log(out.join("\n"));""", "php": r"""
<?php
$p = rtrim((string) fgets(STDIN), "\r\n");
$k = (int) trim(fgets(STDIN));
for ($t = 0; $t < $k; $t++) {
    $w = rtrim((string) fgets(STDIN), "\r\n");
    $n = strlen($w);
    $prec = array_fill(0, $n + 1, false);
    $prec[0] = true;
    for ($i = 0; $i < strlen($p); $i++) {
        $c = $p[$i];
        $cur = [$prec[0] && $c === '*'];
        for ($j = 1; $j <= $n; $j++)
            $cur[$j] = $c === '*' ? ($prec[$j] || $cur[$j - 1]) : ($prec[$j - 1] && ($c === '?' || $c === $w[$j - 1]));
        $prec = $cur;
    }
    echo $prec[$n] ? "oui" : "non", "\n";
}"""}, banned={"python": [r"fnmatch", r"\bre\b"], "php": [r"fnmatch", r"preg_"], "javascript": [r"RegExp", r"\.match\s*\(", r"\.test\s*\("], "c": [r"fnmatch", r"regex"], "cpp": [r"regex"]}, time=3),

    ch("occurrences", 10, "mini", "Chercher un motif", "recherche de texte",
       "Ligne 1 : un texte (jusqu'à 1 000 000 caractères). Ligne 2 : un motif. Affichez le nombre d'occurrences du motif dans le texte (elles peuvent "
       "se chevaucher : « aa » apparaît 3 fois dans « aaaa »), puis sur une deuxième ligne les positions (à partir de 1) des 10 premières, ou « aucune ».",
       [("abracadabra\nabra", "2\n1 8"), ("aaaa\naa", "3\n1 2 3"), ("forge\nxyz", "0\naucune"), ("abc\nabc", "1\n1"),
        lambda: "a" * 1000000 + "\n" + "a" * 1000 + "b", lambda: ("ab" * 500000) + "\n" + "abab", lambda: "".join("abc"[x % 3] for x in _rand(1000000, 0, 10 ** 6, 9)) + "\nabcab"],
       ["Comparer le motif à chaque position peut coûter n × m : 10^9 opérations quand le texte est « aaaa…a » et le motif « aaa…ab ».",
        "Algorithme de Knuth-Morris-Pratt : précalculez pour le motif la table des plus longs préfixes qui sont aussi suffixes, pour ne jamais reculer dans le texte.",
        "Autre voie : la fonction de recherche du langage (find, strstr, indexOf, strpos) appelée en boucle à partir de la position suivant la dernière trouvée + 1."],
       {"python": r"""
import sys
L = sys.stdin.read().split("\n")
t, m = L[0].rstrip("\r"), L[1].rstrip("\r")
# table KMP : pi[i] = longueur du plus long préfixe propre de m[:i+1] qui en est aussi suffixe
pi = [0] * len(m)
k = 0
for i in range(1, len(m)):
    while k and m[i] != m[k]:
        k = pi[k - 1]
    if m[i] == m[k]:
        k += 1
    pi[i] = k
pos, k = [], 0
nb = 0
for i, c in enumerate(t):
    while k and c != m[k]:
        k = pi[k - 1]
    if c == m[k]:
        k += 1
    if k == len(m):
        nb += 1
        if len(pos) < 10:
            pos.append(i - len(m) + 2)
        k = pi[k - 1]
print(nb)
print(" ".join(map(str, pos)) if pos else "aucune")""", "c": r"""
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
static char t[1100000], m[1100000];
static int pi[1100000];
int main(void) {
    if (!fgets(t, sizeof t, stdin) || !fgets(m, sizeof m, stdin)) return 1;
    t[strcspn(t, "\r\n")] = '\0';
    m[strcspn(m, "\r\n")] = '\0';
    int n = (int)strlen(t), lm = (int)strlen(m), k = 0, nb = 0, np = 0, pos[10];
    for (int i = 1; i < lm; ++i) {
        while (k && m[i] != m[k]) k = pi[k - 1];
        if (m[i] == m[k]) ++k;
        pi[i] = k;
    }
    k = 0;
    for (int i = 0; i < n; ++i) {
        while (k && t[i] != m[k]) k = pi[k - 1];
        if (t[i] == m[k]) ++k;
        if (k == lm) { ++nb; if (np < 10) pos[np++] = i - lm + 2; k = pi[k - 1]; }
    }
    printf("%d\n", nb);
    if (!np) puts("aucune");
    for (int i = 0; i < np; ++i) printf(i ? " %d" : "%d", pos[i]);
    if (np) printf("\n");
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
#include <vector>
int main() {
    std::ios::sync_with_stdio(false);
    std::string t, m;
    std::getline(std::cin, t);
    std::getline(std::cin, m);
    std::vector<int> pi(m.size(), 0), pos;
    for (size_t i = 1, k = 0; i < m.size(); ++i) {
        while (k && m[i] != m[k]) k = pi[k - 1];
        if (m[i] == m[k]) ++k;
        pi[i] = (int)k;
    }
    long nb = 0;
    for (size_t i = 0, k = 0; i < t.size(); ++i) {
        while (k && t[i] != m[k]) k = pi[k - 1];
        if (t[i] == m[k]) ++k;
        if (k == m.size()) { ++nb; if (pos.size() < 10) pos.push_back((int)(i - m.size() + 2)); k = pi[k - 1]; }
    }
    std::cout << nb << "\n";
    if (pos.empty()) std::cout << "aucune";
    for (size_t i = 0; i < pos.size(); ++i) std::cout << (i ? " " : "") << pos[i];
    std::cout << "\n";
}""", "javascript": r"""
const L = require("fs").readFileSync(0, "utf8").split("\n");
const t = L[0].replace(/\r$/, ""), m = L[1].replace(/\r$/, "");
const pos = [];
let nb = 0;
for (let i = t.indexOf(m); i >= 0; i = t.indexOf(m, i + 1)) {
  nb++;
  if (pos.length < 10) pos.push(i + 1);
}
console.log(`${nb}\n${pos.length ? pos.join(" ") : "aucune"}`);""", "php": r"""
<?php
$t = rtrim((string) fgets(STDIN), "\r\n");
$m = rtrim((string) fgets(STDIN), "\r\n");
$pos = [];
$nb = 0;
for ($i = strpos($t, $m); $i !== false; $i = strpos($t, $m, $i + 1)) {
    $nb++;
    if (count($pos) < 10) $pos[] = $i + 1;
}
echo $nb, "\n", $pos ? implode(' ', $pos) : 'aucune', "\n";"""}, time=3),

    ch("luhn", 10, "mini", "La clé de Luhn", "validation",
       "Chaque ligne est un numéro (de carte bancaire, par exemple), avec éventuellement des espaces entre les chiffres. Affichez « valide » ou "
       "« invalide » selon l'algorithme de Luhn : en partant de la droite, doublez un chiffre sur deux (le 2e, le 4e…), retranchez 9 aux doubles "
       "supérieurs à 9, additionnez tout : le total doit être un multiple de 10. Un numéro de moins de 2 chiffres, ou contenant autre chose que "
       "des chiffres et des espaces, est invalide.",
       [lines(_LUHN), lines(["4" + "0" * 15, "5555 5555 5555 4444", "3782 822463 10005", "6011111111111117", "6011111111111118", "a123", "12 34"])],
       ["Retirez d'abord les espaces, puis vérifiez qu'il ne reste que des chiffres, et au moins 2.",
        "Parcourez les chiffres de droite à gauche avec un indice k : doublez quand k est impair (0 = le plus à droite).",
        "Un double de 2 chiffres (ex. 16) compte pour 1 + 6 = 7, c'est-à-dire 16 - 9."],
       {"python": r"""
import sys
for l in sys.stdin.read().split("\n"):
    if not l.strip():
        continue
    s = l.rstrip("\r").replace(" ", "")
    if len(s) < 2 or not (s.isascii() and s.isdigit()):
        print("invalide")
        continue
    total = 0
    for k, c in enumerate(reversed(s)):
        d = int(c)
        if k % 2:
            d = d * 2 - 9 if d * 2 > 9 else d * 2
        total += d
    print("valide" if total % 10 == 0 else "invalide")""", "c": r"""
#include <stdio.h>
#include <string.h>
int main(void) {
    char l[1024];
    while (fgets(l, sizeof l, stdin)) {
        char s[1024];
        int n = 0, ok = 1;
        l[strcspn(l, "\r\n")] = '\0';
        if (l[strspn(l, " ")] == '\0') continue;          /* ligne vide : ignorée */
        for (char *p = l; *p; ++p) {
            if (*p == ' ') continue;
            if (*p < '0' || *p > '9') ok = 0;
            s[n++] = *p;
        }
        if (!ok || n < 2) { puts("invalide"); continue; }
        int total = 0;
        for (int k = 0; k < n; ++k) {
            int d = s[n - 1 - k] - '0';
            if (k % 2) { d *= 2; if (d > 9) d -= 9; }
            total += d;
        }
        puts(total % 10 == 0 ? "valide" : "invalide");
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
std::string luhn(const std::string& l) {
    std::string s;
    for (char c : l) if (c != ' ') { if (c < '0' || c > '9') return "invalide"; s += c; }
    if (s.size() < 2) return "invalide";
    int total = 0;
    for (size_t k = 0; k < s.size(); ++k) {
        int d = s[s.size() - 1 - k] - '0';
        if (k % 2) { d *= 2; if (d > 9) d -= 9; }
        total += d;
    }
    return total % 10 == 0 ? "valide" : "invalide";
}
int main() {
    std::string l;
    while (std::getline(std::cin, l)) {
        if (!l.empty() && l.back() == '\r') l.pop_back();
        if (l.find_first_not_of(' ') == std::string::npos) continue;
        std::cout << luhn(l) << "\n";
    }
}""", "javascript": r"""
const out = [];
for (const brut of require("fs").readFileSync(0, "utf8").split("\n")) {
  if (!brut.trim()) continue;
  const s = brut.replace(/\r$/, "").replace(/ /g, "");
  if (s.length < 2 || !/^[0-9]+$/.test(s)) { out.push("invalide"); continue; }
  let total = 0;
  for (let k = 0; k < s.length; k++) {
    let d = Number(s[s.length - 1 - k]);
    if (k % 2) { d *= 2; if (d > 9) d -= 9; }
    total += d;
  }
  out.push(total % 10 === 0 ? "valide" : "invalide");
}
console.log(out.join("\n"));""", "php": r"""
<?php
while (($l = fgets(STDIN)) !== false) {
    if (trim($l) === '') continue;
    $s = str_replace(' ', '', rtrim($l, "\r\n"));
    if (strlen($s) < 2 || !ctype_digit($s)) { echo "invalide\n"; continue; }
    $total = 0;
    for ($k = 0, $n = strlen($s); $k < $n; $k++) {
        $d = (int) $s[$n - 1 - $k];
        if ($k % 2) { $d *= 2; if ($d > 9) $d -= 9; }
        $total += $d;
    }
    echo $total % 10 === 0 ? "valide" : "invalide", "\n";
}"""}),

    ch("regex", 10, "exam", "Examen : le moteur d'expressions régulières", "motifs",
       "Ligne 1 : n. Puis n paires de lignes : un motif, puis un texte. Le motif contient des caractères ordinaires, « . » (n'importe quel caractère), "
       "et des quantificateurs qui s'appliquent au caractère qui les précède : « * » (0 fois ou plus), « + » (1 fois ou plus), « ? » (0 ou 1 fois). "
       "« ^ » au tout début ancre le motif au début du texte, « $ » à la toute fin l'ancre à la fin. Sans ancre, le motif peut correspondre à n'importe "
       "quelle partie du texte. Affichez « oui » ou « non » pour chaque paire. Contrainte : pas de bibliothèque d'expressions régulières.",
       [_regex_in(_REGEX[:6]), _regex_in(_REGEX[6:14]), _regex_in(_REGEX[14:])],
       ["Écrivez une fonction récursive « correspond_ici(motif, texte) » qui teste une correspondance qui COMMENCE au début du texte.",
        "Si le 2e caractère du motif est un quantificateur, traitez l'élément (caractère + quantificateur) : pour « * », essayez de consommer 0, 1, 2… caractères qui correspondent, et à chaque fois le reste du motif.",
        "Recherche sans « ^ » : essayez correspond_ici à chaque position du texte (y compris la fin, pour un motif qui accepte le vide). « $ » seul en fin de motif : le texte doit être épuisé."],
       {"python": r"""
import sys

def egal(c, t):
    return c == "." or c == t

def ici(p, t):
    if not p:
        return True
    if p == "$":
        return t == ""
    if len(p) > 1 and p[1] in "*+?":
        c, q, reste = p[0], p[1], p[2:]
        if q == "?":
            return ici(reste, t) or (t != "" and egal(c, t[0]) and ici(reste, t[1:]))
        i = 0 if q == "*" else 1
        if q == "+" and not (t and egal(c, t[0])):
            return False
        while True:
            if ici(reste, t[i:]):
                return True
            if i < len(t) and egal(c, t[i]):
                i += 1
            else:
                return False
    return t != "" and egal(p[0], t[0]) and ici(p[1:], t[1:])

def cherche(p, t):
    if p.startswith("^"):
        return ici(p[1:], t)
    return any(ici(p, t[i:]) for i in range(len(t) + 1))

L = sys.stdin.read().split("\n")
n = int(L[0])
for k in range(n):
    p, t = L[1 + 2 * k].rstrip("\r"), L[2 + 2 * k].rstrip("\r") if 2 + 2 * k < len(L) else ""
    print("oui" if cherche(p, t) else "non")""", "c": r"""
#include <stdio.h>
#include <string.h>
static int egal(char c, char t) { return c == '.' || c == t; }
static int ici(const char *p, const char *t) {
    if (!*p) return 1;
    if (p[0] == '$' && !p[1]) return !*t;
    if (p[1] == '*' || p[1] == '+' || p[1] == '?') {
        char c = p[0], q = p[1];
        const char *reste = p + 2;
        if (q == '?') return ici(reste, t) || (*t && egal(c, *t) && ici(reste, t + 1));
        if (q == '+') { if (!*t || !egal(c, *t)) return 0; ++t; }
        for (;;) {
            if (ici(reste, t)) return 1;
            if (*t && egal(c, *t)) ++t; else return 0;
        }
    }
    return *t && egal(p[0], *t) && ici(p + 1, t + 1);
}
static int cherche(const char *p, const char *t) {
    if (*p == '^') return ici(p + 1, t);
    do { if (ici(p, t)) return 1; } while (*t++);
    return 0;
}
int main(void) {
    int n;
    char p[512], t[4096], l[16];
    if (!fgets(l, sizeof l, stdin) || sscanf(l, "%d", &n) != 1) return 1;
    while (n-- > 0) {
        if (!fgets(p, sizeof p, stdin)) p[0] = '\0';
        if (!fgets(t, sizeof t, stdin)) t[0] = '\0';
        p[strcspn(p, "\r\n")] = '\0';
        t[strcspn(t, "\r\n")] = '\0';
        puts(cherche(p, t) ? "oui" : "non");
    }
    return 0;
}""", "cpp": r"""
#include <iostream>
#include <string>
bool egal(char c, char t) { return c == '.' || c == t; }
bool ici(const std::string& p, size_t i, const std::string& t, size_t j) {
    if (i == p.size()) return true;
    if (p[i] == '$' && i + 1 == p.size()) return j == t.size();
    if (i + 1 < p.size() && (p[i + 1] == '*' || p[i + 1] == '+' || p[i + 1] == '?')) {
        char c = p[i], q = p[i + 1];
        if (q == '?') return ici(p, i + 2, t, j) || (j < t.size() && egal(c, t[j]) && ici(p, i + 2, t, j + 1));
        if (q == '+') { if (j == t.size() || !egal(c, t[j])) return false; ++j; }
        for (;;) {
            if (ici(p, i + 2, t, j)) return true;
            if (j < t.size() && egal(c, t[j])) ++j; else return false;
        }
    }
    return j < t.size() && egal(p[i], t[j]) && ici(p, i + 1, t, j + 1);
}
bool cherche(const std::string& p, const std::string& t) {
    if (!p.empty() && p[0] == '^') return ici(p, 1, t, 0);
    for (size_t j = 0; j <= t.size(); ++j) if (ici(p, 0, t, j)) return true;
    return false;
}
int main() {
    std::string l, p, t;
    std::getline(std::cin, l);
    int n = std::stoi(l);
    while (n-- > 0) {
        std::getline(std::cin, p);
        if (!std::getline(std::cin, t)) t.clear();
        if (!p.empty() && p.back() == '\r') p.pop_back();
        if (!t.empty() && t.back() == '\r') t.pop_back();
        std::cout << (cherche(p, t) ? "oui" : "non") << "\n";
    }
}""", "javascript": r"""
const egal = (c, t) => c === "." || c === t;
const ici = (p, i, t, j) => {
  if (i === p.length) return true;
  if (p[i] === "$" && i + 1 === p.length) return j === t.length;
  const q = p[i + 1];
  if (q === "*" || q === "+" || q === "?") {
    const c = p[i];
    if (q === "?") return ici(p, i + 2, t, j) || (j < t.length && egal(c, t[j]) && ici(p, i + 2, t, j + 1));
    if (q === "+") { if (j === t.length || !egal(c, t[j])) return false; j++; }
    for (;;) {
      if (ici(p, i + 2, t, j)) return true;
      if (j < t.length && egal(c, t[j])) j++; else return false;
    }
  }
  return j < t.length && egal(p[i], t[j]) && ici(p, i + 1, t, j + 1);
};
const cherche = (p, t) => {
  if (p[0] === "^") return ici(p, 1, t, 0);
  for (let j = 0; j <= t.length; j++) if (ici(p, 0, t, j)) return true;
  return false;
};
const L = require("fs").readFileSync(0, "utf8").split("\n").map(l => l.replace(/\r$/, ""));
const out = [];
for (let k = 0; k < Number(L[0]); k++) out.push(cherche(L[1 + 2 * k], L[2 + 2 * k] || "") ? "oui" : "non");
console.log(out.join("\n"));""", "php": r"""
<?php
function egal(string $c, string $t): bool { return $c === '.' || $c === $t; }
function ici(string $p, int $i, string $t, int $j): bool {
    $lp = strlen($p); $lt = strlen($t);
    if ($i === $lp) return true;
    if ($p[$i] === '$' && $i + 1 === $lp) return $j === $lt;
    $q = $i + 1 < $lp ? $p[$i + 1] : '';
    if ($q === '*' || $q === '+' || $q === '?') {
        $c = $p[$i];
        if ($q === '?') return ici($p, $i + 2, $t, $j) || ($j < $lt && egal($c, $t[$j]) && ici($p, $i + 2, $t, $j + 1));
        if ($q === '+') { if ($j === $lt || !egal($c, $t[$j])) return false; $j++; }
        for (;;) {
            if (ici($p, $i + 2, $t, $j)) return true;
            if ($j < $lt && egal($c, $t[$j])) $j++; else return false;
        }
    }
    return $j < $lt && egal($p[$i], $t[$j]) && ici($p, $i + 1, $t, $j + 1);
}
function cherche(string $p, string $t): bool {
    if ($p !== '' && $p[0] === '^') return ici($p, 1, $t, 0);
    for ($j = 0; $j <= strlen($t); $j++) if (ici($p, 0, $t, $j)) return true;
    return false;
}
$n = (int) trim(fgets(STDIN));
for ($k = 0; $k < $n; $k++) {
    $p = rtrim((string) fgets(STDIN), "\r\n");
    $t = rtrim((string) fgets(STDIN), "\r\n");
    echo cherche($p, $t) ? "oui" : "non", "\n";
}"""}, minutes=60, banned={"python": [r"\bimport re\b", r"\bre\.", r"fnmatch"], "javascript": [r"RegExp", r"\.match\s*\(", r"\.test\s*\(", r"\.search\s*\(", r"/[^/\n]+/[gimsuy]*\.test"],
                          "php": [r"preg_", r"ereg", r"fnmatch"], "c": [r"regex"], "cpp": [r"<regex>", r"std::regex"]}),
]
