"""Regression tests for base.txt write integrity (v39).

Run:  .venv/bin/python tests/test_base_txt_integrity.py
"""
import json, os, sys, tempfile, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FAILS = []

def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"   {detail}" if detail and not cond else ""))
    if not cond:
        FAILS.append(name)

def fresh(tmp):
    p = tmp / "base.txt"
    p.write_text(json.dumps({
        "default_stb": "found1",
        "operator_note": "do not delete me",
        "stbs": {
            "found1": {"alias": "found1", "stb": "R1956409151-66", "ip": "10.73.185.34",
                       "protocol": "SGS", "remote": "14", "com_port": "/dev/ttyACM0",
                       "role": "hopper", "host": "found1",
                       "lname": "pairedUser", "passwd": "pairedSecret", "prod": True},
            "joey1": {"alias": "joey1", "role": "joey", "host": "found1", "ip": "10.73.185.35"},
        },
    }, indent=4))
    return p

def load(p):
    return json.loads(p.read_text())

def main():
    from jamboree import base_io
    from jamboree.stb_store import STBStore

    tmp = Path(tempfile.mkdtemp(prefix="base_integrity_"))
    try:
        # ---- T1: the exact call ip_recovery makes must not destroy anything
        print("T1  save({'stbs': ...}) is additive (the old destructive path)")
        p = fresh(tmp); st = STBStore(p)
        stbs = dict(st.all()); stbs["found1"] = dict(stbs["found1"]); stbs["found1"]["ip"] = "10.79.85.200"
        st.save({"stbs": stbs})
        d = load(p)
        check("T1.1 top-level default_stb survives", d.get("default_stb") == "found1")
        check("T1.2 top-level operator_note survives", d.get("operator_note") == "do not delete me")
        check("T1.3 new ip applied", d["stbs"]["found1"]["ip"] == "10.79.85.200")
        check("T1.4 credentials survive", d["stbs"]["found1"].get("passwd") == "pairedSecret")
        check("T1.5 sibling alias joey1 survives", "joey1" in d["stbs"])

        # ---- T2: targeted field update
        print("T2  update_stb() touches only named fields")
        p = fresh(tmp); st = STBStore(p)
        st.update_stb("found1", {"ip": "10.79.85.201"})
        d = load(p)
        before = load(fresh(tmp)) if False else None
        check("T2.1 ip updated", d["stbs"]["found1"]["ip"] == "10.79.85.201")
        check("T2.2 com_port intact", d["stbs"]["found1"]["com_port"] == "/dev/ttyACM0")
        check("T2.3 creds intact", d["stbs"]["found1"]["lname"] == "pairedUser")
        check("T2.4 top-level intact", d.get("operator_note") == "do not delete me")

        # ---- T3: credentials are additive and survive later IP writes
        print("T3  credentials persist across subsequent writes")
        p = fresh(tmp); st = STBStore(p)
        st.set_credentials("found1", "newLogin", "newSecret", paired_ts="2026-08-03T10:00:00")
        st.update_stb("found1", {"ip": "10.79.85.202"})
        st.save({"stbs": {"found1": {"model": "Hopper3"}}})
        d = load(p)
        check("T3.1 lname persisted", d["stbs"]["found1"]["lname"] == "newLogin")
        check("T3.2 passwd persisted", d["stbs"]["found1"]["passwd"] == "newSecret")
        check("T3.3 paired_ts persisted", d["stbs"]["found1"]["paired_ts"] == "2026-08-03T10:00:00")
        check("T3.4 prod flag set", d["stbs"]["found1"]["prod"] is True)
        check("T3.5 model added", d["stbs"]["found1"]["model"] == "Hopper3")
        check("T3.6 ip retained", d["stbs"]["found1"]["ip"] == "10.79.85.202")

        # ---- T4: settops-style bulk replace may delete, must protect creds
        print("T4  replace_stbs() allows deletion but protects credentials")
        p = fresh(tmp); st = STBStore(p)
        # UI posts a table with joey1 removed and no credential fields at all
        st.replace_stbs({"found1": {"alias": "found1", "ip": "10.79.85.203", "protocol": "SGS"}})
        d = load(p)
        check("T4.1 joey1 deleted as requested", "joey1" not in d["stbs"])
        check("T4.2 creds protected from UI blanking", d["stbs"]["found1"].get("passwd") == "pairedSecret")
        check("T4.3 com_port protected", d["stbs"]["found1"].get("com_port") == "/dev/ttyACM0")
        check("T4.4 ip applied", d["stbs"]["found1"]["ip"] == "10.79.85.203")
        check("T4.5 top-level intact", d.get("default_stb") == "found1")

        # ---- T5: explicit deletion still possible
        print("T5  remove() deletes explicitly")
        p = fresh(tmp); st = STBStore(p)
        st.remove(["joey1"])
        d = load(p)
        check("T5.1 joey1 gone", "joey1" not in d["stbs"])
        check("T5.2 found1 stays", "found1" in d["stbs"])

        # ---- T6: atomic write + .bak snapshot
        print("T6  writes are atomic and leave a .bak")
        p = fresh(tmp); st = STBStore(p)
        st.update_stb("found1", {"ip": "10.0.0.9"})
        check("T6.1 .bak created", Path(str(p) + ".bak").is_file())
        check("T6.2 no stray .tmp files", not list(p.parent.glob("base.txt.*.tmp")))
        check("T6.3 file is valid json", isinstance(load(p), dict))

        # ---- T7: corrupt primary falls back to .bak instead of losing config
        print("T7  corrupt base.txt recovers from .bak")
        p = fresh(tmp); st = STBStore(p)
        st.update_stb("found1", {"ip": "10.0.0.10"})     # creates .bak
        p.write_text("{ this is not json")
        rec = base_io.read_document(p)
        check("T7.1 recovered a document", bool(rec.get("stbs")))
        check("T7.2 recovered creds", rec["stbs"]["found1"].get("passwd") == "pairedSecret")

        # ---- T8: deep_merge never drops keys
        print("T8  deep_merge semantics")
        a = {"x": 1, "n": {"p": 1, "q": 2}}
        base_io.deep_merge(a, {"n": {"q": 9, "r": 3}, "y": 2})
        check("T8.1 untouched scalar kept", a["x"] == 1)
        check("T8.2 nested untouched kept", a["n"]["p"] == 1)
        check("T8.3 nested overwritten", a["n"]["q"] == 9)
        check("T8.4 nested added", a["n"]["r"] == 3)
        check("T8.5 top added", a["y"] == 2)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILS:
        print(f"RESULT: {len(FAILS)} FAILURE(S): {FAILS}")
        sys.exit(1)
    print("RESULT: ALL base.txt INTEGRITY TESTS PASSED")

if __name__ == "__main__":
    main()
