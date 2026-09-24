# Вопросы к пакету `kz.corpus.vred_ts`

<!-- Порождено из analysis/questions.json: python3 verify/ci/gates/coverage/check_package_questions.py --emit. Не править руками. -->

Каталог **предусмотренных** запросов §172 и того, чем каждый проверен (DECISION-0190). Карточка не означает положительного ответа по делу: ответ даёт только evaluation-документ с доказательством. Отсутствие карточки означает «не описано каталогом», а не «право молчит».

## Гибель транспортного средства и размер выплаты

Единицы источника: VRED_TS_PT_8, VRED_TS_PT_9.

| id | вопрос | форма | цель | шаблон | ветви | проверено |
|---|---|---|---|---|---|---|
| `unichtozheno` | Считается ли транспортное средство уничтоженным? | truth | `ts_schitaetsya_unichtozhennym(v: TransportnoeSredstvo)` | `evaluate truth(ts_schitaetsya_unichtozhennym(v: <v>));` | восстановление технически невозможно (факт дела) (`UnichtozhenoPoTekhnicheskoyNevozmozhnosti`); восстановление экономически нецелесообразно: расходы строго выше 80 % рыночной стоимости на дату отчёта (`UnichtozhenoPoEkonomicheskoyNetselesoobraznosti`) | тестов 5; дел Gibel, PeredachaOstatkov, Porog, Molchanie, MolchanieSnyato; вопросов `unichtozheno.json` |
| `pochemu-ne-unichtozheno` | Почему транспортное средство не признано уничтоженным: какой посылки не хватает? | why_not | `ts_schitaetsya_unichtozhennym(v: TransportnoeSredstvo)` | `why_not(ts_schitaetsya_unichtozhennym(v: <v>)) — граф блокеров §185 со статусом каждой посылки; law ask --query-json queries/pochemu-ne-unichtozheno.json` | — | дел Porog; вопросов `pochemu-ne-unichtozheno.json` |
| `netselesoobrazno` | Превышают ли ожидаемые расходы на восстановление восемьдесят процентов рыночной стоимости (порог строгий)? | truth | `vosstanovlenie_ekonomicheski_netselesoobrazno(v: TransportnoeSredstvo)` | `evaluate truth(vosstanovlenie_ekonomicheski_netselesoobrazno(v: <v>));` | Money > Money * 0.8 строго; ровно 80 % порога не образуют (`EkonomicheskayaNetselesoobraznost`) | тестов 6 |
| `vyplata-pri-gibeli` | Какова страховая выплата при гибели транспортного средства? | collect | `strakhovaya_vyplata_pri_gibeli(r: RaschetVreda, amount: Money↑)` | `evaluate collect amount: Money where kz.corpus.vred_ts::strakhovaya_vyplata_pri_gibeli(r: <r>, amount: amount);` | остатки переданы в собственность страховщика — рыночная стоимость на дату отчёта (`VyplataPriPeredacheOstatkov`); установлено, что остатки НЕ переданы — рыночная стоимость за минусом годных остатков; молчание дела о передаче отрицанием не считается (§113) (`VyplataZaMinusomGodnykhOstatkov`) | тестов 5; дел Gibel, PeredachaOstatkov, Molchanie, MolchanieSnyato; файлов `examples/gibel-i-detali/check.py` |
| `pochemu-ne-vyplata` | Почему размер выплаты при гибели не выведен? | why_not | `strakhovaya_vyplata_pri_gibeli(r: RaschetVreda, amount: Money)` | `why_not(strakhovaya_vyplata_pri_gibeli(r: <r>, amount: <amount>)); law ask --query-json queries/pochemu-ne-vyplata.json` | — | дел Molchanie; вопросов `pochemu-ne-vyplata.json` |
| `pozitsii-oplata-remonta` | Вправе ли страховщик по согласованию с потерпевшим оплатить ремонт в счёт выплаты? | positions | нормы `OrganizovatOplatuRemonta` | `evaluate positions(); expect position(OrganizovatOplatuRemonta, <статус>);` | — | тестов 1 |

