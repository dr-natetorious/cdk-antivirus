# Anti-virus example with CDK

## How do I build this project

```sh
# Create virtual environment
virtualenv .env
.env/Scripts/activate.ps1
pip install -r images/cdk-deploy/requirements.txt

# Bootstrap CDK
cdk bootstrap aws://$ACCOUNT_ID/$AWS_REGION

# Deploy
cdk deploy -a ./app.py
```
