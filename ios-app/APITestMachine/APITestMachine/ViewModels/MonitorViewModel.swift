//
//  MonitorViewModel.swift
//  APITestMachine
//
//  System monitor state management
//

import Foundation

@MainActor
@Observable
class MonitorViewModel {
    var systemStatus: SystemStatus?
    var isLoading = false
    var error: APIError?
    var lastRefresh: Date?
    var isPolling = true

    private var refreshTask: Task<Void, Never>?
    private var pollingInterval: TimeInterval = 3.0

    func startPolling(interval: TimeInterval = 3.0) {
        self.pollingInterval = interval
        stopPolling()
        isPolling = true

        refreshTask = Task {
            while !Task.isCancelled {
                await refresh()
                try? await Task.sleep(for: .seconds(interval))
            }
        }
    }

    func stopPolling() {
        refreshTask?.cancel()
        refreshTask = nil
        isPolling = false
    }

    func togglePolling(interval: TimeInterval = 3.0) {
        if isPolling {
            stopPolling()
        } else {
            startPolling(interval: interval)
        }
    }

    func refresh() async {
        isLoading = true
        defer { isLoading = false }

        do {
            systemStatus = try await APIClient.shared.getSystemStatus()
            lastRefresh = Date()
            self.error = nil
        } catch let apiError as APIError {
            self.error = apiError
        } catch {
            self.error = .networkError(error)
        }
    }
}
