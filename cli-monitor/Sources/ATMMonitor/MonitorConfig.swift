//
//  MonitorConfig.swift
//  ATMMonitor
//
//  Configuration for the monitor
//

import Foundation

struct MonitorConfig {
    let serverURL: String
    let apiKey: String?
    let refreshInterval: TimeInterval

    var baseURL: String {
        serverURL.hasSuffix("/") ? String(serverURL.dropLast()) : serverURL
    }

    var healthURL: String { "\(baseURL)/health" }
    var runsURL: String { "\(baseURL)/api/v1/runs?limit=20" }
    var schedulesURL: String { "\(baseURL)/api/v1/schedules?limit=20" }
}
