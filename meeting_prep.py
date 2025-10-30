import streamlit as st
from pathlib import Path
from PyPDF2 import PdfReader
from docx import Document
import urllib.parse  # NOVO: Para criar links do ChatGPT

st.set_page_config(
    page_title="IETA Wizard",
    page_icon="🧙",
    layout="wide"
)

# Função para carregar documentos COM MAIS CONTEÚDO
@st.cache_data
def load_all_documents():
    """Carrega documentos com máximo conteúdo possível"""
    docs_folder = Path("documents")
    all_content = {}
    
    if not docs_folder.exists():
        return {}
    
    for file_path in docs_folder.iterdir():
        if file_path.is_file():
            try:
                content = ""
                
                if file_path.suffix.lower() == '.pdf':
                    reader = PdfReader(file_path)
                    for page in reader.pages:
                        content += page.extract_text()
                
                elif file_path.suffix.lower() == '.docx':
                    doc = Document(file_path)
                    content = "\n".join([p.text for p in doc.paragraphs])
                
                elif file_path.suffix.lower() == '.txt':
                    content = file_path.read_text(encoding='utf-8')
                
                if content.strip():
                    all_content[file_path.name] = {
                        'full_content': content,  # Conteúdo completo
                        'size_kb': len(content) / 1024,
                        'char_count': len(content)
                    }
                    
            except Exception as e:
                st.sidebar.warning(f"⚠️ Erro: {file_path.name}")
    
    return all_content

# Título e menu
st.title("🧙 IETA Wizard")

# Menu de ferramentas
tool_choice = st.radio(
    "Escolha a ferramenta:",
    ["🎯 Meeting Prep", "🎤 Panel Prep"],
    horizontal=True
)