- `vyplata-pri-gibeli`: Q2 STATUS.md: альтернативу выплаты определяет установленный факт передачи остатков либо его установленное отрицание; при молчании выплата не определена. Q3: нижняя граница «за минусом» не названа — при остатках дороже рыночной стоимости сумма отрицательна (parity:G14), нуль не подразумевается.
- `pochemu-ne-vyplata`: Голова правила вычисляемая: после E-0164 граф называет оба правила пункта 9, у «за минусом остатков» стоит пометка headArguments (UNEVALUATED). Блокер не доказывает, почему не получено именно заданное значение.

## Оценка заменяемой детали

Единицы источника: VRED_TS_PT_10, VRED_TS_PRIL_3.

| id | вопрос | форма | цель | шаблон | ветви | проверено |
|---|---|---|---|---|---|---|
| `detal-bez-iznosa` | Оценивается ли заменяемая деталь по стоимости новой детали без учёта износа? | truth | `detal_otsenivaetsya_bez_iznosa(d: Detal)` | `evaluate truth(detal_otsenivaetsya_bez_iznosa(d: <d>));` | владелец — физическое лицо, ТС без обязательного техосмотра, среднегодовой пробег не более 15 000 км, деталь не повреждалась и не ремонтировалась (`NovayaDetalUFizicheskogoLitsa`); владелец — юридическое лицо, ТС на гарантийном обслуживании, пробег не более 20 000 км, то же условие о детали (`NovayaDetalUYuridicheskogoLitsa`) | тестов 10; дел DetalFizlitso, DetalYurlitso, DetalRemont; вопросов `detal-bez-iznosa.json` |
| `pochemu-ne-bez-iznosa` | Почему деталь не оценена без износа? | why_not | `detal_otsenivaetsya_bez_iznosa(d: Detal)` | `why_not(detal_otsenivaetsya_bez_iznosa(d: <d>)); law ask --query-json queries/pochemu-ne-bez-iznosa.json` | — | дел DetalRemont; вопросов `pochemu-ne-bez-iznosa.json` |
| `stoimost-detali` | Какая стоимость заменяемой детали идёт в калькуляцию: новой или с учётом износа? | collect | `stoimost_zamenyaemoy_detali(d: Detal, amount: Money↑)` | `evaluate collect amount: Money where kz.corpus.vred_ts::stoimost_zamenyaemoy_detali(d: <d>, amount: amount);` | деталь оценивается без износа — рыночная стоимость новой детали, стоимость с износом вытеснена (`StoimostDetaliBezIznosa`); общее правило приложения 3 — стоимость с учётом износа (факт дела, износ извне) (`StoimostDetaliSUchetomIznosa`) | тестов 4; дел DetalFizlitso, DetalYurlitso, DetalRemont; файлов `examples/gibel-i-detali/check.py` |
| `pozitsii-peredat-detal` | Обязан ли потерпевший передать заменяемую деталь страховщику по его требованию, и исполнена ли обязанность? | positions | нормы `PeredatZamenyaemuyuDetal` | `evaluate positions(); expect position(PeredatZamenyaemuyuDetal, <статус>);` | — | тестов 2; дел DetalFizlitso; вопросов `positions.json` |

- `pozitsii-peredat-detal`: Окно обязанности открыто: нарушенной по сроку она не становится (t17).

- **Не отвечает:** Какова величина амортизационного износа детали? — источник отсылает вовне (VRED_TS_PT_2, VRED_TS_PT_11, VRED_TS_PRIL_3). Величина амортизационного износа не вычисляется: Правила формулы не содержат (пункт 2 отсылает к лицензионному СПО, пункт 11 — к интернет-ресурсу, приложение 3 называет расчёт износа разделом отчёта); стоимость детали с учётом износа входит фактом дела. Подаётся фактом `stoimost_detali_s_uchetom_iznosa`. Связанный вопрос: `stoimost-detali`.

