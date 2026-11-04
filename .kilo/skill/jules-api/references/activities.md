# Activities

Activities represent events that occur during a session. Use the Activities API to monitor progress, retrieve messages, and access artifacts like code changes.

## List Activities

`GET /v1alpha/sessions/{sessionId}/activities`

Lists all activities for a session.

### Path Parameters

- `parent`: The parent session. Format: `sessions/{session}`. Pattern: `^sessions/[^/]+$`

### Query Parameters

- `pageSize`: Number of activities to return (1-100). Defaults to 50.
- `pageToken`: Page token from a previous ListActivities response.

### Example Request

```bash
curl -H "x-goog-api-key: $JULES_API_KEY" \
"https://jules.googleapis.com/v1alpha/sessions/1234567/activities?pageSize=20"
```

## Get an Activity

`GET /v1alpha/sessions/{sessionId}/activities/{activityId}`

Retrieves a single activity by ID.

### Path Parameters

- `name`: The resource name of the activity. Format: `sessions/{session}/activities/{activity}`. Pattern: `^sessions/[^/]+/activities/[^/]+$`

### Example Request

```bash
curl -H "x-goog-api-key: $JULES_API_KEY" \
https://jules.googleapis.com/v1alpha/sessions/1234567/activities/act2
```

## Activity Types

Activities have different types based on what occurred. Each activity will have exactly one of these event fields populated:

- `planGenerated`: Indicates Jules has created a plan for the task.
- `planApproved`: Indicates a plan was approved (by user or auto-approved).
- `userMessaged`: A message from the user.
- `agentMessaged`: A message from Jules.
- `progressUpdated`: A status update during execution.
- `sessionCompleted`: The session finished successfully.
- `sessionFailed`: The session encountered an error.

## Artifacts

Activities may include artifacts—outputs produced during execution:

- **Code Changes (ChangeSet)**: Code changes produced.
- **Bash Output**: Output from a bash command.
- **Media**: A media file output.
