# How modern spell-checkers work — implications for Skrivi

Research date: 21 September 2026. Research and proposed experiments, not a new benchmark or an audit of Skrivi's current implementation. Sources include implementation code, project documentation and research papers. Private user writing was not submitted to external services.

The strongest direction is a hybrid: Norwegian lexical knowledge, a realistic spelling-error model, conservative contextual ranking, and useful explanations. There is worthwhile traditional engineering left to investigate before concluding that a larger neural model is necessary. This is a recommendation from the research, not a measured improvement in Skrivi.

## The problems must be measured separately

| Problem | Typical mechanism | Failure to distinguish |
|---|---|---|
| Is this an accepted written form? | Dictionary, inflection and compound analysis | Unknown is not necessarily incorrect |
| What could the writer have intended? | Edit search, sound/spelling confusions, learned error channel | Correct answer never enters the pool |
| Which candidate fits here? | Frequency, grammatical analysis, sentence model | Correct answer exists but ranks too low |
| Should an existing valid word be challenged? | Context plus a conservative keep/change decision | Plausible alternatives become false alarms |
| Are word boundaries wrong? | Split/join candidate search | Checking each word independently misses the error |
| Can the writer recognise the answer? | Definitions and distinguishing examples | A correct top-three list still fails the person |

These are proposed diagnostic categories for Skrivi. A single overall accuracy number hides which component needs work.

## 1. The traditional foundation is more than a word list

