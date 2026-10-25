"""Knowledge Base and RAG retrieval module for ZentroMart Customer Support.

Implements Step 2:
- Loads 21 markdown documents from kb/ and product catalog from data/products.csv.
- Chunks by [SECTION-ID] and preserves metadata: doc_id, section_id, doc_type, status, effective_from.
- Encodes chunks using sentence-transformers (all-MiniLM-L6-v2) and indexes with FAISS.
- Respects document precedence: Current Policy > Agent Guide > Help > FAQ > Marketing.
- Superseded documents (e.g. pol_returns_v3_superseded.md) are demoted/filtered.
- Records source chunks for evidence attribution.
"""
import os
import re
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer

from src.config import (
    KB_DIR, DATA_DIR, EMBEDDING_MODEL_NAME, RETRIEVAL_TOP_K,
    SIMILARITY_THRESHOLD, POLICY_PRECEDENCE, SUPERSEDED_FILES
)

class KnowledgeBaseChunk:
    """Represents an indexed document or catalog chunk with full metadata."""
    def __init__(
        self,
        chunk_id: str,
        section_id: str,
        doc_id: str,
        title: str,
        doc_type: str,
        status: str,
        effective_from: str,
        filename: str,
        text: str,
    ):
        self.chunk_id = chunk_id
        self.section_id = section_id
        self.doc_id = doc_id
        self.title = title
        self.doc_type = doc_type
        self.status = status
        self.effective_from = effective_from
        self.filename = filename
        self.text = text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "section_id": self.section_id,
            "doc_id": self.doc_id,
            "title": self.title,
            "doc_type": self.doc_type,
            "status": self.status,
            "effective_from": self.effective_from,
            "filename": self.filename,
            "text": self.text,
        }

