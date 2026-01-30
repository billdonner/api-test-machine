//
//  SchedulesViewModel.swift
//  APITestMachine
//
//  Schedule management state
//

import Foundation

@MainActor
@Observable
class SchedulesViewModel {
    var schedules: [ScheduleResponse] = []
    var testConfigs: [TestConfigResponse] = []
    var isLoading = false
    var error: APIError?

    private var refreshTask: Task<Void, Never>?

    func startPolling() {
        stopPolling()

        refreshTask = Task {
            while !Task.isCancelled {
                await refresh()
                try? await Task.sleep(for: .seconds(10))
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

        await refresh()
        await loadTestConfigs()
    }

    func refresh() async {
        do {
            let response = try await APIClient.shared.listSchedules()
            schedules = response.schedules
            error = nil
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(error)
        }
    }

    func loadTestConfigs() async {
        do {
            let response = try await APIClient.shared.listTestConfigs()
            testConfigs = response.configs
        } catch {
            // Ignore errors for test configs
        }
    }

    func pauseSchedule(id: UUID) async {
        do {
            _ = try await APIClient.shared.pauseSchedule(id: id)
            await refresh()
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(error)
        }
    }

    func resumeSchedule(id: UUID) async {
        do {
            _ = try await APIClient.shared.resumeSchedule(id: id)
            await refresh()
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(error)
        }
    }

    func deleteSchedule(id: UUID) async {
        do {
            _ = try await APIClient.shared.deleteSchedule(id: id)
            schedules.removeAll { $0.uuid == id }
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(error)
        }
    }

    func createSchedule(
        name: String,
        description: String?,
        testName: String,
        trigger: AnyCodable,
        maxRuns: Int?,
        enabled: Bool = true,
        tags: [String] = []
    ) async throws {
        let request = CreateScheduleRequest(
            name: name,
            description: description,
            testName: testName,
            spec: nil,
            trigger: trigger,
            maxRuns: maxRuns,
            enabled: enabled,
            tags: tags
        )

        _ = try await APIClient.shared.createSchedule(request: request)
        await refresh()
    }
}
