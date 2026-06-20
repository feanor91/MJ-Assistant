"""Diagnostic simplifié pour La Tisserande Oubliée"""

import yaml
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import json

# Charger config
with open("config.yaml", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# Initialiser embeddings
print("Chargement...")
embeddings = HuggingFaceEmbeddings(
    model_name=config['rag']['embedding_model'],
    model_kwargs={'device': 'cuda' if config['rag'].get('use_cuda', False) else 'cpu'}
)

# Charger la base
db_path = Path(config['paths']['db_dir'])
vectordb = Chroma(
    persist_directory=str(db_path),
    embedding_function=embeddings
)

print(f"\nBase : {vectordb._collection.count()} chunks")

# Recherche par similarité vectorielle
query = "La Tisserande Oubliee"
print(f"\nRecherche vectorielle pour: '{query}'")
print("=" * 60)

docs = vectordb.similarity_search_with_score(query, k=20)

for idx, (doc, score) in enumerate(docs, 1):
    print(f"\n{idx}. Score: {score:.4f}")
    print(f"   Source: {doc.metadata.get('source', 'N/A')}")
    print(f"   Category: {doc.metadata.get('category', 'N/A')}")
    # Afficher seulement les 100 premiers caractères en ascii safe
    content_preview = doc.page_content[:100].encode('ascii', 'ignore').decode('ascii')
    print(f"   Preview: {content_preview}...")

# Comptage par catégorie
from collections import Counter
docs_100 = vectordb.similarity_search(query, k=100)
categories = [doc.metadata.get('category', 'Unknown') for doc in docs_100]
category_counts = Counter(categories)

print("\n" + "=" * 60)
print("Repartition categories (top 100):")
for cat, count in category_counts.most_common():
    print(f"  {cat}: {count} ({count/len(docs_100)*100:.1f}%)")
