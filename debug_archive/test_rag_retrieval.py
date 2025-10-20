"""
Script de test pour diagnostiquer le RAG
Permet de voir quel contexte est récupéré pour une question donnée
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.rag import VectorStore
from core.utils import load_config
from langchain_community.vectorstores import Chroma

def test_rag_retrieval(question: str, k: int = 6):
    """Teste la récupération RAG pour une question donnée"""

    # Charger la configuration
    config = load_config(Path("config.yaml"))

    # Créer le VectorStore
    vector_store = VectorStore(config)

    # Charger la base vectorielle existante
    db_dir = config['paths']['db_dir']
    db_path = Path(db_dir)

    if not db_path.exists() or not any(db_path.iterdir()):
        print("❌ Base vectorielle non trouvée!")
        print(f"Chemin recherché: {db_path}")
        return

    print(f"✅ Chargement de la base vectorielle depuis {db_path}")
    vectordb = Chroma(
        persist_directory=str(db_path),
        embedding_function=vector_store.embeddings
    )

    # Créer un retriever
    retriever = vectordb.as_retriever(search_kwargs={"k": k})

    # Récupérer les documents pertinents
    print(f"\n🔍 Question: {question}")
    print(f"📊 Nombre de chunks à récupérer: {k}\n")
    print("="*80)

    docs = retriever.get_relevant_documents(question)

    if not docs:
        print("❌ Aucun document récupéré!")
        return

    print(f"✅ {len(docs)} documents récupérés\n")

    for i, doc in enumerate(docs, 1):
        print(f"\n{'='*80}")
        print(f"CHUNK {i}/{len(docs)}")
        print('='*80)

        # Afficher le contenu (limité à 500 caractères pour la lisibilité)
        content = doc.page_content
        if len(content) > 800:
            print(content[:800] + "\n[...]")
        else:
            print(content)

        # Afficher les métadonnées si disponibles
        if hasattr(doc, 'metadata') and doc.metadata:
            print(f"\n📋 Métadonnées: {doc.metadata}")

    print("\n" + "="*80)
    print("FIN DE L'ANALYSE")
    print("="*80)


def test_with_filter(question: str, k: int = 50):
    """Teste la récupération avec filtre de catégorie (mode encyclopédique)"""

    config = load_config(Path("config.yaml"))
    vector_store = VectorStore(config)
    db_path = Path(config['paths']['db_dir'])

    if not db_path.exists():
        print("❌ Base vectorielle non trouvée!")
        return

    vectordb = Chroma(
        persist_directory=str(db_path),
        embedding_function=vector_store.embeddings
    )

    print(f"\n🔍 TEST AVEC FILTRE (mode encyclopédique)")
    print(f"Question: {question}")
    print(f"Filtre: category IN ['rules', 'universe_book', 'unknown']")
    print("="*80)

    # Retriever avec filtre
    retriever = vectordb.as_retriever(
        search_kwargs={
            "k": k,
            "filter": {
                "$or": [
                    {"category": "rules"},
                    {"category": "universe_book"},
                    {"category": "unknown"}
                ]
            }
        }
    )

    try:
        docs = retriever.get_relevant_documents(question)
        print(f"✅ {len(docs)} documents récupérés avec filtre\n")

        if docs:
            for i, doc in enumerate(docs[:3], 1):
                print(f"\n--- CHUNK {i} ---")
                print(f"Source: {doc.metadata.get('source', 'inconnu')}")
                print(f"Catégorie: {doc.metadata.get('category', 'inconnu')}")
                print(doc.page_content[:400])
        else:
            print("❌ AUCUN chunk récupéré ! Le filtre bloque tout.")
    except Exception as e:
        print(f"❌ ERREUR: {e}")


def search_exact_text(search_text: str):
    """Recherche un texte exact dans tous les chunks de la base"""

    config = load_config(Path("config.yaml"))
    vector_store = VectorStore(config)
    db_path = Path(config['paths']['db_dir'])

    if not db_path.exists():
        print("❌ Base vectorielle non trouvée!")
        return

    vectordb = Chroma(
        persist_directory=str(db_path),
        embedding_function=vector_store.embeddings
    )

    print(f"\n🔍 RECHERCHE DE TEXTE EXACT : '{search_text}'")
    print("="*80)

    # Récupérer TOUS les chunks (ou beaucoup)
    all_docs = vectordb.similarity_search("test", k=500)  # Récupérer plein de chunks

    found_count = 0
    for i, doc in enumerate(all_docs, 1):
        if search_text.lower() in doc.page_content.lower():
            found_count += 1
            print(f"\n✅ TROUVÉ dans chunk {i}")
            print(f"Source: {doc.metadata.get('source', 'inconnu')}")
            print(f"Catégorie: {doc.metadata.get('category', 'inconnu')}")
            print(f"\nContexte (300 caractères autour) :")

            # Trouver la position et afficher le contexte
            pos = doc.page_content.lower().find(search_text.lower())
            start = max(0, pos - 150)
            end = min(len(doc.page_content), pos + len(search_text) + 150)
            context = doc.page_content[start:end]
            print(f"...{context}...")
            print()

    if found_count == 0:
        print(f"\n❌ Texte '{search_text}' NON TROUVÉ dans les {len(all_docs)} chunks récupérés")
        print("\n💡 Causes possibles:")
        print("1. Le PDF n'est pas dans Data/ ou Data/Regles/")
        print("2. L'extraction PDF a échoué (texte en image ?)")
        print("3. Le chunking a cassé le texte en morceaux trop petits")
        print("4. La base vectorielle n'a pas été reconstruite après ajout du PDF")
    else:
        print(f"\n✅ Texte trouvé dans {found_count} chunks")


if __name__ == "__main__":
    import io
    import sys

    # Fix encodage Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    # Question problématique
    question = "Parle-moi de l'arcane du Tarot des ombres le Voleur sans mémoire"

    print("🧪 TEST DE RÉCUPÉRATION RAG - MJ ASSISTANT")
    print("="*80)

    # Test 1 : Sans filtre
    print("\n\n### TEST 1 : SANS FILTRE ###\n")
    test_rag_retrieval(question, k=10)

    # Test 2 : Avec filtre (mode encyclopédique)
    print("\n\n### TEST 2 : AVEC FILTRE (mode encyclopédique) ###\n")
    test_with_filter(question, k=50)

    # Test 3 : Recherche exacte du texte
    print("\n\n### TEST 3 : RECHERCHE DE TEXTE EXACT ###\n")
    search_exact_text("Voleur sans")

    print("\n\n💡 DIAGNOSTIC:")
    print("- Si TEST 1 trouve des chunks mais PAS TEST 2 : le filtre de catégorie bloque tout")
    print("- Si TEST 1 ne trouve RIEN : problème d'embeddings ou base vide")
    print("- Si les deux trouvent mais contenu incorrect : problème de chunking/extraction PDF")
    print("- Si TEST 3 ne trouve RIEN : le texte n'est pas dans la base (PDF manquant ou extraction échouée)")
