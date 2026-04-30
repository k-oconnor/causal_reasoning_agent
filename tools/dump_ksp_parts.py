"""
tools/dump_ksp_parts.py

Parse KSP 1.12.x GameData part .cfg files and emit a structured Markdown
reference for the agent's skills directory.

Usage:
    python tools/dump_ksp_parts.py

Writes:  skills/ksp_parts.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

KSP_ROOT = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program")
GAMEDATA  = KSP_ROOT / "GameData"
OUT_FILE  = Path(__file__).resolve().parent.parent / "skills" / "ksp_parts.md"

SCAN_DIRS = [
    GAMEDATA / "Squad" / "Parts",
    GAMEDATA / "SquadExpansion" / "MakingHistory" / "Parts",
    GAMEDATA / "SquadExpansion" / "Serenity" / "Parts",
]

# ── low-level text helpers ──────────────────────────────────────────────────

def resolve_title(raw: str) -> str:
    """
    KSP titles look like:
        title = #autoLOC_500439 //#autoLOC_500439 = LV-T30 "Reliant" Liquid Fuel Engine
    Extract the English text after the last '= '.
    Fall back to the raw value if no comment is present.
    """
    # Try the comment form first
    m = re.search(r"//[^=]+=\s*(.+)$", raw)
    if m:
        return m.group(1).strip()
    # If starts with #autoLOC, no useful text
    if raw.startswith("#autoLOC"):
        return ""
    return raw.strip()


def extract_part_block(text: str) -> str | None:
    """Return the text of the outermost PART { ... } block, or None."""
    m = re.search(r"^PART\s*\{", text, re.MULTILINE)
    if not m:
        return None
    start = m.end()
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    return text[start:i - 1]


def top_level_kv(block: str) -> dict[str, str]:
    """
    Extract key=value pairs that are at the TOP level of this block
    (depth 0 — not inside any nested { }).
    """
    kv: dict[str, str] = {}
    depth = 0
    for line in block.splitlines():
        stripped = line.strip()
        depth += stripped.count("{") - stripped.count("}")
        if depth == 0 and "=" in stripped and not stripped.startswith("//"):
            key, _, val = stripped.partition("=")
            # Strip inline comments but keep the whole value including comment
            # (title lines rely on the comment for the English name)
            kv[key.strip()] = val.strip()
    return kv


def extract_module_blocks(block: str) -> list[tuple[str, str]]:
    """Return list of (module_name, module_text) for all MODULE { } blocks."""
    modules: list[tuple[str, str]] = []
    i = 0
    while i < len(block):
        m = re.search(r"\bMODULE\s*\{", block[i:])
        if not m:
            break
        start = i + m.end()
        depth = 1
        j = start
        while j < len(block) and depth > 0:
            if block[j] == "{":
                depth += 1
            elif block[j] == "}":
                depth -= 1
            j += 1
        mod_text = block[start:j - 1]
        # Get the name field of this module
        nm = re.search(r"^\s*name\s*=\s*(\S+)", mod_text, re.MULTILINE)
        mod_name = nm.group(1) if nm else "UNKNOWN"
        modules.append((mod_name, mod_text))
        i = i + m.start() + 1  # advance past this MODULE keyword
    return modules


def parse_atmosphere_curve(mod_text: str) -> tuple[float, float]:
    """Return (isp_vac, isp_sl) from an atmosphereCurve block."""
    ac = re.search(r"atmosphereCurve\s*\{([^}]*)\}", mod_text, re.DOTALL)
    if not ac:
        return 0.0, 0.0
    isp_vac = isp_sl = 0.0
    for line in ac.group(1).splitlines():
        line = line.strip()
        if not line.startswith("key"):
            continue
        # Lines are either "key = 0 310" or "key 0 310"
        # Normalise: strip 'key' prefix and optional '=', then split numbers
        nums = re.findall(r"[-\d.]+", line[3:])  # skip the 'key' word
        if len(nums) >= 2:
            try:
                alt = float(nums[0])
                isp = float(nums[1])
                if alt == 0:
                    isp_vac = isp
                elif alt == 1:
                    isp_sl = isp
            except ValueError:
                pass
    return isp_vac, isp_sl


def parse_resources(block: str) -> dict[str, float]:
    resources: dict[str, float] = {}
    for rb in re.finditer(r"RESOURCE\s*\{([^}]*)\}", block, re.DOTALL):
        inner = rb.group(1)
        nm = re.search(r"^\s*name\s*=\s*(\S+)", inner, re.MULTILINE)
        am = re.search(r"^\s*amount\s*=\s*([\d.]+)", inner, re.MULTILINE)
        if nm and am:
            resources[nm.group(1)] = float(am.group(1))
    return resources


def safe_float(s: str, default: float = 0.0) -> float:
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


# ── part parser ─────────────────────────────────────────────────────────────

def parse_part_file(cfg_path: Path) -> dict | None:
    try:
        # utf-8-sig automatically strips the UTF-8 BOM that many KSP cfg files start with
        text = cfg_path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return None

    part_block = extract_part_block(text)
    if part_block is None:
        return None

    kv = top_level_kv(part_block)

    internal_name = kv.get("name", "")
    title_raw = kv.get("title", "")
    title = resolve_title(title_raw)
    mass  = safe_float(kv.get("mass", "0"))
    bulk  = kv.get("bulkheadProfiles", kv.get("node_size", ""))

    # Pack = which expansion (last meaningful directory name)
    pack_parts = cfg_path.parts
    if "MakingHistory" in pack_parts:
        pack = "MakingHistory"
    elif "Serenity" in pack_parts:
        pack = "Serenity"
    else:
        pack = "Squad"

    modules = extract_module_blocks(part_block)
    module_names = [n for n, _ in modules]
    resources = parse_resources(part_block)

    result: dict = {
        "internal_name": internal_name,
        "title": title,
        "mass": mass,
        "bulk": bulk,
        "pack": pack,
    }

    # ── engine ──
    engine_mods = [(n, t) for n, t in modules if "ModuleEngines" in n]
    if engine_mods:
        _, eng_text = engine_mods[0]
        eng_kv = top_level_kv(eng_text)
        isp_vac, isp_sl = parse_atmosphere_curve(eng_text)
        max_thrust = safe_float(eng_kv.get("maxThrust", "0"))
        sl_thrust = round(max_thrust * isp_sl / isp_vac, 2) if isp_vac > 0 else 0.0

        gimbal_mods = [(n, t) for n, t in modules if "ModuleGimbal" in n]
        gimbal = 0.0
        if gimbal_mods:
            _, gm_text = gimbal_mods[0]
            gm_kv = top_level_kv(gm_text)
            gimbal = safe_float(gm_kv.get("gimbalRange", "0"))

        if "SolidFuel" in resources:
            result["category"] = "srb"
            result.update({
                "thrust_vac": max_thrust,
                "thrust_sl":  sl_thrust,
                "isp_vac":    isp_vac,
                "isp_sl":     isp_sl,
                "solid_fuel": resources.get("SolidFuel", 0),
                "mass_dry":   mass,
                "mass_wet":   round(mass + resources.get("SolidFuel", 0) * 0.0075, 4),
            })
        else:
            result["category"] = "engine"
            result.update({
                "thrust_vac": max_thrust,
                "thrust_sl":  sl_thrust,
                "isp_vac":    isp_vac,
                "isp_sl":     isp_sl,
                "gimbal":     gimbal,
            })
        return result

    # ── decoupler / separator ──
    if any("ModuleDecouple" in n or "ModuleAnchoredDecoupler" in n for n in module_names):
        dc_mod = next(((n, t) for n, t in modules if "ModuleDecouple" in n or "ModuleAnchoredDecoupler" in n), None)
        ej = 0.0
        if dc_mod:
            dc_kv = top_level_kv(dc_mod[1])
            ej = safe_float(dc_kv.get("ejectionForce", "0"))
        result["category"] = "decoupler"
        result["ejection_force"] = ej
        return result

    # ── command module ──
    if any("ModuleCommand" in n for n in module_names):
        crew_m = re.search(r"minimumCrew\s*=\s*(\d+)", part_block)
        crew = int(crew_m.group(1)) if crew_m else 0
        result["category"] = "command"
        result["min_crew"] = crew
        return result

    # ── parachute ──
    if any("ModuleParachute" in n for n in module_names):
        result["category"] = "parachute"
        return result

    # ── RCS ──
    if any("ModuleRCS" in n for n in module_names):
        rcs_mod = next((t for n, t in modules if "ModuleRCS" in n), "")
        rcs_kv = top_level_kv(rcs_mod)
        result["category"] = "rcs"
        result["thrust"] = safe_float(rcs_kv.get("thrusterPower", "0"))
        return result

    # ── fuel tank ──
    lf = resources.get("LiquidFuel", 0)
    ox = resources.get("Oxidizer", 0)
    if lf > 0 or ox > 0:
        prop_mass = (lf + ox) * 0.005
        result["category"] = "tank"
        result.update({
            "lf": lf, "ox": ox,
            "mass_dry": mass,
            "mass_wet": round(mass + prop_mass, 4),
        })
        return result

    mp = resources.get("MonoPropellant", 0)
    if mp > 0:
        result["category"] = "mono_tank"
        result.update({
            "monoprop": mp,
            "mass_dry": mass,
            "mass_wet": round(mass + mp * 0.004, 4),
        })
        return result

    result["category"] = "other"
    return result


# ── markdown formatting ─────────────────────────────────────────────────────

def title_or_name(r: dict) -> str:
    return r["title"] if r["title"] else r["internal_name"]


def fmt_engines(rows: list[dict]) -> str:
    rows = [r for r in rows if r.get("thrust_vac", 0) > 0]
    if not rows:
        return ""
    rows = sorted(rows, key=lambda r: r["thrust_vac"])
    lines = ["\n## Liquid Fuel Engines\n"]
    lines.append("| Title | Internal Name | Mass (t) | Thrust Vac (kN) | Thrust SL (kN) | Isp Vac (s) | Isp SL (s) | Gimbal (°) | Pack |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {title_or_name(r)} | `{r['internal_name']}` | {r['mass']:.3f} "
            f"| {r['thrust_vac']:.2f} | {r.get('thrust_sl',0):.2f} "
            f"| {r.get('isp_vac',0):.0f} | {r.get('isp_sl',0):.0f} "
            f"| {r.get('gimbal',0):.1f} | {r['pack']} |"
        )
    return "\n".join(lines)


def fmt_srbs(rows: list[dict]) -> str:
    rows = [r for r in rows if r.get("thrust_vac", 0) > 0]
    if not rows:
        return ""
    rows = sorted(rows, key=lambda r: r["thrust_vac"])
    lines = ["\n## Solid Rocket Boosters\n"]
    lines.append("| Title | Internal Name | Mass Dry (t) | Mass Wet (t) | SolidFuel (u) | Thrust Vac (kN) | Thrust SL (kN) | Isp Vac (s) | Isp SL (s) | Pack |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {title_or_name(r)} | `{r['internal_name']}` | {r.get('mass_dry',0):.3f} "
            f"| {r.get('mass_wet',0):.3f} | {r.get('solid_fuel',0):.0f} "
            f"| {r.get('thrust_vac',0):.2f} | {r.get('thrust_sl',0):.2f} "
            f"| {r.get('isp_vac',0):.0f} | {r.get('isp_sl',0):.0f} | {r['pack']} |"
        )
    return "\n".join(lines)


def fmt_tanks(rows: list[dict]) -> str:
    rows = [r for r in rows if r.get("lf", 0) > 0 or r.get("ox", 0) > 0]
    if not rows:
        return ""
    rows = sorted(rows, key=lambda r: r.get("mass_wet", 0))
    lines = ["\n## Liquid Fuel + Oxidizer Tanks\n"]
    lines.append("| Title | Internal Name | Mass Dry (t) | Mass Wet (t) | LF (u) | OX (u) | Pack |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {title_or_name(r)} | `{r['internal_name']}` | {r.get('mass_dry',0):.4f} "
            f"| {r.get('mass_wet',0):.4f} | {r.get('lf',0):.0f} | {r.get('ox',0):.0f} | {r['pack']} |"
        )
    return "\n".join(lines)


def fmt_decouplers(rows: list[dict]) -> str:
    if not rows:
        return ""
    rows = sorted(rows, key=lambda r: r["mass"])
    lines = ["\n## Decouplers and Separators\n"]
    lines.append("| Title | Internal Name | Mass (t) | Ejection Force (kN) | Pack |")
    lines.append("|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {title_or_name(r)} | `{r['internal_name']}` | {r['mass']:.4f} "
            f"| {r.get('ejection_force',0):.0f} | {r['pack']} |"
        )
    return "\n".join(lines)


def fmt_command(rows: list[dict]) -> str:
    if not rows:
        return ""
    rows = sorted(rows, key=lambda r: r["mass"])
    lines = ["\n## Command Modules\n"]
    lines.append("| Title | Internal Name | Mass (t) | Pack |")
    lines.append("|---|---|---|---|")
    for r in rows:
        lines.append(f"| {title_or_name(r)} | `{r['internal_name']}` | {r['mass']:.4f} | {r['pack']} |")
    return "\n".join(lines)


def fmt_parachutes(rows: list[dict]) -> str:
    if not rows:
        return ""
    rows = sorted(rows, key=lambda r: r["mass"])
    lines = ["\n## Parachutes\n"]
    lines.append("| Title | Internal Name | Mass (t) | Pack |")
    lines.append("|---|---|---|---|")
    for r in rows:
        lines.append(f"| {title_or_name(r)} | `{r['internal_name']}` | {r['mass']:.4f} | {r['pack']} |")
    return "\n".join(lines)


def fmt_mono_tanks(rows: list[dict]) -> str:
    if not rows:
        return ""
    rows = sorted(rows, key=lambda r: r["mass"])
    lines = ["\n## MonoPropellant Tanks\n"]
    lines.append("| Title | Internal Name | Mass Dry (t) | Mass Wet (t) | MonoProp (u) | Pack |")
    lines.append("|---|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {title_or_name(r)} | `{r['internal_name']}` | {r.get('mass_dry',0):.4f} "
            f"| {r.get('mass_wet',0):.4f} | {r.get('monoprop',0):.0f} | {r['pack']} |"
        )
    return "\n".join(lines)


def fmt_rcs(rows: list[dict]) -> str:
    if not rows:
        return ""
    rows = sorted(rows, key=lambda r: r["mass"])
    lines = ["\n## RCS Thrusters\n"]
    lines.append("| Title | Internal Name | Mass (t) | Thrust (kN) | Pack |")
    lines.append("|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {title_or_name(r)} | `{r['internal_name']}` | {r['mass']:.4f} "
            f"| {r.get('thrust',0):.3f} | {r['pack']} |"
        )
    return "\n".join(lines)


# ── main ───────────────────────────────────────────────────────────────────

def main() -> None:
    cats: dict[str, list[dict]] = {
        "engine": [], "srb": [], "tank": [], "decoupler": [],
        "command": [], "parachute": [], "rcs": [], "mono_tank": [], "other": [],
    }

    print("Scanning KSP GameData...", file=sys.stderr)
    total = 0
    for base in SCAN_DIRS:
        if not base.exists():
            print(f"  [skip] {base}", file=sys.stderr)
            continue
        for cfg_path in sorted(base.rglob("*.cfg")):
            result = parse_part_file(cfg_path)
            if result is None:
                continue
            cat = result.get("category", "other")
            if cat not in cats:
                cats["other"] = cats.get("other", [])
                cat = "other"
            cats[cat].append(result)
            total += 1

    print(f"  Parsed {total} parts:", file=sys.stderr)
    for k, v in cats.items():
        if v:
            print(f"    {k:12s}: {len(v)}", file=sys.stderr)

    sections = [
        "# KSP 1.12.5 Stock Parts Reference",
        "",
        "Generated directly from GameData .cfg files — exact stats for this installation.",
        "",
        "**Internal Name** = the `name` field in the .cfg — what kRPC returns for `part.name`.",
        "**Title** = the display name shown in the VAB parts list.",
        "",
        "Mass = dry mass for engines, decouplers, command pods.",
        "For tanks: dry mass (empty) and wet mass (full). 1 unit LF or OX = 5 kg.",
        "",
        "**Thrust SL** is computed from `thrust_vac × (Isp_SL / Isp_vac)`.",
        "",
        "Pack: `Squad` = stock, `MakingHistory` = Making History DLC, `Serenity` = Breaking Ground DLC.",
        "",
        "---",
    ]

    # Filter out jet engines, ion engine, and parts irrelevant to a rocket Mun mission
    JET_NAMES = {
        "ionEngine", "miniJetEngine", "JetEngine", "turboJet", "turboFanEngine",
        "turboFanSize2", "RAPIER",
    }
    cats["engine"] = [r for r in cats["engine"] if r["internal_name"] not in JET_NAMES]

    # Remove the misclassified FL-C1000 (it's a tank, not an SRB)
    cats["srb"] = [r for r in cats["srb"] if r.get("solid_fuel", 0) > 10]

    for fn, key in [
        (fmt_engines,    "engine"),
        (fmt_srbs,       "srb"),
        (fmt_tanks,      "tank"),
        (fmt_decouplers, "decoupler"),
        (fmt_command,    "command"),
        (fmt_parachutes, "parachute"),
        (fmt_mono_tanks, "mono_tank"),
        (fmt_rcs,        "rcs"),
    ]:
        s = fn(cats[key])
        if s:
            sections.append(s)

    content = "\n".join(sections)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(content, encoding="utf-8")
    print(f"\nWrote: {OUT_FILE}  ({OUT_FILE.stat().st_size:,} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
