//
//  MonitorView.swift
//  APITestMachine
//
//  System monitor view showing server status, processes, and active runs
//

import SwiftUI

struct MonitorView: View {
    @Environment(SettingsManager.self) private var settingsManager
    @State private var viewModel = MonitorViewModel()
    @State private var isRefreshing = false

    var body: some View {
        NavigationStack {
            mainContent
                .navigationTitle("System Monitor")
                .toolbar {
                    ToolbarItem(placement: .primaryAction) {
                        HStack(spacing: 12) {
                            // Polling toggle
                            Button {
                                viewModel.togglePolling(interval: settingsManager.pollingInterval)
                            } label: {
                                Image(systemName: viewModel.isPolling ? "pause.circle.fill" : "play.circle.fill")
                                    .foregroundStyle(viewModel.isPolling ? .green : .secondary)
                            }

                            // Manual refresh
                            Button {
                                Task { await manualRefresh() }
                            } label: {
                                if isRefreshing {
                                    ProgressView()
                                        .scaleEffect(0.8)
                                } else {
                                    Image(systemName: "arrow.clockwise")
                                }
                            }
                            .disabled(isRefreshing)
                            .keyboardShortcut("r", modifiers: .command)
                        }
                    }

                    ToolbarItem(placement: .topBarLeading) {
                        if let lastRefresh = viewModel.lastRefresh {
                            Text("Last: \(lastRefresh.formatted(date: .omitted, time: .shortened))")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
                .refreshable {
                    await viewModel.refresh()
                }
                .onAppear {
                    Task { await viewModel.refresh() }
                    if settingsManager.autoRefresh {
                        viewModel.startPolling(interval: settingsManager.pollingInterval)
                    }
                }
                .onDisappear {
                    viewModel.stopPolling()
                }
        }
    }

    private var mainContent: some View {
        List {
            // Error banner if present
            if let error = viewModel.error {
                Section {
                    HStack {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundStyle(.orange)
                        VStack(alignment: .leading) {
                            Text("Error")
                                .font(.headline)
                            Text(error.localizedDescription)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        Button("Retry") {
                            Task { await manualRefresh() }
                        }
                        .buttonStyle(.bordered)
                    }
                }
            }

            // Loading state
            if viewModel.isLoading && viewModel.systemStatus == nil {
                Section {
                    HStack {
                        Spacer()
                        ProgressView("Loading system status...")
                        Spacer()
                    }
                    .padding()
                }
            }

            if let status = viewModel.systemStatus {
                // Server Status Section
                Section {
                    ServerStatusRow(server: status.server)
                } header: {
                    Text("Server")
                }

                // Process Status Section
                Section {
                    ForEach(status.processes) { process in
                        ProcessRow(process: process)
                    }
                } header: {
                    Text("Processes")
                }

                // Stats Section
                Section {
                    LazyVGrid(columns: [
                        GridItem(.flexible()),
                        GridItem(.flexible())
                    ], spacing: 12) {
                        StatsCardView(
                            title: "Total Runs",
                            value: "\(status.stats.totalRuns)",
                            icon: "number",
                            color: .cyan
                        )

                        StatsCardView(
                            title: "Active",
                            value: "\(status.stats.activeRuns)",
                            icon: "play.circle.fill",
                            color: .yellow
                        )

                        StatsCardView(
                            title: "Passed",
                            value: "\(status.stats.passedRuns)",
                            icon: "checkmark.circle.fill",
                            color: .green
                        )

                        StatsCardView(
                            title: "Failed",
                            value: "\(status.stats.failedRuns)",
                            icon: "xmark.circle.fill",
                            color: .red
                        )
                    }
                    .padding(.vertical, 8)

                    // Pass rate row
                    HStack {
                        Text("Pass Rate")
                            .foregroundStyle(.secondary)
                        Spacer()
                        Text(status.stats.formattedPassRate)
                            .font(.title2)
                            .fontWeight(.bold)
                    }
                } header: {
                    Text("Statistics")
                }

                // Active Runs Section
                Section {
                    if status.activeRuns.isEmpty {
                        Text("No active runs")
                            .foregroundStyle(.secondary)
                            .frame(maxWidth: .infinity, alignment: .center)
                            .padding()
                    } else {
                        ForEach(status.activeRuns) { run in
                            ActiveRunRow(run: run)
                        }
                    }
                } header: {
                    HStack {
                        Text("Active Runs")
                        Spacer()
                        Text("\(status.activeRuns.count)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                // Active Schedules Section
                Section {
                    if status.activeSchedules.isEmpty {
                        Text("No active schedules")
                            .foregroundStyle(.secondary)
                            .frame(maxWidth: .infinity, alignment: .center)
                            .padding()
                    } else {
                        ForEach(status.activeSchedules) { schedule in
                            ActiveScheduleRow(schedule: schedule)
                        }
                    }
                } header: {
                    HStack {
                        Text("Active Schedules")
                        Spacer()
                        Text("\(status.activeSchedules.count)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
        .listStyle(.insetGrouped)
    }

    private func manualRefresh() async {
        isRefreshing = true
        await viewModel.refresh()
        isRefreshing = false
    }
}

// MARK: - Row Views

struct ServerStatusRow: View {
    let server: ServerInfo

    var body: some View {
        HStack {
            Circle()
                .fill(server.online ? .green : .red)
                .frame(width: 12, height: 12)

            VStack(alignment: .leading) {
                Text(server.online ? "Online" : "Offline")
                    .font(.headline)
                    .foregroundStyle(server.online ? .green : .red)

                HStack(spacing: 16) {
                    Text("v\(server.version)")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    Text("Uptime: \(server.formattedUptime)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Spacer()
        }
    }
}

struct ProcessRow: View {
    let process: ProcessStatus

    var body: some View {
        HStack {
            Circle()
                .fill(process.running ? .green : .red)
                .frame(width: 10, height: 10)

            VStack(alignment: .leading) {
                Text(process.name)
                    .font(.subheadline)
                    .fontWeight(.medium)

                Text("Port \(process.port)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Text(process.running ? "Running" : "Stopped")
                .font(.caption)
                .foregroundStyle(process.running ? .green : .red)
        }
    }
}

struct ActiveRunRow: View {
    let run: RunSummary

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(run.name)
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .lineLimit(1)

                Spacer()

                Text(run.status.displayName.uppercased())
                    .font(.caption2)
                    .fontWeight(.semibold)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(.yellow.opacity(0.2))
                    .foregroundStyle(.yellow)
                    .clipShape(RoundedRectangle(cornerRadius: 4))
            }

            // Progress bar
            HStack(spacing: 8) {
                ProgressView(value: run.progress)
                    .tint(.blue)

                Text("\(run.requestsCompleted)/\(run.totalRequests)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 4)
    }
}

struct ActiveScheduleRow: View {
    let schedule: ActiveScheduleInfo

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(schedule.name)
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .lineLimit(1)

                Spacer()

                Text(schedule.triggerType)
                    .font(.caption2)
                    .fontWeight(.medium)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(.green.opacity(0.2))
                    .foregroundStyle(.green)
                    .clipShape(RoundedRectangle(cornerRadius: 4))
            }

            HStack {
                Text("Test: \(schedule.testName)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)

                Spacer()

                if let maxRuns = schedule.maxRuns {
                    Text("Runs: \(schedule.runCount)/\(maxRuns)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                } else {
                    Text("Runs: \(schedule.runCount)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Text("Next: \(schedule.formattedNextRun)")
                .font(.caption)
                .foregroundStyle(.blue)
        }
        .padding(.vertical, 4)
    }
}

#Preview {
    MonitorView()
        .environment(SettingsManager())
}
