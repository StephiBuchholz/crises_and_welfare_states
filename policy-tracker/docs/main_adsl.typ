//  Template with Chicago Author-Date Style

#set document(
  title: [2026-05-26_promptdesign_exp_policytracker_paper_stbuchho],
  author: "Stephanie Buchholz",
  date: auto,
)

// Page setup - Word-like margins
#set page(
  paper: "a4",
  margin: 3cm,  // all around
  numbering: "1",
  number-align: center,
)

// Text formatting
#set text(
  font: "New Computer Modern Math",
  size: 12pt,
  lang: "en",
)

// Paragraph formatting
#set par(
  justify: true,
  leading: 0.65em,
  spacing: 1.5em,  // 1.5 line spacing
  first-line-indent: 0.2in,
)

// Heading styles
#set heading(numbering: "1.1")

#show heading.where(level: 1): set block(above: 24pt, below: 14pt)
#show heading.where(level: 2): set block(above: 18pt, below: 14pt)
#show heading.where(level: 3): set block(above: 14pt, below: 14pt)
#show heading.where(level: 4): it => block(
  above: 14pt,
  below:12pt,
  inset: (left: 1em),
  text(weight: "medium", emph(it.body))
)



#set table(
  stroke: (x, y) => if y == 0 {
    (bottom: 0.7pt + black)
  } else {
    none
  },
  inset: (top: 4pt, bottom: 4pt, left: 6pt, right: 6pt),
  align: left
)
#show table.cell.where(y: 0): strong

#set figure(placement: auto)

// ============================================================
// TITLE
// ============================================================

#align(center)[
  #v(2cm)
  #text(size: 18pt, weight: "bold")[
    Prompt Design and Model Selection in llm-based Social Policy Classification
  ]
  
  #text(size: 14pt)[
    A Multi-Prompt, Multi-Model Experiment on German Legislative Texts
  ]

  #v(0.5cm)
  #text(size: 11pt)[Stephanie Buchholz]
  #v(0.01cm)
  #text(size: 11pt, style: "oblique")[stephanie.buchholz\@uni-mannheim.de]
  #v(0.01cm)
  #text(size: 11pt, style: "italic")[University of Mannheim]
  #v(0.01cm)
  #text(size: 11pt)[#datetime.today().display()]
]

#v(1cm)

// ============================================================
// ABSTRACT
// ============================================================

#v(0.5cm)
#block(
  width: 100%,
  above: 1em,
  below: 1.5em,
)[
  #line(length: 100%, stroke: 0.5pt + black)
  #v(6pt)
  #text(size: 11pt, weight: "bold")[Abstract]
  #v(4pt)
  #par(first-line-indent: 0pt)[
    #text(size: 10pt)[
        This project investigates how social policy shapes welfare states' capacity to mitigate the consequences of crises for individuals and households. The project compiles a novel crises policy tracker that classifies policy responses since the financial crisis of 2008, through Covid-19. With this tracker, I introduce a way scaling social policy analysis through a semi-automated pipeline; I measure what states do in crises and assess whether and for whom it matters.
    ]
  ]
  #v(6pt)
#par(first-line-indent: 0pt)[
  #text(size: 10pt)[#emph[Keywords:] policy tracker; prompt design; llm; social policy]
]
  #line(length: 100%, stroke: 0.5pt + black)
]

// ============================================================
// CONTENT
// ============================================================

= Introduction

Social policy scholars have long documented welfare state measures in order to typologize and trace welfare state change 
and capacity. However, the classification work underpinning this research remains manual, costly, and difficult to scale.
This project addresses that bottleneck: I introduce an automated pipeline for compiling a social policy tracker. 
The pipeline retrieves all raw legal texts for a country and a desired time period and filters those that are social policy 
related. It summarizes them, retrieves dates of legal effect, and then classifies them with regard to relevant dimensions in 
social policy analysis, like social policy field, or crisis-relatedness (2008 Great Recession and Covid-19) using large 
language models (llms). Due to the probabilistic and black-box nature of llms, ensuring internal validity, reliability, and 
reproducibility presents the most significant challenge for applying such pipelines in research. This challenge is 
compounded by the fact that the tasks at hand require substantive domain knowledge and lie outside of more frequently 
tested classification tasks such as sentiment, toxicity, rumor stance, or news frames.

