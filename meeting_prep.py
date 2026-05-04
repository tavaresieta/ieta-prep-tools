import streamlit as st
from pathlib import Path
import json
import os
import anthropic

st.set_page_config(
    page_title="IETA Knowledge Base",
    page_icon="📚",
    layout="wide"
)

DOC_TYPES = [
    "IETA Report",
    "IETA Position / Discussion Paper",
    "IETA Presentation / Slide Deck",
    "External Report",
    "External Paper / Research",
]

TYPE_ICONS = {
    "IETA Report":                      "📄",
    "IETA Position / Discussion Paper": "📋",
    "IETA Presentation / Slide Deck":   "📊",
    "External Report":                  "🌐",
    "External Paper / Research":        "🔬",
}

OUTPUT_MODES = [
    "Trechos comentados — cada trecho com síntese linha a linha",
    "Texto estruturado — narrativa coerente com seções e citações",
]

USE_CONTEXTS = [
    "Reunião com regulador / governo",
    "Reunião com setor privado",
    "Nota técnica interna",
    "Apresentação executiva",
    "Pesquisa e análise de posicionamento",
    "Preparação para painel / evento",
    "Outro",
]

SYSTEM_PROMPT = """Você é um agente especializado em mercados de carbono a serviço da IETA Brasil.
Seu público são profissionais com conhecimento técnico profundo em regulação climática, mercados de carbono, finanças de carbono e política internacional.
Exige-se máxima precisão técnica, linguagem refinada e granularidade elevada.
Use EXCLUSIVAMENTE o conteúdo dos documentos fornecidos — ZERO conhecimento externo.
Não invente, não complemente, não infira além do que está escrito nos documentos."""

# ============================================================================
# DADOS
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
def load_vocabulary():
    for p in [Path("metadata/vocabulary.json")]:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return []

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
# ANTHROPIC
# ============================================================================

def get_anthropic_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            pass
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)

# ============================================================================
# INFERÊNCIA AUTOMÁTICA DE KEYWORDS
# ============================================================================

def infer_keywords(client, query, angle, vocabulary):
    """
    Quando o usuário não seleciona keywords manualmente,
    o modelo infere quais do vocabulário são relevantes para a consulta.
    Retorna lista de keywords inferidas.
    """
    vocab_str = ", ".join(vocabulary)
    angle_str = f"\nÂngulo de foco: {angle}" if angle else ""

    prompt = f"""Você é um especialista em mercados de carbono.

CONSULTA DO USUÁRIO: {query}{angle_str}

Do vocabulário abaixo, selecione as keywords diretamente relevantes a esta consulta.
Use critério temático — inclua termos relacionados ao tema mesmo que não apareçam literalmente na consulta.
Retorne entre 3 e 8 keywords. Não seja exaustivo — priorize relevância sobre cobertura.
Retorne APENAS as keywords separadas por vírgula, sem explicações.

VOCABULÁRIO DISPONÍVEL:
{vocab_str}

Keywords relevantes:"""

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        inferred = [k.strip() for k in raw.split(",") if k.strip() in vocabulary]
        return inferred
    except Exception:
        return []

# ============================================================================
# FILTRO DE DOCUMENTOS
# ============================================================================

def get_documents_by_keywords(selected_keywords, keyword_index, metadata):
    if not selected_keywords:
        return list(metadata.keys())
    doc_scores = {}
    for kw in selected_keywords:
        for doc_id in keyword_index.get(kw, []):
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1
    return [d for d, _ in sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)]

# ============================================================================
# EXTRAÇÃO E SÍNTESE
# ============================================================================

