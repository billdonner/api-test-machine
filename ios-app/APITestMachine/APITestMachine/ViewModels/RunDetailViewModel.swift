//
//  RunDetailViewModel.swift
//  APITestMachine
//
//  Single run detail state management
//

import Foundation

@MainActor
@Observable
class RunDetailViewModel {
    var runDetail: RunDetail?
    var isLoading = false
    var error: APIError?
    var selectedRequest: RequestDetail?

    private let runId: UUID
    private var refreshTask: Task<Void, Never>?

    init(runId: UUID) {
        self.runId = runId
    }

    var isActive: Bool {
        runDetail?.status.isActive ?? false
    }

    func startPolling() {
        guard isActive else { return }

        refreshTask = Task {
            while !Task.isCancelled {
                await refresh()
                guard self.isActive else { break }
                try? await Task.sleep(for: .seconds(2))
            }
        }
    }

    func stopPolling() {
        refreshTask?.cancel()
        refreshTask = nil
    }

    func load() async {
        isLoading = true
        defer { isLoading = false }

        do {
            runDetail = try await APIClient.shared.getRun(id: runId)
            error = nil
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(error)
        }
    }

    func refresh() async {
        do {
            runDetail = try await APIClient.shared.getRun(id: runId)
            error = nil
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(error)
        }
    }

    func loadRequestDetail(requestNumber: Int) async {
        do {
            selectedRequest = try await APIClient.shared.getRequestDetail(
                runId: runId,
                requestNumber: requestNumber
            )
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(error)
        }
    }

    func cancelRun() async {
        do {
            _ = try await APIClient.shared.cancelRun(id: runId)
            await refresh()
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(error)
        }
    }
}