This paper therefore addresses the question: How do prompt design and model selection affect the compliance and accuracy
of llm-generated social policy classifications?
In the context of this paper, I apply the pipeline to German social policy between 2008 and 2022, encompassing both routine and crisis-related legislation. 
Crisis-related legislation is a particularly demanding case for tracking, since policy responses unfold rapidly and across 
many countries and social policy fields simultaneously. However, the pipeline is designed to be scaled to additional countries 
or longer time frames later. 

Two key aspects influence validity, reliability and reproduciblity, that is model architecture and prompt configurations.
I therefore employ a 5 × 16 factorial experiment, crossing 5 models with 16 prompt configurations, the latter of which are 
derived from a 2⁴ fully crossed design spanning four prompt dimensions.
For models, I accomodate different architectures and sizes using four open source models mistra-large-3-675b, llama-3.3-70b, 
qwen-3.6-35b-a3b and gpt-oss-120b, as well as one proprietary model as control, i.e. gpt-4.1-mini.
The prompt is the most sensitive part in the pipeline, especially with theoretically 
complex sociological classifications and underlying concepts being put to test. I therefore vary prompt configurations across the following
four dimensions a) class definitions (included/not included), b) few-shot versus zero-shot settings (giving the model some/no examples of the 
classification task), c) batch processing (giving the model one/multiple tasks at once) and, d) justification (the model is required/not required to 
justify its classification). 

- Results:






Classification results are evaluated against a human-labelled goldstandard based on a subset of the policies. 
Cohen's K and F1-scores are computed as inter-coder-reliability metrics between the goldstandard and 
each llm-output.


-  Sharpen contribution

- structure of the paper








= Large Language Models as Annotators: What We Know


== Applications and Best Practices

Social science scholars frequently need labelled data, especially so when large text corpora are at the core of the analysis. To this end,
llms have been found to outperform both trained expert and crowd worker annotators for some tasks @gilardi_2023_chatgpt_vs_crowd @tornberg_chatgpt-4_2023 @tornberg_large_2025. 
Other studies advise caution as they stress the need for validation and suggest pooling outputs from multiple repetitions @reiss_testing_2023 
or point out the dependence on the kind of task given to an llm @zhu_can_2023. Common tasks given to llms are sentiment analysis @zhang_sentiment_2024, rumor detection 
@yan_enhancing_2024, news framing @pastorino_newsframe_2024 or toxicity @li2024hottox, for a combination of all of them also see @atreja2025s. 

Only a few papers apply automated annotation in context of policy analysis. Gunes and Florczak test several llms to label US congressional bills and hearings with 
regard to their policy topics and find, when benchmarking against Babel, which is a custom trained algorithm for this specific use case, that their top-performing 
model-output, pooling two agreeing models, falls short by 13 to 16 percentage points in accuracy. 
In an older approach, Burscher et al. #cite(<burscher_using_2015>, form: "year") attempt a content classification of Dutch parliamentary questions 
with supervised machine learning with bag-of-words features. 
Peña et al. #cite(<pena_etal_llm_topiclass_publicpolicy>, form: "year") apply language models to the classification of legislative documents, demonstrating their utility for topic classification of Spanish 
parliamentary initiatives across 30 policy categories. Sebők et al. #cite(<sebHok2025leveraging>, form: "year") classify legislative texts into policy topics across multiple languages 
using the Comparative Agendas Project codebook, validating their pipeline against a human-coded gold standard in terms of validity, reliability, and cost. Both Peña et al.  #cite(<pena_etal_llm_topiclass_publicpolicy>, form: "year")
and Sebők et al. #cite(<sebHok2025leveraging>, form: "year"), however, rely on fine-tuned encoder-based models trained on large labeled corpora, whereas the approach taken here foregoes task-specific 
training in favor of prompting instruction-tuned generative LLMs. if prompt configurations and model choice can be systematically optimized, offers a scalable 
route to automated policy analysis without the overhead of domain-specific fine-tuning. The application of instruction-tuned generative models to legislative classification 
thus remains underexplored, and the present study addresses this gap by systematically examining how prompt design and model choice shape classification output.

