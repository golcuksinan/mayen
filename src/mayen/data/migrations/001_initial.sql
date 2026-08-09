-- Şema v1 — §16'daki dokuz veri grubunun tamamı.
--
-- Zaman alanları: ISO-8601 UTC metni ('2026-08-09T14:03:11Z'). Sözlükbilimsel sıralama
-- kronolojik sıralamayla aynı, gözle okunabiliyor ve SQLite'ın date fonksiyonları
-- doğrudan çalışıyor. Epoch tamsayısı hata ayıklarken her seferinde çeviri istiyor.
--
-- Alan sözlüğü (kademe gibi) Türkçe, aksansız; şema adları İngilizce. Gerekçe CLAUDE.md'de.

-- §11.2: özetleme "son açılıştan bu yana özetlenmemiş konuşma" üzerinde çalışır; o soru
-- ancak açılışların kaydı varsa cevaplanabilir. Temiz kapanış `stopped_at` yazar, çökme
-- yazmaz — NULL kalan satır çökmüş bir çalışmadır.
CREATE TABLE boot_records (
    id         INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    stopped_at TEXT,
    version    TEXT NOT NULL
) STRICT;

-- §10.2. TANINMAYAN kademesi burada yok: profili olmayan kişinin satırı da yoktur.
CREATE TABLE people (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    tier       TEXT NOT NULL CHECK (tier IN ('SAHIP', 'KAYITLI_KISI', 'BEKLEYEN')),
    phone      TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
) STRICT;

-- §10.5. Birleştirilmiş gömü; ham örnekler saklanmaz. `model_version` olmadan, model
-- değiştiğinde eski gömülerle yeni gömüler sessizce karşılaştırılır ve skor anlamsızlaşır.
CREATE TABLE voice_profiles (
    id            INTEGER PRIMARY KEY,
    person_id     INTEGER NOT NULL REFERENCES people (id) ON DELETE CASCADE,
    embedding     BLOB NOT NULL,
    sample_count  INTEGER NOT NULL,
    model_version TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
) STRICT;

CREATE UNIQUE INDEX voice_profiles_person ON voice_profiles (person_id);

-- §11.1. Oturum sınırı yok; geçmiş tek sürekli akış, sıra `id`.
--
-- `token_count` NULL olabilir: sayı LLM sunucusunun sayacından gelir, tahmin edilmez
-- (Kural 10). Henüz sorulmadıysa alan boş kalır — sıfır yazmak tahmin etmektir.
--
-- `summary_id` NULL = henüz özetlenmedi. Sert kırpma satırı silmez (§11.1); yalnızca
-- pencerenin dışında bırakır, ve bu alan boşta kalan özetleme işinin iş listesidir.
CREATE TABLE messages (
    id          INTEGER PRIMARY KEY,
    turn_id     TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool')),
    person_id   INTEGER REFERENCES people (id) ON DELETE SET NULL,
    content     TEXT NOT NULL,
    token_count INTEGER,
    summary_id  INTEGER REFERENCES summaries (id) ON DELETE SET NULL,
    created_at  TEXT NOT NULL
) STRICT;

CREATE INDEX messages_unsummarized ON messages (id) WHERE summary_id IS NULL;
CREATE INDEX messages_turn ON messages (turn_id);

-- §11.2. Bir özet, kapsadığı mesaj aralığıyla birlikte durur; aralık olmadan hangi
-- konuşmanın yerine geçtiği bilinemez.
CREATE TABLE summaries (
    id           INTEGER PRIMARY KEY,
    from_message INTEGER NOT NULL,
    to_message   INTEGER NOT NULL,
    content      TEXT NOT NULL,
    token_count  INTEGER,
    created_at   TEXT NOT NULL
) STRICT;

-- §11.3. Tek ortak havuz, kişi etiketli. `person_id` NULL = tanınmayan birinden geldi.
-- `source_message_id` olgunun nereden çıkarıldığını gösterir; mesaj silinse de olgu kalır.
CREATE TABLE facts (
    id                INTEGER PRIMARY KEY,
    person_id         INTEGER REFERENCES people (id) ON DELETE SET NULL,
    content           TEXT NOT NULL,
    source_message_id INTEGER REFERENCES messages (id) ON DELETE SET NULL,
    created_at        TEXT NOT NULL
) STRICT;

CREATE INDEX facts_person ON facts (person_id);

CREATE TABLE notes (
    id         INTEGER PRIMARY KEY,
    body       TEXT NOT NULL,
    person_id  INTEGER REFERENCES people (id) ON DELETE SET NULL,
    created_at TEXT NOT NULL
) STRICT;

-- §19.8: kaynak depodaki program dosyası, DB'ye açılışta yüklenir. Buradan yazan bir tool
-- yok; yükleyici dönemi silip yeniden yazar, o yüzden `term` üzerinde çalışır.
-- `day_of_week` 1=Pazartesi … 7=Pazar (ISO-8601).
CREATE TABLE course_sessions (
    id          INTEGER PRIMARY KEY,
    term        TEXT NOT NULL,
    course_code TEXT NOT NULL,
    title       TEXT NOT NULL,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    start_time  TEXT NOT NULL,
    end_time    TEXT NOT NULL,
    location    TEXT
) STRICT;

CREATE INDEX course_sessions_term_day ON course_sessions (term, day_of_week);

-- §12. `payload` görev tipine göre değişen JSON; şemayı görev tipi başına tabloya bölmek
-- tek tip görev varken spekülatif.
--
-- Durumlar alan sözlüğü olduğu için Türkçe. DUSURULDU = uygulama kapalıyken vakti geçmiş
-- ve tolerans dışında kalmış görev; §12 bunun kaydedilmesini şart koşuyor, `outcome`
-- sebebi taşır.
CREATE TABLE scheduled_tasks (
    id         INTEGER PRIMARY KEY,
    kind       TEXT NOT NULL,
    payload    TEXT NOT NULL,
    due_at     TEXT NOT NULL,
    status     TEXT NOT NULL CHECK (status IN ('BEKLIYOR', 'CALISTI', 'IPTAL', 'DUSURULDU')),
    outcome    TEXT,
    person_id  INTEGER REFERENCES people (id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    settled_at TEXT
) STRICT;

CREATE INDEX scheduled_tasks_due ON scheduled_tasks (due_at) WHERE status = 'BEKLIYOR';

-- §15. Tur başına bir satır. İz mesaj gövdelerini kopyalamaz (P3 notu, §15 kayıt hacmi
-- kuralı); gövde `messages`'ta, burada yalnızca ona referans var.
CREATE TABLE turn_traces (
    turn_id    TEXT PRIMARY KEY,
    device_id  TEXT NOT NULL,
    person_id  INTEGER REFERENCES people (id) ON DELETE SET NULL,
    started_at TEXT NOT NULL,
    ended_at   TEXT,
    outcome    TEXT
) STRICT;

-- Aşama sayısı tur başına değişken (kaç tool çalıştıysa o kadar satır), bu yüzden ayrı
-- tablo. `name` sabit bir küme değil: tool aşamaları tool adını taşır.
CREATE TABLE turn_trace_stages (
    id          INTEGER PRIMARY KEY,
    turn_id     TEXT NOT NULL REFERENCES turn_traces (turn_id) ON DELETE CASCADE,
    seq         INTEGER NOT NULL,
    name        TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    duration_ms INTEGER,
    detail      TEXT
) STRICT;

CREATE UNIQUE INDEX turn_trace_stages_order ON turn_trace_stages (turn_id, seq);
