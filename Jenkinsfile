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
            sh 'mayapy -c "from maya import standalone, cmds;standalone.initialize();"'
          }
        }

      }
    }

  }
}