class KnowledgeBase:
    """Vector database and semantic search engine for ZentroMart."""

    def __init__(
        self,
        kb_dir: Optional[Path] = None,
        model_name: str = EMBEDDING_MODEL_NAME,
        top_k: int = RETRIEVAL_TOP_K,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
    ):
        self.kb_dir = kb_dir or KB_DIR
        self.model_name = model_name
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        
        self.model = SentenceTransformer(self.model_name)
        self.chunks: List[KnowledgeBaseChunk] = []
        self.index: Optional[faiss.IndexFlatIP] = None
        self._load_and_index()

    def _parse_frontmatter(self, content: str) -> Tuple[Dict[str, str], str]:
        """Extract YAML-like frontmatter metadata and body from markdown file."""
        metadata = {}
        body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                raw_fm = parts[1]
                body = parts[2].strip()
                for line in raw_fm.strip().splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        metadata[k.strip()] = v.strip()
        return metadata, body

    def _load_and_index(self):
        """Parse markdown KB documents and products.csv into chunks, then build FAISS index."""
        cache_dir = self.kb_dir.parent / ".cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        index_cache = cache_dir / "kb_faiss.index"
        chunks_cache = cache_dir / "kb_chunks.pkl"

        # Load from disk cache if present for instant startup
        if index_cache.exists() and chunks_cache.exists():
            try:
                self.index = faiss.read_index(str(index_cache))
                with open(chunks_cache, "rb") as f:
                    self.chunks = pickle.load(f)
                return
            except Exception:
                pass

        self.chunks = []
        
        # 1. Parse KB markdown files
        for md_file in self.kb_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            meta, body = self._parse_frontmatter(content)
            
            doc_id = meta.get("doc_id", md_file.stem)
            title = meta.get("title", md_file.stem)
            doc_type = meta.get("doc_type", "policy")
            status = meta.get("status", "current")
            effective_from = meta.get("effective_from", "2026-01-01")
            
            # Split sections by '## [SECTION-ID]'
            sections = re.split(r"(?=^##\s*\[[^\]]+\])", body, flags=re.MULTILINE)
            for idx, sec in enumerate(sections):
                sec = sec.strip()
                if not sec:
                    continue
                
                sec_match = re.search(r"^##\s*\[([^\]]+)\]\s*(.*)", sec, re.MULTILINE)
                if sec_match:
                    sec_id = sec_match.group(1).strip()
                    sec_title = sec_match.group(2).strip() or title
                else:
                    sec_id = f"{doc_id}-SEC-{idx}"
                    sec_title = title
                    
                chunk_id = f"{doc_id}_{sec_id}_{idx}"
                chunk = KnowledgeBaseChunk(
                    chunk_id=chunk_id,
                    section_id=sec_id,
                    doc_id=doc_id,
                    title=f"{title} - {sec_title}",
                    doc_type=doc_type,
                    status=status,
                    effective_from=effective_from,
                    filename=md_file.name,
                    text=sec,
                )
                self.chunks.append(chunk)

        # 2. Parse products.csv into indexed catalog chunks
        products_csv = DATA_DIR / "products.csv"
        if products_csv.exists():
            df_prod = pd.read_csv(products_csv, dtype=str)
            for _, row in df_prod.iterrows():
                sku = row["sku"]
                prod_text = (
                    f"Product Catalog Entry: SKU {sku}\n"
                    f"Title: {row.get('title')}\n"
                    f"Brand: {row.get('brand')}\n"
                    f"Return Category: {row.get('return_category')}\n"
                    f"Price: Rs. {row.get('price_inr')}\n"
                    f"Fulfilled by: {row.get('fulfilled_by')}\n"
                    f"Assured: {row.get('assured')}\n"
                    f"Warranty Months: {row.get('warranty_months')}\n"
                    f"Description: {row.get('description')}"
                )
                chunk = KnowledgeBaseChunk(
                    chunk_id=f"PROD_{sku}",
                    section_id=f"products.csv:{sku}",
                    doc_id="products_catalog",
                    title=f"Product SKU {sku} - {row.get('title')}",
                    doc_type="product_catalog",
                    status="current",
                    effective_from="2026-01-01",
                    filename="products.csv",
                    text=prod_text,
                )
                self.chunks.append(chunk)

        # 3. Build FAISS vector index (Inner Product / Cosine Similarity)
        texts_to_embed = [f"{c.title}\n{c.text}" for c in self.chunks]
        embeddings = self.model.encode(texts_to_embed, normalize_embeddings=True, show_progress_bar=False)
        embeddings = np.array(embeddings, dtype=np.float32)
        
        d = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(d)
        self.index.add(embeddings)

        # Persist index and chunks to disk cache
        try:
            faiss.write_index(self.index, str(index_cache))
            with open(chunks_cache, "wb") as f:
                pickle.dump(self.chunks, f)
        except Exception:
            pass

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_superseded: bool = True,
    ) -> List[Tuple[KnowledgeBaseChunk, float]]:
        """Retrieve the top-K relevant chunks with precedence weighting and score filtering."""
        if not query or not query.strip():
            return []
            
        k = top_k or self.top_k
        query_emb = self.model.encode([query], normalize_embeddings=True, show_progress_bar=False)
        query_emb = np.array(query_emb, dtype=np.float32)
        
        # Search over 2x candidates to allow for policy precedence reranking
        search_k = min(len(self.chunks), max(k * 3, 10))
        scores, indices = self.index.search(query_emb, search_k)
        
        # Check for explicit SKU mentions to ensure exact catalog entity retrieval
        sku_match = re.search(r"\b([A-Z]{3}-\d{4})\b", query.upper())
        exact_entity_chunk = None
        if sku_match:
            target_sku = sku_match.group(1)
            for c in self.chunks:
                if c.section_id == f"products.csv:{target_sku}":
                    exact_entity_chunk = (c, 1.25)  # Boost exact entity match
                    break

        results = []
        if exact_entity_chunk:
            results.append(exact_entity_chunk)

        for raw_score, idx in zip(scores[0], indices[0]):
            chunk = self.chunks[idx]
            if exact_entity_chunk and chunk.chunk_id == exact_entity_chunk[0].chunk_id:
                continue
            
            # Policy status filtering: exclude superseded documents AND superseded files
            if filter_superseded:
                if chunk.status == "superseded" or chunk.filename in SUPERSEDED_FILES:
                    continue
                
            # Precedence weighting
            score = float(raw_score)
            doc_type = chunk.doc_type
            if doc_type == "policy":
                weight = 1.05
            elif doc_type == "agent_guide":
                weight = 1.02
            elif doc_type == "help":
                weight = 1.00
            elif doc_type == "faq":
                weight = 0.98
            elif doc_type == "marketing":
                weight = 0.90
            else:
                weight = 1.00
                
            final_score = score * weight
            if final_score >= self.similarity_threshold:
                results.append((chunk, final_score))
                
        # Sort by final score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]
