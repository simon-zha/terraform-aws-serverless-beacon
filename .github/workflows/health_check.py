# .github/workflows/health-check.yml
name: API Health Check

on:
  workflow_dispatch:
    inputs:
      environment:
        description: "Environment to check (dev/staging/prod/all)"
        required: false
        default: "all"
      expected_status:
        description: "Expected HTTP status code"
        required: false
        default: "200"
      retries:
        description: "Maximum retry attempts"
        required: false
        default: "6"
      timeout:
        description: "Per-request timeout in seconds"
        required: false
        default: "8"
      backoff:
        description: "Exponential backoff multiplier"
        required: false
        default: "2"
  schedule:
    - cron: "20 * * * *"

permissions:
  contents: read
  actions: read
  issues: write

jobs:
  health-check:
    name: Check ${{ matrix.environment_name }} API
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        include:
          - environment_name: dev
            github_environment: dev
            api_var: DEV_API_URL
            api_url: ${{ vars.DEV_API_URL }}
          - environment_name: staging
            github_environment: staging
            api_var: STAGING_API_URL
            api_url: ${{ vars.STAGING_API_URL }}
          - environment_name: prod
            github_environment: prod
            api_var: PROD_API_URL
            api_url: ${{ vars.PROD_API_URL }}
    environment: ${{ matrix.github_environment }}
    if: >
      ${{
        (github.event_name != 'workflow_dispatch') ||
        (github.event.inputs.environment == 'all') ||
        (github.event.inputs.environment == matrix.environment_name)
      }}
    env:
      API_URL: ${{ matrix.api_url }}
      API_VAR_KEY: ${{ matrix.api_var }}
      ENV_NAME: ${{ matrix.environment_name }}
      EXPECTED_STATUS: ${{ (github.event_name == 'workflow_dispatch' && github.event.inputs.expected_status) || '200' }}
      RETRIES: ${{ (github.event_name == 'workflow_dispatch' && github.event.inputs.retries) || '6' }}
      TIMEOUT: ${{ (github.event_name == 'workflow_dispatch' && github.event.inputs.timeout) || '8' }}
      BACKOFF: ${{ (github.event_name == 'workflow_dispatch' && github.event.inputs.backoff) || '2' }}
      AWS_REGION: ${{ vars.AWS_REGION || 'ap-southeast-2' }}
      COGNITO_USER_POOL_ID: ${{ secrets.COGNITO_USER_POOL_ID || '' }}
      COGNITO_APP_CLIENT_ID: ${{ secrets.COGNITO_APP_CLIENT_ID || '' }}
      COGNITO_USERNAME: ${{ secrets.BEACON_GUEST_USERNAME || secrets.BEACON_ADMIN_USERNAME || '' }}
      COGNITO_PASSWORD: ${{ secrets.BEACON_GUEST_PASSWORD || secrets.BEACON_ADMIN_PASSWORD || '' }}
    steps:
      - name: Validate API URL
        run: |
          if [ -z "${API_URL}" ]; then
            echo "::error::Missing API URL for ${ENV_NAME} (vars.${API_VAR_KEY})."
            exit 1
          fi
          if [ -n "${COGNITO_USER_POOL_ID}" ] && [ -z "${COGNITO_APP_CLIENT_ID}" ]; then
            echo "::error::COGNITO_USER_POOL_ID is set but COGNITO_APP_CLIENT_ID is missing."
            exit 1
          fi

      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        if: ${{ env.COGNITO_USER_POOL_ID != '' && env.COGNITO_APP_CLIENT_ID != '' && env.COGNITO_USERNAME != '' && env.COGNITO_PASSWORD != '' }}
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Obtain Cognito token
        if: ${{ env.COGNITO_USER_POOL_ID != '' && env.COGNITO_APP_CLIENT_ID != '' && env.COGNITO_USERNAME != '' && env.COGNITO_PASSWORD != '' }}
        id: cognito
        shell: bash
        run: |
          set -euo pipefail
          response=$(aws cognito-idp admin-initiate-auth \
            --user-pool-id "${COGNITO_USER_POOL_ID}" \
            --region "${AWS_REGION}" \
            --client-id "${COGNITO_APP_CLIENT_ID}" \
            --auth-flow ADMIN_USER_PASSWORD_AUTH \
            --auth-parameters USERNAME="${COGNITO_USERNAME}",PASSWORD="${COGNITO_PASSWORD}")
          token=$(echo "${response}" | jq -r '.AuthenticationResult.IdToken // empty')
          if [ -z "${token}" ]; then
            echo "::error::Failed to obtain Cognito IdToken."
            exit 1
          fi
          echo "token=${token}" >> "$GITHUB_OUTPUT"
          echo "BEARER_TOKEN=${token}" >> "$GITHUB_ENV"

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Run health check
        id: health
        continue-on-error: true
        run: |
          set -euo pipefail
          EXTRA_ARGS=()
          if [ -n "${BEARER_TOKEN:-}" ]; then
            EXTRA_ARGS+=(--bearer-token "${BEARER_TOKEN}")
          fi
          python scripts/health_check.py \
            --url "${API_URL}" \
            --expected-status "${EXPECTED_STATUS}" \
            --retries "${RETRIES}" \
            --timeout "${TIMEOUT}" \
            --backoff "${BACKOFF}" \
            "${EXTRA_ARGS[@]}"

      - name: Handle failure
        if: steps.health.outcome == 'failure'
        uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          script: |
            const envName = '${{ matrix.environment_name }}';
            const apiUrl = process.env.API_URL;
            const runUrl = `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;
            const title = `API Health Check failed: ${envName}`;
            const body = [
              `Environment: **${envName}**`,
              `URL: ${apiUrl}`,
              `Workflow run: ${runUrl}`,
              '',
              'Please verify API availability.'
            ].join('\n');
            const { data: issues } = await github.rest.issues.listForRepo({
              owner: context.repo.owner,
              repo: context.repo.repo,
              state: 'open',
              per_page: 100,
              labels: 'health-check'
            });
            const existing = issues.find(issue => issue.title === title);
            if (existing) {
              await github.rest.issues.createComment({
                owner: context.repo.owner,
                repo: context.repo.repo,
                issue_number: existing.number,
                body: `Health check failed again. Details: ${runUrl}`
              });
            } else {
              await github.rest.issues.create({
                owner: context.repo.owner,
                repo: context.repo.repo,
                title,
                body,
                labels: ['health-check','automated']
              });
            }
            core.setFailed(`Health check failed for ${envName}`);

      - name: Append result to summary
        if: always()
        run: |
          if [ "${{ steps.health.outcome }}" = "success" ]; then
            status="[PASS]"
          else
            status="[FAIL]"
          fi
          {
            echo "### ${status} - ${ENV_NAME}"
            echo "- URL: ${API_URL}"
            echo "- Run: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
          } >> "$GITHUB_STEP_SUMMARY"

