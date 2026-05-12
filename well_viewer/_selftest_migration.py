"""Self-test for the saved-selections v1→v2 migration (Phase 8.0, Stage A).

Run::

    python well_viewer/_selftest_migration.py

GUI-free. Prints ``[PASS]`` / ``[FAIL]`` per case and ``ALL PASS`` / ``SOME FAILED``;
exits 0 iff every case passes (so it can gate CI / a pre-commit hook). Covers the
``design/SELECTIONS_MIGRATION.md`` test plan T1–T5, T7 (backup/recovery), T8
(failure handling). T6 (real saved data) is the user's manual check.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from well_viewer import selections_model as M  # noqa: E402

_PALETTE = ["#111111", "#222222", "#333333", "#444444", "#555555",
            "#666666", "#777777", "#888888", "#999999", "#AAAAAA"]


def _counter_factory():
    n = [0]

    def _f():
        n[0] += 1
        return f"id{n[0]:03d}"
    return _f


def _ok(cond, msg, fails):
    if not cond:
        fails.append(msg)
    return cond


# ────────────────────────────────────────────────────────────────── T1 ──
def t1_clean(fails):
    block = {
        "well_labels": {"A01": "Ctrl", "Z99": "  ", "B05": "Solo"},
        "notes": "hello",
        "rep_sets": [
            {"name": "Rep 1", "wells": ["A1", "A02", "A03"]},
            {"name": "Rep 2", "wells": ["B01", "B02", "B03"]},
            {"name": "Free A", "wells": ["c1", "C02"]},
        ],
        "groups": [
            {"name": "Control", "hidden": False, "members": ["Rep 1"], "solo_wells": ["B05"]},
            {"name": "Drug A", "hidden": True, "members": ["Rep 2"], "solo_wells": []},
        ],
    }
    sels, cur = M.migrate_v1(block, bar_active_grp=0, palette=_PALETTE,
                             id_factory=_counter_factory())
    _ok(len(sels) == 3, f"T1: expected 3 selections, got {len(sels)}", fails)
    _ok([s["source"] for s in sels] == ["bar_group", "bar_group", "rep_set"],
        f"T1: sources/order wrong: {[s['source'] for s in sels]}", fails)
    _ok([s["name"] for s in sels] == ["Control", "Drug A", "Free A"],
        f"T1: names: {[s['name'] for s in sels]}", fails)
    _ok(sels[0]["wells"] == ["A01", "A02", "A03", "B05"],
        f"T1: group wells/normalisation: {sels[0]['wells']}", fails)
    _ok(sels[0]["replicates"] == [["A01", "A02", "A03"], ["B05"]],
        f"T1: group replicates: {sels[0]['replicates']}", fails)
    _ok(sels[1]["hidden"] is True and sels[0]["hidden"] is False,
        "T1: hidden flags wrong", fails)
    _ok(sels[2]["replicates"] == [["C01", "C02"]],
        f"T1: free rep-set replicates should be [wells]: {sels[2]['replicates']}", fails)
    # colours = rank colour of the lowest well (A01 rank 0, B01 rank 12, C01 rank 24)
    _ok(sels[0]["color"] == _PALETTE[0], f"T1: colour[0]={sels[0]['color']}", fails)
    _ok(sels[1]["color"] == _PALETTE[12 % len(_PALETTE)], f"T1: colour[1]={sels[1]['color']}", fails)
    _ok(sels[2]["color"] == _PALETTE[24 % len(_PALETTE)], f"T1: colour[2]={sels[2]['color']}", fails)
    _ok(all(len(s["id"]) >= 1 for s in sels) and len({s["id"] for s in sels}) == 3,
        "T1: ids not unique", fails)
    _ok(cur == sels[0]["id"], f"T1: current should be group 0: {cur}", fails)
    # full block round-trip
    blk = M.to_block(sels, block["well_labels"], block["notes"], cur)
    _ok(blk["schema_version"] == 2 and "rep_sets" not in blk and "groups" not in blk,
        "T1: to_block shape wrong", fails)
    _ok(blk["well_labels"] == {"A01": "Ctrl", "B05": "Solo"},
        f"T1: well_labels filtered wrong: {blk['well_labels']}", fails)
    back, back_cur, back_lbl, back_notes = M.from_block(blk)
    _ok(back == M.validate_repair(sels) and back_cur == cur and back_notes == "hello"
        and back_lbl == {"A01": "Ctrl", "B05": "Solo"},
        "T1: block round-trip not stable", fails)
    # inverse map sanity
    rs, bg, ari, bag, rh = M.selections_to_legacy(sels, cur)
    _ok(len(bg) == 2 and bag == 0 and ari == -1 and rh == set(),
        f"T1: inverse map: bg={len(bg)} bag={bag} ari={ari} rh={rh}", fails)
    # Control: members "Control #1" (Rep1) + "Control #2" (solo B05); Drug A: "Drug A #1"; free "Free A" → 4
    _ok(len(rs) == 4 and [r.name for r in rs] == ["Control #1", "Control #2", "Drug A #1", "Free A"],
        f"T1: inverse rep_sets: {[r.name for r in rs]}", fails)
    _ok([r.name for r in bg[0].members] == ["Control #1", "Control #2"],
        f"T1: derived group members: {[r.name for r in bg[0].members]}", fails)


# ────────────────────────────────────────────────────────────────── T2 ──
def t2_conflicts(fails):
    block = {
        "rep_sets": [
            {"name": "Control_v2", "wells": ["D01"]},   # already literally taken-ish
            {"name": "Control", "wells": ["E01"]},
        ],
        "groups": [
            {"name": "Control", "members": [], "solo_wells": ["A01"]},
            {"name": "Control", "members": [], "solo_wells": ["A02"]},
        ],
    }
    sels, _cur = M.migrate_v1(block, bar_active_grp=-1, palette=_PALETTE,
                              id_factory=_counter_factory())
    names = [s["name"] for s in sels]
    # groups first → "Control", then "Control"→"Control_v2".
    # free rep-sets next (rep_sets list order): the literal "Control_v2" → taken →
    # "Control_v2"+"_v2" = "Control_v2_v2"; then "Control" → "Control_v2" taken →
    # "Control_v2 2". (Matches SavedSelectionsList._unique_name's append-"_v2"-then-
    # "<base> N" rule exactly.)
    _ok(names == ["Control", "Control_v2", "Control_v2_v2", "Control_v2 2"],
        f"T2: name resolution sequence: {names}", fails)
    # also: a name already ending in _v2 with no further collisions stays put
    s2, _c = M.migrate_v1({"rep_sets": [{"name": "X", "wells": ["A01"]},
                                        {"name": "X_v2", "wells": ["A02"]}], "groups": []},
                          id_factory=_counter_factory())
    _ok([s["name"] for s in s2] == ["X", "X_v2"], f"T2b: {[s['name'] for s in s2]}", fails)


# ────────────────────────────────────────────────────────────────── T3 ──
def t3_malformed(fails):
    block = {
        "rep_sets": [
            {"name": "R1", "wells": ["A01", "ZZZ", 123, "A01"]},   # dup + junk token
            "not a dict",
            {"name": "R2", "wells": "B01,B02"},                    # wells not a list
        ],
        "groups": [
            {"name": "G missing member", "members": ["nope"], "solo_wells": ["c3"]},
            {"name": "G empty", "members": [], "solo_wells": []},
            {"name": "G strbool", "hidden": "true", "members": ["R1"], "solo_wells": []},
            "not a dict either",
        ],
    }
    sels, cur = M.migrate_v1(block, palette=_PALETTE, id_factory=_counter_factory())
    # 3 groups survive (incl. the empty one), R2 is free (wells empty → replicates None), R1 is in a group
    _ok(len(sels) == 4, f"T3: expected 4 selections, got {len(sels)} ({[s['name'] for s in sels]})", fails)
    g_missing = sels[0]
    _ok(g_missing["wells"] == ["C03"] and g_missing["replicates"] == [["C03"]],
        f"T3: missing-member group: wells={g_missing['wells']} reps={g_missing['replicates']}", fails)
    g_empty = sels[1]
    _ok(g_empty["wells"] == [] and g_empty["replicates"] is None,
        f"T3: empty group should survive empty: {g_empty}", fails)
    g_strbool = sels[2]
    _ok(g_strbool["hidden"] is True, "T3: 'true' string should coerce to hidden", fails)
    _ok(g_strbool["wells"] == ["A01"] and g_strbool["replicates"] == [["A01"]],
        f"T3: R1 cleaned: {g_strbool}", fails)
    r2 = sels[3]
    _ok(r2["source"] == "rep_set" and r2["wells"] == [] and r2["replicates"] is None,
        f"T3: R2 (bad wells) → empty free rep-set: {r2}", fails)
    _ok(cur == sels[0]["id"], "T3: current should default to first", fails)


# ────────────────────────────────────────────────────────────────── T4 ──
def t4_missing(fails):
    for name, block, want_n in [
        ("only labels", {"well_labels": {"A01": "x"}}, 0),
        ("empty dict", {}, 0),
        ("reps no groups", {"rep_sets": [{"name": "R", "wells": ["A01"]}]}, 1),
        ("null", None, 0),
        ("no block-ish", {"unrelated": 1}, 0),
    ]:
        sels, cur, lbl, notes = M.from_block(block, id_factory=_counter_factory())
        _ok(len(sels) == want_n, f"T4 [{name}]: expected {want_n} selections, got {len(sels)}", fails)
        _ok(cur == (sels[0]["id"] if sels else None), f"T4 [{name}]: current wrong", fails)
        _ok(isinstance(lbl, dict) and isinstance(notes, str), f"T4 [{name}]: labels/notes types", fails)


# ────────────────────────────────────────────────────────────────── T5 ──
def t5_v2_roundtrip(fails):
    v2 = {
        "schema_version": 2,
        "current_id": "keepme",
        "selections": [
            {"id": "keepme", "name": "A", "color": "#abc", "hidden": False,
             "wells": ["A01", "A02"], "replicates": [["A01", "A02"]], "source": "user",
             "future_key": 42},
            {"id": "keepme", "name": "A", "color": "not-a-colour",   # dup id, dup name, bad colour
             "wells": ["B01"], "source": "user"},
            "junk",
            {"id": "", "name": "", "wells": []},                      # empty id/name
        ],
        "well_labels": {"A01": "alpha"},
        "notes": "n",
    }
    sels, cur, lbl, notes = M.from_block(v2, palette=_PALETTE, id_factory=_counter_factory())
    _ok(len(sels) == 3, f"T5: 3 dicts survive (junk dropped): {len(sels)}", fails)
    _ok(len({s["id"] for s in sels}) == 3, "T5: ids made unique", fails)
    _ok(len({s["name"] for s in sels}) == 3, f"T5: names made unique: {[s['name'] for s in sels]}", fails)
    _ok(sels[0]["color"] == "#AABBCC", f"T5: #abc → #AABBCC: {sels[0]['color']}", fails)
    _ok(all(M._hex6(s["color"]) for s in sels), "T5: every colour is valid #RRGGBB", fails)
    _ok(sels[0].get("future_key") == 42, "T5: unknown keys preserved", fails)
    _ok(cur == sels[0]["id"], "T5: current_id preserved (it was the surviving 'keepme')", fails)
    _ok(M.block_is_v2(v2) and not M.block_is_v2({"rep_sets": [], "groups": []}),
        "T5: block_is_v2 detection", fails)
    # not re-migrated: round-trip is idempotent
    blk2 = M.to_block(sels, lbl, notes, cur)
    sels3, *_ = M.from_block(blk2)
    _ok(sels3 == M.validate_repair(sels), "T5: v2 round-trip not idempotent", fails)


# ────────────────────────────────────────────────────────────── T7 / T8 ──
def t7_backup(fails):
    """Disk-level: a v1 pipeline_info.json + a v2 save → .pre-v2-backup written,
    byte-identical to the pre-save file; a second save doesn't clobber it;
    restoring the backup gives the v1 file back."""
    from well_viewer import sample_definitions as SD
    with tempfile.TemporaryDirectory() as d:
        out = Path(d)
        info = out / "pipeline_info.json"
        v1_payload = {
            "schema": "pipeline",
            "fov_index": [1, 2, 3],
            "sample_definitions": {
                "well_labels": {"A01": "Ctrl"},
                "rep_sets": [{"name": "R1", "wells": ["A01", "A02"]}],
                "groups": [{"name": "G1", "hidden": False, "members": ["R1"], "solo_wells": []}],
                "notes": "n",
            },
        }
        original_bytes = json.dumps(v1_payload, indent=2).encode()
        info.write_bytes(original_bytes)

        block = M.to_block(
            *(_extract := (lambda b: (b[0], b[2], b[3], b[1]))(M.from_block(v1_payload["sample_definitions"])))
        )
        SD.save_to_pipeline_info(out, block)

        backup = out / ("pipeline_info.json" + SD.PRE_V2_BACKUP_SUFFIX)
        _ok(backup.exists(), "T7: .pre-v2-backup not created", fails)
        _ok(backup.read_bytes() == original_bytes, "T7: backup not byte-identical to pre-save file", fails)

        # the live file is now v2
        live = json.loads(info.read_text())
        _ok(M.block_is_v2(live["sample_definitions"]), "T7: live file not v2 after save", fails)
        _ok(live["schema"] == "pipeline" and live["fov_index"] == [1, 2, 3],
            "T7: other pipeline keys not preserved", fails)

        # a second v2 save doesn't clobber the (now-v1-was) backup
        before = backup.read_bytes()
        SD.save_to_pipeline_info(out, block)  # old block on disk is now v2 → no new backup
        _ok(backup.read_bytes() == before, "T7: second save clobbered the backup", fails)
        _ok(not any(p.name.startswith("pipeline_info.json.pre-v2-backup.") for p in out.iterdir()),
            "T7: unexpected timestamped backup on a v2→v2 save", fails)

        # recovery: restore the backup → reads as v1 again
        info.write_bytes(backup.read_bytes())
        restored = json.loads(info.read_text())
        _ok(not M.block_is_v2(restored["sample_definitions"]), "T7: restored file should be v1 again", fails)


def t8_failure(fails):
    """A migration that throws must not crash: from_block swallows nothing weird,
    but selections_to_legacy / from_block on truly hostile input return safely."""
    # hostile inputs that must not raise
    for bad in [object(), 12345, b"bytes", [1, 2, 3], {"selections": "not-a-list", "schema_version": 2}]:
        try:
            sels, cur, lbl, notes = M.from_block(bad, id_factory=_counter_factory())
            _ok(isinstance(sels, list), f"T8: from_block({type(bad).__name__}) → non-list", fails)
        except Exception as exc:  # pragma: no cover
            _ok(False, f"T8: from_block({type(bad).__name__}) raised {exc!r}", fails)
    # selections_to_legacy on junk
    try:
        rs, bg, ari, bag, rh = M.selections_to_legacy([{"id": "x"}, "junk", {"id": "y", "wells": ["A01"], "source": "rep_set"}], "x")
        _ok(isinstance(rs, list) and isinstance(bg, list), "T8: selections_to_legacy types", fails)
    except Exception as exc:  # pragma: no cover
        _ok(False, f"T8: selections_to_legacy raised {exc!r}", fails)
    # a deliberately-throwing id_factory falls back to uuid (no infinite loop / crash)
    sels, _cur = M.migrate_v1({"rep_sets": [{"name": "R", "wells": ["A01"]}], "groups": []},
                              id_factory=(lambda: (_ for _ in ()).throw(RuntimeError("boom"))))
    _ok(len(sels) == 1 and isinstance(sels[0]["id"], str) and sels[0]["id"],
        "T8: throwing id_factory not handled", fails)


# ─────────────────────────────────────────────────────────────────── run ──
def run() -> bool:
    cases = [
        ("T1 clean migration", t1_clean),
        ("T2 name conflicts", t2_conflicts),
        ("T3 malformed legacy data", t3_malformed),
        ("T4 missing fields", t4_missing),
        ("T5 already-v2 / repair / round-trip", t5_v2_roundtrip),
        ("T7 backup & recovery (disk)", t7_backup),
        ("T8 failure handling", t8_failure),
    ]
    all_ok = True
    for name, fn in cases:
        fails: list[str] = []
        try:
            fn(fails)
        except Exception as exc:  # pragma: no cover
            fails.append(f"unexpected exception: {exc!r}")
        ok = not fails
        all_ok = all_ok and ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}"
              + ("" if ok else "\n      - " + "\n      - ".join(fails)))
    print("ALL PASS" if all_ok else "SOME FAILED")
    return all_ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
