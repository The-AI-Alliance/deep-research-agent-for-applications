#!/usr/bin/env zsh

# A helper script for running the applications with several variants
# for the optional arguments.

# WARNING: At this time, these model definitions actually don't work. You have
# to set the "default_model" in the mcp_agent.config.yaml (when using OpenAI or
# Anthropic) or mcp_agent.config.ollama.yaml (when using ollama).
OPENAI_RESEARCH_MODEL="gpt-4o"
OPENAI_EXCEL_WRITER_MODEL="o4-mini"
OLLAMA_RESEARCH_MODEL="gpt-oss:20b"
#OLLAMA_RESEARCH_MODEL="qwen3.5:27b"
# When running with Ollama, there is less need to run a low-cost model 
# for the Excel spreadsheet generation task, and keeping the same model
# in memory saves time.
OLLAMA_EXCEL_WRITER_MODEL="$OLLAMA_RESEARCH_MODEL"

help() {
	cat <<EOF
Usage: $0 [options] [make_options]
Where the options are:
--target  TARGET  Build make target TARGET (default: app-run)
--finance         Run the finance app (default)
--medical         Run the medical app
--arxiv           Run the arxiv app

For the finance app: These flags are ignored if not running the finance app.
--apple           Research on Apple
--ibm             Research on IBM  
--meta            Research on Meta

For the medical and arxiv app:
--query  "QUERY"  Use this query (ignored if not running the medical app)
--title  "TITLE"  Report title
--report-title "TITLE"  
                  Same as "--title TITLE".
--terms  "TERMS"  Terms/keywords that are important for this topic. (Only for the medical app)
--categories "CATEGORIES"
                  The categories to focus on. (Only for the arxiv app)

--openai          Use OpenAI models for inference:
                    Orchestration:    $OPENAI_RESEARCH_MODEL
                    Excel report gen: $OPENAI_EXCEL_WRITER_MODEL
--ollama          Use Ollama models for inference:
                    Orchestration:    $OLLAMA_RESEARCH_MODEL
                    Excel report gen: $OLLAMA_EXCEL_WRITER_MODEL
--short | --short-run
                  Do a short run (low "max values" for testing)
--noop            Just print the command that will be executed, but don't run it.

All other arguments passed to make. So for example, to see what command make will
run without running it, pass "-n".
EOF
}

# Some variable definitions won't apply for all apps!
vars=()
make_args=()
which_app=finance
target=
show_footer=true
TIME=time
while [[ $# -gt 0 ]]
do
	case $1 in
	-h|--help)
		help
		exit 0
		;;
	--noop)
		NOOP=echo
		;;
	--short|--short-run)
		vars+=(
			APP_ARGS="--short-run"
		)
		;;
	--target)
		shift
		target=$1
		# Only time execution and show the footer at the bottom if we are doing the default run target...
		TIME=
		show_footer=false 
		;;
	--finance)
		which_app=finance
		vars+=(
			APP="finance"
		)
		;;
	--medical)
		which_app=medical
		vars+=(
			APP="medical"
		)
		;;
	--arxiv)
		which_app=arxiv
		vars+=(
			APP="arxiv"
		)
		;;
	--openai)
		vars+=(
			RESEARCH_MODEL="$OPENAI_RESEARCH_MODEL"
			EXCEL_WRITER_MODEL="$OPENAI_EXCEL_WRITER_MODEL"
			INFERENCE_PROVIDER="openai"
		)
		;;
	--apple)
		vars+=(
			TICKER="AAPL" 
			COMPANY_NAME="Apple Inc."
		)
		;;
	--ibm)
		vars+=(
			TICKER="IBM" 
			COMPANY_NAME="International Business Machines Corporation"
		)
		;;
	--meta)
		vars+=(
			TICKER="META" 
			COMPANY_NAME="Meta Platforms, Inc."
		)
		;;
	--query)
		shift
		vars+=(
			QUERY="$1" 
		)
		;;
	--title|--report-title)
		shift
		vars+=(
			REPORT_TITLE="$1" 
		)
		;;
	--terms)
		shift
		vars+=(
			TERMS="$1"
		)
		;;
	--categories)
		shift
		vars+=(
			CATEGORIES="$1"
		)
		;;
	--ollama)
		vars+=(
			RESEARCH_MODEL="$OLLAMA_RESEARCH_MODEL"
			EXCEL_WRITER_MODEL="$OLLAMA_EXCEL_WRITER_MODEL"
			INFERENCE_PROVIDER="ollama"
		)
		;;
	*)
		make_args+=("$1")
		;;
	esac
	shift
done

[[ -z $target ]] && target=app-run-$which_app

started=$(date)
echo $started

$TIME $NOOP make "${vars[@]}" "${make_args[@]}" $target

$show_footer || exit 0

cat <<EOF

=============================================
Started:  $started
Finished: $(date)
=============================================
EOF

# "beep"
print "\a\a"
sleep 1
print "\a\a"
