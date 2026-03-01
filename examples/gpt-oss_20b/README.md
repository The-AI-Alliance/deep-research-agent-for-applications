# README for `examples/gpt-oss_20b`

This directory contains some example output files from various runs of the applications.

## Finance Application

* [`META_report.md`](META_report.md) - An early, successful run of an older version of the app output.
* [`META_report_problems.md`](META_report_problems.md) - A recent, unsuccessful run where data fetching ran into problems. This is example is provided mostly to illustrate that it's difficult to build agents that can reliably retrieve information from the open Internet!
* [`META_financials.xlsx`](META_financials.xlsx) - An Excel spreadsheet generated from a successful run.

## Medical Application

Three example reports from running the medical application with the query, _"What are the best treatments for diabetes mellitus?"_  and the terms, _"insulin, diabetes, pharmaceuticals, surgery."_ They were executed over several weeks with refinements to the [research agent prompt template](https://github.com/The-AI-Alliance/deep-research-agent-for-applications/blob/main/dra-apps/medical/templates/medical_research_agent.md), the MCP servers used, and some code changes over that time.

If you compare them, they have a lot of different material, reflecting the _stocahstic_ nature of LLMs. This suggests it's a good idea to run a report, for either application, several times and compare the results. Also, 

1. `diabetes_report` - Three runs
	1. ([Markdown](diabetes_report-1.md), [HTML](diabetes_report-1.html)). The earliest, with good information, but surpassed by the next two.
	1. ([Markdown](diabetes_report-2.md), [HTML](diabetes_report-2.html)). Close to the quality of #3.
	1. ([Markdown](diabetes_report-3.md), [HTML](diabetes_report-3.html)). The best report.
1. `covid_report` 
	1. ([Markdown](covid_report.md), [HTML](covid_report.html)). The most recent of the four medical examples.
