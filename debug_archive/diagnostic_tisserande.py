"""
Script de diagnostic pour comprendre pourquoi "La Tisserande Oubliée" n'est pas trouvée
"""

import yaml
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# Charger config
with open("config.yaml", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# Initialiser embeddings
print("Chargement des embeddings...")
embeddings = HuggingFaceEmbeddings(
    model_name=config['rag']['embedding_model'],
    model_kwargs={'device': 'cuda' if config['rag'].get('use_cuda', False) else 'cpu'}
)

# Charger la base vectorielle
db_path = Path(config['paths']['db_dir'])
print(f"Chargement de la base depuis {db_path}...")
vectordb = Chroma(
    persist_directory=str(db_path),
    embedding_function=embeddings
)

print(f"Base chargee : {vectordb._collection.count()} chunks\n")

# 1. Recherche directe dans la collection
print("=" * 80)
print("1. RECHERCHE DIRECTE : 'Tisserande Oubliee'")
print("=" * 80)

results = vectordb._collection.get(
    where=None,
    limit=vectordb._collection.count()
)

tisserande_chunks = []
for i, doc in enumerate(results['documents']):
    if 'tisserande' in doc.lower() and 'oubliée' in doc.lower():
        tisserande_chunks.append({
            'id': results['ids'][i],
            'content': doc[:500],
            'metadata': results['metadatas'][i] if results['metadatas'] else {}
        })

print(f"Trouve {len(tisserande_chunks)} chunks contenant 'tisserande oubliee'\n")

for idx, chunk in enumerate(tisserande_chunks[:5]):  # Afficher les 5 premiers
    print(f"\n--- Chunk {idx + 1} ---")
    print(f"ID: {chunk['id']}")
    print(f"Metadata: {chunk['metadata']}")
    print(f"Contenu (500 premiers caractères):\n{chunk['content']}")
    print("-" * 80)

# 2. Recherche par similarité vectorielle
print("\n" + "=" * 80)
print("2. RECHERCHE PAR SIMILARITE VECTORIELLE (k=20)")
print("=" * 80)

query = "La Tisserande Oubliee"
docs = vectordb.similarity_search_with_score(query, k=20)

print(f"\nTop 20 resultats pour la requete : '{query}'\n")
for idx, (doc, score) in enumerate(docs, 1):
    print(f"\n--- Résultat {idx} (score: {score:.4f}) ---")
    print(f"Source: {doc.metadata.get('source', 'N/A')}")
    print(f"Category: {doc.metadata.get('category', 'N/A')}")
    print(f"Contenu (300 premiers caractères):\n{doc.page_content[:300]}")
    print("-" * 80)

# 3. Recherche avec re-ranking
print("\n" + "=" * 80)
print("3. RECHERCHE AVEC RE-RANKING (100 -> 20)")
print("=" * 80)

from sentence_transformers import CrossEncoder

print("Chargement du re-ranker...")
reranker = CrossEncoder(
    config['rag'].get('rerank_model', 'BAAI/bge-reranker-v2-m3'),
    device='cuda' if config['rag'].get('use_cuda', False) else 'cpu'
)

# Récupérer 100 chunks
docs_100 = vectordb.similarity_search(query, k=100)

print(f"Recupere {len(docs_100)} chunks initiaux")

# Re-ranker
pairs = [[query, doc.page_content] for doc in docs_100]
scores = reranker.predict(pairs)

# Trier par score
docs_with_scores = list(zip(docs_100, scores))
docs_with_scores.sort(key=lambda x: x[1], reverse=True)

print(f"\nTop 20 apres re-ranking:\n")
for idx, (doc, score) in enumerate(docs_with_scores[:20], 1):
    print(f"\n--- Résultat {idx} (score: {score:.4f}) ---")
    print(f"Source: {doc.metadata.get('source', 'N/A')}")
    print(f"Category: {doc.metadata.get('category', 'N/A')}")
    print(f"Contenu (300 premiers caractères):\n{doc.page_content[:300]}")
    print("-" * 80)

# 4. Statistiques par catégorie
print("\n" + "=" * 80)
print("4. STATISTIQUES DES CATEGORIES DANS LES TOP 100")
print("=" * 80)

from collections import Counter

categories = [doc.metadata.get('category', 'Unknown') for doc in docs_100]
category_counts = Counter(categories)

print("\nRepartition des categories:")
for cat, count in category_counts.most_common():
    print(f"  {cat}: {count} chunks ({count/len(docs_100)*100:.1f}%)")

print("\n" + "=" * 80)
print("DIAGNOSTIC TERMINE")
print("=" * 80)
