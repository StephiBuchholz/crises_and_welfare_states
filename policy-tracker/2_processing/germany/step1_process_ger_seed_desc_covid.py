# 1 processing german seed descriptions for covid-specific legislation
"""

this file is a pre-step for the processing of the retrieved german legislative texts. it serves as a source for a completeness check
for specific covid policies, because some of these policies may not have been captured  in the
processing/german/step2_process_ger_seed_descriptions.py due to their crisis-specific word embeddings.
alternatively, it can also be used as a completeness check later on.

this file contains a list of German covid regulations (Gesetze, Verordnungen, Bekanntmachungen) retrieved from https://de.wikipedia.org/wiki/Liste_der_infolge_der_COVID-19-Pandemie_erlassenen_deutschen_Gesetze_und_Verordnungen#Landesrecht .


interactive triage: mark each COVID legislative item as social policy relevant (y) or not (n).
progress is auto-saved so one can can quit and resume at any time.

instructions: run script (runs in terminal) and make selections

controls:  y = yes   n / Enter = no   b = back   q = quit & save

result: see from_proc_step1_ger_cov_triage_selected.txt in data/processed/germany/ -> contains 24 out of 144 titles
"""

# imports

import json
import sys
from pathlib import Path

# setup

PROGRESS_FILE = Path(__file__).parent / ".triage_progress.json"
OUTPUT_FILE = (
    Path(__file__).parent.parent.parent
    / "data"
    / "processed"
    / "germany"
    / "from_proc_step1_ger_cov_triage_selected.txt"
)

# triage loop

