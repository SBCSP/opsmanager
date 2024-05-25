pipeline {
    agent { label 'docker-agent' }
    stages {
        stage('Test') {
            steps {
                sh 'docker version'
            }
        }
    }
}