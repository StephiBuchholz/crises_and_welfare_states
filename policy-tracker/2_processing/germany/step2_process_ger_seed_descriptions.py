# 2 processing german seed descriptions

"""
seed descriptions for cosine-similarity filtering social-policy relevant texts among retrieved BGBl I texts.

derived from: BMAS, "Soziale Sicherung im Überblick" (2023 edition), see data/external/bmas_soziale-sicherung-im-ueberblick.pdf
method: derived with claude opus 4.6 (web interface) + plausibilty check
purpose: in process_germany.ipynb i embed these seed descriptions alongside the legislative corpus using a German-capable
         sentence transformer, then filter by cosine similarity to retain
         only social-policy-relevant Gesetze and Verordnungen.

design choices:
  - each seed is a short German phrase (5–25 words) that uses the actual
    vocabulary of German legislative texts, not plain-language paraphrases.
    This maximizes embedding overlap with the BGBl corpus.
  - seeds cover all major policy domains from the BMAS document, including
    sub-domains where distinct legislative vocabulary exists.
  - seeds are grouped by policy domain for documentation, but the grouping
    itself is not used in the filtering pipeline — all seeds are embedded
    as a flat list.
  - seed 14: the bmas pdf focuses on general social/labour policy.
    i created another seed from a list of covid-policies in 1_process_ger_seed_desc_covid.py
    to capture more specific covid-motivated policies.
  - for exclusions: manually "out-comment" lines if term is out of scope -> do not delete

"""

