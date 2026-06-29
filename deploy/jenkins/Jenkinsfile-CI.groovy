@Library('vaas-shared') _

ciPipelineLambda(
        project: 'days_past_due',
        projectPath: '.',
        slackChannel: 'elisir-team',
        nextCdJob: 'CD-days-past-due',
        terraformFolder: 'deploy/terraform',
        terraformConfigBaseFolder: 'configuration',
        testDockerTarget: 'test-runner'
)
