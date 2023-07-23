#!/bin/sh -l

GITHUB_BASEURL=https://api.github.com
GITHUB_API="/repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}/jobs"
eval "$(curl --get -Ss -H "Authorization: token ${INPUT_GITHUB_TOKEN}" -H "Accept: application/vnd.github.v3+json" "${GITHUB_BASEURL}${GITHUB_API}" \
| jq -r --arg job_name "${INPUT_JOB_NAME}" '.jobs | map(select(.name == $job_name)) | .[0] | @sh "job_id=\(.id) html_url=\(.html_url)"')"
echo "job_id=${job_id}"
# echo "html_url=${html_url}"
echo "job_id=${job_id}" >> $GITHUB_OUTPUT
# echo "html_url=${html_url}" >> $GITHUB_OUTPUT