def extract_and_synthesize(client, documents, relevant_ids, keywords_metadata,
                           query, angle, use_context, n_excerpts_mode,
                           feedback_context=""):
    """
    Para cada documento relevante, extrai trechos com síntese linha a linha.
    Retorna lista de blocos estruturados.
    """
    n_map = {
        "0–10 trechos":  (3, 10),
        "10–25 trechos": (10, 25),
        "Mais de 25":    (25, 999),
    }
    n_min, n_max = n_map.get(n_excerpts_mode, (3, 10))
    n_instruction = (
        f"entre {n_min} e {n_max} trechos"
        if n_max < 999
        else f"mais de {n_min} trechos — seja exaustivo"
    )

    angle_str    = f"\nÂngulo de foco: {angle}" if angle else ""
    context_str  = f"\nContexto de uso: {use_context}" if use_context else ""
    feedback_str = f"\nRefinamento solicitado pelo usuário: {feedback_context}" if feedback_context else ""

    results = []

    for doc_id in relevant_ids:
        if doc_id not in documents:
            continue
        doc_data   = documents[doc_id]
        doc_meta   = keywords_metadata.get(doc_id, {})
        doc_type   = doc_meta.get("doc_type", "—")
        sharepoint = doc_meta.get("sharepoint_url", "")

        prompt = f"""{SYSTEM_PROMPT}

CONSULTA: {query}{angle_str}{context_str}{feedback_str}

TAREFA:
Extraia {n_instruction} do documento que sejam relevantes para a consulta.
Use critério TEMÁTICO — busque conceitos, mecanismos e contextos relacionados, não apenas palavras exatas.
Para cada trecho, forneça:
- Uma frase de síntese técnica (o que esse trecho contribui para a consulta)
- O trecho copiado literalmente (preserve números, datas, dados, terminologia técnica)

FORMATO (repita para cada trecho):
###
SÍNTESE: [frase técnica explicando a contribuição]
TRECHO: [cópia literal do documento]

Responda "SEM CONTEÚDO RELEVANTE" apenas se o documento genuinamente não abordar o tema.

DOCUMENTO: {doc_data['filename']}
{doc_data['full_content'][:15000]}"""

        try:
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()

            if "SEM CONTEÚDO RELEVANTE" in raw:
                continue

            points = []
            for block in [b.strip() for b in raw.split("###") if b.strip()]:
                synthesis, excerpt, in_excerpt = "", "", False
                for line in block.splitlines():
                    if line.startswith("SÍNTESE:"):
                        synthesis  = line.replace("SÍNTESE:", "").strip()
                        in_excerpt = False
                    elif line.startswith("TRECHO:"):
                        excerpt    = line.replace("TRECHO:", "").strip()
                        in_excerpt = True
                    elif in_excerpt:
                        excerpt += "\n" + line
                if synthesis or excerpt:
                    points.append({"synthesis": synthesis, "excerpt": excerpt.strip()})

            if points:
                results.append({
                    "filename":      doc_data["filename"],
                    "doc_type":      doc_type,
                    "sharepoint_url": sharepoint,
                    "points":        points,
                })

        except Exception as e:
            st.warning(f"⚠️ Erro ao processar `{doc_data['filename']}`: {e}")

    return results


def generate_structured_text(client, query, angle, use_context,
                              results, feedback_context=""):
    """
    Gera texto estruturado com seções e citações inline
    a partir dos trechos já extraídos.
    """
    angle_str    = f"\nÂngulo de foco: {angle}" if angle else ""
    context_str  = f"\nContexto de uso: {use_context}" if use_context else ""
    feedback_str = f"\nRefinamento solicitado: {feedback_context}" if feedback_context else ""

    passages = "\n\n".join(
        f"[{r['filename']}]\n" +
        "\n".join(f"- {p['excerpt']}" for p in r["points"] if p.get("excerpt"))
        for r in results
    )

    prompt = f"""{SYSTEM_PROMPT}

CONSULTA: {query}{angle_str}{context_str}{feedback_str}

Com base EXCLUSIVAMENTE nos trechos abaixo, produza um texto técnico estruturado que responda à consulta.

ESTRUTURA SUGERIDA (adapte conforme o conteúdo disponível):
## Contexto e relevância
## Posicionamento da IETA
## Implicações e análise
## Lacunas ou ausências identificadas na base

DIRETRIZES:
- Linguagem técnica e precisa, adequada a especialistas em mercados de carbono
- Cite sempre a fonte inline: [Fonte: nome_do_documento]
- Não adicione informações além do que está nos trechos
- Se os trechos não cobrirem alguma seção, diga explicitamente

TRECHOS DISPONÍVEIS:
{passages[:40000]}

TEXTO ESTRUTURADO:"""

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        return f"_Erro ao gerar texto estruturado: {e}_"

