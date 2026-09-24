# vocab.geo — географический словарь представления

Словарный пакет `packs/vocab/` ([DECISION-0139](../../../spec/decisions/0139-lens-type-driven-views.ru.md) §5).
Юрисдикции нет, источника права нет, правил нет: словарь ничего не выводит.

## Типы

| Тип | Смысл |
|---|---|
| `Region` | административно-территориальная единица первого уровня |
| `Station` | станция наблюдений с географическим положением; предметный пакет объявляет подтип через алиас |
| `Point` | запись `{lat, lon}` WGS84 — объявление будущего API: литерал записи не исполняется ни одной реализацией, в обещание видов не входит |

## Отношения

| Отношение | Смысл |
|---|---|
| `region_code(region, code: Text)` | код ISO 3166-2 |
| `region_anchor(region, lat: Decimal, lon: Decimal)` | опорная точка для подписи на карте |
| `station_location(station, lat: Decimal, lon: Decimal)` | положение станции; факты подаёт потребитель |

Координаты — WGS84, градусы, порядок `lat, lon`, `Decimal` с двумя знаками,
диапазоны `[-90, 90]` / `[-180, 180]`; ключ отношения — сущность (одна опора
на сущность). Опора выбрана вручную, это картографическая точка для подписи,
не центроид и не правовой факт.

## Данные

`regions.json` — 17 областей и три города республиканского значения
Республики Казахстан (ISO 3166-2:KZ, редакция 2022 года: `KZ-10` Абай …
`KZ-79` Шымкент), подписи ru/kk/en и опорные точки. Модуль
`01-kz-regions.law` порождает только `tools/gen_regions.py`:

```bash
python3 packs/vocab/geo/tools/gen_regions.py          # записать
python3 packs/vocab/geo/tools/gen_regions.py --check  # сверить (зовут ворота)
```

## Как читает Lens

Аргумент или элемент ответа `law_ask` типа `vocab.geo::Region` (в том числе
через подтип и алиас) → карта статусов по опорным точкам на тайлах
OpenStreetMap с таблицей «регион → статус» под ней; `signature` ответа
несёт все константы типа с атрибутами (`region_code`, `region_anchor`).
Легенда у выборки — «в выборке / вне выборки», у `truth` — статус
спрошенного кортежа и «не спрашивалось» у остальных.

## Потребитель

`corpus/laws/kz/ministries/kazhydromet-observations`: `station_region(station,
region: Region)` и региональные выводы (`region_temperature_record`,
`region_precipitation_record`, `region_negative_temperature_anomaly`).

## Проверка

```bash
python3 verify/ci/gates/differential/check_vocab.py --only geo [--lawc <бинарь>]
python3 verify/ci/gates/differential/check_vocab.py --canary
```
