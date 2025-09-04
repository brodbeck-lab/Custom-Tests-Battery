"""
Unified data saver for the Auditory Stroop Task
Saves exactly TWO files per session:
  1) A single consolidated TEXT report (.txt)
  2) A single consolidated JSON bundle (.json)

Author: Behavioral Research Lab
Version: 2.1
"""

import os
import json
from datetime import datetime


# -------------------- Public API --------------------

def save_auditory_stroop_data(trial_data, participant_id, participant_folder_path, task_config):
    """
    Save Auditory Stroop task results as a SINGLE text file and a SINGLE json file.

    Parameters
    ----------
    trial_data : list[dict]
        Each element is a trial record produced by the task.
    participant_id : str
        Participant identifier.
    participant_folder_path : str
        Path to the participant’s root folder.
    task_config : dict
        Configuration used for this run.

    Returns
    -------
    bool
        True if both files were written successfully, else False.
    """
    try:
        # --- Create a task run folder ---
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_folder = os.path.join(participant_folder_path, f"auditory_stroop_task_{timestamp}")
        os.makedirs(task_folder, exist_ok=True)

        # --- Compute summary stats and analysis rows ---
        summary = _compute_summary(trial_data, task_config, participant_id)
        analysis_rows, analysis_headers = _build_analysis_rows(trial_data, participant_id)

        # --- 1) Write unified TEXT report ---
        txt_ok = _write_unified_text_report(
            folder=task_folder,
            timestamp=timestamp,
            participant_id=participant_id,
            task_config=task_config,
            summary=summary,
            trial_data=trial_data,
            analysis_headers=analysis_headers,
            analysis_rows=analysis_rows,
        )

        # --- 2) Write unified JSON bundle ---
        json_ok = _write_unified_json_bundle(
            folder=task_folder,
            timestamp=timestamp,
            participant_id=participant_id,
            task_config=task_config,
            summary=summary,
            trial_data=trial_data,
            analysis_headers=analysis_headers,
            analysis_rows=analysis_rows,
        )

        if txt_ok and json_ok:
            print("✓ Auditory Stroop: saved unified text & json.")
            print(f"  Folder: {task_folder}")
        else:
            print("✗ Auditory Stroop: one or more saves failed.")

        return bool(txt_ok and json_ok)

    except Exception as e:
        print(f"Critical error saving Auditory Stroop data: {e}")
        return False


