"""
Chercher directement "voleur" dans les chunks de la base
"""

import sys
import io

# Fix encodage Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings

emb = SentenceTransformerEmbeddings(model_name='BAAI/bge-m3')
db = Chroma(persist_directory='lames_db', embedding_function=emb)

print(f'📊 Total chunks: {db._collection.count()}\n')

# Récupérer tous les docs
docs = db.similarity_search('voleur', k=1000)

# Chercher "voleur sans"
voleur_sans = [d for d in docs if 'voleur sans' in d.page_content.lower()]
print(f'✅ Chunks contenant "voleur sans": {len(voleur_sans)}')

# Chunks de Livre 2
livre2_docs = [d for d in docs if 'Livre 2' in d.metadata.get('source', '')]
print(f'📖 Chunks de Livre 2: {len(livre2_docs)}')

# Chunks Livre 2 avec "voleur"
livre2_voleur = [d for d in livre2_docs if 'voleur' in d.page_content.lower()]
print(f'🔍 Chunks Livre 2 contenant "voleur": {len(livre2_voleur)}\n')

if livre2_voleur:
    print('📝 Premiers chunks Livre 2 contenant "voleur":\n')
    for i, d in enumerate(livre2_voleur[:5]):
        print(f'--- Chunk {i+1} ---')
        print(d.page_content[:500])
        print()
else:
    print('❌ AUCUN chunk de Livre 2 ne contient "voleur"')
    print('\n💡 Affichons les 5 premiers chunks de Livre 2:\n')
    for i, d in enumerate(livre2_docs[:5]):
        print(f'--- Chunk {i+1} ---')
        print(d.page_content[:400])
        print()
