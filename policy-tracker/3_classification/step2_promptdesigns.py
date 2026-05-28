#!/usr/bin/env python3
"""
step2_promptdesigns.py

all 16 prompt variants for the 2×2×2×2 factorial classification experiment.

this script is automatically run when running step2_classify_llm.py which imports the prompt templates from here.

dimensions
----------
zero_shot / few_shot  : whether labeled examples precede the task
batch / single        : batch — all tasks (dates + social policy field + crisis_ref);
                        single — social policy field (SPF) classification only
nodef / def           : nodef — label list only; def — full class definitions
nojus / jus           : nojus — classification only; jus — + written justification

exports
-------
PROMPTS      dict[str, {"system": str, "user": str}]
               user template receives keyword args: {title}, {date_published}, {full_text}
OUTPUT_SCHEMAS dict[str, dict]
               plain JSON Schema object per prompt key (model-agnostic);
               model-specific wrapping (e.g. OpenAI response_format) is handled in step3
"""

#x ─── COUNTRY CONFIGURATION ────────────────────────────────────────────────────
#feeds into system prompt
COUNTRY_ADJECTIVE = "German"              # possessive adjective, e.g. "French", "British"
LEGISLATION_SOURCE = "Bundesgesetzblatt"  # official publication name for this country
DOCUMENT_TYPES    = "Gesetze, Verordnungen, Bekanntmachungen"  # official word for the given document types in local language
# ──────────────────────────────────────────────────────────────────────────────

# ─── SPF OPTIONS ──────────────────────────────────────────────────────────────

_SPF_OPTIONS = [
    "unemployment",
    "family/children",
    "housing",
    "disability",
    "retirement",
    "survivors",
    "sickness/health/care",
    "labour market",
    "taxes",
    "none"
]

# ─── SPF CLASS DEFINITIONS (from codebook) ────────────────────────────────────────────────────

_SPF_CLASS_DEF = """\
Unemployment — Regards benefits, measures, and/or social security contributions that:
- replace in whole or in part income lost by a worker due to the loss of gainful employment;
- provide a subsistence (or better) income to persons entering or re-entering the labour market;
- compensate for the loss of earnings due to partial unemployment;
- replace in whole or in part income lost by an older worker who retires from gainful employment before the reference retirement age because of job reductions for economic reasons;
- contribute to the cost of training or re-training people looking for employment;
- help unemployed persons meet the cost of travelling or relocating to obtain employment;
- provide help and relief by providing appropriate goods and services;
- provide for jobseekers who do not qualify for unemployment insurance benefits, or whose entitlement to these benefits is low or has expired;
- provide for a universal basic income that substitutes or supplements unemployment protection.

Family/children — Regards benefits, measures, and/or social security contributions that:
- provide financial support to households for bringing up children;
- provide financial assistance to people who support relatives other than children;
- provide social services specifically designed to assist and protect the family, particularly children;
- expand the availability of or enhance access to child care facilities;
- regulate child alimony between parents.
Excludes: measures concretely designed as a tax cut or tax advantage for families with children or for those providing assistance to a care-dependent relative. These fall under "taxes."

Housing — Regards benefits, measures, and/or social security contributions that:
- help households meet the cost of housing, for example through rent benefits, social housing, or benefits to owner-occupiers;
- subsidise heating, water, and electricity expenditures;
- aim to end homelessness through "housing first" policies;
- increase the availability of social housing.

Disability — Regards benefits, measures, and/or social security contributions that:
- provide an income to persons whose full or partial inability to engage in economic activity or to lead a normal life, due to a physical or mental impairment that is likely to be permanent or to persist beyond a minimum prescribed period, impairs their ability to work and earn beyond a minimum level laid down by legislation;
- provide allowances designed to cover disability-related costs or needs.
Excludes: short-term sickness benefits, which fall under "sickness/health/care." Also excludes benefits for persons providing care to incapacitated individuals, which fall under "family/children."

Retirement — Regards benefits, measures, and/or social security contributions that:
- provide a replacement income when the aged person retires from the labour market;
- guarantee a certain income when a person has reached a prescribed age;
- regulate private retirement provisions.
Excludes: benefits and contributions for medical care and elderly care, which fall under "sickness/health/care."

Survivors — Regards benefits, measures, and/or social security contributions that:
- provide a temporary or permanent income to people who have suffered from the loss of a spouse or next-of-kin, usually when the latter represented the main breadwinner for the beneficiary;
- compensate survivors for funeral costs or for any hardship caused by the death of a family member;
- provide goods and services to eligible survivors.

Sickness/health/care — Regards benefits, measures, and/or social security contributions that:
- replace in whole or in part loss of earnings during temporary inability to work due to sickness or injury;
- provide medical care in the framework of social protection to maintain, restore, or improve the health of the people protected;
- provide goods or services specifically required by the personal or social circumstances of the elderly (elderly care is classified here rather than under "retirement");
- concern the institutional setup of health insurance systems, both public and private.
Excludes: long-term disability benefits, which fall under "disability." Also excludes benefits for persons providing care to incapacitated individuals, which fall under "family/children."

Labour market — Regards benefits, measures, and/or social security contributions that:
- regulate the terms and conditions of employment (wages, minimum wages, working hours, non-standard and atypical employment, employment exempt from social security contributions, illegal employment);
- actively intervene to expand labour force participation and facilitate (re-)employment — through employment services, direct job creation, start-up incentives, or hiring and wage subsidies targeted at specific groups — including by enforcing the conditionality of benefits on active job search and participation in employability measures.

Taxes — Regards all personal income taxes payable in respect of employment and self-employment earnings, including measures that alter tax rates, thresholds, deductions, or credits for these earnings.
Also includes: measures concretely designed as a tax cut or tax advantage for families with children or for those providing assistance to a care-dependent relative. These are classified here rather than under "family/children.


None - The policy does not concern social policy at all and cannot be matched to any of the other classes.\""""



# ─── FEW-SHOT EXAMPLES ────────────────────────────────────────────────────────
# Source: germany gold standard (bgbl1-2020-58-1, bgbl1-2008-32-5, bgbl1-2010-66-8).
# bgbl1-2008-32-5 has no retrieved full text — title-based classification is intentional
# and common for vocational training regulations with a standardised title pattern.
# Batch variants: all output fields (summary, dates, spf_justification, spf1/2, crisis_ref).
# Single variants: SPF fields only (spf_justification, spf1/2).

