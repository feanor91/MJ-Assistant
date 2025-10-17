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

try:
    from langchain_ollama import OllamaLLM
    OllamaLLM_available = True
except ImportError:
    try:
        from langchain_community.llms import Ollama as OllamaLLM
        OllamaLLM_available = True
    except ImportError:
        OllamaLLM_available = False


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
        """Extrait le texte d'un PDF"""
        try:
            if USE_PDFPLUMBER:
                with pdfplumber.open(pdf_path) as pdf:
                    pages = pdf.pages[:max_pages] if max_pages else pdf.pages
                    return "\n".join([p.extract_text() or "" for p in pages])
            else:
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
    def extract_from_directory(directory: Path, max_pages: Optional[int] = None, progress_callback=None) -> Dict[str, str]:
        """Extrait tous les documents d'un répertoire avec callback de progression"""
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
                if progress_callback:
                    progress_callback(idx, total_files, f"Lecture: {file_path.name}")
                
                suffix = file_path.suffix.lower()
                if suffix == ".pdf":
                    content = DocumentExtractor.extract_from_pdf(file_path, max_pages)
                else:
                    content = DocumentExtractor.extract_from_text(file_path)
                
                documents[file_path.name] = content
                
            except Exception as e:
                if progress_callback:
                    progress_callback(idx, total_files, f"⚠️ Erreur: {file_path.name}")
                print(f"Erreur lecture {file_path.name}: {e}")
        
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
    
    def build_or_load(self, documents: Dict[str, str], db_dir: Path, source_dir: Path, progress_callback=None) -> Chroma:
        """Construit ou charge la base vectorielle avec progression"""
        db_dir_str = str(db_dir)
        metadata_file = db_dir / "corpus_metadata.json"
        
        # Créer ou charger
        if not db_dir.exists() or not any(db_dir.iterdir()):
            if progress_callback:
                progress_callback("Préparation des documents...")
            
            # Combine tous les documents
            full_text = "\n\n".join([
                f"--- DOCUMENT: {name} ---\n\n{content}"
                for name, content in documents.items()
            ])
            
            if progress_callback:
                progress_callback(f"Découpage en chunks (taille: {self.chunk_size})...")
            
            # Split en chunks
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            chunks = splitter.split_text(full_text)
            
            if progress_callback:
                progress_callback(f"Création de {len(chunks)} chunks...")
            
            db_dir.mkdir(parents=True, exist_ok=True)
            
            if progress_callback:
                progress_callback(f"Génération des embeddings ({len(chunks)} vecteurs)...")
            
            self._vectordb = Chroma.from_documents(
                documents=[Document(page_content=c) for c in chunks],
                embedding=self.embeddings,
                persist_directory=db_dir_str
            )
            
            # Sauvegarder les métadonnées du corpus
            DocumentExtractor.save_corpus_metadata(source_dir, db_dir)
            
            if progress_callback:
                progress_callback("✅ Base vectorielle créée !")
        else:
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
        if db_dir.exists():
            shutil.rmtree(db_dir)
        db_dir.mkdir(parents=True, exist_ok=True)
        self._vectordb = None
    
    def get_retriever(self, k: int):
        """Retourne un retriever avec k documents"""
        if self._vectordb is None:
            raise ValueError("VectorDB not initialized. Call build_or_load first.")
        return self._vectordb.as_retriever(search_kwargs={"k": k})


class RAGChain:
    """Gestion de la chaîne RAG complète"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        if not OllamaLLM_available:
            raise RuntimeError(
                "Ollama non disponible. Installe 'langchain-ollama' avec: "
                "pip install langchain-ollama"
            )
    
    def create_llm(self, model_name: str, temperature: float, top_p: float):
        """Crée une instance LLM"""
        try:
            return OllamaLLM(model=model_name, temperature=temperature, top_p=top_p)
        except TypeError:
            # Fallback si certains paramètres ne sont pas supportés
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

Contexte pertinent (extraits du corpus) :
{{context}}

Question : {{question}}

Réponse factuelle (basée uniquement sur le contexte) :"""
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
        level: str = "N/A"
    ) -> RetrievalQA:
        """Crée la chaîne QA complète avec les paramètres intégrés au prompt"""
        llm = self.create_llm(model_name, temperature, top_p)
        prompt = self.create_prompt(mode, system_prompt, memory, short_memory, level)
        
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