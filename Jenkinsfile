pipeline {
    agent { label 'docker-agent' }
    stages {
        stage('Test') {
            steps {
                sshagent(['dev-opsmanager']) {
                    sh '''
                        ssh root@192.168.3.18 "docker version"
                    '''
                }
            }
        }
    }
}