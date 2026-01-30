//
//  RunResult.swift
//  APITestMachine
//
//  Run summary and detail models
//

import Foundation

enum RunStatus: String, Codable, CaseIterable, Sendable {
    case pending
    case running
    case completed
    case cancelled
    case failed

    var displayName: String {
        rawValue.capitalized
    }

    var isActive: Bool {
        self == .pending || self == .running
    }

    var isComplete: Bool {
        self == .completed || self == .cancelled || self == .failed
    }
}

struct RunSummary: Codable, Identifiable, Equatable, Hashable, Sendable {
    let id: UUID
    let name: String
    let status: RunStatus
    let startedAt: Date?
    let completedAt: Date?
    let totalRequests: Int
    let requestsCompleted: Int
    let passed: Bool?

    enum CodingKeys: String, CodingKey {
        case id, name, status, passed
        case startedAt = "started_at"
        case completedAt = "completed_at"
        case totalRequests = "total_requests"
        case requestsCompleted = "requests_completed"
    }

    var progress: Double {
        guard totalRequests > 0 else { return 0 }
        return Double(requestsCompleted) / Double(totalRequests)
    }

    var statusColor: String {
        switch status {
        case .pending: return "gray"
        case .running: return "blue"
        case .completed:
            if let passed = passed {
                return passed ? "green" : "red"
            }
            return "gray"
        case .cancelled: return "orange"
        case .failed: return "red"
        }
    }
}

struct RequestSummary: Codable, Identifiable, Sendable {
    var id: Int { requestNumber }
    let requestNumber: Int
    let statusCode: Int?
    let latencyMs: Double
    let error: String?
    let timestamp: Date
    let responseSizeBytes: Int?
    let endpointName: String?

    enum CodingKeys: String, CodingKey {
        case requestNumber = "request_number"
        case statusCode = "status_code"
        case latencyMs = "latency_ms"
        case error, timestamp
        case responseSizeBytes = "response_size_bytes"
        case endpointName = "endpoint_name"
    }

    var isSuccess: Bool {
        error == nil && statusCode != nil && (200..<300).contains(statusCode!)
    }
}

struct RequestDetail: Codable, Identifiable, Sendable {
    var id: Int { requestNumber }
    let requestNumber: Int
    let statusCode: Int?
    let latencyMs: Double
    let error: String?
    let timestamp: Date
    let responseSizeBytes: Int?
    let endpointName: String?
    let requestUrl: String?
    let requestMethod: String?
    let requestHeaders: [String: String]?
    let requestBody: String?
    let responseHeaders: [String: String]?
    let responseBody: String?

    enum CodingKeys: String, CodingKey {
        case requestNumber = "request_number"
        case statusCode = "status_code"
        case latencyMs = "latency_ms"
        case error, timestamp
        case responseSizeBytes = "response_size_bytes"
        case endpointName = "endpoint_name"
        case requestUrl = "request_url"
        case requestMethod = "request_method"
        case requestHeaders = "request_headers"
        case requestBody = "request_body"
        case responseHeaders = "response_headers"
        case responseBody = "response_body"
    }
}

struct RunDetail: Codable, Identifiable, Sendable {
    let id: UUID
    let spec: TestSpec
    let status: RunStatus
    let startedAt: Date?
    let completedAt: Date?
    let metrics: Metrics
    let passed: Bool?
    let failureReasons: [String]
    let requestsCompleted: Int
    let errorMessage: String?
    let sampledRequests: [RequestSummary]
    let endpointMetrics: [EndpointMetrics]

    enum CodingKeys: String, CodingKey {
        case id, spec, status, metrics, passed
        case startedAt = "started_at"
        case completedAt = "completed_at"
        case failureReasons = "failure_reasons"
        case requestsCompleted = "requests_completed"
        case errorMessage = "error_message"
        case sampledRequests = "sampled_requests"
        case endpointMetrics = "endpoint_metrics"
    }

    var progress: Double {
        guard spec.totalRequests > 0 else { return 0 }
        return Double(requestsCompleted) / Double(spec.totalRequests)
    }
}

// API Response wrappers
struct RunListResponse: Codable, Sendable {
    let runs: [RunSummary]
    let total: Int
}

struct CreateRunRequest: Codable, Sendable {
    let spec: TestSpec
}

struct CreateRunResponse: Codable, Sendable {
    let id: UUID
    let status: RunStatus
    let message: String
}

struct CancelRunResponse: Codable, Sendable {
    let id: UUID
    let status: RunStatus
    let message: String
}

struct DeleteRunResponse: Codable, Sendable {
    let id: UUID
    let message: String
}

struct HealthResponse: Codable, Sendable {
    let status: String
    let version: String
    let timestamp: Date
}
