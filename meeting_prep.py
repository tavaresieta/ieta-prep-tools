import streamlit as st
from pathlib import Path
import json
import os
import anthropic
import base64
import time

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

CONSTITUTIONAL_RULES = """
VERIFICAÇÃO OBRIGATÓRIA antes de incluir qualquer trecho:
(a) LITERALIDADE: o trecho está copiado literalmente do documento, sem paráfrases ou adaptações?
(b) RELEVÂNCIA: o trecho é diretamente relevante ao tema da consulta, não apenas tangencial?
(c) CONSISTÊNCIA: o trecho não contradiz outros trechos já selecionados do mesmo ou de outros documentos?
Se qualquer verificação falhar, descarte o trecho. Só então responda."""

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
    if Path("metadata/vocabulary.json").exists():
        return json.loads(Path("metadata/vocabulary.json").read_text(encoding="utf-8"))
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

@st.cache_data
def load_pdf_as_base64(pdf_path: str) -> str:
    """Carrega PDF e converte para base64 para envio direto à API."""
    with open(pdf_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")

# ============================================================================
# ANTHROPIC CLIENT
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
# INFERÊNCIA DE KEYWORDS
# ============================================================================

def infer_keywords(client, query, angle, vocabulary):
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
        return [k.strip() for k in raw.split(",") if k.strip() in vocabulary]
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
# PARSING DE BLOCOS ###
# ============================================================================

def parse_blocks(raw: str) -> list:
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
    return points

# ============================================================================
# EXTRAÇÃO — BATCH API (processamento paralelo)
# ============================================================================

def build_extraction_prompt(doc_filename, doc_content, query, angle,
                             use_context, n_instruction, feedback_context,
                             enable_cot, doc_pdf_b64=None):
    """Monta o prompt de extração, com suporte a PDF direto e chain-of-thought."""
    angle_str    = f"\nÂngulo de foco: {angle}" if angle else ""
    context_str  = f"\nContexto de uso: {use_context}" if use_context else ""
    feedback_str = f"\nRefinamento solicitado: {feedback_context}" if feedback_context else ""

    cot_instruction = ""
    if enable_cot:
        cot_instruction = """
CHAIN-OF-THOUGHT ATIVADO:
Antes de selecionar os trechos, raciocine em voz alta:
1. Liste os temas centrais deste documento
2. Identifique como cada tema se relaciona com a consulta
3. Justifique por que cada trecho passa nas verificações constitucionais
Apresente o raciocínio entre tags <thinking>...</thinking> antes dos trechos.
"""

    prompt_text = f"""{SYSTEM_PROMPT}

CONSULTA: {query}{angle_str}{context_str}{feedback_str}
{CONSTITUTIONAL_RULES}
{cot_instruction}
TAREFA:
Extraia {n_instruction} do documento relevantes para a consulta.
Use critério TEMÁTICO — busque conceitos, mecanismos e contextos relacionados.
Para cada trecho:
- Uma frase de síntese técnica (contribuição para a consulta)
- O trecho copiado literalmente (preserve números, datas, terminologia técnica)

FORMATO (repita para cada trecho):
###
SÍNTESE: [frase técnica]
TRECHO: [cópia literal]

Responda "SEM CONTEÚDO RELEVANTE" apenas se o documento genuinamente não abordar o tema.

DOCUMENTO: {doc_filename}"""

    # Se tiver PDF em base64, monta conteúdo multimodal
    if doc_pdf_b64:
        return [
            {
                "type": "document",
                "source": {
                    "type":       "base64",
                    "media_type": "application/pdf",
                    "data":       doc_pdf_b64,
                },
            },
            {"type": "text", "text": prompt_text},
        ]
    else:
        return prompt_text + f"\n{doc_content[:15000]}"


def extract_with_batch(client, documents, relevant_ids, keywords_metadata,
                       query, angle, use_context, n_excerpts_mode,
                       feedback_context, enable_cot, use_pdf_direct):
    """
    Submete todos os documentos de uma vez via Batch API.
    Retorna resultados processados.
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

    # Monta requests para o batch
    batch_requests = []
    doc_meta_map   = {}

    for doc_id in relevant_ids:
        if doc_id not in documents:
            continue
        doc_data   = documents[doc_id]
        doc_meta   = keywords_metadata.get(doc_id, {})

        # Tenta carregar PDF original se use_pdf_direct estiver ativo
        pdf_b64 = None
        if use_pdf_direct:
            # Procura na pasta input/ pelo nome original sem .txt
            original_name = doc_data["filename"].replace(".txt", "")
            for ext in [".pdf", ".PDF"]:
                pdf_path = Path("input") / (original_name + ext)
                if pdf_path.exists():
                    try:
                        pdf_b64 = load_pdf_as_base64(str(pdf_path))
                    except Exception:
                        pass
                    break

        content = build_extraction_prompt(
            doc_data["filename"],
            doc_data["full_content"],
            query, angle, use_context,
            n_instruction, feedback_context,
            enable_cot, pdf_b64,
        )

        # Batch API espera messages como lista
        if isinstance(content, str):
            messages = [{"role": "user", "content": content}]
        else:
            messages = [{"role": "user", "content": content}]

        batch_requests.append({
            "custom_id": doc_id,
            "params": {
                "model":      "claude-sonnet-4-20250514",
                "max_tokens": 3000,
                "messages":   messages,
            },
        })

        doc_meta_map[doc_id] = {
            "filename":      doc_data["filename"],
            "doc_type":      doc_meta.get("doc_type", "—"),
            "sharepoint_url": doc_meta.get("sharepoint_url", ""),
            "full_content":  doc_data["full_content"],
        }

    if not batch_requests:
        return []

    # Submete batch
    batch = client.beta.messages.batches.create(requests=batch_requests)

    # Polling com progress bar
    progress = st.progress(0, text="Processando documentos em paralelo (Batch API)...")
    while True:
        batch = client.beta.messages.batches.retrieve(batch.id)
        counts = batch.request_counts
        total  = counts.processing + counts.succeeded + counts.errored + counts.canceled + counts.expired
        done   = counts.succeeded + counts.errored + counts.canceled + counts.expired
        if total > 0:
            progress.progress(done / total, text=f"Processando... {done}/{total} documentos")
        if batch.processing_status == "ended":
            break
        time.sleep(3)
    progress.empty()

    # Coleta resultados
    results = []
    for result in client.beta.messages.batches.results(batch.id):
        if result.result.type != "succeeded":
            continue
        doc_id = result.custom_id
        raw    = result.result.message.content[0].text.strip()

        if "SEM CONTEÚDO RELEVANTE" in raw:
            continue

        # Extrai thinking se chain-of-thought ativo
        thinking = ""
        if enable_cot and "<thinking>" in raw:
            start = raw.find("<thinking>") + len("<thinking>")
            end   = raw.find("</thinking>")
            if end > start:
                thinking = raw[start:end].strip()
                raw      = raw[end + len("</thinking>"):].strip()

        points = parse_blocks(raw)
        if points:
            meta = doc_meta_map.get(doc_id, {})
            results.append({
                "filename":       meta["filename"],
                "doc_type":       meta["doc_type"],
                "sharepoint_url": meta["sharepoint_url"],
                "points":         points,
                "thinking":       thinking,
            })

    return results


# ============================================================================
# EXTRAÇÃO — STREAMING (tempo real, sem batch)
# ============================================================================

def extract_with_streaming(client, documents, relevant_ids, keywords_metadata,
                           query, angle, use_context, n_excerpts_mode,
                           feedback_context, enable_cot, use_pdf_direct,
                           output_placeholder):
    """
    Processa documentos sequencialmente com streaming — output aparece em tempo real.
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

    results      = []
    stream_text  = ""

    for i, doc_id in enumerate(relevant_ids):
        if doc_id not in documents:
            continue
        doc_data = documents[doc_id]
        doc_meta = keywords_metadata.get(doc_id, {})

        pdf_b64 = None
        if use_pdf_direct:
            original_name = doc_data["filename"].replace(".txt", "")
            for ext in [".pdf", ".PDF"]:
                pdf_path = Path("input") / (original_name + ext)
                if pdf_path.exists():
                    try:
                        pdf_b64 = load_pdf_as_base64(str(pdf_path))
                    except Exception:
                        pass
                    break

        content = build_extraction_prompt(
            doc_data["filename"], doc_data["full_content"],
            query, angle, use_context,
            n_instruction, feedback_context,
            enable_cot, pdf_b64,
        )

        messages = [{"role": "user", "content": content}]
        raw = ""

        stream_text += f"\n\n**Analisando: {doc_data['filename'].replace('.txt','')}**\n"
        output_placeholder.markdown(stream_text + "▌")

        try:
            with client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=3000,
                messages=messages,
            ) as stream:
                for text_chunk in stream.text_stream:
                    raw        += text_chunk
                    stream_text += text_chunk
                    output_placeholder.markdown(stream_text + "▌")
        except Exception as e:
            st.warning(f"⚠️ Erro em `{doc_data['filename']}`: {e}")
            continue

        if "SEM CONTEÚDO RELEVANTE" in raw:
            continue

        thinking = ""
        if enable_cot and "<thinking>" in raw:
            start = raw.find("<thinking>") + len("<thinking>")
            end   = raw.find("</thinking>")
            if end > start:
                thinking = raw[start:end].strip()
                raw      = raw[end + len("</thinking>"):].strip()

        points = parse_blocks(raw)
        if points:
            results.append({
                "filename":       doc_data["filename"],
                "doc_type":       doc_meta.get("doc_type", "—"),
                "sharepoint_url": doc_meta.get("sharepoint_url", ""),
                "points":         points,
                "thinking":       thinking,
            })

    output_placeholder.empty()
    return results


