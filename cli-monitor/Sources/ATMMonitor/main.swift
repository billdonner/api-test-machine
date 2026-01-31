//
//  main.swift
//  ATMMonitor
//
//  Terminal monitor for API Test Machine
//

import Foundation
import ArgumentParser

@main
struct ATMMonitor: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "atm-monitor",
        abstract: "Real-time terminal dashboard for API Test Machine",
        version: "1.0.0"
    )

    @Option(name: [.short, .long], help: "API server URL")
    var server: String = "http://localhost:8000"

    @Option(name: [.short, .long], help: "API key for authentication (or set ATM_API_KEY env var)")
    var apiKey: String = ""

    @Option(name: [.short, .long], help: "Refresh interval in seconds")
    var refresh: Int = 3

    mutating func run() async throws {
        // Load API key from environment if not provided via flag
        let key = apiKey.isEmpty ? ProcessInfo.processInfo.environment["ATM_API_KEY"] : apiKey

        let config = MonitorConfig(
            serverURL: server,
            apiKey: key,
            refreshInterval: TimeInterval(refresh)
        )

        print("Starting API Test Machine Monitor...")
        print("Server: \(config.serverURL)")
        print("Refresh: \(refresh)s")
        print("")
        print("Press 'q' to quit, 'r' to refresh")
        print("")

        // Brief pause before starting dashboard
        try await Task.sleep(nanoseconds: 1_000_000_000)

        let dashboard = Dashboard(config: config)
        await dashboard.run()
    }
}
