#!/usr/bin/env python3
"""
tools/build_glossary.py
Construit automatiquement le glossaire de synonymes depuis la base vectorielle ChromaDB.

Ce script extrait les termes officiels du jeu (## headers, champs section),
puis demande au LLM quels mots courants un joueur utiliserait pour chercher chaque concept.
Le glossaire JSON résultant est utilisé par _expand_query() pour une expansion
instantanée (zéro latence) avant chaque retrieval RAG.

Usage :
    python tools/build_glossary.py
    python tools/build_glossary.py --model mistral-nemo
    python tools/build_glossary.py --dry-run     # extrait les termes sans appeler le LLM
    python tools/build_glossary.py --config config.yaml
"""

import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire parent au path pour importer core/
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.utils import load_config

GLOSSARY_PATH = Path("prompts/glossary.json")
BATCH_SIZE = 12  # Termes par appel LLM (équilibre qualité/vitesse)

# Termes trop génériques pour avoir des synonymes utiles — à ignorer
NOISE_TERMS = {
    "suite", "introduction", "annexe", "index", "sommaire", "préface",
    "avant-propos", "conclusion", "chapitre", "partie", "section",
}


def load_vectordb(config: dict):
    """Charge ChromaDB avec la même config que l'app."""
    from langchain_chroma import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings

    embed_model = config['rag']['embedding_model']
    use_cuda = config['rag'].get('use_cuda', True)
    db_dir = str(Path(config['paths']['db_dir']))

    print(f"  Modele d'embedding : {embed_model}")
    print(f"  Base vectorielle   : {db_dir}")

    try:
        device = "cuda" if use_cuda else "cpu"
        embeddings = HuggingFaceEmbeddings(
            model_name=embed_model,
            model_kwargs={"device": device},
        )
    except Exception:
        embeddings = HuggingFaceEmbeddings(model_name=embed_model)

    return Chroma(persist_directory=db_dir, embedding_function=embeddings)


def _is_clean_term(text: str) -> bool:
    """Retourne True si le texte est un terme mécanique utilisable."""
    # Doit tenir sur une seule ligne (pas de fragments de paragraphe)
    if "\n" in text or len(text) > 70:
        return False
    # Longueur minimale significative
    if len(text) < 5:
        return False
    # Rejeter les prefixes de scenario recurrents
    _bad_starts = ("ne me decevez", "scène ", "acte ", "acte i", "acte ii", "acte iii",
                   "piste ", "partie ", "prologue", "epilogue", "chapitre", "annexe",
                   "vue de", "carte de", "graphi", "remerci", "credite", "crédits",
                   "un scénario", "dramatis", "table des", "pour aller", "un scénario")
    tl = text.lower().strip()
    if any(tl.startswith(p) for p in _bad_starts):
        return False
    # Rejeter les termes avec OCR garbled (mélange min/MAJ erratique)
    # ex: "dEscriPtiOn", "GAlAntEriE" — détecte des MAJ isolées au milieu d'un mot
    if re.search(r"[a-z][A-Z][a-z]", text):
        return False
    # Rejeter si contient des caractères typiques de noms de personnages (parenthèse + chiffre)
    # ex: "Saint-Lucq, Lame insaisissable (Combattant 4)"
    if re.search(r"\(\s*\w+\s+\d\s*\)", text):
        return False
    # Rejeter les purs fragments numériques ou symboles
    if re.match(r"^[\d\s.,;:!?()\[\]└├╔┴]+$", text):
        return False
    # Rejeter les termes qui ne contiennent que des mots très courts (titres coupés, etc.)
    words = re.findall(r"\w{3,}", text)
    if len(words) == 0:
        return False
    return True


def extract_terms(vectordb, rules_only: bool = True) -> list:
    """Extrait les termes mécaniques officiels depuis les chunks ChromaDB.

    rules_only=True : ne traite que les chunks category='rules' (recommandé).
    Les catégories 'universe_book' peuvent être incluses pour les termes draconiques.
    """
    print("Recuperation des documents...")
    all_data = vectordb.get(include=["metadatas", "documents"])

    terms: set = set()

    header_re = re.compile(r"^#{1,3}\s*(.+?)\s*$", re.MULTILINE)
    # Nettoie prefixes numeriques : "12 Opposition" → "Opposition", "II. Tarot" → "Tarot"
    num_prefix_re = re.compile(r"^[\d\s]+[\.\)]\s*|^\s*\d+\s+")

    # Categories acceptees
    accepted_cats = {"rules"} if rules_only else {"rules", "universe_book"}

    rules_docs = 0
    for meta, doc_text in zip(all_data["metadatas"], all_data["documents"]):
        cat = meta.get("category", "unknown")
        if cat not in accepted_cats:
            continue
        rules_docs += 1

        # 1. Champ metadata 'section'
        raw = (meta.get("section") or "").strip()
        if raw and not raw.startswith("---"):
            cleaned = num_prefix_re.sub("", raw).strip()
            cleaned = re.sub(r"\s*\(suite\)\s*$", "", cleaned).strip()
            if _is_clean_term(cleaned) and cleaned.lower() not in NOISE_TERMS:
                terms.add(cleaned)

        # 2. En-tetes ## et ### dans le texte du chunk
        for match in header_re.finditer(doc_text):
            raw = match.group(1).strip()
            cleaned = num_prefix_re.sub("", raw).strip()
            cleaned = re.sub(r"\s*\(suite\)\s*$", "", cleaned).strip()
            if _is_clean_term(cleaned) and cleaned.lower() not in NOISE_TERMS:
                terms.add(cleaned)

    print(f"  {rules_docs} chunks '{'+'.join(accepted_cats)}' analyses")

    # Trier : termes les plus longs/specifiques en premier
    sorted_terms = sorted(terms, key=lambda t: (-len(t), t.lower()))

    # Deduplication douce : retire les termes sous-chaines d'un terme plus long
    final: list = []
    for term in sorted_terms:
        tl = term.lower()
        if not any(tl in other.lower() and tl != other.lower() for other in final):
            final.append(term)

    print(f"  {len(final)} termes mecaniques extraits")
    return final


