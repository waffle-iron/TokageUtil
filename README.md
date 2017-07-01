# TokageUtil
TokageCam 肥大化に伴いmodule分離

## Integrate
Linux/bash
```
$ export PYTHONPATH=$PYTHONPATH:/path_to/TokageUtil
# run some calee code
$ ~/TokageCam/scripts/kickTokageCam.sh 5m
```
or
```
# e.g., raspbian
$ sudo sh -c "echo '/path_to/TokageUtil' >> YOUR_PYTHON_ENV/python3/dist-packages/custom.pth"
# run some calee code
$ ~/TokageCam/scripts/kickTokageCam.sh 5m
```