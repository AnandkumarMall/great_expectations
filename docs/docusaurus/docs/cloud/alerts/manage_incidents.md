---
sidebar_label: 'Manage incidents'
title: 'Manage incidents'
description: Link Expectation failures to new or existing Jira work items to streamline collaboration and provide visibility in resolving data quality problems. 
---

import TabItem from '@theme/TabItem';
import Tabs from '@theme/Tabs';

GX Cloud provides incident management [integrations](/cloud/integrations/integrate_jira.md) to help you triage, prioritize, assign, and track the resolution of data quality problems. When a Validation run fails, you can link Expectation failures to new or existing Jira work items to create incidents in GX Cloud. Linked work items are made accessible at the Data Asset level on the **Incidents** tab and on individual Validation runs on the **Validations** tab  for visibility.

:::note More integrations are coming soon
Integrations for PagerDuty and ServiceNow are coming soon. [Contact us](mailto:sales@greatexpectations.io) to learn more or to request a different integration.
:::

GX Cloud supports a many-to-many relationship between Expectation failures and Jira work items.

- A given Expectation failure can be linked to multiple Jira work items. This is helpful if, for example, multiple teams need to be engaged to resolve a data quality problem.
- A given Jira work item can be linked to multiple Expectation failures. This is helpful if, for example, a single bug is suspected to be the root cause of multiple Expectation failures. 

Here’s an example of how an organization might manage incidents on a Data Asset.

![order_id values not being unique is linked to an engineering work item for resolving duplicates and a marketing work item for updating a forecast presentation. order_date values not being of type "DATE" is linked to an engineering work item for normalizing timestamps and the marketing work item for updating the forecast presentation. usage exceeding allowance is linked to sales work items for investigating overconsumption and preparing upgrade offers.](/img/incidents.png)


Keep the following in mind when working with incidents:

- To enable incident management, your GX Cloud workspace must be [integrated with Jira](/cloud/integrations/integrate_jira.md).
- You must have [Workspace Editor permissions](/cloud/access/manage_access.md#roles-and-permissions) or greater to manage incidents.
- All workspace members can view the **Incidents** tab and follow incident links.
- Closing an incident’s work item in Jira does not automatically [resolve](/cloud/alerts/manage_incidents.md#edit-or-resolve-an-incident) the incident in GX Cloud.

## Create an incident

You can create an incident from the **Incidents** tab or the **Validations** tab. These two locations offer different options as follows:

- On the **Incidents** tab, you can link Jira work items to multiple failed Expectations from the last 5 failed Validation runs.
- On the **Validations** tab, you can link Jira work items to a single failed Expectation from any timeframe.

<Tabs 
   queryString="location"
   defaultValue="incidents"
   values={[
      {value: 'incidents', label: 'Incidents'},
      {value: 'validations', label: 'Validations'}
   ]}
>

<TabItem value="incidents" label="Incidents">
1. In GX Cloud, select the relevant **Workspace** and then click **Data Assets**.
2. In the **Data Assets** list, click the Data Asset name.
3. Click the **Incidents** tab.
4. Click <img src="/img/link_icon.png" alt="link icon" width="20" height="20"/> **Link a Jira work item**.
5. Select one or more **Expectation failures**.
6. Select whether you want to link **Existing work items** or a **New work item**.
7. The next steps depend on the prior selection:
   - If you selected **Existing work items**, search for and select one or more **Work items** to link.
   - If you selected **New work item**, select a **Space** and **Work type**, then enter a **Summary** and **Description**. When GX Cloud creates the work item in Jira, your description will be appended with metadata about the linked Expectation failures, including their timestamps and failure severities.
8. Click **Save**.
</TabItem>

<TabItem value="validations" label="Validations">
1. Navigate to a failed Validation run in one of the following ways:

   - From a [Microsoft Teams, Slack, or email notification](/cloud/alerts/alert_about_failures.md) about Expectation failures, click **View Validation Results** or **View details**.
   - In GX Cloud, do the following:
   
      1. Select the relevant **Workspace** and then click **Data Assets**.
      2. In the **Data Assets** list, click the Data Asset name.
      3. Click the **Validations** tab.
      4. If you have multiple **Expectation Suites**, select the suite of interest.
      5. Select an entry in the **Batches & run history** pane.

2. Find the Expectation failure you want to link and click <img src="/img/link_icon.png" alt="link icon" width="20" height="20"/> **Link a Jira work item**.
3. Select whether you want to link **Existing work items** or a **New work item**.
4. The next steps depend on the prior selection:
   - If you selected **Existing work items**, search for and select one or more **Work items** to link.
   - If you selected **New work item**, select a **Space** and **Work type**, then enter a **Summary** and **Description**. When GX Cloud creates the work item in Jira, your description will be appended with metadata about the linked Expectation failure, including its timestamp and failure severity.
5. Click **Save**.
</TabItem>

</Tabs>


## Edit or resolve an incident

As data quality problems are addressed, you can unlink Expectation failures and Jira work items to resolve incidents. You can unlink a single Expectation failure or all Expectation failures that were linked to a Jira work item. 

<Tabs 
   queryString="scope"
   defaultValue="single"
   values={[
      {value: 'single', label: 'Single'},
      {value: 'all', label: 'All'}
   ]}
>

<TabItem value="single" label="Single">
1. Select the relevant **Workspace** and then click **Data Assets**.
2. In the **Data Assets** list, click the Data Asset name.
3. Click the **Validations** tab.
4. If you have multiple **Expectation Suites**, select the suite of interest.
5. Select the relevant entry in the **Batches & run history** pane.
6. Find the Expectation failure you want to unlink and click the <img src="/img/jira_logo.png" alt="jira logo" width="20" height="20"/> **Jira** icon.
7. Find the work item you want to unlink and click <img src="/img/unlink_icon.png" alt="unlink icon" width="20" height="20"/>  **Unlink work item**.
8. Review the warning and click **Unlink** to confirm.

If the work item was linked to multiple Expectation failures, it will remain on the **Incidents** tab to track those remaining links. If the work item was linked to only the one Expectation failure, the work item will be removed from the **Incidents** tab as fully resolved.
</TabItem>

<TabItem value="all" label="All">
1. In GX Cloud, select the relevant **Workspace** and then click **Data Assets**.
2. In the **Data Assets** list, click the Data Asset name.
3. Click the **Incidents** tab.
4. Find the work item you want to unlink and click <img src="/img/unlink_icon.png" alt="unlink icon" width="20" height="20"/> **Unlink work item**.
5. Review the warning and click **Unlink** to confirm.

The work item will be removed from the **Incidents** tab as fully resolved.
</TabItem>

</Tabs>