# Antigravity Geliştirici Deneyimi (DX) Analizi ve AEE/ATFE Plugin Mimarisi

Bu belge, ağır kodlama (code-heavy) yapan profesyonel yazılım geliştiricilerin ihtiyaçları doğrultusunda Google Antigravity platformunun UX/DX (Kullanıcı ve Geliştirici Deneyimi) analizini sunmakta ve geliştirdiğimiz **AEE/ATFE (Agent Execution Engine / Task-Flow Engine)** sisteminin Antigravity platformuna entegre edilebilir bir **Plugin (Eklenti)** olarak nasıl yapılandırılacağını açıklamaktadır.

---

## 1. Antigravity UX/DX Analizi ve Eksik Alanlar

Antigravity, geleneksel "kod tamamlama" (copilot) araçlarının ötesine geçerek ajan-tabanlı (agentic) yazılım süreçlerini IDE içerisine getiren devrimsel bir platformdur. Ancak ağır kod yazan ve otonom deploy süreçleri yöneten geliştiriciler için kritik bazı **DX eksiklikleri** bulunmaktadır:

| Mevcut Durum / Özellik | Ağır Kodlama Yapan Geliştirici İhtiyacı | Antigravity'deki Eksiklik / Geliştirme Alanı |
|---|---|---|
| **Ajan Serbestliği** | Ajanın hedefe giden yolda güvenli ve deterministik sınırlar içinde kalması. | **Doğrulama Boşluğu:** Ajan, kod yazıp terminal komutu koşturduktan sonra çıktının doğruluğunu (görsel çakışma, mantık hataları, test patlamaları) kontrol etmeden görevi bitti raporlayabiliyor (Halüsinasyon / Hatalı Güven). |
| **Hafıza ve Bağlam (Context)** | Ajanın geçmiş seanslardaki IP'leri, SSH key durumlarını ve kritik yasakları (örn. "Lazarus decommissioned") unutmama ihtiyacı. | **Oturum Demansı (Dementia):** Her yeni ajan oturumu sıfır hafıza ile başlar. Kullanıcı her defasında aynı uyarıları ve credentials bilgilerini tekrar girmek zorunda kalır. |
| **UX Görünürlüğü** | Ajanın arka planda ne yaptığını (trace), hangi komutların çalıştığını adım adım görebilmek. | **Kapsülleme Karanlığı:** Ajanın terminalde yürüttüğü işlemler ve verifier çıktıları genellikle gizli kalır veya karmaşık chat geçmişinde kaybolur. |
| **Multi-Agent Orkestrasyonu** | Bir ajanın kod yazarken (Executer), başka bir ajanın onu bağımsızca denetlemesi (Checker/Auditor). | **Tekil Ajan Kısıtı:** Varsayılan akış tek bir LLM seansı etrafında döner. Rol ayrışması (Separation of Concerns) ve otonom kalite kapıları (Quality Gates) yoktur. |

---

## 2. Loop Mühendisliği ve Agentic AI Teorik Araştırması (Literature Synthesis)

Mükemmel bir ajan kontrol döngüsü tasarlamak için güncel akademik literatürdeki şu 3 ana yaklaşımdan yararlanıyoruz:

### A. TDD-Governance (Test-Driven Development Yönetimi)
*   *Kaynak:* *TDD Governance for Multi-Agent Code Generation via Prompt Engineering* (arXiv:2604.26615)
*   *Teori:* Bir ajanın ürettiği kodun kalitesi, LLM'in kendi iç sesine (introspection) bırakılamaz. Süreç, kodun çalıştırılıp test edilmesi ve çıktının doğrulanması şeklinde **deterministik bir dış kontrol halkası** ile yönetilmelidir. AEE'deki `harness.py` ve `verifiers.py` bu felsefeyi uygulamaktadır.

### B. AgentDevel / Release Engineering (Sürüm Mühendisliği)
*   *Kaynak:* *Reframing Self-Evolving LLM Agents as Release Engineering* (arXiv:2603.11186)
*   *Teori:* Ajanın hataları düzeltme süreci (Self-Healing), rastgele denemeler yerine "Implementation-Blind Critic" (uygulamayı bilmeyen, sadece çıktıyı test eden denetçi) tarafından analiz edilmeli ve regresyon testleri ile kilitlenmelidir. Bizim tasarladığımız **Checker Mode** (`orchestrator.py check`) bu prensibe dayanır.

### C. State-Graph tabanlı Çoklu Ajan Döngüleri (Multi-Agent State Graphs)
*   *Kaynak:* LangGraph & *Agentic Programming for Agent Harness* (arXiv:2605.18747)
*   *Teori:* Ajanın durumu bir yönlü graf (DAG) olarak modellenmeli, her durum geçişinde (Planning -> Writing -> Testing -> Auditing) kesin geçiş kriterleri ve kilit durumlar (BLOCKED) tanımlanmalıdır.

---

