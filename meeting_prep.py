import streamlit as st
from pathlib import Path
from PyPDF2 import PdfReader
from docx import Document
import urllib.parse
import json

st.set_page_config(
    page_title="IETA Wizard",
    page_icon="🧙",
    layout="wide"
)

# ============================================================================
# FUNÇÕES DE KEYWORDS
# ============================================================================

@st.cache_data
def load_keywords_metadata():
    """Carrega metadata de keywords dos documentos"""
    # Tenta primeiro na pasta metadata/, depois na raiz
    metadata_file = Path("metadata/keywords_metadata.json")
    if not metadata_file.exists():
        metadata_file = Path("keywords_metadata.json")
    if metadata_file.exists():
        with open(metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

@st.cache_data
def load_keyword_index():
    """Carrega índice invertido de keywords"""
    # Tenta primeiro na pasta metadata/, depois na raiz
    index_file = Path("metadata/keywords_metadata_index.json")
    if not index_file.exists():
        index_file = Path("keywords_metadata_index.json")
    if index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def get_available_keywords(keyword_index):
    """Retorna lista de keywords disponíveis organizadas por categoria"""
    
    # Organização por categoria (ajuste conforme seu domínio)
    keyword_categories = {
        "📋 Regulação": [
            "artigo-6.2", "artigo-6.4", "sbce", "cdm-transition", 
            "compliance-market", "corresponding-adjustments", "mrv", 
            "transparency", "baseline"
        ],
        "💼 Mercado": [
            "ecora", "vcm", "voluntary-carbon-market", "certificação", 
            "credito-carbono", "open-coalition", "financiamento", 
            "tfff", "ecoinvest", "fundo-clima", "jredd", "cadtrust", 
            "registry", "verificação"
        ],
        "🏭 Setores": [
            "nbs", "nature-based-solutions", "floresta", "reflorestamento",
            "biocombustiveis", "etanol", "biodiesel", "saf",
            "energia", "renovaveis", "solar", "eolica", "hidro",
            "cimento", "mineracao", "aviacao", "hard-to-abate",
            "agricultura", "pecuaria", "uso-do-solo"
        ],
        "🌐 Conceitos": [
            "integridade", "adicionalidade", "permanencia", "metodologia",
            "escopo-1", "escopo-2", "escopo-3", "inventario",
            "net-zero", "neutralidade", "compensacao", "remocao",
            "co-beneficios", "sdgs", "comunidades-tradicionais"
        ],
        "🗺️ Geografia": [
            "brasil", "amazonia", "cerrado", "mata-atlantica",
            "america-latina", "global", "bilateral"
        ]
    }
    
    # Filtra apenas keywords que existem no índice
    available_categories = {}
    for category, keywords in keyword_categories.items():
        available = [kw for kw in keywords if kw in keyword_index]
        if available:
            available_categories[category] = available
    
    return available_categories

def get_documents_by_keywords(selected_keywords, keyword_index, metadata):
    """
    Retorna documentos filtrados pelas keywords selecionadas
    Ordenados por relevância (número de keywords matched)
    """
    if not selected_keywords:
        # Se nenhuma keyword selecionada, retorna todos
        return list(metadata.keys())
    
    doc_scores = {}  # doc_id -> número de keywords matched
    
    for keyword in selected_keywords:
        if keyword in keyword_index:
            for doc_id in keyword_index[keyword]:
                doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1
    
    # Ordena por relevância
    sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
    
    return [doc_id for doc_id, score in sorted_docs]

# ============================================================================
# FUNÇÃO PARA CARREGAR DOCUMENTOS (ADAPTADA)
# ============================================================================

@st.cache_data
def load_all_documents():
    """Carrega documentos TXT da pasta documents/"""
    docs_folder = Path("documents")
    all_content = {}
    
    if not docs_folder.exists():
        return {}
    
    for file_path in docs_folder.glob("*.txt"):
        try:
            content = file_path.read_text(encoding='utf-8')
            
            if content.strip():
                # Remove extensão .txt para match com metadata
                doc_id = file_path.stem
                
                all_content[doc_id] = {
                    'filename': file_path.name,
                    'full_content': content,
                    'size_kb': len(content) / 1024,
                    'char_count': len(content),
                    'filepath': str(file_path)
                }
                
        except Exception as e:
            st.sidebar.warning(f"⚠️ Erro ao carregar {file_path.name}")
    
    return all_content

# ============================================================================
# TÍTULO E MENU
# ============================================================================

st.title("🧙 IETA Wizard")

# Menu de ferramentas
tool_choice = st.radio(
    "Escolha a ferramenta:",
    ["🎯 Meeting Prep", "🎤 Panel Prep"],
    horizontal=True
)

# ============================================================================
# SIDEBAR COM KEYWORDS
# ============================================================================

with st.sidebar:
    st.header("📊 Base de Conhecimento")
    
    # Botão de reload
    if st.button("🔄 Recarregar Documentos", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.success("✅ Base atualizada!")
        st.rerun()
    
    st.markdown("---")
    
    # Carregar documentos e metadata
    documents = load_all_documents()
    keywords_metadata = load_keywords_metadata()
    keyword_index = load_keyword_index()
    
    if not documents:
        st.error("❌ Nenhum documento encontrado!")
        st.info("Adicione arquivos TXT na pasta 'documents/'")
    else:
        st.success(f"✅ {len(documents)} documentos")
        
        # Estatísticas gerais
        total_chars = sum(doc['char_count'] for doc in documents.values())
        total_kb = sum(doc['size_kb'] for doc in documents.values())
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Caracteres", f"{total_chars:,}")
        with col2:
            st.metric("Tamanho", f"{total_kb:.1f} KB")
    
    st.markdown("---")
    
    # ========================================================================
    # SELEÇÃO DE KEYWORDS (PRINCIPAL)
    # ========================================================================
    
    st.header("🔍 Selecionar Keywords para Filtrar Documentos")
    st.markdown("**Selecione até 5 keywords das categorias abaixo. Os documentos correspondentes aparecerão automaticamente.**")
    
    # Verifica se há metadata de keywords
    if keyword_index:
        st.success(f"✅ {len(keyword_index)} keywords disponíveis em {len(keywords_metadata)} documentos")
        
        # Organiza keywords por categoria
        keyword_categories = get_available_keywords(keyword_index)
        
        # Cria lista plana de todas as keywords com contagem
        all_keywords_flat = []
        for category, keywords in keyword_categories.items():
            for kw in keywords:
                doc_count = len(keyword_index.get(kw, []))
                all_keywords_flat.append(f"{kw} ({doc_count} docs)")
        
        # Seleção múltipla de keywords (limitado a 5)
        selected_keywords_raw = st.multiselect(
            "Selecione até 5 keywords:",
            options=all_keywords_flat,
            max_selections=5,
            help="Selecione keywords relevantes para sua reunião/painel. Os documentos que contêm essas keywords serão mostrados abaixo."
        )
        
        # Extrai apenas o nome da keyword (remove contagem)
        selected_keywords = [kw.split(" (")[0] for kw in selected_keywords_raw]
        
        # Mostra keywords selecionadas
        if selected_keywords:
            st.markdown("**✅ Keywords selecionadas:**")
            cols = st.columns(len(selected_keywords))
            for i, kw in enumerate(selected_keywords):
                with cols[i]:
                    st.markdown(f"🏷️ **{kw}**")
            
            # Calcula documentos filtrados
            filtered_docs = get_documents_by_keywords(
                selected_keywords, keyword_index, keywords_metadata
            )
            
            st.markdown("---")
            st.subheader(f"📚 Documentos Encontrados ({len(filtered_docs)})")
            
            if filtered_docs:
                # Mostra lista de documentos encontrados
                for idx, doc_id in enumerate(filtered_docs[:20], 1):  # Limita a 20 para não sobrecarregar
                    if doc_id in keywords_metadata:
                        doc_meta = keywords_metadata[doc_id]
                        doc_keywords = doc_meta.get('keywords', [])
                        # Calcula relevância (quantas keywords do documento foram selecionadas)
                        relevance = len(set(doc_keywords) & set(selected_keywords))
                        
                        with st.expander(f"{idx}. {doc_meta.get('filename', doc_id)} (Relevância: {relevance}/{len(selected_keywords)})"):
                            st.markdown(f"**Arquivo:** `{doc_meta.get('filename', doc_id)}`")
                            st.markdown(f"**Keywords do documento:** {', '.join(doc_keywords) if doc_keywords else 'Nenhuma'}")
                            st.markdown(f"**Tamanho:** {doc_meta.get('word_count', 0):,} palavras | {doc_meta.get('char_count', 0):,} caracteres")
                
                if len(filtered_docs) > 20:
                    st.info(f"Mostrando 20 de {len(filtered_docs)} documentos. Use essas keywords no prompt para focar nos documentos mais relevantes.")
            else:
                st.warning("⚠️ Nenhum documento encontrado com essas keywords. Tente selecionar outras keywords.")
        else:
            st.info("👆 Selecione keywords acima para ver os documentos correspondentes")
            filtered_docs = []
        
        use_keywords = len(selected_keywords) > 0
    else:
        st.warning("⚠️ Metadata de keywords não encontrada")
        st.info("Execute: `python process_and_sync.py --keywords-only` para gerar keywords")
        use_keywords = False
        selected_keywords = []
        filtered_docs = []
    
    st.markdown("---")
    
    # Lista de documentos
    if documents:
        with st.expander("📄 Ver documentos"):
            for doc_id, doc_data in sorted(documents.items()):
                # Mostra keywords do documento se disponível
                if doc_id in keywords_metadata:
                    doc_keywords = keywords_metadata[doc_id].get('keywords', [])
                    st.text(f"• {doc_data['filename']}")
                    st.caption(f"  🏷️ {', '.join(doc_keywords)}")
                else:
                    st.text(f"• {doc_data['filename']}")
                st.caption(f"  {doc_data['char_count']:,} chars")
    
    st.markdown("---")
    st.caption("🌐 IETA Brazil Initiative")

# ============================================================================
# VERIFICAÇÃO DE DOCUMENTOS
# ============================================================================

if not documents:
    st.warning("⚠️ Adicione documentos à pasta 'documents/' e clique em 'Recarregar Documentos'")
    st.stop()

# ============================================================================
# FUNÇÃO AUXILIAR: PREPARAR CONTEXTO FILTRADO
# ============================================================================

def prepare_filtered_context(documents, selected_keywords, keyword_index, keywords_metadata):
    """
    Prepara contexto apenas com documentos relevantes às keywords
    """
    # Se keywords ativas, filtra documentos
    if selected_keywords:
        relevant_doc_ids = get_documents_by_keywords(
            selected_keywords, keyword_index, keywords_metadata
        )
        
        if not relevant_doc_ids:
            st.error("❌ Nenhum documento encontrado com essas keywords!")
            return None, []
    else:
        # Sem filtro, usa todos
        relevant_doc_ids = list(documents.keys())
    
    # Prepara contexto
    docs_context = []
    used_docs = []
    
    for doc_id in relevant_doc_ids:
        if doc_id in documents:
            doc_data = documents[doc_id]
            content = doc_data['full_content'][:12000]
            
            # Info sobre keywords do documento
            doc_keywords = ""
            if doc_id in keywords_metadata:
                kw_list = keywords_metadata[doc_id].get('keywords', [])
                doc_keywords = f"\nKeywords: {', '.join(kw_list)}"
            
            docs_context.append(f"""
{'='*70}
DOCUMENTO: {doc_data['filename']}
Tamanho: {doc_data['char_count']:,} caracteres{doc_keywords}
{'='*70}

{content}

""")
            used_docs.append(doc_data['filename'])
    
    # Limita contexto total
    full_context = "\n".join(docs_context)[:80000]
    
    return full_context, used_docs

# ============================================================================
# MEETING PREP
# ============================================================================

if tool_choice == "🎯 Meeting Prep":
    st.markdown("### Preparação para Reuniões")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        organization = st.text_input(
            "**Organização/Participantes:**",
            placeholder="Ex: IBP - Instituto Brasileiro do Petróleo"
        )
    
    with col2:
        meeting_date = st.date_input("**Data:**")
    
    topics = st.text_area(
        "**Tópicos principais:**",
        placeholder="Ex: SBCE, CBAM, CBIOs, certificados de biometano",
        height=100
    )
    
    col3, col4 = st.columns(2)
    
    with col3:
        meeting_type = st.selectbox(
            "**Tipo:**",
            ["Reunião de Mapeamento", "Painel", "Call Técnico", "Workshop", "Bilateral"]
        )
    
    with col4:
        detail_level = st.select_slider(
            "**Detalhe:**",
            options=["Rápido", "Padrão", "Completo"],
            value="Padrão"
        )
    
    objectives = st.text_area(
        "**Objetivos (opcional):**",
        placeholder="Ex: Mapear prioridades do setor, identificar oportunidades",
        height=80
    )
    
    st.markdown("---")
    
    if st.button("🚀 Gerar Briefing", type="primary", use_container_width=True):
        
        if not organization or not topics:
            st.error("⚠️ Preencha pelo menos Organização e Tópicos")
        else:
                with st.spinner("🔍 Preparando briefing com documentos filtrados..."):
                    
                    # Prepara contexto filtrado por keywords
                    full_context, used_docs = prepare_filtered_context(
                        documents, selected_keywords, keyword_index, keywords_metadata
                    )
                    
                    if full_context is None:
                        st.stop()
                    
                    # Ajustar seções por nível
                    if detail_level == "Rápido":
                        sections = """
1. 🎯 Objetivos Estratégicos (2-3 pontos)
2. 💡 Posições IETA Relevantes (cite documentos específicos)
3. 🗣️ 3 Talking Points Principais
"""
                    elif detail_level == "Padrão":
                        sections = """
1. 🎯 Objetivos Estratégicos IETA
2. 📊 Contexto sobre a Organização
3. 💡 Posições IETA Relevantes (SEMPRE cite o documento fonte)
4. 🗣️ 5 Talking Points Estratégicos
5. ❓ 3-4 Perguntas Prováveis e Respostas
"""
                    else:  # Completo
                        sections = """
1. 🎯 Objetivos Estratégicos IETA
2. 📊 Contexto Detalhado sobre a Organização
3. 💡 Posições IETA Relevantes (com citações literais dos documentos)
4. 🗣️ 7 Talking Points Estratégicos
5. ❓ 5+ Perguntas Prováveis e Respostas Preparadas
6. ⚠️ Considerações Estratégicas (Oportunidades e Riscos)
7. 📋 Action Items para Follow-up
"""
                    
                    # Info sobre filtro aplicado
                    filter_info = ""
                    if selected_keywords:
                        filter_info = f"""
IMPORTANTE: Esta reunião foi preparada usando APENAS documentos filtrados pelas seguintes keywords:
{', '.join(selected_keywords)}

Documentos utilizados ({len(used_docs)}):
{chr(10).join([f"- {doc}" for doc in used_docs])}
"""
                    
                    # Criar prompt
                    prompt = f"""Você é um assistente especializado da IETA (International Emissions Trading Association) Brasil.

REGRAS CRÍTICAS DE RESPOSTA:
1. Use APENAS informações dos documentos fornecidos abaixo
2. SEMPRE cite a fonte: "Segundo [nome do documento], ..."
3. Use dados numéricos EXATOS dos documentos (não invente)
4. Se não houver informação específica, diga claramente
5. Priorize informações de Position Papers oficiais
6. Quando múltiplos documentos mencionarem algo, sintetize mostrando convergências

{filter_info}

INFORMAÇÕES DA REUNIÃO:
- Organização: {organization}
- Data: {meeting_date}
- Tipo: {meeting_type}
- Tópicos: {topics}
- Objetivos: {objectives if objectives else "Mapear oportunidades e alinhar posições"}

DOCUMENTOS IETA ({len(used_docs)} documentos selecionados, ~{len(full_context):,} caracteres):

{full_context}

TAREFA:
Crie um briefing executivo estruturado para esta reunião.

ESTRUTURA DO BRIEFING:
{sections}

FORMATO:
- Use markdown com headers (##, ###) e bullet points
- Cada afirmação importante deve incluir [Fonte: nome_do_documento]
- Seja específico e prático
- Foque em informações ACIONÁVEIS

BRIEFING:
"""
                    
                    # Mostrar resultados
                    st.success("✅ Prompt gerado!")
                    
                    # Estatísticas
                    col_stat1, col_stat2, col_stat3 = st.columns(3)
                    
                    with col_stat1:
                        st.metric("Documentos incluídos", len(used_docs))
                    
                    with col_stat2:
                        st.metric("Caracteres", f"{len(full_context):,}")
                    
                    with col_stat3:
                        st.metric("Tokens aprox.", f"{len(full_context)//4:,}")
                    
                    # Mostra keywords usadas
                    if selected_keywords:
                        st.info(f"🏷️ **Filtrado por keywords:** {', '.join(selected_keywords)}")
                    
                    st.markdown("---")
                    
                    # Mostrar prompt
                    st.markdown("### 📋 Prompt Gerado (Copie e Cole no ChatGPT/Claude)")
                    
                    st.text_area(
                        "Prompt completo:",
                        prompt,
                        height=400,
                        help="Copie todo este texto e cole no ChatGPT ou Claude.ai"
                    )
                    
                    # Botões de ação
                    encoded_prompt = urllib.parse.quote(prompt[:2000])
                    
                    col_btn1, col_btn2 = st.columns(2)
                    
                    with col_btn1:
                        st.download_button(
                            "📥 Baixar Prompt",
                            prompt,
                            file_name=f"briefing_{organization.replace(' ', '_')}_{meeting_date}.txt",
                            use_container_width=True
                        )
                    
                    with col_btn2:
                        st.markdown(f"""
                        <a href="https://chat.openai.com/?q={encoded_prompt}" target="_blank">
                            <button style="
                                width: 100%;
                                height: 43px;
                                padding: 0.5rem;
                                background-color: #10a37f;
                                color: white;
                                border: none;
                                border-radius: 0.5rem;
                                cursor: pointer;
                                font-size: 14px;
                                font-weight: 500;
                            ">
                                🤖 Abrir no ChatGPT
                            </button>
                        </a>
                        """, unsafe_allow_html=True)
                    
                    st.info("💡 **Dica:** O botão ChatGPT abre com parte do prompt. Para prompt completo, copie da caixa acima!")

# ============================================================================
# PANEL PREP
# ============================================================================

elif tool_choice == "🎤 Panel Prep":
    st.markdown("### Preparação para Painéis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        panel_title = st.text_input(
            "**Título do Painel:**",
            placeholder="Ex: Descarbonização da Aviação e Mercados de Carbono"
        )
        
        event_name = st.text_input(
            "**Evento:**",
            placeholder="Ex: Conferência Anual Aviação Sustentável"
        )
    
    with col2:
        panel_date = st.date_input("**Data:**")
        
        your_role = st.selectbox(
            "**Seu papel:**",
            ["Painelista", "Moderador", "Keynote Speaker"]
        )
    
    panel_topic = st.text_area(
        "**Tema/questão do painel:**",
        placeholder="Ex: Como SBCE e CBAM impactam aviação? Oportunidades e desafios.",
        height=100
    )
    
    col3, col4 = st.columns(2)
    
    with col3:
        duration = st.selectbox(
            "**Duração da sua fala:**",
            ["5 minutos", "10 minutos", "15 minutos", "20 minutos"]
        )
    
    with col4:
        prep_level = st.select_slider(
            "**Preparação:**",
            options=["Básico", "Intermediário", "Avançado"],
            value="Intermediário"
        )
    
    audience = st.text_input(
        "**Público esperado:**",
        placeholder="Ex: Executivos de aviação, reguladores"
    )
    
    other_panelists = st.text_area(
        "**Outros painelistas (opcional):**",
        placeholder="Ex: Representante da ANAC, CEO de companhia aérea, especialista em SAF",
        height=80
    )
    
    key_message = st.text_area(
        "**Mensagem-chave que quer transmitir (opcional):**",
        placeholder="Ex: Brasil pode liderar transição verde na aviação através de SAF e mercados bem desenhados",
        height=80
    )
    
    st.markdown("---")
    
    if st.button("🎤 Gerar Preparação para Painel", type="primary", use_container_width=True):
        
        if not panel_title or not panel_topic:
            st.error("⚠️ Preencha pelo menos Título e Tema do Painel")
        else:
            with st.spinner("🔍 Preparando material para painel..."):
                    
                    # Prepara contexto filtrado
                    full_context, used_docs = prepare_filtered_context(
                        documents, selected_keywords, keyword_index, keywords_metadata
                    )
                    
                    if full_context is None:
                        st.stop()
                    
                    # Ajustar por nível
                    if prep_level == "Básico":
                        sections = """
1. 🎯 Mensagem Central (1 frase impactante)
2. 💡 3 Pontos-Chave para Sua Fala
3. 📊 2-3 Dados de Apoio dos documentos
4. 🎤 Sugestão de Abertura
5. 📚 Sugestão de Fechamento
"""
                    elif prep_level == "Intermediário":
                        sections = """
1. 🎯 Mensagem Central e Narrativa
2. 💡 5 Pontos Principais Estruturados
3. 📊 Dados e Evidências (com fontes)
4. 🎤 Abertura Impactante
5. 🗣️ Possíveis Perguntas do Moderador/Audiência
6. 📚 Fechamento Memorável
7. ⏰ Estrutura por Tempo ({duration})
"""
                    else:  # Avançado
                        sections = """
1. 🎯 Narrativa Estratégica Completa
2. 💡 7-10 Pontos de Argumentação
3. 📊 Dados, Evidências e Cases (citando documentos)
4. 🎤 Múltiplas Opções de Abertura
5. 🗣️ Banco de Q&A (10+ perguntas)
6. 💬 Soundbites para Mídia/Redes
7. 📚 Variações de Fechamento
8. ⏰ Roteiro Minuto a Minuto
9. 🎭 Gestão de Debates e Contra-argumentos
"""
                    
                    # Info sobre filtro
                    filter_info = ""
                    if selected_keywords:
                        filter_info = f"""
IMPORTANTE: Esta preparação usa APENAS documentos filtrados pelas keywords:
{', '.join(selected_keywords)}

Documentos utilizados ({len(used_docs)}):
{chr(10).join([f"- {doc}" for doc in used_docs])}
"""
                    
                    prompt = f"""Você é um coach de comunicação especializado em painéis sobre mercados de carbono para a IETA.

REGRAS CRÍTICAS:
1. Use APENAS informações dos documentos IETA fornecidos
2. Cite fontes específicas: [Fonte: nome_documento]
3. Foque em comunicação CLARA e IMPACTANTE
4. Adapte ao tempo disponível ({duration})
5. Considere o público: {audience if audience else "profissionais do setor"}

{filter_info}

PAINEL:
- Título: {panel_title}
- Evento: {event_name}
- Data: {panel_date}
- Seu papel: {your_role}
- Duração: {duration}
- Tema: {panel_topic}
- Público: {audience if audience else "profissionais do setor"}
- Outros painelistas: {other_panelists if other_panelists else "Não informado"}
- Mensagem-chave desejada: {key_message if key_message else "A definir com base nos documentos IETA"}

DOCUMENTOS IETA ({len(used_docs)} documentos):

{full_context}

TAREFA:
Crie uma preparação completa e prática para este painel.

ESTRUTURA:
{sections}

DIRETRIZES:
- Seja PRÁTICO e ACIONÁVEL
- Pense em storytelling, não só dados
- Inclua transições naturais
- Prepare para imprevistos
- Use dados concretos dos documentos IETA

PREPARAÇÃO:
"""
                    
                    # Mostrar resultados
                    st.success("✅ Preparação estruturada!")
                    
                    col_stat1, col_stat2 = st.columns(2)
                    
                    with col_stat1:
                        st.metric("Documentos", len(used_docs))
                    
                    with col_stat2:
                        st.metric("Contexto", f"{len(full_context):,} chars")
                    
                    if selected_keywords:
                        st.info(f"🏷️ **Filtrado por keywords:** {', '.join(selected_keywords)}")
                    
                    st.markdown("---")
                    
                    st.markdown("### 🎤 Prompt para Panel Prep")
                    
                    st.text_area(
                        "Prompt completo:",
                        prompt,
                        height=400
                    )
                    
                    # Botões
                    encoded_prompt = urllib.parse.quote(prompt[:2000])
                    
                    col_btn1, col_btn2 = st.columns(2)
                    
                    with col_btn1:
                        st.download_button(
                            "📥 Baixar Prompt",
                            prompt,
                            file_name=f"panel_{panel_title[:30].replace(' ', '_')}_{panel_date}.txt",
                            use_container_width=True
                        )
                    
                    with col_btn2:
                        st.markdown(f"""
                        <a href="https://chat.openai.com/?q={encoded_prompt}" target="_blank">
                            <button style="
                                width: 100%;
                                height: 43px;
                                padding: 0.5rem;
                                background-color: #10a37f;
                                color: white;
                                border: none;
                                border-radius: 0.5rem;
                                cursor: pointer;
                                font-size: 14px;
                                font-weight: 500;
                            ">
                                🤖 Abrir no ChatGPT
                            </button>
                        </a>
                        """, unsafe_allow_html=True)
                    
                    st.info("💡 **Dica:** O botão ChatGPT abre com parte do prompt. Para prompt completo, copie da caixa acima!")

# Rodapé
st.markdown("---")
st.caption("💡 **Dica:** Copie o prompt gerado e cole no ChatGPT Plus ou Claude.ai para melhores resultados!")
st.caption("🔄 Use 'Recarregar Documentos' sempre que adicionar novos arquivos à pasta.")
st.caption("🏷️ Use keywords para focar em documentos específicos sobre os temas da reunião/painel.")