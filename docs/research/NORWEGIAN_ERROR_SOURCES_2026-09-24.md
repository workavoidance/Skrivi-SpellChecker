# Norwegian spelling-error sources: follow-up research

Date: 2026-09-24. Online source inspection only; no new accuracy measurements, corpus imports, model downloads or application changes.

## Recommended source: ASK-GEC

- University of Oslo Language Technology Group release: https://huggingface.co/datasets/ltg/ask-gec
- Dataset card reports 45,673 source/correction rows, three splits and 9.67 MB. It identifies the material as ASK-RAW from Matias Jentoft's 2023 thesis and declares CC BY 4.0.
- Original corpus description: https://aclanthology.org/L06-1345/
- Authentic Norwegian second-language examination writing, not a diagnosed-dyslexia corpus. Useful as an additional evaluation stratum, not a replacement for pupil data.
- Inspected the public preview. It contains spelling, word-boundary, grammatical and editorial changes, plus unchanged sentences. Some corrected outputs retain errors or contain malformed spacing. Whole corrected sentences must not become unquestioned spelling answer keys.
- Before ingestion, check the release terms against underlying corpus terms; retain provenance and attribution. No corpus contents are committed here.

## Expert-designed paragraphs and correct-word controls

Sprakradet's March 2026 spelling-program report includes the test texts in its appendix (PDF pages 25-26):
https://sprakradet.no/wp-content/uploads/Stavekontrollrapport-18.06.26.pdf

Its Bokmal error paragraph has 36 deliberately inserted errors. A separate clean paragraph tests valid but less-common forms. The scope includes grammar and punctuation, so select spelling and boundary cases rather than using the entire score as our product target. These are constructed tests, not authentic dyslexic writing. The text extraction was readable; the screenshot service failed, so visual colour annotations were not independently inspected.

The report also explains why the ASK conversion is not a ready-made reference benchmark: one sentence reference, incomplete detailed human review, and sentence-level rather than word-level correction representation. This corroborates the need for a reviewed spelling subset. Public availability of the report does not itself establish permission to redistribute its complete test texts.

## Authentic early pupil writing

Skrivesenteret publishes classroom examples about rosehips, magnets and paper spinners:
https://skrivesenteret.no/ressurs/veiledet-skriving-med-de-yngste/

Useful for observing errors in genuine early writing. The article does not identify these pupils as dyslexic. It describes substantial teacher support, so the writing should not be treated as wholly unaided. Linked PDF retrieval failed during this research; no pupil transcription or inferred answer key has been added.

## Historical source worth tracing

SCARRIE's final report describes a Norwegian database of 630 actual proofreading errors from books and newspapers:
https://ling.w.uib.no/projects/scarrie/scarrie-final-report/

This is adult edited-publication material, not pupil/dyslexia evidence. The database link in the historical report points to localhost; no usable error-database download was verified. The separately published SCARRIE lexicon is not this error database. Keep as a lead, not an available dataset.

## Other checks

The published case study below discusses a pupil diagnosed with dyslexia, but does not expose a useful collection of exact error/correction pairs. Do not count it as acquired test data:
https://utdanningsforskning.no/artikler/2020/nar-tiltakene-ikke-har-effekt--en-kasusbeskrivelse-av-en-elev-med-dysleksi/

NORM remains a previously identified source with access/permission pending; it is not a new discovery in this search. See NORWEGIAN_DYSLEXIA_DATASET_RESEARCH.md.

## Proposed next experiment

1. Build a modest reviewed ASK spelling subset locally, initially about 100 cases, retaining the original sentence, precise error span, acceptable corrections, source record and error category.
2. Exclude grammatical/style rewrites and ambiguous intended words. Keep unchanged controls and legitimate Bokmal variants; allow multiple valid answers.
3. Include substitutions, omissions, insertions, letter ordering, Norwegian characters, multiple edits and word boundaries. Do not infer prevalence from a hand-selected sample.
4. Check overlap with existing tests. Reserve evaluation cases by original essay where identifiers permit; otherwise document the weaker separation. Public corpora may already have appeared in model training, so this is not a contamination-free benchmark.
5. Report detection, candidate-pool inclusion, top-three/top-five inclusion and false alarms separately. Keep learner, pupil, constructed and private family examples in separate reporting groups.

No part of this proposed experiment has been run yet. Keep corpus records and private writing out of GitHub; publish source metadata, procedure and aggregate results only.
