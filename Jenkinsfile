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
            sh '''printenv
ls
pwd'''
          }
        }

        stage('error') {
          steps {
            sh '''cd $WORKSPACE
sh /usr/autodesk/maya//bin/mayapy "$WORKSPACE/mayapytest.py"'''
          }
        }

      }
    }

  }
}