"""Ön kontrol: üç servisin de gerçekten çalıştığını doğrular (pipeline öncesi)."""
import os

from dotenv import load_dotenv

load_dotenv()

ok = True

# 1) Supabase
try:
    from src import storage
    rows = storage.get_client().table("user_settings").select("id").execute().data
    print(f"[OK] Supabase baglantisi calisiyor (user_settings: {len(rows)} satir)")
except Exception as e:
    ok = False
    print(f"[HATA] Supabase: {e}")

# 2) Gemini
try:
    from google import genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    r = client.models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        contents="Sadece 'test tamam' yaz, baska hicbir sey yazma.",
    )
    print(f"[OK] Gemini calisiyor, cevap: {r.text.strip()[:40]}")
except Exception as e:
    ok = False
    print(f"[HATA] Gemini: {str(e)[:300]}")

# 3) Telegram
try:
    from src import notifier
    notifier.send("✅ Kurulum testi başarılı — Finansal Asistanın hazır!", tur="test")
    print("[OK] Telegram mesaji gonderildi (telefonunu kontrol et)")
except Exception as e:
    ok = False
    print(f"[HATA] Telegram: {str(e)[:300]}")

print("\nSONUC:", "HEPSI HAZIR - pipeline calistirilabilir" if ok else "eksikler var, yukaridaki hatalara bak")
