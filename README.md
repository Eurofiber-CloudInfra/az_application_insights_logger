# Azure Application Insights logger

Push traces and events to Azure Application Insights.

> Note: this is a minimal Python-based implementation, which is intended to be packaged as single binary.

## Configuration

- configuration file (YAML-based) is used for Python logging framework config and message envelope overrides.
- cli arguments are used for partial message envelop overrides

> Example config file
```
message_envelope:
  tags:
    "ai.cloud.role": "app"
    "ai.cloud.roleInstance": "pipeline1"
    "ai.operation.parentId": "job1234"
    "ai.operation.id": "step123456"
    "ai.operation.name": "step name"
    # "ai.device.id": "bot1"
    # "ai.device.locale": "en_US"
    # "ai.device.type": "logbot"
    # "ai.device.model": "pipeline bot"
    # "ai.device.osVersion": "some other linux"
logging_config:
  version: 1
  formatters:
    simple:
      format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    super_simple:
      format: '%(name)s - %(levelname)s - %(message)s'
  handlers:
    console:
      class: logging.StreamHandler
      level: DEBUG
      formatter: simple
      stream: ext://sys.stdout
    event:
      class: opencensus.ext.azure.log_exporter.AzureEventHandler
      formatter: super_simple
    trace:
      class: opencensus.ext.azure.log_exporter.AzureLogHandler
      formatter: super_simple
  loggers:
    aitracelog:
      level: DEBUG
      handlers: [trace]
      propagate: no
    aieventlog:
      level: DEBUG
      handlers: [event]
      propagate: no
  root:
    handlers: [console]
```

## Usage

```
Usage: appinsights_logger.py [OPTIONS]

Options:
  -c, --config PATH               Configuration file path.  [default:
                                  appinsights_logconfig.yml]
  -a, --app TEXT                  Application Insights Logger instance name.
                                  Needs to coincide within logger config!
                                  [default: aitracelog]
  -l, --level [critical|error|warning|info|debug]
                                  Log Level for submitted message.  [default:
                                  info]
  -m, --message TEXT              Log Message to submit.  [required]
  -t, --tag TEXT                  Custom tag, multiple invocations allowed.
                                  Check dist config for available values.
                                  [format: "key:=value"]
  -p, --property TEXT             Custom dimension property, multiple
                                  invocations allowed. [format: "key:=value"]
  -v                              Verbosity level, increased by multiple use.
  --help                          Show this message and exit.
```

## Single binary packaging

- requirements: ccache, gcc, patchelf

- test first with:
  ```
  nuitka3 appinsights_logger.py --static-libpython=yes --standalone
  ```
  - execute binary within the `dist` folder

- if previous test works, try with:
  ```
  nuitka3 appinsights_logger.py --static-libpython=yes --onefile
  ```

## Azure Application Insights setup

- find source files for Bicep based deployment in `./bicep/deployments`
- find used assets in `./bicep/assets` related to:
  - Alert Rule Kusto query
  - Alert Rule dimensions for log data extraction
  - Logic App code definition

### Deployment details

- Requirements:
  - MS Teams `Incoming Webhook` URL
  - Azure Resource group
  - [Optional] Log Analytics Workspace Resource ID

- Resources to be deployed:
  - [Optional] Log Analytics Workspace with minimal default settings
  - Application Insights based on the Log Analytics Workspace
  - Logic App processing Common Alert Schema and defined dimensions to MS Teams Message
  - Action Group using Logic App adapter for payload submission
  - Alert Rule with Log Search V2 based on Application Insights, using Common Alert Schema and Action Group integration

### Deployment example

> Parameter files need to be written out separately or fill the require parameters via CLI.

- Deployment of Application Insights base
  ```
  az deployment group create -c -g <RG_NAME> -f bicep/deployments/01_appinsights_baseline.bicep -p params/01_appinsights_baseline.params.json
  ```

- Deployment of Teams notification resources
  ```
  az deployment group create -c -g <RG_NAME> -f bicep/deployments/02_appinsights_teams_notifier.bicep -p params/02_appinsights_teams_notifier.params.json
  ```
