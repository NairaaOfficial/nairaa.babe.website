#!/bin/bash

while true; do
  ids=$(gh run list --limit 1000 --json databaseId -q '.[].databaseId')
  if [ -z "$ids" ]; then
    echo "No more workflow runs to delete."
    break
  fi
  for id in $ids; do
    echo "Deleting run $id"
    gh run delete "$id" <<< "y"
  done
done