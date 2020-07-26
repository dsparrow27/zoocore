pipeline {
  agent {
    docker {
      image 'mottosso/maya'
    }

  }
  stages {
    stage('test') {
      parallel {
        stage('test') {
          steps {
            echo 'printenv'
          }
        }

        stage('error') {
          steps {
            sh 'mayapy '
          }
        }

      }
    }

  }
}