#!/bin/bash

while true; do
  ids=$(gh run list --limit 1000 --json databaseId -q '.[].databaseId')
  if [ -z "$ids" ]; then
    echo "No more workflow runs to delete."
    break
  fi
  echo "$ids" | xargs -P 100 -I {} sh -c 'echo "Deleting run {}"; yes | gh run delete "{}"'
done