_FEW_SHOT_EXAMPLES_BATCH = """\
──── EXAMPLES ────

Title     : Zweites Gesetz zur steuerlichen Entlastung von Familien sowie zur Anpassung weiterer steuerlicher Regelungen (Zweites Familienentlastungsgesetz – 2. FamEntlastG)
Published : 2020-12-07

2616         Bundesgesetzblatt Jahrgang 2020 Teil I Nr. 58, ausgegeben zu Bonn am 7. Dezember 2020
Zweites Gesetz
zur steuerlichen Entlastung von Familien
sowie zur Anpassung weiterer steuerlicher Regelungen
(Zweites Familienentlastungsgesetz – 2. FamEntlastG)
Vom 1. Dezember 2020
Der Bundestag hat mit Zustimmung des Bundes-             6. In § 50 Absatz 2 Satz 2 Nummer 4 Buchstabe a wird
rates das folgende Gesetz beschlossen:                         die Angabe „11 900 Euro" durch die Angabe
„12 250 Euro" ersetzt.
Artikel 1
7. § 51a wird wie folgt geändert:
Änderung des
Einkommensteuergesetzes                          a) In Absatz 1 Satz 1 werden nach den Wörtern
Das Einkommensteuergesetz in der Fassung der Be-               „dieses Gesetzes" die Wörter „mit Ausnahme
kanntmachung vom 8. Oktober 2009 (BGBl. I S. 3366,                des § 36a" eingefügt.
3862), das zuletzt durch Artikel 6 des Gesetzes vom            b) Absatz 2a Satz 1 wird wie folgt gefasst:
12. August 2020 (BGBl. I S. 1879) geändert worden ist,
wird wie folgt geändert:                                          „Vorbehaltlich des § 40a Absatz 2 ist beim Steu-
1. In § 32 Absatz 6 Satz 1 wird die Angabe „2 586 Euro"           erabzug vom Arbeitslohn Bemessungsgrundlage
durch die Angabe „2 730 Euro" und die Angabe                   die Lohnsteuer; beim Steuerabzug vom laufen-
„1 320 Euro" durch die Angabe „1 464 Euro" ersetzt.            den Arbeitslohn und beim Jahresausgleich ist
die Lohnsteuer maßgebend, die sich ergibt, wenn
2. § 32a Absatz 1 wird wie folgt gefasst:                         der nach § 39b Absatz 2 Satz 5 zu versteuernde
„(1) Die tarifliche Einkommensteuer bemisst sich            Jahresbetrag für die Steuerklassen I, II und III um
nach dem zu versteuernden Einkommen. Sie be-                   den doppelten Kinderfreibetrag sowie den dop-
trägt im Veranlagungszeitraum 2021 vorbehaltlich               pelten Freibetrag für den Betreuungs- und Erzie-
der §§ 32b, 32d, 34, 34a, 34b und 34c jeweils in               hungs- oder Ausbildungsbedarf und für die Steu-
Euro für zu versteuernde Einkommen                             erklasse IV um den Kinderfreibetrag sowie den
1. bis 9 744 Euro (Grundfreibetrag):                           Freibetrag für den Betreuungs- und Erziehungs-
oder Ausbildungsbedarf (§ 32 Absatz 6 Satz 1)
0;
für jedes Kind vermindert wird, für das eine Kür-
2. von 9 745 Euro bis 14 753 Euro:                             zung der Freibeträge für Kinder nach § 32 Ab-
(995,21 · y + 1 400) · y;                                   satz 6 Satz 4 nicht in Betracht kommt."
3. von 14 754 Euro bis 57 918 Euro:                         c) Absatz 2e Satz 4 wird wie folgt gefasst:
(208,85 · z + 2 397) · z + 950,96;
„Das Bundeszentralamt für Steuern übermittelt
4. von 57 919 Euro bis 274 612 Euro:                           für jeden Veranlagungszeitraum, für den ein
0,42 · x – 9 136,63;                                        Sperrvermerk abgerufen worden ist, an das
5. von 274 613 Euro an:                                        Wohnsitzfinanzamt des Schuldners der Kapital-
ertragsteuer Name und Anschrift des Kirchen-
0,45 · x – 17 374,99.                                       steuerabzugsverpflichteten, dem im Fall des
Die Größe „y" ist ein Zehntausendstel des den                  Absatzes 2c Satz 1 Nummer 3 auf Grund des
Grundfreibetrag übersteigenden Teils des auf einen             Sperrvermerks ein Nullwert im Sinne des Absat-
vollen Euro-Betrag abgerundeten zu versteuernden               zes 2c Satz 1 Nummer 3 Satz 10 mitgeteilt wor-
Einkommens. Die Größe „z" ist ein Zehntausendstel              den ist."
des 14 753 Euro übersteigenden Teils des auf einen
vollen Euro-Betrag abgerundeten zu versteuernden         8. § 52 wird wie folgt geändert:
Einkommens. Die Größe „x" ist das auf einen vollen          a) Absatz 1 wird wie folgt geändert:
Euro-Betrag abgerundete zu versteuernde Einkom-
men. Der sich ergebende Steuerbetrag ist auf den               aa) In Satz 1 wird die Angabe „Veranlagungszeit-
nächsten vollen Euro-Betrag abzurunden."                            raum 2020" durch die Angabe „Veranla-
3. In § 33a Absatz 1 Satz 1 wird die Angabe                            gungszeitraum 2021" ersetzt.
„9 408 Euro" durch die Angabe „9 744 Euro" ersetzt.            bb) In den Sätzen 2 und 3 wird jeweils die An-
4. In § 39b Absatz 2 Satz 7 wird die Angabe                            gabe „31. Dezember 2019" durch die Angabe
„10 898 Euro" durch die Angabe „11 237 Euro",                       „31. Dezember 2020" ersetzt.
die Angabe „28 526 Euro" durch die Angabe
„28 959 Euro" und die Angabe „216 400 Euro"                 b) Dem Absatz 49a wird folgender Satz angefügt:
durch die Angabe „219 690 Euro" ersetzt.                       „§ 66 Absatz 1 in der Fassung des Artikels 1 des
5. In § 46 Absatz 2 Nummer 3 und 4 wird jeweils die               Gesetzes vom 1. Dezember 2020 (BGBl. I S.
Angabe „11 900 Euro" durch die Angabe                          2616) ist für Kindergeldfestsetzungen anzuwen-
„12 250 Euro" und die Angabe „22 600 Euro" durch               den, die Zeiträume betreffen, die nach dem
die Angabe „23 350 Euro" ersetzt.                              31. Dezember 2020 beginnen."

Bundesgesetzblatt Jahrgang 2020 Teil I Nr. 58, ausgegeben zu Bonn am 7. Dezember 2020               2617
9. § 66 Absatz 1 wird wie folgt gefasst:                                pitalertragsteuer bei Begründung einer recht-
„(1) Das Kindergeld beträgt monatlich für das                     lichen Verbindung beim Bundeszentralamt für
erste und zweite Kind jeweils 219 Euro, für das                      Steuern anzufragen, ob der Schuldner der
dritte Kind 225 Euro und für das vierte und jedes                    Kapitalertragsteuer kirchensteuerpflichtig ist
weitere Kind jeweils 250 Euro."                                      (Anlassabfrage), und einmal jährlich im Zeit-
raum vom 1. September bis 31. Oktober beim
Artikel 2                                     Bundeszentralamt für Steuern anzufragen, ob
der Schuldner der Kapitalertragsteuer am
Weitere Änderung                                    31. August des betreffenden Jahres (Stichtag)
des Einkommensteuergesetzes                                kirchensteuerpflichtig ist (Regelabfrage)."
Das Einkommensteuergesetz, das zuletzt durch Ar-
bb) Satz 3 wird wie folgt gefasst:
tikel 1 dieses Gesetzes geändert worden ist, wird wie
folgt geändert:                                                         „Im Übrigen kann der Kirchensteuerabzugs-
verpflichtete eine Anlassabfrage auf Veran-
1. § 32a Absatz 1 wird wie folgt gefasst:
lassung des Schuldners der Kapitalertrag-
„(1) Die tarifliche Einkommensteuer bemisst sich                  steuer an das Bundeszentralamt für Steuern
nach dem zu versteuernden Einkommen. Sie be-                         richten."
trägt ab dem Veranlagungszeitraum 2022 vorbehalt-
cc) Satz 5 wird wie folgt gefasst:
lich der §§ 32b, 32d, 34, 34a, 34b und 34c jeweils in
Euro für zu versteuernde Einkommen                                   „Bei Begründung einer rechtlichen Verbin-
1. bis 9 984 Euro (Grundfreibetrag):                                 dung ist der Schuldner der Kapitalertrag-
steuer vom Kirchensteuerabzugsverpflich-
0;                                                               teten auf die Datenabfrage sowie das
2. von 9 985 Euro bis 14 926 Euro:                                   Antragsrecht nach Absatz 2e Satz 1 in geeig-
(1 008,70 · y + 1 400) · y;                                      neter Form hinzuweisen."
3. von 14 927 Euro bis 58 596 Euro:                              dd) Satz 9 wird aufgehoben.
(206,43 · z + 2 397) · z + 938,24;                        b) In Absatz 2e Satz 4 werden die Wörter „Absat-
zes 2c Satz 1 Nummer 3 Satz 10" durch die
4. von 58 597 Euro bis 277 825 Euro:
Wörter „Absatzes 2c Satz 1 Nummer 3 Satz 9"
0,42 · x – 9 267,53;                                         ersetzt.
5. von 277 826 Euro an:                                   7. § 52 Absatz 1 wird wie folgt geändert:
0,45 · x – 17 602,28.                                     a) In Satz 1 wird die Angabe „Veranlagungszeit-
Die Größe „y" ist ein Zehntausendstel des den                    raum 2021" durch die Angabe „Veranlagungs-
Grundfreibetrag übersteigenden Teils des auf einen               zeitraum 2022" ersetzt.
vollen Euro-Betrag abgerundeten zu versteuernden              b) In den Sätzen 2 und 3 wird jeweils die Angabe
Einkommens. Die Größe „z" ist ein Zehntausendstel                „31. Dezember 2020" durch die Angabe „31. De-
des 14 926 Euro übersteigenden Teils des auf einen               zember 2021" ersetzt.
vollen Euro-Betrag abgerundeten zu versteuernden
Einkommens. Die Größe „x" ist das auf einen vollen                                 Artikel 3
Euro-Betrag abgerundete zu versteuernde Einkom-
men. Der sich ergebende Steuerbetrag ist auf den                               Weitere Änderung
nächsten vollen Euro-Betrag abzurunden."                               des Einkommensteuergesetzes
2. In § 33a Absatz 1 Satz 1 wird die Angabe                     Dem § 51a Absatz 2b des Einkommensteuergeset-
„9 696 Euro" durch die Angabe „9 984 Euro" ersetzt.       zes, das zuletzt durch Artikel 2 dieses Gesetzes geän-
dert worden ist, wird folgender Satz angefügt:
3. In § 39b Absatz 2 Satz 7 wird die Angabe
„11 237 Euro" durch die Angabe „11 480 Euro",             „Satz 1 ist nicht anzuwenden, wenn die Kapitalerträge
die Angabe „28 959 Euro" durch die Angabe                 zu den Einkünften aus Land- und Forstwirtschaft, aus
„29 298 Euro" und die Angabe „219 690 Euro"               Gewerbebetrieb, aus selbständiger Arbeit oder aus
durch die Angabe „222 260 Euro" ersetzt.                  Vermietung und Verpachtung gehören."
4. In § 46 Absatz 2 Nummer 3 und 4 wird jeweils die
Artikel 4
Angabe „12 250 Euro" durch die Angabe
„12 550 Euro" und die Angabe „23 350 Euro" durch                                Änderung des
die Angabe „23 900 Euro" ersetzt.                                    Solidaritätszuschlaggesetzes 1995
5. In § 50 Absatz 2 Satz 2 Nummer 4 Buchstabe a wird            Das Solidaritätszuschlaggesetz 1995 in der Fassung
die Angabe „12 250 Euro" durch die Angabe                 der Bekanntmachung vom 15. Oktober 2002 (BGBl. I
„12 550 Euro" ersetzt.                                    S. 4130), das zuletzt durch Artikel 1 des Gesetzes vom
10. Dezember 2019 (BGBl. I S. 2115) geändert worden
6. § 51a wird wie folgt geändert:
ist, wird wie folgt geändert:
a) Absatz 2c Satz 1 Nummer 3 wird wie folgt geän-
dert:                                                 1. In § 3 Absatz 2a Satz 1 wird die Angabe „5 172 Euro"
durch die Angabe „5 460 Euro", die Angabe
aa) Der Satzteil vor Satz 2 wird wie folgt gefasst:       „2 640 Euro" durch die Angabe „2 928 Euro", die
„der Kirchensteuerabzugsverpflichtete hat             Angabe „2 586 Euro" durch die Angabe „2 730 Euro"
unter Angabe der Identifikationsnummer und            und die Angabe „1 320 Euro" durch die Angabe
des Geburtsdatums des Schuldners der Ka-              „1 464 Euro" ersetzt.

2618          Bundesgesetzblatt Jahrgang 2020 Teil I Nr. 58, ausgegeben zu Bonn am 7. Dezember 2020
2. Dem § 6 wird folgender Absatz 22 angefügt:                           geld in der Höhe anzusetzen, in der es voraus-
„(22) § 3 Absatz 2a in der am 1. Januar 2021 gel-                sichtlich für den Antragsmonat zu bewilligen
tenden Fassung ist erstmals auf den laufenden Ar-                   wäre."
beitslohn anzuwenden, der für einen nach dem                4. § 8 wird wie folgt geändert:
31. Dezember 2020 endenden Lohnzahlungszeit-
a) In Absatz 2 werden nach dem Wort „Kindergel-
raum gezahlt wird, und auf sonstige Bezüge, die
des" die Wörter „und des Kinderzuschlags" ein-
nach dem 31. Dezember 2020 zufließen."
gefügt.
Artikel 5                                 b) Absatz 3 wird wie folgt geändert:
Änderung des                                     aa) In Satz 1 werden die Wörter „, in einem
Bundeskindergeldgesetzes                                     Pauschbetrag, der zwischen der Bundes-
Das Bundeskindergeldgesetz in der Fassung der                            regierung und der Bundesagentur vereinbart
Bekanntmachung vom 28. Januar 2009 (BGBl. I S. 142,                         wird" gestrichen.
3177), das zuletzt durch Artikel 12 des Gesetzes vom                   bb) Folgender Satz wird angefügt:
23. Oktober 2020 (BGBl. I S. 2208) geändert worden
„Näheres wird durch Verwaltungsvereinba-
ist, wird wie folgt geändert:
rung geregelt."
1. § 5 Absatz 3 Satz 2 wird aufgehoben.
5. § 13 wird wie folgt geändert:
2. § 6 wird wie folgt geändert:
a) In Absatz 1 Satz 4 wird das Wort „Nürnberg"
a) Absatz 1 wird wie folgt gefasst:                                durch die Wörter „Bayern Nord" ersetzt.
„(1) Das Kindergeld beträgt monatlich für das
b) In Absatz 3 werden nach dem Wort „Kindergeld"
erste und zweite Kind jeweils 219 Euro, für das
die Wörter „und Kinderzuschlag einheitlich" ein-
dritte Kind 225 Euro und für das vierte und jedes
gefügt.
weitere Kind jeweils 250 Euro."
6. In § 20 Absatz 2 wird die Angabe „31. Dezember
b) In Absatz 2 wird die Angabe „204 Euro" durch die
2022" durch die Angabe „31. Dezember 2023" er-
Angabe „219 Euro" ersetzt.
setzt.
3. § 6a Absatz 1 Nummer 3 wird wie folgt gefasst:
7. In § 22 wird die Angabe „31. Juli 2022" durch die
„3. bei Bezug des Kinderzuschlags keine Hilfebe-                Angabe „31. Juli 2023" ersetzt.
dürftigkeit im Sinne des § 9 des Zweiten Buches
Sozialgesetzbuch besteht, wobei die Bedarfe
Artikel 6
nach § 28 des Zweiten Buches Sozialgesetz-
buch außer Betracht bleiben. Bei der Prüfung                                    Inkrafttreten
der Hilfebedürftigkeit ist das für den Antrags-            (1) Dieses Gesetz tritt vorbehaltlich der Absätze 2
monat bewilligte Wohngeld zu berücksichtigen.           und 3 am 1. Januar 2021 in Kraft.
Wird kein Wohngeld bezogen und könnte mit
Wohngeld und Kinderzuschlag Hilfebedürftigkeit             (2) Artikel 2 tritt am 1. Januar 2022 in Kraft.
vermieden werden, ist bei der Prüfung Wohn-                (3) Artikel 3 tritt am 1. Januar 2023 in Kraft.
Das vorstehende Gesetz wird hiermit ausgefertigt.
Es ist im Bundesgesetzblatt zu verkünden.
Berlin, den 1. Dezember 2020
Der Bundespräsident

Classification: {
  "summary": "The law is an omnibus law with several provisions to strenghten families with children. It alters calculation bases for the income tax and adjusts the monthly child benefit to 219€ for the first and second, 225€ for the third and 250€ for the fourth and for every further child. It also alters the calculation for Hilfsbedürftigkeit and Wohngeld.",
  "legally_effective": "2021-01",
  "leg_eff_terminate": "na",
  "legally_effective_2": "2022-01",
  "leg_eff_terminate_2": "na",
  "art_leg_eff_2": "2",
  "legally_effective_3": "2023-01",
  "leg_eff_terminate_3": "na",
  "art_leg_eff_3": "3",
  "spf_justification": "The law makes alterations both to child benefits and to family income tax arrangements.",
  "social_policy_field_1": "family/children",
  "social_policy_field_2": "taxes",
  "crisis_ref": 0
}
---

Title     : Verordnung über die Berufsausbildung zum Systemelektroniker und zur Systemelektronikerin
Published : 2008-07-30

[full text not retrieved]

Classification: {
  "summary": "The policy regulates professional training and certification for a specific profession, i.e. system electronics technicians.",
  "legally_effective": "2008-08",
  "leg_eff_terminate": "na",
  "legally_effective_2": "na",
  "leg_eff_terminate_2": "na",
  "art_leg_eff_2": "na",
  "legally_effective_3": "na",
  "leg_eff_terminate_3": "na",
  "art_leg_eff_3": "na",
  "spf_justification": "the decree regulates the occupational training and certification of a specific occupation and therefore regulates quality standards in and educational requirements for access to labour markets.",
  "social_policy_field_1": "labour market",
  "social_policy_field_2": "na",
  "crisis_ref": 0
}
---

Title     : Erste Verordnung zur Änderung der Verordnung über die Pauschalierung und Zahlung des Ausgleichsbetrags der Bundesagentur für Arbeit an die Träger der gesetzlichen Rentenversicherung für arbeitsmarktbedingte Renten wegen voller Erwerbsminderung
Published : 2010-12-22

Bundesgesetzblatt Jahrgang 2010 Teil I Nr. 66, ausgegeben zu Bonn am 22. Dezember 2010 2127
Erste Verordnung
zur Änderung der Verordnung
über die Pauschalierung und Zahlung
des Ausgleichsbetrags der Bundesagentur
für Arbeit an die Träger der gesetzlichen Rentenversicherung
für arbeitsmarktbedingte Renten wegen voller Erwerbsminderung
Vom 17. Dezember 2010
Auf Grund des § 226 Absatz 4 des Sechsten Buches Sozialgesetzbuch – Ge-
setzliche Rentenversicherung –, der zuletzt durch Artikel 259 Nummer 4 Buch-
stabe b der Verordnung vom 31. Oktober 2006 (BGBl. I S. 2407) geändert
worden ist, verordnet das Bundesministerium für Arbeit und Soziales im Einver-
nehmen mit dem Bundesministerium der Finanzen:
Artikel 1
§ 1 der Verordnung über die Pauschalierung und Zahlung des Ausgleichs-
betrags der Bundesagentur für Arbeit an die Träger der gesetzlichen Rentenver-
sicherung für arbeitsmarktbedingte Renten wegen voller Erwerbsminderung
vom 27. September 2002 (BGBl. I S. 3961), die zuletzt durch Artikel 78 des
Gesetzes vom 9. Dezember 2004 (BGBl. I S. 3242) geändert worden ist, wird
wie folgt geändert:
1. Absatz 1 wird wie folgt geändert:
a) In Nummer 2 werden die Wörter „Kranken- und Pflegeversicherung" durch
das Wort „Krankenversicherung" ersetzt.
b) In Nummer 3 wird die Angabe „15,2" durch die Angabe „10,4" ersetzt.
2. In Absatz 2 wird die Angabe „15,2" durch die Angabe „10,4" ersetzt.
Artikel 2
Inkrafttreten
Diese Verordnung tritt mit Wirkung vom 1. Januar 2010 in Kraft.
Der Bundesrat hat zugestimmt.
Berlin, den 17. Dezember 2010


Classification: {
  "summary": "The law amends a regulation governing a lump-sum compensation payment from the Federal Employment Agency to statutory retirement insurance carriers for disability pensions triggered by labour market conditions. It adjusts the contribution rate and removes a reference to long-term care insurance.",
  "legally_effective": "2010-01",
  "leg_eff_terminate": "na",
  "legally_effective_2": "na",
  "leg_eff_terminate_2": "na",
  "art_leg_eff_2": "na",
  "legally_effective_3": "na",
  "leg_eff_terminate_3": "na",
  "art_leg_eff_3": "na",
  "spf_justification": "The regulation sits at the intersection of disability and retirement: it concerns disability pensions (Rente wegen voller Erwerbsminderung) and the financial settlement mechanism between labour market and retirement insurance institutions.",
  "social_policy_field_1": "disability",
  "social_policy_field_2": "retirement",
  "crisis_ref": 0
}
──────────────────"""

