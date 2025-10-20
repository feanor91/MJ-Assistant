"""
core/rag.py
Module de gestion du RAG (Retrieval-Augmented Generation)
"""

import os
import shutil
import hashlib
import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import streamlit as st

# Ordre de préférence pour l'extraction PDF :
# 1. PyMuPDF (fitz) - MEILLEUR pour les PDFs multi-colonnes
# 2. pdfplumber - Bon mais mélange parfois les colonnes
# 3. PyPDF2 - Fallback basique

try:
    import fitz  # PyMuPDF
    USE_PYMUPDF = True
    USE_PDFPLUMBER = False
except ImportError:
    USE_PYMUPDF = False
    try:
        import pdfplumber
        USE_PDFPLUMBER = True
    except ImportError:
        import PyPDF2
        USE_PDFPLUMBER = False

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain.schema.retriever import BaseRetriever
from langchain.callbacks.manager import CallbackManagerForRetrieverRun

try:
    from langchain_ollama import OllamaLLM
    OllamaLLM_available = True
except ImportError:
    try:
        from langchain_community.llms import Ollama as OllamaLLM
        OllamaLLM_available = True
    except ImportError:
        OllamaLLM_available = False

# Import pour re-ranking
try:
    from sentence_transformers import CrossEncoder
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False
    print("⚠️ CrossEncoder non disponible. Installe avec: pip install sentence-transformers")

# Import pour typing
from typing import Any


