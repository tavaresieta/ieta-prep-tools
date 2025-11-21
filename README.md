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

## Configuração da API Key (Anthropic)

Para usar funcionalidades que requerem a API da Anthropic (ex: `process_and_sync.py --keywords-only`):

### No Streamlit Cloud:
1. Acesse as configurações do app no Streamlit Cloud
2. Vá em "Secrets" ou "Environment variables"
3. Adicione: `ANTHROPIC_API_KEY` = `sua-chave-aqui`
4. O app irá usar automaticamente

### Para desenvolvimento local:
**Opção 1 - Variável de ambiente (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY = "sua-chave-aqui"
```

**Opção 2 - Variável de ambiente permanente:**
```powershell
setx ANTHROPIC_API_KEY "sua-chave-aqui"
```
(Reinicie o terminal após usar `setx`)

**Opção 3 - Arquivo .env (local apenas):**
1. Crie um arquivo `.env` na raiz do projeto
2. Adicione: `ANTHROPIC_API_KEY=sua-chave-aqui`
3. O arquivo `.env` já está no `.gitignore` (não será commitado)

---

Desenvolvido pela IETA Brazil Initiative 🌍
```




