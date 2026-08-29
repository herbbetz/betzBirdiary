#!/bin/bash
# write lastdown.json when called as './lastdownwrite.sh a_message'
#!/bin/bash
# Usage: ./lastdownwrite.sh "a message"
APPDIR="$HOME/station3"
jsonfile="$APPDIR/lastdown.json"
tempfile="$APPDIR/lastdown.json.tmp"

if [[ -z "$1" ]]; then
    msg="anyshutdown"
else
    msg="$1"
fi

formatted_date=$(date "+%Y-%m-%d %H:%M")

# non existing 'testmode' property will be added as 'testmode=0'
if [[ -f "$jsonfile" ]]; then
    if jq \
        --arg msg "$msg" \
        --arg date "$formatted_date" \
        '.testmode = (.testmode // 0) | .msg = $msg | .date = $date' \
        "$jsonfile" > "$tempfile"
    then
        mv "$tempfile" "$jsonfile"
    else
        rm -f "$tempfile"
        echo "Error: could not update $jsonfile" >&2
        exit 1
    fi
else
    if jq -n \
        --arg msg "$msg" \
        --arg date "$formatted_date" \
        --argjson testmode 0 \
        '{msg: $msg, date: $date, testmode: $testmode}' \
        > "$tempfile"
    then
        mv "$tempfile" "$jsonfile"
    else
        rm -f "$tempfile"
        echo "Error: could not create $jsonfile" >&2
        exit 1
    fi
fi
sleep 1