class DocumentExtractor:
    """Extrait le texte de différents types de documents"""
    
    @staticmethod
    def calculate_directory_hash(directory: Path) -> Tuple[str, Dict[str, Any]]:
        """Calcule un hash du répertoire et retourne les métadonnées des fichiers"""
        if not directory.exists():
            return "", {}
        
        file_metadata = {}
        hash_content = []
        
        for file_path in sorted(directory.rglob("*")):
            if not file_path.is_file():
                continue
            
            suffix = file_path.suffix.lower()
            if suffix not in [".pdf", ".txt", ".md"]:
                continue
            
            # Métadonnées du fichier
            stat = file_path.stat()
            file_info = {
                "name": file_path.name,
                "path": str(file_path.relative_to(directory)),
                "size": stat.st_size,
                "modified": stat.st_mtime
            }
            file_metadata[str(file_path.relative_to(directory))] = file_info
            
            # Pour le hash : nom + taille + date modif
            hash_content.append(f"{file_path.name}|{stat.st_size}|{stat.st_mtime}")
        
        # Calculer hash global
        hash_str = "|".join(hash_content)
        directory_hash = hashlib.md5(hash_str.encode()).hexdigest()
        
        return directory_hash, file_metadata
    
    @staticmethod
    def check_if_reload_needed(directory: Path, db_dir: Path) -> Tuple[bool, str]:
        """Vérifie si un rechargement est nécessaire"""
        metadata_file = db_dir / "corpus_metadata.json"
        
        # Si la base n'existe pas, rechargement nécessaire
        if not db_dir.exists() or not any(db_dir.iterdir()) or not metadata_file.exists():
            return True, "Base vectorielle inexistante"
        
        # Calculer le hash actuel
        current_hash, current_metadata = DocumentExtractor.calculate_directory_hash(directory)
        
        # Charger les métadonnées précédentes
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                saved_hash = saved_data.get('hash', '')
                saved_metadata = saved_data.get('files', {})
        except Exception:
            return True, "Métadonnées corrompues"
        
        # Comparer les hash
        if current_hash != saved_hash:
            # Analyser les différences
            current_files = set(current_metadata.keys())
            saved_files = set(saved_metadata.keys())
            
            added = current_files - saved_files
            removed = saved_files - current_files
            modified = []
            
            for file_path in current_files & saved_files:
                if (current_metadata[file_path]['size'] != saved_metadata[file_path]['size'] or
                    current_metadata[file_path]['modified'] != saved_metadata[file_path]['modified']):
                    modified.append(file_path)
            
            # Construire le message de différence
            changes = []
            if added:
                changes.append(f"{len(added)} fichier(s) ajouté(s)")
            if removed:
                changes.append(f"{len(removed)} fichier(s) supprimé(s)")
            if modified:
                changes.append(f"{len(modified)} fichier(s) modifié(s)")
            
            reason = ", ".join(changes) if changes else "Changements détectés"
            return True, reason
        
        return False, "Corpus inchangé"
    
    @staticmethod
    def save_corpus_metadata(directory: Path, db_dir: Path):
        """Sauvegarde les métadonnées du corpus"""
        directory_hash, file_metadata = DocumentExtractor.calculate_directory_hash(directory)
        
        metadata = {
            'hash': directory_hash,
            'files': file_metadata,
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'total_files': len(file_metadata)
        }
        
        metadata_file = db_dir / "corpus_metadata.json"
        db_dir.mkdir(parents=True, exist_ok=True)
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def extract_from_pdf(pdf_path: Path, max_pages: Optional[int] = None) -> str:
        """Extrait le texte d'un PDF (utilise PyMuPDF si disponible pour meilleure qualité)"""
        try:
            if USE_PYMUPDF:
                # PyMuPDF (fitz) - Meilleur pour les PDFs multi-colonnes
                doc = fitz.open(pdf_path)
                num_pages = len(doc) if not max_pages else min(len(doc), max_pages)

                text_parts = []
                for page_num in range(num_pages):
                    try:
                        page = doc[page_num]

                        # Utiliser get_text("blocks") pour mieux respecter la structure
                        blocks = page.get_text("blocks")

                        # Détecter si la page a 2 colonnes
                        # Blocs texte uniquement
                        text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]

                        if not text_blocks:
                            text_parts.append("")
                            continue

                        # Calculer la position X médiane pour détecter colonnes
                        page_width = page.rect.width
                        mid_x = page_width / 2

                        # Séparer en colonnes gauche/droite
                        left_blocks = [b for b in text_blocks if (b[0] + b[2]) / 2 < mid_x]
                        right_blocks = [b for b in text_blocks if (b[0] + b[2]) / 2 >= mid_x]

                        # Si les deux colonnes existent, traiter séparément
                        if left_blocks and right_blocks:
                            # Trier chaque colonne de haut en bas
                            left_sorted = sorted(left_blocks, key=lambda b: b[1])
                            right_sorted = sorted(right_blocks, key=lambda b: b[1])

                            # Lire colonne gauche COMPLÈTE, puis colonne droite
                            page_text = ""

                            # Colonne gauche
                            for block in left_sorted:
                                text = block[4].strip()
                                if text:
                                    page_text += text + "\n"

                            page_text += "\n--- COLONNE DROITE ---\n\n"

                            # Colonne droite
                            for block in right_sorted:
                                text = block[4].strip()
                                if text:
                                    page_text += text + "\n"
                        else:
                            # Page simple colonne : tri normal
                            sorted_blocks = sorted(text_blocks, key=lambda b: (b[1], b[0]))
                            page_text = ""
                            for block in sorted_blocks:
                                text = block[4].strip()
                                if text:
                                    page_text += text + "\n"

                        text_parts.append(page_text)
                    except Exception as e:
                        # Si une page pose problème, on continue avec les autres
                        print(f"⚠️  Page {page_num + 1} ignorée (erreur: {str(e)[:50]})")
                        # Essayer extraction simple en fallback
                        try:
                            page_text = page.get_text("text")
                            text_parts.append(page_text)
                        except:
                            # Si même l'extraction simple échoue, on skip cette page
                            text_parts.append(f"[Page {page_num + 1} non extractible]")

                doc.close()
                return "\n".join(text_parts)

            elif USE_PDFPLUMBER:
                with pdfplumber.open(pdf_path) as pdf:
                    pages = pdf.pages[:max_pages] if max_pages else pdf.pages
                    return "\n".join([p.extract_text() or "" for p in pages])
            else:
                import PyPDF2
                with open(pdf_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    pages = reader.pages[:max_pages] if max_pages else reader.pages
                    return "\n".join([p.extract_text() or "" for p in pages])
        except Exception as e:
            return f"[Erreur extraction PDF: {e}]"
    
    @staticmethod
    def extract_from_text(file_path: Path) -> str:
        """Extrait le texte d'un fichier texte"""
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return f"[Erreur lecture fichier: {e}]"
    
    @staticmethod
    def extract_from_directory(directory: Path, max_pages: Optional[int] = None, progress_callback=None) -> Dict[str, Dict[str, Any]]:
        """Extrait tous les documents d'un répertoire avec callback de progression

        Returns:
            Dict avec structure: {
                "file_name": {
                    "content": str,
                    "category": str,  # "rules", "universe_book", "novel", "scenario"
                    "path": str
                }
            }
        """
        documents = {}
        if not directory.exists():
            return documents

        # Compter d'abord le nombre total de fichiers
        all_files = [f for f in directory.rglob("*")
                     if f.is_file() and f.suffix.lower() in [".pdf", ".txt", ".md"]]
        total_files = len(all_files)

        if progress_callback:
            progress_callback(0, total_files, "Scan des fichiers...")

        for idx, file_path in enumerate(all_files, 1):
            try:
                # Affichage console ET callback Streamlit
                print(f"📖 [{idx}/{total_files}] Extraction de : {file_path.name}")

                if progress_callback:
                    progress_callback(idx, total_files, file_path.name)

                suffix = file_path.suffix.lower()
                if suffix == ".pdf":
                    content = DocumentExtractor.extract_from_pdf(file_path, max_pages)
                else:
                    content = DocumentExtractor.extract_from_text(file_path)

                # Déterminer la catégorie basée sur le chemin
                relative_path = file_path.relative_to(directory)
                parts = relative_path.parts

                category = "unknown"
                if len(parts) > 0:
                    folder = parts[0].lower()
                    file_name = file_path.name.lower()

                    if folder == "regles" or "règles" in folder:
                        category = "rules"
                    elif folder == "univers":
                        # Distinguer livre d'univers des romans
                        if "livre 1" in file_name or "l'univers" in file_name or "univers" in file_name:
                            category = "universe_book"
                        else:
                            category = "novel"
                    elif folder == "scenarii" or "scenario" in folder:
                        category = "scenario"

                documents[file_path.name] = {
                    "content": content,
                    "category": category,
                    "path": str(relative_path)
                }
                print(f"   ✅ {len(content)} caractères extraits (catégorie: {category})")

            except Exception as e:
                if progress_callback:
                    progress_callback(idx, total_files, f"⚠️ Erreur: {file_path.name}")
                print(f"❌ Erreur lecture {file_path.name}: {e}")

        return documents


class VectorStore:
    """Gestion du stockage vectoriel avec Chroma"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.embedding_model = config['rag']['embedding_model']
        self.use_cuda = config['rag'].get('use_cuda', True)
        self.chunk_size = config['rag']['chunk_size']
        self.chunk_overlap = config['rag']['chunk_overlap']
        self._embeddings = None
        self._vectordb = None
    
    @property
    def embeddings(self):
        """Lazy loading des embeddings"""
        if self._embeddings is None:
            try:
                device = "cuda" if self.use_cuda else "cpu"
                self._embeddings = SentenceTransformerEmbeddings(
                    model_name=self.embedding_model,
                    model_kwargs={"device": device}
                )
            except Exception:
                # Fallback to CPU
                self._embeddings = SentenceTransformerEmbeddings(
                    model_name=self.embedding_model
                )
        return self._embeddings
    
    def build_or_load(self, documents: Dict[str, Dict[str, Any]], db_dir: Path, source_dir: Path, progress_callback=None) -> Chroma:
        """Construit ou charge la base vectorielle avec progression"""
        db_dir_str = str(db_dir)
        metadata_file = db_dir / "corpus_metadata.json"

        # Créer ou charger
        if not db_dir.exists() or not any(db_dir.iterdir()):
            print("\n🔧 Préparation des documents...")
            if progress_callback:
                progress_callback("Préparation des documents...")

            # Préparer les chunks avec métadonnées
            all_chunks = []

            for name, doc_data in documents.items():
                content = doc_data["content"]
                category = doc_data["category"]
                path = doc_data["path"]

                # Découper ce document en chunks
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap
                )
                doc_chunks = splitter.split_text(f"--- DOCUMENT: {name} ---\n\n{content}")

                # Créer des Documents avec métadonnées
                for chunk in doc_chunks:
                    all_chunks.append(
                        Document(
                            page_content=chunk,
                            metadata={
                                "source": name,
                                "category": category,
                                "path": path
                            }
                        )
                    )

            print(f"✅ {len(all_chunks)} chunks créés avec métadonnées")
            if progress_callback:
                progress_callback(f"Création de {len(all_chunks)} chunks...")

            db_dir.mkdir(parents=True, exist_ok=True)

            print(f"🧮 Génération des embeddings avec {self.embedding_model}...")
            print(f"   (Cela peut prendre plusieurs minutes pour {len(all_chunks)} vecteurs)")
            if progress_callback:
                progress_callback(f"Génération des embeddings ({len(all_chunks)} vecteurs)...")

            self._vectordb = Chroma.from_documents(
                documents=all_chunks,
                embedding=self.embeddings,
                persist_directory=db_dir_str
            )

            # Sauvegarder les métadonnées du corpus
            DocumentExtractor.save_corpus_metadata(source_dir, db_dir)

            print("✅ Base vectorielle créée avec succès !")
            if progress_callback:
                progress_callback("✅ Base vectorielle créée !")
        else:
            print("📂 Chargement de la base vectorielle existante...")
            if progress_callback:
                progress_callback("Chargement de la base existante...")

            self._vectordb = Chroma(
                persist_directory=db_dir_str,
                embedding_function=self.embeddings
            )

            # IMPORTANT: Sauvegarder les métadonnées si elles n'existent pas
            # (cas où la base existe mais pas le fichier de métadonnées)
            if not metadata_file.exists():
                if progress_callback:
                    progress_callback("Création des métadonnées manquantes...")
                DocumentExtractor.save_corpus_metadata(source_dir, db_dir)

            if progress_callback:
                progress_callback("✅ Base vectorielle chargée !")

        # Persist si possible
        try:
            self._vectordb.persist()
        except AttributeError:
            pass  # Nouvelle version de Chroma sans persist()

        return self._vectordb
    
    def reset(self, db_dir: Path):
        """Réinitialise la base vectorielle"""
        # Fermer proprement la connexion si elle existe
        if self._vectordb is not None:
            try:
                # Tenter de fermer la connexion (si la méthode existe)
                if hasattr(self._vectordb, '_client'):
                    self._vectordb._client = None
                del self._vectordb
            except Exception:
                pass
            self._vectordb = None

        # Attendre un peu pour que les fichiers soient libérés
        import time
        time.sleep(0.5)

        # Supprimer le répertoire avec gestion d'erreur robuste
        if db_dir.exists():
            try:
                shutil.rmtree(db_dir)
            except PermissionError:
                # Sur Windows, essayer avec rmtree en mode forcé
                import os
                def force_remove_readonly(func, path, exc_info):
                    os.chmod(path, 0o777)
                    func(path)

                try:
                    shutil.rmtree(db_dir, onerror=force_remove_readonly)
                except Exception as e:
                    raise RuntimeError(
                        f"Impossible de supprimer la base de données. "
                        f"Fermez l'application et supprimez manuellement le dossier '{db_dir}'. "
                        f"Erreur: {e}"
                    )

        db_dir.mkdir(parents=True, exist_ok=True)
    
    def get_retriever(self, k: int):
        """Retourne un retriever avec k documents"""
        if self._vectordb is None:
            raise ValueError("VectorDB not initialized. Call build_or_load first.")
        return self._vectordb.as_retriever(search_kwargs={"k": k})


class RAGChain:
    """Gestion de la chaîne RAG complète avec re-ranking"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        if not OllamaLLM_available:
            raise RuntimeError(
                "Ollama non disponible. Installe 'langchain-ollama' avec: "
                "pip install langchain-ollama"
            )

        # Initialiser le re-ranker si activé
        self.reranker = None
        if config['rag'].get('enable_reranking', False) and RERANKER_AVAILABLE:
            try:
                rerank_model = config['rag'].get('rerank_model', 'BAAI/bge-reranker-v2-m3')
                device = "cuda" if config['rag'].get('use_cuda', False) else "cpu"
                print(f"🔧 Chargement du re-ranker : {rerank_model} sur {device}...")
                self.reranker = CrossEncoder(rerank_model, device=device)
                print("✅ Re-ranker chargé avec succès")
            except Exception as e:
                print(f"⚠️ Impossible de charger le re-ranker : {e}")
                self.reranker = None

    def rerank_documents(self, query: str, documents: List, k: int) -> List:
        """Re-rank les documents selon leur pertinence avec la query"""
        if not self.reranker or not documents:
            return documents[:k]

        try:
            # Préparer les paires (query, doc) pour le re-ranker
            pairs = [[query, doc.page_content] for doc in documents]

            # Calculer les scores de pertinence
            scores = self.reranker.predict(pairs)

            # Trier les documents par score décroissant
            scored_docs = list(zip(documents, scores))
            scored_docs.sort(key=lambda x: x[1], reverse=True)

            # Retourner les k meilleurs
            reranked = [doc for doc, score in scored_docs[:k]]

            print(f"🎯 Re-ranking : {len(documents)} → {len(reranked)} chunks (scores: {scores[:3].tolist() if len(scores) > 0 else []}...)")

            return reranked
        except Exception as e:
            print(f"⚠️ Erreur re-ranking : {e}, fallback sur retrieval initial")
            return documents[:k]
    
    def create_llm(self, model_name: str, temperature: float, top_p: float):
        """Crée une instance LLM"""
        # Récupérer les paramètres du config
        num_ctx = self.config.get('model', {}).get('num_ctx', 8192)
        num_predict = self.config.get('model', {}).get('num_predict', 2048)

        try:
            return OllamaLLM(
                model=model_name,
                temperature=temperature,
                top_p=top_p,
                num_ctx=num_ctx,
                num_predict=num_predict
            )
        except TypeError:
            # Fallback si certains paramètres ne sont pas supportés
            try:
                return OllamaLLM(model=model_name, temperature=temperature, top_p=top_p)
            except TypeError:
                try:
                    return OllamaLLM(model=model_name, temperature=temperature)
                except Exception:
                    return OllamaLLM(model=model_name)
    
    def create_prompt(self, mode: str, system_prompt: str = "", memory: str = "", short_memory: str = "", level: str = "N/A") -> PromptTemplate:
        """Crée le prompt selon le mode avec les données déjà intégrées"""
        if mode == "mj":
            template = f"""
{system_prompt}

Mémoire de la partie :
{memory}

Contexte pertinent (extraits du corpus) :
{{context}}

Niveau de narration : {level}

Question / Action du joueur : {{question}}

Réponds en suivant ce format :
1. Description immersive (adapte la longueur au niveau choisi)
2. Propose 2 à 4 options claires (format: OPTION 1: ..., OPTION 2: ..., etc.)
3. Si nécessaire, liste les conséquences structurées:
   - [PNJ:Nom:Statut] (Statut: Ami, Ennemi, Neutre, etc.)
   - [Lieu:Nom:Statut] (Statut: Visité, Non visité, etc.)
   - [Intrigue:Nom:Statut] (Statut: Résolue, En cours, Bloquée, etc.)

Ta réponse :"""
            return PromptTemplate(
                template=template,
                input_variables=["context", "question"]
            )
        else:  # encyclo
            template = f"""
{system_prompt}

Mémoire des derniers échanges :
{short_memory}

===== CONTEXTE (extraits des documents) =====
{{context}}
===== FIN DU CONTEXTE =====

Question : {{question}}

⚠️ INSTRUCTIONS CRITIQUES :
1. CHERCHE d'abord le chunk qui contient une DÉFINITION ou DESCRIPTION directe du sujet
2. IGNORE les passages narratifs (scénarios, histoires, dialogues, noms de personnages)
3. PRIVILÉGIE les chunks avec : VD, M, C, MD, Sortilèges, Rituels (= descriptions de règles)
4. Si le Chunk #1 répond directement à la question, utilise-le en priorité
5. Cite directement et complètement le texte pertinent
6. Organise ta réponse avec des titres markdown (## et ###)
7. Si aucun chunk ne contient de définition/règle, dis-le clairement

Ta réponse :"""
            return PromptTemplate(
                template=template,
                input_variables=["context", "question"]
            )
    
    def create_qa_chain(
        self,
        retriever,
        model_name: str,
        mode: str,
        temperature: float,
        top_p: float,
        return_sources: bool = False,
        system_prompt: str = "",
        memory: str = "",
        short_memory: str = "",
        level: str = "N/A",
        query: str = ""  # Nouveau : query pour re-ranking
    ) -> RetrievalQA:
        """Crée la chaîne QA complète avec les paramètres intégrés au prompt et re-ranking"""
        llm = self.create_llm(model_name, temperature, top_p)
        prompt = self.create_prompt(mode, system_prompt, memory, short_memory, level)

        # Créer un retriever filtré pour le mode encyclopédique (exclut les novels)
        if mode == "encyclo" and not (self.reranker and query):
            # Si pas de re-ranking, créer un retriever filtré simple
            original_retriever = retriever

            class FilteredRetriever(BaseRetriever):
                """Retriever qui filtre les novels en mode encyclopédique"""
                base_retriever: Any
                mode: str

                class Config:
                    arbitrary_types_allowed = True

                def __init__(self, base_retriever, mode):
                    super().__init__(
                        base_retriever=base_retriever,
                        mode=mode
                    )

                def _get_relevant_documents(
                    self, query: str, *, run_manager: CallbackManagerForRetrieverRun = None
                ) -> List[Document]:
                    docs = self.base_retriever.invoke(query)
                    if self.mode == "encyclo":
                        before = len(docs)
                        docs = [doc for doc in docs if doc.metadata.get('category', '') != 'novel']
                        print(f"🔍 Filtre encyclopédique : {before} → {len(docs)} chunks (exclus: novels)")
                    return docs

            retriever = FilteredRetriever(original_retriever, mode)

        # Si re-ranking activé, wrapper le retriever
        elif self.reranker and query:
            original_retriever = retriever
            # Récupérer le k du slider depuis le retriever
            k_from_slider = retriever.search_kwargs.get('k', 50)

            class RerankedRetriever(BaseRetriever):
                """Retriever avec re-ranking intégré qui hérite de BaseRetriever"""
                base_retriever: Any
                reranker: Any
                config: Dict[str, Any]
                mode: str
                query_text: str
                k_final: int  # Nombre final de chunks après re-ranking (depuis slider)

                class Config:
                    arbitrary_types_allowed = True

                def __init__(self, base_retriever, reranker, config, mode, query_text, k_final):
                    super().__init__(
                        base_retriever=base_retriever,
                        reranker=reranker,
                        config=config,
                        mode=mode,
                        query_text=query_text,
                        k_final=k_final
                    )

                def _get_relevant_documents(
                    self, query: str, *, run_manager: CallbackManagerForRetrieverRun = None
                ) -> List[Document]:
                    """Méthode requise par BaseRetriever"""
                    # Récupérer beaucoup de documents initialement
                    k_initial = self.config['rag'].get('k_initial_retrieval', 100)

                    # DEBUG : Vérifier si le filtre ChromaDB est présent
                    current_filter = self.base_retriever.search_kwargs.get('filter', None)
                    print(f"🔍 Filtre ChromaDB actif : {current_filter}")

                    # Temporairement changer k du retriever (sans toucher au filtre)
                    old_k = self.base_retriever.search_kwargs.get('k', 10)
                    self.base_retriever.search_kwargs['k'] = k_initial

                    # Récupération initiale (utilise invoke au lieu de get_relevant_documents)
                    # Le filtre ChromaDB devrait être appliqué automatiquement
                    docs = self.base_retriever.invoke(query)

                    # Restaurer k original
                    self.base_retriever.search_kwargs['k'] = old_k

                    # Compter les catégories avant filtrage
                    from collections import Counter
                    categories_before = Counter([doc.metadata.get('category', 'unknown') for doc in docs])
                    print(f"📥 Récupéré {len(docs)} chunks - Catégories: {dict(categories_before)}")

                    # ⚡ Filtrage supplémentaire en mode encyclopédique (au cas où le filtre ChromaDB n'a pas fonctionné)
                    if self.mode == "encyclo":
                        before_filter = len(docs)
                        docs = [doc for doc in docs if doc.metadata.get('category', '') != 'novel']
                        after_filter = len(docs)
                        if before_filter != after_filter:
                            print(f"⚠️ ChromaDB n'a PAS filtré ! Post-filtrage : {before_filter} → {after_filter} chunks (novels enlevés)")
                        else:
                            print(f"✅ ChromaDB a correctement filtré (aucun novel trouvé)")

                    # Re-ranking avec k_final depuis le slider de l'interface
                    print(f"🎯 Utilisation du slider : k_final = {self.k_final}")
                    reranked = self.reranker(query, docs, self.k_final)
                    return reranked

            retriever = RerankedRetriever(original_retriever, self.rerank_documents, self.config, mode, query, k_from_slider)

        return RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            chain_type="stuff",
            chain_type_kwargs={"prompt": prompt},
            return_source_documents=return_sources
        )
    
    def query(
        self,
        qa_chain: RetrievalQA,
        question: str,
        mode: str,
        system_prompt: str,
        memory: str = "",
        level: str = "N/A",
        short_memory: str = ""
    ) -> Dict[str, Any]:
        """Exécute une requête sur la chaîne QA"""
        inputs = {
            "query": question,
            "question": question,
            "system_prompt": system_prompt
        }
        
        if mode == "mj":
            inputs["memory"] = memory
            inputs["level"] = level
        else:
            inputs["short_memory"] = short_memory
        
        result = qa_chain(inputs)
        
        # Normaliser le résultat
        if isinstance(result, dict):
            response_text = result.get("result") or result.get("output_text") or ""
            source_docs = result.get("source_documents", [])
        else:
            response_text = str(result)
            source_docs = []
        
        return {
            "response": response_text,
            "sources": source_docs,
            "confidence": self._calculate_confidence(source_docs)
        }
    
    def _calculate_confidence(self, source_docs: List) -> float:
        """Calcule un score de confiance basé sur les sources"""
        if not source_docs:
            return 0.0
        
        # Score simple basé sur le nombre de sources
        # Plus sophistiqué: utiliser les scores de similarité si disponibles
        return min(1.0, len(source_docs) / self.config['rag']['k_retrieval'])