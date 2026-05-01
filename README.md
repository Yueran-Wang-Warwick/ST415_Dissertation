# ST415 Dissertation Appendix Repository

This repository contains the supporting materials for the dissertation
`Transformers-Based Customer Review Analysis on E-commerce platforms` by Yueran
Wang. It corresponds to the appendix material referenced in
`ST415_Dissertation.tex`, especially Appendix `Project Resources`, and contains
the notebooks, source review file, and local web application used in the project.

## Dissertation Mapping

| Repository item | Dissertation section |
| --- | --- |
| `ST415_EDA.ipynb` | Chapter 2, `Data`, including exploratory data analysis, review length analysis, noise evidence, cleaning, and gibberish filtering. |
| `BERT_Family_Performances.ipynb` | Chapter 4, `Ternary Sentiment Classification`, including BERT, RoBERTa, and DeBERTa training and benchmark comparison on the Amazon corpus. |
| `Transfer_Learning_HLC.ipynb` | Chapter 4, `Domain Adaptation to Happy Linen Company`, including frozen-backbone head adaptation and full parameter fine-tuning on HLC product and service reviews. |
| `service_topic0_negative.xlsx` | Chapter 6, `Summarisation Evaluation`, as the source review file for the negative-sentiment summary of the service topic labelled `efficient, customer service, quick service`. |
| `Sentiment_Analysis_Local_Web/` | Chapter 7, `Local Web Deployment`, including the FastAPI web interface, table cleaning module, CSV analysis module, model inference code, topic summarisation code, and local SEDNA_BERT package. |

The same items are listed in Appendix `Project Resources`, under the `GitHub
Repository` subsection.

## Top-Level Files

### `ST415_EDA.ipynb`

This notebook supports the data chapter. It covers the Amazon review subset,
label distribution, review length distribution, evidence of malformed or
gibberish text, cleaning operations, and the construction of the ternary labels
used later for sentiment modelling.

Relevant dissertation locations:

- Chapter 2, `The Amazon Reviews Dataset`
- Chapter 2, `Exploratory Data Analysis`
- Chapter 2, `Data Cleaning`
- Chapter 2, `Gibberish Detection and Ternary Label Construction`

### `BERT_Family_Performances.ipynb`

This notebook supports the Amazon benchmark experiments. It records the training
and evaluation workflow for the BERT-family comparison, including BERT, RoBERTa,
and DeBERTa.

Relevant dissertation locations:

- Chapter 4, `The BERT Family: Encoder-Only Models for Classification`
- Chapter 4, `Fine-Tuning Design`
- Chapter 4, `Results on Amazon Benchmark`
- Chapter 4, `Cross-Model Comparison: BERT vs. RoBERTa vs. DeBERTa`

### `Transfer_Learning_HLC.ipynb`

This notebook supports the HLC domain adaptation experiments. It contains the
training and evaluation workflow for adapting the Amazon-trained DeBERTa model
to the product and service review corpora.

Relevant dissertation locations:

- Chapter 2, `The Happy Linen Company Dataset`
- Chapter 2, `Rationale for the Two-Stage Training Strategy`
- Chapter 4, `Domain Adaptation to Happy Linen Company`
- Chapter 4, `Frozen-Backbone Head Adaptation`
- Chapter 4, `Full Parameter Fine-Tuning`
- Chapter 4, `Four-Condition Comparison`
- Chapter 4, `Misclassification Analysis`

### `service_topic0_negative.xlsx`

This spreadsheet contains the source reviews used for the worked
summarisation-evaluation example. It is the negative-sentiment subset for the
largest HLC service BERTopic cluster.

Relevant dissertation locations:

- Chapter 5, `Service Reviews: BERTopic Clustering`
- Chapter 6, `Summarisation Evaluation`
- Appendix `Project Resources`

## Local Web Application

The `Sentiment_Analysis_Local_Web/` directory contains the locally deployable web
application described in Chapter 7. The application exposes the cleaning,
sentiment classification, topic modelling, and summarisation workflow through a
browser interface.

Main files:

| File or directory | Purpose |
| --- | --- |
| `main.py` | Launches the FastAPI application with Uvicorn and opens the local browser page. |
| `app.py` | Defines the FastAPI application and routes. |
| `config.py` | Stores model paths, thresholds, device settings, generation parameters, and runtime directories. |
| `runtime.py` | Initialises shared runtime state for the web application. |
| `excel_pipeline.py` | Implements the table-cleaning workflow used by the Table Data Cleaning module. |
| `csv_nlp.py` | Runs the CSV analysis pipeline, including sentiment classification and topic modelling. |
| `inference.py` | Loads and applies the DeBERTa sentiment classifier. |
| `topic_summary.py` | Handles topic-level summarisation. |
| `llama_input_prep.py` | Prepares review text for the local Llama summarisation backend. |
| `ui_*.py` files | Build the browser interface components shown in Chapter 7. |
| `SEDNA_BERT_lib/` | Local editable Python package containing the project NLP pipeline code. |
| `README.md` | Installation and launch instructions for the local web application. |

Relevant dissertation locations:

- Chapter 7, `Local Web Deployment`
- Chapter 7, `System Architecture and Setup`
- Chapter 7, `Interface Overview`
- Chapter 7, `Table Data Cleaning`
- Chapter 7, `CSV Analysis`
- Appendix `Project Resources`

## Required Model Artefacts

The web application expects two model artefacts to be placed in the
`Sentiment_Analysis_Local_Web/` directory before launch:

```text
DeBERTa_Sentiment_Analysis.pt
LLaMA_3_instruct_8B_4bits/
```

The DeBERTa checkpoint corresponds to the Hugging Face model listed in Appendix
`Hugging Face Model`. The Llama directory corresponds to the local generation
backend described in Chapter 7, `System Architecture and Setup`.

These large artefacts may not be present in the repository folder by default and
should be downloaded or placed locally before running the web application.



