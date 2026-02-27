YAML files make variables more visible, are easier to edit, and allow for modularization. For example, you can create a YAML file for development and testing and another for production.

A File Data Context is required before you can configure credentials in a YAML file.  By default, the credentials file in a File Data Context is located at `/great_expectations/uncommitted/config_variables.yml`.  The `uncommitted/` directory is included in a default `.gitignore` and will be excluded from version control.

Save your access credentials or the database connection string to ``great_expectations/uncommitted/config_variables.yml``. For example:

```bash title="config_variables.yml"
MY_POSTGRES_USERNAME: <USERNAME>
MY_POSTGRES_PASSWORD: <PASSWORD>
```

or:

```bash title="config_variables.yml"
POSTGRES_CONNECTION_STRING: postgresql+psycopg2://<USERNAME>:<PASSWORD>@<HOST>:<PORT>/<DATABASE>
```

You can also reference your stored credentials within a stored connection string by wrapping their corresponding variable in `${` and `}`. For example:

```bash title="config_variables.yml"
MY_POSTGRES_USERNAME: <USERNAME>
MY_POSTGRES_PASSWORD: <PASSWORD>
POSTGRES_CONNECTION_STRING: postgresql+psycopg2://${MY_POSTGRES_USERNAME}:${MY_POSTGRES_PASSWORD}@<HOST>:<PORT>/<DATABASE>
```

Because the `${` sequence is used to indicate the start of a config variable substitution (e.g. `${MY_PASSWORD}`), it should be escaped using a backslash `\` if it appears literally in your credentials. For example, if your password is `pa${word}` then in the previous examples you would use the command:

```bash title="Terminal"
export MY_POSTGRES_PASSWORD=pa\${word}
```

Note: a bare `$` that is not followed by `{` does not need to be escaped. For example, a password like `pa$word` can be used as-is.