## Отчёт о размере вреда: сроки, отметки, возражения, оформление

Единицы источника: VRED_TS_PT_3, VRED_TS_PT_3_1, VRED_TS_PRIL_3.

| id | вопрос | форма | цель | шаблон | ветви | проверено |
|---|---|---|---|---|---|---|
| `predel-otmetki` | Какой день — последний для отметки потерпевшего об ознакомлении с отчётом (три рабочих дня)? | truth | `predel_otmetki_poterpevshego(r: RaschetVreda, day: Date)` | `evaluate truth(predel_otmetki_poterpevshego(r: <r>, day: <day>)); — в мире нужен снимок kz.corpus.clir.official_calendar и deadline_policy дела` | три рабочих дня со дня получения отчёта по официальному календарю (`PredelOtmetkiPoterpevshego`); при упрощённом оформлении происшествия срок снят (дефитер) (`PredelOtmetkiPoterpevshego/unless/UproshchennoeOformlenie`) | тестов 6 |
| `predel-otveta` | Какой день — последний для ответа страховщика на отметку о несогласии? | truth | `predel_otveta_strakhovshchika(r: RaschetVreda, day: Date)` | `evaluate truth(predel_otveta_strakhovshchika(r: <r>, day: <day>)); — нужен снимок календаря §85` | три рабочих дня со дня получения отметки о несогласии (`PredelOtvetaStrakhovshchika`); при упрощённом оформлении срок снят (`PredelOtvetaStrakhovshchika/unless/UproshchennoeOformlenie`) | тестов 3 |
| `predel-otcheta` | Какой день — последний для представления отчёта потерпевшему (пять рабочих дней со дня осмотра)? | truth | `predel_predostavleniya_otcheta(r: RaschetVreda, day: Date)` | `evaluate truth(predel_predostavleniya_otcheta(r: <r>, day: <day>)); — нужен снимок календаря §85` | пять рабочих дней со дня осмотра (`PredelPredostavleniyaOtcheta`); при упрощённом оформлении срок снят (`PredelPredostavleniyaOtcheta/unless/UproshchennoeOformlenie`) | тестов 3 |
| `otchet-ne-v-srok` | Не предоставлен ли отчёт в установленный срок? | truth | `otchet_ne_predostavlen_v_srok(r: RaschetVreda)` | `evaluate truth(otchet_ne_predostavlen_v_srok(r: <r>));` | отчёт получен после предела срока (`OtchetPoluchenPosleSroka`); отчёт не предоставлен вовсе (установленное отрицание получения) (`OtchetNePredostavlenVovse`) | тестов 3 |
| `pravo-na-vyplatu-3-1` | Есть ли у потерпевшего право на выплату по пункту 3-1 статьи 22 Закона при непредоставлении отчёта? | truth | `pravo_na_vyplatu_po_punktu_3_1_stati_22_zakona(p: Poterpevshiy, r: RaschetVreda)` | `evaluate truth(pravo_na_vyplatu_po_punktu_3_1_stati_22_zakona(p: <p>, r: <r>));` | право выводится из непредоставления отчёта в срок; РАЗМЕР выплаты здесь не считается (`PravoNaVyplatuPriNepredostavleniiOtcheta`) | тестов 5 |
| `otvet-na-nesoglasie` | Отреагировал ли страховщик на отметку о несогласии: корректировкой отчёта либо письменным ответом? | truth | `strakhovshchik_otreagiroval_na_nesoglasie(r: RaschetVreda)` | `evaluate truth(strakhovshchik_otreagiroval_na_nesoglasie(r: <r>));` | корректировка расчёта (`ReaktsiyaKorrektirovkoy`); письменный мотивированный ответ (`ReaktsiyaPismennymOtvetom`) | тестов 1 |
| `pozitsii-otchet` | Исполнена, нарушена или ещё открыта обязанность страховщика представить отчёт (в срок либо без срока при упрощённом оформлении)? | positions | нормы `PredostavitOtchet`, `PredostavitOtchetBezSroka` | `evaluate positions(); expect position(PredostavitOtchet, <статус>); expect position(PredostavitOtchetBezSroka, <статус>); — нужен снимок календаря §85` | — | тестов 4 |
| `pozitsii-otmetka-i-otvet` | Каков статус обязанностей проставить отметку (потерпевший) и ответить на несогласие (страховщик)? | positions | нормы `ProstavitOtmetku`, `OtvetitNaNesoglasie` | `evaluate positions(); expect position(ProstavitOtmetku, <статус>); expect position(OtvetitNaNesoglasie, <статус>);` | — | тестов 3 |
| `otchet-sostavlen` | Составлен ли отчёт по Правилам: оформлен по приложению 3, утверждён, представлен в допустимом виде? | truth | `otchet_sostavlen_po_pravilam(o: Otchet)` | `evaluate truth(otchet_sostavlen_po_pravilam(o: <o>));` | — | тестов 1 |
| `otchet-prilozhenie-3` | Оформлен ли отчёт согласно приложению 3 (титульный лист, сведения пункта 1, стоимости и объёмы, приложения, итоговая величина, заверение, отметки)? | truth | `otchet_oformlen_po_prilozheniyu_3(o: Otchet)` | `evaluate truth(otchet_oformlen_po_prilozheniyu_3(o: <o>));` | — | тестов 1 |
| `otchet-titulnyy-list` | Полон ли титульный лист отчёта (восемь элементов приложения 3 значениями полей)? | truth | `otchet_soderzhit_titulnyy_list(o: Otchet)` | `evaluate truth(otchet_soderzhit_titulnyy_list(o: <o>));` | — | тестов 4 |
| `otchet-zaveren` | Заверен ли отчёт: печатью и подписью либо одной подписью при установленном отсутствии печати? | truth | `otchet_zaveren(o: Otchet)` | `evaluate truth(otchet_zaveren(o: <o>));` | печать и подпись (`OtchetZaverenPechatyuIPodpisyu`); подпись без печати при установленном её отсутствии (`OtchetZaverenPodpisyuBezPechati`) | тестов 2 |
| `otchet-stoimosti-i-obemy` | Содержит ли отчёт расчётные указания: стоимости работ, материалов, деталей и объёмы? | truth | `otchet_soderzhit_stoimosti_i_obemy(o: Otchet)` | `evaluate truth(otchet_soderzhit_stoimosti_i_obemy(o: <o>));` | — | тестов 3 |
| `otchet-prilozheniya` | Содержит ли отчёт три приложения, названные приложением 3? | truth | `otchet_soderzhit_prilozheniya(o: Otchet)` | `evaluate truth(otchet_soderzhit_prilozheniya(o: <o>));` | — | тестов 2 |
| `otchet-itogovaya-velichina` | Указана ли итоговая величина вреда целым числом тенге? | truth | `otchet_soderzhit_itogovuyu_velichinu(o: Otchet)` | `evaluate truth(otchet_soderzhit_itogovuyu_velichinu(o: <o>));` | round(amount, 0, "HALF_UP") == amount — проверка отсутствия дробной части, режим округления не выбирается (§50) (`OtchetSoderzhitItogovuyuVelichinu`) | тестов 4 |

