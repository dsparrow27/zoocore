pipeline {
  agent {
    docker {
      image 'mottosso/maya:2019'
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
            sh 'mayapy $WORKSPACE/mayapytest.py'
          }
        }

      }
    }

  }
}
