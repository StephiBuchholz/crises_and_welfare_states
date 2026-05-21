# 2 processing german seed descriptions

"""
seed descriptions for cosine-similarity filtering social-policy relevant texts among retrieved BGBl I texts. part of pooled evaluation.

derived from:
    1) BMAS, "Soziale Sicherung im Überblick" (2023 edition), see data/external/bmas_soziale-sicherung-im-ueberblick.pdf
    2) BMBFSJF website crawled and seed descriptions produced with claude opus 4.6, https://www.bmbfsfj.bund.de/bmbfsfj/themen, April 2026


merged seed descriptions for cosine-similarity-based filtering (System 1)
in a pooled evaluation pipeline (3 systems) for identifying social-policy legislation
within the German federal legislative corpus (BGBl Teil I, 2008–2022).


in this system 1, five source documents, each covering a different policy era are used:
  1. BMAS "Soziale Sicherung im Überblick" (2025) [data/external/bmas_soziale-sicherung-im-ueberblick.pdf] 
  2. BMBFSFJ-derived [https://www.bmbfsfj.bund.de/bmbfsfj/themen, April 2026]  
  3. COVID Wikipedia list [step1_process_ger_seed_desc_covid.py]
  4. BMAS Sozialbericht 2009 (16. Legislaturperiode, ~2005–2009)
  5. BMAS Sozialbericht 2017 (18. Legislaturperiode, ~2013–2017)

seed descriptions were computed by Claude Opus 4.6 in a single run per
source document, then merged and deduplicated. seeds are kept era-specific
rather than collapsed by policy field, because era-distinct vocabulary
(e.g. "Quali-KUG" in 2009, "Sozialschutzpaket" in 2020) likely provides sharper
lexical anchors for cosine similarity.

near-duplicates across sources resolved by keeping the more specific version
or splitting out the distinctive terms. 

why pooled evaluation?

    pooled evaluation is applied because no single filtering method can
    guarantee completeness; using multiple systems with weakly correlated
    recall failures reduces the risk of systematic omissions.

    this is one of three retrieval systems in the pooled evaluation. Systems 2
    (keyword/regex on SGB references) and 3 (BERTopic or TF-IDF) use different
    detection mechanisms. The union of all three systems' candidate sets is
    manually assessed for relevance; a random sample of the rejected set is
    checked to verify completeness.

"""

