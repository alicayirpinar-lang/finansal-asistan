"""v1 pipeline: haber topla -> filtrele -> finansal beyin -> kaydet -> bildir.

Çalıştırma: python main.py
"""
import os
import sys
import traceback
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from config import (
    SYMBOLS, CORE_SYMBOLS, MAX_THESES_PER_RUN, TRIAGE_BATCH_SIZE, TRIAGE_KUME_BASI_MAKS,
    IKINCI_DERECE_MIN_KAYNAK, IZLEME_TTL_GUN,
)
from src import analytics, collector, filter as f1, brain, kap, prices, retro, storage, notifier


def _teknik_teyit(symbol, market, yon):
    """Faz 12 B füzyon şartı: sembolde `yon` ile aynı yönde herhangi bir
    teknik kurulum var mı (kanıtlı şartı yok — A'dan daha hafif bar, sadece
    grafik desteği arıyoruz)."""
    analiz = analytics.sembol_analiz(symbol, market)
    if not analiz:
        return False
    return any(s["yon"] == yon for s in analiz.get("kurulumlar", []))


def _ikinci_derece_isle(clusters):
    """Faz 12 B: eşleşmeyen+çok-kaynaklı kümelerden ikinci derece (dolaylı)
    bağ arar (TEK toplu Gemini çağrısı). Füzyon şartını geçenleri teze
    (kaynak=ikinci_derece) yollar, geçemeyenleri izleme listesine ekler
    (tez değil, bildirim yok — teknik kurulunca terfi eder). Döner: teze
    hazır event listesi (triage atlar, zaten iki kapıdan geçti)."""
    promoted = []
    adaylar = f1.unmatched_clusters(clusters, IKINCI_DERECE_MIN_KAYNAK)
    if not (adaylar and not brain.too_many_attempts_this_run()):
        return promoted
    for b in brain.ikinci_derece(adaylar):
        no = b.get("haber_no")
        sembol = (b.get("sembol") or "").upper()
        yon = b.get("yon")
        if not (isinstance(no, int) and 1 <= no <= len(adaylar)
                and sembol in CORE_SYMBOLS and yon in ("yukselis", "dusus")):
            continue  # AI kapalı listeye uymadı / eksik alan: halüsinasyon savunması
        cluster = adaylar[no - 1]
        rep = cluster["rep"]
        market = CORE_SYMBOLS[sembol]["market"]
        print(f'  ikinci derece bağ: [{sembol}] {rep["title"][:70]} — {b.get("mekanizma", "")[:80]}')
        if _teknik_teyit(sembol, market, yon):
            promoted.append({
                "cluster_id": f"ikinci-{no}", "symbol": sembol, "market": market,
                "category": "ikinci_derece", "relevance_score": 0.5,
                "priority_lane": "normal_kuyruk", "title": rep["title"],
                "summary": b.get("mekanizma", ""), "url": rep.get("url"),
                "source": "ikinci_derece", "source_count": len(cluster["members"]),
                "published_at": rep["published_at"], "kaynak": "ikinci_derece",
            })
            print("    -> teknik teyit VAR, teze gidiyor")
        else:
            storage.insert_izleme(sembol, market, yon, b.get("mekanizma", ""),
                                  b.get("guven", "orta"), rep["title"], rep.get("url"))
            print("    -> teknik teyit yok, izleme listesine eklendi")
    return promoted


def _izleme_kontrol():
    """Bekleyen ikinci derece bağları kontrol eder: teknik teyit geldiyse
    teze terfi ettirir (kaynak=ikinci_derece), süresi dolduysa düşürür.
    Döner: teze hazır event listesi (triage atlar)."""
    promoted = []
    for row in storage.pending_izleme():
        created = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        yas_gun = (datetime.now(timezone.utc) - created).days
        if _teknik_teyit(row["symbol"], row["market"], row["yon"]):
            promoted.append({
                "cluster_id": f'izleme-{row["id"]}', "symbol": row["symbol"],
                "market": row["market"], "category": "ikinci_derece",
                "relevance_score": 0.5, "priority_lane": "normal_kuyruk",
                "title": row["kaynak_baslik"] or row["symbol"], "summary": row["mekanizma"],
                "url": row.get("kaynak_url"), "source": "ikinci_derece", "source_count": 1,
                "published_at": datetime.now(timezone.utc), "kaynak": "ikinci_derece",
            })
            storage.close_izleme(row["id"], "teyit_edildi")
            print(f'  izleme teyit: [{row["symbol"]}] gecikmeli teknik teyit geldi, teze gidiyor')
        elif yas_gun >= IZLEME_TTL_GUN:
            storage.close_izleme(row["id"], "suresi_doldu")
    return promoted