# ============================================================================
# TEXTO ESTRUTURADO
# ============================================================================

def generate_structured_text(client, query, angle, use_context,
                              results, feedback_context, enable_cot):
    angle_str    = f"\nÂngulo de foco: {angle}" if angle else ""
    context_str  = f"\nContexto de uso: {use_context}" if use_context else ""
    feedback_str = f"\nRefinamento solicitado: {feedback_context}" if feedback_context else ""

    passages = "\n\n".join(
        f"[{r['filename']}]\n" +
        "\n".join(f"- {p['excerpt']}" for p in r["points"] if p.get("excerpt"))
        for r in results
    )

    cot_instruction = ""
    if enable_cot:
        cot_instruction = """
CHAIN-OF-THOUGHT ATIVADO:
Antes de redigir, raciocine entre tags <thinking>...</thinking>:
- Qual é a tese central que os trechos suportam?
- Existem contradições ou lacunas entre as fontes?
- Qual estrutura melhor serve à consulta?
"""

    prompt = f"""{SYSTEM_PROMPT}

CONSULTA: {query}{angle_str}{context_str}{feedback_str}
{CONSTITUTIONAL_RULES}
{cot_instruction}
Com base EXCLUSIVAMENTE nos trechos abaixo, produza um texto técnico estruturado.

ESTRUTURA (adapte conforme o conteúdo disponível):
## Contexto e relevância
## Posicionamento da IETA
## Implicações e análise
## Lacunas ou ausências identificadas na base

DIRETRIZES:
- Linguagem técnica e precisa para especialistas em mercados de carbono
- Cite sempre a fonte inline: [Fonte: nome_do_documento]
- Não adicione informações além dos trechos
- Se uma seção não tiver cobertura, diga explicitamente

TRECHOS DISPONÍVEIS:
{passages[:40000]}

TEXTO ESTRUTURADO:"""

    output_text = ""
    placeholder = st.empty()

    try:
        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for chunk in stream.text_stream:
                output_text += chunk
                # Filtra thinking do display principal
                display = output_text
                if "<thinking>" in display and "</thinking>" not in display:
                    display = display[:display.find("<thinking>")] + "_Raciocínio em andamento..._"
                elif "</thinking>" in display:
                    display = display[display.find("</thinking>") + len("</thinking>"):]
                placeholder.markdown(display + "▌")

        placeholder.markdown(output_text.split("</thinking>")[-1].strip()
                              if "</thinking>" in output_text else output_text)

        # Extrai thinking se presente
        thinking = ""
        if enable_cot and "<thinking>" in output_text:
            start    = output_text.find("<thinking>") + len("<thinking>")
            end      = output_text.find("</thinking>")
            thinking = output_text[start:end].strip() if end > start else ""

        return output_text.split("</thinking>")[-1].strip() if "</thinking>" in output_text else output_text, thinking

    except Exception as e:
        return f"_Erro ao gerar texto estruturado: {e}_", ""


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
st.markdown("Busca e curadoria de conteúdo técnico — lastreada exclusivamente na base de documentos internos da IETA Brasil.")
st.markdown("---")

