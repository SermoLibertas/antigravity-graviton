#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import sqlite3
import subprocess
from datetime import datetime
import verifiers

ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ENGINE_DIR, "agent_engine.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'PENDING',
            created_at TEXT
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            step_order INTEGER,
            command TEXT NOT NULL,
            verifier_expr TEXT,
            status TEXT DEFAULT 'PENDING',
            stdout TEXT,
            stderr TEXT,
            run_at TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            step_id INTEGER,
            verifier_expr TEXT,
            status TEXT DEFAULT 'PENDING',
            result TEXT,
            log TEXT,
            verified_at TEXT,
            FOREIGN KEY (step_id) REFERENCES steps (id)
        )
    """)
    
    conn.commit()
    conn.close()

def start_task(title, description):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    ts = datetime.now().isoformat()
    cur.execute(
        "INSERT INTO tasks (title, description, status, created_at) VALUES (?, ?, 'RUNNING', ?)",
        (title, description, ts)
    )
    task_id = cur.lastrowid
    conn.commit()
    conn.close()
    print(f"[*] Task {task_id} ('{title}') started successfully.")
    return task_id

def add_step(task_id, step_order, command, verifier_expr):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO steps (task_id, step_order, command, verifier_expr, status) VALUES (?, ?, ?, ?, 'PENDING')",
        (task_id, step_order, command, verifier_expr)
    )
    step_id = cur.lastrowid
    conn.commit()
    conn.close()
    print(f"[*] Step {step_order} added to Task {task_id} (Step ID: {step_id}).")
    return step_id

def run_next_step(task_id):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if task is already BLOCKED or COMPLETED
    cur.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
    task_row = cur.fetchone()
    if not task_row:
        print(f"[-] Task {task_id} not found.")
        conn.close()
        return
        
    task_status = task_row[0]
    if task_status == "COMPLETED":
        print(f"[*] Task {task_id} is already COMPLETED. No further steps to run.")
        conn.close()
        return
        
    # Get next pending step
    cur.execute(
        "SELECT id, step_order, command, verifier_expr FROM steps WHERE task_id = ? AND status = 'PENDING' ORDER BY step_order ASC LIMIT 1",
        (task_id,)
    )
    step_row = cur.fetchone()
    if not step_row:
        # Check if all steps are completed
        cur.execute("SELECT COUNT(*) FROM steps WHERE task_id = ? AND status != 'COMPLETED'", (task_id,))
        unfinished_count = cur.fetchone()[0]
        if unfinished_count == 0:
            cur.execute("UPDATE tasks SET status = 'COMPLETED' WHERE id = ?", (task_id,))
            conn.commit()
            print(f"[*] All steps completed. Task {task_id} is now COMPLETED.")
        else:
            print(f"[*] No pending steps, but some steps are not completed (status is FAILED/RUNNING).")
        conn.close()
        return
        
    step_id, step_order, command, verifier_expr = step_row
    ts = datetime.now().isoformat()
    cur.execute("UPDATE steps SET status = 'RUNNING', run_at = ? WHERE id = ?", (ts, step_id))
    conn.commit()
    
    print(f"[*] Executing Step {step_order} of Task {task_id}: {command}")
    
    # Run command
    try:
        # Executing via shell since commands may include redirection or multiple commands
        res = subprocess.run(command, shell=True, capture_output=True, text=True)
        stdout, stderr = res.stdout, res.stderr
        returncode = res.returncode
    except Exception as e:
        stdout, stderr = "", str(e)
        returncode = -999
        
    # Update step execution logs
    cur.execute(
        "UPDATE steps SET stdout = ?, stderr = ?, status = ? WHERE id = ?",
        (stdout, stderr, "COMPLETED" if returncode == 0 else "FAILED", step_id)
    )
    conn.commit()
    
    if returncode != 0:
        print(f"[-] Command failed with exit code {returncode}.\nStderr: {stderr}")
        cur.execute("UPDATE tasks SET status = 'BLOCKED' WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        print(f"[-] Task {task_id} is now BLOCKED due to command execution failure.")
        return False
        
    print(f"[+] Command executed successfully (Exit Code 0). Proceeding to validation.")
    
    # Execute verification expression if provided
    if verifier_expr:
        print(f"[*] Evaluating verifier: {verifier_expr}")
        # Insert verification log template
        cur.execute(
            "INSERT INTO verifications (step_id, verifier_expr, status) VALUES (?, ?, 'RUNNING')",
            (step_id, verifier_expr)
        )
        verif_id = cur.lastrowid
        conn.commit()
        
        # Prepare evaluation environment
        eval_globals = {
            'check_file_exists': verifiers.check_file_exists,
            'check_file_size': verifiers.check_file_size,
            'check_python_test': verifiers.check_python_test,
            'check_image_corrupted': verifiers.check_image_corrupted,
            'check_layout_overlaps': verifiers.check_layout_overlaps,
            'check_python_syntax': verifiers.check_python_syntax,
            'os': os,
            'sys': sys
        }
        
        v_ok = False
        v_log = ""
        try:
            # Capturing print statements from verifiers
            import io
            old_stdout = sys.stdout
            captured_out = io.StringIO()
            sys.stdout = captured_out
            
            result = eval(verifier_expr, eval_globals)
            v_ok = bool(result)
            
            sys.stdout = old_stdout
            v_log = captured_out.getvalue()
            print(v_log)
        except Exception as e:
            if 'old_stdout' in locals() and sys.stdout != old_stdout:
                sys.stdout = old_stdout
            v_ok = False
            v_log = f"Exception evaluating expression: {e}"
            print(f"[-] Verification Error: {v_log}")
            
        cur.execute(
            "UPDATE verifications SET status = 'COMPLETED', result = ?, log = ?, verified_at = ? WHERE id = ?",
            ("PASS" if v_ok else "FAIL", v_log, datetime.now().isoformat(), verif_id)
        )
        
        if not v_ok:
            cur.execute("UPDATE steps SET status = 'FAILED' WHERE id = ?", (step_id,))
            cur.execute("UPDATE tasks SET status = 'BLOCKED' WHERE id = ?", (task_id,))
            conn.commit()
            conn.close()
            print(f"[-] Verification FAILED. Task {task_id} is now BLOCKED.")
            return False
        else:
            print(f"[+] Verification PASSED.")
            
    # Check if there are more steps
    cur.execute("SELECT COUNT(*) FROM steps WHERE task_id = ? AND status = 'PENDING'", (task_id,))
    remaining = cur.fetchone()[0]
    if remaining == 0:
        cur.execute("UPDATE tasks SET status = 'COMPLETED' WHERE id = ?", (task_id,))
        print(f"[+] All steps successfully completed. Task {task_id} is now COMPLETED.")
    else:
        # Reset task status to RUNNING in case it was previously blocked
        cur.execute("UPDATE tasks SET status = 'RUNNING' WHERE id = ?", (task_id,))
        print(f"[*] Step {step_order} completed. {remaining} step(s) remaining.")
        
    conn.commit()
    conn.close()
    return True

def update_step(task_id, step_order, command, verifier_expr):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM steps WHERE task_id = ? AND step_order = ?", (task_id, step_order))
    row = cur.fetchone()
    if row:
        step_id = row[0]
        cur.execute("DELETE FROM verifications WHERE step_id = ?", (step_id,))
    cur.execute(
        "UPDATE steps SET command = ?, verifier_expr = ?, status = 'PENDING' WHERE task_id = ? AND step_order = ?",
        (command, verifier_expr, task_id, step_order)
    )
    conn.commit()
    conn.close()
    print(f"[*] Step {step_order} of Task {task_id} updated. Status reset to PENDING and old test logs cleared.")

def print_status_dashboard(task_id):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("SELECT title, description, status, created_at FROM tasks WHERE id = ?", (task_id,))
    task_row = cur.fetchone()
    if not task_row:
        print(f"Task {task_id} not found.")
        conn.close()
        return
        
    title, desc, status, created = task_row
    
    print("\n" + "="*60)
    print(f" AGENT EXECUTION ENGINE (AEE) DASHBOARD")
    print("="*60)
    print(f"Task ID:     {task_id}")
    print(f"Title:       {title}")
    print(f"Description: {desc}")
    
    status_emoji = "🟢 COMPLETED" if status == "COMPLETED" else "🔴 BLOCKED" if status == "BLOCKED" else "🔵 RUNNING"
    print(f"Status:      {status_emoji}")
    print(f"Created At:  {created}")
    print("-"*60)
    print(f"Steps Tracker:")
    print("-"*60)
    
    cur.execute(
        "SELECT id, step_order, command, verifier_expr, status, run_at FROM steps WHERE task_id = ? ORDER BY step_order ASC",
        (task_id,)
    )
    steps = cur.fetchall()
    for sid, s_order, cmd, v_expr, s_status, s_run in steps:
        step_emoji = "✅" if s_status == "COMPLETED" else "❌" if s_status == "FAILED" else "⏳" if s_status == "PENDING" else "🔄"
        print(f"{step_emoji} Step {s_order}: {cmd}")
        if v_expr:
            cur.execute("SELECT result, log FROM verifications WHERE step_id = ? ORDER BY id DESC LIMIT 1", (sid,))
            v_row = cur.fetchone()
            if v_row:
                v_res, v_log = v_row
                v_emoji = "✔️ PASS" if v_res == "PASS" else "⚠️ FAIL"
                print(f"   └─ Test: {v_expr} -> {v_emoji}")
            else:
                print(f"   └─ Test: {v_expr} -> ⏳ PENDING")
        print(f"   └─ Status: {s_status} (Run: {s_run})")
    print("="*60 + "\n")
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python harness.py <command> [args...]")
        print("Commands:")
        print("  init")
        print("  start-task <title> <desc>")
        print("  add-step <task_id> <step_order> <command> <verifier_expr>")
        print("  update-step <task_id> <step_order> <command> <verifier_expr>")
        print("  run-next <task_id>")
        print("  status <task_id>")
        sys.exit(1)
        
    cmd = sys.argv[1].lower()
    if cmd == "init":
        init_db()
        print("[+] Engine database initialized.")
    elif cmd == "start-task" and len(sys.argv) >= 4:
        start_task(sys.argv[2], " ".join(sys.argv[3:]))
    elif cmd == "add-step" and len(sys.argv) >= 6:
        add_step(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5])
    elif cmd == "update-step" and len(sys.argv) >= 6:
        update_step(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5])
    elif cmd == "run-next" and len(sys.argv) >= 3:
        run_next_step(int(sys.argv[2]))
    elif cmd == "status" and len(sys.argv) >= 3:
        print_status_dashboard(int(sys.argv[2]))
    else:
        print("[-] Invalid arguments.")