- **Не отвечает:** Каков размер выплаты при непредоставлении отчёта в срок? — источник отсылает вовне (VRED_TS_PT_3). Размер выплаты при непредоставлении отчёта не считается: пункт 3-1 статьи 22 Закона; вычисляется только право на такую выплату. Связанный вопрос: `pravo-na-vyplatu-3-1`.
- **Не отвечает:** Как округлить итоговую величину до тенге? — источник отсылает вовне (VRED_TS_PRIL_3). Округление итоговой величины до тенге не выполняется: приложение 3 требует округления, но режима не называет (§50); проверяется лишь отсутствие дробной части. Связанный вопрос: `otchet-itogovaya-velichina`.
- **Не отвечает:** Как исчисляются рабочие дни сроков пункта 3: со следующего дня, с переносом на рабочий день? — нужны данные, которые приносит дело (VRED_TS_PT_3). Порядок исчисления сроков (§86) нормой не объявляется: Правила сроки называют, политика и снимок официального календаря §85 приходят входом дела; без снимка в мире ответ — MISSING_INPUT. Связанный вопрос: `predel-otmetki`. ГК РК ст. 173, 176; сценарий tests/otchet/16-srok-bez-kalendarya.lawtest проверяет ОТСУТСТВИЕ календаря в мире.
- **Не отвечает:** Какой статус получает вопрос о сроке с датой за пределами снимка календаря? — ограничение языка или движка (VRED_TS_PT_3). Дата за пределами снимка календаря: обе реализации отвечают MISSING_INPUT с кодом CALENDAR_OUT_OF_RANGE, prose §175 перечнем E-0105 называет RUNTIME_ERROR — пробел SPEC (SPEC-1); сценарий закрепляет код и NEITHER, статус не закрепляет. Связанный вопрос: `predel-otmetki`.

