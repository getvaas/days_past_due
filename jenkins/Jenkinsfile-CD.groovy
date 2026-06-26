def projectName = "days-past-due"
def slackChannel = "jenkins"
def isManual = env.isManual.toBoolean()
def terraformFolder = "terraform"
def terraformConfigBaseFolder = "configuration"
def authorEmail = 'Github'
def vaasScriptPath = "~/vaas-jenkins-scripts"
def customGitBranch = "${customGitBranch}"
def targetEnvironment = "${targetEnvironment}"
def version = "${version}"
def COLOR_MAP = [
    SUCCESS: 'good',
    FAILURE: 'danger',
    UNSTABLE: 'danger',
    RUNNING: 'warning'
]
def AWS_PARAMETERS = [
    'Development': [
        'ENV'                   : "dev",
        'JENKINS_CREDENTIAL_ID' : "jenkins-aws-development",
        'S3_BUCKET_NAME'        : "6fc5w786-dev-vaas-configurations/days-past-due/dev-${projectName}",
        'AWS_REGION'            : "us-east-1",
        'ECR_REPOSITORY_URL'    : "052650215423.dkr.ecr.us-east-1.amazonaws.com/dev-${projectName}-repository",
        'ECR_LOGIN_URL'         : "052650215423.dkr.ecr.us-east-1.amazonaws.com",
        'LAMBDA_FUNCTION_NAME'  : "dev-${projectName}-lambda",
    ],
    'Staging': [
        'ENV'                   : "stg",
        'JENKINS_CREDENTIAL_ID' : "jenkins-aws-development",
        'S3_BUCKET_NAME'        : "6fc5w786-stg-vaas-configurations/days-past-due/stg-${projectName}",
        'AWS_REGION'            : "us-east-1",
        'ECR_REPOSITORY_URL'    : "052650215423.dkr.ecr.us-east-1.amazonaws.com/stg-${projectName}-repository",
        'ECR_LOGIN_URL'         : "052650215423.dkr.ecr.us-east-1.amazonaws.com",
        'LAMBDA_FUNCTION_NAME'  : "stg-${projectName}-lambda",
    ],
    'Production': [
        'ENV'                   : "prod",
        'JENKINS_CREDENTIAL_ID' : "jenkins-aws-production-core",
        'S3_BUCKET_NAME'        : "tt9rln6r-prod-vaas-configurations/days-past-due/prod-${projectName}",
        'AWS_REGION'            : "us-east-1",
        'ECR_REPOSITORY_URL'    : "387023001980.dkr.ecr.us-east-1.amazonaws.com/prod-${projectName}-repository",
        'ECR_LOGIN_URL'         : "387023001980.dkr.ecr.us-east-1.amazonaws.com",
        'LAMBDA_FUNCTION_NAME'  : "prod-${projectName}-lambda",
    ]
]
pipeline {
    agent {
        label 'arm-agent'
    }
    environment {
        PATH="/usr/local/bin:/var/lib/jenkins/.local/bin:${env.PATH}"
        GIT_SHORT_COMMIT = sh(script: "printf \$(git rev-parse --short ${GIT_COMMIT})", returnStdout: true)
    }
    stages {
        stage('Notify the action') {
            steps {
                script {
                    if (isManual) {
                        authorEmail = "${BUILD_USER_EMAIL}"
                    }
                    def notifyActionSlackMessage = """\
                        *Action:* Continuous Deployment
                        *Status:* RUNNING
                        *Version:* ${version}
                        *Repository:* ${GIT_URL}
                        *AuthorEmail:* ${authorEmail}
                        *SourceBranch:* ${customGitBranch}
                        *EnvironmentDeploy:* ${targetEnvironment}
                        *Mode:* ${(isManual) ? 'Manual' : 'Github'}
                        *PipelineUrl:* ${BUILD_URL}
                        *LatestCommit:* ${GIT_URL}/commit/${GIT_COMMIT}
                    """
                    slackSend(
                        channel: slackChannel,
                        color: "${COLOR_MAP['RUNNING']}",
                        message: notifyActionSlackMessage.stripIndent()
                    )
                }
            }
        }
        stage('Apply terraform changes') {
            steps {
                script {
                    def parameters = AWS_PARAMETERS[targetEnvironment]
                    withAWS(credentials: parameters['JENKINS_CREDENTIAL_ID'], region: parameters['AWS_REGION']) {
                        sh "mkdir -p ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts"
                        sh "cd ${terraformFolder} && \
                        rm -rf .terraform* && \
                        terraform init -backend-config=${terraformConfigBaseFolder}/${parameters['ENV']}/backend.conf && \
                        terraform apply \
                            -var-file=${terraformConfigBaseFolder}/${parameters['ENV']}/vars.tfvars \
                            -var-file=${terraformConfigBaseFolder}/global.tfvars \
                            -auto-approve && \
                        cd -"
                    }
                }
            }
        }
        stage('Build Docker Image') {
            steps {
                script {
                    def dockerImage = "${AWS_PARAMETERS[targetEnvironment]['ECR_REPOSITORY_URL']}:${GIT_SHORT_COMMIT}"
                    sh """
                        if ! docker info > /dev/null 2>&1; then
                            dockerd &
                            sleep 5
                        fi
                        docker build --platform linux/amd64 -f Dockerfile -t ${dockerImage} .
                    """
                }
            }
        }
        stage('Push Docker Image to ECR') {
            steps {
                script {
                    def parameters = AWS_PARAMETERS[targetEnvironment]
                    def dockerImage = "${parameters['ECR_REPOSITORY_URL']}:${GIT_SHORT_COMMIT}"
                    def latestImage = "${parameters['ECR_REPOSITORY_URL']}:latest"
                    withAWS(credentials: parameters['JENKINS_CREDENTIAL_ID'], region: parameters['AWS_REGION']) {
                        sh "aws ecr get-login-password --region ${parameters['AWS_REGION']} | docker login --username AWS --password-stdin ${parameters['ECR_LOGIN_URL']}"
                        sh "docker push ${dockerImage}"
                        sh "docker tag ${dockerImage} ${latestImage}"
                        sh "docker push ${latestImage}"
                    }
                }
            }
        }
        stage('Upload to S3') {
            steps {
                script {
                    withAWS(credentials: AWS_PARAMETERS[targetEnvironment]['JENKINS_CREDENTIAL_ID'], region: AWS_PARAMETERS[targetEnvironment]['AWS_REGION']) {
                        sh "aws s3 cp ${terraformFolder}/tfplan s3://${AWS_PARAMETERS[targetEnvironment]['S3_BUCKET_NAME']}/history/previous_version/tfplan"
                        sh "aws s3 cp ${terraformFolder}/tfplan.json s3://${AWS_PARAMETERS[targetEnvironment]['S3_BUCKET_NAME']}/history/previous_version/tfplan.json"
                    }
                }
            }
        }
        stage('Deploy to Lambda') {
            steps {
                script {
                    def parameters = AWS_PARAMETERS[targetEnvironment]
                    def dockerImage = "${parameters['ECR_REPOSITORY_URL']}:${GIT_SHORT_COMMIT}"
                    withAWS(credentials: parameters['JENKINS_CREDENTIAL_ID'], region: parameters['AWS_REGION']) {
                        sh "aws lambda update-function-code --function-name ${parameters['LAMBDA_FUNCTION_NAME']} --image-uri ${dockerImage}"
                    }
                }
            }
        }
    }
    post {
        always {
            script {
                def postAlwaysSlackMessage = """\
                    *Action:* Continuous Deployment
                    *Status:* ${currentBuild.currentResult}
                    *Version:* ${version}
                    *Repository:* ${GIT_URL}
                    *AuthorEmail:* ${authorEmail}
                    *SourceBranch:* ${customGitBranch}
                    *EnvironmentDeploy:* ${targetEnvironment}
                    *Mode:* ${(isManual) ? 'Manual' : 'Github'}
                    *PipelineUrl:* ${BUILD_URL}
                    *LatestCommit:* ${GIT_URL}/commit/${GIT_COMMIT}
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
                echo 'Deployed successfully!'
                echo "Version deployed: ${version}"
            }
        }
    }
}