SEED_DESCRIPTIONS_MERGED = {
 
    # ══════════════════════════════════════════════════════════════
    # EXISTING SEEDS (from 2025 BMAS brochure + BMBFSFJ + COVID)
    # ══════════════════════════════════════════════════════════════
 
    # ── 1. ARBEITSFÖRDERUNG (SGB III) ──────────────────────────────
    "arbeitsforderung": [
        "Arbeitslosengeld Anspruch Anwartschaftszeit Rahmenfrist",
        "Arbeitslosengeld I Arbeitslosengeld II",
        "Arbeitslosenhilfe",
        "Hartz I Hartz II Hartz III Hartz IV Reform Einführung der Grundsicherung für Arbeitsuchende",
        "Kurzarbeitergeld bei vorübergehendem Arbeitsausfall",
        "Saison-Kurzarbeitergeld Schlechtwetterzeit Baugewerbe",
        "Transferkurzarbeitergeld Betriebsänderung Personalanpassung",
        "Insolvenzgeld bei Zahlungsunfähigkeit des Arbeitgebers",
        "Förderung der beruflichen Weiterbildung Bildungsgutschein",
        "Qualifizierungschancengesetz Weiterbildung beschäftigter Arbeitnehmer",
        "Weiterbildung während Kurzarbeit Beschäftigungssicherungsgesetz",
        "Berufsausbildungsbeihilfe Auszubildende Lebensunterhalt",
        "Assistierte Ausbildung lernbeeinträchtigte sozial benachteiligte junge Menschen",
        "Einstiegsqualifizierung berufspraktische Erfahrungen Ausbildung",
        "Gründungszuschuss Aufnahme selbstständiger Tätigkeit Arbeitslosigkeit",
        "Einstiegsgeld Grundsicherung Beschäftigungsaufnahme",
        "Eingliederungszuschuss Arbeitgeber erschwerte Vermittlung",
        "Maßnahmen zur Aktivierung und beruflichen Eingliederung",
        "Vermittlungsbudget Förderung Anbahnung versicherungspflichtiger Beschäftigung",
        "Arbeitsmarktförderung Personen mit Migrationshintergrund Integration durch Qualifizierung",
        "Teilhabe von Menschen mit Behinderungen am Arbeitsleben berufliche Rehabilitation",
    ],
 
    # ── 2. ARBEITSRECHT ────────────────────────────────────────────
    "arbeitsrecht": [
        "Kündigungsschutzgesetz soziale Rechtfertigung Kündigung Arbeitsverhältnis",
        "Teilzeit- und Befristungsgesetz Brückenteilzeit Arbeitszeitreduzierung",
        "Entgeltfortzahlungsgesetz Lohnfortzahlung im Krankheitsfall",
        "Lohn Löhne Entgelt Gehalt Erwerbseinkommen",
        "Bundesurlaubsgesetz Mindesturlaub Arbeitnehmer",
        "Mutterschutzgesetz Beschäftigungsverbot schwangere Arbeitnehmerinnen",
        "Pflegezeitgesetz Familienpflegezeitgesetz Freistellung häusliche Pflege Angehöriger",
        "Arbeitnehmerüberlassungsgesetz Leiharbeit Zeitarbeit Überlassung",
        "Allgemeines Gleichbehandlungsgesetz Benachteiligungsverbot Diskriminierung Beschäftigung",
        "Nachweisgesetz wesentliche Arbeitsbedingungen Arbeitsvertrag",
    ],
 
    # ── 3. ARBEITSSCHUTZ ──────────────────────────────────────────
    "arbeitsschutz": [
        "Arbeitszeitgesetz Höchstarbeitszeit Ruhezeit Nachtarbeit Sonntagsarbeit",
        "Jugendarbeitsschutzgesetz Kinderarbeitsschutzverordnung",
        "SARS-CoV-2-Arbeitsschutzverordnung Infektionsschutz am Arbeitsplatz",
    ],
 
    # ── 4. BETRIEBSVERFASSUNG / MITBESTIMMUNG ─────────────────────
    "betriebsverfassung_mitbestimmung": [
        "Betriebsverfassungsgesetz Betriebsrat Mitbestimmung soziale Angelegenheiten",
        "Mitbestimmungsgesetz Montan-Mitbestimmung Aufsichtsrat Arbeitnehmervertreter",
        "Tarifvertragsgesetz Tarifautonomie Allgemeinverbindlicherklärung",
        "Europäischer Betriebsrat grenzübergreifende Unterrichtung Anhörung",
    ],
 
    # ── 5. BÜRGERGELD / GRUNDSICHERUNG FÜR ARBEITSUCHENDE (SGB II)
    "buergergeld": [
        "Bürgergeld Grundsicherung für Arbeitsuchende erwerbsfähige Hilfebedürftige SGB II",
        "Regelbedarf Regelbedarfsstufe Existenzminimum Fortschreibung",
        "Kosten der Unterkunft und Heizung Angemessenheit Wohnung SGB II",
        "Eingliederungsleistungen Jobcenter Vermittlung Arbeitsmarkt",
        "Bildung und Teilhabe Bildungspaket Kinder Jugendliche",
        "Sozialer Arbeitsmarkt Teilhabe am Arbeitsmarkt Langzeitarbeitslose öffentlich geförderte Beschäftigung",
        "Sanktionen Leistungsminderung Pflichtverletzung Mitwirkungspflicht",
        "Karenzzeit Vermögen Schonvermögen Bürgergeld-Gesetz",
    ],
 
    # ── 6. ZUSÄTZLICHE ALTERSVORSORGE ─────────────────────────────
    "zusaetzliche_altersvorsorge": [
        "Riester-Rente Zulagen Altersvorsorge private Vorsorge staatliche Förderung",
        "Betriebliche Altersversorgung Entgeltumwandlung Betriebsrentengesetz",
        "Altersvorsorgezulage Grundzulage Kinderzulage Altersvorsorgebeiträge",
    ],
 
    # ── 7. MINDESTLOHN ────────────────────────────────────────────
    "mindestlohn": [
        "Mindestlohngesetz allgemeiner gesetzlicher Mindestlohn Stundenlohn",
        "Mindestlohnkommission Anpassung Mindestlohn Erhöhung",
    ],
 
    # ── 8. RENTENVERSICHERUNG ─────────────────────────────────────
    "rentenversicherung": [
        "Gesetzliche Rentenversicherung Pflichtversicherung Beitragssatz Beitragsbemessungsgrenze",
        "Regelaltersrente Regelaltersgrenze Anhebung Rente mit 67",
        "Altersrente für besonders langjährig Versicherte 45 Jahre Wartezeit",
        "Rente wegen verminderter Erwerbsfähigkeit Erwerbsminderungsrente",
        "Hinterbliebenenrente Witwenrente Waisenrente Renten wegen Todes",
        "Rentenberechnung Entgeltpunkte Zugangsfaktor Rentenartfaktor aktueller Rentenwert",
        "Kindererziehungszeiten Mütterrente Anrechnung Rentenversicherung",
        "Grundrente Grundrentenzuschlag langjährige Versicherung niedriges Einkommen",
        "Rentenanpassung Rentenerhöhung Lohnentwicklung Nachholfaktor",
        "Freiwillige Versicherung Selbstständige Rentenversicherung",
        "Rehabilitation Prävention Erwerbsfähigkeit medizinische Rehabilitation Rentenversicherung",
        "Geringfügige Beschäftigung Minijob Rentenversicherungspflicht Pauschalbeitrag",
        "Flexi-Rente Hinzuverdienst Beschäftigung neben Altersrente flexible Übergänge",
    ],
 
    # ── 9. SOZIALHILFE (SGB XII) ─────────────────────────────────
    "sozialhilfe": [
        "Sozialhilfe Hilfe zum Lebensunterhalt nicht erwerbsfähige Hilfebedürftige SGB XII",
        "Grundsicherung im Alter und bei Erwerbsminderung vierte Kapitel SGB XII",
        "Hilfe zur Pflege Sozialhilfe stationäre häusliche Pflege",
        "Hilfe zur Überwindung besonderer sozialer Schwierigkeiten Wohnungslose",
        "Regelbedarf Sozialhilfe Regelbedarfsstufen Existenzminimum",
    ],
 
    # ── 10. UNFALLVERSICHERUNG (SGB VII) ──────────────────────────
    "unfallversicherung": [
        "Gesetzliche Unfallversicherung Arbeitsunfall Berufskrankheit Berufsgenossenschaft",
        "Unfallverhütungsvorschriften Prävention Arbeitsunfälle Berufsgenossenschaft",
        "Verletztengeld Übergangsgeld Unfallrente Leistungen Unfallversicherung",
        "Wegeunfall Versicherungsschutz Arbeitsweg",
    ],
 
    # ── 11. SOZIALVERSICHERUNG ALLGEMEIN / ÜBERGREIFEND ───────────
    "sozialversicherung_allgemein": [
        "Sozialversicherung Beitragssatz Beitragsbemessungsgrenze Sozialversicherungsbeiträge",
        "Krankenversicherung Pflegeversicherung Beitragssatz gesetzliche Krankenversicherung",
        "Sozialgerichtsbarkeit Sozialgericht Widerspruch Rechtsschutz",
        "Sozialdatenschutz Sozialgeheimnis Datenschutz Sozialleistungsträger",
    ],
 
    # ── 12. KRISENSPEZIFISCHE / QUERSCHNITTSTHEMEN (COVID) ────────
    "krisenbezogen_covid": [
        "Sozialschutzpaket COVID-19 Pandemie Erleichterungen Sozialleistungen",
        "Vereinfachter Zugang Grundsicherung Kurzarbeit Pandemie Corona",
        "Erleichterter Zugang Kurzarbeitergeld Anforderungen Arbeitsausfall",
        "Konjunkturpaket Stabilisierungsmaßnahmen Wirtschaftskrise soziale Sicherung",
        "Arbeitszeitverordnung Ausnahmen Höchstarbeitszeit Krisensituation",
        "Infektionsschutzgesetz Maßnahmen Pandemiebekämpfung Entschädigung Verdienstausfall",
        "Kinderkrankengeld Erweiterung Anspruch Betreuung pandemiebedingt",
        "Sonderzahlungen steuerfreie Corona-Prämie Beschäftigte",
        "Einmalige Sonderzahlung aus Anlass der COVID-19-Pandemie",
        "Beschäftigungssicherung infolge der COVID-19-Pandemie",
        "Konjunktur- und Krisenbewältigungspaket",
        "Minderung von Arbeitslosigkeitsrisiken infloge des COVID-19-Ausbruchs",
        "steuerlicher Hilfsmaßnahmen zur Bewältigung der Corona-Krise",
        "Unterstützung von Wissenschaft und Studierenden aufgrund der COVID-19-Pandemie",
        "Maßnahmen im Elterngeld aus Anlass der Covid-19-Pandemie",
        "erleichterten Zugang zu sozialer Sicherung",
        "sozialen Maßnahmen zur Bekämpfung der Corona-Pandemie Sozialschutz-Paket II Sozialschutz-Paket I",
        "SARS-CoV-2-Arbeitsschutzverordnung",
        "Verordnung über die Bezugsdauer für das Kurzarbeitergeld Kurzarbeitergeldverordnung Kurzarbeitergeldbezugsdauerverordnung",
        "Abweichungen vom Arbeitszeitgesetz infolge der COVID-19-Epidemie",
        "Überbrückungshilfe Soforthilfe Selbstständige Kleinunternehmer Krise",
        "Corona-Sonderzahlungsrichtlinie pandemiebedingten Mehrbedarfs Härterichtlinien Einmalleistungen",
    ],
 
    # ── 13. ELTERNGELD UND ELTERNZEIT ─────────────────────────────
    "elterngeld_elternzeit": [
        "Elterngeld Basiselterngeld ElterngeldPlus Partnerschaftsbonus Einkommensersatz",
        "Bundeselterngeld- und Elternzeitgesetz BEEG Anspruch Elterngeld Bezugszeitraum",
        "Elternzeit Anspruch Arbeitsverhältnis Kündigungsschutz Teilzeitarbeit",
        "Elterngeld Einkommensgrenze Bemessungszeitraum Partnerschaftsmonate",
        "Änderung Bundeselterngeld- und Elternzeitgesetz Einkommensgrenzen Bezugsdauer",
    ],
 
    # ── 14. KINDERGELD UND KINDERFREIBETRÄGE ──────────────────────
    "kindergeld_kinderfreibetrag": [
        "Kindergeld Bundeskindergeldgesetz BKGG Anspruch Auszahlung Familienkasse",
        "Kinderfreibetrag Einkommensteuergesetz EStG steuerliche Entlastung Familien",
        "Kinderzuschlag Familien geringes Einkommen Leistungen Bildung Teilhabe",
        "Kindergelderhöhung Anpassung Höhe Kindergeld Existenzminimum Kinder",
    ],
 
    # ── 15. UNTERHALTSRECHT UND UNTERHALTSVORSCHUSS ───────────────
    "unterhalt": [
        "Unterhaltsvorschussgesetz Alleinerziehende Unterhaltsvorschuss Anspruch Leistung",
        "Unterhaltsrecht Reform Kindesunterhalt Betreuungsunterhalt Barunterhalt",
    ],
 
    # ── 16. MUTTERSCHUTZ ──────────────────────────────────────────
    "mutterschutz": [
        "Mutterschutzgesetz MuSchG Beschäftigungsverbot Schwangerschaft Entbindung",
        "Mutterschaftsgeld Arbeitgeberzuschuss Mutterschutzfrist Kündigungsschutz Stillzeit",
        "Reform Mutterschutzgesetz Ausweitung Schülerinnen Studentinnen Schutzfristen",
        "Vertrauliche Geburt Schwangerschaftskonfliktgesetz Beratung Schwangere",
    ],
 
    # ── 17. KINDERBETREUUNG UND GANZTAG ───────────────────────────
    "kinderbetreuung_ganztag": [
        "Kinderförderungsgesetz KiföG Rechtsanspruch Betreuungsplatz Kindertagespflege",
        "KiTa-Qualitätsgesetz Qualität Kindertagesbetreuung Fachkraft-Kind-Schlüssel",
        "Ganztagsförderungsgesetz Rechtsanspruch Ganztagsbetreuung Grundschulkinder",
        "Finanzhilfen Bund Ausbau Tagesbetreuung Kinder Investitionsprogramm Kinderbetreuung",
        "Gute-KiTa-Gesetz Qualitätsentwicklung Kindertageseinrichtungen Beitragsentlastung",
        "Kinderbetreuung Tageseinrichtung Tagespflege Förderung frühkindliche Bildung",
    ],
 
    # ── 18. PFLEGE UND VEREINBARKEIT ──────────────────────────────
    "pflege_vereinbarkeit": [
        "Pflegezeitgesetz PflegeZG Pflegezeit Freistellung Angehörigenpflege Kündigungsschutz",
        "Familienpflegezeitgesetz FPfZG Familienpflegezeit Teilzeit Pflege Angehörige Darlehen",
    ],
 
    # ── 19. SONSTIGES (EXISTING) ──────────────────────────────────
    "manual_cat": [
        "Wohngeld WoGG Mietzuschuss Lastenzuschuss",
        "Soziale Pflegeversicherung SGB XI Grad der Pflegebedürftigkeit häusliche Pflege",
    ],
 
    # ══════════════════════════════════════════════════════════════
    # SUPPLEMENTARY SEEDS FROM SOZIALBERICHT 2009
    # ══════════════════════════════════════════════════════════════
 
    # ── 20. FINANZKRISE / KONJUNKTURPOLITIK (2008–2009) ───────────
    "finanzkrise_konjunktur_2009": [
        "Gesetz zur Sicherung von Beschäftigung und Stabilität in Deutschland Konjunkturpaket II",
        "Qualifizieren statt Entlassen Kurzarbeit Weiterqualifizierung Krisenbewältigung",
        "Bezugsdauer Kurzarbeitergeld Verlängerung 24 Monate Verordnung",
        "Erstattung Sozialversicherungsbeiträge Kurzarbeit Arbeitgeber Bundesagentur für Arbeit",
        "Erleichterung Voraussetzungen Kurzarbeit Vereinfachung Antragstellung",
        "ESF-Programm Qualifizierung während Kurzarbeit Quali-KUG Transferkurzarbeitergeld",
        "Beitragssatz Arbeitslosenversicherung Stabilisierung Stundung Darlehen Bundesagentur",
        "automatische Stabilisatoren Sozialversicherung konjunktureller Abschwung Binnennachfrage",
    ],
 
    # ── 21. ARBEITSMARKT / GRUNDSICHERUNG (2005–2009 ERA) ─────────
    "arbeitsmarkt_grundsicherung_2009": [
        "Neuausrichtung arbeitsmarktpolitische Instrumente Vermittlung Eingliederung",
        "JobPerspektive Beschäftigungsmöglichkeiten langzeitarbeitslose Bezieher Arbeitslosengeld II",
        "Weiterentwicklung Regelleistung Grundsicherung für Arbeitsuchende SGB II",
        "Neuorganisation Aufgabenwahrnehmung Arbeitsagenturen Kommunen Jobcenter",
        "Förderung Existenzgründungen Arbeitslose Selbstständigkeit",
        "Einstiegsqualifizierung Jugendlicher betriebliche Berufsausbildungsvorbereitung",
        "Ausbildungspakt Wirtschaft Bundesregierung Mobilisierung Ausbildungsplätze",
        "WeGebAU Programm Weiterbildung Geringqualifizierter beschäftigter älterer Arbeitnehmer",
        "Maßnahmen ältere Arbeitnehmerinnen Arbeitnehmer Initiative 50plus Beschäftigungspakt",
        "Regelsatzbemessung Sozialhilfe Einkommens- und Verbrauchsstichprobe Existenzminimum",
    ],
 
    # ── 22. ARBEITSRECHT (2005–2009 ERA) ──────────────────────────
    "arbeitsrecht_2009": [
        "Arbeitnehmer-Entsendegesetz branchenspezifische Mindestlöhne Neufassung",
        "Mindestarbeitsbedingungengesetz Modernisierung Erweiterung Branchen",
        "Rahmenbedingungen Langzeitkonten Wertguthaben Altersteilzeit Freistellung",
    ],
 
    # ── 23. ALTERSSICHERUNG (2005–2009 ERA) ───────────────────────
    "alterssicherung_2009": [
        "Anhebung Regelaltersgrenze stufenweise 65 auf 67 Rentenversicherung",
        "Schutzklausel Rentenanpassung Ausweitung Absicherung gegen Rentenkürzung",
        "Rentenanpassung 2008 Weitergeltung aktueller Rentenwerte Rentengarantie",
        "Riester-Rente steuerlich geförderte private Altersvorsorge Zulagen Eigenheimrentengesetz",
        "Portabilität Unverfallbarkeit betriebliche Altersversorgung Arbeitgeberwechsel",
        "Altersrente wegen Arbeitslosigkeit nach Altersteilzeitarbeit Vertrauensschutz",
    ],
 
    # ── 24. GESUNDHEIT / GKV (2005–2009 ERA) ─────────────────────
    "gesundheit_2009": [
        "GKV-Wettbewerbsstärkungsgesetz Gesundheitsreform Finanzreform Krankenversicherung",
        "Gesundheitsfonds einheitlicher Beitragssatz Risikostrukturausgleich morbiditätsorientiert",
        "Versicherungspflicht Personen ohne anderweitige Absicherung Krankheitsfall",
        "Reform Krankenhausfinanzierung Fallpauschalen Konvergenzphase Landesbasisfallwert",
        "Arzneimittelversorgungs-Wirtschaftlichkeitsgesetz AVWG Vertragsarztrechtsänderungsgesetz",
        "Reform private Krankenversicherung Basistarif Portabilität Alterungsrückstellung",
    ],
 
    # ── 25. PFLEGE (2005–2009 ERA) ────────────────────────────────
    "pflege_2009": [
        "Pflege-Weiterentwicklungsgesetz Leistungsverbesserung ambulant vor stationär Pflegegeld",
        "Pflegezeitgesetz kurzzeitige Arbeitsverhinderung Pflege naher Angehöriger zehn Arbeitstage",
        "Wohn- und Betreuungsvertragsgesetz Heimvertrag Verbraucherschutz Pflegebedürftige",
        "Pflegebedürftigkeitsbegriff Überarbeitung Begutachtung Pflegebedürftigkeit",
    ],
 
    # ── 26. FAMILIE / KINDER / JUGEND (2005–2009 ERA) ────────────
    "familie_kinder_2009": [
        "Erziehungsgeld Weiterentwicklung Elterngeld Einkommensersatz Partnermonate",
        "Kinderbetreuung Ausbau unter Dreijährige Rechtsanspruch Tagesbetreuungsausbaugesetz",
        "Schulbedarfspaket Schuljahresbeginn einmalige Leistung Kinder Grundsicherung",
        "Kindergeld Anhebung Kinderfreibetrag steuerliche Entlastung Familienleistungsausgleich",
        "Frühe Hilfen aktiver Kinderschutz Bundeskinderschutzgesetz",
        "BAföG Kinderbetreuungszuschlag Ausbildungsförderung Anpassung Bedarfssätze",
    ],
 
    # ── 27. WOHNEN (2005–2009 ERA) ────────────────────────────────
    "wohnen_2009": [
        "Wohngeldreform Leistungsverbesserung Heizkosten Wohngeldgesetz",
        "Eigenheimrentengesetz Wohn-Riester selbst genutztes Wohneigentum Altersvorsorge",
        "Soziale Stadt Städtebauförderung benachteiligte Quartiere Integration",
    ],
 
    # ── 28. WEITERE SICHERUNGSSYSTEME (2005–2009 ERA) ─────────────
    "weitere_2009": [
        "Gesetz Modernisierung gesetzliche Unfallversicherung Organisationsreform Berufsgenossenschaft",
        "Künstlersozialversicherung Erfassung abgabepflichtiger Verwerter Überprüfung Versicherte",
        "Landwirtschaftliche Sozialversicherung Alterssicherung Landwirte Krankenversicherung",
        "Soziale Entschädigung Bundesversorgungsgesetz Kriegsopferversorgung Opferentschädigung",
        "Asylbewerberleistungsgesetz Leistungen Asylsuchende Grundleistungen",
    ],
 
    # ══════════════════════════════════════════════════════════════
    # SUPPLEMENTARY SEEDS FROM SOZIALBERICHT 2017
    # ══════════════════════════════════════════════════════════════
 
    # ── 29. MINDESTLOHN / LEIHARBEIT / WERKVERTRÄGE (2013–2017) ──
    "mindestlohn_leiharbeit_2017": [
        "Tarifautonomiestärkungsgesetz allgemeiner gesetzlicher Mindestlohn Einführung",
        "Änderung Arbeitnehmerüberlassungsgesetz Leiharbeit Höchstüberlassungsdauer Equal Pay",
        "Missbrauch Werkvertragsgestaltungen verdeckte Arbeitnehmerüberlassung Bekämpfung",
    ],
 
    # ── 30. GRUNDSICHERUNG / SOZIALHILFE (2013–2017) ─────────────
    "grundsicherung_2017": [
        "Regelbedarfsermittlungsgesetz Neuermittlung Regelbedarfe Einkommens- und Verbrauchsstichprobe",
        "Gesamtkonzept Chancen eröffnen soziale Teilhabe sichern Abbau Langzeitarbeitslosigkeit",
        "ESF-Bundesprogramm Eingliederung langzeitarbeitsloser Leistungsberechtigter allgemeiner Arbeitsmarkt",
        "Netzwerke ABC Aktivierung Betreuung Chancen Jobcenter Langzeitarbeitslose",
        "Bildungs- und Teilhabepaket Leistungen Kinder Jugendliche Existenzminimum",
    ],
 
    # ── 31. MIGRATION / INTEGRATION / ASYL (2013–2017) ───────────
    "migration_integration_2017": [
        "Integrationsgesetz Arbeitsmarktzugang Geflüchtete Integrationskurse Wohnsitzregelung",
        "Asylverfahrensbeschleunigungsgesetz Asylpaket Verfahrensbeschleunigung sichere Herkunftsstaaten",
        "Anerkennungsgesetz ausländische Berufsqualifikationen Gleichwertigkeitsprüfung",
        "Förderung Integration Flüchtlinge Arbeitsmarkt Sprachkurse berufsbezogene Deutschförderung",
        "Reform Asylbewerberleistungsgesetz Leistungssätze Grundleistungen Analogleistungen",
    ],
 
    # ── 32. ALTERSSICHERUNG (2013–2017) ──────────────────────────
    "alterssicherung_2017": [
        "Rentenpaket abschlagsfreie Rente ab 63 besonders langjährig Versicherte",
        "Mütterrente Ausweitung Kindererziehungszeiten vor 1992 geborene Kinder",
        "Verbesserung Erwerbsminderungsrente Zurechnungszeit Verlängerung Absicherung",
        "Betriebsrentenstärkungsgesetz reine Beitragszusage Sozialpartnermodell Tarifebene",
        "BAV-Förderbetrag Geringverdiener betriebliche Altersversorgung steuerliche Förderung",
    ],
 
    # ── 33. GESUNDHEIT (2013–2017) ────────────────────────────────
    "gesundheit_2017": [
        "Präventionsgesetz Stärkung Prävention Gesundheitsförderung Lebenswelten Krankenkassen",
        "GKV-Versorgungsstärkungsgesetz medizinische Versorgung ländlicher Raum Niederlassung Ärzte",
        "Hospiz- und Palliativgesetz Ausbau Hospizversorgung Palliativversorgung flächendeckend",
        "Krankenhausstrukturgesetz Qualität Krankenhausversorgung Krankenhausplanung Strukturfonds",
        "E-Health-Gesetz digitale Gesundheitsversorgung Telematikinfrastruktur elektronische Gesundheitskarte",
        "GKV-Arzneimittelversorgungsstärkungsgesetz Arzneimittelpreise Nutzenbewertung AMNOG",
    ],
 
    # ── 34. PFLEGE (2013–2017) ────────────────────────────────────
    "pflege_2017": [
        "Erstes Pflegestärkungsgesetz PSG I Leistungsverbesserung Pflegegeld Pflegesachleistung",
        "Zweites Pflegestärkungsgesetz PSG II neuer Pflegebedürftigkeitsbegriff fünf Pflegegrade",
        "Drittes Pflegestärkungsgesetz PSG III Pflegebedürftigkeitsbegriff Sozialhilferecht SGB XII",
        "Pflegevorsorgefonds Stabilisierung Beitragssatz geburtenstarke Jahrgänge",
        "Pflegeberufegesetz generalistische Pflegeausbildung Reform Pflegeberufe",
    ],
 
    # ── 35. REHABILITATION / TEILHABE (2013–2017) ────────────────
    "rehabilitation_teilhabe_2017": [
        "Bundesteilhabegesetz Weiterentwicklung Eingliederungshilfe modernes Teilhaberecht",
        "Eingliederungshilfe Leistungen Teilhabe Menschen mit Behinderungen SGB IX Reform",
        "Verbesserung Einkommens- und Vermögensanrechnung Eingliederungshilfe Freibeträge",
    ],
 
    # ── 36. FAMILIE / GLEICHSTELLUNG (2013–2017) ─────────────────
    "familie_gleichstellung_2017": [
        "ElterngeldPlus Partnerschaftsbonus Teilzeitarbeit Elternzeit Flexibilisierung",
        "Betreuungsgeld Aufhebung verfassungswidrig Bundesmittel Kinderbetreuung Länder",
        "Entgelttransparenzgesetz Lohntransparenz gleicher Lohn gleiche gleichwertige Arbeit",
        "Mietpreisbremse Begrenzung Miethöhe angespannte Wohnungsmärkte Mietrechtsnovellierung",
        "Wohngeldreform 2016 Anpassung Wohngeld Mieten- und Einkommensentwicklung",
    ],
}
 
# Flat list for embedding
ALL_SEEDS = [
    seed for domain_seeds in SEED_DESCRIPTIONS.values() for seed in domain_seeds
]

if __name__ == "__main__":
    print(f"Total seed descriptions: {len(ALL_SEEDS)}")
    print(f"Domains: {len(SEED_DESCRIPTIONS)}")
    print()
    for domain, seeds in SEED_DESCRIPTIONS.items():
        print(f"  {domain}: {len(seeds)} seeds")