_FEW_SHOT_EXAMPLES_SINGLE = """\
──── EXAMPLES ────

Title     : Zweites Gesetz zur steuerlichen Entlastung von Familien sowie zur Anpassung weiterer steuerlicher Regelungen (Zweites Familienentlastungsgesetz – 2. FamEntlastG)
Published : 2020-12-07

2616         Bundesgesetzblatt Jahrgang 2020 Teil I Nr. 58, ausgegeben zu Bonn am 7. Dezember 2020
Zweites Gesetz
zur steuerlichen Entlastung von Familien
sowie zur Anpassung weiterer steuerlicher Regelungen
(Zweites Familienentlastungsgesetz – 2. FamEntlastG)
Vom 1. Dezember 2020
Der Bundestag hat mit Zustimmung des Bundes-             6. In § 50 Absatz 2 Satz 2 Nummer 4 Buchstabe a wird
rates das folgende Gesetz beschlossen:                         die Angabe „11 900 Euro" durch die Angabe
„12 250 Euro" ersetzt.
Artikel 1
7. § 51a wird wie folgt geändert:
Änderung des
Einkommensteuergesetzes                          a) In Absatz 1 Satz 1 werden nach den Wörtern
Das Einkommensteuergesetz in der Fassung der Be-               „dieses Gesetzes" die Wörter „mit Ausnahme
kanntmachung vom 8. Oktober 2009 (BGBl. I S. 3366,                des § 36a" eingefügt.
3862), das zuletzt durch Artikel 6 des Gesetzes vom            b) Absatz 2a Satz 1 wird wie folgt gefasst:
12. August 2020 (BGBl. I S. 1879) geändert worden ist,
wird wie folgt geändert:                                          „Vorbehaltlich des § 40a Absatz 2 ist beim Steu-
1. In § 32 Absatz 6 Satz 1 wird die Angabe „2 586 Euro"           erabzug vom Arbeitslohn Bemessungsgrundlage
durch die Angabe „2 730 Euro" und die Angabe                   die Lohnsteuer; beim Steuerabzug vom laufen-
„1 320 Euro" durch die Angabe „1 464 Euro" ersetzt.            den Arbeitslohn und beim Jahresausgleich ist
die Lohnsteuer maßgebend, die sich ergibt, wenn
2. § 32a Absatz 1 wird wie folgt gefasst:                         der nach § 39b Absatz 2 Satz 5 zu versteuernde
„(1) Die tarifliche Einkommensteuer bemisst sich            Jahresbetrag für die Steuerklassen I, II und III um
nach dem zu versteuernden Einkommen. Sie be-                   den doppelten Kinderfreibetrag sowie den dop-
trägt im Veranlagungszeitraum 2021 vorbehaltlich               pelten Freibetrag für den Betreuungs- und Erzie-
der §§ 32b, 32d, 34, 34a, 34b und 34c jeweils in               hungs- oder Ausbildungsbedarf und für die Steu-
Euro für zu versteuernde Einkommen                             erklasse IV um den Kinderfreibetrag sowie den
1. bis 9 744 Euro (Grundfreibetrag):                           Freibetrag für den Betreuungs- und Erziehungs-
oder Ausbildungsbedarf (§ 32 Absatz 6 Satz 1)
0;
für jedes Kind vermindert wird, für das eine Kür-
2. von 9 745 Euro bis 14 753 Euro:                             zung der Freibeträge für Kinder nach § 32 Ab-
(995,21 · y + 1 400) · y;                                   satz 6 Satz 4 nicht in Betracht kommt."
3. von 14 754 Euro bis 57 918 Euro:                         c) Absatz 2e Satz 4 wird wie folgt gefasst:
(208,85 · z + 2 397) · z + 950,96;
„Das Bundeszentralamt für Steuern übermittelt
4. von 57 919 Euro bis 274 612 Euro:                           für jeden Veranlagungszeitraum, für den ein
0,42 · x – 9 136,63;                                        Sperrvermerk abgerufen worden ist, an das
5. von 274 613 Euro an:                                        Wohnsitzfinanzamt des Schuldners der Kapital-
ertragsteuer Name und Anschrift des Kirchen-
0,45 · x – 17 374,99.                                       steuerabzugsverpflichteten, dem im Fall des
Die Größe „y" ist ein Zehntausendstel des den                  Absatzes 2c Satz 1 Nummer 3 auf Grund des
Grundfreibetrag übersteigenden Teils des auf einen             Sperrvermerks ein Nullwert im Sinne des Absat-
vollen Euro-Betrag abgerundeten zu versteuernden               zes 2c Satz 1 Nummer 3 Satz 10 mitgeteilt wor-
Einkommens. Die Größe „z" ist ein Zehntausendstel              den ist."
des 14 753 Euro übersteigenden Teils des auf einen
vollen Euro-Betrag abgerundeten zu versteuernden         8. § 52 wird wie folgt geändert:
Einkommens. Die Größe „x" ist das auf einen vollen          a) Absatz 1 wird wie folgt geändert:
Euro-Betrag abgerundete zu versteuernde Einkom-
men. Der sich ergebende Steuerbetrag ist auf den               aa) In Satz 1 wird die Angabe „Veranlagungszeit-
nächsten vollen Euro-Betrag abzurunden."                            raum 2020" durch die Angabe „Veranla-
3. In § 33a Absatz 1 Satz 1 wird die Angabe                            gungszeitraum 2021" ersetzt.
„9 408 Euro" durch die Angabe „9 744 Euro" ersetzt.            bb) In den Sätzen 2 und 3 wird jeweils die An-
4. In § 39b Absatz 2 Satz 7 wird die Angabe                            gabe „31. Dezember 2019" durch die Angabe
„10 898 Euro" durch die Angabe „11 237 Euro",                       „31. Dezember 2020" ersetzt.
die Angabe „28 526 Euro" durch die Angabe
„28 959 Euro" und die Angabe „216 400 Euro"                 b) Dem Absatz 49a wird folgender Satz angefügt:
durch die Angabe „219 690 Euro" ersetzt.                       „§ 66 Absatz 1 in der Fassung des Artikels 1 des
5. In § 46 Absatz 2 Nummer 3 und 4 wird jeweils die               Gesetzes vom 1. Dezember 2020 (BGBl. I S.
Angabe „11 900 Euro" durch die Angabe                          2616) ist für Kindergeldfestsetzungen anzuwen-
„12 250 Euro" und die Angabe „22 600 Euro" durch               den, die Zeiträume betreffen, die nach dem
die Angabe „23 350 Euro" ersetzt.                              31. Dezember 2020 beginnen."

Bundesgesetzblatt Jahrgang 2020 Teil I Nr. 58, ausgegeben zu Bonn am 7. Dezember 2020               2617
9. § 66 Absatz 1 wird wie folgt gefasst:                                pitalertragsteuer bei Begründung einer recht-
„(1) Das Kindergeld beträgt monatlich für das                     lichen Verbindung beim Bundeszentralamt für
erste und zweite Kind jeweils 219 Euro, für das                      Steuern anzufragen, ob der Schuldner der
dritte Kind 225 Euro und für das vierte und jedes                    Kapitalertragsteuer kirchensteuerpflichtig ist
weitere Kind jeweils 250 Euro."                                      (Anlassabfrage), und einmal jährlich im Zeit-
raum vom 1. September bis 31. Oktober beim
Artikel 2                                     Bundeszentralamt für Steuern anzufragen, ob
der Schuldner der Kapitalertragsteuer am
Weitere Änderung                                    31. August des betreffenden Jahres (Stichtag)
des Einkommensteuergesetzes                                kirchensteuerpflichtig ist (Regelabfrage)."
Das Einkommensteuergesetz, das zuletzt durch Ar-
bb) Satz 3 wird wie folgt gefasst:
tikel 1 dieses Gesetzes geändert worden ist, wird wie
folgt geändert:                                                         „Im Übrigen kann der Kirchensteuerabzugs-
verpflichtete eine Anlassabfrage auf Veran-
1. § 32a Absatz 1 wird wie folgt gefasst:
lassung des Schuldners der Kapitalertrag-
„(1) Die tarifliche Einkommensteuer bemisst sich                  steuer an das Bundeszentralamt für Steuern
nach dem zu versteuernden Einkommen. Sie be-                         richten."
trägt ab dem Veranlagungszeitraum 2022 vorbehalt-
cc) Satz 5 wird wie folgt gefasst:
lich der §§ 32b, 32d, 34, 34a, 34b und 34c jeweils in
Euro für zu versteuernde Einkommen                                   „Bei Begründung einer rechtlichen Verbin-
1. bis 9 984 Euro (Grundfreibetrag):                                 dung ist der Schuldner der Kapitalertrag-
steuer vom Kirchensteuerabzugsverpflich-
0;                                                               teten auf die Datenabfrage sowie das
2. von 9 985 Euro bis 14 926 Euro:                                   Antragsrecht nach Absatz 2e Satz 1 in geeig-
(1 008,70 · y + 1 400) · y;                                      neter Form hinzuweisen."
3. von 14 927 Euro bis 58 596 Euro:                              dd) Satz 9 wird aufgehoben.
(206,43 · z + 2 397) · z + 938,24;                        b) In Absatz 2e Satz 4 werden die Wörter „Absat-
zes 2c Satz 1 Nummer 3 Satz 10" durch die
4. von 58 597 Euro bis 277 825 Euro:
Wörter „Absatzes 2c Satz 1 Nummer 3 Satz 9"
0,42 · x – 9 267,53;                                         ersetzt.
5. von 277 826 Euro an:                                   7. § 52 Absatz 1 wird wie folgt geändert:
0,45 · x – 17 602,28.                                     a) In Satz 1 wird die Angabe „Veranlagungszeit-
Die Größe „y" ist ein Zehntausendstel des den                    raum 2021" durch die Angabe „Veranlagungs-
Grundfreibetrag übersteigenden Teils des auf einen               zeitraum 2022" ersetzt.
vollen Euro-Betrag abgerundeten zu versteuernden              b) In den Sätzen 2 und 3 wird jeweils die Angabe
Einkommens. Die Größe „z" ist ein Zehntausendstel                „31. Dezember 2020" durch die Angabe „31. De-
des 14 926 Euro übersteigenden Teils des auf einen               zember 2021" ersetzt.
vollen Euro-Betrag abgerundeten zu versteuernden
Einkommens. Die Größe „x" ist das auf einen vollen                                 Artikel 3
Euro-Betrag abgerundete zu versteuernde Einkom-
men. Der sich ergebende Steuerbetrag ist auf den                               Weitere Änderung
nächsten vollen Euro-Betrag abzurunden."                               des Einkommensteuergesetzes
2. In § 33a Absatz 1 Satz 1 wird die Angabe                     Dem § 51a Absatz 2b des Einkommensteuergeset-
„9 696 Euro" durch die Angabe „9 984 Euro" ersetzt.       zes, das zuletzt durch Artikel 2 dieses Gesetzes geän-
dert worden ist, wird folgender Satz angefügt:
3. In § 39b Absatz 2 Satz 7 wird die Angabe
„11 237 Euro" durch die Angabe „11 480 Euro",             „Satz 1 ist nicht anzuwenden, wenn die Kapitalerträge
die Angabe „28 959 Euro" durch die Angabe                 zu den Einkünften aus Land- und Forstwirtschaft, aus
„29 298 Euro" und die Angabe „219 690 Euro"               Gewerbebetrieb, aus selbständiger Arbeit oder aus
durch die Angabe „222 260 Euro" ersetzt.                  Vermietung und Verpachtung gehören."
4. In § 46 Absatz 2 Nummer 3 und 4 wird jeweils die
Artikel 4
Angabe „12 250 Euro" durch die Angabe
„12 550 Euro" und die Angabe „23 350 Euro" durch                                Änderung des
die Angabe „23 900 Euro" ersetzt.                                    Solidaritätszuschlaggesetzes 1995
5. In § 50 Absatz 2 Satz 2 Nummer 4 Buchstabe a wird            Das Solidaritätszuschlaggesetz 1995 in der Fassung
die Angabe „12 250 Euro" durch die Angabe                 der Bekanntmachung vom 15. Oktober 2002 (BGBl. I
„12 550 Euro" ersetzt.                                    S. 4130), das zuletzt durch Artikel 1 des Gesetzes vom
10. Dezember 2019 (BGBl. I S. 2115) geändert worden
6. § 51a wird wie folgt geändert:
ist, wird wie folgt geändert:
a) Absatz 2c Satz 1 Nummer 3 wird wie folgt geän-
dert:                                                 1. In § 3 Absatz 2a Satz 1 wird die Angabe „5 172 Euro"
durch die Angabe „5 460 Euro", die Angabe
aa) Der Satzteil vor Satz 2 wird wie folgt gefasst:       „2 640 Euro" durch die Angabe „2 928 Euro", die
„der Kirchensteuerabzugsverpflichtete hat             Angabe „2 586 Euro" durch die Angabe „2 730 Euro"
unter Angabe der Identifikationsnummer und            und die Angabe „1 320 Euro" durch die Angabe
des Geburtsdatums des Schuldners der Ka-              „1 464 Euro" ersetzt.

2618          Bundesgesetzblatt Jahrgang 2020 Teil I Nr. 58, ausgegeben zu Bonn am 7. Dezember 2020
2. Dem § 6 wird folgender Absatz 22 angefügt:                           geld in der Höhe anzusetzen, in der es voraus-
„(22) § 3 Absatz 2a in der am 1. Januar 2021 gel-                sichtlich für den Antragsmonat zu bewilligen
tenden Fassung ist erstmals auf den laufenden Ar-                   wäre."
beitslohn anzuwenden, der für einen nach dem                4. § 8 wird wie folgt geändert:
31. Dezember 2020 endenden Lohnzahlungszeit-
a) In Absatz 2 werden nach dem Wort „Kindergel-
raum gezahlt wird, und auf sonstige Bezüge, die
des" die Wörter „und des Kinderzuschlags" ein-
nach dem 31. Dezember 2020 zufließen."
gefügt.
Artikel 5                                 b) Absatz 3 wird wie folgt geändert:
Änderung des                                     aa) In Satz 1 werden die Wörter „, in einem
Bundeskindergeldgesetzes                                     Pauschbetrag, der zwischen der Bundes-
Das Bundeskindergeldgesetz in der Fassung der                            regierung und der Bundesagentur vereinbart
Bekanntmachung vom 28. Januar 2009 (BGBl. I S. 142,                         wird" gestrichen.
3177), das zuletzt durch Artikel 12 des Gesetzes vom                   bb) Folgender Satz wird angefügt:
23. Oktober 2020 (BGBl. I S. 2208) geändert worden
„Näheres wird durch Verwaltungsvereinba-
ist, wird wie folgt geändert:
rung geregelt."
1. § 5 Absatz 3 Satz 2 wird aufgehoben.
5. § 13 wird wie folgt geändert:
2. § 6 wird wie folgt geändert:
a) In Absatz 1 Satz 4 wird das Wort „Nürnberg"
a) Absatz 1 wird wie folgt gefasst:                                durch die Wörter „Bayern Nord" ersetzt.
„(1) Das Kindergeld beträgt monatlich für das
b) In Absatz 3 werden nach dem Wort „Kindergeld"
erste und zweite Kind jeweils 219 Euro, für das
die Wörter „und Kinderzuschlag einheitlich" ein-
dritte Kind 225 Euro und für das vierte und jedes
gefügt.
weitere Kind jeweils 250 Euro."
6. In § 20 Absatz 2 wird die Angabe „31. Dezember
b) In Absatz 2 wird die Angabe „204 Euro" durch die
2022" durch die Angabe „31. Dezember 2023" er-
Angabe „219 Euro" ersetzt.
setzt.
3. § 6a Absatz 1 Nummer 3 wird wie folgt gefasst:
7. In § 22 wird die Angabe „31. Juli 2022" durch die
„3. bei Bezug des Kinderzuschlags keine Hilfebe-                Angabe „31. Juli 2023" ersetzt.
dürftigkeit im Sinne des § 9 des Zweiten Buches
Sozialgesetzbuch besteht, wobei die Bedarfe
Artikel 6
nach § 28 des Zweiten Buches Sozialgesetz-
buch außer Betracht bleiben. Bei der Prüfung                                    Inkrafttreten
der Hilfebedürftigkeit ist das für den Antrags-            (1) Dieses Gesetz tritt vorbehaltlich der Absätze 2
monat bewilligte Wohngeld zu berücksichtigen.           und 3 am 1. Januar 2021 in Kraft.
Wird kein Wohngeld bezogen und könnte mit
Wohngeld und Kinderzuschlag Hilfebedürftigkeit             (2) Artikel 2 tritt am 1. Januar 2022 in Kraft.
vermieden werden, ist bei der Prüfung Wohn-                (3) Artikel 3 tritt am 1. Januar 2023 in Kraft.
Das vorstehende Gesetz wird hiermit ausgefertigt.
Es ist im Bundesgesetzblatt zu verkünden.
Berlin, den 1. Dezember 2020
Der Bundespräsident


Classification: {
  "spf_justification": "The law makes alterations both to child benefits and to family income tax arrangements.",
  "social_policy_field_1": "family/children",
  "social_policy_field_2": "taxes"
}
---

Title     : Verordnung über die Berufsausbildung zum Systemelektroniker und zur Systemelektronikerin
Published : 2008-07-30

[full text not retrieved]

Classification: {
  "spf_justification": "the decree regulates the occupational training and certification of a specific occupation and therefore regulates quality standards in and educational requirements for access to labour markets.",
  "social_policy_field_1": "labour market",
  "social_policy_field_2": "na"
}
---

Title     : Erste Verordnung zur Änderung der Verordnung über die Pauschalierung und Zahlung des Ausgleichsbetrags der Bundesagentur für Arbeit an die Träger der gesetzlichen Rentenversicherung für arbeitsmarktbedingte Renten wegen voller Erwerbsminderung
Published : 2010-12-22

Bundesgesetzblatt Jahrgang 2010 Teil I Nr. 66, ausgegeben zu Bonn am 22. Dezember 2010 2127
Erste Verordnung
zur Änderung der Verordnung
über die Pauschalierung und Zahlung
des Ausgleichsbetrags der Bundesagentur
für Arbeit an die Träger der gesetzlichen Rentenversicherung
für arbeitsmarktbedingte Renten wegen voller Erwerbsminderung
Vom 17. Dezember 2010
Auf Grund des § 226 Absatz 4 des Sechsten Buches Sozialgesetzbuch – Ge-
setzliche Rentenversicherung –, der zuletzt durch Artikel 259 Nummer 4 Buch-
stabe b der Verordnung vom 31. Oktober 2006 (BGBl. I S. 2407) geändert
worden ist, verordnet das Bundesministerium für Arbeit und Soziales im Einver-
nehmen mit dem Bundesministerium der Finanzen:
Artikel 1
§ 1 der Verordnung über die Pauschalierung und Zahlung des Ausgleichs-
betrags der Bundesagentur für Arbeit an die Träger der gesetzlichen Rentenver-
sicherung für arbeitsmarktbedingte Renten wegen voller Erwerbsminderung
vom 27. September 2002 (BGBl. I S. 3961), die zuletzt durch Artikel 78 des
Gesetzes vom 9. Dezember 2004 (BGBl. I S. 3242) geändert worden ist, wird
wie folgt geändert:
1. Absatz 1 wird wie folgt geändert:
a) In Nummer 2 werden die Wörter „Kranken- und Pflegeversicherung" durch
das Wort „Krankenversicherung" ersetzt.
b) In Nummer 3 wird die Angabe „15,2" durch die Angabe „10,4" ersetzt.
2. In Absatz 2 wird die Angabe „15,2" durch die Angabe „10,4" ersetzt.
Artikel 2
Inkrafttreten
Diese Verordnung tritt mit Wirkung vom 1. Januar 2010 in Kraft.
Der Bundesrat hat zugestimmt.
Berlin, den 17. Dezember 2010


Classification: {
  "spf_justification": "The regulation sits at the intersection of disability and retirement: it concerns disability pensions (Rente wegen voller Erwerbsminderung) and the financial settlement mechanism between labour market and retirement insurance institutions.",
  "social_policy_field_1": "disability",
  "social_policy_field_2": "retirement"
}
──────────────────"""