## Осмотр и акт осмотра

Единицы источника: VRED_TS_PT_2, VRED_TS_PT_7, VRED_TS_PRIL_2.

| id | вопрос | форма | цель | шаблон | ветви | проверено |
|---|---|---|---|---|---|---|
| `osmotr-vozmozhen` | Соблюдены ли все семь условий возможности осмотра (пункт 7)? | truth | `osmotr_vozmozhen(r: RaschetVreda)` | `evaluate truth(osmotr_vozmozhen(r: <r>));` | — | тестов 2 |
| `osmotr-dopustim` | Допустим ли осмотр: при определении стоимости ремонта — только с документами о повреждениях в ДТП? | truth | `osmotr_dopustim(r: RaschetVreda)` | `evaluate truth(osmotr_dopustim(r: <r>));` | стоимость ремонта определяется и документы представлены (`OsmotrDopustimPriOpredeleniiStoimostiRemonta`); стоимость ремонта не определяется (`OsmotrDopustimVneOpredeleniyaStoimostiRemonta`); установленное отсутствие документов — недопустимость (отрицательный вывод) (`OsmotrNedopustimBezDokumentovODtp`) | тестов 5 |
| `osmotr-oformlen` | Оформлен ли осмотр актом надлежащим образом? | truth | `osmotr_oformlen(r: RaschetVreda)` | `evaluate truth(osmotr_oformlen(r: <r>));` | — | тестов 1 |
| `akt-prilozhenie-2` | Содержит ли акт осмотра все сведения приложения 2 (значениями полей: VIN, госномер, пробег, даты, дефекты)? | truth | `akt_soderzhit_svedeniya_prilozheniya_2(a: AktOsmotra)` | `evaluate truth(akt_soderzhit_svedeniya_prilozheniya_2(a: <a>));` | — | тестов 5 |
| `akt-svedeniya-o-ts` | Полны ли сведения акта о транспортном средстве (пункт 4 приложения 2, фото одометра при наличии)? | truth | `akt_soderzhit_svedeniya_o_ts(a: AktOsmotra)` | `evaluate truth(akt_soderzhit_svedeniya_o_ts(a: <a>));` | — | тестов 3 |
| `akt-predstavivshee-litso` | Полны ли сведения акта о лице, представившем ТС для осмотра (пункт 3 приложения 2)? | truth | `akt_soderzhit_svedeniya_o_predstavivshem_lice(a: AktOsmotra)` | `evaluate truth(akt_soderzhit_svedeniya_o_predstavivshem_lice(a: <a>));` | — | тестов 1 |
| `akt-povrezhdennye-elementy` | Полны ли сведения акта о повреждённых элементах (пункт 5 приложения 2)? | truth | `akt_soderzhit_svedeniya_o_povrezhdennykh_elementakh(a: AktOsmotra)` | `evaluate truth(akt_soderzhit_svedeniya_o_povrezhdennykh_elementakh(a: <a>));` | — | тестов 1 |
| `dopolnitelnyy-osmotr` | Проведён ли дополнительный осмотр по правилам: по надлежащему заявлению, страховщиком, с актом? | truth | `dopolnitelnyy_osmotr_proveden_po_pravilam(r: RaschetVreda)` | `evaluate truth(dopolnitelnyy_osmotr_proveden_po_pravilam(r: <r>));` | — | тестов 1 |
| `korrektirovka-skrytye-defekty` | Оформляется ли корректировка расчёта при скрытых дефектах дополнением к отчёту? | truth | `korrektirovka_pri_skrytykh_defektakh_oformlyaetsya_dopolneniem(r: RaschetVreda)` | `evaluate truth(korrektirovka_pri_skrytykh_defektakh_oformlyaetsya_dopolneniem(r: <r>));` | — | тестов 4 |
| `pozitsii-osmotr-na-sto` | Обязан ли страховщик провести осмотр на станции техобслуживания по требованию потерпевшего, и исполнена ли обязанность? | positions | нормы `OsmotrNaStantsii` | `evaluate positions(); expect position(OsmotrNaStantsii, <статус>);` | — | тестов 2 |

