"""KAP (Kamuyu Aydınlatma Platformu) entegrasyonu — faz 12 fırsat kaynağı #4.

Resmi API yok; `kap-client` (PyPI) KAP'ın herkese açık, kimlik doğrulaması
gerektirmeyen JSON uç noktasını sarmalıyor. Bulk sorgu: `mkkMemberOidList`
boş bırakılırsa TEK istekte TÜM şirketlerin bildirimleri gelir — ticker→OID
çözümlemesi (600 şirket için 600 istek) gerekmez. Canlı doğrulandı (21 Temmuz
2026): 7 günlük pencere ~1260 satır, `disclosureClass=ODA` filtresiyle ~900.
"""
from datetime import date, timedelta, timezone
from zoneinfo import ZoneInfo

from kap_client._client import KapHttpClient
from kap_client._endpoints import MEMBER_DISCLOSURE_QUERY_URL, DisclosureRow, MemberDisclosureQueryBody
from kap_client._models import Disclosure

QUERY_GUN = 2  # geriye dönük kaç gün sorgulanır (kota: ~2000 satır/sorgu tavanı, kısa pencere güvenli)
_TR_TZ = ZoneInfo("Europe/Istanbul")  # KAP saatleri TR yerel (Türkiye DST uygulamıyor)


def collect_kap():
    """Son QUERY_GUN gündeki ODA (Özel Durum Açıklaması) sınıfı bildirimleri
    tek istekte çeker. RSS koleksiyoncusuyla aynı hata toleransı: ağ hatası
    pipeline'ı durdurmaz, boş liste + hata metni döner."""
    today = date.today()
    body = MemberDisclosureQueryBody(
        fromDate=(today - timedelta(days=QUERY_GUN)).isoformat(),
        toDate=today.isoformat(),
        mkkMemberOidList=[],
        disclosureClass="ODA",
    )
    try:
        with KapHttpClient() as http:
            rows = http.post(MEMBER_DISCLOSURE_QUERY_URL, body)
    except Exception as e:
        return [], str(e)
    disclosures = []
    for r in rows:
        try:
            disclosures.append(Disclosure.from_row(DisclosureRow.model_validate(r)))
        except Exception:
            continue  # tek satır bozuksa listenin geri kalanı kaybolmasın
    return disclosures, None


def publish_datetime_utc(d):
    """KAP'ın naive TR yerel saatini UTC'ye çevirir (tazelik skoru için şart)."""
    return d.publish_datetime.replace(tzinfo=_TR_TZ).astimezone(timezone.utc)
