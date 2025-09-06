# N.B. This script must be sourced, rather than executed, to get
# the environment variables into the correct process environment

AWS_REGION="eu-west-2"
AWS_PROFILE="${AWS_PROFILE:-production}"
NO_AWS_PROFILE="${NO_AWS_PROFILE:-FALSE}"

echo "AWS_PROFILE: ${AWS_PROFILE}"
echo "AWS_REGION: ${AWS_REGION}"
echo "NO_AWS_PROFILE: ${NO_AWS_PROFILE}"

function aws_profile() {
  if [ "${NO_AWS_PROFILE}" = "FALSE" ]; then
    echo "--profile ${AWS_PROFILE}"
  fi
}


function get_token() {
  # shellcheck disable=SC2046
  aws codeartifact get-authorization-token \
    --domain open-corporates \
    --domain-owner 089449186373 \
    --region "$AWS_REGION" \
    $(aws_profile) \
    --output text \
    --query authorizationToken
}

# shellcheck disable=SC2046
if aws sts get-caller-identity $(aws_profile) &>/dev/null; then
  echo "AWS SSO already logged in"
else
  echo "Need to login to AWS SSO"
  # avoid weird behaviour with multiple browser profiles
  aws sso login $(aws_profile) --no-browser
fi


export POETRY_HTTP_BASIC_OCPY_USERNAME="aws"
# shellcheck disable=SC2155
export POETRY_HTTP_BASIC_OCPY_PASSWORD="$(get_token)"

# we need a second repo/set of credentials because poetry tries to use
# the wrong (source) URL to publish to otherwise
export POETRY_HTTP_BASIC_OCPYUPLOAD_USERNAME="aws"
# shellcheck disable=SC2155
export POETRY_HTTP_BASIC_OCPYUPLOAD_PASSWORD="$(get_token)"


echo "exported POETRY_HTTP_BASIC_OCPY_USERNAME=aws"
echo "exported POETRY_HTTP_BASIC_OCPY_PASSWORD=${POETRY_HTTP_BASIC_OCPY_PASSWORD:0:5}..."
echo "exported POETRY_HTTP_BASIC_OCPYUPLOAD_USERNAME=aws"
echo "exported POETRY_HTTP_BASIC_OCPYUPLOAD_PASSWORD=${POETRY_HTTP_BASIC_OCPYUPLOAD_PASSWORD:0:5}..."
