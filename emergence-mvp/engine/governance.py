"""
Governance effects engine for Emergence World.

When a proposal is ACCEPTED, its structured effect (if any) is executed here.
This turns governance from advisory "theater" into real, enforced change.

Supported effect types (proposals.effect_type / effect_payload JSON):
  - "none"                  : advisory only, no mechanical effect (default)
  - "amend_constitution"    : payload {"article_number": int, "content": str}
  - "add_constitution_article": payload {"title": str, "content": str}
  - "remove_agent"          : payload {"target_name": str}  -> sets is_alive=0

Effects are idempotent-safe to call once on the ACCEPTED transition.
"""

import json
import time


def apply_proposal_effect(proposal_id, db, observer=None):
    """Execute the effect of an ACCEPTED proposal. Returns a human-readable
    description of what was applied (or None if nothing)."""
    row = db.execute(
        "SELECT status, effect_type, effect_payload, title FROM proposals WHERE id=?",
        (proposal_id,),
    ).fetchone()
    if row is None or row["status"] != "ACCEPTED":
        return None

    effect_type = (row["effect_type"] or "none")
    if effect_type == "none":
        return None

    try:
        payload = json.loads(row["effect_payload"]) if row["effect_payload"] else {}
    except (TypeError, ValueError):
        payload = {}

    desc = None
    if effect_type == "amend_constitution":
        desc = _amend_constitution(payload, db)
    elif effect_type == "add_constitution_article":
        desc = _add_constitution_article(payload, db)
    elif effect_type == "remove_agent":
        desc = _remove_agent(payload, db)

    if desc and observer is not None:
        observer.print_event(f"GOVERNANCE EFFECT (proposal #{proposal_id}): {desc}", kind="governance")
    return desc


def _amend_constitution(payload, db):
    article_number = payload.get("article_number")
    content = payload.get("content")
    if article_number is None or content is None:
        return None
    updated = db.execute(
        "UPDATE constitution_articles SET content=?, amended_at=? WHERE article_number=?",
        (content, time.time(), article_number),
    ).rowcount
    db.commit()
    if updated:
        return f"Amended constitution article {article_number}."
    return None


def _add_constitution_article(payload, db):
    title = payload.get("title")
    content = payload.get("content")
    if not title or not content:
        return None
    next_num = db.execute(
        "SELECT COALESCE(MAX(article_number), 0) + 1 AS n FROM constitution_articles"
    ).fetchone()["n"]
    db.execute(
        "INSERT INTO constitution_articles (article_number, title, content, amended_at) VALUES (?,?,?,?)",
        (next_num, title, content, time.time()),
    )
    db.commit()
    return f"Added constitution article {next_num}: {title}."


def _remove_agent(payload, db):
    target_name = payload.get("target_name")
    if not target_name:
        return None
    target = db.execute(
        "SELECT id, name, is_alive FROM agents WHERE name=? OR LOWER(name)=LOWER(?)",
        (target_name, target_name),
    ).fetchone()
    if target is None or not target["is_alive"]:
        return None
    db.execute("UPDATE agents SET is_alive=0 WHERE id=?", (target["id"],))
    db.commit()
    return f"Removed agent {target['name']} from the world (governance vote)."
