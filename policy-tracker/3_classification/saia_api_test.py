# imports
from openai import OpenAI
from dotenv import load_dotenv
import os # to load -env
import json
from pathlib import Path
import sys

#load_env
load_dotenv()

#Configurations

saia_api_key= os.getenv("SAIA_API_KEY")
base_url= os.getenv("SAIA_API_ENDPOINT")
m1_llama= "llama-3.3-70b-instruct"
m2_mistral= "mistral-large-3-675b-instruct-2512"
m3_qwen= "qwen3.5-397b-a17b"
m4_gemma= "gemma-4-31b-it"
m5_gpt= "openai-gpt-oss-120b" #reasoning model
m6_devstral= "devstral-2-123b-instruct-2512" #for software engineering/coding

#set openAI client (for wrapper)
client= OpenAI(api_key=saia_api_key, base_url=base_url)


test_policy= {
    "id": "bgbl1-2020-26-5",
    #"year": 2020,
    #"issue_number": 26,
    #"order_in_issue": 5,
    "title": "Achte Verordnung zur Änderung der Arbeitslosengeld II/Sozialgeld-Verordnung",
    #"doc_type": "Verordnung",
    #"date_published": "2020-06-05T00:00:00Z",
    #"date_law": "2020-05-28T00:00:00Z",
    #"bgbl_page": 1206,
    #"pdf_page": 48,
    #"num_pages": 1,
    #"url_web": "https://offenegesetze.de/veroeffentlichung/bgbl1/2020/26#page=48",
    #"url_api": "https://api.offenegesetze.de/v1/veroeffentlichung/bgbl1-2020-26-5/",
    #"url_pdf": "https://media.offenegesetze.de/bgbl1/2020/bgbl1_2020_26.pdf#page=48",
    "full_text": """1206 Bundesgesetzblatt Jahrgang 2020 Teil I Nr. 26, ausgegeben zu Bonn am 5. Juni 2020\nAchte Verordnung\nzur Änderung der Arbeitslosengeld II/Sozialgeld-Verordnung\nVom 28. Mai 2020\nAuf Grund des § 13 Absatz 1 Nummer 1 des Zweiten Buches Sozialgesetzbuch\n– Grundsicherung für Arbeitsuchende – in der Fassung der Bekanntmachung vom\n13. Mai 2011 (BGBl. I S. 850, 2094) verordnet das Bundesministerium für Arbeit\nund Soziales im Einvernehmen mit dem Bundesministerium der Finanzen:\nArtikel 1\nÄnderung der\nArbeitslosengeld II/Sozialgeld-Verordnung\nDie Arbeitslosengeld II/Sozialgeld-Verordnung vom 17. Dezember 2007\n(BGBl. I S. 2942), die zuletzt durch Artikel 8 des Gesetzes vom 29. April 2019\n(BGBl. I S. 530) geändert worden ist, wird wie folgt geändert:\n1. § 1 wird wie folgt geändert:\na) Absatz 1 wird wie folgt geändert:\naa) Nummer 2 wird aufgehoben.\nbb) In Nummer 5 werden die Wörter „und der Leistungszuschlag" gestri-\nchen.\ncc) Nummer 7 wird aufgehoben.\ndd) Nummer 10 wird wie folgt gefasst:\n„10. Beihilfen und Unterstützungen bis zu einem Betrag von insgesamt\n1 500 Euro, die Arbeitgeber ihren Arbeitnehmern aufgrund der\nCOVID-19-Pandemie in der Zeit vom 1. März bis 31. Dezember\n2020 zusätzlich zum ohnehin geschuldeten Arbeitslohn nach § 3\nNummer 11 des Einkommensteuergesetzes steuerfrei gewähren;\nden Beihilfen und Unterstützungen seitens der Arbeitgeber stehen\nentsprechende Zahlungen aus den Haushalten des Bundes und\nder Länder gleich,".\nb) Absatz 4 wird wie folgt geändert:\naa) In Satz 1 werden nach dem Wort „Schulferien" die Wörter „für\nhöchstens vier Wochen je Kalenderjahr" gestrichen sowie die Angabe\n„1 200" durch die Angabe „2 400" ersetzt.\nbb) Satz 2 wird aufgehoben.\n2. In § 3 Absatz 1 Satz 2 wird der Klammerzusatz „(§ 41 Abs. 1 Satz 4 des\nZweiten Buches Sozialgesetzbuch)" durch die Wörter „nach § 41 Absatz 3\ndes Zweiten Buches Sozialgesetzbuch" ersetzt.\nArtikel 2\nInkrafttreten\nDiese Verordnung tritt mit Wirkung vom 1. März 2020 in Kraft.\nBerlin, den 28. Mai 2020\nDer Bundesminister\nfür Arbeit und Soziales\nHubertus Heil""",
  }




# loop

model_list= [m1_llama, m2_mistral, m3_qwen, m4_gemma, m5_gpt, m6_devstral]

for model in model_list:
    print(f"model: {model}")
    try:
        response=client.chat.completions.create(
            model=model,
            temperature=0,
            seed=0,
            top_p=1,
            messages=[{"role": "system",
                       "content": "You are a social policy researcher."},
                       {"role": "user",
                        "content": f"Provide two sentences to pointedly summarize this German legal policy text in English.\n\nTitle: {test_policy['title']}\n\nText: {test_policy['full_text']}"
                        }]
        )
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"ERROR: {e}")
    print("\n\n")
