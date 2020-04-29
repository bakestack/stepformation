resourcePrefix=""
parameters="ResourcePrefix=${resourcePrefix}"
stackName="stepformation"
aws cloudformation deploy --stack-name ${stackName} --template-file init.yml --parameter-overrides ${parameters} --capabilities CAPABILITY_NAMED_IAM