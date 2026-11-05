"""Core patents.

A candidate files its core patent when it first clears a real gate (preclinical for innovative drugs,
the design stage for improved drugs). The patent is granted a year later. The product keeps market
exclusivity until the patent expires; then generic competitors arrive and sales fall to a floor over
about half a year. This keeps old blockbusters from paying for everything forever, and gives the long
middle of a game a few more visible moments.
"""

from . import events
from .content import PATENT, STAGES
from .model import date, log


def maybe_file(s, p, key):
    kind = p["kind"]
    if kind not in PATENT["term"] or p.get("patent") or PATENT["filed_after"][kind] != key:
        return
    expires = s["week"] + PATENT["term"][kind]
    p["patent"] = {"filed": s["week"], "granted": None, "expires": expires}
    events.emit(
        s,
        "patent_filed",
        project=p["id"],
        room=STAGES[key]["room"],
        data={"name": p["name"], "expires": expires, "expires_year": expires // 48 + 1},
    )


def exclusive_until(p):
    return p["patent"]["expires"] if p.get("patent") else None


def tick(s):
    for p in s["projects"]:
        patent = p.get("patent")
        if not patent or patent["granted"] is not None or s["week"] - patent["filed"] < PATENT["grant_delay"]:
            continue
        if p["status"] in ("failed", "terminated"):
            patent["granted"] = False
            continue
        patent["granted"] = s["week"]
        gain = 2 if p["kind"] == "innovative" else 1
        s["reputation"] += gain
        events.emit(s, "patent_granted", project=p["id"], data={"name": p["name"], "reputation": gain})
    for d in s["products"]:
        expires = d.get("exclusive_until")
        if expires is None or not d["active"]:
            continue
        if s["week"] == expires - 48 and not d["partner"]:
            log(s, f"{d['name']}的专利还有一年到期。可以准备换代或新产品，接上之后的收入。")
        if s["week"] >= expires and not d.get("generic_entry"):
            d["generic_entry"] = s["week"]
            events.emit(s, "patent_expired", project=d["project"], data={"name": d["name"]})


def erosion(s, d):
    """Sales factor after generic entry: 1 before expiry, then down to the floor over erosion_weeks."""
    expires = d.get("exclusive_until")
    if expires is None or s["week"] < expires:
        return 1.0
    floor = PATENT["floor"][d["kind"]]
    progress = min(1.0, (s["week"] - expires) / PATENT["erosion_weeks"])
    return 1 - (1 - floor) * progress


def view(s):
    rows = []
    for p in s["projects"]:
        patent = p.get("patent")
        if not patent or patent["granted"] is False:
            continue
        product = next((d for d in s["products"] if d["project"] == p["id"]), None)
        if s["week"] >= patent["expires"]:
            status = "已到期"
        elif patent["granted"]:
            status = "已授权"
        else:
            status = "审查中"
        rows.append(
            {
                "project": p["id"],
                "name": product["name"] if product else p["name"],
                "filed": patent["filed"],
                "granted": patent["granted"],
                "expires": patent["expires"],
                "expires_label": date(patent["expires"]),
                "status": status,
                "on_market": bool(product and product["active"]),
            }
        )
    return rows
