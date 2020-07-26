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
            sh 'printenv'
          }
        }

        stage('error') {
          steps {
            sh 'sh mayapy $WORKSPACE/mayapytest.py'
          }
        }

      }
    }

  }
}