//
//  Constants.swift
//  APITestMachine
//
//  API paths, colors, and other constants
//

import SwiftUI

enum APIPath {
    static let health = "/health"
    static let runs = "/runs"
    static let schedules = "/schedules"
    static let tests = "/tests"
    static let storage = "/storage"

    static func run(id: String) -> String {
        "\(runs)/\(id)"
    }

    static func runCancel(id: String) -> String {
        "\(runs)/\(id)/cancel"
    }

    static func request(runId: String, number: Int) -> String {
        "\(runs)/\(runId)/requests/\(number)"
    }

    static func schedule(id: String) -> String {
        "\(schedules)/\(id)"
    }

    static func schedulePause(id: String) -> String {
        "\(schedules)/\(id)/pause"
    }

    static func scheduleResume(id: String) -> String {
        "\(schedules)/\(id)/resume"
    }
}

enum AppColors {
    static let success = Color.green
    static let failure = Color.red
    static let warning = Color.orange
    static let info = Color.blue
    static let pending = Color.gray
    static let running = Color.blue

    static let latencyGood = Color.green
    static let latencyWarning = Color.yellow
    static let latencyBad = Color.red

    static func statusColor(_ status: RunStatus) -> Color {
        switch status {
        case .pending: return pending
        case .running: return running
        case .completed: return success
        case .cancelled: return warning
        case .failed: return failure
        }
    }

    static func latencyColor(_ latencyMs: Double, thresholdMs: Double = 1000) -> Color {
        if latencyMs < thresholdMs * 0.5 {
            return latencyGood
        } else if latencyMs < thresholdMs {
            return latencyWarning
        } else {
            return latencyBad
        }
    }

    static func statusCodeColor(_ code: Int) -> Color {
        switch code {
        case 200..<300: return success
        case 300..<400: return info
        case 400..<500: return warning
        case 500..<600: return failure
        default: return pending
        }
    }
}

enum AppDefaults {
    static let pollingInterval: TimeInterval = 3.0
    static let maxPollingInterval: TimeInterval = 30.0
    static let minPollingInterval: TimeInterval = 1.0

    static let defaultTotalRequests = 100
    static let defaultConcurrency = 10
    static let defaultTimeoutSeconds = 30.0

    static let maxDisplayedRequests = 100
    static let maxRunsPerPage = 50
}

enum AppStrings {
    static let appName = "API Test Machine"
    static let appVersion = "1.0.0"

    static let dashboardTitle = "Dashboard"
    static let schedulesTitle = "Schedules"
    static let settingsTitle = "Settings"

    static let noRuns = "No test runs yet"
    static let noSchedules = "No schedules configured"
    static let configureFirst = "Configure your API URL and key in Settings"

    static let loading = "Loading..."
    static let refreshing = "Refreshing..."
    static let error = "Error"
    static let retry = "Retry"
    static let cancel = "Cancel"
    static let delete = "Delete"
    static let confirm = "Confirm"
}