The discourse around the deployment of LLMs as annotator has inspired an increasing focus on the quality of the llm output and its suitability for research. Törnberg 
#cite(<tornberg_best_2024>, form: "year") identifies nine best practices in this, that I want to address briefly: 
(1) choice of an appropriate model - I address this by testing various families, types and sizes of models against each other.
(2) adherence to a systematic coding procedure - I address this by systematically testing different components of information that are integrated into the prompts. 
(3) develop a prompt codebook - I address this by providing a detailed codebook with label schemata and definitions to both the human coders and the llm.
(4) validate your model - the validation process is the core of this experiment by testing llm outputs against a human-labelled gold standard and I present the results of this
in the chapter on evaluation. 
(5) engineer your prompts - this is explicitly done through my testing of prompt configurations, through the provision of a fixed JSON output format and testing 
chain-of-thought triggering and few-shot prompting. 
(6) specify your LLM parameters - I fix temperature, seeds and top-p 
(7) discuss ethical and legal implications - I do not use any personal data, posts made by individuals on online platforms or copyrighted data that require GDPR-conform storage, anonymization or licencing. 
(8) examine model stochasticity - i investigte whether (small and large) changes in the prompts yield different classifications.
(9) consider that your data may be in the training data - the policies I examine are most certainly in the training data. However, the specific tasks and labels I require 
were created by me - the gold standard was labelled specifically for this project and has not existed in the training data either. It can therefore be plausibly assumed that 
the match of policies and labels does not exist in the training data.

Part of first best practice principle, i.e. choosing an appropriate model, is the prioritization of open-source models in order to ensure both 
reproducibility (open-source models are transparent on model weights and configurations) and data privacy @weber_evaluation_2024 @pangakis_automated_2023. I therefore
test five open-source models and use only one proprietary model for comparative purposes. 


== Evaluating LLM Output: Validity, Reliability, and Reproducibility

Validity, reliability, and reproducibility are central to my two-fold aim of establishing automated text annotation in social policy analysis and establishing the 
policy tracker as a data source for further scientific use.  
In experimental research, _validity_ is typically understood as internal validity — the capacity to attribute variation in an outcome to deliberate manipulation of 
an independent variable @mcdermott2011validity. A second and distinct concern is measurement validity, which asks whether (model-)assigned labels 
accurately reflect the underlying construct @mcdermott2011validity — here, the assignment of legislative texts to social policy fields derived from ESSPROS, OECD SOCX, and OECD taxben — 
rather than surface features of the text or prompt. The two are related. Internal validity is a precondition for measurement validity, in that only once the sources 
of labelling variance are identified and controlled can confidence in the labels themselves be established. 

_Reliability_ generally refers to the consistency of measurement; a measure is reliable when it yields the same result every time it is applied. 
In the context of LLM annotation, reliability typically refers to intercoder reliability, that is  
whether there is consistency in labelling between coders, or more precisely, between human and LLM coders. Intercoder reliability is understood as a 
"numerical measure of the agreement between different coders regarding how the same data should be coded" #cite(<oconnor2020intercoder>, supplement: [2]).

_Reproducibility_, by contrast, concerns the ability of other 
researchers to produce the exact same "computational results using the same input data, computational steps, methods, code, and conditions of analysis" 
#cite(<NAP25303_reproduc>, supplement: [HIGHLIGHTS, no page]). In the context of LLM annotation this is non-trivial, as large language models operate 
non-deterministically with hard-to-predict stochasticity. In the experiments reported here, all stochasticity parameters are set to their most deterministic values 
across all models: seeds are fixed, temperature is set to 0, and top-p is set to 1.0, so that backend changes on the model developer's side cannot silently alter sampling. 
The factorial experiment addresses internal validity and reliability simultaneously. By systematically varying four prompt dimensions across five language models, variation in 
labelling outcomes can be plausibly attributed to specific design choices rather than uncontrolled differences in elicitation.