SEED_DESCRIPTIONS = {
    # ── 1. ARBEITSFÖRDERUNG (SGB III) ──────────────────────────────
    "arbeitsforderung": [
        "Arbeitslosengeld Anspruch Anwartschaftszeit Rahmenfrist",
        "Arbeitslosengeld I Arbeitslosengeld II",
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
        "Lohn Löhne Entgelt Gehalt Erwerbseinkommen",  # manually added
        "Bundesurlaubsgesetz Mindesturlaub Arbeitnehmer",
        "Mutterschutzgesetz Beschäftigungsverbot schwangere Arbeitnehmerinnen",
        "Pflegezeitgesetz Familienpflegezeitgesetz Freistellung häusliche Pflege Angehöriger",
        "Arbeitnehmerüberlassungsgesetz Leiharbeit Zeitarbeit Überlassung",
        # "Arbeitnehmer-Entsendegesetz Arbeitsbedingungen entsandte Arbeitnehmer",
        "Allgemeines Gleichbehandlungsgesetz Benachteiligungsverbot Diskriminierung Beschäftigung",
        "Nachweisgesetz wesentliche Arbeitsbedingungen Arbeitsvertrag",
    ],
    # ── 3. ARBEITSSCHUTZ ──────────────────────────────────────────
    "arbeitsschutz": [
        # "Arbeitsschutzgesetz Gefährdungsbeurteilung Sicherheit Gesundheit Beschäftigte",
        "Arbeitszeitgesetz Höchstarbeitszeit Ruhezeit Nachtarbeit Sonntagsarbeit",
        "Jugendarbeitsschutzgesetz Kinderarbeitsschutzverordnung",
        # "Arbeitsstättenverordnung Einrichtung Betrieb Arbeitsstätten",
        # "Gefahrstoffverordnung Schutz Beschäftigte Tätigkeiten Gefahrstoffe",
        # "Biostoffverordnung Schutz biologische Arbeitsstoffe Infektionsschutz",
        # "Betriebssicherheitsverordnung Arbeitsmittel überwachungsbedürftige Anlagen",
        # "Arbeitsmedizinische Vorsorge Verordnung Beschäftigungsfähigkeit",
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
    # ── 8. REHABILITATION UND TEILHABE BEHINDERTER MENSCHEN ──────
    # "rehabilitation_teilhabe": [
    # "Rehabilitation und Teilhabe Menschen mit Behinderungen SGB IX Bundesteilhabegesetz",
    # "Schwerbehindertenrecht Beschäftigungspflicht Ausgleichsabgabe Integrationsamt",
    # "Eingliederungshilfe Teilhabe am Leben in der Gemeinschaft",
    # "Werkstätten für behinderte Menschen Berufsbildungsbereich",
    # "Barrierefreiheit Behindertengleichstellungsgesetz Inklusion",
    # "Persönliches Budget selbstbestimmte Teilhabe Leistungserbringung",
    # "Ergänzende unabhängige Teilhabeberatung EUTB",
    # ],
    # ── 9. RENTENVERSICHERUNG ─────────────────────────────────────
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
        "Flexi-Rente Hinzuverdienst Beschäftigung neben Altersrente",
    ],
    # ── 10. SOZIALHILFE (SGB XII) ─────────────────────────────────
    "sozialhilfe": [
        "Sozialhilfe Hilfe zum Lebensunterhalt nicht erwerbsfähige Hilfebedürftige SGB XII",
        "Grundsicherung im Alter und bei Erwerbsminderung vierte Kapitel SGB XII",
        "Hilfe zur Pflege Sozialhilfe stationäre häusliche Pflege",
        "Hilfe zur Überwindung besonderer sozialer Schwierigkeiten Wohnungslose",
        "Regelbedarf Sozialhilfe Regelbedarfsstufen Existenzminimum",
    ],
    # ── 11. SOZIALE ENTSCHÄDIGUNG ─────────────────────────────────
    # "soziale_entschaedigung": [
    # "Bundesversorgungsgesetz Soziale Entschädigung Kriegsopferversorgung",
    # "Opferentschädigungsgesetz Opfer von Gewalttaten Entschädigung",
    # "Soldatenversorgungsgesetz Beschädigtenversorgung Wehrdienst",
    # "Soziales Entschädigungsrecht SGB XIV Entschädigungsleistungen",
    # ],
    # ── 12. UNFALLVERSICHERUNG (SGB VII) ──────────────────────────
    "unfallversicherung": [
        "Gesetzliche Unfallversicherung Arbeitsunfall Berufskrankheit Berufsgenossenschaft",
        "Unfallverhütungsvorschriften Prävention Arbeitsunfälle Berufsgenossenschaft",
        "Verletztengeld Übergangsgeld Unfallrente Leistungen Unfallversicherung",
        "Wegeunfall Versicherungsschutz Arbeitsweg",
    ],
    # ── 13. SOZIALVERSICHERUNG ALLGEMEIN / ÜBERGREIFEND ───────────
    "sozialversicherung_allgemein": [
        "Sozialversicherung Beitragssatz Beitragsbemessungsgrenze Sozialversicherungsbeiträge",
        "Krankenversicherung Pflegeversicherung Beitragssatz gesetzliche Krankenversicherung",
        "Sozialgerichtsbarkeit Sozialgericht Widerspruch Rechtsschutz",
        "Sozialdatenschutz Sozialgeheimnis Datenschutz Sozialleistungsträger",
    ],
    # ── 14. KRISENSPEZIFISCHE / QUERSCHNITTSTHEMEN ────────────────
    #    (not directly from single BMAS chapters, but vocabulary that
    #     appears in crisis-era legislation cutting across domains)
    "krisenbezogen": [
        "Sozialschutzpaket COVID-19 Pandemie Erleichterungen Sozialleistungen",
        "Vereinfachter Zugang Grundsicherung Kurzarbeit Pandemie Corona",
        "Erleichterter Zugang Kurzarbeitergeld Anforderungen Arbeitsausfall",
        "Konjunkturpaket Stabilisierungsmaßnahmen Wirtschaftskrise soziale Sicherung",
        "Arbeitszeitverordnung Ausnahmen Höchstarbeitszeit Krisensituation",
        "Infektionsschutzgesetz Maßnahmen Pandemiebekämpfung Entschädigung Verdienstausfall",
        "Kinderkrankengeld Erweiterung Anspruch Betreuung pandemiebedingt",
        "Sonderzahlungen steuerfreie Corona-Prämie Beschäftigte",
        "Einmalige Sonderzahlung aus Anlass der COVID-19-Pandemie",  # manually from 1_process_ger_seed_desc_covid.py
        "Beschäftigungssicherung infolge der COVID-19-Pandemie",  # manually from 1_process_ger_seed_desc_covid.py
        "Konjunktur- und Krisenbewältigungspaket",  # manually from 1_process_ger_seed_desc_covid.py
        "Minderung von Arbeitslosigkeitsrisiken infloge des COVID-19-Ausbruchs",  # manually from 1_process_ger_seed_desc_covid.py
        "steuerlicher Hilfsmaßnahmen zur Bewältigung der Corona-Krise",  # manually from 1_process_ger_seed_desc_covid.py
        "Unterstützung von Wissenschaft und Studierenden aufgrund der COVID-19-Pandemie",  # manually from 1_process_ger_seed_desc_covid.py
        "Maßnahmen im Elterngeld aus Anlass der Covid-19-Pandemie",  # manually from 1_process_ger_seed_desc_covid.py
        "erleichterten Zugang zu sozialer Sicherung",  # manually from 1_process_ger_seed_desc_covid.py
        "sozialen Maßnahmen zur Bekämpfung der Corona-Pandemie Sozialschutz-Paket II Sozialschutz-Paket I",  # manually from 1_process_ger_seed_desc_covid.py
        "SARS-CoV-2-Arbeitsschutzverordnung",  # manually from 1_process_ger_seed_desc_covid.py
        "Verordnung über die Bezugsdauer für das Kurzarbeitergeld Kurzarbeitergeldverordnung Kurzarbeitergeldbezugsdauerverordnung",  # manually from 1_process_ger_seed_desc_covid.py
        "Abweichungen vom Arbeitszeitgesetz infolge der COVID-19-Epidemie",  # manually from 1_process_ger_seed_desc_covid.py
        "Überbrückungshilfe Soforthilfe Selbstständige Kleinunternehmer Krise",  # manually from 1_process_ger_seed_desc_covid.py
        "Corona-Sonderzahlungsrichtlinie pandemiebedingten Mehrbedarfs Härterichtlinien Einmalleistungen",  # manually from 1_process_ger_seed_desc_covid.py
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