# ── CONSULTA ─────────────────────────────────────────────────────────────────

st.markdown("**Consulta**")
st.caption(
    "Descreva com precisão o que deseja saber ou mapear. "
    "_Ex: \"Posicionamento da IETA sobre corresponding adjustments no Artigo 6.2\" "
    "ou \"Referências sobre integridade de créditos de carbono no mercado voluntário brasileiro.\"_"
)
query = st.text_area(
    "", placeholder="Ex: Posicionamento da IETA sobre o CBAM e seus impactos no setor produtivo brasileiro",
    height=90, label_visibility="collapsed",
)

angle = st.text_input(
    "**Ângulo ou foco específico** (opcional):",
    placeholder="Ex: Evidencie impactos no setor de hard-to-abate e reações do setor produtivo brasileiro",
)

col_ctx, col_out = st.columns(2)
with col_ctx:
    use_context = st.selectbox(
        "**Contexto de uso:**",
        options=[""] + USE_CONTEXTS,
        format_func=lambda x: "Selecione (opcional)" if x == "" else x,
    )
with col_out:
    output_mode = st.selectbox("**Formato do output:**", options=OUTPUT_MODES)

# ── FILTROS ───────────────────────────────────────────────────────────────────

st.markdown("**Filtros** — deixe keywords em branco para inferência automática")