= The policy tracker pipeline

The policy tracker pipeline consists of four basic steps: 1) data collection, 2) filtering, 3) llm-classifications (and goldstandard labelling), 
and 4) evaluation. In the following section, I describe the data collection and filtering steps for the case of German policies, before I move on to 
classifications and tasks given to the llms. Descriptions on 4) evaluation are part of the subsequent chapter on research design.



== Data Collection and Filtering

Legislative texts are retrieved from the German Federal Law Gazette (Bundesgesetzblatt, BGBl Teil I) 
via the OffeneGesetze.de API @offenegesetze_api for two crisis periods: the 2008 financial crisis (2008–2015) and the COVID-19 pandemic (2019–2022). A two-pass collection strategy first retrieves document metadata (titles, publication dates, document types) and subsequently fetches full legislative text for each identified document. Documents are automatically classified into three types: laws (Gesetze), regulations (Verordnungen), and announcements (Bekanntmachungen). The raw corpus covers all federal legislation published in those periods 
and is stored without modification to preserve reproducibility.

Because only a subset of federal legislation concerns social policy, I filter the raw corpus using a 
pooled evaluation framework combining two independent retrieval systems with two distinct failure modes.
System 1 measures cosine similarity between document titles and a set of llm-generated (Claude Opus 4.6 by Anthropic) 
seed descriptions covering areas of social policy. These seed descriptions are drawn from official German 
social policy reports @bmas2023soziale @bmas2009sozialbericht @bmas2017sozialbericht @bmas2021sozialbericht which are fed to the llm.
The seed descriptions are stratified by era to capture time-variant terminology (e.g., Hartz-era vocabulary in 2009 differs from 
Bürgergeld vocabulary in 2021). Titles are embedded using the paraphrase-multilingual-mpnet-base-v2 model @reimers-gurevych-2019-sentence 
and compared against seeds via cosine similarity. Documents scoring above an empirically set upper 
threshold are automatically accepted; those falling in an intermediate range are flagged for manual 
triage; documents below the lower threshold are discarded. The processes is conducted with three different rounds of llm-computed seed descriptions, always based
on the documents named above, until no new documents were retrieved.
System 2 applies unsupervised topic modelling via BERTopic @grootendorst2022bertopic. Title embeddings 
(cached from the first system) are reduced to two dimensions using UMAP and clustered using 
HDBSCAN (minimum cluster size = 10) with a fixed seed. Topic labels are derived via class-TF-IDF after 
lemmatisation with spaCy's German language model. I review each discovered topic and 
mark it as welfare-relevant or not; all documents in welfare-relevant topics are checked manually and, in the current case, were all found to be admissible.
A few topics were edge cases and a only very few of their topics were included. Non-welfare relevant topics are discarded entirely.
The two candidate sets are combined via union to maximise recall, reflecting the complementary 
failure modes of the two systems: the similarity-based approach may miss documents with unusual 
vocabulary, while topic clustering may aggregate documents from disparate domains. The details of the 
thresholds, manual triage and resulting policy document counts from system 1, as well as the topics
and decisions from system 2 are presented in the Appendix.
After deduplication, the resulting policy set for Germany covers 681 documents.

== Classification and Task Designs

This section describes which tasks and classification problems are given to the llms in the experiment. 
Each policy is classified by an llm along several dimensions: a brief summary; 
entry-into-force and termination dates; whether the text explicitly references a crisis, and, as the most central task,
choosing a primary and secondary social policy field. 

=== Task 1: Summary