# ============================================================================
# SIDEBAR
# ============================================================================

documents         = load_all_documents()
keywords_metadata = load_keywords_metadata()
keyword_index     = load_keyword_index()
vocabulary        = load_vocabulary()

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
                st.text(f"• {doc_data['filename'].replace('.txt','')}")
                if kws:
                    st.caption(f"  🏷️ {', '.join(kws)}")

    st.markdown("---")
    st.caption("🌐 IETA Brazil Initiative")

if not documents:
    st.warning("⚠️ Adicione documentos à pasta 'documents/' e clique em Recarregar.")
    st.stop()

# ============================================================================
# INTERFACE PRINCIPAL
# ============================================================================

st.title("📚 IETA Knowledge Base")
st.markdown("Busca e curadoria de conteúdo técnico sobre mercados de carbono — lastreada exclusivamente na base de documentos internos da IETA Brasil.")
st.markdown("---")

# ── CONSULTA ─────────────────────────────────────────────────────────────────

st.markdown("**Consulta**")
st.caption(
    "Descreva com precisão o que deseja saber ou mapear. Quanto mais específico, "
    "mais aderente será o resultado. "
    "_Ex: \"Posicionamento da IETA sobre corresponding adjustments no Artigo 6.2\" "
    "ou \"Referências sobre integridade de créditos de carbono no mercado voluntário brasileiro.\"_"
)
query = st.text_area(
    "",
    placeholder="Ex: Posicionamento da IETA sobre o CBAM e seus impactos no setor produtivo brasileiro",
    height=90,
    label_visibility="collapsed",
)

angle = st.text_input(
    "**Ângulo ou foco específico** (opcional):",
    placeholder="Ex: Evidencie impactos no setor de hard-to-abate e reações do setor produtivo brasileiro",
)

# ── CONTEXTO DE USO E OUTPUT ──────────────────────────────────────────────────

col_ctx, col_out = st.columns(2)
with col_ctx:
    use_context = st.selectbox(
        "**Contexto de uso:**",
        options=[""] + USE_CONTEXTS,
        format_func=lambda x: "Selecione (opcional)" if x == "" else x,
        help="Orienta o tom e profundidade da resposta.",
    )
with col_out:
    output_mode = st.selectbox(
        "**Formato do output:**",
        options=OUTPUT_MODES,
        help="Trechos comentados: cada ponto com síntese + trecho literal. Texto estruturado: narrativa com seções e citações.",
    )

# ── FILTROS ───────────────────────────────────────────────────────────────────

st.markdown("**Filtros** — deixe em branco para inferência automática de keywords")

col_kw, col_type = st.columns(2)

with col_kw:
    available_kws = sorted(keyword_index.keys()) if keyword_index else []
    kw_options    = [f"{kw} ({len(keyword_index[kw])} docs)" for kw in available_kws]
    raw_selected  = st.multiselect(
        "Keywords (opcional — se vazio, inferidas automaticamente):",
        options=kw_options,
        max_selections=8,
        help="Se não selecionar, o modelo infere as keywords relevantes a partir da sua consulta.",
    )
    selected_keywords = [k.split(" (")[0] for k in raw_selected]

with col_type:
    selected_types_raw = st.multiselect(
        "Tipos de documento:",
        options=DOC_TYPES,
        default=DOC_TYPES,
    )
    selected_types = selected_types_raw if selected_types_raw else DOC_TYPES

col_n, _ = st.columns(2)
with col_n:
    n_excerpts_mode = st.selectbox(
        "**Número de trechos por documento:**",
        options=["0–10 trechos", "10–25 trechos", "Mais de 25"],
        index=0,
    )

st.markdown("---")

# ── BOTÃO ────────────────────────────────────────────────────────────────────