def generate_synonyms_batch(terms: list, model_name: str) -> dict:
    """Genere les synonymes pour un batch de termes officiels via LLM."""
    from langchain_ollama import ChatOllama
    from langchain_core.messages import HumanMessage

    terms_list = "\n".join(f"- {t}" for t in terms)

    prompt = (
        'Tu es expert du jeu de role "Les Lames du Cardinal" (Paris XVIIe, cape et epee, Tarot magique).\n'
        "Pour chaque terme officiel du jeu ci-dessous, donne les mots courants qu'un joueur\n"
        "ordinaire utiliserait pour CHERCHER ce concept — sans connaitre la terminologie exacte.\n"
        "Exemples : 'Opposition Dramatique' → ['combat', 'duel', 'affrontement', 'bagarre'],\n"
        "           'Tarot des Ombres' → ['magie', 'sorts', 'carte', 'pouvoirs magiques'],\n"
        "           'Blessures' → ['points de vie', 'HP', 'sante', 'degats recus'].\n"
        "REGLES : \n"
        "- Max 6 synonymes par terme\n"
        "- N'inclus un terme que s'il a AU MOINS 2 synonymes courants utiles\n"
        "- Omets les termes trop specifiques sans equivalent courant\n"
        "- Reponds en JSON valide UNIQUEMENT, sans markdown, sans explication\n\n"
        f"Termes officiels :\n{terms_list}\n\n"
        "Format de reponse :\n"
        '{"Terme officiel": ["mot courant 1", "mot courant 2"], ...}'
    )

    llm = ChatOllama(model=model_name, temperature=0.0, num_predict=700)
    result = llm.invoke([HumanMessage(content=prompt)])
    content = (result.content or "").strip()

    # Supprimer les fences markdown eventuelles
    content = re.sub(r"^```(?:json)?\n?", "", content)
    content = re.sub(r"\n?```$", "", content).strip()

    try:
        parsed = json.loads(content)
        # Valider : garder seulement les entrees qui sont des listes non vides
        return {k: v for k, v in parsed.items() if isinstance(v, list) and len(v) >= 2}
    except json.JSONDecodeError:
        # Tentative de recuperation : chercher un bloc {...} dans la reponse
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                return {k: v for k, v in parsed.items() if isinstance(v, list) and len(v) >= 2}
            except json.JSONDecodeError:
                pass
    print("    [!] Batch non parseable, ignore")
    return {}


def build_glossary(config: dict, model_name: str, dry_run: bool = False, all_cats: bool = False) -> dict:
    """Construit le glossaire complet depuis ChromaDB."""
    vectordb = load_vectordb(config)
    terms = extract_terms(vectordb, rules_only=not all_cats)

    if dry_run:
        print("\nTermes extraits (dry-run — aucun appel LLM) :")
        for i, t in enumerate(terms, 1):
            print(f"  {i:3d}. {t}")
        return {}

    glossary: dict = {
        "version": "1.0",
        "generated": datetime.now().isoformat(),
        "model_used": model_name,
        "mappings": {},
    }

    total_batches = (len(terms) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx in range(0, len(terms), BATCH_SIZE):
        batch = terms[batch_idx : batch_idx + BATCH_SIZE]
        batch_num = batch_idx // BATCH_SIZE + 1

        print(f"  Batch {batch_num}/{total_batches} ({len(batch)} termes)... ", end="", flush=True)
        synonyms = generate_synonyms_batch(batch, model_name)
        print(f"{len(synonyms)} mappings")

        glossary["mappings"].update(synonyms)

        # Sauvegarde progressive — resiste aux interruptions
        GLOSSARY_PATH.parent.mkdir(parents=True, exist_ok=True)
        GLOSSARY_PATH.write_text(
            json.dumps(glossary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return glossary


def print_summary(glossary: dict) -> None:
    mappings = glossary.get("mappings", {})
    print(f"\n{len(mappings)} termes dans le glossaire.")
    print("Apercu (10 premiers) :")
    for term, synonyms in list(mappings.items())[:10]:
        syns = ", ".join(f'"{s}"' for s in synonyms)
        print(f"  {term!r:40s} <- [{syns}]")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Construit le glossaire de synonymes depuis ChromaDB"
    )
    parser.add_argument("--model", default=None, help="Modele Ollama (defaut: config.yaml)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extrait uniquement les termes, sans appeler le LLM",
    )
    parser.add_argument(
        "--all-cats",
        action="store_true",
        help="Inclure aussi les chunks universe_book (pas seulement rules)",
    )
    parser.add_argument("--config", default="config.yaml", help="Chemin vers config.yaml")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    model_name = args.model or config["model"]["default"]

    print("=== Generateur de glossaire — Les Lames du Cardinal ===")
    print(f"  Modele  : {model_name}")
    print(f"  Sortie  : {GLOSSARY_PATH}")
    print()

    glossary = build_glossary(config, model_name, dry_run=args.dry_run, all_cats=args.all_cats)

    if not args.dry_run and glossary.get("mappings"):
        print(f"\nGlossaire sauvegarde : {GLOSSARY_PATH}")
        print_summary(glossary)
    elif args.dry_run:
        print("\n(dry-run termine — glossaire non genere)")


if __name__ == "__main__":
    main()
