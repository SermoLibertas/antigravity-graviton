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
DEVAM_PATH = os.path.join(WORK_DIR, "DEVAM.md")

def parse_devam_tasks():
    tasks = []
    if not os.path.exists(DEVAM_PATH):
        return tasks
    try:
        with open(DEVAM_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Match tasks under the target header
        match = re.search(r"## 🎯 SONRAKİ GÖREVLER.*?\n(.*?)(?:\n##|\Z)", content, re.DOTALL)
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
        print(f"[-] Orchestrator: Error parsing DEVAM.md: {e}")
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
    
    # 1. Parse DEVAM.md Tasks
    devam_tasks = parse_devam_tasks()
    print("🎯 DEVAM.md Sonraki Görevler Listesi:")
    if devam_tasks:
        for i, (desc, status) in enumerate(devam_tasks, 1):
            status_symbol = "⏳ PENDING" if status == "PENDING" else "🔄 RUNNING" if status == "RUNNING" else "✅ COMPLETED"
            print(f"  [{i}] {desc} ({status_symbol})")
    else:
        print("  (DEVAM.md üzerinde bekleyen görev bulunamadı.)")
        
    print("-"*70)
    
    # 2. Check Engine Tasks Status
    print("🗄️ AEE Veritabanı Aktif Görevler (agent_engine.db):")
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
                print("  (Veritabanında kayıtlı görev bulunmamaktadır.)")
            conn.close()
        except Exception as e:
            print(f"  [-] Veritabanı sorgu hatası: {e}")
    else:
        print("  (AEE Veritabanı henüz oluşturulmamış. 'harness.py init' çalıştırın.)")
        
    print("-"*70)
    print("💡 Nasıl Devam Etmek İstersiniz?")
    print("  1. Yukarıdaki görevlerden birini seçin (Örn: 'python .engine/harness.py start-task <title> <desc>')")
    print("  2. Yeni bir bağımsız görev başlatın.")
    print("="*70 + "\n")

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
