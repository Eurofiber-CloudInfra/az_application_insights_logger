targetScope = 'resourceGroup'

param ai_name string
param law_id string = ''
param law_name string = uniqueString(resourceGroup().name)
param law_sku string = 'PerGB2018'
param location string = resourceGroup().location
param tags object = {}

@minValue(30)
@maxValue(730)
param retention_in_days int = 30
param cap_daily_quota_gb int = 0

param ft_disable_local_auth bool = true
param ft_forced_purge_past30d bool = true
param ft_enable_log_access_using_only_resource_permissions bool = false
param ft_enable_data_export bool = false

param netacl_public_ingestion bool = true
param netacl_public_query bool = true

resource law 'Microsoft.OperationalInsights/workspaces@2021-06-01' = if(empty(law_id)){
  name: law_name
  location: location
  tags: tags
  properties: {
    sku: {
      name: law_sku
    }
    retentionInDays: retention_in_days
    features: {
      immediatePurgeDataOn30Days: ft_forced_purge_past30d
      disableLocalAuth: ft_disable_local_auth
      enableLogAccessUsingOnlyResourcePermissions: ft_enable_log_access_using_only_resource_permissions
      enableDataExport: ft_enable_data_export
    }
    workspaceCapping: {
      dailyQuotaGb: (cap_daily_quota_gb == 0) ? null : cap_daily_quota_gb
    }
    publicNetworkAccessForIngestion: netacl_public_ingestion ? 'Enabled' : 'Disabled'
    publicNetworkAccessForQuery: netacl_public_query ? 'Enabled' : 'Disabled'
  }
}

var law_instance_id = empty(law_id) ? law.id : law_id

resource ai_web_instance 'Microsoft.Insights/components@2020-02-02' = {
  name: ai_name
  tags: tags
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    publicNetworkAccessForIngestion: netacl_public_ingestion ? 'Enabled' : 'Disabled'
    publicNetworkAccessForQuery: netacl_public_query ? 'Enabled' : 'Disabled'
    IngestionMode: 'LogAnalytics'
    WorkspaceResourceId: law_instance_id
    RetentionInDays: retention_in_days
    Request_Source: 'rest'
  }
}

output ai_id string = ai_web_instance.id
output ai_cs string = ai_web_instance.properties.ConnectionString
