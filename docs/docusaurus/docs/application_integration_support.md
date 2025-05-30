---
title: Integration support policy
---

For production environments, GX recommends using GX Cloud integrations.

GX uses libraries such as Pandas, Spark, and SQLAlchemy to integrate with different Data Sources. This also allows you to deploy GX with community-supported integrations.

## Levels of support

The following are the levels of support provided by GX:

- <b>GX Cloud - guided support</b> - these integrations are available for configuration in the GX Cloud UI. They are generally compatible with features available in the Cloud UI. They may abstract away some customization options for the sake of simplicity. They are tested and are actively maintained with new GX Cloud releases. See the guided vs. programmatic support tables below for details on cross-feature compatibility.

- <b>GX Cloud - programmatic support</b> - these integrations are available for configuration in the GX Cloud API. They may offer extra customization options for flexibility. They may not work with Cloud UI features that prioritize simplicity. They are tested and are actively maintained with new GX Cloud releases. See the guided vs. programmatic support tables below for details on cross-feature compatibility. See the guided vs. programmatic support tables below for details on cross-feature compatibility.

- <b>GX Core</b> - GX Core supported integrations are available in GX Core. They are tested and are actively maintained with new GX Core releases.

- <b>Community</b> - Community supported integrations may be available in the GX Cloud API or in GX Core. These were initially implemented by GX or the community. It is up to the community for ongoing maintenance.

## Data Sources

Support for integrating with Data Sources is as follows

| Data Source | GX Cloud - guided support | GX Cloud - programmatic support | Core support | Community support |
|---|---|---|---|---|
| BigQuery |  | ✅ | ✅ |  |
| Databricks (SQL) | ✅ | ✅ | ✅ |  |
| Pandas |  | ✅ | ✅ |  |
| PostgreSQL | ✅ | ✅ | ✅ |  |
| Redshift | ✅ | ✅ | ✅ |  |
| Snowflake | ✅ | ✅ | ✅ |  |
| Spark |  | ✅ | ✅ |  |
| SQLite |  | ✅ | ✅ |  |
| MSSQL |  |  |  | ✅ |
| MySQL |  |  |  | ✅ |

Cross-feature compatiblility for Cloud-supported Data Sources is as follows


| Related feature | Source added through guided support | Source added through programmatic support |
|---|---|---|
| Add Data Asset through UI | Yes | Yes |
| Schedule recurring validations | Yes | No, use an orchestrator |

### GX components

The following table defines the GX components supported by GX Cloud and GX Core.

| Component    | GX Cloud                                                                                        | GX Core                                                               | Community                                                                  |
| ------------ | ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Expectations | See [Available Expectations](/cloud/expectations/manage_expectations.md#available-expectations) | See [Expectations Gallery](https://greatexpectations.io/expectations) | See [Legacy Gallery](https://greatexpectations.io/legacy/v1/expectations/) |
| GX Agent     | All versions                                                                                    | N/A                                                                   | N/A                                                                        |

### Operating systems

The following table defines the operating systems supported by GX Cloud and GX Core.

| GX Cloud               | GX Core   | Community |
| ---------------------- | --------- | --------- |
| Mac/Linux <sup>1</sup> | Mac/Linux | Mac/Linux |

<sup>1</sup> GX does not currently support Windows. However, we've seen users successfully deploying GX on Windows.

### Python versions

The following table defines the Python versions supported by GX Cloud and GX Core. GX typically follows the [Python release cycle](https://devguide.python.org/versions/).

| GX Cloud    | GX Core     | Community   |
| ----------- | ----------- | ----------- |
| 3.9 to 3.12 | 3.9 to 3.12 | 3.9 to 3.12 |

### GX versions

The following table defines the GX versions supported by GX Cloud and GX Core.

| GX Cloud | GX Core | Community |
| -------- | ------- | --------- |
| ≥1.0     | ≥1.0    | ≥1.0      |

### Web browsers

The following web browsers are supported by GX Cloud.

- [Google Chrome](https://www.google.com/chrome/) — the latest version is fully supported

- [Mozilla Firefox](https://www.mozilla.org/en-US/firefox/) — the latest version is fully supported

- [Apple Safari](https://www.apple.com/safari/) — the latest version is fully supported

- [Microsoft Edge](https://www.microsoft.com/en-us/edge?ep=82&form=MA13KI&es=24) — the latest version is fully supported
