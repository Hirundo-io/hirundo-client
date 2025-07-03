1. Set the following environment variable:
   GxccITHUB_WORKFLOW_REF: <path_to_deploy_to_pypi.yaml>
2. Make sure the pr.json fits to your needs, otherwise create your own json and give it as argument when you run act
3. Create your own api-key to be able to push the new pypi package to pypi/test.pypi
4. Make the variable ACT=true.
5. Example:
   act pull_request -e act-events/pr.json --secret-file act-events/pr.secrets --var-file pr.variables -W .github/workflows/deploy-to-pypi.yaml