col_kw, col_type = st.columns(2)
with col_kw:
    available_kws = sorted(keyword_index.keys()) if keyword_index else []
    kw_options    = [f"{kw} ({len(keyword_index[kw])} docs)" for kw in available_kws]
    raw_selected  = st.multiselect(
        "Keywords (opcional — se vazio, inferidas automaticamente):",
        options=kw_options, max_selections=8,
    )
    selected_keywords = [k.split(" (")[0] for k in raw_selected]

with col_type:
    selected_types_raw = st.multiselect("Tipos de documento:", options=DOC_TYPES, default=DOC_TYPES)
    selected_types = selected_types_raw if selected_types_raw else DOC_TYPES

col_n, col_proc = st.columns(2)
with col_n:
    n_excerpts_mode = st.selectbox(
        "**Trechos por documento:**",
        options=["0–10 trechos", "10–25 trechos", "Mais de 25"], index=0,
    )
with col_proc:
    processing_mode = st.selectbox(
        "**Modo de processamento:**",
        options=["Streaming — output em tempo real", "Batch — paralelo, 50% mais barato"],
        help="Streaming: veja os resultados aparecerem em tempo real. Batch: todos os documentos processados em paralelo, mais eficiente para bases grandes.",
    )

# ── OPÇÕES AVANÇADAS ──────────────────────────────────────────────────────────

