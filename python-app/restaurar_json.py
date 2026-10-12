"""Restaura um arquivo .json (backup do app ou snapshot) no banco 'receitaturso'.

Uso:
  python restaurar_json.py ARQUIVO.json              -> so compara (nao altera nada)
  python restaurar_json.py ARQUIVO.json --mesclar    -> acrescenta o que falta, mantem o que ja existe
  python restaurar_json.py ARQUIVO.json --substituir -> apaga o destino e restaura exatamente o arquivo
Antes de qualquer alteracao salva uma copia local do destino (snapshot_destino_*.json).
O token vem da variavel TURSO_DEST_TOKEN ou e pedido na tela.
"""
import getpass
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from culinaria.turso import TursoClient

DEST_URL = "https://receitaturso-fiscon.aws-us-east-2.turso.io/"
LOTE = 20
INS = "INSERT INTO receitas (ID, Cod, CodCat, Titulo, Receita, Link) VALUES (?, ?, ?, ?, ?, ?)"
INS_NOVO = "INSERT INTO receitas (Cod, CodCat, Titulo, Receita, Link) VALUES (?, ?, ?, ?, ?)"


def ler_arquivo(caminho: Path):
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if not isinstance(dados, dict) or "receitas" not in dados:
        sys.exit("Arquivo invalido: nao tem a chave 'receitas'.")
    cats = [{"CodCat": c["CodCat"], "Cat": c["Cat"]} for c in dados.get("categorias") or []]
    recs = [{k: r.get(k) for k in ("ID", "Cod", "CodCat", "Titulo", "Receita", "Link")} for r in dados["receitas"]]
    return cats, recs


def n(dest, tabela):
    return int(dest.query(f"SELECT COUNT(*) AS n FROM {tabela}")[0]["n"])


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    arq = Path(args[0])
    mesclar, substituir = "--mesclar" in sys.argv, "--substituir" in sys.argv
    cats, recs = ler_arquivo(arq)
    print(f"Arquivo: {arq.name} -> {len(cats)} categorias, {len(recs)} receitas")
    if any(r["ID"] is None for r in recs):
        sys.exit("Ha receitas sem ID no arquivo; abortado.")

    token = os.environ.get("TURSO_DEST_TOKEN") or getpass.getpass("Token (Read & Write) do receitaturso: ")
    token = token.strip().strip('"').strip("'").strip()
    print(f"Token recebido: {len(token)} caracteres")
    dest = TursoClient(DEST_URL, token)
    try:
        dest.query("SELECT 1 AS ok")
    except Exception as e:
        sys.exit(f"Falha ao conectar em {DEST_URL}: {e}")

    dest.execute("CREATE TABLE IF NOT EXISTS categorias (CodCat INTEGER PRIMARY KEY, Cat TEXT NOT NULL)")
    dest.execute("CREATE TABLE IF NOT EXISTS receitas (ID INTEGER PRIMARY KEY, Cod INTEGER, CodCat INTEGER, Titulo TEXT, Receita TEXT, Link TEXT)")

    d_cats = dest.query("SELECT CodCat, Cat FROM categorias ORDER BY CodCat")
    d_recs = dest.query("SELECT ID, Cod, CodCat, Titulo, Receita, Link FROM receitas ORDER BY ID")
    print(f"Destino atual: {len(d_cats)} categorias, {len(d_recs)} receitas")
    if d_recs:
        snap = Path(__file__).parent / f"snapshot_destino_{datetime.now():%Y%m%d_%H%M%S}.json"
        snap.write_text(json.dumps({"categorias": d_cats, "receitas": d_recs}, ensure_ascii=False), encoding="utf-8")
        print("Copia local do destino salva em:", snap.name)

    so, do = {r["ID"]: r for r in recs}, {r["ID"]: r for r in d_recs}
    faltam = [i for i in so if i not in do]
    difere = [i for i in so if i in do and so[i] != do[i]]
    so_dest = [i for i in do if i not in so]
    print(f"So no arquivo: {len(faltam)} | So no destino: {len(so_dest)} | Mesmo ID com conteudo diferente: {len(difere)}")
    for i in so_dest[:15]:
        print(f"  [so no destino] ID {i}: {do[i]['Titulo']}")
    for i in difere[:15]:
        print(f"  [diferente] ID {i}: arquivo='{so[i]['Titulo']}' destino='{do[i]['Titulo']}'")

    if not (mesclar or substituir):
        print("\nNada foi alterado. Use --mesclar (recomendado) ou --substituir.")
        return

    if substituir:
        if input(f"CONFIRMA apagar {len(d_recs)} receitas do destino e restaurar o arquivo? (digite SIM): ").strip() != "SIM":
            sys.exit("Cancelado.")
        dest.batch([("DELETE FROM receitas", None), ("DELETE FROM categorias", None)], transacao=True)
        d_cats, do, difere = [], {}, []
        faltam = list(so)

    codcats = {c["CodCat"] for c in d_cats}
    novas = [c for c in cats if c["CodCat"] not in codcats]
    if novas:
        dest.batch([("INSERT INTO categorias (CodCat, Cat) VALUES (?, ?)", [c["CodCat"], c["Cat"]]) for c in novas], transacao=True)

    for k in range(0, len(faltam), LOTE):
        dest.batch([(INS, [so[i][c] for c in ("ID", "Cod", "CodCat", "Titulo", "Receita", "Link")]) for i in faltam[k:k + LOTE]], transacao=True)
        print(f"  restauradas {min(k + LOTE, len(faltam))}/{len(faltam)}")

    titulos = {r["Titulo"] for r in d_recs}
    for i in difere:  # so ocorre no --mesclar: mantem o destino e reinsere o do arquivo com ID/Cod novos
        r = so[i]
        if r["Titulo"] in titulos:
            print(f"  ja existe com outro ID, ignorada: {r['Titulo']}")
            continue
        m = int(dest.query("SELECT COALESCE(MAX(Cod), 0) AS m FROM receitas")[0]["m"])
        dest.execute(INS_NOVO, [m + 1, r["CodCat"], r["Titulo"], r["Receita"], r["Link"]])
        print(f"  reinserida com novo Cod {m + 1}: {r['Titulo']}")

    print(f"Destino agora: {n(dest, 'categorias')} categorias, {n(dest, 'receitas')} receitas")


if __name__ == "__main__":
    main()
