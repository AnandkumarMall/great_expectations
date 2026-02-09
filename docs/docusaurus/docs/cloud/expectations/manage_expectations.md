---
sidebar_label: "Manage Expectations"
title: "Manage Expectations"
description: Create and manage Expectations in GX Cloud.
---

You can manually create Expectations and use several different GX Cloud features to generate Expectations.

This page provides instructions for working with Expectations. To learn about Expectation types and options, see the [Expectations overview](/cloud/expectations/expectations_overview.md). To learn about the Expectation changelog at the Data Asset level, visit [Manage Data Assets](/cloud/data_assets/manage_data_assets.md#view-data-asset-history).

## Prerequisites

- You have a [Data Asset](/cloud/data_assets/manage_data_assets.md).



## Add an Expectation

1. In GX Cloud, select the relevant **Workspace** and then click **Data Assets**.

2. In the **Data Assets** list, click the Data Asset name.

3. Click **New Expectation**.

4. Select a data quality issue to test for or an option for writing your own test.

   :::tip Tip
   This is a tip.
   :::

   :::note Note
   this is a note
   :::

   :::warning Warning
   this is a warning
   :::

   :::danger Danger
   this is a danger, though we don't really use this one
   :::

5. Select an Expectation type.

6. Complete the mandatory and optional fields for the Expectation.

   <details>
   <summary>Restrict an Expectation to specific rows</summary>

   To restrict an Expectation to a subset of the data retrieved in a Batch, use the `row_condition` argument. The `row_condition` argument takes a boolean expression built with Python objects. Rows will be validated for the Expectation when the `row_condition` expression evaluates to True. Conversely, if the `row_condition` evaluates to False, the corresponding row will not be validated for the Expectation.


   To support complex business use cases, logical clauses can be combined with AND / OR relationships within the `row_condition` argument.

   ```python title="Python" name="docs/docusaurus/docs/core/customize_expectations/_examples/row_conditions.py - determine expression"
   ```

   Here are some examples of how to create common patterns in row conditions:

   - **A and B**.
      ```python title="Python" name="docs/docusaurus/docs/core/customize_expectations/_examples/row_conditions.py - a and b"
      ```

   - **A or B**.
      ```python title="Python" name="docs/docusaurus/docs/core/customize_expectations/_examples/row_conditions.py - a or b"
      ```

   - **(A and B) or (C and D)**.
      ```python title="Python" name="docs/docusaurus/docs/core/customize_expectations/_examples/row_conditions.py - a and b or c and d"
      ```

   - **A and (B or C)**. This pattern is not supported verbatim, but you can achieve the same result with **(A and B) or (A and C)**.
      ```python title="Python" name="docs/docusaurus/docs/core/customize_expectations/_examples/row_conditions.py - a and b or c"
      ```

   The following comparison operators are supported: `==`, `!=`, `>`, `<`, `>=`, `<=`, `is_in`, `is_not_in`, `is_null`, `is_not_null`. Here are some examples of using different kinds of operators:

   ```python title="Python" name="docs/docusaurus/docs/core/customize_expectations/_examples/row_conditions.py - operators"
   ```


   </details>
   

7. Click **Save** or click **Save & Add More** and then repeat steps 4 through 7 to add additional Expectations.

8. Optional. [Run an ad hoc Validation](/cloud/validations/run_validations.md).

9. Optional. Configure recurring Validations. See [Manage schedules](/docs/cloud/schedules/manage_schedules).


## Save time with ExpectAI

ExpectAI is an analytical AI tool that you can use to generate tests.

### Generate Expectations

To accelerate test coverage, you can use ExpectAI to generate recommended Expectations for a Data Asset. These will be personalized based on an analysis of a sample of your data.

Keep the following requirements in mind when working with ExpectAI:
- Your organization must be using a [fully-hosted deployment](/cloud/deploy/deployment_patterns.md).
- The Data Asset's Data Source must be AlloyDB, Amazon Aurora PostgreSQL, Citus, Databricks SQL, Neon, PostgreSQL, Redshift, or Snowflake.
- Generated Expectations will default to warning severity, which you can edit later.

To add AI-recommended Expectations:
1. In GX Cloud, select the relevant **Workspace** and then click **Data Assets**.
2. In the **Data Assets** list, click the Data Asset name.
3. Click **Generate Expectations**.
   :::note This might take a few minutes
   ExpectAI may take a few minutes to analyze your data and recommend personalized Expectations. You can navigate away from the page while ExpectAI works in the background. GX will send an [email alert](/cloud/alerts/manage_email_alerts.md) when your recommended Expectations are ready for review.
   :::
4. Review the recommended Expectations and **Approve** (✓) or **Reject** (✗) them within 48 hours. After 48 hours, any remaining recommendations will be discarded.
5. Optional. [Run an ad hoc Validation](/cloud/validations/run_validations.md).
6. Optional. [Edit](#edit-an-expectation) AI-generated Expectations based on the insights you get from running a Validation and your data quality needs.

### Generate SQL

To simplify working with [custom SQL Expectations](/cloud/expectations/expectations_overview.md#custom-sql-expectations), you can use ExpectAI to generate a SQL query based on a natural language prompt you provide and a data profile GX Cloud automatically provides.

For example, imagine you have a New York City taxi trip dataset with columns named `pickup_borough`, `vehicle_type`, and `passenger_count`. If you [add a custom SQL Expectation](#add-an-expectation) with a **Prompt for SQL generation** like `sedan rides in Manhattan shouldn't have more than 4 passengers` then ExpectAI would generate a SQL query similar to the following:

```sql title="SQL query"
SELECT
*
FROM
{batch}
WHERE
pickup_borough = 'Manhattan'
AND vehicle_type = 'Sedan'
AND passenger_count > 4
```

Keep the following requirements in mind when working with ExpectAI:
- Your organization must be using a [fully-hosted deployment](/cloud/deploy/deployment_patterns.md).
- The Data Asset's Data Source must be AlloyDB, Amazon Aurora PostgreSQL, Citus, Databricks SQL, Neon, PostgreSQL, Redshift, or Snowflake.

## Edit an Expectation

1. In GX Cloud, select the relevant **Workspace** and then click **Data Assets**.

2. In the **Data Assets** list, click the Data Asset name.

3. Find the Expectation that you want to edit.

4. Click <img src="/img/pencil.png" alt="pencil icon" width="20" height="20"/> **Edit Expectation** for the Expectation that you want to edit.

5. Edit the Expectation configuration.

6. Click **Save**.

:::note Severity changes apply going forward
If you edit the **Severity** of an Expectation, note that historical validation results will continue to indicate the severity that was recorded at the time of an Expectation failure. The newly assigned severity will apply to future validation failures only. 
:::

## Delete an Expectation

1. In GX Cloud, select the relevant **Workspace** and then click **Data Assets**.

2. In the **Data Assets** list, click the Data Asset name.

3. Find the Expectation that you want to delete.

4. Click <img src="/img/trash.png" alt="trash icon" width="20" height="20"/> **Delete Expectation** for the Expectation that you want to delete.

   :::tip You can delete Expectations in bulk
    If you want to delete all Expectations that test for a certain data quality issue, you can instead click <img src="/img/trash.png" alt="trash icon" width="20" height="20"/> **Bulk-delete Expectations** for the relevant category.
    :::

5. Click **Delete**.


