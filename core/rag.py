"""
core/rag.py
Module de gestion du RAG (Retrieval-Augmented Generation)
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
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
    def extract_from_directory(directory: Path, max_pages: Optional[int] = None) -> Dict[str, str]:
        """Extrait tous les documents d'un répertoire"""
        documents = {}
        if not directory.exists():
            return documents
        
        for file_path in sorted(directory.rglob("*")):
            if not file_path.is_file():
                continue
            
            suffix = file_path.suffix.lower()
            if suffix not in [".pdf", ".txt", ".md"]:
                continue
            
            try:
                if suffix == ".pdf":
                    content = DocumentExtractor.extract_from_pdf(file_path, max_pages)
                else:
                    content = DocumentExtractor.extract_from_text(file_path)
                
                documents[file_path.name] = content
            except Exception as e:
                st.warning(f"Impossible de lire {file_path.name}: {e}")
        
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
    
    def build_or_load(self, documents: Dict[str, str], db_dir: Path) -> Chroma:
        """Construit ou charge la base vectorielle"""
        # Combine tous les documents
        full_text = "\n\n".join([
            f"--- DOCUMENT: {name} ---\n\n{content}"
            for name, content in documents.items()
        ])
        
        # Split en chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        chunks = splitter.split_text(full_text)
        
        db_dir_str = str(db_dir)
        
        # Créer ou charger
        if not db_dir.exists() or not any(db_dir.iterdir()):
            db_dir.mkdir(parents=True, exist_ok=True)
            self._vectordb = Chroma.from_documents(
                documents=[Document(page_content=c) for c in chunks],
                embedding=self.embeddings,
                persist_directory=db_dir_str
            )
        else:
            self._vectordb = Chroma(
                persist_directory=db_dir_str,
                embedding_function=self.embeddings
            )
        
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
    
    def create_prompt(self, mode: str) -> PromptTemplate:
        """Crée le prompt selon le mode"""
        if mode == "mj":
            template = """
{system_prompt}

Mémoire de la partie :
{memory}

Contexte pertinent (extraits du corpus) :
{context}

Niveau de narration : {level}

Question / Action du joueur : {question}

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
                input_variables=["context", "question", "memory", "level", "system_prompt"]
            )
        else:  # encyclo
            template = """
{system_prompt}

Mémoire des derniers échanges :
{short_memory}

Contexte pertinent (extraits du corpus) :
{context}

Question : {question}

Réponse factuelle (basée uniquement sur le contexte) :"""
            return PromptTemplate(
                template=template,
                input_variables=["context", "question", "short_memory", "system_prompt"]
            )
    
    def create_qa_chain(
        self,
        retriever,
        model_name: str,
        mode: str,
        temperature: float,
        top_p: float,
        return_sources: bool = False
    ) -> RetrievalQA:
        """Crée la chaîne QA complète"""
        llm = self.create_llm(model_name, temperature, top_p)
        prompt = self.create_prompt(mode)
        
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