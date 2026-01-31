//
//  APIClient.swift
//  APITestMachine
//
//  HTTP client for API communication (async/await)
//

import Foundation

actor APIClient {
    static let shared = APIClient()

    // Default to localhost for development (includes /api/v1 prefix)
    private static let defaultBaseURL = URL(string: "http://localhost:8000/api/v1")!

    private var baseURL: URL
    private var apiKey: String

    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    init() {
        self.baseURL = Self.defaultBaseURL
        self.apiKey = ""
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: config)

        self.decoder = JSONDecoder()
        self.decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let dateString = try container.decode(String.self)

            // Try ISO8601 with fractional seconds
            let formatter = ISO8601DateFormatter()
            formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = formatter.date(from: dateString) {
                return date
            }

            // Try ISO8601 without fractional seconds
            formatter.formatOptions = [.withInternetDateTime]
            if let date = formatter.date(from: dateString) {
                return date
            }

            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Cannot decode date: \(dateString)"
            )
        }

        self.encoder = JSONEncoder()
        self.encoder.dateEncodingStrategy = .iso8601
    }

    func configure(baseURL: URL, apiKey: String) {
        self.baseURL = baseURL
        self.apiKey = apiKey
    }

    func updateBaseURL(_ url: URL) {
        self.baseURL = url
    }

    func updateAPIKey(_ key: String) {
        self.apiKey = key
    }

    // MARK: - Health

    func checkHealth() async throws -> HealthResponse {
        return try await get(path: "/health")
    }

    // MARK: - Runs

    func listRuns(status: RunStatus? = nil, limit: Int = 50, offset: Int = 0) async throws -> RunListResponse {
        var queryItems: [URLQueryItem] = [
            URLQueryItem(name: "limit", value: String(limit)),
            URLQueryItem(name: "offset", value: String(offset))
        ]
        if let status = status {
            queryItems.append(URLQueryItem(name: "status", value: status.rawValue))
        }
        return try await get(path: "/runs", queryItems: queryItems)
    }

    func getRun(id: UUID) async throws -> RunDetail {
        return try await get(path: "/runs/\(id.uuidString)")
    }

    func createRun(spec: TestSpec) async throws -> CreateRunResponse {
        let request = CreateRunRequest(spec: spec)
        return try await post(path: "/runs", body: request)
    }

    func cancelRun(id: UUID) async throws -> CancelRunResponse {
        return try await post(path: "/runs/\(id.uuidString)/cancel", body: EmptyBody())
    }

    func deleteRun(id: UUID) async throws -> DeleteRunResponse {
        return try await delete(path: "/runs/\(id.uuidString)")
    }

    func getRequestDetail(runId: UUID, requestNumber: Int) async throws -> RequestDetail {
        return try await get(path: "/runs/\(runId.uuidString)/requests/\(requestNumber)")
    }

    // MARK: - Schedules

    func listSchedules() async throws -> ScheduleListResponse {
        return try await get(path: "/schedules")
    }

    func getSchedule(id: UUID) async throws -> ScheduleResponse {
        return try await get(path: "/schedules/\(id.uuidString)")
    }

    func createSchedule(request: CreateScheduleRequest) async throws -> ScheduleResponse {
        return try await post(path: "/schedules", body: request)
    }

    func deleteSchedule(id: UUID) async throws -> ScheduleActionResponse {
        return try await delete(path: "/schedules/\(id.uuidString)")
    }

    func pauseSchedule(id: UUID) async throws -> ScheduleActionResponse {
        return try await post(path: "/schedules/\(id.uuidString)/pause", body: EmptyBody())
    }

    func resumeSchedule(id: UUID) async throws -> ScheduleActionResponse {
        return try await post(path: "/schedules/\(id.uuidString)/resume", body: EmptyBody())
    }

    // MARK: - Test Configs

    func listTestConfigs(enabledOnly: Bool = false) async throws -> TestConfigListResponse {
        var queryItems: [URLQueryItem] = []
        if enabledOnly {
            queryItems.append(URLQueryItem(name: "enabled_only", value: "true"))
        }
        return try await get(path: "/tests", queryItems: queryItems)
    }

    func runAllEnabledTests(repetitions: Int = 1, maxConcurrency: Int = 0) async throws -> BatchStartResponse {
        let request = RunAllRequest(repetitions: repetitions, maxConcurrency: maxConcurrency)
        return try await post(path: "/tests/run-all", body: request)
    }

    // MARK: - Private HTTP Methods

    private func get<T: Decodable & Sendable>(path: String, queryItems: [URLQueryItem] = []) async throws -> T {
        let request = try buildRequest(path: path, method: "GET", queryItems: queryItems)
        return try await execute(request)
    }

    private func post<T: Decodable & Sendable, B: Encodable & Sendable>(path: String, body: B, queryItems: [URLQueryItem] = []) async throws -> T {
        var request = try buildRequest(path: path, method: "POST", queryItems: queryItems)
        request.httpBody = try encoder.encode(body)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        return try await execute(request)
    }

    private func delete<T: Decodable & Sendable>(path: String, queryItems: [URLQueryItem] = []) async throws -> T {
        let request = try buildRequest(path: path, method: "DELETE", queryItems: queryItems)
        return try await execute(request)
    }

    private func buildRequest(path: String, method: String, queryItems: [URLQueryItem] = []) throws -> URLRequest {
        var components = URLComponents(url: baseURL.appendingPathComponent(path), resolvingAgainstBaseURL: true)
        if !queryItems.isEmpty {
            components?.queryItems = queryItems
        }

        guard let url = components?.url else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method

        // Add API key if available (not required for health check)
        if !apiKey.isEmpty && !path.contains("/health") {
            request.setValue(apiKey, forHTTPHeaderField: "X-API-Key")
        }

        return request
    }

    private func execute<T: Decodable & Sendable>(_ request: URLRequest) async throws -> T {
        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        switch httpResponse.statusCode {
        case 200..<300:
            do {
                return try decoder.decode(T.self, from: data)
            } catch {
                throw APIError.decodingError(error)
            }
        case 401:
            throw APIError.unauthorized
        case 404:
            throw APIError.notFound
        default:
            let errorResponse = try? decoder.decode(ErrorResponse.self, from: data)
            throw APIError.httpError(statusCode: httpResponse.statusCode, message: errorResponse?.detail ?? errorResponse?.error)
        }
    }
}

// Helper for empty request bodies
private struct EmptyBody: Encodable, Sendable {}

// Additional response types
struct TestConfigResponse: Codable, Identifiable, Sendable {
    var id: String { name }
    let name: String
    let enabled: Bool
    let spec: TestSpec
    let createdAt: Date?
    let updatedAt: Date?
    let runCount: Int

    enum CodingKeys: String, CodingKey {
        case name, enabled, spec
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case runCount = "run_count"
    }
}

struct TestConfigListResponse: Codable, Sendable {
    let configs: [TestConfigResponse]
    let total: Int
}

struct RunAllRequest: Codable, Sendable {
    let repetitions: Int
    let maxConcurrency: Int

    enum CodingKeys: String, CodingKey {
        case repetitions
        case maxConcurrency = "max_concurrency"
    }
}

struct BatchStartResponse: Codable, Sendable {
    let batchId: String
    let totalTests: Int
    let runIds: [UUID]
    let message: String

    enum CodingKeys: String, CodingKey {
        case batchId = "batch_id"
        case totalTests = "total_tests"
        case runIds = "run_ids"
        case message
    }
}