- **Не отвечает:** В какой срок страховщик обязан провести осмотр и составить акт? — источник отсылает вовне (VRED_TS_PT_3). Срок осмотра и составления акта осмотра не считается: часть первая пункта 3 отдаёт его пункту 3 статьи 22 Закона, закреплённых байтов Закона в пакете нет. Связанный вопрос: `pozitsii-osmotr-na-sto`. Обязанность осмотра на СТО выводится с открытым окном: нарушенной по сроку не становится.

## Кто ведёт расчёт и как он организован

Единицы источника: VRED_TS_PT_2, VRED_TS_PT_4, VRED_TS_PT_4_1, VRED_TS_PT_6, VRED_TS_PRIL_1.

| id | вопрос | форма | цель | шаблон | ветви | проверено |
|---|---|---|---|---|---|---|
| `raschet-po-pravilam` | Ведётся ли расчёт по Правилам и кем: страховщиком или привлечённым оценщиком? | truth | `raschet_vedetsya_po_pravilam(r: RaschetVreda)` | `evaluate truth(raschet_vedetsya_po_pravilam(r: <r>));` | расчёт осуществляет страховщик (`RaschetStrakhovshchikom`); расчёт осуществляет привлечённый по договору оценщик (пункт 4) (`RaschetOtsenshchikom`) | тестов 2 |
| `organizatsiya-rascheta` | Выполнена ли организация расчёта: пройдены ли три этапа пункта 6? | truth | `organizatsiya_rascheta_vypolnena(r: RaschetVreda)` | `evaluate truth(organizatsiya_rascheta_vypolnena(r: <r>));` | — | тестов 2 |
| `vybor-otsenshchikov` | Обеспечен ли потерпевшему выбор не менее чем из двух оценщиков? | truth | `vybor_otsenshchikov_obespechen(r: RaschetVreda)` | `evaluate truth(vybor_otsenshchikov_obespechen(r: <r>));` | предложено не менее двух (>= 2) (`VyborOtsenshchikovObespechen`); предложено меньше двух — поражаемое отрицание (`VyborOtsenshchikovNeObespechen`) | тестов 6 |
| `pozitsii-dva-otsenshchika` | Исполнена ли обязанность страховщика предложить потерпевшему выбор из двух оценщиков? | positions | нормы `PredlozhitDvukhOtsenshchikov` | `evaluate positions(); expect position(PredlozhitDvukhOtsenshchikov, <статус>);` | — | тестов 2 |
| `pozitsii-poterpevshiy` | Каков статус обязанностей потерпевшего со дня заявления: сохранить имущество и предоставить возможность расчёта? | positions | нормы `SokhranitImushchestvo`, `PredostavitVozmozhnostRascheta` | `evaluate positions(); expect position(SokhranitImushchestvo, <статус>); expect position(PredostavitVozmozhnostRascheta, <статус>);` | — | тестов 2 |

