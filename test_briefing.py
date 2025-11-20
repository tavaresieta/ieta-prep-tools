from pathlib import Path
from PyPDF2 import PdfReader
from docx import Document

# Carregar documentos
docs_folder = Path("documents")
all_text = []

for file_path in docs_folder.iterdir():
    if file_path.suffix == '.pdf':
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        all_text.append(f"=== {file_path.name} ===\n{text[:2000]}")
    elif file_path.suffix == '.txt':
        text = file_path.read_text(encoding='utf-8')
        all_text.append(f"=== {file_path.name} ===\n{text[:2000]}")

docs_context = "\n\n".join(all_text)

# Criar prompt
prompt = f"""
Baseado nestes documentos IETA, crie um briefing para:

REUNIÃO:
- Organização: IBP - Instituto Brasileiro do Petróleo  
- Tópicos: SBCE, CBAM, CBIOs, mercados de carbono

Inclua:
1. Objetivos estratégicos IETA
2. Posições relevantes
3. 5 talking points
4. 3 perguntas prováveis

DOCUMENTOS:
{docs_context[:8000]}
"""

print("PROMPT GERADO:")
print("="*60)
print(prompt)