The summary task prompts the llm to provide a pointed summary of the policy in English and of one to two sentences. The output requirement in json format demands a string format, i.e. a natural language sentence. This task is only part of batch prompts and not included in single prompts.

=== Task 2: Dates of Legal Effect

The offenegesetze.de API automatically delivers the date a policy was adopted by the lawmaker or the administration as well as the date a law was 
published in the Bundesanzeiger. However, in Germany a policy often has separate dates for entering into or terminating legal effect. If so, these
are listed at the end of the policy text and must therefore be retrieved separately. In many cases, the date of legal effect is simply specified 
as "the date of publication [in German: "Verkündung"] in the Bundesgesetzblatt." The prompt requires a date of legal effect and allows a date of termination.
It additionally allows, but does not require a second and third date of legal effect and termination in case single articles in omnibus laws codify separate
dates of legal effect. This granularity is important, because policies may stagger legal effects by entire years. If there is no second or third date
of legal effect or termination, the llm must pass "na" as an answer.
The output requirement in the json format demands a yyyy-mm form, which is detailled enough for the policy tracker, despite the dates usually being specified on a day-basis 
in the policies.
This task is only part of batch prompts and not included in single prompts.

=== Tasks 3: Crisis Reference

The llm is prompted to stat whether a policy text explicitly references COVID-19/the corona pandemic or the 2008 financial/economic crisis as a binary measure of 1 (yes) or 0 (no).


=== Tasks 4 and 5: Social Policy Field and Justification

The social policy field classification is the most central task in this experiment. It requires the llm to choose one of 10 classes, those being:
1. unemployment, 2. family/children, 3. housing, 4. disability, 5. retirement, 6. survivors, 7. sickness/health/care, 8. labour market, 9. taxes, 10. none.
Categories 1 to 9 are derived from three leading classification schemata in the field of social policy analysis, all of which
have slightly different use cases: ESSPROS @eurostat2026esspros , OECD taxben  and OECD SOCX. ESSPROS, the European System of Social Protection Statistics, is a "
framework that enables international comparison of the administrative national data on social protection" provided by eurostat (the European Union). 
THE OECD SOCX (OECD Social Expenditure Database) @adema2019socx is intended to compare social spending between OECD countries and is the only one
of the three schemas that includes "active labour market policies", which I expanded to "labour market policies" more generally. The OECD 
Tax-Benefit model @oecd2022taxben is a microsimulation framework that calculates net incomes, tax liabilities, and 
benefit entitlements for hypothetical households across OECD countries, enabling cross-national comparison of tax-benefit systems. It is the 
only of the three that included taxation as a category. By incorporating all three schemas, I maximized breadth while guaranteeing the 
relevance of all categories. I have added the tenth category "none" in case the data filtering mistakenly lead to the inclusion of a policy text that
not related to social policy at all. This is especially relevant when applying the policy tracker pipeline to other country cases for which filtering due to 
the country-specific data collection processes may look entirely different. Instead of distorting accuracy by a random assignment to one of 
the 9 categories, the none category can buffer this. The llm must assign one policy field (social_policy_field1) and can assign a second one in a second key-value pair (social_policy_field2). If there is 
no second policy field, the llm is required to pass "na" as an answer. If category 10. none was assignes in social_policy_field1, the llm must assign "na"
to social_policy_field2. 

Based on the definitions of the three schemas I developed definitions of the categories, which are part of an entire codebook that is attached in the 
Appendix and which also contains the phrasing and definitions of all other tasks.

The two social policy fields are part of both the batch and single prompts. Depending on the variant, the definitions of the categories are either 
provided to the llm or not.

Depending on the variant, the llm is required to provide a justification for its social policy field classification _before_ assigning the label. I followed Ahnert et al. 
@ahnert2025survey with their Restricted Reasoning Method.






= Research Design

== Factorial Experiment

This section describes the factorial experiment that I deploy to isolate the effects of prompt designs and model choice on compliance 
and accuracy of the model output. 

