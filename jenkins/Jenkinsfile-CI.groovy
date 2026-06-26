def projectName = "days-past-due"
def slackChannel = "jenkins"

def nextJobName = "CD-Days-Past-Due"
def vaasScriptPath = "~/vaas-jenkins-scripts"
def reportMarkdownToCommentIntoPrGithubPythonScript = "report_markdown_to_comment_into_pr_github.py"
def ENVIRONMENT_CONVENTION = [
    "develop": "Development",
    "staging": "Staging",
    "master": "Production",
]
def AWS_PARAMETERS = [
    'Development': [
        'JENKINS_CREDENTIAL_ID': 'jenkins-aws-development',
        'AWS_REGION': 'us-east-1',
        'TERRAFORM_CONFIG_FOLDER': 'dev'
    ],
    'Staging': [
        'JENKINS_CREDENTIAL_ID': 'jenkins-aws-development',
        'AWS_REGION': 'us-east-1',
        'TERRAFORM_CONFIG_FOLDER': 'stg'
    ],
    'Production': [
        'JENKINS_CREDENTIAL_ID': 'jenkins-aws-production-core',
        'AWS_REGION': 'us-east-1',
        'TERRAFORM_CONFIG_FOLDER': 'prod'
    ]
]
def COLOR_MAP = [
    SUCCESS: 'good',
    FAILURE: 'danger',
    UNSTABLE: 'danger',
    RUNNING: 'warning'
]
def credentialsId = 'Vaas Jenkins App'
def gitTargetBranch = '-'
def isManual = false
def authorEmail = '-'
def gitUrl = scm.getUserRemoteConfigs()[0].getUrl()
def deployTheBranch = env.deployTheBranch.toBoolean()
def environmentDeploy = env.environmentDeploy
def ignoreTest = env.ignoreTest.toBoolean()
def pipelineUrl = "${BUILD_URL}"
def sourceUrl = '-'
def targetEnvironment = '-'
pipeline {
    agent {
        label 'arm-agent'
    }
    options {
        skipDefaultCheckout(true)
    }
    environment {
        PATH="/usr/local/bin:/var/lib/jenkins/.local/bin:${env.PATH}"
    }
    stages {
        stage('Checkout SCM') {
            steps {
                script {
                    cleanWs()
                    def gitVars = git(
                        url: "${gitUrl}",
                        credentialsId: "${credentialsId}",
                        branch: "${env.ghprbSourceBranch}"
                    )
                    if (env.ghprbActualCommitAuthorEmail != null) {
                        authorEmail = "${ghprbActualCommitAuthorEmail}"
                        gitTargetBranch = "${ghprbTargetBranch}"
                        environmentDeploy = "-"
                        sourceUrl = "${ghprbPullLink}"
                        targetEnvironment = ENVIRONMENT_CONVENTION.containsKey(env.ghprbTargetBranch) ? "${ENVIRONMENT_CONVENTION[gitTargetBranch]}" : "-"
                    } else {
                        isManual = true
                        authorEmail = "${BUILD_USER_EMAIL}"
                        targetEnvironment = "${environmentDeploy}"
                        sourceUrl = "${gitUrl.replace('.git','')}/commit/${gitVars.GIT_COMMIT}"
                    }
                    if (!deployTheBranch) {
                        environmentDeploy = '-'
                    }
                }
            }
        }
        stage('Notify the action') {
            steps {
                script {
                    def notifyActionSlackMessage = """\
                        *Action:* Continuous Integration
                        *Status:* RUNNING
                        *Repository:* ${gitUrl}
                        *AuthorEmail:* ${authorEmail}
                        *SourceBranch:* ${env.ghprbSourceBranch}
                        *TargetBranch:* ${gitTargetBranch}
                        *Mode:* ${(isManual) ? 'Manual' : 'Github'}
                        *DeployTheBranch:* ${(deployTheBranch) ? 'Yes' : 'No'}
                        *IgnoreTest:* ${(ignoreTest) ? 'Yes' : 'No'}
                        *EnvironmentDeploy:* ${environmentDeploy}
                        *PipelineUrl:* ${pipelineUrl}
                        *SourceLink:* ${sourceUrl}
                        """
                    slackSend(
                        channel: slackChannel,
                        color: "${COLOR_MAP['RUNNING']}",
                        message: notifyActionSlackMessage.stripIndent()
                    )
                }
            }
        }
        stage('Terraform Plan') {
            steps {
                script {
                    if (targetEnvironment == '-') {
                        echo "Ignore the Terraform stage"
                    } else {
                        def jenkinsCredentialId = "${AWS_PARAMETERS[targetEnvironment]['JENKINS_CREDENTIAL_ID']}"
                        def awsRegion = "${AWS_PARAMETERS[targetEnvironment]['AWS_REGION']}"
                        def terraformConfigFolder = "${AWS_PARAMETERS[targetEnvironment]['TERRAFORM_CONFIG_FOLDER']}"
                        withAWS(credentials: jenkinsCredentialId, region: awsRegion) {
                            sh "cd terraform && \
                            rm -rf .terraform* && \
                            terraform init -backend-config=configuration/${terraformConfigFolder}/backend.conf && \
                            terraform plan \
                                -var-file=configuration/${terraformConfigFolder}/vars.tfvars \
                                -var-file=configuration/global.tfvars \
                                -out=tfplan && \
                            terraform show -json tfplan > tfplan.json && \
                            cd -"
                        }
                        if (!isManual && !ignoreTest) {
                            sh "cp ${vaasScriptPath}/read_terraform_plan_file.py ./read_terraform_plan_file.py"
                            sh "python3.11 ./read_terraform_plan_file.py ./terraform/tfplan.json"
                        }
                    }
                }
            }
        }
        stage('Tests') {
            steps {
                script {
                    if (!ignoreTest) {
                        try {
                            sh "./scripts/run-tests.sh"
                        } catch (Exception e) {
                            echo "Test execution failed: ${e}"
                            error("Tests failed!")
                        }
                    } else {
                        echo "Ignoring the tests"
                    }
                }
            }
        }
        stage('Send Comments') {
            steps {
                script {
                    if (!isManual && !ignoreTest && targetEnvironment != '-') {
                        sh "cp ${vaasScriptPath}/${reportMarkdownToCommentIntoPrGithubPythonScript} ./${reportMarkdownToCommentIntoPrGithubPythonScript}"
                        withCredentials([usernamePassword(credentialsId: 'Jenkins-Credentials',
                            usernameVariable: 'GITHUB_APP',
                            passwordVariable: 'GITHUB_ACCESS_TOKEN')]) {
                                sh "python3.11 ${reportMarkdownToCommentIntoPrGithubPythonScript} ${ghprbGhRepository} ${ghprbPullId} ${GITHUB_ACCESS_TOKEN} terraform_plan.md"
                        }
                    } else {
                        echo "Ignore the action for send the comments to the pull request"
                    }
                }
            }
        }
    }
    post {
        always {
            script {
                def postAlwaysSlackMessage = """\
                        *Action:* Continuous Integration
                        *Status:* ${currentBuild.currentResult}
                        *Repository:* ${gitUrl}
                        *AuthorEmail:* ${authorEmail}
                        *SourceBranch:* ${env.ghprbSourceBranch}
                        *TargetBranch:* ${gitTargetBranch}
                        *Mode:* ${(isManual) ? 'Manual' : 'Github'}
                        *DeployTheBranch:* ${(deployTheBranch) ? 'Yes' : 'No'}
                        *IgnoreTest:* ${(ignoreTest) ? 'Yes' : 'No'}
                        *EnvironmentDeploy:* ${environmentDeploy}
                        *PipelineUrl:* ${pipelineUrl}
                        *SourceLink:* ${sourceUrl}
                        """
                slackSend(
                    channel: slackChannel,
                    color: "${COLOR_MAP[currentBuild.currentResult]}",
                    message: postAlwaysSlackMessage.stripIndent()
                )
            }
        }
        success {
            script {
                echo 'I succeeded!'
                if (isManual && deployTheBranch) {
                    build(
                        job: "${nextJobName}",
                        parameters: [
                            string(name: 'customGitBranch', value: "${env.ghprbSourceBranch}"),
                            string(name: 'targetEnvironment', value: "${environmentDeploy}")
                        ],
                        wait: false
                    )
                }
            }
        }
    }
}
