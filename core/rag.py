"""
core/rag.py
Module de gestion du RAG (Retrieval-Augmented Generation)
"""

import os
import pickle
import shutil
import hashlib
import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import streamlit as st

# Imports LangChain - obligatoires
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.callbacks import BaseCallbackHandler
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Import de l'agent pour les outils personnalisés
try:
    from langchain.agents import create_react_agent, AgentExecutor
except ImportError:
    try:
        from langchain.agents import create_tool_calling_agent, AgentExecutor
    except ImportError:
        try:
            from langgraph.prebuilt import create_react_agent
        except ImportError:
            create_react_agent = None
            create_tool_calling_agent = None

try:
    from langchain_ollama import ChatOllama
    OllamaLLM_available = True
except ImportError:
    OllamaLLM_available = False

try:
    from sentence_transformers import CrossEncoder
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False

# Ordre de preference pour l'extraction PDF :
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

from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.callbacks import BaseCallbackHandler

try:
    from langchain_ollama import ChatOllama
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

# Import pour chunking sémantique
try:
    from langchain_experimental.text_splitter import SemanticChunker
    SEMANTIC_CHUNKER_AVAILABLE = True
except ImportError:
    SEMANTIC_CHUNKER_AVAILABLE = False
    print("⚠️ SemanticChunker non disponible. Installe avec: pip install langchain-experimental")

# Import pour hybrid search (BM25)
try:
    from langchain_community.retrievers.bm25 import BM25Retriever
    BM25_AVAILABLE = True
except Exception:
    BM25_AVAILABLE = False
    print("⚠️ BM25 non disponible. Installe avec: pip install rank_bm25")