ITEMS = [
    # ── Gesetze ─────────────────────────────────────────────────────────────
    "Gesetz zur Stärkung der Impfprävention gegen COVID-19 und zur Änderung weiterer Vorschriften im Zusammenhang mit der COVID-19-Pandemie vom 10. Dezember 2021\n  → Artikel 1 – Änderung des Infektionsschutzgesetzes\n  → Artikel 2 – Weitere Änderung des Infektionsschutzgesetzes",
    "Viertes Gesetz zum Schutz der Bevölkerung bei einer epidemischen Lage von nationaler Tragweite vom 22. April 2021",
    "Gesetz zur Fortgeltung der die epidemische Lage von nationaler Tragweite betreffenden Regelungen vom 29. März 2021 (BGBl. I S. 370)",
    "Gesetz zur Verlängerung der Aussetzung der Insolvenzantragspflicht und des Anfechtungsschutzes für pandemiebedingte Stundungen sowie zur Verlängerung der Steuererklärungsfrist in beratenen Fällen und der zinsfreien Karenzzeit für den Veranlagungszeitraum 2019 vom 15. Februar 2021 (BGBl. I S. 237)",
    "Gesetz über eine einmalige Sonderzahlung aus Anlass der COVID-19-Pandemie an Besoldungs- und Wehrsoldempfänger vom 21. Dezember 2020 (BGBl. I S. 3136)",
    "Gesetz zur Beschäftigungssicherung infolge der COVID-19-Pandemie (Beschäftigungssicherungsgesetz – BeschSiG) vom 3. Dezember 2020 (BGBl. I S. 2691)",
    "Drittes Gesetz zum Schutz der Bevölkerung bei einer epidemischen Lage von nationaler Tragweite vom 18. November 2020 (BGBl. I S. 2397)",
    "Verordnung zur Umsetzung pandemiebedingter und weiterer Anpassungen in Rechtsverordnungen auf Grundlage des Energiewirtschaftsgesetzes vom 30. Oktober 2020 (BGBl. I S. 2269)",
    "Gesetz zur Änderung des Bundeswahlgesetzes und des Gesetzes über Maßnahmen im Gesellschafts-, Genossenschafts-, Vereins-, Stiftungs- und Wohnungseigentumsrecht zur Bekämpfung der Auswirkungen der COVID-19-Pandemie vom 28. Oktober 2020 (BGBl. I S. 2264)",
    "Gesetz für ein Zukunftsprogramm Krankenhäuser (Krankenhauszukunftsgesetz) vom 23. Oktober 2020 (BGBl. I S. 2208)",
    "Gesetz zur finanziellen Entlastung der Kommunen und der neuen Länder vom 6. Oktober 2020 (BGBl. I S. 2072)",
    "Gesetz zur Änderung des Grundgesetzes (Artikel 104a und 143h) vom 29. September 2020 (BGBl. I S. 2048)",
    "Gesetz zur Änderung des COVID-19-Insolvenzaussetzungsgesetzes vom 25. September 2020 (BGBl. I S. 2016)",
    "Gesetz über begleitende Maßnahmen zur Umsetzung des Konjunktur- und Krisenbewältigungspakets vom 14. Juli 2020 (BGBl. I S. 1683)",
    "Gesetz über die Feststellung eines Zweiten Nachtrags zum Bundeshaushaltsplan für das Haushaltsjahr 2020 (Zweites Nachtragshaushaltsgesetz 2020) vom 14. Juli 2020 (BGBl. I S. 1669)",
    "Gesetz zur Abmilderung der Folgen der COVID-19-Pandemie im Pauschalreisevertragsrecht und zur Sicherstellung der Funktionsfähigkeit der Kammern im Bereich der Bundesrechtsanwaltsordnung, der Bundesnotarordnung, der Wirtschaftsprüferordnung und des Steuerberatungsgesetzes während der COVID-19-Pandemie vom 10. Juli 2020 (BGBl. I S. 1643)\n  enthält: COVID-19-Gesetz zur Funktionsfähigkeit der Kammern",
    "Gesetz zur Gewährleistungsübernahme im Rahmen eines Europäischen Instruments zur vorübergehenden Unterstützung bei der Minderung von Arbeitslosigkeitsrisiken infolge des COVID-19-Ausbruchs und zur Änderung des Stabilisierungsfondsgesetzes und des Wirtschaftsstabilisierungsbeschleunigungsgesetzes sowie erforderliche Folgeänderungen vom 10. Juli 2020 (BGBl. I S. 1633)\n  enthält: SURE-Gewährleistungsgesetz",
    "Zweites Gesetz zur Umsetzung steuerlicher Hilfsmaßnahmen zur Bewältigung der Corona-Krise (Zweites Corona-Steuerhilfegesetz) vom 29. Juni 2020 (BGBl. I S. 1512)",
    "Gesetz zur Umsetzung steuerlicher Hilfsmaßnahmen zur Bewältigung der Corona-Krise (Corona-Steuerhilfegesetz) vom 19. Juni 2020 (BGBl. I S. 1385)",
    "Gesetz zur Aussetzung des Anpassungsverfahrens gemäß Paragraf 11 Absatz 4 des Abgeordnetengesetzes für das Jahr 2020 sowie zur Änderung des Abgeordnetengesetzes (Anpassungsverfahrensaussetzungsgesetz 2020) (BGBl. I S. 1161)",
    "Gesetz zur Unterstützung von Wissenschaft und Studierenden aufgrund der COVID-19-Pandemie (Wissenschafts- und Studierendenunterstützungsgesetz) vom 25. Mai 2020 (BGBl. I S. 1073)",
    "Gesetz zur Abmilderung der Folgen der COVID-19-Pandemie im Wettbewerbsrecht und für den Bereich der Selbstverwaltungsorganisationen der gewerblichen Wirtschaft vom 25. Mai 2020 (BGBl. I S. 1067)",
    "Zweites Gesetz zur Änderung des Bundespersonalvertretungsgesetzes und weiterer dienstrechtlicher Vorschriften aus Anlass der COVID-19-Pandemie vom 25. Mai 2020 (BGBl. I S. 1063)",
    "Gesetz für Maßnahmen im Elterngeld aus Anlass der Covid-19-Pandemie vom 20. Mai 2020 (BGBl. I S. 1061)",
    "Gesetz zu sozialen Maßnahmen zur Bekämpfung der Corona-Pandemie (Sozialschutz-Paket II) vom 20. Mai 2020 (BGBl. I S. 1055)",
    "Gesetz zur Sicherstellung ordnungsgemäßer Planungs- und Genehmigungsverfahren während der COVID-19-Pandemie (Planungssicherstellungsgesetz) vom 20. Mai 2020 (BGBl. I S. 1041)",
    "Zweites Gesetz zum Schutz der Bevölkerung bei einer epidemischen Lage von nationaler Tragweite vom 19. Mai 2020 (BGBl. I S. 1018)",
    "Gesetz zur Abmilderung der Folgen der COVID-19-Pandemie im Veranstaltungsvertragsrecht und im Recht der Europäischen Gesellschaft (SE) und der Europäischen Genossenschaft (SCE) vom 15. Mai 2020 (BGBl. I S. 948)",
    "Gesetz zum Schutz der Bevölkerung bei einer epidemischen Lage von nationaler Tragweite vom 27. März 2020 (BGBl. I S. 587)",
    "Gesetz zum Ausgleich COVID-19 bedingter finanzieller Belastungen der Krankenhäuser und weiterer Gesundheitseinrichtungen (COVID-19-Krankenhausentlastungsgesetz) vom 27. März 2020 (BGBl. I S. 580)",
    "Gesetz für den erleichterten Zugang zu sozialer Sicherung und zum Einsatz und zur Absicherung sozialer Dienstleister aufgrund des Coronavirus SARS-CoV-2 (Sozialschutz-Paket) vom 27. März 2020 (BGBl. I S. 575)\n  enthält: Sozialdienstleister-Einsatzgesetz",
    "Gesetz zur Abmilderung der Folgen der COVID-19-Pandemie im Zivil-, Insolvenz- und Strafverfahrensrecht vom 27. März 2020 (BGBl. I S. 569)\n  enthält: COVID-19-Insolvenzaussetzungsgesetz\n  enthält: Gesetz über Maßnahmen im Gesellschafts-, Genossenschafts-, Vereins-, Stiftungs- und Wohnungseigentumsrecht zur Bekämpfung der Auswirkungen der COVID-19-Pandemie",
    "Gesetz über die Feststellung eines Nachtrags zum Bundeshaushaltsplan für das Haushaltsjahr 2020 (Nachtragshaushaltsgesetz 2020) vom 27. März 2020 (BGBl. I S. 556)",
    "Gesetz zur Errichtung eines Wirtschaftsstabilisierungsfonds (Wirtschaftsstabilisierungsfondsgesetz) vom 27. März 2020 (BGBl. I S. 543)",
    "Gesetz zur befristeten krisenbedingten Verbesserung der Regelungen für das Kurzarbeitergeld vom 13. März 2020 (BGBl. I S. 493)",
    # ── Verordnungen ────────────────────────────────────────────────────────
    "Erste Verordnung zur Änderung der COVID-19-Schutzmaßnahmen-Ausnahmenverordnung vom 10. Dezember 2021",
    "Verordnung zur Änderung der Coronavirus-Testverordnung, der DIVI IntensivRegister-Verordnung und der Coronavirus-Surveillanceverordnung vom 12. November 2021 (BAnz AT 12.11.2021 V1)",
    "Erste Verordnung zur Änderung der Pflegepersonaluntergrenzen-Verordnung vom 8. November 2021 (BGBl. I S. 4792)",
    "COVID-19-Schutzmaßnahmen-Ausnahmenverordnung vom 8. Mai 2021 (BAnz AT 08.05.2021 V1)",
    "Verordnung zum Anspruch auf Schutzimpfung gegen das Coronavirus SARS-CoV-2 (Coronavirus-Impfverordnung – CoronaImpfV) vom 31. März 2021 (BAnz AT 01.04.2021 V1)",
    "Erste Verordnung zur Änderung der Coronavirus-Einreiseverordnung vom 26. März 2021 (BAnz AT 26.03.2021 V1)",
    "Erste Verordnung zur Änderung der Coronavirus-Impfverordnung vom 24. Februar 2021 (BAnz AT 24.02.2021 V1)",
    "Verordnung zum Anspruch auf Schutzimpfung gegen das Coronavirus SARS-CoV-2 (Coronavirus-Impfverordnung – CoronaImpfV) vom 8. Februar 2021 (BAnz AT 08.02.2021 V1)",
    "Erste Verordnung zur Änderung der Coronavirus-Schutzmasken-Verordnung vom 4. Februar 2021 (BAnz AT 05.02.2021 V1)",
    "Dritte Verordnung zur Änderung der Medizinprodukte-Abgabeverordnung im Rahmen der epidemischen Lage von nationaler Tragweite vom 1. Februar 2021 (BAnz AT 02.02.2021 V1)",
    "Verordnung zum Schutz vor einreisebedingten Infektionsgefahren in Bezug auf neuartige Mutationen des Coronavirus SARS-CoV-2 (Coronavirus-Schutzverordnung – CoronaSchV) vom 29. Januar 2021 (BAnz AT 29.01.2021 V1)",
    "Verordnung über die Aufstellung von Wahlbewerbern und die Wahl der Vertreter für die Vertreterversammlungen für die Wahl zum 20. Deutschen Bundestag unter den Bedingungen der COVID-19-Pandemie (COVID-19-Wahlbewerberaufstellungsverordnung) (BGBl. I S. 115)",
    "Verordnung zum Anspruch auf Testung in Bezug auf einen direkten Erregernachweis des Coronavirus SARS-CoV-2 (Coronavirus-Testverordnung – TestV) vom 27. Januar 2021 (BAnz AT 27.01.2021 V2)",
    "SARS-CoV-2-Arbeitsschutzverordnung (Corona-ArbSchV) vom 21. Januar 2021 (BAnz AT 22.01.2021 V1)",
    "Verordnung zur molekulargenetischen Surveillance des Coronavirus SARS-CoV-2 (Coronavirus-Surveillanceverordnung – CorSurV) vom 18. Januar 2021 (BAnz AT 19.01.2021 V2)",
    "Erste Verordnung zur Änderung der Coronavirus-Testverordnung vom 15. Januar 2021 (BAnz AT 15.01.2021 V1)",
    "Verordnung zum Schutz vor einreisebedingten Infektionsgefahren in Bezug auf das Coronavirus SARS-CoV-2 (Coronavirus-Einreiseverordnung – CoronaEinreiseV) vom 13. Januar 2021 (BAnz AT 13.01.2021 V1)",
    "Verordnung zur Anpassung der Voraussetzungen für die Anspruchsberechtigung der Krankenhäuser nach § 21 Absatz 1a des Krankenhausfinanzierungsgesetzes vom 22. Dezember 2020 (BAnz AT 24.12.2020 V1)",
    "Verordnung zum Schutz vor einreisebedingten Infektionsgefahren in Bezug auf neuartige Mutationen des Coronavirus SARS-CoV-2 (Coronavirus-Schutzverordnung – CoronaSchV) vom 21. Dezember 2020 (BAnz AT 21.12.2020 V4)",
    "Verordnung zum Anspruch auf Schutzimpfung gegen das Coronavirus SARS-CoV-2 (Coronavirus-Impfverordnung – CoronaImpfV) vom 18. Dezember 2020 (BAnz AT 21.12.2020 V3)",
    "Dritte Verordnung zur Änderung der Ersten Verordnung zum Sprengstoffgesetz vom 18. Dezember 2020 (BAnz AT 21.12.2020 V1)",
    "Verordnung zum Anspruch auf Schutzmasken zur Vermeidung einer Infektion mit dem Coronavirus SARS-CoV-2 (Coronavirus-Schutzmasken-Verordnung – SchutzmV) vom 14. Dezember 2020 (BAnz AT 15.12.2020 V1)",
    "Preisverordnung für SARS-CoV-2 Antigen-Tests zur patientennahen Anwendung (AntigenPreisV) vom 7. Dezember 2020 (BAnz AT 08.12.2020 V1)",
    "Verordnung zur Änderung der Medizinprodukte-Abgabeverordnung im Rahmen der epidemischen Lage von nationaler Tragweite vom 2. Dezember 2020 (BAnz AT 03.12.2020 V1)",
    "Verordnung zum Anspruch auf Testung in Bezug auf einen direkten Erregernachweis des Coronavirus SARS-CoV-2 (Coronavirus-Testverordnung – TestV) vom 30. November 2020 (BAnz AT 01.12.2020 V1)",
    "Verordnung zur Testpflicht von Einreisenden aus Risikogebieten vom 4. November 2020 (BAnz AT 06.11.2020 V1)",
    "Verordnung zur Verlängerung von Maßnahmen im Gesellschafts-, Genossenschafts-, Vereins- und Stiftungsrecht zur Bekämpfung der Auswirkungen der COVID-19-Pandemie (GesRGenRCOVMVV) vom 20. Oktober 2020 (BGBl. I S. 2258)",
    "Verordnung zur Erhebung von Garantieprämien für die ergänzende staatliche Absicherung von Reisegutscheinen wegen der COVID-19-Pandemie (Garantieprämienerhebungsverordnung – GPEV) vom 15. Oktober 2020 (BGBl. I S. 2178)",
    "Verordnung zum Anspruch auf Testung in Bezug auf einen direkten Erregernachweis des Coronavirus SARS-CoV-2 (Coronavirus-Testverordnung – TestV) vom 14. Oktober 2020 (BAnz AT 14.10.2020 V1)",
    "Zweite Verordnung über die Bezugsdauer für das Kurzarbeitergeld (Zweite Kurzarbeitergeldbezugsdauerverordnung – 2. KugBeV) vom 12. Oktober 2020 (BGBl. I S. 2165)",
    "Verordnung zur Änderung der COVID-19-Versorgungsstrukturen-Schutzverordnung vom 29. September 2020 (BAnz AT 30.09.2020 V2)",
    "Erste Verordnung zur Änderung der SARS-CoV-2-Arzneimittelversorgungsverordnung vom 28. September 2020 (BAnz AT 30.09.2020 V1)",
    "Erste Verordnung zur Änderung der Vereinfachter-Zugang-Verlängerungsverordnung vom 16. September 2020 (BGBl. I S. 2001)",
    "Zweite Verordnung zur Änderung der Verordnung zum Anspruch auf bestimmte Testungen für den Nachweis des Vorliegens einer Infektion mit dem Coronavirus SARS-CoV-2 vom 11. September 2020 (BAnz AT 14.09.2020 V1)",
    "Verordnung zur Testpflicht von Einreisenden aus Risikogebieten vom 6. August 2020 (BAnz AT 07.08.2020 V1)",
    "Verordnung zur Änderung der Verordnung zum Anspruch auf bestimmte Testungen für den Nachweis des Vorliegens einer Infektion mit dem Coronavirus SARS-CoV-2 vom 31. Juli 2020 (BAnz AT 31.07.2020 V1)",
    "ITS-Arzneimittelbevorratungsverordnung vom 7. Juli 2020 (BAnz AT 08.07.2020 V1)",
    "Verordnung zur Anpassung der Ausgleichszahlungen an Krankenhäuser aufgrund von Sonderbelastungen durch das Coronavirus SARS-CoV-2 (COVID-19-Ausgleichszahlungs-Anpassungs-Verordnung – AusglZAV) vom 3. Juli 2020 (BGBl. I S. 1556)",
    "Verordnung über von den Approbationsordnungen für Ärzte, Zahnärzte und Apotheker abweichende Vorschriften bei Vorliegen einer epidemischen Lage von nationaler Tragweite (BAnz AT 03.07.2020 V1)",
    "Verordnung zur Verlängerung des Zeitraums für das vereinfachte Verfahren für den Zugang zu den Grundsicherungssystemen und für Bedarfe für Mittagsverpflegung aus Anlass der COVID-19-Pandemie (Vereinfachter-Zugang-Verlängerungsverordnung) vom 25. Juni 2020 (BGBl. I S. 1509)",
    "Verordnung zur Verlängerung der vorübergehenden Befreiung von Inhabern ablaufender Schengen-Visa und zur vorübergehenden Befreiung zur Durchreise zum Zweck der Ausreise aus dem Schengen-Raum vom Erfordernis eines Aufenthaltstitels auf Grund der COVID-19-Pandemie (2. Schengen-COVID-19-Pandemie-Verordnung – 2. Schengen-COVID-19-V) vom 17. Juni 2020 (BAnz AT 18.06.2020 V1)",
    "Verordnung zur Sicherung der Ausbildungen in den Gesundheitsfachberufen während einer epidemischen Lage von nationaler Tragweite vom 10. Juni 2020 (BAnz AT 12.06.2020 V1)",
    "Verordnung zum Anspruch auf bestimmte Testungen für den Nachweis des Vorliegens einer Infektion mit dem Coronavirus SARS-CoV-2 vom 8. Juni 2020 (BAnz AT 09.06.2020 V1)",
    "Verordnung zur Sicherstellung der Versorgung der Bevölkerung mit Produkten des medizinischen Bedarfs bei der durch das Coronavirus SARS-CoV-2 verursachten Epidemie (Medizinischer Bedarf Versorgungssicherstellungsverordnung – MedBVSV) vom 25. Mai 2020 (BAnz AT 26.05.2020 V1)",
    "COVID-19-Versorgungsstrukturen-Schutzverordnung vom 30. April 2020 (BAnz AT 04.05.2020 V1)",
    "Verordnung zur Abgrenzung der Steuerpflicht nach dem Kraftfahrzeugsteuergesetz infolge der SARS-CoV-2-Pandemie (SARSCoV2-Kraftfahrzeugsteuer-Verordnung) vom 24. April 2020 (BGBl. I S. 845)",
    "Fünfte Verordnung zur Änderung der Wahlordnung zum Bundespersonalvertretungsgesetz vom 24. April 2020 (BAnz AT 28.04.2020 V1)",
    "Verordnung über Abweichungen von den Vorschriften des Fünften Buches Sozialgesetzbuch, des Apothekengesetzes, der Apothekenbetriebsordnung, der Arzneimittelpreisverordnung, des Betäubungsmittelgesetzes und der Betäubungsmittel-Verschreibungsverordnung infolge der SARS-CoV-2-Epidemie (SARS-CoV-2-Arzneimittelversorgungsverordnung) vom 20. April 2020 (BAnz AT 21.04.2020 V1)",
    "Kurzarbeitergeldbezugsdauerverordnung vom 16. April 2020 (BGBl. I S. 801)",
    "Verordnung zur Aufrechterhaltung und Sicherung intensivmedizinischer Krankenhauskapazitäten (DIVI IntensivRegister-Verordnung) vom 8. April 2020 (BAnz AT 09.04.2020 V4)",
    "Verordnung zur Beschaffung von Medizinprodukten und persönlicher Schutzausrüstung bei der durch das Coronavirus SARS-CoV-2 verursachten Epidemie vom 8. April 2020 (BAnz AT 09.04.2020 V3)",
    "Verordnung zur vorübergehenden Befreiung von Inhabern ablaufender Schengen-Visa vom Erfordernis eines Aufenthaltstitels auf Grund der COVID-19-Pandemie (Schengen-Visa-COVID-19-Pandemie-Verordnung – SchengenVisaCOVID-19-V) vom 8. April 2020 (BAnz AT 09.04.2020 V1)",
    "Verordnung zu Abweichungen vom Arbeitszeitgesetz infolge der COVID-19-Epidemie (COVID-19-Arbeitszeitverordnung – COVID-19-ArbZV) vom 7. April 2020 (BAnz AT 09.04.2020 V2)",
    "Verordnung zur Abweichung von der Approbationsordnung für Ärzte bei einer epidemischen Lage von nationaler Tragweite vom 30. März 2020 (BAnz AT 31.03.2020 V1)",
    "Erste Verordnung zur Änderung der Pflegepersonaluntergrenzen-Verordnung vom 25. März 2020 (BGBl. I S. 596)",
    "Kurzarbeitergeldverordnung vom 25. März 2020 (BGBl. I S. 595)",
    'Verordnung über die Ausdehnung der Meldepflicht nach § 6 Absatz 1 Satz 1 Nummer 1 und § 7 Absatz 1 Satz 1 des Infektionsschutzgesetzes auf Infektionen mit dem erstmals im Dezember 2019 in Wuhan/Volksrepublik China aufgetretenen neuartigen Coronavirus („2019-nCoV") vom 30. Januar 2020 (BAnz AT 31.01.2020 V1)',
    # ── Weitere Bekanntmachungen ─────────────────────────────────────────────
    'Regelung zur vorübergehenden Gewährung von Beihilfen für niedrigverzinsliche Darlehen und Direktbeteiligungen im Rahmen von Konsortialkrediten im Zusammenhang mit dem Ausbruch von COVID-19 („Bundesregelung Beihilfen für niedrigverzinsliche Darlehen 2020") vom 16. Februar 2021 (BAnz AT 01.03.2021 B3)',
    'Regelung zur Gewährung von Unterstützung für ungedeckte Fixkosten im Zusammenhang mit dem Ausbruch von COVID-19 („Bundesregelung Fixkostenhilfe 2020") vom 12. Februar 2021 (BAnz AT 01.03.2021 B2)',
    'Vierte geänderte Regelung zur vorübergehenden Gewährung geringfügiger Beihilfen im Zusammenhang mit dem Ausbruch von COVID-19 („Vierte Geänderte Bundesregelung Kleinbeihilfen 2020") vom 12. Februar 2021 (BAnz AT 01.03.2021 B1)',
    "Beschluss des Gemeinsamen Bundesausschusses zu Richtlinien über veranlasste Leistungen: COVID-19-Epidemie – Verlängerung befristeter bundeseinheitlicher Sonderregelungen vom 21. Januar 2021 (BAnz AT 22.02.2021 B3)",
    "Richtlinie über eine zusätzliche Einmalzahlung an Personen, die Einmalleistungen nach den WDF-Richtlinien oder den AKG-Härterichtlinien erhalten haben, zur Abmilderung des pandemiebedingten Mehrbedarfs (Corona-Sonderzahlungsrichtlinie) vom 18. Januar 2021 (BAnz AT 29.01.2021 B1)",
    "Richtlinie über die vorübergehende Gewährung von Billigkeitsleistungen zum Ausgleich von Einnahmeausfällen in der Reisebusbranche im Zusammenhang mit dem Ausbruch von COVID-19 vom 18. Dezember 2020 (BAnz AT 24.12.2020 B4)",
    "Beschluss des Gemeinsamen Bundesausschusses über eine Änderung der Richtlinie ambulante spezialfachärztliche Versorgung nach § 116b SGB V: Ausnahmeregelungen für die Aufnahme von Leistungen aufgrund der COVID-19-Pandemie vom 17. Dezember 2020 (BAnz AT 03.02.2021 B4)",
    "Bekanntmachung eines Beschlusses des Gemeinsamen Bundesausschusses über die 25. Änderung der DMP-Anforderungen-Richtlinie – Verlängerung der Ausnahmeregelungen für Schulungen und Dokumentationen aufgrund der COVID-19-Pandemie vom 17. Dezember 2020 (BAnz AT 14.01.2021 B4)",
    "Bekanntmachung der Richtlinie für die Bundesförderung von Produktionsanlagen von Point-of-Care-Antigentests zum Nachweis von SARS-CoV-2 vom 10. Dezember 2020 (BAnz AT 15.12.2020 B1)",
    "Bekanntmachung eines Beschlusses des Gemeinsamen Bundesausschusses über eine Änderung der Arbeitsunfähigkeits-Richtlinie: COVID-19-Epidemie – Verlängerung der bundesweiten Sonderregelung zur telefonischen Feststellung von Arbeitsunfähigkeit vom 3. Dezember 2020 (BAnz AT 17.12.2020 B9)",
    "Beschluss des Gemeinsamen Bundesausschusses über Änderungen verschiedener Qualitätssicherungs-Richtlinien: COVID-19 – Ausnahmen zu QS-Anforderungen vom 3. Dezember 2020 (BAnz AT 03.02.2021 B2)",
    'Bekanntmachung der dritten geänderten Regelung zur vorübergehenden Gewährung geringfügiger Beihilfen im Zusammenhang mit dem Ausbruch von COVID-19 („Dritte Geänderte Bundesregelung Kleinbeihilfen 2020") vom 2. Dezember 2020 (BAnz AT 03.12.2020 B2)',
    "Bekanntmachung der Richtlinie über die Gewährung von Billigkeitsleistungen an Einrichtungen der Behindertenhilfe, Inklusionsbetriebe, Sozialkaufhäuser und Sozialunternehmen zum Ausgleich von Schäden infolge der Corona-Pandemie vom 25. November 2020 (BAnz AT 11.12.2020 B3)",
    'Bekanntmachung der geänderten Regelung zur vorübergehenden Gewährung von Bürgschaften, Rückbürgschaften und Garantien im Zusammenhang mit dem Ausbruch von COVID-19 („Bundesregelung Bürgschaften 2020") vom 25. November 2020 (BAnz AT 07.12.2020 B1)',
    'Änderung der Bekanntmachung der Regelung zur vorübergehenden Gewährung von Beihilfen im Zusammenhang mit dem Ausbruch von COVID-19 („Bundesregelung Forschungs-, Entwicklungs- und Investitionsbeihilfen") vom 24. November 2020 (BAnz AT 01.12.2020 B5)',
    "Bekanntmachung eines Beschlusses des Gemeinsamen Bundesausschusses über eine Änderung der Regelungen zu einem gestuften System von Notfallstrukturen in Krankenhäusern gemäß § 136c Absatz 4 SGB V: Ausnahmeregelung zur Aufnahmebereitschaft für beatmungspflichtige Intensivpatienten vom 20. November 2020 (BAnz AT 24.12.2020 B2)",
    'Bekanntmachung der Regelung zur Gewährung von Unterstützung für ungedeckte Fixkosten im Zusammenhang mit dem Ausbruch von COVID-19 („Bundesregelung Fixkostenhilfe 2020") vom 20. November 2020 (BAnz AT 14.12.2020 B2)',
    "Bekanntmachung eines Beschlusses des Gemeinsamen Bundesausschusses über Änderungen verschiedener Qualitätssicherungs-Richtlinien: COVID-19 – Ausnahmen von Mindestanforderungen an das Pflegepersonal vom 20. November 2020 (BAnz AT 16.12.2020 B2)",
    'Bekanntmachung der Regelung zur vorübergehenden Gewährung von Beihilfen für niedrigverzinsliche Darlehen und Direktbeteiligungen im Rahmen von Konsortialkrediten im Zusammenhang mit dem Ausbruch von COVID-19 („Bundesregelung Beihilfen für niedrigverzinsliche Darlehen 2020") vom 20. November 2020 (BAnz AT 14.12.2020 B1)',
    "Bekanntmachung eines Beschlusses des Gemeinsamen Bundesausschusses über eine Änderung der Arbeitsunfähigkeits-Richtlinie: COVID-19-Epidemie – Bundesweite Sonderregelung zur telefonischen Feststellung von Arbeitsunfähigkeit vom 15. Oktober 2020 (BAnz AT 12.11.2020 B3)",
    "Bekanntmachung eines Beschlusses des Gemeinsamen Bundesausschusses zu Richtlinien über veranlasste Leistungen: COVID-19-Epidemie – Befristete bundeseinheitliche Sonderregelungen vom 30. Oktober 2020 (BAnz AT 06.11.2020 B2)",
    "Bekanntmachung der Begründung zur Verordnung zur Verlängerung von Maßnahmen im Gesellschafts-, Genossenschafts-, Vereins- und Stiftungsrecht zur Bekämpfung der Auswirkungen der COVID-19-Pandemie vom 20. Oktober 2020 (BAnz AT 28.10.2020 B3)",
    "Bekanntmachung der Richtlinie für die Bundesförderung Corona-gerechte Um- und Aufrüstung von raumlufttechnischen Anlagen in öffentlichen Gebäuden und Versammlungsstätten vom 13. Oktober 2020 (BAnz AT 19.10.2020 B1)",
    "Bekanntmachung eines Beschlusses des Gemeinsamen Bundesausschusses über Änderungen der Häusliche Krankenpflege-Richtlinie, Soziotherapie-Richtlinie, Hilfsmittel-Richtlinie, Heilmittel-Richtlinien, Krankentransport-Richtlinie und Arbeitsunfähigkeits-Richtlinie: COVID-19-Epidemie – Verlängerung und Anpassung von Sonderregelungen vom 17. September 2020 (BAnz AT 30.09.2020 B2)",
    'Bekanntmachung der Regelung zur vorübergehenden Gewährung von Beihilfen für niedrigverzinsliche Darlehen und Direktbeteiligungen im Rahmen von Konsortialkrediten im Zusammenhang mit dem Ausbruch von COVID-19 („Bundesregelung Beihilfen für niedrigverzinsliche Darlehen 2020") vom 4. August 2020 (BAnz AT 19.08.2020 B1)',
    'Bekanntmachung der zweiten geänderten Regelung zur vorübergehenden Gewährung geringfügiger Beihilfen im Zusammenhang mit dem Ausbruch von COVID-19 („Zweite Geänderte Bundesregelung Kleinbeihilfen 2020") vom 3. August 2020 (BAnz AT 11.08.2020 B1)',
    "Änderung der Bekanntmachung der Richtlinie über die vorübergehende Gewährung von Billigkeitsleistungen zum Ausgleich von Einnahmeausfällen in der Reisebusbranche im Zusammenhang mit dem Ausbruch von COVID-19 vom 29. Juli 2020 (BAnz AT 05.08.2020 B5)",
    "Bekanntmachung eines Beschlusses des Gemeinsamen Bundesausschusses über eine Änderung der Regelungen zur Fortbildung im Krankenhaus (FKH-R): COVID-19 – Verlängerung der Nachweisfrist gemäß § 6 vom 16. Juli 2020 (BAnz AT 11.08.2020 B2)",
    "Bekanntmachung eines Beschlusses des Gemeinsamen Bundesausschusses über Änderungen der Heilmittel-Richtlinien und der Krankentransport-Richtlinie: Verlängerung und Anpassung von Sonderregelungen aufgrund der COVID-19-Pandemie vom 29. Juni 2020 (BAnz AT 28.07.2020 B3)",
    "Bekanntmachung eines Beschlusses des Gemeinsamen Bundesausschusses über eine Änderung der Richtlinie ambulante spezialfachärztliche Versorgung nach § 116b SGB V: Ausnahmeregelungen für die Aufnahme von Leistungen aufgrund der COVID-19-Pandemie vom 5. Juni 2020 (BAnz AT 23.07.2020 B2)",
    "Bekanntmachung der Richtlinie über die vorübergehende Gewährung von Billigkeitsleistungen zum Ausgleich von Einnahmeausfällen in der Reisebusbranche im Zusammenhang mit dem Ausbruch von COVID-19 vom 14. Juli 2020 (BAnz AT 17.07.2020 B6)",
    "Bekanntmachung der Verbindlichen Handlungsleitlinien für die Bundesverwaltung für die Vergabe öffentlicher Aufträge zur Beschleunigung investiver Maßnahmen zur Bewältigung der wirtschaftlichen Folgen der COVID-19-Pandemie vom 8. Juli 2020 (BAnz AT 13.07.2020 B2)",
    "Bekanntmachung eines Beschlusses des Gemeinsamen Bundesausschusses über eine Änderung der Arzneimittel-Richtlinie (AM-RL): Verlängerung der Sonderregelungen im Zusammenhang mit der COVID-19-Pandemie betreffend die §§ 8, 9 und 11 AM-RL vom 28. Mai 2020 (BAnz AT 29.06.2020 B6)",
    "Bekanntmachung eines Beschlusses des Gemeinsamen Bundesausschusses über Änderungen verschiedener Richtlinien (häusliche Krankenpflege, SAPV, Soziotherapie, Hilfsmittel, Heilmittel, Krankentransport, Arbeitsunfähigkeit): Verlängerung und Anpassung der Sonderregelungen aufgrund der COVID-19-Pandemie vom 28. Mai 2020 (BAnz AT 12.06.2020 B3)",
    "Bekanntmachung eines Beschlusses des Gemeinsamen Bundesausschusses über eine Änderung der Richtlinie Methoden vertragsärztliche Versorgung: Ausnahmeregelung von Vorgaben zur Qualitätssicherung im Zusammenhang mit der COVID-19-Pandemie vom 14. Mai 2020 (BAnz AT 12.06.2020 B2)",
    "Bekanntmachung eines Beschlusses des Gemeinsamen Bundesausschusses über eine Änderung der Richtlinie über Maßnahmen der Qualitätssicherung in Krankenhäusern (QSKH-RL): COVID-19 – Ausnahmen zu QS-Anforderungen vom 14. Mai 2020 (BAnz AT 03.06.2020 B3)",
    "Bekanntmachung eines Beschlusses des Gemeinsamen Bundesausschusses über eine Änderung der Kinder-Richtlinie: Ausnahmeregelung im Zusammenhang mit der COVID-19-Pandemie betreffend die Untersuchungszeiträume der U6 bis U9 vom 14. Mai 2020 (BAnz AT 29.05.2020 B6)",
    'Aufruf zur Einreichung von Interessenbekundungen zur Einrichtung von Forschungsprojekten im Kontext der Corona-Pandemie im Rahmen der Förderrichtlinie zur „Förderung der Forschung und Lehre im Bereich der Sozialpolitik" vom 12. Mai 2020 (BAnz AT 19.05.2020 B2)',
    "Richtlinie für die Bundesförderung von Produktionsanlagen von persönlicher Schutzausrüstung und dem Patientenschutz dienender Medizinprodukte sowie deren Vorprodukte vom 27. April 2020 (BAnz AT 30.04.2020 B3)",
    'Sonderaufruf „Ersatzmobilität für Personal in Kliniken, Pflegeeinrichtungen und Corona-Testlaboren – COVID-19" vom 21. April 2020 (BAnz AT 27.04.2020 B6)',
    "Richtlinie für die Gewährung von Bürgschaften für Liquiditätssicherungsdarlehen der Landwirtschaftlichen Rentenbank vom 16. April 2020 (BAnz AT 05.05.2020 B3)",
    "Bundesregelung Beihilfen für niedrigverzinsliche Darlehen 2020 vom 16. April 2020 (BAnz AT 24.04.2020 B2)",
    "Geänderte Bundesregelung Kleinbeihilfen 2020 vom 11. April 2020 (BAnz AT 24.04.2020 B1)",
    "Anordnungen gemäß § 5 des Infektionsschutzgesetzes nach Feststellung einer epidemischen Lage von nationaler Tragweite durch den Deutschen Bundestag vom 8. April 2020 (BAnz AT 09.04.2020 B7)",
    "Anordnung des Bundesministeriums für Gesundheit auf Grund von § 5 des Infektionsschutzgesetzes nach Feststellung einer epidemischen Lage von nationaler Tragweite durch den Deutschen Bundestag vom 31. März 2020",
    "Bundesregelung Kleinbeihilfen 2020 vom 26. März 2020 (BAnz AT 31.03.2020 B2)",
    "Änderung der Geschäftsordnung des Deutschen Bundestages vom 25. März 2020 (BGBl. I S. 764)",
    "Bundesregelung Bürgschaften 2020 vom 20. März 2020 (BAnz AT 31.03.2020 B1)",
    "Beschluss des Gemeinsamen Bundesausschusses über eine Änderung der Arbeitsunfähigkeits-Richtlinie: Ausnahmeregelung zur Feststellung von Arbeitsunfähigkeit aufgrund telefonischer Anamnese vom 20. März 2020 (BAnz AT 23.03.2020 B6) [inkl. mehrerer Folgebeschlüsse und Verlängerungen bis 29. April 2020]",
    "Beschluss des Gemeinsamen Bundesausschusses über Änderungen der Qualitätssicherungs-Richtlinie Früh- und Reifgeborene und weiterer Richtlinien: COVID-19 – Ausnahmen von Mindestanforderungen an das Pflegepersonal vom 20. März 2020 (BAnz AT 23.03.2020 B7)",
    "Bekanntmachung nach § 79 Absatz 5 des Arzneimittelgesetzes vom 16. März 2020 (BAnz AT 17.03.2020 B4)",
    "Bekanntmachung nach § 79 Absatz 5 des Arzneimittelgesetzes vom 26. Februar 2020 (BAnz AT 27.02.2020 B4)",
]

