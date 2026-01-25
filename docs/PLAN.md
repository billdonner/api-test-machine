# API Test Machine - Development Plan

## Current Status

**Version:** 0.1.0

### Completed Features

- [x] Core async test engine with httpx
- [x] Rate limiting (token bucket algorithm)
- [x] Template variable substitution
- [x] Pass/fail thresholds
- [x] FastAPI Control API
- [x] Typer CLI
- [x] SvelteKit Web Dashboard
- [x] MCP Server for LLM agents
- [x] Agent scheduler
- [x] Authentication support (Bearer, API Key, Basic)
- [x] **Multi-endpoint testing** (NEW)
  - Round-robin, weighted, and sequential distribution
  - Per-endpoint metrics
  - UI support in webapp

### In Progress

- [ ] Persistent storage (currently in-memory only)
- [ ] WebSocket real-time updates

## Roadmap

### Phase 1: Core Stability (Current)

Focus on reliability and usability of existing features.

**Tasks:**
- [ ] Add database persistence (SQLite/PostgreSQL)
- [ ] Improve error handling and reporting
- [ ] Add request/response assertion capabilities
- [ ] Expand test coverage to 90%+

### Phase 2: Enhanced Testing

Advanced testing capabilities.

**Tasks:**
- [ ] Custom scripting support (pre/post request hooks)
- [ ] Response validation (JSON schema, regex)
- [ ] Data-driven testing (CSV/JSON data sources)
- [ ] Scenario-based testing (chained requests)
- [ ] gRPC support

### Phase 3: Scale & Distribution

Distributed testing for higher loads.

**Tasks:**
- [ ] Worker pool architecture
- [ ] Distributed execution across nodes
- [ ] Results aggregation from multiple workers
- [ ] Cloud deployment templates (AWS, GCP, Azure)

### Phase 4: Observability

Better insights and integration.

**Tasks:**
- [ ] Prometheus metrics export
- [ ] OpenTelemetry tracing
- [ ] Grafana dashboard templates
- [ ] Slack/PagerDuty alerting
- [ ] CI/CD integration (GitHub Actions, GitLab CI)

### Phase 5: Enterprise Features

Production-ready capabilities.

**Tasks:**
- [ ] User authentication and authorization
- [ ] Team workspaces
- [ ] Test history and trending
- [ ] Scheduled test reports (email, Slack)
- [ ] API versioning

## Technical Debt

- [ ] Fix datetime deprecation warnings (use timezone-aware)
- [ ] Resolve TypeScript errors in webapp charts
- [ ] Add proper form label associations (a11y)
- [ ] Improve error messages for invalid specs

## Design Decisions Log

### 2025-01-25: Multi-Endpoint Feature

**Decision:** Add optional `endpoints` array to TestSpec rather than creating a separate MultiEndpointTestSpec.

**Rationale:**
- Maintains backward compatibility
- Single code path with conditional handling
- Simpler API surface

**Trade-offs:**
- TestSpec model is more complex
- Validation logic needs to handle both modes

### Previous Decisions

**Async-first architecture:** All I/O uses async/await for scalability.

**Pydantic v2:** Chosen for performance and better validation.

**In-memory storage (initial):** Simplifies development; persistence to be added later.

## Contributing

See the main README for development setup. Key areas needing contribution:

1. **Testing:** More integration tests, especially for multi-endpoint scenarios
2. **Documentation:** API documentation, more examples
3. **Performance:** Profiling and optimization
4. **Features:** Pick items from the roadmap above
