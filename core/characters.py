"""
core/characters.py
Gestion des fiches de personnages
"""

from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

try:
    import pdfplumber
    USE_PDFPLUMBER = True
except ImportError:
    import PyPDF2
    USE_PDFPLUMBER = False


@dataclass
class Character:
    """Représente un personnage"""
    name: str
    file_path: Path
    content: str
    
    @property
    def short_preview(self, length: int = 200) -> str:
        """Retourne un aperçu court du contenu"""
        return self.content[:length] + "..." if len(self.content) > length else self.content


class CharacterManager:
    """Gestion des fiches de personnages"""
    
    def __init__(self, char_dir: Path):
        self.char_dir = char_dir
        self.char_dir.mkdir(parents=True, exist_ok=True)
        self._characters: Optional[List[Character]] = None
    
    @property
    def characters(self) -> List[Character]:
        """Liste des personnages (avec cache)"""
        if self._characters is None:
            self._characters = self._load_characters()
        return self._characters
    
    def refresh(self):
        """Force le rechargement des personnages"""
        self._characters = None
    
    def _load_characters(self) -> List[Character]:
        """Charge tous les personnages du répertoire"""
        characters = []
        
        if not self.char_dir.exists():
            return characters
        
        for file_path in sorted(self.char_dir.iterdir()):
            if not file_path.is_file():
                continue
            
            suffix = file_path.suffix.lower()
            if suffix not in [".txt", ".md", ".pdf"]:
                continue
            
            try:
                content = self._load_file(file_path)
                characters.append(Character(
                    name=file_path.stem,
                    file_path=file_path,
                    content=content
                ))
            except Exception as e:
                print(f"Erreur chargement {file_path.name}: {e}")
        
        return characters
    
    def _load_file(self, file_path: Path) -> str:
        """Charge le contenu d'un fichier"""
        if file_path.suffix.lower() == ".pdf":
            return self._load_pdf(file_path)
        else:
            return file_path.read_text(encoding="utf-8", errors="ignore")
    
    def _load_pdf(self, pdf_path: Path) -> str:
        """Charge un PDF"""
        try:
            if USE_PDFPLUMBER:
                with pdfplumber.open(pdf_path) as pdf:
                    return "\n".join([p.extract_text() or "" for p in pdf.pages])
            else:
                with open(pdf_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    return "\n".join([p.extract_text() or "" for p in reader.pages])
        except Exception as e:
            return f"Erreur lecture PDF: {e}"
    
    def get_character(self, name: str) -> Optional[Character]:
        """Récupère un personnage par son nom"""
        for char in self.characters:
            if char.name == name:
                return char
        return None
    
    def get_character_names(self) -> List[str]:
        """Retourne la liste des noms de personnages"""
        return [char.name for char in self.characters]
    
    def search_in_characters(self, query: str) -> List[Character]:
        """Recherche dans le contenu des personnages"""
        query_lower = query.lower()
        results = []
        
        for char in self.characters:
            if query_lower in char.name.lower() or query_lower in char.content.lower():
                results.append(char)
        
        return results
    
    def add_character(self, name: str, content: str, extension: str = ".txt") -> bool:
        """Ajoute un nouveau personnage"""
        try:
            file_path = self.char_dir / f"{name}{extension}"
            file_path.write_text(content, encoding="utf-8")
            self.refresh()
            return True
        except Exception as e:
            print(f"Erreur ajout personnage: {e}")
            return False
    
    def delete_character(self, name: str) -> bool:
        """Supprime un personnage"""
        char = self.get_character(name)
        if char:
            try:
                char.file_path.unlink()
                self.refresh()
                return True
            except Exception as e:
                print(f"Erreur suppression personnage: {e}")
                return False
        return False
    
    def export_all_as_text(self) -> str:
        """Exporte tous les personnages en un seul texte"""
        lines = []
        for char in self.characters:
            lines.append(f"=== {char.name} ===\n")
            lines.append(char.content)
            lines.append("\n" + "="*50 + "\n")
        
        return "\n".join(lines)