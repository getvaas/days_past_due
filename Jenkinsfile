def SERVICE_NAME = "days-past-due"
def REPOSITORY_NAME = "${SERVICE_NAME}-repository"
def LAMBDA_NAME = "${params.Environment}-${SERVICE_NAME}-lambda"
def COLOR_MAP = [
    SUCCESS: 'good',
    FAILURE: 'danger'
]

def REPOSITORY_URL
def JENKINS_CREDENTIALS

if (params.Environment == "prod") {
    REPOSITORY_URL = "387023001980.dkr.ecr.us-east-1.amazonaws.com"
    JENKINS_CREDENTIALS = "jenkins-aws-production-core"
} else {
    REPOSITORY_URL = "052650215423.dkr.ecr.us-east-1.amazonaws.com"
    JENKINS_CREDENTIALS = "jenkins-aws-development"
}

pipeline {
    agent any
    stages {
        stage("Initialization") {
            steps {
                buildDescription "Environment: ${params.Environment} - Branch: ${params.Branch}"
            }
        }
        stage("NotificateAction") {
            steps {
                slackSend(
                    channel: "jenkins",
                    color: "warning",
                    message: "*Action:* Beginning the CI\n*Environment:* ${params.Environment}\n*JobName:* ${JOB_BASE_NAME}\n*Version:* v${BUILD_ID}\n*Username:* ${BUILD_USER}"
                )
            }
        }
        stage("BuildImage") {
            steps {
                script {
                    sh "docker build -t ${params.Environment}-${REPOSITORY_NAME} ."
                    sh "docker tag ${params.Environment}-${REPOSITORY_NAME}:latest ${REPOSITORY_URL}/${params.Environment}-${REPOSITORY_NAME}:v${BUILD_ID}"
                }
            }
        }
        stage("UploadToEcr") {
            steps {
                script {
                    withAWS(credentials: JENKINS_CREDENTIALS, region: "us-east-1") {
                        sh "aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${REPOSITORY_URL}"
                        sh "docker push ${REPOSITORY_URL}/${params.Environment}-${REPOSITORY_NAME}:v${BUILD_ID}"
                    }
                }
            }
        }
        stage("UpdateLambda") {
            steps {
                script {
                    withAWS(credentials: JENKINS_CREDENTIALS, region: "us-east-1") {
                        sh """
                            aws lambda update-function-code \
                                --function-name ${LAMBDA_NAME} \
                                --image-uri ${REPOSITORY_URL}/${params.Environment}-${REPOSITORY_NAME}:v${BUILD_ID} \
                                --region us-east-1
                        """
                    }
                }
            }
        }
    }
    post {
        always {
            slackSend(
                channel: "jenkins",
                color: COLOR_MAP[currentBuild.currentResult],
                message: "*Action:* Finished CI\n*Environment:* ${params.Environment}\n*JobName:* ${JOB_BASE_NAME}\n*Version:* v${BUILD_ID}\n*Username:* ${BUILD_USER}\n*Status:* ${currentBuild.currentResult}"
            )
        }
    }
}