def emergency_save_auditory_stroop_task(session_manager, trial_data):
    """
    Lightweight emergency save (JSON only) used by crash handler.

    Returns
    -------
    bool
        True if emergency snapshot was written.
    """
    try:
        participant_id = session_manager.session_data.get("participant_id", "EMERGENCY_PARTICIPANT")
        participant_folder = getattr(session_manager, "participant_folder_path", None)

        if not participant_folder:
            documents_path = os.path.expanduser("~/Documents")
            participant_folder = os.path.join(documents_path, "Custom Tests Battery Data", participant_id)
            os.makedirs(participant_folder, exist_ok=True)

        emergency_folder = os.path.join(participant_folder, "system", "emergency_saves")
        os.makedirs(emergency_folder, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        emergency_path = os.path.join(emergency_folder, f"EMERGENCY_auditory_stroop_{ts}.json")

        data = {
            "task_name": "Auditory Stroop Task",
            "participant_id": participant_id,
            "save_time": datetime.now().isoformat(),
            "trial_data": trial_data,
            "session_data": session_manager.session_data,
            "note": "Emergency snapshot for recovery",
        }
        with open(emergency_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Emergency save completed: {os.path.basename(emergency_path)}")
        return True
    except Exception as e:
        print(f"Emergency save failed (Auditory Stroop): {e}")
        return False


__all__ = ["save_auditory_stroop_data", "emergency_save_auditory_stroop_task"]


# -------------------- Helpers: summaries & analysis table --------------------

def _compute_summary(trial_data, task_config, participant_id):
    """
    Build a compact summary with overall and per-part metrics.
    """
    total = len(trial_data)
    responded = [t for t in trial_data if t.get("response") and t["response"] != "NO_RESPONSE"]
    correct = [t for t in responded if t.get("correct_response")]
    overall_acc = (len(correct) / total * 100) if total else 0.0
    overall_resp_rate = (len(responded) / total * 100) if total else 0.0
    overall_avg_rt = (sum(t.get("reaction_time_ms", 0.0) for t in responded) / len(responded)) if responded else 0.0

    def part_stats(part_idx):
        pts = [t for t in trial_data if t.get("part") == part_idx]
        rpts = [t for t in pts if t.get("response") and t["response"] != "NO_RESPONSE"]
        cpts = [t for t in rpts if t.get("correct_response")]
        acc = (len(cpts) / len(pts) * 100) if pts else 0.0
        rr = (len(rpts) / len(pts) * 100) if pts else 0.0
        art = (sum(t.get("reaction_time_ms", 0.0) for t in rpts) / len(rpts)) if rpts else 0.0
        return {
            "trials": len(pts),
            "responses": len(rpts),
            "correct": len(cpts),
            "accuracy_pct": acc,
            "response_rate_pct": rr,
            "avg_rt_ms": art,
        }

    return {
        "participant_id": participant_id,
        "save_time": datetime.now().isoformat(),
        "totals": {
            "trials": total,
            "responses": len(responded),
            "correct": len(correct),
            "accuracy_pct": overall_acc,
            "response_rate_pct": overall_resp_rate,
            "avg_rt_ms": overall_avg_rt,
        },
        "by_part": {
            "practice": part_stats(0),
            "main": part_stats(1),
        },
        "config": dict(task_config or {}),
    }


def _build_analysis_rows(trial_data, participant_id):
    """
    Build an 'analysis-ready' table in memory.
    Returns (rows, headers).
    """
    headers = [
        "participant",
        "trial_id",
        "part",                 # 0 practice, 1 main
        "trial_in_part",
        "stimulus",
        "expected_gender",
        "response",
        "correct",              # 0/1
        "reaction_time_ms",
        "timestamp",
    ]
    rows = []
    for i, t in enumerate(trial_data, start=1):
        rows.append([
            participant_id,
            i,
            t.get("part", ""),
            t.get("trial_in_part", ""),
            t.get("stimulus_file", ""),
            t.get("expected_gender", ""),
            t.get("response", ""),
            1 if t.get("correct_response") else 0,
            round(float(t.get("reaction_time_ms", 0.0)), 2) if t.get("reaction_time_ms") is not None else "",
            t.get("timestamp", ""),
        ])
    return rows, headers


# -------------------- Writers: unified text + json ---------------------------

def _write_unified_text_report(
    folder, timestamp, participant_id, task_config, summary,
    trial_data, analysis_headers, analysis_rows
):
    """
    Write ONE consolidated text report.
    """
    try:
        fname = os.path.join(folder, f"auditory_stroop_report_{timestamp}.txt")
        with open(fname, "w", encoding="utf-8") as f:
            # Header
            f.write("AUDITORY STROOP TASK — CONSOLIDATED REPORT\n")
            f.write("=" * 72 + "\n\n")
            f.write(f"Participant ID: {participant_id}\n")
            f.write(f"Saved: {summary['save_time']}\n")
            f.write(f"Task Version: 2.1\n\n")

            # Configuration
            f.write("TASK CONFIGURATION\n")
            f.write("-" * 72 + "\n")
            for k, v in (task_config or {}).items():
                f.write(f"{k}: {v}\n")
            f.write("\n")

            # Summary
            f.write("PERFORMANCE SUMMARY\n")
            f.write("-" * 72 + "\n")
            tot = summary["totals"]
            f.write(f"Total Trials: {tot['trials']}\n")
            f.write(f"Total Responses: {tot['responses']}\n")
            f.write(f"Correct Responses: {tot['correct']}\n")
            f.write(f"Overall Accuracy: {tot['accuracy_pct']:.1f}%\n")
            f.write(f"Response Rate: {tot['response_rate_pct']:.1f}%\n")
            f.write(f"Average RT: {tot['avg_rt_ms']:.0f} ms\n\n")

            f.write("By Part:\n")
            for label, stats in summary["by_part"].items():
                f.write(
                    f"  {label.title()} — Trials: {stats['trials']}, "
                    f"Responses: {stats['responses']}, Correct: {stats['correct']}, "
                    f"Accuracy: {stats['accuracy_pct']:.1f}%, "
                    f"Resp. Rate: {stats['response_rate_pct']:.1f}%, "
                    f"Avg RT: {stats['avg_rt_ms']:.0f} ms\n"
                )
            f.write("\n")

            # Detailed trial dump
            f.write("DETAILED TRIAL DATA\n")
            f.write("-" * 72 + "\n")
            f.write("idx | part | trial_in_part | stimulus | expected | response | correct | rt(ms) | timestamp\n")
            f.write("-" * 72 + "\n")
            for i, t in enumerate(trial_data, start=1):
                f.write(
                    f"{i:3d} | {t.get('part',''):4} | {t.get('trial_in_part',''):12} | "
                    f"{t.get('stimulus_file','')[:20]:20} | "
                    f"{t.get('expected_gender','')[:7]:7} | "
                    f"{t.get('response','')[:7]:7} | "
                    f"{'1' if t.get('correct_response') else '0':7} | "
                    f"{round(float(t.get('reaction_time_ms', 0.0)),0):6.0f} | "
                    f"{t.get('timestamp','')}\n"
                )
            f.write("\n")

            # Analysis table (CSV-style inside the TXT)
            f.write("ANALYSIS TABLE (CSV-FORMATTED)\n")
            f.write("-" * 72 + "\n")
            f.write(",".join(analysis_headers) + "\n")
            for row in analysis_rows:
                f.write(",".join(_csv_field(x) for x in row) + "\n")

            f.write("\n" + "=" * 72 + "\n")
            f.write("End of report\n")

        print(f"✓ Unified TEXT saved: {os.path.basename(fname)}")
        return True
    except Exception as e:
        print(f"Error writing unified text report: {e}")
        return False


def _write_unified_json_bundle(
    folder, timestamp, participant_id, task_config, summary,
    trial_data, analysis_headers, analysis_rows
):
    """
    Write ONE consolidated JSON bundle with metadata+config+summary+trials+analysis.
    """
    try:
        fname = os.path.join(folder, f"auditory_stroop_data_{timestamp}.json")
        bundle = {
            "metadata": {
                "task_name": "Auditory Stroop Task",
                "task_version": "2.1",
                "participant_id": participant_id,
                "save_timestamp": summary["save_time"],
                "total_trials": len(trial_data),
                "files": {
                    "text_report": f"auditory_stroop_report_{timestamp}.txt",
                    "json_bundle": os.path.basename(fname),
                },
            },
            "configuration": task_config or {},
            "summary": summary,
            "trial_data": trial_data,  # full raw trials
            "analysis": {
                "headers": analysis_headers,
                "rows": analysis_rows,
            },
        }
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(bundle, f, indent=2, ensure_ascii=False)

        print(f"✓ Unified JSON saved: {os.path.basename(fname)}")
        return True
    except Exception as e:
        print(f"Error writing unified JSON: {e}")
        return False


# -------------------- Small utilities --------------------

def _csv_field(value):
    """
    Render a Python value as a CSV-safe string for the TXT report's analysis table.
    """
    if value is None:
        return ""
    s = str(value)
    if any(c in s for c in [",", "\"", "\n"]):
        s = '"' + s.replace('"', '""') + '"'
    return s
