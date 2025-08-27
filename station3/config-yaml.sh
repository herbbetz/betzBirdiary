#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: ${0##*/} <yaml_file>"
    exit 1
fi

YAML_FILE="$1"
JSON_FILE="config.json"

if [[ ! -f "$YAML_FILE" ]]; then
    echo "YAML file '$YAML_FILE' not found."
    exit 1
fi

if [[ ! -f "$JSON_FILE" ]]; then
    echo "JSON file '$JSON_FILE' not found."
    exit 1
fi

# Parse YAML (flat key: value format)
# Remove quotes and trailing \r, trim spaces, convert to key=value
mapfile -t kv_pairs < <( # put lines into array kv_pairs, -t removes trailing \n
    grep -v '^\s*#' "$YAML_FILE" |             # remove comment lines
    grep ':' |                                 # keep lines with colon
    sed 's/^[[:space:]]*//; s/[[:space:]]*$//' | # trim leading/trailing space
    tr -d '"' |                                # remove double quotes
    tr -d '\r' |                               # remove Windows line endings
    sed 's/[[:space:]]*:[[:space:]]*/=/'       # replace : with =
)

tmp_json=$(mktemp)
cp "$JSON_FILE" "$tmp_json"

for kv in "${kv_pairs[@]}"; do
    # %% vs #, remove part after vs before:
    key="${kv%%=*}"
    value="${kv#*=}"

    if [[ -z "$key" ]]; then # check for ':value' in the yaml, whereas 'key:' should end up in the json as "key":""
        echo "Error: Empty key found in $YAML_FILE"
        rm -f "$tmp_json"
        exit 1
    fi


    # jq -e 'has($k)' ensures the key exists at the top level of the JSON:
    if ! jq -e --arg k "$key" 'has($k)' "$tmp_json" > /dev/null; then
        echo "Error: Key '$key' not found in $JSON_FILE"
        rm -f "$tmp_json"
        exit 1
    fi

    # Update value using jq to set .[$k] to the YAML’s value (string by default):
    tmp_json2=$(mktemp)
    jq --arg k "$key" --arg v "$value" '.[$k] = $v' "$tmp_json" > "$tmp_json2"
    mv "$tmp_json2" "$tmp_json"
done

# Overwrite the JSON file
flock "$JSON_FILE" ./update_config.sh "$tmp_json"
rm "$tmp_json"
echo "$JSON_FILE updated from $YAML_FILE."