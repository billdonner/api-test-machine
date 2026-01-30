//
//  Schedule.swift
//  APITestMachine
//
//  Schedule configuration models
//

import Foundation

enum TriggerType: String, Codable, CaseIterable, Sendable {
    case cron
    case interval
    case date

    var displayName: String {
        switch self {
        case .cron: return "Cron"
        case .interval: return "Interval"
        case .date: return "One-time"
        }
    }
}

struct IntervalTrigger: Codable, Equatable, Sendable {
    var type: String = "interval"
    var seconds: Int?
    var minutes: Int?
    var hours: Int?
    var days: Int?

    var displayDescription: String {
        var parts: [String] = []
        if let days = days, days > 0 {
            parts.append("\(days) day\(days == 1 ? "" : "s")")
        }
        if let hours = hours, hours > 0 {
            parts.append("\(hours) hour\(hours == 1 ? "" : "s")")
        }
        if let minutes = minutes, minutes > 0 {
            parts.append("\(minutes) minute\(minutes == 1 ? "" : "s")")
        }
        if let seconds = seconds, seconds > 0 {
            parts.append("\(seconds) second\(seconds == 1 ? "" : "s")")
        }
        return parts.isEmpty ? "No interval" : "Every " + parts.joined(separator: ", ")
    }
}

struct CronTrigger: Codable, Equatable, Sendable {
    var type: String = "cron"
    var minute: String = "*"
    var hour: String = "*"
    var day: String = "*"
    var month: String = "*"
    var dayOfWeek: String = "*"
    var timezone: String = "UTC"

    enum CodingKeys: String, CodingKey {
        case type, minute, hour, day, month, timezone
        case dayOfWeek = "day_of_week"
    }

    var cronExpression: String {
        "\(minute) \(hour) \(day) \(month) \(dayOfWeek)"
    }
}

struct DateTrigger: Codable, Equatable, Sendable {
    var type: String = "date"
    var runDate: Date

    enum CodingKeys: String, CodingKey {
        case type
        case runDate = "run_date"
    }
}

struct ScheduleResponse: Codable, Identifiable, Sendable {
    let id: String
    let name: String
    let description: String?
    let testName: String
    let triggerType: String
    let trigger: [String: AnyCodable]
    let maxRuns: Int?
    let runCount: Int
    let enabled: Bool
    let paused: Bool
    let nextRunTime: String?
    let createdAt: Date
    let updatedAt: Date
    let tags: [String]

    enum CodingKeys: String, CodingKey {
        case id, name, description, trigger, enabled, paused, tags
        case testName = "test_name"
        case triggerType = "trigger_type"
        case maxRuns = "max_runs"
        case runCount = "run_count"
        case nextRunTime = "next_run_time"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }

    var triggerDisplayDescription: String {
        switch TriggerType(rawValue: triggerType) {
        case .interval:
            var parts: [String] = []
            if let days = trigger["days"]?.intValue, days > 0 {
                parts.append("\(days)d")
            }
            if let hours = trigger["hours"]?.intValue, hours > 0 {
                parts.append("\(hours)h")
            }
            if let minutes = trigger["minutes"]?.intValue, minutes > 0 {
                parts.append("\(minutes)m")
            }
            if let seconds = trigger["seconds"]?.intValue, seconds > 0 {
                parts.append("\(seconds)s")
            }
            return parts.isEmpty ? "Interval" : "Every " + parts.joined(separator: " ")
        case .cron:
            let minute = trigger["minute"]?.stringValue ?? "*"
            let hour = trigger["hour"]?.stringValue ?? "*"
            return "Cron: \(minute) \(hour) * * *"
        case .date:
            return "One-time"
        case .none:
            return triggerType
        }
    }

    var uuid: UUID? {
        UUID(uuidString: id)
    }
}

struct ScheduleListResponse: Codable, Sendable {
    let schedules: [ScheduleResponse]
    let total: Int
}

struct CreateScheduleRequest: Codable, Sendable {
    let name: String
    let description: String?
    let testName: String
    let spec: TestSpec?
    let trigger: AnyCodable
    let maxRuns: Int?
    let enabled: Bool
    let tags: [String]

    enum CodingKeys: String, CodingKey {
        case name, description, spec, trigger, enabled, tags
        case testName = "test_name"
        case maxRuns = "max_runs"
    }
}

struct ScheduleActionResponse: Codable, Sendable {
    let id: String
    let action: String
    let success: Bool
    let message: String
}
