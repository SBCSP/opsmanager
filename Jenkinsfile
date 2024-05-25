pipeline {
    agent { label 'docker-agent' }
    stages {
        stage('Test') {
            steps {
                withCredentials([sshUserPrivateKey(credentialsId: 'dev-opsmanager', keyFileVariable: 'MY_SSH_KEY')]) {
                    sh '''
                    ssh -i $MY_SSH_KEY root@192.168.3.18 "docker ps"
                    '''
                }
            }
        }
    }
}