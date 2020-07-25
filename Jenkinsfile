pipeline {
  agent {
    docker {
      image 'mottosso/maya'
    }

  }
  stages {
    stage('test') {
      steps {
        echo 'print("testing jenkins maya")'
      }
    }

  }
}