if st.button("🔍 Buscar e Extrair Referências", type="primary", use_container_width=True):
    if not query.strip():
        st.error("⚠️ Descreva o que você quer saber ou mapear.")
        st.stop()

    client = get_anthropic_client()
    if not client:
        st.error("⚠️ ANTHROPIC_API_KEY não configurada.")
        st.stop()

    # ── INFERÊNCIA OU SELEÇÃO DE KEYWORDS ────────────────────────────────
    if selected_keywords:
        active_keywords = selected_keywords
        kw_source       = f"Keywords selecionadas manualmente: {', '.join(active_keywords)}"
    else:
        with st.spinner("Inferindo keywords relevantes para a consulta..."):
            active_keywords = infer_keywords(client, query, angle, vocabulary)
        kw_source = (
            f"Keywords inferidas automaticamente: {', '.join(active_keywords)}"
            if active_keywords
            else "Nenhuma keyword inferida — consultando toda a base"
        )

    # ── FILTRA DOCUMENTOS ────────────────────────────────────────────────
    if active_keywords:
        doc_scores = {}
        for kw in active_keywords:
            for doc_id in keyword_index.get(kw, []):
                doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1
        relevant_ids = [d for d, _ in sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)]
    else:
        relevant_ids = list(documents.keys())

    # Filtra por tipo
    if selected_types:
        relevant_ids = [
            d for d in relevant_ids
            if keywords_metadata.get(d, {}).get("doc_type", "") in selected_types
        ]

    used_docs = [
        documents[d]["filename"] for d in relevant_ids if d in documents
    ]

    if not used_docs:
        st.error("❌ Nenhum documento encontrado. Tente ampliar os filtros ou reformular a consulta.")
        st.stop()

    # ── DOCUMENTOS CONSULTADOS ────────────────────────────────────────────
    st.markdown("### 📚 Documentos consultados")
    st.caption(kw_source)
    st.caption(f"{len(used_docs)} documento(s) identificado(s)")

    fname_meta = {
        v.get("filename", ""): {
            "doc_type":       v.get("doc_type", "—"),
            "sharepoint_url": v.get("sharepoint_url", ""),
        }
        for v in keywords_metadata.values()
    }

    for fname in used_docs:
        meta   = fname_meta.get(fname, {})
        dtype  = meta.get("doc_type", "—")
        sp_url = meta.get("sharepoint_url", "")
        icon   = TYPE_ICONS.get(dtype, "📎")
        orig   = fname.replace(".txt", "")
        col1, col2 = st.columns([5, 2])
        with col1:
            if sp_url:
                st.markdown(f"{icon} [{orig}]({sp_url})")
            else:
                st.markdown(f"{icon} `{orig}`")
        with col2:
            st.caption(dtype)

    st.markdown("---")

    # ── EXTRAÇÃO ─────────────────────────────────────────────────────────
    feedback_context = st.session_state.get("feedback_context", "")

    with st.spinner(f"Analisando {len(used_docs)} documento(s)..."):
        results = extract_and_synthesize(
            client, documents, relevant_ids, keywords_metadata,
            query, angle, use_context, n_excerpts_mode, feedback_context,
        )

    if not results:
        st.warning("⚠️ Nenhum trecho relevante encontrado. Tente ampliar os filtros ou reformular a consulta.")
        st.stop()

    # Salva resultados no session_state para re-iteração
    st.session_state["last_results"]  = results
    st.session_state["last_query"]    = query
    st.session_state["last_angle"]    = angle
    st.session_state["last_context"]  = use_context

    total_points = sum(len(r["points"]) for r in results)

    # ── OUTPUT ────────────────────────────────────────────────────────────
    if "Texto estruturado" in output_mode:
        st.markdown("### 📝 Análise estruturada")
        st.caption("Texto gerado exclusivamente a partir dos trechos extraídos da base.")
        with st.spinner("Gerando texto estruturado..."):
            structured = generate_structured_text(
                client, query, angle, use_context, results, feedback_context)
        st.markdown(structured)

        st.markdown("---")
        st.markdown(f"#### 📑 Trechos de base ({total_points} em {len(results)} documento(s))")
        st.caption("Trechos literais que embasaram o texto acima.")
        for result in results:
            orig   = result["filename"].replace(".txt", "")
            sp_url = result["sharepoint_url"]
            icon   = TYPE_ICONS.get(result["doc_type"], "📎")
            label  = f"{icon} [{orig}]({sp_url})" if sp_url else f"{icon} **{orig}**"
            with st.expander(label):
                st.caption(result["doc_type"])
                for p in result["points"]:
                    if p.get("excerpt"):
                        st.markdown(
                            f"<blockquote style='border-left:3px solid #1a1a2e;"
                            f"padding:8px 12px;margin:4px 0 12px 0;"
                            f"background:#f7f9fc;color:#333;font-size:0.88rem;"
                            f"font-style:italic'>{p['excerpt']}</blockquote>",
                            unsafe_allow_html=True,
                        )

        full_output = structured + "\n\n---\nTRECHOS DE BASE\n\n" + "\n\n".join(
            f"=== {r['filename']} ===\n" +
            "\n".join(f"• {p['excerpt']}" for p in r["points"] if p.get("excerpt"))
            for r in results
        )

    else:
        # Trechos comentados
        st.markdown(f"### 💡 Referências extraídas — {total_points} trecho(s) em {len(results)} documento(s)")

        full_output_lines = [f"CONSULTA: {query}"]
        if angle:
            full_output_lines.append(f"ÂNGULO: {angle}")
        full_output_lines.append("")

        for result in results:
            orig   = result["filename"].replace(".txt", "")
            sp_url = result["sharepoint_url"]
            icon   = TYPE_ICONS.get(result["doc_type"], "📎")
            label  = f"{icon} [{orig}]({sp_url})" if sp_url else f"{icon} **{orig}**"

            st.markdown(f"#### {label}")
            st.caption(result["doc_type"])
            full_output_lines.append(f"=== {orig} ({result['doc_type']}) ===")

            for i, point in enumerate(result["points"], 1):
                synthesis = point.get("synthesis", "")
                excerpt   = point.get("excerpt", "")
                if synthesis:
                    st.markdown(f"**{i}. {synthesis}**")
                    full_output_lines.append(f"\n{i}. {synthesis}")
                if excerpt:
                    st.markdown(
                        f"<blockquote style='border-left:3px solid #1a1a2e;"
                        f"padding:8px 12px;margin:4px 0 16px 0;"
                        f"background:#f7f9fc;color:#333;font-size:0.88rem;"
                        f"font-style:italic'>{excerpt}</blockquote>",
                        unsafe_allow_html=True,
                    )
                    full_output_lines.append(f'"{excerpt}"')

            st.markdown("---")
            full_output_lines.append("")

        full_output = "\n".join(full_output_lines)

    st.download_button(
        "📥 Baixar resultado completo",
        full_output,
        file_name="ieta_referencias.txt",
        use_container_width=True,
    )

