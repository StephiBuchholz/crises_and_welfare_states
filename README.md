# phd research: automated policy-tracking, welfare states and crises

A phd research project at the university of mannheim on the automated, llm-based compilation of policy-trackers holding complex policy classifications.

---

## about this project

this research project has two aims: 

1) it develops a pipeline for the llm-based compilation of policy-trackers including time-stamps, summaries and, most importantly, complex classification tasks based on raw social policy texts.

3) it investigates social policy responses tocrises across different countries and regions. Key questions include:
    - How do welfare states adapt during crises? Are they resilient?
    - What policy instruments are deployed in response to crises?
    - What can we learn from comparing COVID-19 and Great Recession responses?

---

## repository structure

| Folder | Description |
|--------|-------------|
| `litrev/` | Systematic literature review — data processing pipeline and analysis |
| `policy-tracker/` | pipeline fetching raw policy texts and processing into policy-tracker using llms |


---

## literature review

the `litrev/` folder contains a reproducible pipeline for systematic literature review:

1. **data collection** from academic databases (scopus, web of science)
2. **keyword extraction** using nlp methods to identify relevant search terms
3. **dataset assembly** combining automated and manual searches
4. **analysis** structures the literature, deploys llms for abstract summaries

### quick start

```bash
# install dependencies
pip install pandas keybert yake openpyxl

# run the jupyter notebooks in litrev/notebooks/ sequentially
```

## policy-tracker


---

## contact

For questions about this research or collaboration opportunities, please open an issue.

---

## acknowledgments

- University of Mannheim
- [KeyBERT](https://github.com/MaartenGr/KeyBERT) and [YAKE](https://github.com/LIAAD/yake) for keyword extraction