# ─── SHARED SYSTEM PROMPT ─────────────────────────────────────────────────────

_SYSTEM = (
    f"You are an expert in {COUNTRY_ADJECTIVE} social policy legislation. "
    f"You classify legislative texts ({DOCUMENT_TYPES}) from the {LEGISLATION_SOURCE} "
    "according to a structured codebook. When full texts are not retrieved, go by titles."
    "Return your classifications as a JSON object with the exact fields specified."
)

# ─── REUSABLE TEXT SECTIONS ───────────────────────────────────────────────────

_SEC_SUM = (
    "──── SUMMARY ────\n"
    "Provide 1-2 brief sentences to pointedly summarize this legal policy text in English."
)

_SEC_DATE = """\
──── DATE EXTRACTION ────
legally_effective   : Date the law enters into force. Use the BGBl publication
                      date if no explicit date is stated. Format: yyyy-mm.
leg_eff_terminate   : Date legal effect terminates. "na" if not specified.
legally_effective_2 : Second entry-into-force date if the law specifies multiple. "na" if not applicable.
leg_eff_terminate_2 : Termination date for legally_effective_2. "na" if not applicable.
art_leg_eff_2       : Article/paragraph number that legally_effective_2 refers to
                      (first number + optional letter only, e.g. "4a"). "na" if not applicable.
legally_effective_3 : Third entry-into-force date. "na" if not applicable.
leg_eff_terminate_3 : Termination date for legally_effective_3. "na" if not applicable.
art_leg_eff_3       : Article/paragraph number for legally_effective_3. "na" if not applicable."""

