"""Bu API anahtarıyla kullanılabilir modelleri listele ve flash modellerini dene."""
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

print("Kullanilabilir modeller (generateContent destekleyenler):")
flash_models = []
for m in client.models.list():
    actions = getattr(m, "supported_actions", None) or []
    if "generateContent" in actions or not actions:
        name = m.name.replace("models/", "")
        print(f"  {name}")
        if "flash" in name.lower():
            flash_models.append(name)

print("\nFlash modelleri deneniyor (ilk calisan kazanir):")
for name in flash_models[:8]:
    try:
        r = client.models.generate_content(model=name, contents="Sadece 'ok' yaz.")
        print(f"  [CALISIYOR] {name} -> {r.text.strip()[:20]}")
        break
    except Exception as e:
        msg = str(e)
        kind = "kota yok (429)" if "429" in msg else msg[:80]
        print(f"  [olmadi] {name}: {kind}")
