---
id: core_to_cloud
sidebar_label: 'GX Core to GX Cloud Migration Guide'
title: "GX Core to GX Cloud Migration Guide"
---

## Overview

This guide will enable you to migrate your GX Core configuration to a GX Cloud organization. Since GX Cloud is built on top of GX Core, the code you used to originally set up your GX Core configuration can be reused for setting up your GX Cloud organization. 

The key difference between using GX Core and GX Cloud is the Data Context. By setting the mode of your Data Context to Cloud and then providing the appropriate credentials, you will be able to connect to your GX Cloud organization. Once you have created a Cloud Data Context, the rest of the code you have already written to configure your GX entities, such as Data Sources, Data Assets, and Expectations, can be re-run to migrate your existing configuration into GX Cloud. Similarly, any code that you have written to run validations, including Custom Actions, can also be reused.

## Examples

### Configuration Setup
In the example below, a File Data Context has been created, along with a Postgres Data Source and Data Asset.

```python
import great_expectations as gx

context = gx.get_context(mode="file")
ds = context.data_sources.add_sql(name="Postgres DB", connection_string="postgresql+psycopg2://username:passowrd@myhost.domain>:443>/sample_db")
asset = ds.add_table_asset(table_name="sample_table", name="sample_table")

bd = asset.add_batch_definition_whole_table(
    name="FULL_TABLE"
)

suite = context.suites.get("my_suite")

validation_definition = gx.ValidationDefinition(
    data=bd, suite=suite, name="Validation Definition"
)
context.validation_definitions.add(validation_definition)
```

In order to recreate these same entities in GX Cloud, create a Cloud Data Context by setting the mode to `cloud` and providing your [GX Cloud Credentials](/cloud/connect/connect_python.md#get-your-credentials) for the `GX_CLOUD_ORGANIZATION_ID`, `GX_CLOUD_WORKSPACE_ID` and `GX_CLOUD_ACCESS_TOKEN` environment variables. The rest of the code remains unchanged.

```python
import great_expectations as gx
import os

os.environ["GX_CLOUD_ORGANIZATION_ID"] = "<YOUR_GX_CLOUD_ORGANIZATION_ID>"
os.environ["GX_CLOUD_WORKSPACE_ID"] = "<YOUR_GX_CLOUD_WORKSPACE_ID>"
os.environ["GX_CLOUD_ACCESS_TOKEN"] = "<YOUR_GX_CLOUD_ACCESS_TOKEN>"

context = gx.get_context(mode="cloud")
data_source = context.data_sources.add_sql(name="Postgres DB", connection_string="postgresql+psycopg2://username:passowrd@myhost.domain>:443>/sample_db")
asset = data_source.add_table_asset(table_name="sample_table", name="sample_table")

batch_definition = asset.add_batch_definition_whole_table(
    name="FULL_TABLE"
)

suite = context.suites.get("my_suite")

validation_definition = gx.ValidationDefinition(
    data=batch_definition, suite=suite, name="Validation Definition"
)
context.validation_definitions.add(validation_definition)
```

Running this script will now create the same Data Source, Data Asset, Batch Definition, and Validation Definition in your GX Cloud organization.

### Running Validations

The code snippet below runs a Checkpoint in an existing GX Core configuration.

```python
import great_expectations as gx

context = gx.get_context("file")
checkpoint = context.checkpoints.get("My Checkpoint")
checkpoint.run()
```

In order to execute a checkpoint within your GX Cloud organization, the same code snippet can be used. In the same way as the previous example, set the mode of your data context to `cloud` and provide your [GX Cloud Credentials](/cloud/connect/connect_python.md#get-your-credentials) for the `GX_CLOUD_ORGANIZATION_ID`, `GX_CLOUD_WORKSPACE_ID` and `GX_CLOUD_ACCESS_TOKEN` environment variables.

```python
import great_expectations as gx
import os

os.environ["GX_CLOUD_ORGANIZATION_ID"] = "<YOUR_GX_CLOUD_ORGANIZATION_ID>"
os.environ["GX_CLOUD_WORKSPACE_ID"] = "<YOUR_GX_CLOUD_WORKSPACE_ID>"
os.environ["GX_CLOUD_ACCESS_TOKEN"] = "<YOUR_GX_CLOUD_ACCESS_TOKEN>"

context = gx.get_context(mode="cloud")
checkpoint = context.checkpoints.get("My Checkpoint")
checkpoint.run()
```

Your GX Cloud checkpoint can now be used to run validations wherever needed, such as within your data pipelines.

## Limitations
Any Custom Expectations that you may have created are not compatible with GX Cloud. 