//
//  Models.swift
//  ATMMonitor
//
//  Data models for API Test Machine monitoring
//

import Foundation

// MARK: - API Response Models

struct RunListResponse: Codable {
    let runs: [RunSummary]
    let total: Int
}

struct RunSummary: Codable {
    let id: String
    let name: String
    let status: String
    let passed: Bool?
    let requestsCompleted: Int
    let totalRequests: Int
    let createdAt: String
    let startedAt: String?
    let completedAt: String?

    enum CodingKeys: String, CodingKey {
        case id, name, status, passed
        case requestsCompleted = "requests_completed"
        case totalRequests = "total_requests"
        case createdAt = "created_at"
        case startedAt = "started_at"
        case completedAt = "completed_at"
    }

    var progressPercent: Int {
        guard totalRequests > 0 else { return 0 }
        return Int((Double(requestsCompleted) / Double(totalRequests)) * 100)
    }
}

struct ScheduleListResponse: Codable {
    let schedules: [ScheduleSummary]
    let total: Int
}

struct ScheduleSummary: Codable {
    let id: String
    let name: String
    let testName: String
    let triggerType: String
    let enabled: Bool
    let paused: Bool
    let runCount: Int
    let maxRuns: Int?
    let nextRunTime: String?

    enum CodingKeys: String, CodingKey {
        case id, name, enabled, paused
        case testName = "test_name"
        case triggerType = "trigger_type"
        case runCount = "run_count"
        case maxRuns = "max_runs"
        case nextRunTime = "next_run_time"
    }
}

struct HealthResponse: Codable {
    let status: String
    let version: String?
    let uptime: Double?
}

// MARK: - Dashboard State

struct DashboardState {
    var serverOnline: Bool = false
    var serverVersion: String = "unknown"
    var serverUptime: TimeInterval = 0

    var runs: [RunSummary] = []
    var schedules: [ScheduleSummary] = []

    var lastFetchTime: Date = Date()
    var fetchError: String? = nil

    var activeRuns: [RunSummary] {
        runs.filter { $0.status == "running" || $0.status == "pending" }
    }

    var recentCompletedRuns: [RunSummary] {
        runs.filter { $0.status == "completed" || $0.status == "failed" || $0.status == "cancelled" }
            .prefix(5)
            .map { $0 }
    }

    var enabledSchedules: [ScheduleSummary] {
        schedules.filter { $0.enabled && !$0.paused }
    }

    var pausedSchedules: [ScheduleSummary] {
        schedules.filter { $0.paused }
    }
}

// MARK: - Process Info

struct ATMProcessInfo {
    let name: String
    let port: Int
    let isRunning: Bool
    let pid: Int?
}