- `pozitsii-poterpevshiy`: Сохранение имущества — обязанность поддержания §124.2: изменение имущества после происшествия даёт VIOLATED.

## Доступность расчёта износа

Единицы источника: VRED_TS_PT_11.

| id | вопрос | форма | цель | шаблон | ветви | проверено |
|---|---|---|---|---|---|---|
| `pozitsii-raschet-iznosa` | Обеспечена ли возможность расчёта износа страховым омбудсманом и страховщиком (пункт 11)? | positions | нормы `ObespechitRaschetIznosaOmbudsmanom`, `ObespechitRaschetIznosaStrakhovshchikom` | `evaluate positions(); expect position(ObespechitRaschetIznosaOmbudsmanom, <статус>); expect position(ObespechitRaschetIznosaStrakhovshchikom, <статус>);` | — | тестов 2 |

## Выводимое без собственной карточки

Звенья вывода: спрашиваются через карточки выше, названы здесь ради полноты поверхности в обе стороны.

| предикат | почему без карточки |
|---|---|
| `detal_ne_povrezhdalas_i_ne_remontirovalas` | Условие пункта 10 двумя фактами; читается правилами detal_otsenivaetsya_bez_iznosa, спрашивается через карточку detal-bez-iznosa (t12). |
| `dopolnitelnyy_osmotr_oformlen` | Звено дополнительного осмотра; спрашивается через dopolnitelnyy_osmotr_proveden_po_pravilam (t10-d). |
| `otchet_predostavlen_v_dopustimom_vide` | Бумажный либо электронный вид (§206); звено otchet_sostavlen_po_pravilam (KZ-VRED-27). |
| `otchet_soderzhit_otmetki` | Обе отметки пункта 3; звено otchet_oformlen_po_prilozheniyu_3 (t20-a). |
| `otchet_soderzhit_svedeniya_punkta_1` | Сведения пункта 1 приложения 3; звено otchet_oformlen_po_prilozheniyu_3 (t20-a). |
| `otchet_utverzhden` | Утверждение руководителем либо уполномоченным лицом (§206); звено otchet_sostavlen_po_pravilam (KZ-VRED-27). |
| `otmetka_prostavlena` | Отметка о согласии либо о несогласии с причинами (§206); звено обязанности ProstavitOtmetku (KZ-VRED-13, KZ-VRED-14). |
| `raschet_osushchestvlyaet_otsenshchik` | Привлечённый оценщик пункта 4; звено raschet_vedetsya_po_pravilam (KZ-VRED-22). |
| `srok_otmetki_poterpevshego` | Нормативная константа срока (3 рабочих дня, assert-факт); читается правилом PredelOtmetkiPoterpevshego. |
| `srok_otveta_strakhovshchika` | Нормативная константа срока (3 рабочих дня, assert-факт); читается правилом PredelOtvetaStrakhovshchika. |
| `srok_predostavleniya_otcheta` | Нормативная константа срока (5 рабочих дней, assert-факт); читается правилом PredelPredostavleniyaOtcheta. |
| `trebovanie_o_foto_odometra_soblyudeno` | Оговорка «фото одометра при наличии» двумя правилами; звено akt_soderzhit_svedeniya_o_ts (t09-c, t09-d). |
| `zayavlenie_soderzhit_svedeniya_prilozheniya_1` | Состав заявления по приложению 1; звено дополнительного осмотра и организации расчёта (t10-d, KZ-VRED-25). |

## Итог

Карточек 41, границ 6, внутренних звеньев 13; выводимых предикатов в CLIR 43, норм 12 — поверхность закрыта в обе стороны. Причины по конкретному делу берутся не из каталога, а из issues и why_not ответа.