def _kritik_ozet(aday_sayisi, triage_elenen, sonuclar):
    """Kritik hızlı yol tetiklediyse ve tez çıkmadıysa kullanıcıya nedenini söyle.
    ('tez gelebilir' bildirimi askıda kalmasın — dürüst kapanış, plan bölüm 11)."""
    if aday_sayisi == 0:
        sebep = ("Kritik başlık takip listesindeki hiçbir sembole/temaya "
                 "bağlanamadı (genel veya jeopolitik haber).")
    else:
        satirlar = [f"{aday_sayisi} olay adayı incelendi."]
        if triage_elenen:
            satirlar.append(f"Ön eleme {triage_elenen} adayı eledi (rutin / yeni bilgi yok).")
        satirlar += sonuclar[:5]
        sebep = "\n".join(satirlar)
    notifier.send("ℹ️ Kritik haber analizi tamamlandı — tez çıkmadı.\n"
                  + sebep +
                  "\nBu normaldir: her kritik haber yatırılabilir bir tez üretmez.",
                  tur="kritik_ozet")


def run():
    kritik_tetik = os.environ.get("TETIK_KAYNAK", "") == "kritik"

    print("Semboller senkronlanıyor...")
    storage.ensure_symbols(SYMBOLS)

    print("Haberler toplanıyor...")
    items, errors = collector.collect_news()
    print(f"  {len(items)} haber, {len(errors)} kaynak hatası")
    for name, err in errors:
        print(f"  ! {name}: {err[:100]}")
        storage.log_error(f"collector:{name}", "RSS kaynağı hatası", err)

    print("KAP bildirimleri çekiliyor...")
    kap_disclosures, kap_error = kap.collect_kap()
    if kap_error:
        print(f"  ! KAP: {kap_error[:100]}")
        storage.log_error("kap.py", "KAP bildirimleri çekilemedi", kap_error)
    else:
        print(f"  {len(kap_disclosures)} KAP bildirimi (ODA)")

    if not items and not kap_disclosures:
        print("Hiç haber/bildirim yok, çıkılıyor.")
        if kritik_tetik:
            _kritik_ozet(0, 0, [])
        return

    clusters = f1.dedup(items) if items else []
    print(f"  dedup: {len(items)} haber -> {len(clusters)} küme")

    # Geriye dönük tez talepleri (dashboard köprüsü) — kullanıcı talebi
    # olduğu için normal olaylardan ÖNCE, kota önceliğiyle işlenir.
    try:
        retro.process_queue(clusters)
    except Exception:
        print("Geriye dönük tez kuyruğu hatası (pipeline devam ediyor):")
        traceback.print_exc(limit=2)
        storage.log_error("main.py:retro", "Geriye dönük tez kuyruğu hatası", traceback.format_exc())

    portfolio_syms = storage.open_portfolio_symbols()
    events = f1.build_events(clusters, portfolio_syms)
    kap_events = f1.build_kap_events(kap_disclosures, portfolio_syms) if kap_disclosures else []
    if kap_events:
        print(f"  {len(kap_events)} KAP olayı (rutin bildirimler elendi)")
        events = sorted(events + kap_events,
                        key=lambda e: (e["priority_lane"] != "kritik", -e["relevance_score"]))
    print(f"  {len(events)} skorlu olay adayı")

    # Faz 12 B — ikinci derece akıl yürütme: eşleşmeyen+çok-kaynaklı kümeler
    # + bekleyen izleme listesi. Füzyon şartını geçenler doğrudan teze gider
    # (triage atlar, zaten iki kapıdan geçti); geçemeyenler izlemede kalır.
    promoted_b = []
    try:
        promoted_b += _ikinci_derece_isle(clusters)
        promoted_b += _izleme_kontrol()
    except Exception:
        print("İkinci derece akıl yürütme hatası (pipeline devam ediyor, migration 006 bekliyor olabilir):")
        traceback.print_exc(limit=2)
        storage.log_error("main.py:ikinci_derece", "İkinci derece akıl yürütme hatası", traceback.format_exc())

    # Triage: normal kuyruk toplu ön elemeden geçer (1 Gemini çağrısı, tez
    # kalitesi fazı); kritik hızlı yol elemesiz geçer.
    aday_sayisi = len(events) + len(promoted_b)
    triage_elenen = 0
    kritik = [e for e in events if e["priority_lane"] == "kritik"]
    normal_havuzu = [e for e in events if e["priority_lane"] != "kritik"]
    normal = f1.select_diverse(normal_havuzu, TRIAGE_BATCH_SIZE, TRIAGE_KUME_BASI_MAKS)
    if normal and not brain.too_many_attempts_this_run():
        normal, triage_elenen = brain.triage(normal)
        if triage_elenen:
            print(f"  triage: {triage_elenen} olay elendi, {len(normal)} kaldı")
    events = kritik + normal + promoted_b

    settings = storage.get_settings()
    rejimler = {}  # pazar başına bir kez hesapla

    def market_rejim(market):
        if market not in rejimler:
            rejimler[market] = analytics.rejim(market)
            print(f'  rejim [{market}]: {rejimler[market]["rejim"]}')
        return rejimler[market]

    produced = 0
    sonuclar = []     # kritik kapanış özeti için kısa sonuç satırları
    per_cluster = {}  # aynı haber kümesinden en fazla 2 tez (kopya tez freni)
    for event in events:
        if produced >= MAX_THESES_PER_RUN:
            break
        if per_cluster.get(event["cluster_id"], 0) >= 2:
            continue
        # Devre kesici: bu çalıştırmada Gemini tamamen ölüyse (22 Temmuz 2026
        # ikinci kesinti) kalan olaylarda dakikalarca ölü servise vurmak yerine
        # dur — 30 dk sonraki koşu (fresh process) sıfırdan dener.
        if brain.circuit_acik_mi():
            print("Gemini bu çalıştırmada tamamen başarısız — kalan olaylar 30 dk sonraki koşuya bırakılıyor.")
            break
        if brain.too_many_attempts_this_run():
            mesaj = (f"bu çalıştırmada {brain.MAX_ATTEMPTS_PER_RUN}+ Gemini denemesi yapıldı — "
                     f"normalin çok üstünde, muhtemel bir döngü hatası. Kalan olaylar bırakılıyor.")
            print(mesaj)
            storage.log_error("main.py:too_many_attempts", mesaj, seviye="kritik")
            break
        if storage.recent_thesis_exists(event["symbol"]):
            continue  # aynı sembolde 48 saat içinde tez var: mükerrer önleme
        try:
            print(f'\n[{event["symbol"]}] {event["title"][:80]}...')
            # Analitik motor: grafik okumasını KOD yapar, AI yorumlar (faz 11)
            analiz = analytics.sembol_analiz(event["symbol"], event["market"])
            rejim_bilgi = market_rejim(event["market"])
            teknik = analytics.prompt_blok(analiz, rejim_bilgi)
            kat_tip, kat_guclu = analytics.katalizor_tipi(
                event["title"] + " " + event.get("summary", ""))

            draft = brain.draft_chain(event, teknik)
            if draft.get("tez_yok"):
                print(f'  -> taslak beyni reddetti: {draft.get("neden", "?")[:100]}')
                sonuclar.append(f'{event["symbol"]}: tez kurulamadı — '
                                f'{draft.get("neden", "?")[:90]}')
                continue
            redteam = brain.red_team(event, draft, teknik)
            final, tier, status, neden = brain.merge(event, draft, redteam)

            # Engel oranı: yıllık eşdeğer risksiz alternatifi yenmiyorsa tez açılmaz
            engel = analytics.engel_kontrol(draft, event["market"], settings)
            if status == "acik" and engel["gecemedi"]:
                status, tier, neden = "taslak", "gozlem", engel["neden"]

            # Büyük fırsat şeridi — saf kod: güçlü katalizör × kurulum × rejim
            buyuk = status == "acik" and analytics.buyuk_firsat_mu(
                kat_guclu, analiz, rejim_bilgi, draft.get("yon"))

            # Analitik özet tezle birlikte saklanır (izlenebilirlik)
            draft["teknik_gorunum"] = {
                "katalizor": kat_tip, "buyuk_firsat": buyuk,
                "rejim": rejim_bilgi.get("rejim"),
                "kurulumlar": (analiz or {}).get("kurulumlar", []),
                "tepki": (analiz or {}).get("tepki"),
                "engel": engel.get("metin", ""),
            }

            # Referans fiyat + stop (2×ATR) — tez takibi bunlarla çalışır (plan bölüm 7)
            entry_ref = ((analiz or {}).get("vektor") or {}).get("fiyat") or \
                prices.current_price(event["symbol"], event["market"])
            if entry_ref and status == "acik":
                atr = prices.atr14(event["symbol"], event["market"])
                if atr:
                    sign = 1 if draft["yon"] == "yukselis" else -1
                    inv = redteam.setdefault("gecersiz_kilma_kosulu", {})
                    inv["stop_fiyat"] = round(entry_ref - sign * 2 * atr, 2)
            thesis = storage.insert_thesis(event, draft, redteam, final, tier, status,
                                           entry_price_ref=entry_ref, note=neden,
                                           kaynak=event.get("kaynak", "haber"))
            if status == "acik":
                produced += 1
                per_cluster[event["cluster_id"]] = per_cluster.get(event["cluster_id"], 0) + 1
            print(f"  -> güven={final}, katman={tier}, durum={status}"
                  + (f" ({neden})" if neden else "") + (" 🚀 BÜYÜK FIRSAT" if buyuk else ""))
            if status != "acik":
                sonuclar.append(f'{event["symbol"]}: {status}'
                                + (f' — {neden[:90]}' if neden else ""))
            if status == "acik" and tier in ("kritik", "orta"):
                # Düşüş tezi eyleme dönüşmez (açığa satış yok): sembol portföyde
                # değilse bildirim gitmez — tez sitede ve karnede kalır.
                if draft.get("yon") == "dusus" and event["symbol"] not in portfolio_syms:
                    print("  -> düşüş tezi, sembol portföyde değil: bildirim yok (sitede görünür)")
                else:
                    msg = notifier.format_thesis(event, draft, redteam, final, tier)
                    if draft.get("yon") == "dusus":
                        msg = "🛡️ PORTFÖY KORUMA — elindeki hisse için düşüş tezi\n" + msg
                    if buyuk:
                        msg = "🚀 BÜYÜK FIRSAT ADAYI — güçlü katalizör + teknik kurulum + rejim uyumu\n" + msg
                    if engel.get("metin"):
                        msg += f'\n{engel["metin"]}'
                    notifier.send(msg, tur=f"yeni_tez_{tier}")
                    print("  -> Telegram bildirimi gönderildi")
        except Exception:
            print(f'  ! {event["symbol"]} işlenirken hata (pipeline devam ediyor):')
            traceback.print_exc(limit=2)
            storage.log_error("main.py:event", f'{event["symbol"]} işlenirken hata', traceback.format_exc())

    print(f"\nBitti: {produced} açık tez. Bugünkü Gemini kullanımı: "
          f"{storage.gemini_basarili_calls_today()} başarılı "
          f"({storage.gemini_calls_today()} toplam deneme)")
    if kritik_tetik and produced == 0:
        _kritik_ozet(aday_sayisi, triage_elenen, sonuclar)
    brain.sistemik_hata_kontrolu("main.py (tarama.yml)")


if __name__ == "__main__":
    missing = [k for k in ("GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN",
                           "TELEGRAM_CHAT_ID", "SUPABASE_URL", "SUPABASE_KEY")
               if not os.environ.get(k)]
    if missing:
        print("Eksik .env değişkenleri:", ", ".join(missing))
        print(".env.example dosyasını .env olarak kopyalayıp doldur.")
        sys.exit(1)
    run()
