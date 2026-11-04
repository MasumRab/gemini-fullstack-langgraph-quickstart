# Sources

Sources represent repositories connected to Jules. Currently, Jules supports GitHub repositories. Use the Sources API to list available repositories and get details about specific sources.

Sources are created when you connect a GitHub repository to Jules through the web interface. The API currently only supports reading sources, not creating them.

## List Sources

`GET /v1alpha/sources`

Lists all sources (repositories) connected to your account.

### Query Parameters

- `pageSize`: Number of sources to return (1-100). Defaults to 30.
- `pageToken`: Page token from a previous ListSources response.
- `filter`: Filter expression based on AIP-160. Example: `'name=sources/source1 OR name=sources/source2'`

### Example Request

```bash
curl -H "x-goog-api-key: $JULES_API_KEY" \
https://jules.googleapis.com/v1alpha/sources
```

## Get a Source

`GET /v1alpha/sources/{sourceId}`

Retrieves a single source by ID.

### Path Parameters

- `name`: The resource name of the source. Format: `sources/{source}`. Pattern: `^sources/.*$`

### Example Request

```bash
curl -H "x-goog-api-key: $JULES_API_KEY" \
https://jules.googleapis.com/v1alpha/sources/sourceId
```

## Using Sources with Sessions

When creating a session, reference a source using its resource name in the `sourceContext`:

```json
{
  "sourceContext": {
    "source": "sources/github/owner/repo"
  }
}
```
