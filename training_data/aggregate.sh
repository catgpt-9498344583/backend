#!/bin/bash

# Output file name
OUTFILE="aggregated.json"

# Start JSON array
echo "[" > "$OUTFILE"

first=true

for f in *.json; do
    # Skip output file if it also ends with .json
    if [ "$f" = "$OUTFILE" ]; then
        continue
    fi

    if [ "$first" = true ]; then
        first=false
    else
        # Add a comma before the next object
        echo "," >> "$OUTFILE"
    fi

    # Append file contents
    cat "$f" >> "$OUTFILE"
done

# Close JSON array
echo "]" >> "$OUTFILE"

echo "Created $OUTFILE"
