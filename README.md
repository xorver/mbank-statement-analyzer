# mbank-statement-analyzer
Scrap transactions from mBank account basing on statement emails, process the transactions.

## Debugging locally with PyCharm

Follow [this](https://github.com/joelgerard/functions-framework-python/blob/pycharm/PYCHARM.md) guide, updating the module name as mentioned in [here](https://github.com/GoogleCloudPlatform/functions-framework-python/issues/32#issuecomment-650399687)

## Python env 

### Select venv

```bash
source venv/bin/activate
```

### Generate requirements.txt

```bash
pip freeze > requirements.txt
```



## Gcloud Configuration

Follow https://developers.google.com/workspace/add-ons/alternate-runtimes-quickstart

### Creat Secret with passwords

On the https://console.cloud.google.com/security/secret-manager create a secret with a map of gmail address to PESEL

Example:
```json
{
  "asdf@gmail.com": "85033395735",
  "ghij@gmail.com": "67050512753"
}
```

```bash
gcloud functions deploy displayTax --runtime python38 --trigger-http --set-secrets=/etc/secrets/email-to-pesel.json=email-to-pesel:latest
```

### Create Cloud Functions

```bash
gcloud functions deploy loadHomePage --runtime python38 --trigger-http
gcloud functions call loadHomePage
gcloud functions deploy displayTax --runtime python38 --trigger-http --set-secrets=/email-to-pesel=email-to-pesel:latest
gcloud functions call displayTax
```

### Create workspace add-on

```bash
gcloud workspace-add-ons get-authorization
gcloud functions add-iam-policy-binding loadHomePage --role roles/cloudfunctions.invoker --member serviceAccount:SERVICE_ACCOUNT_EMAIL
gcloud functions add-iam-policy-binding displayTax --role roles/cloudfunctions.invoker --member serviceAccount:SERVICE_ACCOUNT_EMAIL
gcloud workspace-add-ons deployments create quickstart --deployment-file=deployment.json
gcloud workspace-add-ons deployments install quickstart
```
