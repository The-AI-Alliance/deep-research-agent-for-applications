# README for `examples/gpt-oss_20b`

This directory contains some example output files from various runs of the applications.

## Finance Application

These example outputs, which provide research on Meta, are in the `finance` directory:

* `META_report` ([Markdown](finance/META_report.md), [HTML](finance/META_report.html)) - An early, successful run of an older version of the app output.
* `META_report_problems` ([Markdown](finance/META_report_problems.md), [HTML](finance/META_report_problems.html)) - A recent, unsuccessful run where data fetching ran into problems. This is example is provided mostly to illustrate that it's difficult to build agents that can reliably retrieve information from the open Internet!
* [`META_financials.xlsx`](finance/META_financials.xlsx) - An Excel spreadsheet generated from a successful run.

## Medical Application

Here are three example reports from running the medical application with the query, _"What are the best treatments for diabetes mellitus?"_  and the terms, _"insulin, diabetes, pharmaceuticals, surgery,"_ which demonstrate the variability that occurs due to the stochastic nature of LLMs and the agents that use them. This suggests it's a good idea to run a report, for either application, several times and compare the results. However, it is also true that these runs occurred over several weeks with refinements to the [research agent prompt template](https://github.com/The-AI-Alliance/deep-research-agent-for-applications/blob/main/dra-apps/medical/templates/medical_research_agent.md), the MCP servers used, and some code changes over that time. There is also a single example of a COVID treatment report, which is the most recent example generated, reflecting the latest modifications to the code, prompts, etc.

These example outputs are in the `medical` directory.

`diabetes_report` - Three runs:

1. [Markdown](medical/diabetes_report-1.md), [HTML](medical/diabetes_report-1.html) - The earliest, with good information, but surpassed by the next two.
1. [Markdown](medical/diabetes_report-2.md), [HTML](medical/diabetes_report-2.html) - Close to the quality of #3.
1. [Markdown](medical/diabetes_report-3.md), [HTML](medical/diabetes_report-3.html) - The best report.

`covid_report` - One run:

1. [Markdown](medical/covid_report.md), [HTML](medical/covid_report.html) - The most recent of the four medical examples.

## ArXiv Application

This application focuses its research on papers found at [ArXiv](https://arxiv.org), supplemented by web search, and with additional support for parsing documents provided by [Docling](https://docling-project.github.io/docling/).

Two example outputs are provided, both running the same query. The first example was generated before Docling was added as an MCP server and the second was generated afterwards. However, most of the differences in the report reflect the stochastic behavior of the agents more than this configuration difference.

These example outputs are in the `arxiv` directory.

`synthesizing-data-arxiv_research_report` - Two runs:

1. [Markdown](arxiv/synthesizing-data-arxiv_research_report-1.md), [HTML](arxiv/synthesizing-data-arxiv_research_report-1.html) - Without use of Docling.
1. [Markdown](arxiv/synthesizing-data-arxiv_research_report-2.md), [HTML](arxiv/synthesizing-data-arxiv_research_report-2.html) - With use of Docling.