# ── FEEDBACK E RE-ITERAÇÃO ────────────────────────────────────────────────────

if "last_results" in st.session_state:
    st.markdown("---")
    st.markdown("### 🔄 Refinar busca")
    st.caption("Indique o que ajustar para uma nova iteração — ex: 'foque mais em impactos regulatórios', 'exclua documentos sobre aviação', 'aprofunde nos dados quantitativos'.")

    feedback = st.text_area(
        "O que ajustar na próxima busca?",
        placeholder="Ex: Os trechos sobre impactos setoriais foram os mais relevantes. Aprofunde nessa dimensão e exclua referências puramente regulatórias.",
        height=80,
        key="feedback_input",
    )

    col_fb1, col_fb2 = st.columns(2)
    with col_fb1:
        if st.button("🔁 Refinar e buscar novamente", use_container_width=True, type="primary"):
            st.session_state["feedback_context"] = feedback
            st.rerun()
    with col_fb2:
        if st.button("🗑️ Limpar e começar nova busca", use_container_width=True):
            for key in ["last_results", "last_query", "last_angle",
                        "last_context", "feedback_context"]:
                st.session_state.pop(key, None)
            st.rerun()

# ============================================================================
# RODAPÉ
# ============================================================================
st.markdown("---")
st.caption("🌐 IETA Brazil Initiative · Use 'Recarregar' na sidebar sempre que a base for atualizada.")
