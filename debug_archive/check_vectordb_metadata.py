"""
Script pour vérifier les métadonnées de la base vectorielle
"""

from pathlib import Path
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings

# Configuration
db_dir = Path("lames_db")
embedding_model = "BAAI/bge-m3"

print("🔍 Chargement de la base vectorielle...")
print(f"   Dossier: {db_dir}")

if not db_dir.exists():
    print("❌ La base vectorielle n'existe pas !")
    exit(1)

# Charger les embeddings
embeddings = SentenceTransformerEmbeddings(model_name=embedding_model)

# Charger la base
vectordb = Chroma(
    persist_directory=str(db_dir),
    embedding_function=embeddings
)

print(f"✅ Base chargée avec {vectordb._collection.count()} documents\n")

# Récupérer tous les documents
print("📊 ANALYSE DES MÉTADONNÉES:\n")

all_docs = vectordb.similarity_search("test", k=1000)

# Analyser les catégories
categories = {}
sources = {}

for doc in all_docs:
    # Catégorie
    cat = doc.metadata.get("category", "unknown")
    categories[cat] = categories.get(cat, 0) + 1

    # Source
    src = doc.metadata.get("source", "unknown")
    sources[src] = sources.get(src, 0) + 1

print(f"📂 CATÉGORIES ({len(categories)} types):")
for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
    print(f"   {cat}: {count} chunks")

print(f"\n📄 SOURCES ({len(sources)} fichiers):")
for src, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
    print(f"   {src}: {count} chunks")

# Chercher spécifiquement "Livre 2 - Le Jeu.pdf"
print("\n\n🔍 RECHERCHE SPÉCIFIQUE: 'Livre 2 - Le Jeu.pdf'")
print("="*80)

livre2_chunks = [doc for doc in all_docs if "Livre 2" in doc.metadata.get("source", "")]

if livre2_chunks:
    print(f"✅ Trouvé {len(livre2_chunks)} chunks de 'Livre 2 - Le Jeu.pdf'")

    # Afficher la catégorie
    cat = livre2_chunks[0].metadata.get("category", "unknown")
    print(f"   Catégorie: {cat}")

    # Chercher "Voleur sans"
    voleur_chunks = [doc for doc in livre2_chunks if "voleur sans" in doc.page_content.lower()]

    if voleur_chunks:
        print(f"\n✅ Trouvé {len(voleur_chunks)} chunks contenant 'Voleur sans' !\n")
        for i, chunk in enumerate(voleur_chunks[:3], 1):
            print(f"--- Chunk {i} ---")
            print(chunk.page_content[:500])
            print()
    else:
        print("\n❌ AUCUN chunk ne contient 'Voleur sans' dans ce fichier")
        print("\n💡 Vérifions les premiers chunks de Livre 2:")
        for i, chunk in enumerate(livre2_chunks[:5], 1):
            print(f"\n--- Chunk {i} (premiers 300 car) ---")
            print(chunk.page_content[:300])
else:
    print("❌ 'Livre 2 - Le Jeu.pdf' NON TROUVÉ dans la base !")
    print("\n💡 Sources disponibles:")
    for src in sorted(sources.keys()):
        if "livre" in src.lower() or "jeu" in src.lower():
            print(f"   - {src}")
