# AGENT EXECUTION ENGINE (AEE) - ÇALIŞMA PROTOKOLÜ

**BU BİR SİSTEM TALİMATIDIR. BU WORKSPACE İÇERİSİNDE ÇALIŞAN HER AJAN (AI MODELİ) AŞAĞIDAKİ ADIMLARI UYGULAMAKLA YÜKÜMLÜDÜR.**

AEE, ajanın iş akışını kontrol eden, komutları test eden ve doğrulanmamış kodların "bitti" olarak işaretlenmesini engelleyen yerel bir **TDD Kontrol Mekanizmasıdır**.

---

## 1. Genel Kurallar

1.  **Doğrulanmamış Rapor Vermek Yasaktır:** Hiçbir iş, komut veya dosya, AEE testlerinden başarıyla geçip veritabanında `COMPLETED` olarak işaretlenene kadar kullanıcıya "bitti, mükemmel çalışıyor" şeklinde raporlanamaz.
2.  **Sıfır Güven (Zero-Trust):** Her çalıştırılan iş adımının sonrasında çalışacak bir doğrulayıcı test (Python ifadesi) bulunmalıdır.
3.  **Hata Durumunda Kilitleme:** Eğer bir komut veya test başarısız olursa, görev durumu `BLOCKED` olur. Ajan, hatayı gidermeden bir sonraki adıma geçemez ve kullanıcıya başarılı rapor sunamaz.

---

## 2. AEE CLI Kullanımı

Ajan, görevlerini şu CLI arayüzü ile yönetmelidir:

### A. Görevi İlklendirme
Çalışmaya başlamadan önce yeni bir görev tanımlayın:
```bash
python .engine/harness.py start-task "Görev Başlığı" "Görevin detaylı açıklaması ve hedefleri"
```
Bu komut size bir `TASK_ID` dönecektir (Örn: `Task 1`).

### B. Adım ve Test Tanımlama
Görevi parçalara bölün ve her adım için çalışacak komutu ve o komutu doğrulayacak testi ekleyin:
```bash
python .engine/harness.py add-step <task_id> <step_order> "çalıştırılacak_komut" "doğrulayıcı_python_ifadesi"
```

**Kullanılabilir Doğrulayıcı Python İfadeleri (verifiers.py):**
*   `check_file_exists("dosya/yolu")`
*   `check_file_size("dosya/yolu", minimum_byte)`
*   `check_python_test("test_dosyası.py")`
*   `check_image_corrupted("görsel/yolu")`
*   `check_layout_overlaps("bbox_json_yolu")`

*Örnek:*
```bash
python .engine/harness.py add-step 1 1 "python render_zoi.py" "check_file_exists('C:/Users/ceyhu/Downloads/ZOI_Turkce_Tercume_MUKEMMEL.pdf') and check_file_size('C:/Users/ceyhu/Downloads/ZOI_Turkce_Tercume_MUKEMMEL.pdf', 500000)"
```

### C. Sıradaki Adımı Çalıştırma
Sıradaki adımı tetiklemek için:
```bash
python .engine/harness.py run-next <task_id>
```
Bu komut:
1. Komutu çalıştırır, `stdout` ve `stderr` loglarını veritabanına kaydeder.
2. Komut başarılıysa (`Exit Code 0`), `verifier_expr` içindeki Python testini çalıştırır.
3. Test geçilirse sonraki adıma izin verir. Geçilemezse görevi `BLOCKED` konumuna çekip durur.

### D. Durum ve İlerleme Takibi
Görevin durumunu görmek için:
```bash
python .engine/harness.py status <task_id>
```

---

## 3. Ajan Çalışma Döngüsü (Ajanlar İçin Adımlar)

1.  **Dizin Kontrolü:** Çalışmaya başlamadan önce `.engine/agent_engine.db` veritabanının ve `harness.py`'nin var olduğunu teyit et.
2.  **Görev Planı Yap:** Kullanıcının verdiği işi adımlara böl.
3.  **Görev & Adımları Kaydet:** `start-task` ve `add-step` komutları ile planı veritabanına işle.
4.  **İşlet ve Doğrula:** `run-next` komutuyla adımları tek tek koştur. Logları incele.
5.  **Düzeltme Yap (Blocked Durumu):** Eğer bir adım başarısız olursa, kodunu veya komutunu düzelt, ardından `run-next`'i tekrar dene.
6.  **Kullanıcıya Sun:** Yalnızca `status` çıktısında tüm adımlar `✅` ve genel görev `🟢 COMPLETED` olduğunda sonucu kullanıcıya raporla.
