import streamlit as st
from pathlib import Path
import urllib.parse
import json
 
st.set_page_config(
    page_title="IETA Wizard",
    page_icon="🧙",
    layout="wide"
)
 
DOC_TYPES = [
    "IETA Report",
    "IETA Position / Discussion Paper",
    "IETA Presentation / Slide Deck",
    "External Report",
    "External Paper / Research",
    "External Presentation / Slide Deck",
]
 
# ============================================================================
# CARREGAMENTO DE DADOS
# ============================================================================
 
@st.cache_data
def load_keywords_metadata():
    for p in [Path("metadata/keywords_metadata.json"), Path("keywords_metadata.json")]:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return {}
 
@st.cache_data
def load_keyword_index():
    for p in [Path("metadata/keywords_metadata_index.json"), Path("keywords_metadata_index.json")]:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return {}
 
@st.cache_data
def load_all_documents():
    docs_folder = Path("documents")
    all_content = {}
    if not docs_folder.exists():
        return {}
    for file_path in docs_folder.glob("*.txt"):
        try:
            content = file_path.read_text(encoding="utf-8")
            if content.strip():
                all_content[file_path.stem] = {
                    "filename":     file_path.name,
                    "full_content": content,
                    "size_kb":      len(content) / 1024,
                    "char_count":   len(content),
                }
        except Exception:
            pass
    return all_content
 
# ============================================================================
# FUNÇÕES DE BUSCA E CONTEXTO
# ============================================================================
 
def get_documents_by_keywords(selected_keywords, keyword_index, metadata):
    if not selected_keywords:
        return list(metadata.keys())
    doc_scores = {}
    for kw in selected_keywords:
        for doc_id in keyword_index.get(kw, []):
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1
    return [d for d, _ in sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)]
 
def get_keyword_doc_map(selected_keywords, keyword_index, keywords_metadata):
    result = {}
    for kw in selected_keywords:
        doc_ids = keyword_index.get(kw, [])
        result[kw] = [
            keywords_metadata[d]["filename"]
            for d in doc_ids if d in keywords_metadata
        ]
    return result
 