with st.expander("⚙️ Opções avançadas"):
    col_adv1, col_adv2 = st.columns(2)

    with col_adv1:
        enable_cot = st.checkbox(
            "🧠 Ativar Chain-of-Thought",
            value=False,
            help="O modelo explicitará o raciocínio antes de selecionar os trechos.",
        )
        if enable_cot:
            st.warning(
                "⚠️ **Chain-of-Thought ativado** — espere um aumento de 30–50% no tempo de processamento "
                "e no custo por consulta. Recomendado para diagnóstico e calibração, não para uso rotineiro."
            )

    with col_adv2:
        enable_extended = st.checkbox(
            "🔬 Extended Thinking (diagnóstico)",
            value=False,
            help="Ativa o raciocínio estendido do modelo para entender por que determinadas escolhas foram feitas. Alto custo — use apenas para diagnóstico.",
        )
        if enable_extended:
            st.error(
                "⚠️ **Extended Thinking ativado** — pode triplicar o tempo e o custo. "
                "Use exclusivamente para diagnosticar resultados inesperados."
            )

        use_pdf_direct = st.checkbox(
            "📄 Envio direto de PDFs",
            value=False,
            help="Se o PDF original estiver disponível na pasta 'input/', envia diretamente ao modelo preservando tabelas e estrutura visual.",
        )
        if use_pdf_direct:
            st.info("ℹ️ PDFs originais buscados em `input/`. Documentos sem PDF usam o texto extraído normalmente.")

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

    # ── KEYWORDS ─────────────────────────────────────────────────────────
    if selected_keywords:
        active_keywords = selected_keywords
        kw_source = f"Keywords selecionadas manualmente: {', '.join(active_keywords)}"
    else:
        with st.spinner("Inferindo keywords relevantes..."):
            active_keywords = infer_keywords(client, query, angle, vocabulary)
        kw_source = (
            f"Keywords inferidas automaticamente: {', '.join(active_keywords)}"
            if active_keywords else "Nenhuma keyword inferida — consultando toda a base"
        )

    # ── FILTRA DOCUMENTOS ─────────────────────────────────────────────────
    if active_keywords:
        doc_scores = {}
        for kw in active_keywords:
            for doc_id in keyword_index.get(kw, []):
                doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1
        relevant_ids = [d for d, _ in sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)]
    else:
        relevant_ids = list(documents.keys())

    if selected_types:
        relevant_ids = [
            d for d in relevant_ids
            if keywords_metadata.get(d, {}).get("doc_type", "") in selected_types
        ]

    used_docs = [documents[d]["filename"] for d in relevant_ids if d in documents]

    if not used_docs:
        st.error("❌ Nenhum documento encontrado. Tente ampliar os filtros.")
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
        c1, c2 = st.columns([5, 2])
        with c1:
            st.markdown(f"{icon} [{orig}]({sp_url})" if sp_url else f"{icon} `{orig}`")
        with c2:
            st.caption(dtype)

    st.markdown("---")

    # ── EXTRAÇÃO ─────────────────────────────────────────────────────────
    feedback_context = st.session_state.get("feedback_context", "")
    use_batch = "Batch" in processing_mode

    if use_batch:
        st.info("⚙️ Processamento em paralelo via Batch API — aguarde...")
        results = extract_with_batch(
            client, documents, relevant_ids, keywords_metadata,
            query, angle, use_context, n_excerpts_mode,
            feedback_context, enable_cot, use_pdf_direct,
        )
    else:
        st.markdown("**Extraindo trechos em tempo real...**")
        stream_placeholder = st.empty()
        results = extract_with_streaming(
            client, documents, relevant_ids, keywords_metadata,
            query, angle, use_context, n_excerpts_mode,
            feedback_context, enable_cot, use_pdf_direct,
            stream_placeholder,
        )

    if not results:
        st.warning("⚠️ Nenhum trecho relevante encontrado. Tente ampliar os filtros ou reformular a consulta.")
        st.stop()

    st.session_state["last_results"] = results
    st.session_state["last_query"]   = query
    st.session_state["last_angle"]   = angle

    total_points = sum(len(r["points"]) for r in results)

    # ── OUTPUT ────────────────────────────────────────────────────────────
    if "Texto estruturado" in output_mode:
        st.markdown("### 📝 Análise estruturada")
        st.caption("Gerado exclusivamente a partir dos trechos extraídos da base.")
        structured, struct_thinking = generate_structured_text(
            client, query, angle, use_context,
            results, feedback_context, enable_cot,
        )

        if enable_cot and struct_thinking:
            with st.expander("🧠 Raciocínio do modelo (chain-of-thought)"):
                st.markdown(struct_thinking)

        st.markdown("---")
        st.markdown(f"#### 📑 Trechos de base ({total_points} em {len(results)} documento(s))")
        for result in results:
            orig   = result["filename"].replace(".txt", "")
            sp_url = result["sharepoint_url"]
            icon   = TYPE_ICONS.get(result["doc_type"], "📎")
            label  = f"{icon} [{orig}]({sp_url})" if sp_url else f"{icon} **{orig}**"
            with st.expander(label):
                st.caption(result["doc_type"])
                if enable_cot and result.get("thinking"):
                    with st.expander("🧠 Raciocínio"):
                        st.markdown(result["thinking"])
                for p in result["points"]:
                    if p.get("synthesis"):
                        st.markdown(f"**{p['synthesis']}**")
                    if p.get("excerpt"):
                        st.markdown(
                            f"<blockquote style='border-left:3px solid #1a1a2e;"
                            f"padding:8px 12px;margin:4px 0 12px 0;"
                            f"background:#f7f9fc;color:#333;font-size:0.88rem;"
                            f"font-style:italic'>{p['excerpt']}</blockquote>",
                            unsafe_allow_html=True,
                        )
        full_output = structured

    else:
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

            if enable_cot and result.get("thinking"):
                with st.expander("🧠 Raciocínio do modelo"):
                    st.markdown(result["thinking"])

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
    st.caption("Indique o que ajustar para uma nova iteração.")

    feedback = st.text_area(
        "O que ajustar na próxima busca?",
        placeholder="Ex: Aprofunde nos impactos setoriais e exclua referências puramente regulatórias.",
        height=80, key="feedback_input",
    )

    col_fb1, col_fb2 = st.columns(2)
    with col_fb1:
        if st.button("🔁 Refinar e buscar novamente", use_container_width=True, type="primary"):
            st.session_state["feedback_context"] = feedback
            st.rerun()
    with col_fb2:
        if st.button("🗑️ Limpar e começar nova busca", use_container_width=True):
            for key in ["last_results", "last_query", "last_angle", "last_context", "feedback_context"]:
                st.session_state.pop(key, None)
            st.rerun()

# ============================================================================
# RODAPÉ
# ============================================================================
st.markdown("---")
st.caption("🌐 IETA Brazil Initiative · Use 'Recarregar' na sidebar sempre que a base for atualizada.")