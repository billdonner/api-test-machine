//
//  DashboardView.swift
//  APITestMachine
//
//  Main dashboard with run list and stats
//

import SwiftUI

struct DashboardView: View {
    @Environment(SettingsManager.self) private var settingsManager
    @State private var viewModel = DashboardViewModel()
    @State private var showingCreateTest = false
    @State private var selectedRun: RunSummary?
    @State private var isRefreshing = false

    var body: some View {
        NavigationStack {
            mainContent
                .navigationTitle("Dashboard")
                .toolbar {
                    ToolbarItem(placement: .primaryAction) {
                        HStack(spacing: 12) {
                            // Refresh button
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

                            // Create test button
                            Button {
                                showingCreateTest = true
                            } label: {
                                Image(systemName: "plus")
                            }
                        }
                    }

                    ToolbarItem(placement: .topBarLeading) {
                        Menu {
                            Button("All") { viewModel.filterByStatus(nil) }
                            Divider()
                            ForEach(RunStatus.allCases, id: \.self) { status in
                                Button(status.displayName) {
                                    viewModel.filterByStatus(status)
                                }
                            }
                        } label: {
                            Label(
                                viewModel.selectedStatus?.displayName ?? "All",
                                systemImage: "line.3.horizontal.decrease.circle"
                            )
                        }
                    }
                }
                .sheet(isPresented: $showingCreateTest) {
                    CreateTestView()
                }
                .navigationDestination(item: $selectedRun) { run in
                    RunDetailView(runId: run.id)
                }
                .refreshable {
                    await viewModel.refresh()
                }
                .onAppear {
                    // Always try to refresh on appear
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

    // Always show the main content structure, even with missing data
    private var mainContent: some View {
        List {
            // Connection status section (if enabled)
            if settingsManager.showConnectionStatus {
                ConnectionStatusSection(
                    isConfigured: settingsManager.isConfigured,
                    hasAPIKey: settingsManager.hasAPIKey,
                    error: viewModel.error,
                    isLoading: viewModel.isLoading
                )
            }

            // Error banner if present
            if let error = viewModel.error {
                Section {
                    ErrorBannerView(error: error) {
                        Task { await manualRefresh() }
                    }
                }
            }

            // Stats section - always show, even with zeros
            StatsSection(viewModel: viewModel)

            // Runs list or empty state
            if viewModel.runs.isEmpty {
                Section {
                    EmptyRunsRow(showCreateTest: $showingCreateTest)
                }
            } else {
                ForEach(viewModel.sortedGroupNames, id: \.self) { groupName in
                    Section {
                        ForEach(viewModel.groupedRuns[groupName] ?? []) { run in
                            RunRowView(run: run)
                                .contentShape(Rectangle())
                                .onTapGesture {
                                    selectedRun = run
                                }
                                .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                                    if run.status.isActive {
                                        Button("Cancel", role: .destructive) {
                                            Task { await viewModel.cancelRun(id: run.id) }
                                        }
                                    } else {
                                        Button("Delete", role: .destructive) {
                                            Task { await viewModel.deleteRun(id: run.id) }
                                        }
                                    }
                                }
                        }
                    } header: {
                        HStack {
                            Text(groupName)
                            Spacer()
                            Text("\(viewModel.groupedRuns[groupName]?.count ?? 0) runs")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
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

struct StatsSection: View {
    let viewModel: DashboardViewModel

    var body: some View {
        Section {
            LazyVGrid(columns: [
                GridItem(.flexible()),
                GridItem(.flexible())
            ], spacing: 12) {
                StatsCardView(
                    title: "Total Runs",
                    value: "\(viewModel.total)",
                    icon: "number",
                    color: .blue
                )

                StatsCardView(
                    title: "Active",
                    value: "\(viewModel.activeRunsCount)",
                    icon: "play.circle.fill",
                    color: .orange
                )

                StatsCardView(
                    title: "Passed",
                    value: "\(viewModel.passedRunsCount)",
                    icon: "checkmark.circle.fill",
                    color: .green
                )

                StatsCardView(
                    title: "Failed",
                    value: "\(viewModel.failedRunsCount)",
                    icon: "xmark.circle.fill",
                    color: .red
                )
            }
            .padding(.vertical, 8)
        }
    }
}

struct ConnectionStatusSection: View {
    let isConfigured: Bool
    let hasAPIKey: Bool
    let error: APIError?
    let isLoading: Bool

    var body: some View {
        Section {
            HStack {
                // Status indicator
                Circle()
                    .fill(statusColor)
                    .frame(width: 10, height: 10)

                Text(statusText)
                    .font(.subheadline)

                Spacer()

                if isLoading {
                    ProgressView()
                        .scaleEffect(0.7)
                }
            }
        } header: {
            Text("Connection")
        }
    }

    private var statusColor: Color {
        if !isConfigured {
            return .gray
        } else if error != nil {
            return .red
        } else {
            return .green
        }
    }

    private var statusText: String {
        if !isConfigured {
            return "Not configured - set API URL in Settings"
        } else if !hasAPIKey {
            return "Connected (no API key)"
        } else if error != nil {
            return "Connection error"
        } else {
            return "Connected"
        }
    }
}

struct EmptyRunsRow: View {
    @Binding var showCreateTest: Bool

    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: "testtube.2")
                .font(.largeTitle)
                .foregroundStyle(.secondary)

            Text("No test runs yet")
                .font(.headline)

            Text("Create your first test to get started")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            Button("Create Test") {
                showCreateTest = true
            }
            .buttonStyle(.borderedProminent)
            .padding(.top, 8)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 24)
    }
}

struct ErrorBannerView: View {
    let error: APIError
    let retry: () -> Void

    var body: some View {
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
                retry()
            }
            .buttonStyle(.bordered)
        }
        .padding(.vertical, 4)
    }
}

#Preview {
    DashboardView()
        .environment(SettingsManager())
}
