# IETA Prep Tools

Ferramentas de preparação para reuniões e painéis da IETA Brazil Initiative.

## Ferramentas Disponíveis

- 🎯 **Meeting Prep**: Preparação para reuniões bilaterais e técnicas
- 🎤 **Panel Prep**: Preparação para painéis e apresentações
- ✂️ **Chunk Documents**: Divide documentos grandes em partes processáveis

## Como Usar as Ferramentas Principais

1. Acesse o app: https://ieta-prep-tools.streamlit.app/
2. Escolha a ferramenta (Meeting ou Panel)
3. Preencha as informações
4. Clique em "Gerar" e copie o prompt
5. Cole no ChatGPT ou Claude para obter o briefing completo

## Como Processar Documentos Grandes

Se você tem documentos muito grandes (50+ páginas):

1. Criar pasta `documentos_grandes/` na raiz do projeto
2. Colocar PDFs ou Words grandes nessa pasta
3. Executar: `python chunk_documents.py`
4. Chunks aparecerão em `documentos_chunked/`
5. Mover os chunks para `documents/`
6. Clicar em "Recarregar Documentos" no app

## Atualização de Documentos

Para atualizar a base de conhecimento, clique no botão "🔄 Recarregar Documentos" na sidebar.

---

Desenvolvido pela IETA Brazil Initiative 🌍
```

---

## Checklist Atualizado

**Arquivos que você deve ter agora:**
```
IETA_Bot/
├── meeting_prep.py          ← ✅ Já tem
├── chunk_documents.py       ← ✅ Criar agora
├── requirements.txt         ← ✅ Já tem
├── README.md               ← ✅ Atualizar
├── .gitignore              ← ✅ Adicionar conteúdo
└── documents/              ← ✅ Pasta

    └── .gitkeep            ← Criar arquivo vazio

