@Library('vaas-shared') _

cdPipelineLambda(
        project: 'days_past_due',
        projectPath: '.',
        slackChannel: 'elisir-team',
        terraformFolder: 'deploy/terraform',
        terraformConfigBaseFolder: 'configuration'
)