_SEC_SPF_HEAD = (
    "──── SOCIAL POLICY FIELD ────\n"
    "Assign the primary social policy field that the legislative text addresses (social_policy_field_1). "
    "If the text substantively addresses a second, distinct policy field, assign it as social_policy_field_2; "
    'otherwise set social_policy_field_2 to "na". Only select "none" for social_policy_field_1 if the policy does not relate to social policy at all. In this case, you' \
    'must set social_policy_field_2 to "na". ' #head and tail split for flexible combination with jus versus nojus prompts
)

_SEC_SPF_NODEF_TAIL = (
    "Valid values:\n"
    + "\n".join(f'  "{opt}"' for opt in _SPF_OPTIONS) #head and tail tail split for flexible combination with jus versus nojus prompts
)

_SEC_SPF_DEF_TAIL = (
    "Classify according to these class definitions:\n\n"
    + _SPF_CLASS_DEF #head and tail tail split for flexible combination with jus versus nojus prompts
)

_SEC_SPF_NODEF = _SEC_SPF_HEAD + "\n\n" + _SEC_SPF_NODEF_TAIL #prompts with no definitions for spf
_SEC_SPF_DEF   = _SEC_SPF_HEAD + "\n\n" + _SEC_SPF_DEF_TAIL #prompts with definitions for spf

