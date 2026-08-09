"""Local stand-ins for the platform data tools the Agent would normally call.

  profile   -> profile_data: per-column type, null rate, distinct count,
               min/max, and top-N value frequencies. Feeds R6 and M5.
  joinev    -> the six numbers section 9 requires to validate a declared join:
               left rows, matched, unmatched, joined rows, distinct join keys
               before and after, and max matches per left key.

Both are deliberately dumb: they measure and print. No judgment, no thresholds.
Usage:
  python3 tools/dq.py profile  <db> <relation> [--cols a,b,c] [--top 10] [--where SQL]
  python3 tools/dq.py joinev   <db> <left> <right> <left_key> <right_key> [--where SQL]
  python3 tools/dq.py sql      <db> "<query>"
"""

import argparse
import duckdb


def _con(db):
    return duckdb.connect(db, read_only=True)


def _fmt(v, w=14):
    if isinstance(v, int):
        return f"{v:>{w},}"
    if isinstance(v, float):
        return f"{v:>{w},.4f}"
    s = "NULL" if v is None else str(v)
    return f"{s:>{w}}"[:w] if len(s) > w else f"{s:>{w}}"


def profile(db, relation, cols=None, top=10, where=None):
    con = _con(db)
    pred = f"WHERE {where}" if where else ""
    src = f"(SELECT * FROM {relation} {pred})"
    total = con.execute(f"SELECT count(*) FROM {src} t").fetchone()[0]
    schema = con.execute(f"DESCRIBE SELECT * FROM {src} t").fetchall()
    names = [r[0] for r in schema]
    types = dict((r[0], r[1]) for r in schema)
    if cols:
        names = [c for c in cols if c in types]

    print(f"\n=== profile: {relation} {('WHERE ' + where) if where else ''}")
    print(f"rows: {total:,}\n")
    hdr = f"{'column':30} {'type':12} {'nulls%':>8} {'distinct':>12} {'min':>22} {'max':>22}"
    print(hdr)
    print("-" * len(hdr))
    for c in names:
        q = f'''SELECT count(*) - count("{c}"), count(DISTINCT "{c}"),
                       min("{c}")::VARCHAR, max("{c}")::VARCHAR FROM {src} t'''
        try:
            nulls, ndv, mn, mx = con.execute(q).fetchone()
        except Exception as e:
            print(f"{c:30} {types[c][:12]:12} {'-':>8} {'-':>12}  {type(e).__name__}")
            continue
        pct = (nulls / total * 100) if total else 0
        print(
            f"{c:30} {types[c][:12]:12} {pct:>8.2f} {ndv:>12,} "
            f"{(mn or 'NULL')[:22]:>22} {(mx or 'NULL')[:22]:>22}"
        )

    if top:
        for c in names:
            if types[c] in ("TIMESTAMP", "DATE") or "trip_key" in c:
                continue
            try:
                rows = con.execute(
                    f'''SELECT "{c}"::VARCHAR v, count(*) n FROM {src} t
                        GROUP BY 1 ORDER BY n DESC LIMIT {top}'''
                ).fetchall()
            except Exception:
                continue
            if len(rows) <= 1 or len(rows) >= top:
                if len(rows) < top:
                    continue
            print(f"\n  top {top} :: {c}")
            for v, n in rows:
                print(f"    {str(v)[:40]:40} {n:>14,}  {n/total*100:>6.2f}%")
    con.close()


def joinev(db, left, right, lkey, rkey, where=None):
    con = _con(db)
    pred = f"WHERE {where}" if where else ""
    L = f"(SELECT * FROM {left} {pred})"
    q = f"""
    WITH l AS (SELECT * FROM {L} x), r AS (SELECT * FROM {right} y)
    SELECT
      (SELECT count(*) FROM l)                                        AS left_rows,
      (SELECT count(*) FROM l WHERE {lkey} IS NULL)                   AS left_null_key,
      (SELECT count(DISTINCT {lkey}) FROM l)                          AS left_distinct_keys,
      (SELECT count(*) FROM l JOIN r ON l.{lkey} = r.{rkey})          AS joined_rows,
      (SELECT count(*) FROM l WHERE {lkey} IN (SELECT {rkey} FROM r)) AS matched_rows,
      (SELECT count(*) FROM l WHERE {lkey} NOT IN (SELECT {rkey} FROM r WHERE {rkey} IS NOT NULL)
                              OR {lkey} IS NULL)                      AS unmatched_rows,
      (SELECT count(DISTINCT l.{lkey}) FROM l JOIN r ON l.{lkey} = r.{rkey}) AS distinct_keys_after,
      (SELECT max(c) FROM (SELECT {rkey} k, count(*) c FROM r GROUP BY 1)) AS max_matches_per_left_key,
      (SELECT count(*) FROM r)                                        AS right_rows,
      (SELECT count(DISTINCT {rkey}) FROM r)                          AS right_distinct_keys
    """
    row = con.execute(q).fetchone()
    labels = [
        "left rows", "  of which null key", "left distinct keys",
        "joined rows (result)", "matched left rows", "unmatched left rows",
        "distinct keys after join", "max matches per left key",
        "right rows", "right distinct keys",
    ]
    print(f"\n=== join evidence: {left} -> {right}  ON {lkey} = {rkey}")
    if where:
        print(f"    left filtered: {where}")
    print()
    for lab, v in zip(labels, row):
        print(f"  {lab:28} {v:>14,}")
    lr, _, _, jr, mr, ur = row[0], row[1], row[2], row[3], row[4], row[5]
    print()
    print(f"  row multiplication      {jr/lr if lr else 0:>14.6f}  (1.0 = no fanout)")
    print(f"  unmatched rate          {ur/lr*100 if lr else 0:>14.4f} %")
    con.close()


def run_sql(db, q):
    con = _con(db)
    cur = con.execute(q)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    w = [max(len(c), 16) for c in cols]
    print("  ".join(c.ljust(w[i]) for i, c in enumerate(cols)))
    print("  ".join("-" * w[i] for i in range(len(cols))))
    for r in rows:
        print("  ".join(_fmt(v, w[i]).strip().ljust(w[i]) for i, v in enumerate(r)))
    print(f"\n({len(rows)} rows)")
    con.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("profile")
    a.add_argument("db"); a.add_argument("relation")
    a.add_argument("--cols"); a.add_argument("--top", type=int, default=10)
    a.add_argument("--where")
    b = sub.add_parser("joinev")
    b.add_argument("db"); b.add_argument("left"); b.add_argument("right")
    b.add_argument("left_key"); b.add_argument("right_key"); b.add_argument("--where")
    c = sub.add_parser("sql")
    c.add_argument("db"); c.add_argument("query")
    n = p.parse_args()
    if n.cmd == "profile":
        profile(n.db, n.relation, n.cols.split(",") if n.cols else None, n.top, n.where)
    elif n.cmd == "joinev":
        joinev(n.db, n.left, n.right, n.left_key, n.right_key, n.where)
    else:
        run_sql(n.db, n.query)
