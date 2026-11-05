# -*- coding: utf-8 -*-
"""Socle du parcours : grades (métiers du code), paliers et fabrique de défis.

Un défi = un énoncé, des tests (entrée envoyée au programme → sortie attendue ; les premiers sont
visibles, les autres cachés), trois indices et des solutions de référence en C, C++, Python,
JavaScript et PHP. Les tests passant par l'entrée/sortie standard, le parcours fonctionne dans
tous les langages ; chaque langage a son propre grade.
"""

# Grade n = nombre d'examens réussis. Réussir l'examen du palier s fait passer au grade s + 1.
LEVELS = [
    ("Stagiaire", "🎒"),
    ("Alternant", "📚"),
    ("Dev Junior", "☕"),
    ("Développeur", "⌨️"),
    ("Dev Confirmé", "🔧"),
    ("Dev Senior", "🧱"),
    ("Tech Lead", "🧭"),
    ("Staff Engineer", "🧠"),
    ("Architecte logiciel", "🏛️"),
    ("Principal Engineer", "⚙️"),
    ("Distinguished Engineer", "🛰️"),
    ("CTO", "🚀"),
    ("Légende du code", "👑"),
]

# (thème, domaine, ce qu'on y apprend) — un palier par grade à conquérir
STAGES = [
    ("Les bases", "fondamentaux", "Entrées/sorties, variables, types numériques, conditions."),
    ("Les boucles", "fondamentaux", "Boucles for/while, accumulateurs, boucles imbriquées, lecture jusqu'à la fin."),
    ("Tableaux et chaînes", "fondamentaux", "Tableaux, parcours, manipulation de texte, matrices."),
    ("Fonctions et récursivité", "conception", "Fonctions, récursion, dictionnaires, décomposition d'un problème."),
    ("Robustesse et débogage", "qualité", "Cas limites, débordements, arrondis, dates, parsing, corriger le code d'un autre."),
    ("Structures de données", "structures", "Piles, files, tas, listes chaînées, ensembles, historiques."),
    ("Recherche, tri et complexité", "algorithmique", "Recherche binaire, deux pointeurs, fenêtres, sommes préfixes, O(n log n)."),
    ("Modélisation et simulation", "conception", "Objets, états, règles métier, simulations : penser comme un ingénieur logiciel."),
    ("Graphes et réseaux", "algorithmique", "Parcours en largeur/profondeur, plus courts chemins, dépendances, arbres couvrants."),
    ("Programmation dynamique", "algorithmique", "Mémoïsation, DP, retour sur trace : les problèmes des entretiens techniques."),
    ("Bits, encodages et texte", "systèmes", "Opérations bit à bit, chiffrement, compression, UTF-8, motifs de texte."),
    ("Projets d'ingénieur", "systèmes", "Parseurs, machines virtuelles, interpréteurs, bases de données : le niveau pro."),
]
STAGE_THEMES = [s[0] for s in STAGES]

# Filière « Algorithmique mathématique » : même mécanique (12 paliers, 13 grades), défis purement mathématiques.
# Paliers 0 à 5 : Algorithme ; paliers 6 à 11 : Algorithme avancé. Contenu dans les modules m00_… à m11_….
MATH_LEVELS = [
    ("Élève", "🎒"),
    ("Lycéen", "✏️"),
    ("Taupin", "📐"),
    ("Licencié", "📘"),
    ("Agrégé", "🎓"),
    ("Doctorant", "🔬"),
    ("Docteur", "📜"),
    ("Maître de conférences", "🧮"),
    ("Professeur", "🏛️"),
    ("Directeur de recherche", "🔭"),
    ("Académicien", "⚜️"),
    ("Médaille Fields", "🏅"),
    ("Légende des mathématiques", "♾️"),
]
MATH_STAGES = [
    ("Premiers calculs", "arithmétique", "Carrés, divisibilité, diviseurs, PGCD, PPCM, fractions, écriture binaire."),
    ("Nombres premiers", "arithmétique", "Primalité, factorisation, diviseurs, cribles."),
    ("Suites et récurrences", "analyse", "Suites récurrentes, sommes, cycles, points fixes."),
    ("Combinatoire", "combinatoire", "Factorielles, coefficients binomiaux, permutations, dénombrement."),
    ("Arithmétique modulaire", "arithmétique", "Congruences, exponentiation rapide, inverse modulaire, petit théorème de Fermat."),
    ("Calcul numérique", "analyse", "Dichotomie, méthode de Newton, intégration, précision flottante."),
    ("Théorie des nombres", "arithmétique", "Euclide étendu, restes chinois, indicatrice d'Euler, Miller-Rabin."),
    ("Matrices et algèbre linéaire", "algèbre", "Puissance matricielle, pivot de Gauss, déterminants, systèmes linéaires."),
    ("Combinatoire avancée", "combinatoire", "Lucas, inclusion-exclusion, Catalan, Burnside."),
    ("Géométrie algorithmique", "géométrie", "Produit vectoriel, enveloppe convexe, intersections, aires, Pick."),
    ("Probabilités exactes", "probabilités", "Espérances, fractions exactes, probabilités modulo p, chaînes de Markov."),
    ("Grands nombres et transformées", "algèbre", "Entiers arbitraires, NTT, Pollard rho : le niveau recherche."),
]

# id → (nom, icône, sous-titre, grades, paliers, domaines du radar)
TRACKS = {
    "dev": ("Développeur", "💻", "Du stage à la légende", LEVELS, STAGES,
            ["fondamentaux", "conception", "qualité", "structures", "algorithmique", "systèmes"]),
    "math": ("Mathématicien", "∑", "De l'élève à la médaille Fields", MATH_LEVELS, MATH_STAGES,
             ["arithmétique", "analyse", "combinatoire", "algèbre", "géométrie", "probabilités"]),
}

SOL_LANGS = ("c", "cpp", "python", "javascript", "php")


def ch(cid, stage, kind, title, theme, desc, tests, hints, sol, visible=2, tag="", starter=None, **limits):
    """Fabrique un défi. « sol » : {langage: code} ; « starter » : code de départ imposé (défis de débogage).
    Un test peut être une simple entrée (chaîne), ou une fonction qui fabrique l'entrée (gros tests, générés à la
    demande pour ne pas ralentir le démarrage) : sa sortie attendue (None ici) sera celle de la solution Python,
    calculée à la demande par parcours.remplir() et confrontée aux quatre autres langages par le vérificateur."""
    assert kind in ("mini", "exam"), cid
    assert len(hints) == 3, cid
    tests = [(t, None) if isinstance(t, str) or callable(t) else t for t in tests]
    return {"id": cid, "stage": stage, "kind": kind, "title": title, "theme": theme, "desc": desc, "tag": tag,
            "tests": [{"in": None if callable(i) else i, "gen": i if callable(i) else None, "out": o, "hidden": n >= visible, "auto": o is None}
                      for n, (i, o) in enumerate(tests)],
            "hints": hints, "sol": {k: v.strip("\n") + "\n" for k, v in sol.items()},
            "starter": {k: v.strip("\n") + "\n" for k, v in (starter or {}).items()},
            "xp": (100 if kind == "exam" else 20) * (stage + 1),
            "limits": {"time": limits.get("time", 2), "minutes": limits.get("minutes", 0),
                       "max_lines": limits.get("max_lines", 0), "banned": limits.get("banned", {})}}


def lines(it):
    """Assemble des valeurs en lignes (pratique pour écrire les sorties attendues)."""
    return "\n".join(str(x) for x in it)