_SEC_CRISIS = """\
──── CRISIS REFERENCE ────
crisis_ref : 1 if the text explicitly references COVID-19/the pandemic or the
             2008 financial/economic crisis; 0 otherwise."""

_SEC_JUS = """\
However, before classifying, you always reason through the social policy field options below, first, in light of the legislative text — considering both the primary field (social_policy_field_1) and, if so, which secondary field applies (social_policy_field_2).
spf_justification : Your reasoning about which social policy field(s) apply. This field precedes social_policy_field_1 and social_policy_field_2 in the output schema."""

_SEC_TEXT = """\
──── LEGISLATIVE TEXT ────
Title     : {title}
Published : {date_published}

{full_text}"""

# ─── COMPOSITION HELPERS ──────────────────────────────────────────────────────


def _join(*parts: str) -> str:
    return "\n\n".join(p for p in parts if p)


def _compose_batch(spf_sec: str, *, few_shot: bool) -> str: #function that composes the batch task prompts, used later in build-step
    return _join(
        _FEW_SHOT_EXAMPLES_BATCH if few_shot else "",
        "Classify the legislative text below according to these codebook rules.",
        _SEC_SUM,
        _SEC_DATE,
        spf_sec,
        _SEC_CRISIS,
        _SEC_TEXT,
    )


