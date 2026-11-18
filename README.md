# Thesla Green ModBUS – integracja Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Validate](https://github.com/GieOeRZet/TheslagreenModbus/actions/workflows/validate.yml/badge.svg)](https://github.com/GieOeRZet/TheslagreenModbus/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/GieOeRZet/TheslagreenModbus)](https://github.com/GieOeRZet/TheslagreenModbus/releases)

Integracja do sterowania i monitorowania rekuperatora (testowana na dokumentacji **AirPack 4**) przez **Modbus**.
Zamiast kilkudziesięciu luźnych encji z pliku YAML dostajesz **jedno urządzenie** z uporządkowanymi encjami,
konfigurację z poziomu interfejsu i możliwość wyłączenia encji, których nie potrzebujesz
(ich rejestry nie są wtedy w ogóle odpytywane).

> Projekt nieoficjalny, niezwiązany z producentem urządzenia. Używasz na własną odpowiedzialność.
> Zapis do rejestrów zmienia ustawienia rekuperatora.

## Funkcje

- Konfigurator w UI: nazwa, typ połączenia, parametry, wybór encji.
- Typy połączenia: **Modbus TCP**, **Modbus RTU over TCP**, **Modbus UDP**, **Serial** (RTU / ASCII).
- Wszystkie encje w jednym urządzeniu; nazwa urządzenia jest prefiksem nazw i ID encji
  (np. nazwa `Rekuperator` → `sensor.rekuperator_temperatura_czerpnia`).
- Rekonfiguracja bez usuwania integracji: zmiana typu połączenia, adresu, portu, Unit ID, parametrów linii
  oraz zaznaczanie i odznaczanie encji (odznaczone są usuwane i nie obciążają magistrali).
- Każdy rejestr ma własny interwał odpytywania; odpytywane są tylko te, które potrzebują włączone encje.
- Suwaki z polem tekstowym dla timeoutu, opóźnienia, przerwy między zapytaniami i Unit ID.
- Lista wyboru trybu specjalnego, sezonu i trybu auto/manual jako osobne encje.
- Suwak intensywności manualnej, który sam przełącza centralę na tryb manualny.

## Instalacja przez HACS

1. HACS → menu ⋮ → **Custom repositories**.
2. Dodaj `https://github.com/GieOeRZet/TheslagreenModbus`, kategoria **Integration**.
3. Znajdź **Thesla Green ModBUS**, pobierz i zrestartuj Home Assistant.
4. **Ustawienia → Urządzenia i usługi → Dodaj integrację → Thesla Green ModBUS**.