class SimpleEnsembleRetriever:
    """Fusion BM25 + vectoriel sans dépendance EnsembleRetriever."""

    def __init__(self, retrievers: list, weights: list):
        self.retrievers = retrievers
        self.weights = weights

    def invoke(self, query: str) -> list:
        seen, results = set(), []
        for retriever in self.retrievers:
            try:
                for doc in retriever.invoke(query):
                    key = doc.page_content[:120]
                    if key not in seen:
                        seen.add(key)
                        results.append(doc)
            except Exception:
                pass
        return results

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
    def extract_from_pdf(pdf_path: Path, max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """Extrait le texte page par page avec nettoyage headers/footers et détection sections.

        Returns: [{"page": int, "text": str, "section": str}, ...]
        """
        import re as _re

        if not USE_PYMUPDF:
            pages_out = []
            try:
                if USE_PDFPLUMBER:
                    with pdfplumber.open(pdf_path) as pdf:
                        pdf_pages = pdf.pages[:max_pages] if max_pages else pdf.pages
                        for i, p in enumerate(pdf_pages):
                            pages_out.append({"page": i + 1, "text": p.extract_text() or "", "section": ""})
                else:
                    import PyPDF2
                    with open(pdf_path, "rb") as f:
                        reader = PyPDF2.PdfReader(f)
                        pdf_pages = reader.pages[:max_pages] if max_pages else reader.pages
                        for i, p in enumerate(pdf_pages):
                            pages_out.append({"page": i + 1, "text": p.extract_text() or "", "section": ""})
            except Exception as e:
                pages_out.append({"page": 1, "text": f"[Erreur extraction PDF: {e}]", "section": ""})
            return pages_out

        try:
            doc = fitz.open(pdf_path)
            num_pages = len(doc) if not max_pages else min(len(doc), max_pages)

            # ── Pass 1 : détection des headers/footers répétitifs ────────────────
            sample_size = min(num_pages, 40)
            hf_count = {}
            for pn in range(sample_size):
                page = doc[pn]
                h = page.rect.height
                for block in page.get_text("blocks"):
                    if block[6] != 0:
                        continue
                    _, y0, _, y1, text = block[:5]
                    text = text.strip()
                    if not text or len(text) > 120:
                        continue
                    norm = _re.sub(r'\d+', 'N', text).strip()
                    if not norm:
                        continue
                    if y0 < h * 0.09 or y1 > h * 0.91:
                        hf_count[norm] = hf_count.get(norm, 0) + 1

            repeated = {t for t, c in hf_count.items() if c / sample_size > 0.28}

            # ── Taille de police médiane pour détecter les titres de section ─────
            font_sizes = []
            for pn in range(min(10, num_pages)):
                page = doc[pn]
                try:
                    for block in page.get_text("dict")["blocks"]:
                        if block.get("type") == 0:
                            for line in block.get("lines", []):
                                for span in line.get("spans", []):
                                    sz = span.get("size", 0)
                                    if sz > 0:
                                        font_sizes.append(sz)
                except Exception:
                    pass

            if font_sizes:
                font_sizes.sort()
                median_font = font_sizes[len(font_sizes) // 2]
            else:
                median_font = 11.0
            title_threshold = median_font * 1.3

            # ── Pass 2 : extraction filtrée page par page ─────────────────────────
            pages_out = []
            current_section = ""

            for pn in range(num_pages):
                try:
                    page = doc[pn]
                    h = page.rect.height
                    page_width = page.rect.width
                    mid_x = page_width / 2

                    try:
                        raw_blocks = page.get_text("dict")["blocks"]
                    except Exception:
                        raw_blocks = []

                    # Construire (bbox, texte, police_max) pour chaque bloc texte
                    text_blocks = []
                    for block in raw_blocks:
                        if block.get("type") != 0:
                            continue
                        bbox = block["bbox"]
                        block_text = ""
                        max_font = 0.0
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                block_text += span.get("text", "")
                                max_font = max(max_font, span.get("size", 0))
                            block_text += "\n"
                        block_text = block_text.strip()
                        if block_text:
                            text_blocks.append((bbox, block_text, max_font))

                    # Filtrer headers/footers
                    filtered = []
                    for bbox, text, font in text_blocks:
                        _, y0, _, y1 = bbox
                        if y0 < h * 0.09 or y1 > h * 0.91:
                            norm = _re.sub(r'\d+', 'N', text).strip()
                            if norm in repeated:
                                continue
                        filtered.append((bbox, text, font))

                    if not filtered:
                        pages_out.append({"page": pn + 1, "text": "", "section": current_section})
                        continue

                    # Détection 2 colonnes
                    left_blocks = [(b, t, f) for b, t, f in filtered if (b[0] + b[2]) / 2 < mid_x]
                    right_blocks = [(b, t, f) for b, t, f in filtered if (b[0] + b[2]) / 2 >= mid_x]

                    if left_blocks and right_blocks:
                        columns = [
                            sorted(left_blocks, key=lambda x: x[0][1]),
                            sorted(right_blocks, key=lambda x: x[0][1]),
                        ]
                    else:
                        columns = [sorted(filtered, key=lambda x: x[0][1])]

                    page_text = ""
                    for col_idx, col_blocks in enumerate(columns):
                        if col_idx > 0:
                            page_text += "\n"
                        for bbox, text, font in col_blocks:
                            if font >= title_threshold and len(text) < 100:
                                current_section = text.strip()
                                page_text += "\n## " + text.strip() + "\n"
                            else:
                                page_text += text + "\n"

                    pages_out.append({"page": pn + 1, "text": page_text.strip(), "section": current_section})

                except Exception as e:
                    print(f"⚠️  Page {pn + 1} ignorée (erreur: {str(e)[:60]})")
                    try:
                        fallback_text = doc[pn].get_text("text")
                        pages_out.append({"page": pn + 1, "text": fallback_text, "section": current_section})
                    except Exception:
                        pages_out.append({"page": pn + 1, "text": "", "section": current_section})

            doc.close()
            return pages_out

        except Exception as e:
            return [{"page": 1, "text": f"[Erreur extraction PDF: {e}]", "section": ""}]
    
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
                    pages_data = DocumentExtractor.extract_from_pdf(file_path, max_pages)
                    content = "\n".join(p["text"] for p in pages_data if p["text"])
                else:
                    content = DocumentExtractor.extract_from_text(file_path)
                    pages_data = None

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
                        if "livre 1" in file_name or "l'univers" in file_name or "univers" in file_name:
                            category = "universe_book"
                        else:
                            category = "novel"
                    elif folder == "scenarii" or "scenario" in folder:
                        category = "scenario"

                documents[file_path.name] = {
                    "content": content,
                    "category": category,
                    "path": str(relative_path),
                    "pages": pages_data,
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
                self._embeddings = HuggingFaceEmbeddings(
                    model_name=self.embedding_model,
                    model_kwargs={"device": device}
                )
            except Exception:
                # Fallback to CPU
                self._embeddings = HuggingFaceEmbeddings(
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

            # Préparer le splitter (sémantique si disponible, sinon fixe)
            if SEMANTIC_CHUNKER_AVAILABLE:
                print("🧠 Chunking sémantique activé (BAAI/bge-m3)")
                if progress_callback:
                    progress_callback("Chargement du modèle de chunking sémantique...")
                try:
                    splitter = SemanticChunker(
                        self.embeddings,
                        breakpoint_threshold_type="percentile",
                        breakpoint_threshold_amount=85
                    )
                    use_semantic = True
                except Exception as e:
                    print(f"⚠️ SemanticChunker échoué ({e}), fallback sur chunking fixe")
                    splitter = RecursiveCharacterTextSplitter(
                        chunk_size=self.chunk_size,
                        chunk_overlap=self.chunk_overlap
                    )
                    use_semantic = False
            else:
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap
                )
                use_semantic = False

            for name, doc_data in documents.items():
                content = doc_data["content"]
                category = doc_data["category"]
                path = doc_data["path"]
                pages_data = doc_data.get("pages")

                try:
                    if pages_data:
                        # Chunking par page : préserve le numéro de page dans les métadonnées
                        for page_info in pages_data:
                            page_text = page_info["text"].strip()
                            if not page_text:
                                continue
                            try:
                                page_chunks = splitter.split_text(page_text)
                            except Exception:
                                page_chunks = RecursiveCharacterTextSplitter(
                                    chunk_size=self.chunk_size,
                                    chunk_overlap=self.chunk_overlap
                                ).split_text(page_text)
                            for chunk in page_chunks:
                                all_chunks.append(Document(
                                    page_content=chunk,
                                    metadata={
                                        "source": name,
                                        "category": category,
                                        "path": path,
                                        "page": page_info["page"],
                                        "section": page_info["section"],
                                    }
                                ))
                    else:
                        # Fichiers non-PDF : comportement original sans métadonnée de page
                        doc_chunks = splitter.split_text(f"--- DOCUMENT: {name} ---\n\n{content}")
                        for chunk in doc_chunks:
                            all_chunks.append(Document(
                                page_content=chunk,
                                metadata={
                                    "source": name,
                                    "category": category,
                                    "path": path,
                                    "page": None,
                                    "section": "",
                                }
                            ))
                except Exception:
                    fallback = RecursiveCharacterTextSplitter(
                        chunk_size=self.chunk_size,
                        chunk_overlap=self.chunk_overlap
                    )
                    for chunk in fallback.split_text(f"--- DOCUMENT: {name} ---\n\n{content}"):
                        all_chunks.append(Document(
                            page_content=chunk,
                            metadata={"source": name, "category": category, "path": path}
                        ))

            chunk_type = "sémantiques" if use_semantic else "fixes"
            print(f"✅ {len(all_chunks)} chunks {chunk_type} créés avec métadonnées")
            if progress_callback:
                progress_callback(f"Création de {len(all_chunks)} chunks {chunk_type}...")

            # Sauvegarder les chunks pour BM25 (hybrid search)
            if BM25_AVAILABLE:
                bm25_file = db_dir / "bm25_docs.pkl"
                db_dir.mkdir(parents=True, exist_ok=True)
                with open(bm25_file, "wb") as f:
                    pickle.dump(all_chunks, f)
                print("✅ Index BM25 sauvegardé")

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

    def get_bm25_retriever(self, db_dir: Path, k: int = 20):
        """Charge et retourne un retriever BM25 depuis le pickle sauvegardé"""
        if not BM25_AVAILABLE:
            return None
        bm25_file = db_dir / "bm25_docs.pkl"
        if not bm25_file.exists():
            return None
        try:
            with open(bm25_file, "rb") as f:
                docs = pickle.load(f)
            retriever = BM25Retriever.from_documents(docs)
            retriever.k = k
            return retriever
        except Exception as e:
            print(f"⚠️ Impossible de charger BM25 : {e}")
            return None


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
            rerank_model = config['rag'].get('rerank_model', 'BAAI/bge-reranker-v2-m3')
            device = "cuda" if config['rag'].get('use_cuda', False) else "cpu"
            try:
                print(f"🔧 Chargement du re-ranker : {rerank_model} sur {device}...")
                self.reranker = CrossEncoder(rerank_model, device=device)
                print("✅ Re-ranker chargé avec succès")
            except Exception as e:
                if device == "cuda":
                    print(f"⚠️ CUDA indisponible pour le re-ranker ({e}), bascule sur CPU...")
                    try:
                        self.reranker = CrossEncoder(rerank_model, device="cpu")
                        print("✅ Re-ranker chargé sur CPU")
                    except Exception as e2:
                        print(f"⚠️ Impossible de charger le re-ranker sur CPU : {e2}")
                        self.reranker = None
                else:
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
        # num_ctx : priorité au slider UI, sinon config, sinon défaut 32K
        try:
            import streamlit as _st
            num_ctx = _st.session_state.get('num_ctx',
                      self.config.get('model', {}).get('num_ctx', 32768))
        except Exception:
            num_ctx = self.config.get('model', {}).get('num_ctx', 32768)
        num_predict = self.config.get('model', {}).get('num_predict', 2048)

        try:
            from langchain_ollama import ChatOllama

            # Modèles "thinking" (qwen3, gemma4, deepseek-r1…) : tout le raisonnement
            # part dans <think>...</think> et le content visible reste vide.
            # On désactive ce mode pour obtenir une réponse directe.
            _thinking_families = ('qwen3', 'gemma4', 'gemma3', 'deepseek-r1', 'qwq')
            extra = {}
            if any(f in model_name.lower() for f in _thinking_families):
                extra['think'] = False

            try:
                return ChatOllama(
                    model=model_name,
                    temperature=temperature,
                    top_p=top_p,
                    num_ctx=num_ctx,
                    num_predict=num_predict,
                    repeat_penalty=1.3,
                    **extra
                )
            except TypeError:
                try:
                    # think= non supporté — réessayer sans
                    return ChatOllama(
                        model=model_name,
                        temperature=temperature,
                        top_p=top_p,
                        num_ctx=num_ctx,
                        num_predict=num_predict,
                        repeat_penalty=1.3,
                    )
                except TypeError:
                    # repeat_penalty non supporté non plus
                    return ChatOllama(
                        model=model_name,
                        temperature=temperature,
                        top_p=top_p,
                        num_ctx=num_ctx,
                        num_predict=num_predict,
                    )
        except TypeError:
            # Fallback si certains paramètres ne sont pas supportés
            try:
                return ChatOllama(model=model_name, temperature=temperature, top_p=top_p)
            except TypeError:
                try:
                    return ChatOllama(model=model_name, temperature=temperature)
                except Exception:
                    return ChatOllama(model=model_name)
    
    def create_prompt(self, mode: str, system_prompt: str = "", memory: str = "", short_memory: str = "", level: str = "N/A") -> PromptTemplate:
        """Crée le prompt selon le mode avec les données déjà intégrées"""
        _level_instructions = {
            "Résumé court": (
                "LONGUEUR : 2 à 3 paragraphes courts et percutants. Va à l'essentiel."
            ),
            "Scène détaillée": (
                "LONGUEUR : 4 à 6 paragraphes. Inclus des détails sensoriels "
                "(sons, odeurs, lumières, textures) pour ancrer la scène."
            ),
            "Longue narration immersive": (
                "LONGUEUR : 8 à 12 paragraphes minimum. Développe chaque élément en profondeur : "
                "décors fouillés, atmosphère, dialogues, tensions dramatiques, arrière-pensées des "
                "personnages. Prends le temps de planter le décor, d'installer la tension, et de "
                "donner vie à chaque détail. Ne résume pas — décris, montre, fais ressentir."
            ),
        }
        level_instruction = _level_instructions.get(level, _level_instructions["Scène détaillée"])

        if mode == "mj":
            template = f"""
{system_prompt}

Mémoire de la partie :
{memory}

Contexte extrait des documents (utilise ces informations en priorité si elles sont pertinentes) :
{{context}}

{level_instruction}

Question / Action du joueur : {{question}}

Instructions :
- Si le contexte contient des informations pertinentes, utilise-les en priorité.
- Pour les demandes créatives (descriptions, PNJ, lieux, ambiances), utilise librement tes connaissances des Lames du Cardinal et de la France du XVIIème siècle.
- Ne mentionne jamais les "documents" ou le "contexte" dans ta réponse.
- Respecte impérativement les consignes de longueur indiquées ci-dessus.

Réponds en suivant ce format :
1. Description immersive (respecte les consignes de longueur)
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

{level_instruction}

⚠️ INSTRUCTIONS CRITIQUES :
1. CHERCHE d'abord le chunk qui contient une DÉFINITION ou DESCRIPTION directe du sujet
2. IGNORE les passages narratifs (scénarios, histoires, dialogues, noms de personnages)
3. PRIVILÉGIE les chunks avec : VD, M, C, MD, Sortilèges, Rituels (= descriptions de règles)
4. Si le Chunk #1 répond directement à la question, utilise-le en priorité
5. Cite directement et complètement le texte pertinent
6. Respecte impérativement le format demandé ci-dessus
7. Si aucun chunk ne contient de définition/règle, dis-le clairement
8. Cite tes sources avec (Réf.X) après chaque information issue des documents.
   Exemple : "Le score de Courage est de 3 par défaut (Réf.1)."
9. STOP dès que tu as répondu à la question. Ne répète JAMAIS une information déjà énoncée.
   Chaque fait doit apparaître UNE SEULE FOIS dans ta réponse.

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
    ) -> dict:
        """Crée une chaîne QA utilisant ChatOllama"""
        from langchain_core.prompts import ChatPromptTemplate
        
        llm = self.create_llm(model_name, temperature, top_p)
        prompt_template = self.create_prompt(mode, system_prompt, memory, short_memory, level)

        # Créer une chaîne RAG classique avec LCEL
        from langchain_core.runnables import RunnablePassthrough
        from operator import itemgetter
        
        # Créer la fonction de formatage du context
        def format_context(docs):
            context_text = "\n\n".join([doc.page_content for doc in docs])
            return context_text
        
        # Construire la chaîne
        chain = (
            {"context": itemgetter("context") | RunnablePassthrough(), "question": itemgetter("question")}
            | prompt_template
            | llm
        )
        
        return {
            "chain": chain,
            "retriever": retriever,
            "llm": llm,
            "prompt": prompt_template,
            "format_context": format_context
        }
    
    def query(
        self,
        qa_chain: dict,
        question: str,
        mode: str,
        system_prompt: str = "",
        memory: str = "",
        short_memory: str = "",
        level: str = "N/A"
    ) -> dict:
        """Exécute la recherche et génère une réponse"""
        try:
            # Récupérer les composants de la chaîne
            chain = qa_chain.get("chain")
            retriever = qa_chain.get("retriever")
            llm = qa_chain.get("llm")
            prompt = qa_chain.get("prompt")
            format_context = qa_chain.get("format_context")
            
            if not chain or not retriever:
                raise ValueError("Chaîne QA invalide")
            
            # Récupérer les documents
            docs = retriever.invoke(question)
            
            # Utiliser la fonction de formatage du context
            context_text = format_context(docs)
            
            # Formater les variables pour le prompt
            input_data = {
                "question": question,
                "context": context_text,
                "mode": mode,
                "level": level,
                "memory": memory,
                "system_prompt": system_prompt
            }
            
            # Exécuter la chaîne
            response = chain.invoke(input_data)
            
            return {
                "response": response,
                "sources": docs,
                "success": True
            }
            
        except Exception as e:
            raise e
    
    def get_base_llm(self, model_name: str = None):
        """Retourne une instance de base LLM (wrapper pour backward compatibility)"""
        return None