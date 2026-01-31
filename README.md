# PhD Research: Welfare States and Crises

A PhD research project at the University of Mannheim examining how welfare states respond to major economic crises, focusing on the COVID-19 pandemic and the 2008 Great Recession.

---

## About This Project

This research investigates social policy responses to economic shocks across different countries and regions. Key questions include:

- How do welfare states adapt during crises? Are they resilient?
- What policy instruments are deployed in response to crises?
- What can we learn from comparing COVID-19 and Great Recession responses?

---

## Repository Structure

| Folder | Description |
|--------|-------------|
| `litrev/` | Systematic literature review — data processing pipeline and analysis |


---

## Literature Review

The `litrev/` folder contains a reproducible pipeline for systematic literature review:

1. **data collection** from academic databases (Scopus, Web of Science)
2. **keyword extraction** using NLP methods to identify relevant search terms
3. **dataset assembly** combining automated and manual searches
4. **analysis** structures the literature, deploys llms for abstract summaries

### Quick Start

```bash
# Install dependencies
pip install pandas keybert yake openpyxl

# Run the Jupyter notebooks in litrev/notebooks/ sequentially
```

---

## Contact

For questions about this research or collaboration opportunities, please open an issue.

---

## Acknowledgments

- University of Mannheim
- [KeyBERT](https://github.com/MaartenGr/KeyBERT) and [YAKE](https://github.com/LIAAD/yake) for keyword extraction