def _compose_single(spf_sec: str, *, few_shot: bool) -> str: #function that composes the single task prompts, used later in build-step
    return _join(
        _FEW_SHOT_EXAMPLES_SINGLE if few_shot else "",
        spf_sec,
        _SEC_TEXT,
    )


# ─── OUTPUT SCHEMA BUILDER ────────────────────────────────────────────────────
# Builds plain JSON Schema objects (model-agnostic). Step 3 scripts wrap these
# in whatever format their target API requires (e.g. OpenAI response_format).


def _make_schema(*, batch: bool, jus: bool) -> dict:
    props: dict = {}
    req: list = []

    if batch:
        props["summary"] = {"type": "string", "description": "1-2 sentence English summary of the policy text"}
        req.append("summary")

        date_fields: dict[str, str] = {
            "legally_effective":   "yyyy-mm",
            "leg_eff_terminate":   "yyyy-mm or na",
            "legally_effective_2": "yyyy-mm or na",
            "leg_eff_terminate_2": "yyyy-mm or na",
            "art_leg_eff_2":       "article number or na",
            "legally_effective_3": "yyyy-mm or na",
            "leg_eff_terminate_3": "yyyy-mm or na",
            "art_leg_eff_3":       "article number or na",
        }
        for k, desc in date_fields.items():
            props[k] = {"type": "string", "description": desc}
        req.extend(date_fields)

    if jus:
        props["spf_justification"] = {
            "type": "string",
            "description": "reasoning about which social policy field(s) apply, before classifying",
        }
        req.append("spf_justification")

    props["social_policy_field_1"] = {"type": "string", "enum": _SPF_OPTIONS}
    props["social_policy_field_2"] = {"type": "string", "enum": _SPF_OPTIONS + ["na"]}
    req += ["social_policy_field_1", "social_policy_field_2"]

    if batch:
        props["crisis_ref"] = {"type": "integer", "enum": [0, 1]}
        req.append("crisis_ref")

    return {
        "type": "object",
        "properties": props,
        "required": req,
        "additionalProperties": False,
    }