def extract_relevant_excerpts(content: str, topics: str, max_chars: int = 8000) -> str:
    terms = [t.lower().strip() for t in topics.replace(",", " ").split() if len(t.strip()) > 3]
    if not terms:
        return content[:max_chars]
    lines = content.split("\n")
    scored_chunks = []
    chunk_size = 10
    for i in range(0, len(lines), chunk_size // 2):
        chunk = "\n".join(lines[i: i + chunk_size])
        score = sum(chunk.lower().count(t) for t in terms)
        if score > 0:
            scored_chunks.append((score, chunk))
    if not scored_chunks:
        return content[:max_chars]
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    excerpts, total = [], 0
    for _, chunk in scored_chunks:
        if total + len(chunk) > max_chars:
            break
        excerpts.append(chunk)
        total += len(chunk)
    return "\n---\n".join(excerpts) if excerpts else content[:max_chars]
 
def prepare_context(documents, selected_keywords, keyword_index, keywords_metadata, topics="", selected_types=None):
    if selected_keywords:
        relevant_ids = get_documents_by_keywords(selected_keywords, keyword_index, keywords_metadata)
        if not relevant_ids:
            return None, [], {}
    else:
        relevant_ids = list(documents.keys())
 
    # Filter by doc type if selected
    if selected_types:
        relevant_ids = [
            doc_id for doc_id in relevant_ids
            if keywords_metadata.get(doc_id, {}).get("doc_type", "") in selected_types
        ]
        if not relevant_ids:
            return None, [], {}
 
    kw_doc_map = get_keyword_doc_map(selected_keywords, keyword_index, keywords_metadata)
    docs_context, used_docs = [], []
 
    for doc_id in relevant_ids:
        if doc_id not in documents:
            continue
        doc_data = documents[doc_id]
        doc_kws  = keywords_metadata.get(doc_id, {}).get("keywords", [])
        excerpt  = extract_relevant_excerpts(doc_data["full_content"], topics)
 
        docs_context.append(
            f"{'='*70}\n"
            f"DOCUMENTO: {doc_data['filename']}\n"
            f"Keywords: {', '.join(doc_kws) or 'N/A'}\n"
            f"{'='*70}\n"
            f"{excerpt}\n"
        )
        used_docs.append(doc_data["filename"])
 
    return "\n".join(docs_context)[:80000], used_docs, kw_doc_map
 
# ============================================================================
# CARREGA DADOS
# ============================================================================
 
documents         = load_all_documents()
keywords_metadata = load_keywords_metadata()
keyword_index     = load_keyword_index()
 
# ============================================================================
# SIDEBAR — info da base apenas
# ============================================================================
 
with st.sidebar:
    st.header("📊 Base de Conhecimento")
 
    if st.button("🔄 Recarregar", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
 
    st.markdown("---")
 
    if not documents:
        st.error("❌ Nenhum documento encontrado.")
    else:
        st.success(f"✅ {len(documents)} documentos")
        total_kb = sum(d["size_kb"] for d in documents.values())
        st.caption(f"{total_kb:.1f} KB · {len(keyword_index)} keywords indexadas")
 
        with st.expander("📄 Ver documentos e keywords"):
            for doc_id, doc_data in sorted(documents.items()):
                kws = keywords_metadata.get(doc_id, {}).get("keywords", [])
                st.text(f"• {doc_data['filename']}")
                if kws:
                    st.caption(f"  🏷️ {', '.join(kws)}")
 
    st.markdown("---")
    st.caption("🌐 IETA Brazil Initiative")
 
# ============================================================================
# GUARD
# ============================================================================
 
if not documents:
    st.warning("⚠️ Adicione documentos à pasta 'documents/' e clique em Recarregar.")
    st.stop()
 
# ============================================================================
# INTERFACE PRINCIPAL
# ============================================================================
 
st.title("🧙 IETA Wizard")
st.subheader("Busca de Referências + Briefing Inicial")
st.markdown("---")
 
# ── INPUTS ───────────────────────────────────────────────────────────────────
 
col_a, col_b = st.columns([3, 1])
with col_a:
    context_description = st.text_input(
        "**Contexto** — com quem é a reunião / qual é o painel:",
        placeholder="Ex: Reunião com IBP sobre regulação SBCE e impacto no setor de petróleo",
    )
with col_b:
    event_date = st.date_input("**Data:**")
 
st.markdown("**O que você quer abordar e como?**")
st.caption(
    "Descreva livremente os tópicos, o tom desejado e qualquer ideia que já tenha em mente. "
    "Quanto mais contexto, mais preciso o briefing. "
    "_Exemplo: Quero focar em SBCE e CBAM com ênfase no impacto para aviação. "
    "Tom propositivo — a IETA tem posições claras sobre integridade de mercado que quero destacar. "
    "Se possível, trazer dados concretos sobre SAF e comparar com experiências internacionais._"
)
topics = st.text_area(
    "",
    placeholder="Ex: Quero abordar SBCE e CBAM com foco no impacto para o setor de aviação. Tom propositivo — destacar a posição da IETA sobre integridade de mercado. Se possível, trazer dados sobre SAF e alguma comparação internacional.",
    height=130,
    label_visibility="collapsed",
)
 
# Keywords — no painel principal
available_kws = sorted(keyword_index.keys()) if keyword_index else []
 
if available_kws:
    kw_options = [f"{kw} ({len(keyword_index[kw])} docs)" for kw in available_kws]
    raw_selected = st.multiselect(
        "**Keywords para filtrar os documentos da base:**",
        options=kw_options,
        max_selections=5,
        help="Selecione as keywords relevantes para este contexto. Apenas documentos tagueados com elas serão usados.",
    )
    selected_keywords = [k.split(" (")[0] for k in raw_selected]
else:
    st.warning("⚠️ Nenhuma keyword indexada. Use o admin.py para processar os documentos.")
    selected_keywords = []
 
selected_types_raw = st.multiselect(
    "**Tipos de documento a considerar:**",
    options=DOC_TYPES,
    default=DOC_TYPES,
    help="Filtre por tipo de fonte. Por padrão todos os tipos são incluídos.",
)
selected_types = selected_types_raw if selected_types_raw else DOC_TYPES
 
detail_level = st.select_slider(
    "**Nível de detalhe:**",
    options=["Rápido", "Padrão", "Completo"],
    value="Padrão",
)
objectives = ""  # incorporado no campo topics
 
st.markdown("---")
 
# ── BOTÃO ────────────────────────────────────────────────────────────────────
 
if st.button("🚀 Buscar Referências e Gerar Briefing", type="primary", use_container_width=True):
    if not context_description or not topics:
        st.error("⚠️ Preencha pelo menos o Contexto e os Tópicos.")
    else:
        with st.spinner("Buscando documentos relevantes..."):
            full_context, used_docs, kw_doc_map = prepare_context(
                documents, selected_keywords, keyword_index,
                keywords_metadata, topics=topics, selected_types=selected_types,
            )
 
        if full_context is None:
            st.error("❌ Nenhum documento encontrado com as keywords selecionadas.")
            st.stop()
 
        # ── REFERÊNCIAS MAPEADAS ─────────────────────────────────────────
        st.markdown("### 📚 Referências mapeadas")
 
        if kw_doc_map:
            for kw, filenames in kw_doc_map.items():
                if filenames:
                    st.markdown(
                        f"🏷️ **`{kw}`** → " + " · ".join(f"`{f}`" for f in filenames)
                    )
                else:
                    st.markdown(f"🏷️ **`{kw}`** → _nenhum documento encontrado_")
        else:
            st.info("Nenhuma keyword selecionada — contexto inclui todos os documentos da base.")
 
        st.markdown(f"**{len(used_docs)} documento(s) incluído(s) no contexto:**")
        # Build reverse map filename -> doc_type
        fname_type = {
            v.get("filename", ""): v.get("doc_type", "—")
            for v in keywords_metadata.values()
        }
        cols = st.columns(3)
        for i, fname in enumerate(used_docs):
            dtype = fname_type.get(fname, "—")
            label = f"- `{fname}` — _{dtype}_"
            cols[i % 3].markdown(label)
 
        st.markdown("---")
 
        # ── MONTA PROMPT ─────────────────────────────────────────────────
        if detail_level == "Rápido":
            sections = """
1. 🎯 Objetivos Estratégicos (2-3 pontos)
2. 💡 Posições IETA Relevantes (cite os documentos)
3. 🗣️ 3 Talking Points Principais
"""
        elif detail_level == "Padrão":
            sections = """
1. 🎯 Objetivos Estratégicos IETA
2. 📊 Contexto sobre o interlocutor / evento
3. 💡 Posições IETA Relevantes (SEMPRE cite o documento fonte)
4. 🗣️ 5 Talking Points Estratégicos
5. ❓ 3-4 Perguntas Prováveis e Respostas
"""
        else:
            sections = """
1. 🎯 Objetivos Estratégicos IETA
2. 📊 Contexto Detalhado sobre o interlocutor / evento
3. 💡 Posições IETA Relevantes (com citações dos documentos)
4. 🗣️ 7 Talking Points Estratégicos
5. ❓ 5+ Perguntas Prováveis e Respostas Preparadas
6. ⚠️ Considerações Estratégicas (Oportunidades e Riscos)
7. 📋 Action Items para Follow-up
"""
 
        filter_info = ""
        if selected_keywords:
            filter_info = (
                f"\nFILTRO APLICADO: use APENAS os trechos abaixo, selecionados pelas keywords: "
                f"{', '.join(selected_keywords)}\n"
                f"Dentro de cada documento, foram extraídos os trechos mais relevantes a: {topics}\n"
            )
 
        prompt = f"""Você é um assistente especializado da IETA (International Emissions Trading Association) Brasil.
 
REGRAS CRÍTICAS:
1. Use APENAS informações dos trechos de documentos fornecidos abaixo
2. SEMPRE cite a fonte: "Segundo [nome do documento], ..."
3. Use dados numéricos EXATOS dos documentos (não invente)
4. Se não houver informação sobre um ponto, diga claramente
5. Foque EXCLUSIVAMENTE nos tópicos: {topics}
6. Ignore qualquer conteúdo dos documentos que não seja relevante a esses tópicos
{filter_info}
CONTEXTO:
{context_description}
Data: {event_date}
Tópicos: {topics}
Objetivo: {objectives if objectives else "Mapear oportunidades e alinhar posições IETA"}
 
DOCUMENTOS DE REFERÊNCIA ({len(used_docs)} documentos · {len(full_context):,} caracteres):
{full_context}
 
TAREFA: Crie um briefing executivo focado exclusivamente nos tópicos acima.
 
ESTRUTURA:
{sections}
FORMATO: markdown com headers e bullet points. Cada afirmação: [Fonte: nome_do_documento]
 
BRIEFING:
"""
 
        # ── OUTPUT DO PROMPT ─────────────────────────────────────────────
        st.markdown("### 📋 Prompt gerado")
        st.caption("Copie e cole no Claude.ai ou ChatGPT para obter o briefing completo.")
        st.text_area("", prompt, height=420, label_visibility="collapsed")
 
        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button(
                "📥 Baixar prompt",
                prompt,
                file_name=f"briefing_{event_date}.txt",
                use_container_width=True,
            )
        with c2:
            encoded = urllib.parse.quote(prompt[:2000])
            st.markdown(f"""
<a href="https://chat.openai.com/?q={encoded}" target="_blank">
<button style="width:100%;height:38px;background:#10a37f;color:white;border:none;
border-radius:6px;cursor:pointer;font-size:13px;font-weight:500;">
🤖 Abrir no ChatGPT
</button></a>""", unsafe_allow_html=True)
        with c3:
            st.metric("Docs no contexto", len(used_docs))
 
# ============================================================================
# RODAPÉ
# ============================================================================
st.markdown("---")
st.caption("🌐 IETA Brazil Initiative · Use 'Recarregar' na sidebar sempre que a base for atualizada.")