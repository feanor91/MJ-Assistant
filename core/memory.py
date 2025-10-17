"""
core/memory.py
Gestion de la mémoire des sessions (MJ et Encyclopédique)
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class MemoryEntry:
    """Représente un échange dans la mémoire"""
    
    def __init__(self, user_message: str, assistant_message: str, timestamp: Optional[str] = None):
        self.user = user_message
        self.assistant = assistant_message
        self.timestamp = timestamp or datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "user": self.user,
            "assistant": self.assistant,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'MemoryEntry':
        return cls(
            user_message=data["user"],
            assistant_message=data["assistant"],
            timestamp=data.get("timestamp")
        )
    
    def format_for_prompt(self, prefix_user: str = "Joueur", prefix_assistant: str = "MJ") -> str:
        """Format pour injection dans un prompt"""
        return f"{prefix_user}: {self.user}\n{prefix_assistant}: {self.assistant}"


class Memory:
    """Gestion de la mémoire avec limite de taille"""
    
    def __init__(self, max_size: int, memory_file: Optional[Path] = None):
        self.max_size = max_size
        self.memory_file = memory_file
        self.entries: List[MemoryEntry] = []
        
        if memory_file and memory_file.exists():
            self.load()
    
    def add(self, user_message: str, assistant_message: str):
        """Ajoute un nouvel échange"""
        entry = MemoryEntry(user_message, assistant_message)
        self.entries.append(entry)
        
        # Limite la taille
        if len(self.entries) > self.max_size:
            self.entries = self.entries[-self.max_size:]
        
        # Auto-save si fichier défini
        if self.memory_file:
            self.save()
    
    def get_recent(self, n: int) -> List[MemoryEntry]:
        """Récupère les n derniers échanges"""
        return self.entries[-n:] if self.entries else []
    
    def format_for_prompt(self, n: Optional[int] = None, prefix_user: str = "Joueur", prefix_assistant: str = "MJ") -> str:
        """Formate la mémoire pour injection dans un prompt"""
        entries = self.get_recent(n) if n else self.entries
        if not entries:
            return "Aucune mémoire de partie pour le moment."
        
        return "\n\n".join([
            entry.format_for_prompt(prefix_user, prefix_assistant)
            for entry in entries
        ])
    
    def clear(self):
        """Efface la mémoire"""
        self.entries = []
        if self.memory_file:
            self.save()
    
    def save(self):
        """Sauvegarde la mémoire"""
        if not self.memory_file:
            return
        
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            data = [entry.to_dict() for entry in self.entries]
            self.memory_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"Erreur sauvegarde mémoire: {e}")
    
    def load(self):
        """Charge la mémoire depuis le fichier"""
        if not self.memory_file or not self.memory_file.exists():
            return
        
        try:
            data = json.loads(self.memory_file.read_text(encoding="utf-8"))
            self.entries = [MemoryEntry.from_dict(e) for e in data]
            
            # Limite après chargement
            if len(self.entries) > self.max_size:
                self.entries = self.entries[-self.max_size:]
        except Exception as e:
            print(f"Erreur chargement mémoire: {e}")
            self.entries = []
    
    def __len__(self) -> int:
        return len(self.entries)
    
    def __bool__(self) -> bool:
        return len(self.entries) > 0


class SessionManager:
    """Gestion des sessions complètes"""
    
    def __init__(self, save_dir: Path):
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)
    
    def save_session(
        self,
        session_name: str,
        mj_memory: Memory,
        encyclo_memory: Memory,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Sauvegarde une session complète"""
        try:
            session_file = self.save_dir / f"{session_name}.json"
            data = {
                "session_name": session_name,
                "timestamp": datetime.now().isoformat(),
                "mj_memory": [e.to_dict() for e in mj_memory.entries],
                "encyclo_memory": [e.to_dict() for e in encyclo_memory.entries],
                "metadata": metadata or {}
            }
            
            session_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            return True
        except Exception as e:
            print(f"Erreur sauvegarde session: {e}")
            return False
    
    def load_session(
        self,
        session_name: str
    ) -> Optional[Dict[str, Any]]:
        """Charge une session"""
        try:
            session_file = self.save_dir / f"{session_name}.json"
            if not session_file.exists():
                return None
            
            data = json.loads(session_file.read_text(encoding="utf-8"))
            
            # Convertir en objets Memory
            mj_entries = [MemoryEntry.from_dict(e) for e in data.get("mj_memory", [])]
            encyclo_entries = [MemoryEntry.from_dict(e) for e in data.get("encyclo_memory", [])]
            
            return {
                "session_name": data.get("session_name"),
                "timestamp": data.get("timestamp"),
                "mj_entries": mj_entries,
                "encyclo_entries": encyclo_entries,
                "metadata": data.get("metadata", {})
            }
        except Exception as e:
            print(f"Erreur chargement session: {e}")
            return None
    
    def list_sessions(self) -> List[str]:
        """Liste toutes les sessions disponibles"""
        if not self.save_dir.exists():
            return []
        
        return sorted([
            f.stem for f in self.save_dir.glob("*.json")
        ])
    
    def delete_session(self, session_name: str) -> bool:
        """Supprime une session"""
        try:
            session_file = self.save_dir / f"{session_name}.json"
            if session_file.exists():
                session_file.unlink()
                return True
            return False
        except Exception as e:
            print(f"Erreur suppression session: {e}")
            return False


class Statistics:
    """Statistiques de session"""
    
    def __init__(self):
        self.total_queries = 0
        self.successful_queries = 0
        self.failed_queries = 0
        self.total_tokens = 0  # À implémenter si disponible
        self.session_start = datetime.now()
    
    def record_query(self, success: bool = True):
        """Enregistre une requête"""
        self.total_queries += 1
        if success:
            self.successful_queries += 1
        else:
            self.failed_queries += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Retourne un résumé des statistiques"""
        duration = datetime.now() - self.session_start
        return {
            "total_queries": self.total_queries,
            "successful_queries": self.successful_queries,
            "failed_queries": self.failed_queries,
            "success_rate": (
                self.successful_queries / self.total_queries * 100
                if self.total_queries > 0 else 0
            ),
            "session_duration": str(duration).split('.')[0],  # Format HH:MM:SS
        }