[![Otwórz w HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=GieOeRZet&repository=TheslagreenModbus&category=integration)

Ręcznie: skopiuj katalog `custom_components/thesla_green_modbus` do `/config/custom_components/`.

Wymagany Home Assistant **2024.11** lub nowszy (rekonfiguracja z poziomu UI).

## Konfiguracja

| Krok | Co podajesz |
|---|---|
| 1 | Nazwa urządzenia i typ połączenia |
| 2 | Parametry połączenia (zależne od typu, patrz niżej) |
| 3 | Lista encji (domyślnie wszystkie zaznaczone) |

Przy „Dalej" w kroku 2 integracja próbuje odczytać jeden rejestr, żeby sprawdzić połączenie i Unit ID.

### Parametry

| Parametr | Typ połączenia | Domyślnie | Opis |
|---|---|---|---|
| Adres IP / host | tcp, rtuovertcp, udp | `192.168.0.11` | Adres urządzenia lub bramki |
| Port | tcp, rtuovertcp, udp | `502` | |
| Port szeregowy | serial | pierwszy wykryty | Można wpisać własną ścieżkę |
| Baudrate, bity danych, parzystość, bity stopu, RTU/ASCII | serial | 9600, 8, E, 1, RTU | |
| Timeout | wszystkie | 5 s | Czas oczekiwania na odpowiedź |
| Opóźnienie po połączeniu | wszystkie | 2 s | Część urządzeń potrzebuje 1–2 s po nawiązaniu połączenia |
| Przerwa między zapytaniami | wszystkie | 0 ms (30 ms dla serial) | Przydaje się przy wolnych bramkach RS-485 |
| Unit ID (slave) | wszystkie | `9` | 1–247 |

Który typ wybrać:

- **TCP** – urządzenie ma własny interfejs Modbus TCP albo bramka tłumaczy TCP ↔ RTU.
- **RTU over TCP** – serwer portu szeregowego lub bramka w trybie przezroczystym (ten sam typ co `rtuovertcp` w YAML).
- **UDP** – rzadko używane.
- **Serial** – adapter USB–RS-485 podłączony do Home Assistant.

## Encje

| Rodzaj | Encje |
|---|---|
| Sensory | temperatury (czerpnia, nawiew, wywiew, za FPX, PCB), strumień nawiew i wywiew, lato/zima, bypass, tryb pracy, tryb specjalny, FPX (flaga, tryb) |
| Wyliczane | sprawność, wysterowanie nawiewu i wywiewu (%), odzyskana moc (W), odzyskana energia (kWh, do panelu Energia) |
| Diagnostyka | alarmy, błędy, zabezpieczenie termiczne FPX, awarie wentylatorów i CF, wymiana filtrów |
| Binary sensory | siłownik bypassu, potwierdzenie pracy |
| Przełączniki | ON/OFF, bypass, mode, zima |
| Listy wyboru | tryb specjalny, sezon, tryb auto/manual |
| Suwak | intensywność manualna |

### Tryb specjalny, sezon, auto/manual

- **Tryb specjalny** (rejestr 4224): Normalny, Kominek, Wietrzenie, Otwarte okna, Pusty dom. Gdy aktywny jest tryb
  uruchomiony z zewnątrz (okap, czujnik, harmonogram), lista nie ma zaznaczonej opcji,
  a atrybut `aktualny_stan` podaje jego nazwę.
- **Sezon** (4209): Lato / Zima.
- **Tryb auto/manual** (4208): Automatyczny / Manualny. Tryb „Chwilowy" jest tylko odczytywany.
- **Intensywność manualna** (4210): suwak 10–100 %. Ruszenie suwaka zapisuje nastawę i przełącza centralę na tryb
  manualny. Wybranie „Automatyczny" w liście trybów przywraca pracę wg harmonogramu.

### Wartości wyliczane

- **Sprawność** = (Tnawiew − Tczerpnia) / (Twywiew − Tczerpnia) × 100 %, a przy otwartym bypassie 0 %.
- **Odzyskana moc** = |Tnawiew − Tczerpnia| × przepływ nawiewu × 1200 / 3600 [W], a przy otwartym bypassie 0 W.
- **Odzyskana energia** całkuje moc w czasie i przywraca wartość po restarcie.
- Wysterowanie liczone jest względem 240 m³/h.

Temperatura `0x8000` (brak czujnika) i przepływ `65535` (nieaktywny CF) są pokazywane jako „niedostępny".

## Przykład: karta z trybami

```yaml
type: custom:button-card
entity: select.rekuperator_tryb_specjalny
name: Pusty dom
state:
  - value: Pusty dom
    color: var(--primary-color)
tap_action:
  action: call-service
  service: select.select_option
  target:
    entity_id: select.rekuperator_tryb_specjalny
  data:
    option: Pusty dom
```

## Migracja z YAML

1. Usuń z `configuration.yaml` hub `modbus:` rekuperatora oraz zależne `template:` i `sensor: integration`.
2. Usuń stare encje i zrestartuj Home Assistant (inaczej bramka będzie odpytywana podwójnie, a nowe encje dostaną końcówkę `_2`).
3. Dodaj integrację. Użyj tej samej nazwy, jeśli chcesz zachować podobne ID encji.
4. Karty i automatyzacje zamieniające `modbus.write_register` przepnij na usługi `select.select_option`,
   `number.set_value` i `switch.turn_on/off`.

Liczniki `utility_meter` (godzina, doba, miesiąc, rok) możesz zostawić w YAML-u z nowym sensorem
`sensor.<nazwa>_odzyskana_energia` jako źródłem.

## Rozwiązywanie problemów

Debug w `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.thesla_green_modbus: debug
    pymodbus: debug
```

- **„Połączenie działa, ale urządzenie nie odpowiada"** – sprawdź Unit ID, typ połączenia i parametry linii.
- **`received pdu without a corresponding request`** w logu pymodbus – zwykle drugi klient na tej samej bramce
  (np. stary hub YAML) albo zbyt krótka przerwa między zapytaniami. Usuń drugiego klienta lub ustaw 30–50 ms.
- **Wiele bramek Modbus rozsyła odpowiedź do wszystkich klientów** – nie łącz się z jedną bramką z kilku miejsc naraz.

## Zgłaszanie błędów

Dołącz log debug i krótki opis urządzenia: [Issues](https://github.com/GieOeRZet/TheslagreenModbus/issues).

## Licencja

MIT
