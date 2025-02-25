#! /bin/bash

THIS_DIR="$(cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd)"

ARTIFACT_DIR=${ARTIFACT_DIR:-/tmp/ci-artifacts_$(date +%Y%m%d)}

MATBENCH_DATA_URL=""

source "$THIS_DIR/config_load_overrides.sh"

export MATBENCH_WORKLOAD=rhods-notebooks-ux

if [[ "${ARTIFACT_DIR:-}" ]] && [[ -f "${ARTIFACT_DIR}/variable_overrides" ]]; then
    source "${ARTIFACT_DIR}/variable_overrides"
fi

if [[ -z "${MATBENCH_WORKLOAD:-}" ]]; then
    echo "ERROR: $0 expects 'MATBENCH_WORKLOAD' to be set ..."
    exit 1
fi

generate_matbench::prepare_matrix_benchmarking() {
    WORKLOAD_STORAGE_DIR="$THIS_DIR/../../subprojects/matrix-benchmarking-workloads/$MATBENCH_WORKLOAD"
    WORKLOAD_RUN_DIR="$THIS_DIR/../../subprojects/matrix-benchmarking/workloads/$MATBENCH_WORKLOAD"

    rm -f "$WORKLOAD_RUN_DIR"
    ln -s "$WORKLOAD_STORAGE_DIR" "$WORKLOAD_RUN_DIR"

    pip install --quiet --requirement "$THIS_DIR/../../subprojects/matrix-benchmarking/requirements.txt"
    pip install --quiet --requirement "$WORKLOAD_STORAGE_DIR/requirements.txt"
}

_get_data_from_pr() {
    MATBENCH_DATA_URL=${PR_POSITIONAL_ARGS:-$MATBENCH_DATA_URL}
    if [[ -z "${MATBENCH_DATA_URL}" ]]; then
        echo "ERROR: _get_data_from_pr expects PR_POSITIONAL_ARGS or MATBENCH_DATA_URL to be set ..."
        exit 1
    fi

    if [[ -z "$MATBENCH_RESULTS_DIRNAME" ]]; then
        echo "ERROR: _get_data_from_pr expects MATBENCH_RESULTS_DIRNAME to be set ..."
    fi

    echo "$MATBENCH_DATA_URL" > "${ARTIFACT_DIR}/source_url"

    results_dir="$MATBENCH_RESULTS_DIRNAME/expe"
    mkdir -p "$results_dir"

    _download_data_from_url "$results_dir" "$MATBENCH_DATA_URL"
}

_download_data_from_url() {
    results_dir=$1
    shift
    url=$1
    shift

    if [[ "${url: -1}" != "/" ]]; then
        url="${url}/"
    fi

    mkdir -p "$results_dir"

    dl_dir=$(echo "$url" | cut -d/ -f4-)

    wget "$url" \
         --directory-prefix "$results_dir" \
         --cut-dirs=$(echo "${dl_dir}" | tr -cd / | wc -c) \
         --recursive \
         --no-host-directories \
         --no-parent \
         --execute robots=off \
         --quiet
}

generate_matbench::get_prometheus() {
    export PATH=$PATH:/tmp/bin
    if which prometheus 2>/dev/null; then
       echo "Prometheus already available."
       return
    fi
    PROMETHEUS_VERSION=2.36.0
    cd /tmp
    wget --quiet "https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz" -O/tmp/prometheus.tar.gz
    tar xf "/tmp/prometheus.tar.gz" -C /tmp
    mkdir -p /tmp/bin
    ln -sf "/tmp/prometheus-${PROMETHEUS_VERSION}.linux-amd64/prometheus" /tmp/bin
    ln -sf "/tmp/prometheus-${PROMETHEUS_VERSION}.linux-amd64/prometheus.yml" /tmp/
}

generate_matbench::generate_plots() {
    if [[ -z "$MATBENCH_RESULTS_DIRNAME" ]]; then
        echo "ERROR: expected MATBENCH_RESULTS_DIRNAME to be set ..."
    fi

    stats_content="$(cat "$WORKLOAD_STORAGE_DIR/data/ci-artifacts.plots")"

    echo "$stats_content"

    generate_url="stats=$(echo -n "$stats_content" | tr '\n' '&' | sed 's/&/&stats=/g')"

    cd "$ARTIFACT_DIR"
    ln -sf /tmp/prometheus.yml "."

    matbench parse

    retcode=0
    VISU_LOG_FILE="$ARTIFACT_DIR/_matbench_visualize.log"
    if ! matbench visualize --generate="$generate_url" |& tee > "$VISU_LOG_FILE"; then
        echo "Visualization generation failed :("
        retcode=1
    fi
    rm -f ./prometheus.yml

    mkdir -p figures_{png,html}
    mv fig_*.png "figures_png" 2>/dev/null || true
    mv fig_*.html "figures_html" 2>/dev/null || true

    if grep "^ERROR" "$VISU_LOG_FILE"; then
        echo "An error happened during the report generation, aborting."
        grep "^ERROR" "$VISU_LOG_FILE" > "$ARTIFACT_DIR"/FAILURE
        exit 1
    fi

    return $retcode
}

action=${1:-}

if [[ "$action" == "prepare_matbench" ]]; then
    set -o errexit
    set -o pipefail
    set -o nounset
    set -x

    generate_matbench::get_prometheus
    generate_matbench::prepare_matrix_benchmarking

elif [[ "$action" == "generate_plots" ]]; then
    set -o errexit
    set -o pipefail
    set -o nounset
    set -x

    generate_matbench::generate_plots

elif [[ "$action" == "from_dir" ]]; then
    set -o errexit
    set -o pipefail
    set -o nounset
    set -x

    dir=${2:-}

    if [[ -z "$dir" ]]; then
        echo "ERROR: no directory provided in 'from_dir' mode ..."
        exit 1
    fi
    export MATBENCH_RESULTS_DIRNAME="$dir"

    generate_matbench::get_prometheus
    generate_matbench::prepare_matrix_benchmarking

    generate_matbench::generate_plots

elif [[ "$action" == "from_pr_args" || "$JOB_NAME_SAFE" == "nb-plot" ]]; then
    set -o errexit
    set -o pipefail
    set -o nounset
    set -x

    export MATBENCH_RESULTS_DIRNAME="/tmp/matrix_benchmarking_results"
    _get_data_from_pr

    generate_matbench::get_prometheus
    generate_matbench::prepare_matrix_benchmarking

    generate_matbench::generate_plots

else
    echo "ERROR: unknown action='$action' (JOB_NAME_SAFE='$JOB_NAME_SAFE')"
    exit 1
fi
