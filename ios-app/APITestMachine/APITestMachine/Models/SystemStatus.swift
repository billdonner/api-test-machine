//
//  SystemStatus.swift
//  APITestMachine
//
//  System status models for monitor view
//

import Foundation

struct ProcessStatus: Codable, Identifiable, Sendable {
    var id: String { name }
    let name: String
    let port: Int
    let running: Bool
}

struct ServerInfo: Codable, Sendable {
    let online: Bool
    let version: String
    let uptime: Double

    var formattedUptime: String {
        let hours = Int(uptime / 3600)
        let minutes = Int((uptime.truncatingRemainder(dividingBy: 3600)) / 60)
        if hours > 0 {
            return "\(hours)h \(minutes)m"
        }
        return "\(minutes)m"
    }
}

struct SystemStats: Codable, Sendable {
    let totalRuns: Int
    let activeRuns: Int
    let passedRuns: Int
    let failedRuns: Int
    let passRate: Double

    enum CodingKeys: String, CodingKey {
        case totalRuns = "total_runs"
        case activeRuns = "active_runs"
        case passedRuns = "passed_runs"
        case failedRuns = "failed_runs"
        case passRate = "pass_rate"
    }

    var formattedPassRate: String {
        String(format: "%.0f%%", passRate)
    }
}

struct ActiveScheduleInfo: Codable, Identifiable, Sendable {
    let id: String
    let name: String
    let testName: String
    let triggerType: String
    let runCount: Int
    let maxRuns: Int?
    let nextRunTime: String?

    enum CodingKeys: String, CodingKey {
        case id, name
        case testName = "test_name"
        case triggerType = "trigger_type"
        case runCount = "run_count"
        case maxRuns = "max_runs"
        case nextRunTime = "next_run_time"
    }

    var formattedNextRun: String {
        guard let nextRunTime = nextRunTime else { return "-" }

        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

        // Try multiple date formats
        var date: Date?
        date = formatter.date(from: nextRunTime)

        if date == nil {
            formatter.formatOptions = [.withInternetDateTime]
            date = formatter.date(from: nextRunTime)
        }

        if date == nil {
            let dateFormatter = DateFormatter()
            dateFormatter.locale = Locale(identifier: "en_US_POSIX")
            dateFormatter.timeZone = TimeZone(identifier: "UTC")
            dateFormatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"
            date = dateFormatter.date(from: nextRunTime)
        }

        guard let parsedDate = date else { return nextRunTime }

        let now = Date()
        let diffMs = parsedDate.timeIntervalSince(now) * 1000

        if diffMs < 0 { return "Now" }

        let diffMins = Int(diffMs / 60000)
        if diffMins < 60 { return "In \(diffMins)m" }

        let diffHours = diffMins / 60
        return "In \(diffHours)h \(diffMins % 60)m"
    }
}

struct SystemStatus: Codable, Sendable {
    let server: ServerInfo
    let processes: [ProcessStatus]
    let stats: SystemStats
    let activeRuns: [RunSummary]
    let activeSchedules: [ActiveScheduleInfo]

    enum CodingKeys: String, CodingKey {
        case server, processes, stats
        case activeRuns = "active_runs"
        case activeSchedules = "active_schedules"
    }
}
