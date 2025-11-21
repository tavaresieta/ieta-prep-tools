"""
Validador de Keywords - IETA Knowledge Base
Permite revisar e editar keywords atribuídas aos documentos

USO:
    python validate_keywords.py              # Modo interativo
    python validate_keywords.py --export     # Exporta CSV para revisar no Excel
    python validate_keywords.py --stats      # Mostra apenas estatísticas
"""

import json
from pathlib import Path
from collections import Counter
import csv

CONFIG = {
    "metadata_file": r"C:\Users\maryb\OneDrive\Desktop\IETA_Tests\IETA_Bot\metadata\keywords_metadata.json",
    "documents_folder": r"C:\Users\maryb\OneDrive\Desktop\IETA_Tests\IETA_Bot\documents"
}

def load_metadata():
    """Carrega metadata de keywords"""
    metadata_file = Path(CONFIG["metadata_file"])
    
    if not metadata_file.exists():
        print("❌ Arquivo de metadata não encontrado!")
        print(f"   Esperado em: {metadata_file}")
        print("\n💡 Execute primeiro: python process_and_sync.py --keywords-only")
        return None
    
    with open(metadata_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_metadata(metadata):
    """Salva metadata atualizada"""
    metadata_file = Path(CONFIG["metadata_file"])
    
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print("\n✅ Metadata atualizada salva!")

def show_statistics(metadata):
    """Mostra estatísticas gerais"""
    print("\n" + "="*70)
    print("📊 ESTATÍSTICAS DE KEYWORDS")
    print("="*70)
    
    # Total de documentos
    total_docs = len(metadata)
    print(f"\n📄 Total de documentos: {total_docs}")
    
    # Documentos sem keywords
    no_keywords = sum(1 for doc in metadata.values() if not doc.get('keywords'))
    if no_keywords > 0:
        print(f"⚠️  Documentos SEM keywords: {no_keywords}")
    
    # Keywords mais usadas
    all_keywords = []
    for doc in metadata.values():
        all_keywords.extend(doc.get('keywords', []))
    
    keyword_counts = Counter(all_keywords)
    
    print(f"\n🏷️  Total de keywords únicas: {len(keyword_counts)}")
    print(f"📊 Total de atribuições: {len(all_keywords)}")
    print(f"📈 Média de keywords por doc: {len(all_keywords)/total_docs:.1f}")
    
    print(f"\n🔥 Top 15 keywords mais usadas:")
    for keyword, count in keyword_counts.most_common(15):
        bar = "█" * min(count, 40)
        print(f"   {keyword:30} {bar} {count}")
    
    # Keywords menos usadas
    rare_keywords = [kw for kw, count in keyword_counts.items() if count == 1]
    if rare_keywords:
        print(f"\n💡 {len(rare_keywords)} keywords aparecem em apenas 1 documento")

def preview_document(doc_id, metadata):
    """Mostra preview do documento"""
    doc_path = Path(CONFIG["documents_folder"]) / metadata[doc_id]['filename']
    
    if doc_path.exists():
        content = doc_path.read_text(encoding='utf-8')
        # Mostra primeiras linhas
        lines = content.split('\n')[:10]
        print("\n📄 Preview do documento:")
        print("─" * 70)
        for line in lines:
            if line.strip():
                print(line[:70])
        print("─" * 70)
        print(f"... ({len(content)} caracteres no total)")
    else:
        print("\n⚠️  Arquivo não encontrado")

def interactive_validation(metadata):
    """Modo interativo de validação"""
    print("\n" + "="*70)
    print("🔍 VALIDADOR INTERATIVO DE KEYWORDS")
    print("="*70)
    print("\nComandos:")
    print("  [número] - Ver documento específico")
    print("  'list'   - Listar todos os documentos")
    print("  'stats'  - Ver estatísticas")
    print("  'search' - Buscar por keyword")
    print("  'edit'   - Editar keywords de um documento")
    print("  'quit'   - Sair")
    
    doc_ids = list(metadata.keys())
    
    while True:
        print("\n" + "─"*70)
        cmd = input("→ Comando: ").strip().lower()
        
        if cmd == 'quit' or cmd == 'q':
            print("\n👋 Até logo!")
            break
        
        elif cmd == 'stats':
            show_statistics(metadata)
        
        elif cmd == 'list':
            print(f"\n📚 {len(doc_ids)} documentos:")
            for i, doc_id in enumerate(doc_ids, 1):
                doc = metadata[doc_id]
                keywords = ', '.join(doc.get('keywords', []))
                print(f"\n  {i}. {doc['filename']}")
                print(f"     🏷️  {keywords}")
        
        elif cmd == 'search':
            keyword = input("     Keyword para buscar: ").strip()
            
            found = []
            for doc_id, doc in metadata.items():
                if keyword in doc.get('keywords', []):
                    found.append((doc_id, doc))
            
            if found:
                print(f"\n✅ {len(found)} documentos com '{keyword}':")
                for i, (doc_id, doc) in enumerate(found, 1):
                    print(f"\n  {i}. {doc['filename']}")
                    print(f"     🏷️  {', '.join(doc['keywords'])}")
            else:
                print(f"\n❌ Nenhum documento com keyword '{keyword}'")
        
        elif cmd == 'edit':
            # Lista documentos com números
            print(f"\n📚 Documentos disponíveis:")
            for i, doc_id in enumerate(doc_ids, 1):
                doc = metadata[doc_id]
                print(f"  {i}. {doc['filename']}")
            
            try:
                doc_num = int(input("\n     Número do documento: "))
                if 1 <= doc_num <= len(doc_ids):
                    doc_id = doc_ids[doc_num - 1]
                    edit_document_keywords(doc_id, metadata)
                else:
                    print("     ❌ Número inválido")
            except ValueError:
                print("     ❌ Digite um número válido")
        
        elif cmd.isdigit():
            doc_num = int(cmd)
            if 1 <= doc_num <= len(doc_ids):
                doc_id = doc_ids[doc_num - 1]
                doc = metadata[doc_id]
                
                print(f"\n📄 Documento #{doc_num}: {doc['filename']}")
                print(f"🏷️  Keywords: {', '.join(doc.get('keywords', []))}")
                print(f"📊 {doc.get('word_count', 0):,} palavras")
                
                preview = input("\n     Ver preview? (s/n): ").lower()
                if preview == 's':
                    preview_document(doc_id, metadata)
                
                edit = input("     Editar keywords? (s/n): ").lower()
                if edit == 's':
                    edit_document_keywords(doc_id, metadata)
            else:
                print("❌ Número inválido")
        
        else:
            print("❌ Comando não reconhecido. Digite 'quit' para sair.")

def edit_document_keywords(doc_id, metadata):
    """Edita keywords de um documento"""
    doc = metadata[doc_id]
    
    print(f"\n📝 Editando: {doc['filename']}")
    print(f"   Keywords atuais: {', '.join(doc.get('keywords', []))}")
    
    print("\n   Opções:")
    print("   1. Adicionar keyword")
    print("   2. Remover keyword")
    print("   3. Substituir todas as keywords")
    print("   4. Cancelar")
    
    choice = input("\n   Escolha (1-4): ").strip()
    
    if choice == '1':
        new_kw = input("   Nova keyword: ").strip()
        if new_kw:
            current_kws = doc.get('keywords', [])
            if new_kw not in current_kws:
                current_kws.append(new_kw)
                doc['keywords'] = current_kws
                print(f"   ✅ '{new_kw}' adicionada")
                save_metadata(metadata)
            else:
                print(f"   ⚠️  '{new_kw}' já existe")
    
    elif choice == '2':
        if doc.get('keywords'):
            print("\n   Keywords atuais:")
            for i, kw in enumerate(doc['keywords'], 1):
                print(f"     {i}. {kw}")
            
            kw_num = input("\n   Número da keyword para remover: ").strip()
            try:
                kw_idx = int(kw_num) - 1
                if 0 <= kw_idx < len(doc['keywords']):
                    removed = doc['keywords'].pop(kw_idx)
                    print(f"   ✅ '{removed}' removida")
                    save_metadata(metadata)
                else:
                    print("   ❌ Número inválido")
            except ValueError:
                print("   ❌ Digite um número")
        else:
            print("   ⚠️  Documento não tem keywords")
    
    elif choice == '3':
        new_kws = input("   Novas keywords (separadas por vírgula): ").strip()
        if new_kws:
            kw_list = [kw.strip() for kw in new_kws.split(',')]
            doc['keywords'] = kw_list
            print(f"   ✅ Keywords atualizadas: {', '.join(kw_list)}")
            save_metadata(metadata)
    
    elif choice == '4':
        print("   ❌ Cancelado")

def export_to_csv(metadata):
    """Exporta para CSV para revisar no Excel"""
    output_file = Path("keywords_validation.csv")
    
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Documento', 'Keyword 1', 'Keyword 2', 'Keyword 3', 'Keyword 4', 'Keyword 5', 'Palavras', 'Caracteres'])
        
        for doc_id, doc in metadata.items():
            keywords = doc.get('keywords', [])
            # Preenche com vazios até ter 5 colunas
            keywords_padded = keywords + [''] * (5 - len(keywords))
            
            writer.writerow([
                doc['filename'],
                *keywords_padded[:5],
                doc.get('word_count', 0),
                doc.get('char_count', 0)
            ])
    
    print(f"\n✅ Exportado para: {output_file.absolute()}")
    print("   Abra no Excel para revisar e editar")
    print("   ⚠️  Após editar no Excel, use o modo interativo para atualizar o JSON")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Valida keywords dos documentos")
    parser.add_argument("--stats", action="store_true", help="Mostra apenas estatísticas")
    parser.add_argument("--export", action="store_true", help="Exporta CSV para Excel")
    
    args = parser.parse_args()
    
    # Carrega metadata
    metadata = load_metadata()
    if not metadata:
        return
    
    # Modos de operação
    if args.stats:
        show_statistics(metadata)
    
    elif args.export:
        show_statistics(metadata)
        export_to_csv(metadata)
    
    else:
        # Modo interativo padrão
        show_statistics(metadata)
        print("\n" + "="*70)
        
        choice = input("\nIniciar validação interativa? (s/n): ").lower()
        if choice == 's':
            interactive_validation(metadata)
        else:
            print("\n💡 Use 'python validate_keywords.py --export' para exportar CSV")

if __name__ == "__main__":
    main()