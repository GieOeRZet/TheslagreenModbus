# Changelog

## v1.0.1

- Poprawka wydania: wersja w `manifest.json` zgodna z tagiem wydania (tag `V1.0.0` wskazywał commit z wersją 0.2.0). Brak zmian w działaniu integracji.

## v1.0.0

- Pierwsze wydanie stabilne: scala funkcje z v0.1.0 i v0.2.0 (konfigurator w UI, rekonfiguracja, liczniki okresowe odzysku energii).
- Poprawione klucze tłumaczeń (zgodność z hassfest), dodana ikona integracji.
- Walidacja HACS i Hassfest w CI przechodzi.

## v0.2.0

- Dodano liczniki okresowe odzysku energii (godzina, dzień, miesiąc, rok) w miejsce `utility_meter` z YAML-a.
- Całkowanie energii przeniesione do koordynatora (jedno źródło dla sensora energii i liczników).

## v0.1.0

Pierwsze wydanie integracji **Thesla Green ModBUS** dla Home Assistant (instalacja przez HACS jako Custom repository).

### Funkcje
- Konfigurator w UI: nazwa, typ połączenia (Modbus TCP, RTU over TCP, UDP, Serial RTU/ASCII), parametry, wybór encji.
- Wszystkie encje w jednym urządzeniu; nazwa urządzenia jest prefiksem nazw i ID encji.
- Rekonfiguracja: typ połączenia, adres, port, Unit ID, parametry linii, zaznaczanie i odznaczanie encji.
- Odpytywane są tylko rejestry potrzebne włączonym encjom, każdy we własnym interwale.
- Listy wyboru: tryb specjalny, sezon, tryb auto/manual.
- Suwak intensywności manualnej 10–100 %, który przełącza centralę na tryb manualny.
- Wartości wyliczane: sprawność, wysterowanie, odzyskana moc i energia (kWh, panel Energia).

### Uwagi
- Wymagany Home Assistant 2024.11 lub nowszy.
- Wersja wstępna, jeszcze nieprzetestowana szeroko na urządzeniach. Zgłaszaj błędy w Issues z logiem debug.
