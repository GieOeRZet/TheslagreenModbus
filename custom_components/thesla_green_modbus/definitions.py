"""Definicje wszystkich encji (rejestry z Twojego YAML-a + wyliczane)."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    Platform,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfVolumeFlowRate,
)

DP = tuple[str, int]  # (rodzaj: input|holding|coil, adres)

DP_T_CZERPNIA: DP = ("input", 16)
DP_T_NAWIEW: DP = ("input", 17)
DP_T_WYWIEW: DP = ("input", 18)
DP_T_FPX: DP = ("input", 19)
DP_T_PCB: DP = ("input", 22)
DP_FLOW_SUPPLY: DP = ("holding", 256)
DP_FLOW_EXTRACT: DP = ("holding", 257)
DP_BYPASS_ACT: DP = ("coil", 9)
DP_RUN_CONFIRM: DP = ("coil", 11)


@dataclass(frozen=True, kw_only=True)
class EntityDef:
    key: str
    name: str
    platform: Platform
    dp: DP | None = None
    interval: int = 30
    needs: tuple[DP, ...] = ()
    scale: float = 1.0
    precision: int | None = None
    unit: str | None = None
    device_class: object | None = None
    state_class: object | None = None
    category: EntityCategory | None = None
    icon: str | None = None
    on_value: int | None = None
    off_value: int | None = None
    fn: str | None = None
    nan: int | None = None  # wartość oznaczająca "brak odczytu" (np. 0x8000 dla temperatur)
    # select
    options: tuple[tuple[int, str], ...] = ()  # (wartość rejestru, etykieta) – to, co można ustawić
    all_labels: tuple[tuple[int, str], ...] = ()  # pełny opis wartości (do atrybutu)
    # number
    min_value: float = 0
    max_value: float = 100
    step: float = 1
    side_writes: tuple[tuple[DP, int], ...] = ()  # dodatkowe zapisy po zapisie głównym


def _temp(key, name, addr, interval):
    return EntityDef(
        key=key, name=name, platform=Platform.SENSOR, dp=("input", addr),
        interval=interval, scale=0.1, precision=1, unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT,
        nan=-32768,  # 0x8000 = brak odczytu czujnika (dokumentacja AirPack4)
    )


def _flow(key, name, addr):
    return EntityDef(
        key=key, name=name, platform=Platform.SENSOR, dp=("holding", addr), interval=5,
        unit=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE, state_class=SensorStateClass.MEASUREMENT,
        nan=-1,  # 65535 = system CF nieaktywny (odczyt jako int16 = -1)
    )


def _raw(key, name, addr, interval, **kw):
    return EntityDef(key=key, name=name, platform=Platform.SENSOR, dp=("holding", addr), interval=interval, **kw)


def _diag(key, name, addr):
    return _raw(key, name, addr, 63, category=EntityCategory.DIAGNOSTIC)


def _switch(key, name, addr, interval, on, off):
    return EntityDef(
        key=key, name=name, platform=Platform.SWITCH, dp=("holding", addr),
        interval=interval, on_value=on, off_value=off,
    )


_EFF_NEEDS = (DP_BYPASS_ACT, DP_T_CZERPNIA, DP_T_NAWIEW, DP_T_WYWIEW)
_POWER_NEEDS = (DP_BYPASS_ACT, DP_T_CZERPNIA, DP_T_NAWIEW, DP_FLOW_SUPPLY)

ENTITY_DEFS: list[EntityDef] = [
    # --- temperatury ---
    _temp("temp_czerpnia", "Temperatura czerpnia", 16, 29),
    _temp("temp_nawiew", "Temperatura nawiew", 17, 29),
    _temp("temp_wywiew", "Temperatura wywiew", 18, 29),
    _temp("temp_fpx", "Temperatura za FPX", 19, 29),
    _temp("temp_pcb", "Temperatura PCB", 22, 59),
    # --- przepływy ---
    _flow("strumien_nawiew", "Strumień nawiew", 256),
    _flow("strumien_wywiew", "Strumień wywiew", 257),
    # --- stany / tryby ---
    _raw("lato_zima", "Lato zima", 4209, 11),
    _raw("bypass", "Bypass", 4320, 11),
    _raw("tryb_pracy", "Tryb pracy", 4208, 6),
    _raw("specjalny_tryb_pracy", "Specjalny tryb pracy", 4224, 6),
    _raw("speedmanual", "Speedmanual", 4210, 5, unit=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT),
    _raw("fpx_flaga", "FPX flaga", 4192, 29),
    _raw("fpx_tryb", "FPX tryb", 4198, 29),
    # --- alarmy (diagnostyka) ---
    _diag("alarm", "Alarm", 8192),
    _diag("error", "Error", 8193),
    _diag("fpx_zabezpieczenie_termiczne", "FPX zabezpieczenie termiczne", 8208),
    _diag("awaria_went_nawiewu", "Awaria wentylatora nawiewu", 8222),
    _diag("awaria_went_wywiewu", "Awaria wentylatora wywiewu", 8223),
    _diag("awaria_cf_nawiewu", "Awaria CF nawiewu", 8330),
    _diag("awaria_cf_wywiewu", "Awaria CF wywiewu", 8331),
    _diag("wymiana_filtrow", "Wymiana filtrów", 8444),
    # --- binary sensory ---
    EntityDef(key="silownik_bypassu", name="Siłownik bypassu", platform=Platform.BINARY_SENSOR, dp=DP_BYPASS_ACT, interval=10),
    EntityDef(
        key="potwierdzenie_pracy", name="Potwierdzenie pracy", platform=Platform.BINARY_SENSOR,
        dp=DP_RUN_CONFIRM, interval=5, device_class=BinarySensorDeviceClass.RUNNING,
    ),
    # --- przełączniki ---
    _switch("sw_on_off", "ON/OFF", 4387, 5, 1, 0),
    _switch("sw_bypass", "Bypass", 4320, 7, 0, 1),
    _switch("sw_mode", "Mode", 4208, 5, 0, 1),
    _switch("sw_zima", "Zima", 4209, 7, 1, 0),
    # --- listy wyboru ---
    EntityDef(
        key="sel_special_mode", name="Tryb specjalny", platform=Platform.SELECT,
        dp=("holding", 4224), interval=6, icon="mdi:home-switch-outline",
        options=((0, "Normalny"), (2, "Kominek"), (7, "Wietrzenie"), (10, "Otwarte okna"), (11, "Pusty dom")),
        all_labels=(
            (0, "Normalny"), (1, "Okap"), (2, "Kominek"), (3, "Wietrzenie (przełącznik dzwonkowy)"),
            (4, "Wietrzenie (przełącznik ON/OFF)"), (5, "Wietrzenie (higrostat)"),
            (6, "Wietrzenie (czujnik jakości powietrza)"), (7, "Wietrzenie"),
            (8, "Wietrzenie (harmonogram auto)"), (9, "Wietrzenie (harmonogram manual)"),
            (10, "Otwarte okna"), (11, "Pusty dom"),
        ),
    ),
    EntityDef(
        key="sel_season", name="Sezon", platform=Platform.SELECT, dp=("holding", 4209),
        interval=11, icon="mdi:sun-snowflake", options=((0, "Lato"), (1, "Zima")),
    ),
    EntityDef(
        key="sel_mode", name="Tryb auto manual", platform=Platform.SELECT, dp=("holding", 4208),
        interval=6, icon="mdi:cog-sync", options=((0, "Automatyczny"), (1, "Manualny")),
        all_labels=((0, "Automatyczny"), (1, "Manualny"), (2, "Chwilowy")),
    ),
    # --- suwak ---
    EntityDef(
        key="num_manual_speed", name="Intensywność manualna", platform=Platform.NUMBER,
        dp=("holding", 4210), interval=5, unit=PERCENTAGE, icon="mdi:fan",
        min_value=10, max_value=100, step=1,
        needs=(("holding", 4208),), side_writes=((("holding", 4208), 1),),
    ),
    # --- wyliczane ---
    EntityDef(
        key="sprawnosc", name="Sprawność", platform=Platform.SENSOR, fn="efficiency",
        needs=_EFF_NEEDS, unit=PERCENTAGE, precision=1, icon="mdi:percent",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EntityDef(
        key="wysterowanie_nawiew", name="Wysterowanie nawiew", platform=Platform.SENSOR,
        fn="flow_supply_pct", needs=(DP_FLOW_SUPPLY,), unit=PERCENTAGE, precision=1,
        icon="mdi:percent", state_class=SensorStateClass.MEASUREMENT,
    ),
    EntityDef(
        key="wysterowanie_wywiew", name="Wysterowanie wywiew", platform=Platform.SENSOR,
        fn="flow_extract_pct", needs=(DP_FLOW_EXTRACT,), unit=PERCENTAGE, precision=1,
        icon="mdi:percent", state_class=SensorStateClass.MEASUREMENT,
    ),
    EntityDef(
        key="odzyskana_moc", name="Odzyskana moc", platform=Platform.SENSOR, fn="power",
        needs=_POWER_NEEDS, unit=UnitOfPower.WATT, precision=0,
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
    ),
    EntityDef(
        key="odzyskana_energia", name="Odzyskana energia", platform=Platform.SENSOR, fn="energy",
        needs=_POWER_NEEDS, unit=UnitOfEnergy.KILO_WATT_HOUR, precision=3,
        device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # liczniki okresowe (odpowiednik utility_meter: godzina / dzień / miesiąc / rok)
    *(
        EntityDef(
            key=f"odzysk_energii_{period}", name=f"Odzysk energii {label}", platform=Platform.SENSOR,
            fn=f"meter_{period}", needs=_POWER_NEEDS, unit=UnitOfEnergy.KILO_WATT_HOUR, precision=3,
            device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL,
        )
        for period, label in (("godzina", "godzina"), ("dzien", "dzień"), ("miesiac", "miesiąc"), ("rok", "rok"))
    ),
]

ENTITIES_BY_KEY: dict[str, EntityDef] = {d.key: d for d in ENTITY_DEFS}
ALL_KEYS: list[str] = [d.key for d in ENTITY_DEFS]

PLATFORM_LABEL = {
    Platform.SENSOR: "sensor",
    Platform.BINARY_SENSOR: "binary sensor",
    Platform.SWITCH: "przełącznik",
    Platform.SELECT: "lista wyboru",
    Platform.NUMBER: "suwak",
}

# domyślny (najkrótszy) interwał dla każdego rejestru – używany dla zależności encji wyliczanych
DP_INTERVAL: dict[DP, int] = {}
for _d in ENTITY_DEFS:
    if _d.dp is not None:
        DP_INTERVAL[_d.dp] = min(DP_INTERVAL.get(_d.dp, 10**9), _d.interval)


def build_plan(defs: list[EntityDef]) -> dict[DP, int]:
    """Które rejestry odpytywać i jak często – tylko to, co potrzebne włączonym encjom."""
    plan: dict[DP, int] = {}
    for d in defs:
        if d.dp is not None:
            plan[d.dp] = min(plan.get(d.dp, 10**9), d.interval)
        for dp in d.needs:
            plan[dp] = min(plan.get(dp, 10**9), DP_INTERVAL[dp])
    return plan
