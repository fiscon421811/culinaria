"""Copia categorias e receitas do banco 'receitas-recuperado' para 'receitaturso'.

Nao altera o banco de origem. Aborta se o destino ja tiver dados
(use --forcar para apagar o destino antes de copiar).
Uso:  python copiar_banco.py [--forcar]
"""
import getpass
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from culinaria import config
from culinaria.turso import TursoClient

DEST_URL = "https://receitaturso-fiscon.aws-us-east-2.turso.io/"
LOTE = 20  # receitas por requisicao


def main() -> None:
    forcar = "--forcar" in sys.argv
    origem = TursoClient(config.TURSO_BASE_URL, config.TURSO_AUTH_TOKEN)
    print("Origem:", config.TURSO_BASE_URL)

    cats = origem.query("SELECT CodCat, Cat FROM categorias ORDER BY CodCat")
    recs = origem.query("SELECT ID, Cod, CodCat, Titulo, Receita, Link FROM receitas ORDER BY ID")
    print(f"Origem: {len(cats)} categorias, {len(recs)} receitas")
    if not recs:
        sys.exit("Origem vazia; nada a copiar.")

    snap = Path(__file__).parent / f"snapshot_origem_{datetime.now():%Y%m%d_%H%M%S}.json"
    snap.write_text(json.dumps({"categorias": cats, "receitas": recs}, ensure_ascii=False), encoding="utf-8")
    print("Copia local salva em:", snap)

    token = os.environ.get("TURSO_DEST_TOKEN") or getpass.getpass(
        "Token (Read & Write) do banco receitaturso (cole com clique direito): "
    )
    token = token.strip().strip('"').strip("'").strip()
    print(f"Token recebido: {len(token)} caracteres, comeca com '{token[:3]}', {token.count('.')} pontos")
    if len(token) < 100 or not token.startswith("eyJ") or token.count(".") != 2:
        sys.exit("Token invalido (um token do Turso tem ~200+ caracteres, comeca com 'eyJ' e tem 2 pontos). Cole de novo.")
    if token == config.TURSO_AUTH_TOKEN:
        sys.exit("Esse e o token do banco RECUPERADO (o mesmo do .env). Gere/cole o token do banco receitaturso.")
    try:
        import base64
        b = token.split(".")[1]
        info = json.loads(base64.urlsafe_b64decode(b + "=" * (-len(b) % 4)))
        exp = info.get("exp")
        print("Token: acesso =", info.get("a"), "| expira =",
              datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M") if exp else "nunca",
              "| criado =", datetime.fromtimestamp(info["iat"]).strftime("%Y-%m-%d %H:%M") if info.get("iat") else "?")
    except Exception:
        pass
    dest = TursoClient(DEST_URL, token)
    try:
        dest.query("SELECT 1 AS ok")
    except Exception as e:
        sys.exit(f"Falha ao conectar no destino {DEST_URL}: {e}")

    for ddl in (
        "CREATE TABLE IF NOT EXISTS categorias (CodCat INTEGER PRIMARY KEY, Cat TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS receitas (ID INTEGER PRIMARY KEY, Cod INTEGER, CodCat INTEGER, Titulo TEXT, Receita TEXT, Link TEXT)",
    ):
        dest.execute(ddl)

    n_cat = int(dest.query("SELECT COUNT(*) AS n FROM categorias")[0]["n"])
    n_rec = int(dest.query("SELECT COUNT(*) AS n FROM receitas")[0]["n"])
    print(f"Destino antes: {n_cat} categorias, {n_rec} receitas")
    if n_cat or n_rec:
        d_cats = dest.query("SELECT CodCat, Cat FROM categorias ORDER BY CodCat")
        d_recs = dest.query("SELECT ID, Cod, CodCat, Titulo, Receita, Link FROM receitas ORDER BY ID")
        dsnap = Path(__file__).parent / f"snapshot_destino_{datetime.now():%Y%m%d_%H%M%S}.json"
        dsnap.write_text(json.dumps({"categorias": d_cats, "receitas": d_recs}, ensure_ascii=False), encoding="utf-8")
        print("Copia local do destino salva em:", dsnap)
        so = {r["ID"]: r for r in recs}
        do = {r["ID"]: r for r in d_recs}
        so_origem = [i for i in so if i not in do]
        so_destino = [i for i in do if i not in so]
        difere = [i for i in so if i in do and so[i] != do[i]]
        print(f"So na origem: {len(so_origem)} | So no destino: {len(so_destino)} | IDs com conteudo diferente: {len(difere)}")
        for i in so_destino:
            print(f"  [so no destino] ID {i}: {do[i]['Titulo']}")
        for i in difere[:10]:
            print(f"  [diferente] ID {i}: origem='{so[i]['Titulo']}' destino='{do[i]['Titulo']}'")
        if "--mesclar" in sys.argv:
            # Conflito de ID: mantem a receita do destino e reinsere a da origem com ID/Cod novos.
            titulos_dest = {r["Titulo"] for r in d_recs}
            for i in difere:
                r = so[i]
                if r["Titulo"] in titulos_dest:
                    print(f"  ja existe no destino com outro ID, ignorando: {r['Titulo']}")
                    continue
                max_cod = int(dest.query("SELECT COALESCE(MAX(Cod), 0) AS m FROM receitas")[0]["m"])
                dest.execute(
                    "INSERT INTO receitas (Cod, CodCat, Titulo, Receita, Link) VALUES (?, ?, ?, ?, ?)",
                    [max_cod + 1, r["CodCat"], r["Titulo"], r["Receita"], r["Link"]],
                )
                print(f"  reinserida com novo Cod {max_cod + 1}: {r['Titulo']}")
            faltam_cat = [c for c in cats if c["CodCat"] not in {x["CodCat"] for x in d_cats}]
            if faltam_cat:
                dest.batch([("INSERT INTO categorias (CodCat, Cat) VALUES (?, ?)", [c["CodCat"], c["Cat"]]) for c in faltam_cat], transacao=True)
            for k in range(0, len(so_origem), LOTE):
                dest.batch([("INSERT INTO receitas (ID, Cod, CodCat, Titulo, Receita, Link) VALUES (?, ?, ?, ?, ?, ?)",
                             [so[i]["ID"], so[i]["Cod"], so[i]["CodCat"], so[i]["Titulo"], so[i]["Receita"], so[i]["Link"]])
                            for i in so_origem[k:k+LOTE]], transacao=True)
            f_rec = int(dest.query("SELECT COUNT(*) AS n FROM receitas")[0]["n"])
            print(f"Mesclagem concluida. Destino agora: {f_rec} receitas (esperado {len(set(so)|set(do))} (+ conflitos reinseridos)).")
            return
        if not forcar:
            print("Nada foi alterado. Use --mesclar para acrescentar so o que falta (recomendado).")
            sys.exit(0)
        dest.batch([("DELETE FROM receitas", None), ("DELETE FROM categorias", None)], transacao=True)

    dest.batch(
        [("INSERT INTO categorias (CodCat, Cat) VALUES (?, ?)", [c["CodCat"], c["Cat"]]) for c in cats],
        transacao=True,
    )
    for i in range(0, len(recs), LOTE):
        parte = recs[i : i + LOTE]
        dest.batch(
            [
                (
                    "INSERT INTO receitas (ID, Cod, CodCat, Titulo, Receita, Link) VALUES (?, ?, ?, ?, ?, ?)",
                    [r["ID"], r["Cod"], r["CodCat"], r["Titulo"], r["Receita"], r["Link"]],
                )
                for r in parte
            ],
            transacao=True,
        )
        print(f"  copiadas {min(i + LOTE, len(recs))}/{len(recs)}")

    d_cat = int(dest.query("SELECT COUNT(*) AS n FROM categorias")[0]["n"])
    d_rec = int(dest.query("SELECT COUNT(*) AS n FROM receitas")[0]["n"])
    ok = d_cat == len(cats) and d_rec == len(recs)
    print(f"Destino depois: {d_cat} categorias, {d_rec} receitas ->", "OK" if ok else "DIVERGENTE!")


if __name__ == "__main__":
    main()
