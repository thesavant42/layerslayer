# Add PAT authentication support to be neighborly and follow rate limits

## Rate Limiting
The Docker Hub API is limited on the amount of requests you can perform per minute against it.

If you haven't hit the limit, each request to the API will return the following headers in the response.

```
X-RateLimit-Limit - The limit of requests per minute.
X-RateLimit-Remaining - The remaining amount of calls within the limit period.
X-RateLimit-Reset - The unix timestamp of when the remaining resets.
```

If you *have* hit the limit, you will receive a response status of `429` and the `Retry-After` header in the response.

The `Retry-After` header specifies the number of seconds to wait until you can call the API again.

**Note**: These rate limits are separate from anti-abuse and Docker Hub download, or pull rate limiting. To learn more about Docker Hub pull rate limiting, see Usage and limits.

### Limits
Personal (authenticated)	200

### Pulls
Personal (authenticated)	200
Unauthenticated Users	100 per IPv4 address or IPv6 /64 subnet

## Task: Implement DockerHub PAT authentication
- [Docker Hub yml api doc](/docs/dhub-latest.yaml)
- [auth.py](/app/modules/auth/auth.py)
