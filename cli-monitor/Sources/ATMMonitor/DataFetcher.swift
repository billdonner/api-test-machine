//
//  DataFetcher.swift
//  ATMMonitor
//
//  Fetches data from API Test Machine server
//

import Foundation
import AsyncHTTPClient
import NIOCore

actor DataFetcher {
    private let httpClient: HTTPClient
    private let config: MonitorConfig

    init(config: MonitorConfig) {
        self.config = config
        self.httpClient = HTTPClient(eventLoopGroupProvider: .singleton)
    }

    deinit {
        try? httpClient.syncShutdown()
    }

    func shutdown() async throws {
        try await httpClient.shutdown()
    }

    // MARK: - Fetch Methods

    func fetchHealth() async -> Result<HealthResponse, Error> {
        do {
            var request = HTTPClientRequest(url: config.healthURL)
            request.method = .GET
            addHeaders(&request)

            let response = try await httpClient.execute(request, timeout: .seconds(5))
            let body = try await response.body.collect(upTo: 1024 * 1024)
            let health = try JSONDecoder().decode(HealthResponse.self, from: body)
            return .success(health)
        } catch {
            return .failure(error)
        }
    }

    func fetchRuns() async -> Result<RunListResponse, Error> {
        do {
            var request = HTTPClientRequest(url: config.runsURL)
            request.method = .GET
            addHeaders(&request)

            let response = try await httpClient.execute(request, timeout: .seconds(10))
            let body = try await response.body.collect(upTo: 10 * 1024 * 1024)
            let runs = try JSONDecoder().decode(RunListResponse.self, from: body)
            return .success(runs)
        } catch {
            return .failure(error)
        }
    }

    func fetchSchedules() async -> Result<ScheduleListResponse, Error> {
        do {
            var request = HTTPClientRequest(url: config.schedulesURL)
            request.method = .GET
            addHeaders(&request)

            let response = try await httpClient.execute(request, timeout: .seconds(10))
            let body = try await response.body.collect(upTo: 10 * 1024 * 1024)
            let schedules = try JSONDecoder().decode(ScheduleListResponse.self, from: body)
            return .success(schedules)
        } catch {
            return .failure(error)
        }
    }

    func fetchAll() async -> DashboardState {
        var state = DashboardState()
        state.lastFetchTime = Date()

        // Fetch all in parallel
        async let healthResult = fetchHealth()
        async let runsResult = fetchRuns()
        async let schedulesResult = fetchSchedules()

        // Process health
        switch await healthResult {
        case .success(let health):
            state.serverOnline = health.status == "healthy" || health.status == "ok"
            state.serverVersion = health.version ?? "unknown"
            state.serverUptime = health.uptime ?? 0
        case .failure(let error):
            state.serverOnline = false
            state.fetchError = error.localizedDescription
        }

        // Process runs
        switch await runsResult {
        case .success(let response):
            state.runs = response.runs
        case .failure:
            // Keep existing runs on error
            break
        }

        // Process schedules
        switch await schedulesResult {
        case .success(let response):
            state.schedules = response.schedules
        case .failure:
            // Keep existing schedules on error
            break
        }

        return state
    }

    // MARK: - Helpers

    private func addHeaders(_ request: inout HTTPClientRequest) {
        request.headers.add(name: "Content-Type", value: "application/json")
        if let apiKey = config.apiKey, !apiKey.isEmpty {
            request.headers.add(name: "X-API-Key", value: apiKey)
        }
    }
}

// MARK: - Process Detection

func isPortListening(_ port: Int) -> Bool {
    let task = Process()
    task.executableURL = URL(fileURLWithPath: "/usr/sbin/lsof")
    task.arguments = ["-i", ":\(port)", "-sTCP:LISTEN"]
    task.standardOutput = FileHandle.nullDevice
    task.standardError = FileHandle.nullDevice

    do {
        try task.run()
        task.waitUntilExit()
        return task.terminationStatus == 0
    } catch {
        return false
    }
}

func getProcesses() -> [ATMProcessInfo] {
    [
        ATMProcessInfo(
            name: "API Server",
            port: 8000,
            isRunning: isPortListening(8000),
            pid: nil
        ),
        ATMProcessInfo(
            name: "Agent/Scheduler",
            port: 8001,
            isRunning: isPortListening(8001),
            pid: nil
        ),
    ]
}
