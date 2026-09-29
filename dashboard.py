import json
import sys

TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Customer 360 — {scenario}</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #fafafa; color: #222; }}
  h1 {{ font-size: 1.3rem; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 10px; font-size: 0.85rem; text-align: left; vertical-align: top; }}
  th {{ background: #f0f0f0; position: sticky; top: 0; }}
  tr.changed {{ background: #fff8e1; }}
  .band-low {{ color: #888; }}
  .band-medium {{ color: #b8860b; font-weight: 600; }}
  .band-high {{ color: #c0392b; font-weight: 700; }}
  .action-no_action {{ color: #888; }}
  .hitl-escalated, .hitl-human_approved, .hitl-human_rejected, .hitl-human_modified {{ font-weight: 600; }}
  .notes {{ max-width: 480px; font-size: 0.8rem; color: #444; }}
  .summary {{ margin: 1rem 0; padding: 0.75rem; background: #eef; border-radius: 6px; font-size: 0.9rem; }}
</style>
</head>
<body>
  <h1>Customer 360 — {scenario}</h1>
  <div class="summary">{summary}</div>
  <table>
    <tr><th>Date</th><th>State</th><th>Confidence</th><th>Action</th><th>Subtype</th><th>HITL</th><th>Notes</th></tr>
    {rows}
  </table>
</body>
</html>
"""

ROW = """<tr class="{row_class}">
  <td>{date}</td>
  <td>{state}</td>
  <td class="band-{band}">{band}</td>
  <td class="action-{action}">{action}</td>
  <td>{subtype}</td>
  <td class="hitl-{hitl}">{hitl}</td>
  <td class="notes">{notes}</td>
</tr>"""


def build(scenario):
    with open(f"outputs/inferred_events_{scenario}.json", encoding="utf-8") as f:
        checkpoints = json.load(f)

    rows, last_key, transitions = [], None, 0
    for cp in checkpoints:
        key = (cp["inferred_state"], cp["confidence_band"], cp["action"])
        changed = key != last_key
        if changed:
            transitions += 1
        rows.append(ROW.format(
            row_class="changed" if changed else "",
            date=cp["as_of_time"][:10],
            state=cp["inferred_state"],
            band=cp["confidence_band"],
            action=cp["action"],
            subtype=cp["action_subtype"] or "-",
            hitl=cp["hitl_status"],
            notes=cp["notes"],
        ))
        last_key = key

    summary = (f"{len(checkpoints)} daily checkpoints, {transitions} state/action changes. "
               f"Final: <b>{checkpoints[-1]['inferred_state']}</b> "
               f"({checkpoints[-1]['confidence_band']}) &rarr; "
               f"<b>{checkpoints[-1]['action']}</b>")

    html = TEMPLATE.format(scenario=scenario, summary=summary, rows="\n".join(rows))
    out_path = f"outputs/dashboard_{scenario}.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "scenario_01")