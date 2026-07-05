#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import sqlite3
import re
from datetime import datetime

ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
WORK_DIR = os.path.dirname(ENGINE_DIR) # CCCWorkscape
DB_PATH = os.path.join(ENGINE_DIR, "agent_engine.db")
MEMORY_DB_PATH = os.path.join(WORK_DIR, ".memory", "agent_memory.db")
def get_roadmap_path():
    possible_names = ["project.md", "ROADMAP.md", "tasks.md", "DEVAM.md"]
    for name in possible_names:
        p = os.path.join(WORK_DIR, name)
        if os.path.exists(p):
            return p, name
    return os.path.join(WORK_DIR, "project.md"), "project.md"

def parse_roadmap_tasks():
    tasks = []
    roadmap_path, _ = get_roadmap_path()
    if not os.path.exists(roadmap_path):
        return tasks
    try:
        with open(roadmap_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Match tasks under the target header (Turkish or English)
        match = re.search(r"## 🎯 (?:SONRAKİ GÖREVLER|NEXT TASKS|TASKS|ROADMAP).*?\n(.*?)(?:\n##|\Z)", content, re.IGNORECASE | re.DOTALL)
        if match:
            lines = match.group(1).strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith("- [ ]") or line.startswith("- [/]") or line.startswith("- [x]"):
                    status = "PENDING"
                    if "[/]" in line: status = "RUNNING"
                    elif "[x]" in line: status = "COMPLETED"
                    desc = line[5:].strip()
                    tasks.append((desc, status))
    except Exception as e:
        print(f"[-] Orchestrator: Error parsing roadmap file: {e}")
    return tasks

def load_memory_facts():
    facts = {}
    if not os.path.exists(MEMORY_DB_PATH):
        return facts
    try:
        conn = sqlite3.connect(MEMORY_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM facts")
        for k, v in cur.fetchall():
            facts[k] = v
        conn.close()
    except Exception as e:
        print(f"[-] Orchestrator: Error loading memory facts: {e}")
    return facts

def print_start_dashboard():
    print("\n" + "="*70)
    print(" ANTIGRIVITY TASK-FLOW ENGINE (ATFE) - START MENU")
    print("="*70)
    
    # 1. Parse Roadmap Tasks
    _, roadmap_name = get_roadmap_path()
    devam_tasks = parse_roadmap_tasks()
    print(f"🎯 Roadmap ({roadmap_name}) Next Tasks List:")
    if devam_tasks:
        for i, (desc, status) in enumerate(devam_tasks, 1):
            status_symbol = "⏳ PENDING" if status == "PENDING" else "🔄 RUNNING" if status == "RUNNING" else "✅ COMPLETED"
            print(f"  [{i}] {desc} ({status_symbol})")
    else:
        print(f"  (No pending tasks found in {roadmap_name} under tasks header.)")
        
    print("-"*70)
    
    # 2. Check Engine Tasks Status
    print("🗄️ AEE Database Active Tasks (agent_engine.db):")
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT id, title, status FROM tasks ORDER BY id DESC LIMIT 5")
            tasks = cur.fetchall()
            if tasks:
                for tid, title, status in tasks:
                    status_emoji = "🟢" if status == "COMPLETED" else "🔴" if status == "BLOCKED" else "🔵"
                    print(f"  Task ID {tid}: {status_emoji} {title} ({status})")
            else:
                print("  (No tasks registered in database.)")
            conn.close()
        except Exception as e:
            print(f"  [-] Database query error: {e}")
    else:
        print("  (AEE Database not created yet. Run 'harness.py init'.)")
        
    print("-"*70)
    print("💡 How would you like to proceed?")
    print("  1. Select one of the tasks above (e.g. 'python .engine/harness.py start-task <title> <desc>')")
    print("  2. Start a new independent task.")
    print("="*70 + "\n")

def find_protocol_file(name):
    name_lower = name.lower()
    for root, dirs, files in os.walk(WORK_DIR):
        # Skip hidden and cache folders to avoid performance issues
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('venv', 'env', 'node_modules', 'BACKUPS', '2026-Backup')]
        for f in files:
            if f.lower() == name_lower:
                return os.path.join(root, f)
    return None

def generate_brief(task_id, raw_desc):
    facts = load_memory_facts()
    print("\n" + "="*70)
    print(f" ATFE: PROMPT & BRIEF GENERATOR (Task ID: {task_id})")
    print("="*70)
    
    # Determine target context based on keywords
    context_tags = []
    warnings = []
    ips = []
    
    lower_desc = raw_desc.lower()
    if "kronos" in lower_desc:
        context_tags.append("KRONOS BOT (Live)")
        ips.append(facts.get("kronos_live_ip", "192.168.1.50"))
        warnings.append("APOLLO V10 ENFORCED: Sadece Kronos, Kronos PT ve RADAR aktiftir. Lazarus/Nexus decommissioned.")
        warnings.append("A-1 BTCUSDT Guard active.")
    if "flash" in lower_desc or "kronos pt" in lower_desc:
        context_tags.append("FLASH BOT (Kronos PT)")
        ips.append(facts.get("kronos_pt_ip", "192.168.1.51"))
        warnings.append("Kısmi otonom kapatma SSH key hatası nedeniyle kilitlenmiş olabilir. SSH publickey sorununu doğrula.")
    if "radar" in lower_desc:
        context_tags.append("RADAR MODEL")
        ips.append(facts.get("radar_ip", "192.168.1.52"))
        
    # Dynamic Protocol Mapping: checks if any word in the task description matches a markdown file in the workspace
    words = re.findall(r'\b\w+\b', lower_desc)
    for word in words:
        # Skip small words or standard keywords to avoid noise
        if len(word) < 3 or word in ('and', 'the', 'for', 'run', 'ssh', 'key', 'bot', 'run'):
            continue
        for ext in ['.md', '_protocol.md']:
            fn = word.lower() + ext
            proto_path = find_protocol_file(fn)
            if proto_path and os.path.exists(proto_path):
                tag = f"{word.upper()} PROTOCOL"
                if tag not in context_tags:
                    context_tags.append(tag)
                    try:
                        with open(proto_path, 'r', encoding='utf-8') as pf:
                            first_line = ""
                            for _ in range(15):
                                line = pf.readline().strip()
                                if line and not line.startswith('>') and not line.startswith('#'):
                                    first_line = line
                                    break
                            # If no plain line, get first heading
                            if not first_line:
                                pf.seek(0)
                                for line in pf:
                                    if line.startswith('#'):
                                        first_line = line.strip('# \t\n')
                                        break
                        if first_line:
                            warnings.append(f"Rules enforced from {os.path.basename(proto_path)}: {first_line}")
                    except Exception:
                        pass
                break
                    
    print(f"🔍 Alınan Görev:  {raw_desc}")
    print(f"🏷️ Tespit Edilen Bağlam: {', '.join(context_tags) if context_tags else 'GENEL GÖREV'}")
    
    if ips:
        print(f"🌐 Sunucu IP'leri: {', '.join(ips)}")
    print("-"*70)
    
    print("⚠️ Güvenlik ve Protokol Kuralları (Knowledge Engine):")
    if warnings:
        for w in warnings:
            print(f"  • {w}")
    else:
        print("  • Genel güvenlik kuralları geçerlidir (kodları lokale çekip doğrula, sunucuda vim/nano hotfix yapma).")
        
    print("-"*70)
    print("📝 AEE İçin Oluşturulan Sıfır-Hata Görev Adımları (TDD Prompt Template):")
    print("Aşağıdaki AEE adımlarını doğrudan ekleyerek çalışmaya başlayın:")
    print("-" * 70)
    
    # Generate generic proposed steps based on keywords
    if "ssh" in lower_desc or "key" in lower_desc:
        print(f"python .engine/harness.py add-step {task_id} 1 \"ping -c 3 {facts.get('kronos_pt_ip', '192.168.1.51')}\" \"check_file_exists('.engine/verifiers.py')\"")
        print(f"python .engine/harness.py add-step {task_id} 2 \"ssh -i ~/.ssh/id_rsa root@{facts.get('kronos_pt_ip', '192.168.1.51')} 'echo OK'\" \"check_file_exists('.engine/verifiers.py')\"")
    elif "deploy" in lower_desc or "run" in lower_desc:
        print(f"python .engine/harness.py add-step {task_id} 1 \"python deploy_fleet.py --dry-run\" \"check_file_exists('deploy_fleet.py')\"")
        print(f"python .engine/harness.py add-step {task_id} 2 \"python deploy_fleet.py\" \"check_file_size('deploy_status.json', 10)\"")
    else:
        # Default fallback template
        print(f"python .engine/harness.py add-step {task_id} 1 \"[Komut]\" \"[check_file_exists('dosya/yolu')]\"")
        print(f"python .engine/harness.py add-step {task_id} 2 \"[Kontrol Komutu]\" \"[check_file_size('dosya/yolu', 100)]\"")
        
    print("="*70 + "\n")

def find_modified_python_files(start_time_iso):
    modified_files = []
    try:
        # Normalize ISO timestamp for comparison
        # Python 3.11+ fromisoformat handles 'Z' and offsets correctly, but we sanitize
        ts_str = start_time_iso.replace('Z', '+00:00')
        start_dt = datetime.fromisoformat(ts_str)
    except Exception as e:
        print(f"  [-] Time parsing error: {e}")
        return modified_files
        
    for root, dirs, files in os.walk(WORK_DIR):
        # Exclude hidden folders, python environments, and scratch folders
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('venv', 'env', 'node_modules', 'scratch', 'BACKUPS', '2026-Backup')]
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                # Skip engine files
                if '.engine' in file_path or 'orchestrator.py' in file_path or 'harness.py' in file_path or 'verifiers.py' in file_path:
                    continue
                try:
                    mtime = os.path.getmtime(file_path)
                    file_dt = datetime.fromtimestamp(mtime)
                    # Convert file_dt to naive or offset-aware depending on start_dt
                    if start_dt.tzinfo is not None and file_dt.tzinfo is None:
                        # Make file_dt offset-aware (using local system timezone)
                        file_dt = file_dt.astimezone()
                    if file_dt > start_dt:
                        modified_files.append(file_path)
                except Exception:
                    pass
    return modified_files