Hunspell combines dictionary entries with affix and compound rules. Its configuration can also encode common replacements (`REP`), related characters (`MAP`), keyboard neighbours (`KEY`) and phonetic transformations (`PHONE`). Supporting a feature in the engine does not mean a particular language package actually supplies it. [Hunspell manual](https://manpages.debian.org/trixie/libhunspell-dev/hunspell.5.en.html)

For implementation study, Spylls provides readable descriptions of Hunspell's suggestion stages. Its character n-gram fallback first finds similar stems, expands forms and refines the result. Those n-grams measure spelling resemblance; they are not a sentence-context language model. [Spylls suggestion documentation](https://spylls.readthedocs.io/en/latest/hunspell/algo_suggest.html), [n-gram implementation guide](https://spylls.readthedocs.io/en/latest/hunspell/algo_ngram_suggest.html)

**Nuspell's actual code is particularly relevant.** Its staged search includes replacements and character mappings, swaps, keyboard substitutions, deletion/insertion, moved characters, repeated sequences and two-word suggestions. In the inspected source, the n-gram fallback runs only when earlier suggestions were not classified as high quality. This means asking the application to retain more suggestions does not necessarily recover candidates that the engine never generated. Instrument the candidate sources before deciding that the neural ranker is the bottleneck. [Nuspell suggester source](https://github.com/nuspell/nuspell/blob/master/src/nuspell/suggester.cxx)

Nuspell and NeuSpell are different projects: Nuspell is a C++ dictionary engine; NeuSpell is a neural spelling toolkit. [Nuspell](https://nuspell.github.io/), [NeuSpell](https://github.com/neuspell/neuspell)

## 2. Fast edit search and realistic error search are different things

SymSpell precomputes deleted-character forms of dictionary words. At lookup, deletion variants of the input lead to candidate matches, followed by distance checks and ranking. It also provides compound correction and segmentation. It is useful for fast bounded-distance retrieval, but it does not inherently understand a sentence or Norwegian pronunciation. Its speed is not evidence that it will recover more severe dyslexic spellings. [SymSpell implementation](https://github.com/wolfgarbe/SymSpell)

A different approach asks: how likely is this typed string if the writer intended that word? Rather than treating all single-character edits equally, a learned error model can assign costs to whole string substitutions. Brill and Moore described this string-to-string noisy-channel approach; Toutanova and Moore investigated adding pronunciation information. These are established alternatives to simply increasing edit distance. [Brill and Moore, 2000](https://aclanthology.org/P00-1037/), [Toutanova and Moore, 2002](https://aclanthology.org/P02-1019/)

For Skrivi, I would test a bounded candidate generator using observed multi-character confusions alongside the existing engine. Examples should come from authorised error/correction pairs, with synthetic cases clearly labelled. Dialect-dependent sound similarities should receive evidence-based weights rather than being treated as universal Norwegian rules.

## 3. Weighted finite-state spell-checking is a serious open-source option

GiellaLT documents a spelling-error model with weighted single-character and multi-character edits, including initial/final substitutions and whole-word replacements. Lower costs express more likely mistakes. Its development workflow combines an error model with a language acceptor derived from morphological resources. Here “language model” can mean a finite-state word/morphology model, not a neural sentence model. [GiellaLT error-model documentation](https://giellalt.github.io/proof/TheSpellerErrorModel.html), [speller construction](https://giellalt.github.io/infra/infraremake/BuildingSpellingCheckers.html)

Divvunspell is a modern Rust implementation for these finite-state spellers. It offers memory mapping, parallel suggestion computation, case handling and tokenisation, with Windows support. The library is dual Apache-2.0/MIT; the command-line program is GPL-3.0, and language data have separate licences. GiellaLT's documentation identifies it as the production suggestion engine since 2024. [Divvunspell repository](https://github.com/divvun/divvunspell), [GiellaLT tooling](https://giellalt.github.io/proof/spelling/divvunspell-suggestions.html)

There are Bokmål and Nynorsk linguistic repositories. However, their existence does not establish the accuracy or deployment readiness of a dyslexia-focused Norwegian product. The Bokmål repository is marked beta. A build-and-benchmark experiment is justified; wholesale replacement of Nuspell is not yet justified. [Bokmål resources](https://github.com/giellalt/lang-nob), [Nynorsk resources](https://github.com/giellalt/lang-nno)

## 4. Context does not require a generative LLM

A Norwegian grammar-checking paper describes morphological analysis, disambiguation and Constraint Grammar rules. It is historical evidence that Norwegian contextual analysis can be rule-based, not evidence about current commercial internals. For Skrivi, grammatical information could help score candidates without enabling grammar rewriting. [Norwegian grammar-checker research, 2001](https://aclanthology.org/W01-1705/)

The Danish DanProof system is a particularly relevant Scandinavian example: it combines a large lexicon, manually collected error substitutions, written and phonetic similarity, frequency and Constraint Grammar context. It also discusses why dyslexic users need prioritised suggestions and explanations. This is transferable architectural evidence, not a Norwegian benchmark. Its reported results and comparison with older Word versions should not be treated as current product comparisons. [Bick, 2015](https://aclanthology.org/R15-1008/)

My proposed scoring design for Skrivi is a tunable combination:

```text
candidate score = contextual fit
                + likelihood of this spelling mistake
                + appropriate frequency/morphology features
                - penalty for changing the original
```

This is a feature-scoring proposal, not a calibrated probability formula. Always score KEEP alongside replacements. A valid original word should require stronger evidence to challenge than an unrecognised form. Uncertainty should remain visible, and low confidence should permit abstention.

## 5. There is a specific BERT-scoring issue worth checking

Masked-language models can score candidate sentences by masking tokens and summing their log probabilities: pseudo-log-likelihood. This is an established rescoring technique. [Salazar et al., 2020](https://aclanthology.org/2020.acl-main.240/)

However, a written word may become several model tokens. Ordinary one-token-at-a-time scoring lets the remaining pieces reveal the masked piece, inflating some scores. Kauf and Ivanova propose masking the target piece and subsequent pieces of that word, called PLL-word-l2r. They compare it with ordinary and whole-word masking. This deserves an ablation in Skrivi; it is not proof of a Norwegian spelling improvement. [A Better Way to Do Masked Language Model Scoring](https://arxiv.org/abs/2305.10588)

NorBERT3 Small is a Norwegian masked-language encoder, rather than a chat model trained to obey correction instructions. Using it to rank explicit candidates is therefore a different task from prompting Qwen to produce a correction list. [NorBERT3 Small model card](https://huggingface.co/ltg/norbert3-small)

Before increasing model size, compare scoring methods with identical candidates and timing conditions. Batch model work where possible, and measure the effects of word length and number of subword pieces. Do not assume raw scores are calibrated confidence values.

## 6. What newer neural correction systems add

| Approach | Coding logic | Relevance and limitation |
|---|---|---|
| Contextual spelling models | Train on corrupted/correct sentence pairs | NeuSpell demonstrates this for English; not a ready Norwegian solution |
| Edit tagging | Predict KEEP and bounded edit labels rather than freely rewrite | GECToR is an example; spelling-only scope would need explicit training and restrictions |
| Specialised sequence generation | Produce corrected text with a task-trained model | Google's on-device grammar system demonstrates specialised deployment; its objective is broader than Skrivi's |
| Fine-tuned LLM correction | Learn task behaviour and error patterns from examples | Potentially useful, but generic model size alone does not establish fit |

[NeuSpell paper](https://arxiv.org/abs/2010.11085), [GECToR](https://aclanthology.org/2020.bea-1.16/), [Google on-device grammar correction](https://www.research.google/blog/grammar-correction-as-you-type-on-pixel-6/), [LMSpell preprint](https://arxiv.org/abs/2512.05414)

Error generation also matters. SAGE studies synthetic errors informed by natural error patterns, with English and Russian experiments. This supports testing realistic corruption against random character noise, but supplies no Norwegian accuracy guarantee. [SAGE, 2024](https://aclanthology.org/2024.findings-eacl.10/)

For training later, I would prioritise a small candidate-ranking/keep-change task over unconstrained rewriting. Training examples should contain the original context, candidate set, acceptable intended forms and a KEEP label. Include correct sentences and hard negative candidates, not only errors.

## 7. Norwegian resources and product reality

| Resource | What it provides | Important boundary |
|---|---|---|
| Ordbanken | Lemmas, inflection and full forms; compound information | Lexical/morphological evidence, not an authentic dyslexia error distribution |
| LibreOffice Norwegian package | Ready dictionary/affix files and thesauri | Engine capability and supplied rules differ |
| GiellaLT Norwegian resources | Finite-state linguistic models | Readiness and quality require direct testing |
| NorBERT | Norwegian contextual representations | Requires an explicit correction/scoring design |
| LanguageTool | Open-source Norwegian dictionary checking is documented | Not a confirmed ready-made Norwegian contextual checker |
| Lingdys | Commercial assistive checking, including context-informed suggestions | Public manuals do not reveal enough to reconstruct its algorithm |

[Ordbanken catalogue](https://www.nb.no/sprakbanken/ressurskatalog/oai-nb-no-sbr-5/)

The inspected LibreOffice package README reports 708,615 Bokmål and 540,664 Nynorsk entries. It identifies Ordbanken-derived material under CC BY 4.0, revision word lists under CLARIN PUB +BY, and legacy affix/thesaurus material under GPLv2. Track licences by component and version rather than assigning one licence to the whole pipeline. [Package README](https://github.com/LibreOffice/dictionaries/tree/master/no)

An actionable finding: the inspected `nb_NO.aff` contains affix and compound directives but no `REP`, `MAP` or `PHONE` sections. That is a property of this upstream file, not an audit finding about Skrivi's installed dictionary or custom logic. It makes a dictionary/rule inventory worthwhile. [Actual Bokmål affix file](https://raw.githubusercontent.com/LibreOffice/dictionaries/master/no/nb_NO.aff)

LanguageTool maintainer Daniel Naber stated in November 2025 that the open-source version supports Norwegian spelling but not grammar checking, using an external Norwegian dictionary. [Maintainer response](https://forum.languagetool.org/t/norwegian-language/11752)

Lingdys's manual explicitly describes contextual suggestions and use of previous word choices. We should not assume it is merely an old dictionary checker. I found no sufficient public implementation evidence to identify its model architecture. [Lingdys Windows manual](https://download.lingit.no/Manualer/Lingdys_Pluss-Windows-Brukerveiledning.pdf)

## 8. Proposed implementation flow

This is my synthesis for a conservative local sandbox, not copied product architecture:

```text
Preserve original text, token offsets and punctuation.
Analyse forms with the Norwegian lexicon/morphology engine.
For unknown forms and narrowly selected real-word suspects:
    Generate a bounded pool from complementary error mechanisms.
    Retain each candidate's source and error cost.
    Add the original as KEEP; deduplicate and validate forms.
    Rank with error likelihood, frequency/morphology and context.
    Compare the best alternative with KEEP under calibrated thresholds.
    Show up to three choices, with an optional more-choices control.
    Retrieve an explanation/example for each surfaced candidate.
Apply only the user's selected edit at the original span.
```

Split/join corrections need an explicit span-edit representation; they cannot be smuggled through an API that promises single-word, whitespace-free replacements. Keep that experiment separate until the UI supports it.

When several nearby words are misspelled, a context model reads damaged context. A later experiment could score a bounded set of combinations of local candidates. This introduces search cost and feedback risks, so preserve the original context and require a measurable gain over independent ranking. Do not turn it into sentence rewriting.

## 9. Experiments in recommended order

| Order | Experiment | Evidence sought | Effort/risk |
|---|---|---|---|
| 1 | Inventory exact dictionary, rules, generator limits and candidate provenance | Find whether intended words are missing or merely ranked low | Low effort; minimal behavioural risk |
| 2 | Add weighted multi-character error candidates beside existing candidates | Improved candidate recall on severe misspellings | Medium; more irrelevant candidates and latency |
| 3 | Compare existing NorBERT scoring with corrected subword-aware scoring and calibrated KEEP | Better top-three accuracy at the same false-alarm rate | Medium; extra model passes |
| 4 | Build a GiellaLT/Divvun Norwegian comparison | Whether richer morphology/error search beats the current generator | Medium–high; integration and resource quality uncertain |
| 5 | Tune or train a small ranker using authorised error pairs | Generalisable ranking improvement beyond hand-set scores | Higher; requires enough representative data |

Use frozen candidate pools for ranker comparisons and frozen rankers for generator comparisons. Hold out writers/documents, not just random sentences, when data permit. Keep synthetic, authentic learner and diagnosed-dyslexia results separate. A gain on one is not automatically a gain on the others.

Record detection precision/recall, candidate recall at a fixed pool budget, top-three and top-five accuracy conditional on the answer being available, and end-to-end availability of the right answer in the displayed list. Report false alarms on correct text, acceptable variant preservation, split/join results, latency distributions and memory separately. Do not count only already-detected errors. Use paired comparisons and repeat timing only when variance warrants it.

Explanations need their own evaluation: coverage, correctness of sense, and whether the user can make a decision. Synonyms are useful optional evidence; the user's feedback already shows they cannot replace definitions/examples universally. That usability observation should remain a separate success criterion from model ranking.

No source reviewed establishes that a ready-made open Norwegian dyslexia checker will solve the complete problem. The practical opportunity is to combine existing components more carefully and measure the failure stages independently.