# ─── BUILD ALL VARIANTS ────────────────────────────────────────────────────

# (version_prefix, few_shot, batch, use_def, jus)
_VARIANTS = [
    ("v1",  False, True,  False, False),
    ("v2",  False, False, False, False),
    ("v3",  False, True,  True,  False),
    ("v4",  False, False, True,  False),
    ("v5",  False, True,  False, True),
    ("v6",  False, False, False, True),
    ("v7",  False, True,  True,  True),
    ("v8",  False, False, True,  True),
    ("v9",  True,  True,  False, False),
    ("v10", True,  False, False, False),
    ("v11", True,  True,  True,  False),
    ("v12", True,  False, True,  False),
    ("v13", True,  True,  False, True),
    ("v14", True,  False, False, True),
    ("v15", True,  True,  True,  True),
    ("v16", True,  False, True,  True),
]


def _build_variants() -> tuple[dict, dict]: #iterates over all rows (prompt variations!) in _VARIANTS, builds individual spf_sec (with or without reasoning and with/out def) and then passes it into _compose_batch or _compose_single.
    prompts: dict = {}
    schemas: dict = {}
    for num, few_shot, batch, use_def, jus in _VARIANTS:
        shot  = "few_shot"  if few_shot else "zero_shot"
        scope = "batch"     if batch    else "single"
        defs  = "def"       if use_def  else "nodef"
        just  = "jus"       if jus      else "nojus"
        key   = f"{num}_{shot}_{scope}_{defs}_{just}"

        tail = _SEC_SPF_DEF_TAIL if use_def else _SEC_SPF_NODEF_TAIL
        spf  = _join(_SEC_SPF_HEAD, _SEC_JUS, tail) if jus else (
               _SEC_SPF_DEF if use_def else _SEC_SPF_NODEF)
        user = (
            _compose_batch(spf, few_shot=few_shot)
            if batch
            else _compose_single(spf, few_shot=few_shot)
        )
        prompts[key] = {"system": _SYSTEM, "user": user}
        schemas[key] = _make_schema(batch=batch, jus=jus)
    return prompts, schemas


PROMPTS, OUTPUT_SCHEMAS = _build_variants()