## 3. Mimarinin Mükemmelleştirilmesi: ATFE Plugin Yapısı

Geliştirdiğimiz sistemi Antigravity'ye entegre edilebilir bir **Plugin** olarak tasarlıyoruz.

### Plugin Paket Yapısı (`agy-atfe-plugin.tar.gz`)
Antigravity plugin standartlarına uygun olarak klasör yapısı şu şekilde olacaktır:

```text
agy-atfe-plugin/
├── package.json              # Eklenti metaverileri, slash commands ve dependencies tanımları
├── manifest.yaml             # Eklenti yetki, araç (tool) ve MCP sunucu tanımları
├── src/
│   ├── orchestrator.py       # Ana iş akışı ve state kontrolörü
│   ├── harness.py            # SQLite loglama ve TDD harness
│   └── verifiers.py          # Görsel, dosya ve syntax doğrulayıcılar
└── prompts/
    ├── system_hook.md        # Ajanı AEE kullanmaya zorlayan sistem promptu enjeksiyonu
    └── start_template.md     # START komutu çıktısı şablonu
```

### manifest.yaml Örneği (Antigravity Entegrasyonu)
Eklentinin Antigravity tarafından bir araç paketi (toolset) olarak tanınması için manifest dosyası:

```yaml
name: "antigravity-task-flow-engine"
version: "1.0.0"
description: "TDD Governance and memory logs wrapper for Google Antigravity coding agents"
entry_point: "src/orchestrator.py"
tools:
  - name: "atfe_start"
    description: "Parses DEVAM.md and prints available tasks menu"
    command: "python src/orchestrator.py start"
  - name: "atfe_define"
    description: "Generates TDD brief and proposed steps for a task"
    command: "python src/orchestrator.py define {task_id} {raw_desc}"
  - name: "atfe_check"
    description: "Executes final verification and output checklist validation"
    command: "python src/orchestrator.py check {task_id}"
rules:
  pre_execution_hook: "src/orchestrator.py pre-hook"
  post_execution_hook: "src/orchestrator.py check {task_id}"
```

---

## 4. Antigravity IDE/App İçine Entegrasyon Yöntemleri

### A. Yerel SDK ve CLI Entegrasyonu (Local Plugin)
Geliştirdiğimiz paketi kendi bilgisayarınızdaki Antigravity CLI veya Desktop uygulamasına yüklemek için:
1.  Paketi tar.gz olarak sıkıştırın:
    ```bash
    tar -czvf agy-atfe-plugin.tar.gz -C c:\Users\ceyhu\Documents\antigravity\CCCWorkscape\.engine .
    ```
2.  Antigravity CLI kullanarak yerel olarak kurun:
    ```bash
    agy plugin install --local ./agy-atfe-plugin.tar.gz
    ```
3.  **Antigravity IDE (VS Code Fork) Entegrasyonu:**
    IDE ayarlarında `Settings > Customizations > Build with Google Plugins` bölümüne giderek `c:\Users\ceyhu\Documents\antigravity\CCCWorkscape\.engine` klasörünü "Development Plugin Path" olarak tanımlayın. Böylece her yeni terminal açıldığında veya ajan tetiklendiğinde ATFE otomatik olarak aktif olacaktır.

### B. GitHub Üzerinden Dağıtım (Open-Source/Community Contribution)
Bunu topluluğa açmak ve Google'a önermek için:
1.  GitHub üzerinde `google-antigravity-atfe` adında bir repository oluşturun.
2.  Kodları ve manifest yapısını push edin.
3.  Kullanıcılar eklentiyi doğrudan GitHub URL'i ile kurabilirler:
    ```bash
    agy plugin install github.com/ceyhun/google-antigravity-atfe
    ```

---

## 5. İlerleme Planı (Step-by-Step Implementation & Test Roadmap)

Acele etmeden, adım adım ve %100 doğrulamayla ilerlemek için şu yol haritasını uygulayacağız:

### Aşama 1: manifest.yaml ve package.json Altyapısının Kurulması
*   `.engine` klasörü altında Antigravity standartlarında manifest dosyalarını oluşturacağız.
*   *Doğrulama:* `harness.py` CLI'ının manifest üzerinden sorunsuz çağrılabildiğini test edeceğiz.

### Aşama 2: Çoklu Ajan ve "Checker" Rollerinin Simülasyonu
*   Ajanın iş yaparken aynı zamanda kendi kodunu denetleyen bağımsız bir "Auditor/Checker" rolüne bölünmesini sağlayacak Python log denetleyicilerini kodlayacağız.
*   *Doğrulama:* Hatalı kod yazıldığında Checker'ın bunu ajanın yüzüne vurup durdurduğunu test edeceğiz.

### Aşama 3: GitHub Deposu Hazırlığı ve Dokümantasyon
*   Tüm süreci temiz bir depoya dönüştürerek push edilmeye hazır hale getireceğiz.
