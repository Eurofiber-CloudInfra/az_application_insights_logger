targetScope = 'resourceGroup'

param teams_webhook_url string
param alert_rule_name string
@allowed([
  'Verbose'
  'Informational'
  'Warning'
  'Error'
  'Critical'
])
param alert_rule_severity string
param appinsights_name string

param logic_app_name string = '${alert_rule_name}-teams-notifier'
param alert_rule_description string = ''
param action_group_name string = '${alert_rule_name}-group-teams-notifier'
@maxLength(12)
param action_group_short_name string = substring(action_group_name, 0, 12)
param action_name string = 'push-2-${logic_app_name}'
param appinsights_rg_name string = resourceGroup().name
param appinsights_sub string = subscription().subscriptionId
param alert_rule_eval_frequency string = 'PT5M'
param alert_rule_window_size string = 'PT5M'
param location string = resourceGroup().location
param tags object = {}


var severity_map = {
  Verbose: 4
  Informational: 3
  Warning: 2
  Error: 1
  Critical: 0
}
var logic_app_code_base = loadTextContent('../assets/logic_app_teams_notifier.json')
var logic_app_teams_notifier_code = replace(logic_app_code_base, '\${TEAMS_WEBHOOK_URL}', teams_webhook_url)
var logic_app_teams_notifier_definition = json(logic_app_teams_notifier_code)

// deploy the logic app for teams notifications
resource logic_app_instance 'Microsoft.Logic/workflows@2019-05-01' = {
  name: logic_app_name
  location: location
  tags: tags
  properties: {
    state: 'Enabled'
    parameters: {}
    definition: logic_app_teams_notifier_definition
  }
}

resource logic_app_trigger 'Microsoft.Logic/workflows/triggers@2019-05-01' existing = {
  name: 'manual'
  parent: logic_app_instance
}

// deploy the alert group integrating the call to the logic app
resource action_group_instance 'Microsoft.Insights/actionGroups@2022-06-01' = {
  name: action_group_name
  location: 'Global'
  tags: tags
  properties: {
    enabled: true
    groupShortName: action_group_short_name
    logicAppReceivers: [
      {
        name: action_name
        useCommonAlertSchema: true
        resourceId: logic_app_instance.id
        callbackUrl: logic_app_trigger.listCallbackUrl().value
      }
    ]
  }
}

// deploy the alert integrating the alert group
var alert_query_base = loadTextContent('../assets/alert_query.kusto')
var alert_dimensions = loadJsonContent('../assets/alert_dimensions.json')

resource ai_instance 'Microsoft.Insights/components@2020-02-02' existing = {
  scope: resourceGroup(appinsights_sub, appinsights_rg_name)
  name: appinsights_name
}

resource alert_rule_instance 'Microsoft.Insights/scheduledQueryRules@2022-06-15' = {
  name: alert_rule_name
  location: location
  properties: {
    displayName: alert_rule_name
    description: alert_rule_description
    severity: severity_map[alert_rule_severity]
    evaluationFrequency: alert_rule_eval_frequency
    scopes: [
      ai_instance.id
    ]
    targetResourceTypes: [
      'Microsoft.Insights/components'
    ]
    windowSize: alert_rule_window_size
    criteria: {
      allOf: [
        {
          query: alert_query_base
          timeAggregation: 'Count'
          dimensions: alert_dimensions
          operator: 'GreaterThanOrEqual'
          threshold: 1
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    autoMitigate: true
    actions: {
      actionGroups: [
        action_group_instance.id
      ]
    }
  }
}