def run_pre_delivery_check(task_id):
    print("\n" + "="*70)
    print(f" ATFE: PRE-DELIVERY CHECKER (Task ID: {task_id})")
    print("="*70)
    
    if not os.path.exists(DB_PATH):
        print("[-] AEE Veritabanı bulunamadı. Kontrol yapılamıyor.")
        return False
        
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. Check Task Status
    cur.execute("SELECT status, title, created_at FROM tasks WHERE id = ?", (task_id,))
    task_row = cur.fetchone()
    if not task_row:
        print(f"[-] Task {task_id} veritabanında bulunamadı.")
        conn.close()
        return False
        
    task_status, task_title, task_created = task_row
    
    # 2. Check Steps Status
    cur.execute("SELECT step_order, command, status FROM steps WHERE task_id = ? ORDER BY step_order ASC", (task_id,))
    steps = cur.fetchall()
    
    print(f"Görev: {task_title}")
    print(f"AEE Durumu: {task_status}")
    print("-"*70)
    
    failed_steps = []
    pending_steps = []
    
    for s_order, s_cmd, s_status in steps:
        print(f"  Step {s_order}: {s_cmd} -> {s_status}")
        if s_status == "FAILED":
            failed_steps.append(s_order)
        elif s_status == "PENDING" or s_status == "RUNNING":
            pending_steps.append(s_order)
            
    print("-"*70)
    
    if failed_steps:
        print(f"🔴 RED (No-Go): {len(failed_steps)} adet adım BAŞARISIZ olmuş! Görevi tamamlayamazsınız.")
        print(f"   Lütfen şu adımları düzeltip tekrar çalıştırın: {failed_steps}")
        conn.close()
        return False
        
    if pending_steps:
        print(f"🔴 RED (No-Go): {len(pending_steps)} adet adım henüz TAMAMLANMAMIŞ! Görevi tamamlayamazsınız.")
        print(f"   Çalıştırılması beklenen adımlar: {pending_steps}")
        conn.close()
        return False
        
    if task_status != "COMPLETED":
        print(f"🔴 RED (No-Go): Görev durumu COMPLETED değil (Mevcut: {task_status}).")
        conn.close()
        return False
        
    # 3. Dynamic syntax check for modified workspace files
    print("🔍 Aktif Seanstaki Değişen Dosyalar ve Sözdizimi (Syntax) Kontrolü:")
    try:
        modified_files = find_modified_python_files(task_created)
        syntax_errors = 0
        if modified_files:
            import verifiers
            for file_path in modified_files:
                # Get relative path for print
                rel_path = os.path.relpath(file_path, WORK_DIR)
                print(f"  • Denetleniyor: {rel_path}")
                if not verifiers.check_python_syntax(file_path):
                    syntax_errors += 1
            if syntax_errors > 0:
                print(f"🔴 RED (No-Go): Değiştirilen Python dosyalarında {syntax_errors} adet sözdizimi (syntax) hatası tespit edildi!")
                conn.close()
                return False
        else:
            print("  (Seansta değiştirilen Python dosyası bulunamadı.)")
    except Exception as e:
        print(f"  [-] Sözdizimi kontrolü sırasında hata: {e}")
        
    print("-"*70)
    print("🟢 GREEN LIGHT (Go): Tüm AEE testleri ve sözdizimi kontrolleri başarıyla geçildi!")
    print("   Görevi güvenle kullanıcıya rapor edebilirsiniz.")
    print("="*70 + "\n")
    conn.close()
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py <command> [args...]")
        print("Commands:")
        print("  start")
        print("  define <task_id> <raw_description>")
        print("  check <task_id>")
        sys.exit(1)
        
    cmd = sys.argv[1].lower()
    if cmd == "start":
        print_start_dashboard()
    elif cmd == "define" and len(sys.argv) >= 4:
        generate_brief(int(sys.argv[2]), " ".join(sys.argv[3:]))
    elif cmd == "check" and len(sys.argv) >= 3:
        run_pre_delivery_check(int(sys.argv[2]))
    else:
        print("[-] Invalid arguments.")