N = len(ITEMS)


def load_progress():
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    return {}


def save_progress(decisions):
    PROGRESS_FILE.write_text(
        json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def show_results(decisions):
    selected = [
        ITEMS[int(k)]
        for k, v in sorted(decisions.items(), key=lambda x: int(x[0]))
        if v == "y"
    ]
    print(f"\n{'='*60}")
    print(f"Selected {len(selected)} / {N} items\n")
    for item in selected:
        print(f"• {item.splitlines()[0]}")
    if selected:
        OUTPUT_FILE.write_text("\n\n".join(selected), encoding="utf-8")
        print(f"\nSaved to: {OUTPUT_FILE}")
    return selected


def run():
    decisions = load_progress()

    # Find first undecided item
    start = next((i for i in range(N) if str(i) not in decisions), N)

    if start == N:
        print("All items already decided.")
        show_results(decisions)
        return

    if start > 0:
        yes_so_far = sum(1 for v in decisions.values() if v == "y")
        print(f"Resuming from item {start + 1}/{N}  ({yes_so_far} selected so far)")

    i = start
    while i < N:
        yes_count = sum(1 for v in decisions.values() if v == "y")
        print(f"\n{'─'*60}")
        print(f"[{i + 1}/{N}]  ({yes_count} selected so far)\n")
        print(ITEMS[i])
        print("\n  y = yes   n / Enter = no   b = back   q = quit")

        try:
            choice = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            save_progress(decisions)
            print("\nInterrupted – progress saved.")
            sys.exit(0)

        if choice == "q":
            save_progress(decisions)
            print(f"\nProgress saved. {yes_count} selected so far.")
            sys.exit(0)
        elif choice == "b":
            if i > 0:
                i -= 1
            continue
        elif choice == "y":
            decisions[str(i)] = "y"
        else:
            decisions[str(i)] = "n"

        save_progress(decisions)
        i += 1

    show_results(decisions)


if __name__ == "__main__":
    run()
