# Culinária — versão Python (PySide6)

Porta desktop do app Android **CulinariaTurso**. Mesma base de dados Turso, mesmos
endpoints de IA, mesmo fluxo de telas — agora como aplicativo de janela em Python.

## Rodar

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
python main.py
```

Opcional: copie `.env.example` para `.env` para sobrescrever URLs, token ou a pasta
dos PDFs. Sem `.env`, os padrões de `culinaria/config.py` (os mesmos do app Android)
já funcionam.

## Telas

| Aba | Equivale a | O que faz |
|---|---|---|
| 📖 Receitas | `ReceitasFragment` | Busca por título/ingrediente (sem acento), filtros por categoria, detalhe em diálogo, PDF da lista |
| 🗓️ Cardápio | `CardapioSemanalFragment` | Cardápio da estação (Hemisfério Sul) + 5 cardápios alternativos; gera a receita completa via IA e importa |
| ➕ Nova | `NovaReceitaFragment` | Cadastro manual, importar de link com IA, buscar receitas em vídeo |
| ✏️ Editar | `EditarFragment` | Busca por nº ou texto, editar, trocar categoria, deletar, abrir link, PDF |
| 🏷️ Categorias | `CategoriasFragment` | Listar, adicionar, renomear e excluir categorias |
| 💾 Backup | *(novo — não existe no Android)* | Exportar em JSON ou SQLite e restaurar substituindo tudo |

## Mapa Kotlin → Python

| Android | Python |
|---|---|
| `TursoClient` + `TursoApiService` + `TursoModels` | `culinaria/turso.py` |
| `ReceitaRepository` + `AppRepository` | `culinaria/repository.py` |
| `AppViewModel` (LiveData) | `culinaria/viewmodel.py` (Qt Signals) |
| `RecipeAiService` / `RecipeAiClient` | `culinaria/ai.py` |
| `CardapioSemanalFragment` (dados) + `BrazilianSeason` + `MealPlannerStore` | `culinaria/planner.py` |
| `PrintHelper` (PdfDocument) | `culinaria/pdf.py` (reportlab) |
| `viewModelScope` + `Dispatchers.IO` | `culinaria/tasks.py` (QThreadPool) |
| `MainActivity` + `bottom_navigation` | `culinaria/ui/main_window.py` (QTabWidget) |
| `res/values/colors.xml` + temas | `culinaria/ui/style.py` (QSS) |

## Diferenças propositais em relação ao Android

- **Categorias agora persistem.** No app Kotlin, `insertCategoria`/`updateCategoria`/
  `deleteCategoria` só mexiam no cache em memória — as mudanças se perdiam ao reabrir.
  Aqui vão para a tabela `categorias` no Turso. A exclusão é bloqueada quando a
  categoria tem receitas, para não deixar receitas órfãs.
- **Editar permite trocar a categoria.** O `EditarFragment` mostrava `CodCat` como
  texto fixo, embora o `UPDATE` já enviasse o campo; virou um combo.
- **`getMaxCod` vem do banco** (`SELECT MAX(Cod)`) em vez do cache, evitando número
  duplicado se o app Android inserir em paralelo.
- **PDF**: gerado com reportlab e aberto no visualizador padrão do sistema. Emojis
  não existem nas fontes base do PDF, então `🔗` sai como `Link:`.
- **Cardápio escolhido é lembrado** entre execuções, em `~/.culinaria/meal_planner.json`.

## Backup e restauração

Aba **💾 Backup**. Um backup contém receitas, categorias e o cardápio escolhido.

**Exportar** — JSON (`.json`) ou SQLite (`.db`), à sua escolha; os dois guardam
exatamente o mesmo conteúdo. O JSON tem cabeçalho com data, origem e totais:

```json
{
  "app": "Culinaria", "versao_backup": 1,
  "gerado_em": "2026-08-17T12:05:00-03:00",
  "origem": "https://receitaturso-fiscon.aws-us-east-2.turso.io",
  "totais": { "categorias": 4, "receitas": 132 },
  "categorias": [ { "CodCat": 1, "Cat": "Bolos" } ],
  "receitas":   [ { "ID": 1, "Cod": 1, "CodCat": 1, "Titulo": "…", "Receita": "…", "Link": null } ],
  "cardapio":   { "menu": "Vegano", "meals": {} }
}
```

O `.db` tem as mesmas tabelas `categorias` e `receitas` do Turso, mais uma
`backup_meta` com data, origem e o cardápio — abre em qualquer cliente SQLite.

**Restaurar** — substitui tudo: apaga receitas e categorias do Turso e grava o
arquivo. As proteções:

1. O formato é detectado pelo **conteúdo**, não pela extensão — um `.db`
   renomeado para `.json` é lido corretamente, e um arquivo corrompido é
   recusado com mensagem explicando o que está errado.
2. Uma tela de prévia mostra data, totais, amostra das receitas e avisos
   (categorias órfãs, `Cod` repetido, versão de backup mais nova que o app).
3. Segunda confirmação: você digita `SUBSTITUIR`.
4. Antes de apagar qualquer coisa, o app exporta o estado atual para
   `antes-de-restaurar-<data>.json` na pasta de backups.
5. O envio vai numa **única requisição com `BEGIN`/`COMMIT`** — como o pipeline
   do Turso roda tudo na mesma conexão, uma falha de rede no meio dá rollback e
   o banco fica intacto. Backups grandes (acima de ~700 KB de payload) são
   divididos em lotes e perdem essa atomicidade; nesse caso o resumo final avisa,
   e o backup do passo 4 é a rede de segurança.

Categorias citadas por receitas mas ausentes do arquivo são criadas
automaticamente como `Categoria <n>`, para nenhuma receita ficar órfã.

## Onde ficam os arquivos

- PDFs: `~/Documentos/Receitas/` (configurável via `PDF_DIR`)
- Backups: `~/Documentos/Receitas/backups/` (configurável via `BACKUP_DIR`)
- Estado do cardápio: `~/.culinaria/meal_planner.json`

## Observação de segurança

O token do Turso está com valor padrão no código, como estava no `TursoClient.kt`.
Para não versionar credencial, deixe-o só no `.env` e apague o valor de
`culinaria/config.py`.
