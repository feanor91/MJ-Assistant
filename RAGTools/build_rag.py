# -*- coding: utf-8 -*-
import fitz
import re
import sys
from pathlib import Path


# =========================================================
# NETTOYAGE DE TEXTE
# =========================================================
def filter_special_chars(text: str) -> str:
    # Codepoints autorises hors Latin-1 - construits via chr() pour eviter
    # tout probleme d'encodage de fichier source Python.
    # 0x0152=Oe 0x0153=oe  0x2014=-- 0x2013=-  0x2026=...
    # 0x2018=' 0x2019='  0x201C=" 0x201D="
    ALLOWED = frozenset(
        chr(0x0152) + chr(0x0153)
        + chr(0x2014) + chr(0x2013) + chr(0x2026)
        + chr(0x2018) + chr(0x2019)
        + chr(0x201C) + chr(0x201D)
    )
    result = []
    for c in text:
        if ord(c) < 0x0100 or c in ALLOWED:
            result.append(c)
        else:
            result.append(' ')
    return re.sub(r'[ \t]+', ' ', ''.join(result))


def join_short_lines(text: str) -> str:
    """Joint les courtes lignes orphelines de la mise en page 2 colonnes PDF."""
    lines = text.split('\n')
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Ligne courte + suivante commence en minuscule = probablement meme phrase
        if (line and i + 1 < len(lines) and lines[i + 1]
                and len(line) < 45
                and not line.endswith(('.', '!', '?', ':', ';'))
                and lines[i + 1][0].islower()):
            result.append(line + ' ' + lines[i + 1])
            i += 2
        else:
            result.append(line)
            i += 1
    return '\n'.join(result)


def clean_page_text(raw_text: str) -> str:
    """Nettoie le texte en preservant les sauts de paragraphe."""
    # Supprime controles sauf \n (\x0a = 10, hors des plages supprimees)
    text = re.sub(r'[\x00-\x09\x0b-\x1f\x7f]', ' ', raw_text)
    # Joint les mots coupes par tiret de fin de ligne
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
    # Filtre caracteres speciaux
    text = filter_special_chars(text)
    # Normalise espaces sur chaque ligne
    lines = text.split('\n')
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in lines]
    text = '\n'.join(lines)
    # Joint les lignes courtes orphelines (artefact 2 colonnes PDF)
    text = join_short_lines(text)
    # Compresse les lignes vides multiples
    lines = text.split('\n')
    result = []
    prev_empty = False
    for line in lines:
        if not line:
            if not prev_empty:
                result.append('')
            prev_empty = True
        else:
            result.append(line)
            prev_empty = False
    return '\n'.join(result).strip()


