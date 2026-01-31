//
//  DashboardViewModel.swift
//  APITestMachine
//
//  Dashboard state management with live polling
//

import Foundation

@MainActor
@Observable
class DashboardViewModel {
    var runs: [RunSummary] = []
    var isLoading = false
    var error: APIError?
    var selectedStatus: RunStatus?
    var total: Int = 0

    private var refreshTask: Task<Void, Never>?
    private var pollingInterval: TimeInterval = 3.0

    var groupedRuns: [String: [RunSummary]] {
        Dictionary(grouping: runs, by: { $0.name })
    }

    var sortedGroupNames: [String] {
        groupedRuns.keys.sorted()
    }

    var activeRunsCount: Int {
        runs.filter { $0.status.isActive }.count
    }

    var completedRunsCount: Int {
        runs.filter { $0.status.isComplete }.count
    }

    var passedRunsCount: Int {
        runs.filter { $0.passed == true }.count
    }

    var failedRunsCount: Int {
        runs.filter { $0.passed == false }.count
    }

    func startPolling(interval: TimeInterval = 3.0) {
        self.pollingInterval = interval
        stopPolling()

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
    }

    func refresh() async {
        isLoading = true
        defer { isLoading = false }

        do {
            let response = try await APIClient.shared.listRuns(status: selectedStatus, limit: 100)
            self.runs = response.runs
            self.total = response.total
            self.error = nil
        } catch let apiError as APIError {
            self.error = apiError
        } catch {
            self.error = .networkError(error)
        }
    }

    func loadMore() async {
        guard !isLoading else { return }
        isLoading = true
        defer { isLoading = false }

        do {
            let response = try await APIClient.shared.listRuns(
                status: selectedStatus,
                limit: 50,
                offset: runs.count
            )
            self.runs.append(contentsOf: response.runs)
            self.total = response.total
        } catch let apiError as APIError {
            self.error = apiError
        } catch {
            self.error = .networkError(error)
        }
    }

    func cancelRun(id: UUID) async {
        do {
            _ = try await APIClient.shared.cancelRun(id: id)
            await refresh()
        } catch let apiError as APIError {
            self.error = apiError
        } catch {
            self.error = .networkError(error)
        }
    }

    func deleteRun(id: UUID) async {
        do {
            _ = try await APIClient.shared.deleteRun(id: id)
            runs.removeAll { $0.id == id }
        } catch let apiError as APIError {
            self.error = apiError
        } catch {
            self.error = .networkError(error)
        }
    }

    func filterByStatus(_ status: RunStatus?) {
        selectedStatus = status
        Task {
            await refresh()
        }
    }
}