I therefore employ a 5 × 16 factorial experiment, crossing 5 models with 16 prompt configurations, the latter of which are 
derived from a 2⁴ fully crossed design spanning four prompt dimensions.

== Prompts

This section introduces 2⁴ design of the prompt variations. All other prompt components remain unaltered across all 16 prompt variations, that is
the json output schema and the system prompt. The json output schema is only differentiated along the batch versus single prompt dimension (see below) to mirror the deliberate 
inclusion versus exclusion of some tasks. The closed source model is the only model that through the openAI API
enables output forcing as JSON, which forces the model to comply to the given schema. All other models are prompted to follow the json schema
structure, but cannot be forced to do so through the API endpoint.
The json ouput schema is, along with all other prompts, provided in the Appendix.
The system prompt contains a brief role-assignment that provides context to the llm on how to behave in response 
to the user prompt that follows it. The system prompt also specifies the context of the policies. There is an entire literature on the possibilities and efficacy or persona prompting
and role assignment in the greater context of prompt engineering (see e.g., @zheng_is_2023 @zheng_when_2024 @lutz2025prompt). 
However, in this experiment the system prompt is held constant across all prompt variations in the following form:


_"You are an expert in German social policy legislation. You classify legislative texts (Gesetze, Bekanntmachungen, Verordnungen) from the 
Bundesgesetzblatt according to a structured codebook. When full texts are not retrieved, go by titles. 
Return your classifications as a JSON object with the exact fields specified."_






=== Zero versus Few Shots
The first dimension contrasts zero-shot prompts — where the model receives only the task instructions — against 
few-shot prompts that prepend three annotated examples drawn from the German gold standard sample, deliberately 
chosen to represent borderline and ambiguous cases (a family/tax omnibus law, a vocational training decree classifiable 
only from its title, and a cross-cutting disability/retirement regulation). 

=== Batch versus Single Prompts
The second dimension varies task scope: 
batch prompts ask the model to simultaneously produce a short English-language policy summary, extract one to three 
entry-into-force dates with termination dates, classify the social policy field, and flag whether the text contains an 
explicit crisis reference; single prompts reduce the task to social policy field classification alone, testing whether 
the multi-task framing dilutes classification quality. 

=== Definition versus no Definition
The third dimension manipulates label informativeness: nodef 
prompts present the ten social policy field labels as a bare list, while def prompts accompany each label with a 
detailed class definition derived from the codebook, including explicit exclusion rules for fields with overlapping 
scope (e.g., disability vs. sickness, family vs. taxes). 

=== Justification versus no Justification
The fourth dimension introduces chain-of-thought elicitation: 
jus prompts instruct the model to produce a written justification of its field assignment before committing to a 
label, while nojus prompts request the label directly. All prompts share an identical system message and label schema, 
so variation is confined to the four experimental factors; 



== Models 

I run the experiment with four open-source models and one proprietary model. @tab:models provides an overview of model specifications. 
Model sizes vary between a 35 billion (with 3 billion active) and 675 billion tokens (with mixture of experts). Parameter counts for the 
proprietary gpt model are undisclosed, but as per openAI's naming convention ('mini') it likely lies on the smaller end of the spectrum.

#figure(
  table(
    columns: (1.2fr, 1fr, 1fr, 1fr, 1fr, 1fr),
    align: (left, center, center, center, center, center),
    inset: (x: 4pt, y: 5pt),

    table.header(
      [ ],
      [*mistral-\ large-3-\ 675b*],
      [*llama-\ 3.3-70b*],
      [*qwen-3.6-\ 35b-a3b*],
      [*gpt-oss-\ 120b*],
      [*gpt-4.1-\ mini*],
    ),

    [parameters],       [675B],         [70B],          [35B],          [120B],         [n/a],
    [developer],        [Mistral],      [Meta],         [Alibaba],      [OpenAI],       [OpenAI],
    [context \ window],   [256k],         [128k],         [262k],         [128k],         [1M],
    [instr. tuned],     [yes],          [yes],          [yes],          [yes],          [yes],
    [reasoning],        [no],           [no],           [hybrid],       [yes],          [no],
    [release date],     [2025-12],      [2024-07],      [2026-04],      [2025-08],      [2025-04],
  ),
  caption: [Model overview.],
) <tab:models>