def clean_text(text: str) -> str:
    """Version plate (sans structure) pour les detections TOC etc."""
    text = re.sub(r'[\x00-\x1f\x7f]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# =========================================================
# FILTRAGE LIGNES PARASITES
# =========================================================
def is_noise_line(line: str) -> bool:
    patterns = [
        r'^©',
        r'©\s*20\d\d',
        r'illustration par',
        r'elder craft',
        r'lames du cardinal.*illustration',
        r'copyright',
        r'^\s*\d+\s*$',
    ]
    return any(re.search(p, line, re.IGNORECASE) for p in patterns)


def filter_noise_lines(raw_text: str) -> str:
    """Filtre les lignes parasites sur le texte brut (avant nettoyage)."""
    lines = raw_text.split('\n')
    return '\n'.join(
        line for line in lines
        if not is_noise_line(line.strip())
    )


# =========================================================
# CHUNKING PAR PARAGRAPHES
# =========================================================
def chunk_text(text: str, max_size: int = 1000) -> list:
    """Decoupe en chunks en respectant les lignes/paragraphes."""
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

    chunks = []
    current_parts = []
    current_size = 0

    for p in paragraphs:
        if current_size + len(p) + 1 > max_size and current_parts:
            chunks.append('\n'.join(current_parts))
            current_parts = [p]
            current_size = len(p)
        else:
            current_parts.append(p)
            current_size += len(p) + 1

    if current_parts:
        chunks.append('\n'.join(current_parts))

    return [c for c in chunks if len(c.strip()) >= 30]


# =========================================================
# TOC DEPUIS BOOKMARKS PDF
# =========================================================
def extract_toc_from_pdf_outline(doc) -> list:
    """Utilise les signets embarques dans le PDF (le plus fiable)."""
    toc_raw = doc.get_toc()
    if len(toc_raw) >= 3:
        return [{"title": title, "page": page, "level": level}
                for level, title, page in toc_raw]
    return []


# =========================================================
# TOC LAYOUT EXTRACTION (fallback secondaire)
# =========================================================
def extract_toc_from_layout(page) -> list:
    blocks = page.get_text("blocks")
    page_width = page.rect.width
    mid = page_width / 2
    left_col, right_col = [], []

    for b in blocks:
        x0, y0, x1, y1, text, *_ = b
        text = clean_text(text)
        if not text or is_noise_line(text):
            continue
        if x0 < mid:
            left_col.append((y0, text))
        else:
            right_col.append((y0, text))

    left_col.sort()
    right_col.sort()
    toc = []

    for i in range(min(len(left_col), len(right_col))):
        title = left_col[i][1]
        match = re.search(r"(\d{1,4})", right_col[i][1])
        if match:
            toc.append({"title": title, "page": int(match.group(1)), "level": 1})

    return toc


# =========================================================
# FALLBACK TOC PAR TEXTE (recoit texte brut avec \n)
# =========================================================
def extract_toc_fallback(raw_text: str) -> list:
    """Parsing ligne par ligne sur le texte brut."""
    toc = []
    pat_arrow = re.compile(r"^(.*?)\s*(?:->|→)\s*(?:page\s*)?(\d{1,4})", re.IGNORECASE)
    pat_inline = re.compile(r"^(.+?)\s+(\d{1,3})\s*$")

    for line in raw_text.split("\n"):
        line = clean_text(line)
        if not line or is_noise_line(line):
            continue
        m = pat_arrow.search(line)
        if m:
            toc.append({"title": m.group(1).strip(), "page": int(m.group(2)), "level": 1})
            continue
        m = pat_inline.match(line)
        if m and len(m.group(1).strip()) > 3:
            toc.append({"title": m.group(1).strip(), "page": int(m.group(2)), "level": 1})

    return toc


# =========================================================
# DETECTION PAGE TOC
# =========================================================
def is_toc_page(text: str) -> bool:
    if re.search(r'table\s+des\s+mati[e\xe8]res', text, re.IGNORECASE):
        return True
    # Heuristique : densite elevee de nombres = liste d'entrees TOC
    num_count = len(re.findall(r'\b\d{1,3}\b', text))
    word_count = len(text.split())
    if word_count > 30 and num_count / max(word_count, 1) > 0.15:
        return True
    return False


# =========================================================
# MAP PAGE -> BREADCRUMB DE SECTION
# =========================================================
def build_section_map(toc: list, total_pages: int) -> dict:
    """Pour chaque page, construit le breadcrumb hierarchique actif
    en suivant les entrees de la TOC triees par page."""
    toc_sorted = sorted(toc, key=lambda x: (x['page'], x.get('level', 1)))

    section_map = {}
    active = {}   # level -> title
    toc_idx = 0

    for page in range(1, total_pages + 1):
        # Avance dans la TOC jusqu'a inclure toutes les entrees <= page
        while toc_idx < len(toc_sorted) and toc_sorted[toc_idx]['page'] <= page:
            entry = toc_sorted[toc_idx]
            level = entry.get('level', 1)
            active[level] = entry['title']
            # Reinitialise les sous-niveaux quand on monte de niveau
            for lvl in list(active.keys()):
                if lvl > level:
                    del active[lvl]
            toc_idx += 1

        if active:
            breadcrumb = ' > '.join(active[l] for l in sorted(active.keys()))
            section_map[page] = breadcrumb

    return section_map


# =========================================================
# PDF PROCESSING
# =========================================================
def process_pdf(pdf_path: Path):
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    # 1. TOC depuis bookmarks PDF (source primaire)
    toc = extract_toc_from_pdf_outline(doc)
    toc_found = len(toc) >= 3

    # 2. Map page -> breadcrumb
    section_map = build_section_map(toc, total_pages) if toc_found else {}

    chunks = []
    in_toc = False

    for page_num, page in enumerate(doc, start=1):
        raw_text = page.get_text("text")
        # Detection TOC sur texte brut (avant filtrage) pour que
        # la densite de chiffres soit preservee
        raw_clean = clean_text(raw_text)

        # -- Detection / skip des pages TOC --
        if is_toc_page(raw_clean):
            if not toc_found:
                toc = extract_toc_from_layout(page)
                if not toc or len(toc) < 3:
                    toc = extract_toc_fallback(raw_text)
                if toc:
                    section_map = build_section_map(toc, total_pages)
                toc_found = True
            in_toc = True
            continue

        if in_toc:
            in_toc = False

        # -- Skip des pages sans section (avant la premiere entree TOC) --
        # Titre, credits, pages blanches d'illustration...
        section = section_map.get(page_num)
        if section_map and section is None:
            continue

        # -- Filtre bruit + nettoyage structure --
        filtered_raw = filter_noise_lines(raw_text)
        text = clean_page_text(filtered_raw)

        if not text or len(text) < 30:
            continue

        # -- Chunking --
        for i, chunk in enumerate(chunk_text(text)):
            chunks.append({
                "page": page_num,
                "chunk_id": f"p{page_num}_{i}",
                "section": section or "",
                "text": chunk,
            })

    return chunks, toc


# =========================================================
# EXPORT MARKDOWN
# =========================================================
def save_markdown(chunks, toc, output_path: Path):
    with open(output_path, "w", encoding="utf-8") as f:

        if toc:
            f.write("# TABLE DES MATIERES\n\n")
            for item in toc:
                level = item.get("level", 1)
                indent = "  " * (level - 1)
                f.write(f"{indent}- {item['title']} -> page {item['page']}\n")

        f.write("\n\n# CONTENU\n")

        for c in chunks:
            section = c.get("section", "")
            f.write(f"\n\n### PAGE {c['page']} | {c['chunk_id']}\n")
            if section:
                f.write(f"**[{section}]**\n\n")
            f.write(c["text"])


# =========================================================
# MAIN
# =========================================================
def main():
    if len(sys.argv) < 2:
        print("Usage: python build_rag.py <pdf>")
        return

    pdf_path = Path(sys.argv[1])
    print(f"Processing: {pdf_path.name}")

    chunks, toc = process_pdf(pdf_path)

    output_file = pdf_path.with_suffix(".md")
    save_markdown(chunks, toc, output_file)

    print(f"Done -> {output_file}")
    print(f"Chunks: {len(chunks)}")
    print(f"TOC entries: {len(toc) if toc else 0}")


if __name__ == "__main__":
    main()
