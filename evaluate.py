"""Accuracy report: runs the agent on data/test_set.csv (no tickets are created)."""

import csv
from pathlib import Path

from agent import SEVERITIES, triage


# ============================================================
# PROJECT PATHS
# ============================================================

BASE = Path(__file__).parent

TEST_FILE = BASE / "data" / "test_set.csv"
RESULTS_CSV = BASE / "data" / "eval_results.csv"
REPORT_MD = BASE / "data" / "eval_report.md"


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # Check test file
    # --------------------------------------------------------

    if not TEST_FILE.exists():
        print(f"Test file nahi mila: {TEST_FILE}")
        return

    # --------------------------------------------------------
    # Read test dataset
    # --------------------------------------------------------

    with open(
        TEST_FILE,
        newline="",
        encoding="utf-8"
    ) as f:

        rows = list(
            csv.DictReader(f)
        )

    results = []


    # ========================================================
    # RUN EACH TEST
    # ========================================================

    for r in rows:

        print(
            f"\nRunning {r['id']} ..."
        )

        try:

            out = triage(
                r["report"],
                create_tickets=False
            )

            d = out.get(
                "decision"
            ) or {}


            # ------------------------------------------------
            # Diagnostic output
            # ------------------------------------------------

            if not d:

                print(
                    "  TRIAGE ERROR:",
                    out.get("error")
                )

            else:

                print(
                    "  DECISION:",
                    d
                )


        except Exception as e:

            print(
                "  ERROR:",
                e
            )

            d = {}


        # ----------------------------------------------------
        # Duplicate prediction
        # ----------------------------------------------------

        pred_dup = (
            "yes"
            if d.get("is_duplicate")
            else "no"
        )


        # ----------------------------------------------------
        # Save result
        # ----------------------------------------------------

        results.append({

            "id":
                r["id"],

            "report":
                r["report"],

            "expected_severity":
                r["expected_severity"],

            "pred_severity":
                d.get(
                    "severity",
                    ""
                ),

            "expected_module":
                r["expected_module"],

            "pred_module":
                d.get(
                    "module",
                    ""
                ),

            "expected_duplicate":
                r["expected_duplicate"],

            "pred_duplicate":
                pred_dup,

            "reasoning":
                d.get(
                    "reasoning",
                    ""
                ),

        })


    # ========================================================
    # NO RESULTS
    # ========================================================

    if not results:

        print(
            "Test dataset mein koi test nahi mila."
        )

        return


    # ========================================================
    # CALCULATE ACCURACY
    # ========================================================

    n = len(results)


    # Exact severity

    sev = sum(

        x["expected_severity"]
        ==
        x["pred_severity"]

        for x in results

    )


    # Severity within one level

    sev_close = sum(

        x["pred_severity"] in SEVERITIES

        and

        abs(
            SEVERITIES.index(
                x["expected_severity"]
            )

            -

            SEVERITIES.index(
                x["pred_severity"]
            )
        ) <= 1

        for x in results

    )


    # Module accuracy

    mod = sum(

        x["expected_module"]
        ==
        x["pred_module"]

        for x in results

    )


    # Duplicate accuracy

    dup = sum(

        x["expected_duplicate"]
        ==
        x["pred_duplicate"]

        for x in results

    )


    # ========================================================
    # SAVE CSV RESULTS
    # ========================================================

    with open(
        RESULTS_CSV,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                results[0].keys()
            )
        )

        writer.writeheader()

        writer.writerows(
            results
        )


    # ========================================================
    # BUILD MARKDOWN REPORT
    # ========================================================

    lines = [

        "# Accuracy Report",

        "",

        f"Test bugs: {n}",

        "",

        "| Metric | Correct | Accuracy |",

        "|---|---|---|",

        (
            f"| Severity (exact) | "
            f"{sev}/{n} | "
            f"{sev / n:.0%} |"
        ),

        (
            f"| Severity (within 1 level) | "
            f"{sev_close}/{n} | "
            f"{sev_close / n:.0%} |"
        ),

        (
            f"| Module | "
            f"{mod}/{n} | "
            f"{mod / n:.0%} |"
        ),

        (
            f"| Duplicate detection | "
            f"{dup}/{n} | "
            f"{dup / n:.0%} |"
        ),

        "",

        "## Wrong predictions",

        ""

    ]


    # ========================================================
    # FIND WRONG PREDICTIONS
    # ========================================================

    wrong = [

        x

        for x in results

        if (

            x["expected_severity"],
            x["expected_module"],
            x["expected_duplicate"]

        )

        != (

            x["pred_severity"],
            x["pred_module"],
            x["pred_duplicate"]

        )

    ]


    # ========================================================
    # ADD WRONG RESULTS TO REPORT
    # ========================================================

    for x in wrong:

        lines.append(

            f"- **{x['id']}**: "
            f"expected "
            f"{x['expected_severity']}/"
            f"{x['expected_module']}/"
            f"dup={x['expected_duplicate']} "
            f"-> got "
            f"{x['pred_severity']}/"
            f"{x['pred_module']}/"
            f"dup={x['pred_duplicate']}"

        )


    # ========================================================
    # ALL CORRECT
    # ========================================================

    if not wrong:

        lines.append(
            "- None, all predictions matched."
        )


    # ========================================================
    # SAVE MARKDOWN REPORT
    # ========================================================

    REPORT_MD.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )


    # ========================================================
    # PRINT REPORT
    # ========================================================

    print(
        "\n".join(lines)
    )

    print(
        f"\nSaved: "
        f"{RESULTS_CSV} "
        f"and "
        f"{REPORT_MD}"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()