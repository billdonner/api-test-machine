//
//  Metrics.swift
//  APITestMachine
//
//  Performance metrics models
//

import Foundation

struct Metrics: Codable, Equatable, Sendable {
    var totalRequests: Int = 0
    var successfulRequests: Int = 0
    var failedRequests: Int = 0
    var latencyMinMs: Double?
    var latencyMaxMs: Double?
    var latencyMeanMs: Double?
    var latencyP50Ms: Double?
    var latencyP90Ms: Double?
    var latencyP95Ms: Double?
    var latencyP99Ms: Double?
    var requestsPerSecond: Double?
    var durationSeconds: Double?
    var errorRate: Double?
    var errorsByType: [String: Int] = [:]
    var statusCodeCounts: [String: Int] = [:]
    var totalBytesReceived: Int = 0

    enum CodingKeys: String, CodingKey {
        case totalRequests = "total_requests"
        case successfulRequests = "successful_requests"
        case failedRequests = "failed_requests"
        case latencyMinMs = "latency_min_ms"
        case latencyMaxMs = "latency_max_ms"
        case latencyMeanMs = "latency_mean_ms"
        case latencyP50Ms = "latency_p50_ms"
        case latencyP90Ms = "latency_p90_ms"
        case latencyP95Ms = "latency_p95_ms"
        case latencyP99Ms = "latency_p99_ms"
        case requestsPerSecond = "requests_per_second"
        case durationSeconds = "duration_seconds"
        case errorRate = "error_rate"
        case errorsByType = "errors_by_type"
        case statusCodeCounts = "status_code_counts"
        case totalBytesReceived = "total_bytes_received"
    }

    var successRate: Double {
        guard totalRequests > 0 else { return 0 }
        return Double(successfulRequests) / Double(totalRequests)
    }

    var formattedDuration: String {
        guard let seconds = durationSeconds else { return "N/A" }
        if seconds < 60 {
            return String(format: "%.1fs", seconds)
        } else {
            let minutes = Int(seconds) / 60
            let remainingSeconds = Int(seconds) % 60
            return "\(minutes)m \(remainingSeconds)s"
        }
    }
}

struct EndpointMetrics: Codable, Identifiable, Sendable {
    var id: String { endpointName }
    var endpointName: String
    var metrics: Metrics

    enum CodingKeys: String, CodingKey {
        case endpointName = "endpoint_name"
        case metrics
    }
}