In the context of the experiments run here, all stochasticity parameters are set to the most deterministic setting for all 
models: seeds are fixed, temperature is set to 0, and top-p is set to 1.0 so that backend changes on the model developer's side 
cannot silently alter sampling. 


== Evaluation


In the following sections I describe how compliance and accuracy are operationalized. In investigating the two, I follow @atreja2025s, but I have 
adapted the operationalization to the core issues of my policy tracker.

=== Compliance

Compliance refers to how faithfully an llm follows prompt instructions. Non-compliance is costly in both time and money @atreja2025s, but the deeper 
problem is that unreliable outputs cannot serve as pipeline-ready data, which is the whole point of a policy tracker. 
In the best case szenario, non-compliance shifts the burden onto manual parsing and cleaning, which defeats the purpose of scaling policy tracking. In the worst case,
the output is entirely unusable. 
Each llm output is therefore checked against a set of five compliance criteria:
+ Does the required JSON output parse?
+ Are all required fields present?
+ Is social_policy_field1 one of the 10 valid categories?
+ Is social_policy_field2 one of the 9 valid categories or "na"?
+ For batch prompts: is crisis_ref euqal to 0 or 1?

I also build a strict compound measure of compliance that, if any one of the five checks fails, counts 
the entire output for a policy counts as non-compliant. Based on that I compute a compliance rate:

$ "Compliance rate" = ("number of policy entries with compliant output") / ("total number of policy entries in the evaluation sample") $


Though of smaller relevance, I also check compliance with the format yyyy-mm for the variables legally_effective (_1 to _3) and 
leg_eff_terminate (_1 to _3). However, I do not include them in the the compound compliance measure.

=== Accuracy

To estimate accuracy, I compare an llm's classification against a human-labelled goldstandard. For the goldstandard, a human coder is
given the full codebook in order to label a 10% subset of the retrieved social policy relevant documents. This essentially mirrors the context the llm is given with the most elaborate prompt 
that encorporates few-shot examples, full class definitions, and the requirement to provide justifications for both 
crisis-relatedness and social policy field classification. The codebook is provided in the Appendix of this paper.
The aim here is simple: If the models can work with less information, i.e. fewer input tokens (and in the case of justification also output
tokens) and still yield acceptable agreement with the human coder(s), computational costs can be reduced. The scaling of tracking social policy 
through llm-assisted automation then becomes more feasible and efficient. Efficiency would be highest if this were possible in batch instead
of single prompts.

At the current state of this paper, the goldstandard has been labelled by me alone. For a full paper, at least one more social policy expert
will label the goldstandard. All accuracy results reported here should therefore be interpreted with this 
limitation in mind. Inter-coder agreement among human coders would allow us to distinguish inherently ambiguous cases, i.e. cases for which 
even trained experts disagree, from more straightforward ones. Disagreement between human and llm annotators, and by extension llm performance, 
can then be evaluated against this baseline of human agreement, providing a more calibrated assessment through task difficulty.

To measure accuracy, I compute the following measures:

measures I compute!!!

= Results

== Compliance



= Conclusion

== Limitations
- at this point, the gold standard has only been labelled by me. Ultimately, the gold standard will be labelled by at least one other
social policy scholar who is not connected to this project.
- changing or expanding the classification tasks given to the llms will influence overall performance. Therefore, adding new tasks requires
new experimental tests taking the findings of this experiment into account.
- berttopic modeling only done in 1 round -> expand to two at least
- a prompt dimension not tested here: prompting for probabilities for each category of social policy field instead of string-label decisions
- more complex labelling tasks to be included later
- i have not fixed top-k

// Bibliography with Chicago Author-Date style
#bibliography("references_adsl.bib", title: "References", style: "chicago-author-date")



//Appendix
= Appendix