# Sidebar
with st.sidebar:
    st.header("📊 Base de Conhecimento")
    
    # BOTÃO DE RELOAD
    if st.button("🔄 Recarregar Documentos", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.success("✅ Base atualizada!")
        st.rerun()
    
    st.markdown("---")
    
    # Carregar documentos
    documents = load_all_documents()
    
    if documents:
        st.success(f"✅ {len(documents)} documentos")
        
        # Estatísticas
        total_chars = sum(doc['char_count'] for doc in documents.values())
        total_kb = sum(doc['size_kb'] for doc in documents.values())
        
        st.metric("Total de caracteres", f"{total_chars:,}")
        st.metric("Tamanho total", f"{total_kb:.1f} KB")
        
        # Lista de documentos
        with st.expander("📄 Ver documentos"):
            for doc_name, doc_data in sorted(documents.items()):
                st.text(f"• {doc_name}")
                st.caption(f"  {doc_data['char_count']:,} chars")
    else:
        st.error("❌ Nenhum documento encontrado!")
        st.info("Adicione arquivos PDF, DOCX ou TXT na pasta 'documents/'")
    
    st.markdown("---")
    st.caption("🌍 IETA Brazil Initiative")

# Main content
if not documents:
    st.warning("⚠️ Adicione documentos à pasta 'documents/' e clique em 'Recarregar Documentos'")
    st.stop()

# ==============================================================================
# MEETING PREP
# ==============================================================================

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
            with st.spinner("📝 Preparando briefing com documentos completos..."):
                
                # Preparar contexto COM MUITO MAIS CONTEÚDO
                docs_context = []
                
                for doc_name, doc_data in documents.items():
                    # Pegar primeiros 12.000 caracteres de cada doc (era 2.500!)
                    content = doc_data['full_content'][:12000]
                    
                    docs_context.append(f"""
{'='*70}
DOCUMENTO: {doc_name}
Tamanho: {doc_data['char_count']:,} caracteres
{'='*70}

{content}

""")
                
                # Limitar contexto total para não explodir (máx 80k chars)
                full_context = "\n".join(docs_context)[:80000]
                
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
                
                # Criar prompt melhorado
                prompt = f"""Você é um assistente especializado da IETA (International Emissions Trading Association) Brasil.

REGRAS CRÍTICAS DE RESPOSTA:
1. Use APENAS informações dos documentos fornecidos abaixo
2. SEMPRE cite a fonte: "Segundo [nome do documento], ..."
3. Use dados numéricos EXATOS dos documentos (não invente)
4. Se não houver informação específica, diga claramente
5. Priorize informações de Position Papers oficiais
6. Quando múltiplos documentos mencionarem algo, sintetize mostrando convergências

INFORMAÇÕES DA REUNIÃO:
- Organização: {organization}
- Data: {meeting_date}
- Tipo: {meeting_type}
- Tópicos: {topics}
- Objetivos: {objectives if objectives else "Mapear oportunidades e alinhar posições"}

DOCUMENTOS IETA COMPLETOS ({len(documents)} documentos, ~{len(full_context):,} caracteres):

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
                st.success("✅ Prompt gerado com documentos completos!")
                
                # Estatísticas
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                
                with col_stat1:
                    st.metric("Documentos incluídos", len(documents))
                
                with col_stat2:
                    st.metric("Caracteres no contexto", f"{len(full_context):,}")
                
                with col_stat3:
                    st.metric("Tokens aproximados", f"{len(full_context)//4:,}")
                
                st.markdown("---")
                
                # Mostrar prompt
                st.markdown("### 📋 Prompt Gerado (Copie e Cole no ChatGPT/Claude)")
                
                st.text_area(
                    "Prompt completo:",
                    prompt,
                    height=400,
                    help="Copie todo este texto e cole no ChatGPT ou Claude.ai"
                )
                
                # NOVO: Botões de ação melhorados
                # Encode do prompt para URL do ChatGPT
                encoded_prompt = urllib.parse.quote(prompt[:2000])  # Limite de URL
                
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    st.download_button(
                        "📥 Baixar Prompt",
                        prompt,
                        file_name=f"briefing_{organization.replace(' ', '_')}_{meeting_date}.txt",
                        use_container_width=True
                    )
                
                with col_btn2:
                    # Botão para abrir ChatGPT
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

# ==============================================================================
# PANEL PREP
# ==============================================================================

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
            with st.spinner("📝 Preparando material para painel..."):
                
                # Preparar contexto (mesmo sistema do Meeting Prep)
                docs_context = []
                
                for doc_name, doc_data in documents.items():
                    content = doc_data['full_content'][:12000]
                    
                    docs_context.append(f"""
{'='*70}
DOCUMENTO: {doc_name}
{'='*70}

{content}

""")
                
                full_context = "\n".join(docs_context)[:80000]
                
                # Ajustar por nível
                if prep_level == "Básico":
                    sections = """
1. 🎯 Mensagem Central (1 frase impactante)
2. 💡 3 Pontos-Chave para Sua Fala
3. 📊 2-3 Dados de Apoio dos documentos
4. 🎤 Sugestão de Abertura
5. 🔚 Sugestão de Fechamento
"""
                elif prep_level == "Intermediário":
                    sections = """
1. 🎯 Mensagem Central e Narrativa
2. 💡 5 Pontos Principais Estruturados
3. 📊 Dados e Evidências (com fontes)
4. 🎤 Abertura Impactante
5. 🗣️ Possíveis Perguntas do Moderador/Audiência
6. 🔚 Fechamento Memorável
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
7. 🔚 Variações de Fechamento
8. ⏰ Roteiro Minuto a Minuto
9. 🎭 Gestão de Debates e Contra-argumentos
"""
                
                prompt = f"""Você é um coach de comunicação especializado em painéis sobre mercados de carbono para a IETA.

REGRAS CRÍTICAS:
1. Use APENAS informações dos documentos IETA fornecidos
2. Cite fontes específicas: [Fonte: nome_documento]
3. Foque em comunicação CLARA e IMPACTANTE
4. Adapte ao tempo disponível ({duration})
5. Considere o público: {audience if audience else "profissionais do setor"}

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

DOCUMENTOS IETA ({len(documents)} documentos):

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
                    st.metric("Documentos", len(documents))
                
                with col_stat2:
                    st.metric("Contexto", f"{len(full_context):,} chars")
                
                st.markdown("---")
                
                st.markdown("### 🎤 Prompt para Panel Prep")
                
                st.text_area(
                    "Prompt completo:",
                    prompt,
                    height=400
                )
                
                # NOVO: Botões melhorados para Panel Prep também
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
