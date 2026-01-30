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

    var body: some View {
        NavigationStack {
            Group {
                if !settingsManager.isConfigured {
                    ConfigurationRequiredView()
                } else if viewModel.runs.isEmpty && viewModel.error == nil {
                    EmptyDashboardView(showCreateTest: $showingCreateTest)
                } else {
                    runsList
                }
            }
            .navigationTitle("Dashboard")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        showingCreateTest = true
                    } label: {
                        Image(systemName: "plus")
                    }
                    .disabled(!settingsManager.isConfigured)
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
                if settingsManager.isConfigured && settingsManager.autoRefresh {
                    viewModel.startPolling(interval: settingsManager.pollingInterval)
                }
            }
            .onDisappear {
                viewModel.stopPolling()
            }
            .onChange(of: settingsManager.isConfigured) { _, isConfigured in
                if isConfigured {
                    Task { await viewModel.refresh() }
                }
            }
        }
    }

    private var runsList: some View {
        List {
            if let error = viewModel.error {
                Section {
                    ErrorBannerView(error: error) {
                        Task { await viewModel.refresh() }
                    }
                }
            }

            StatsSection(viewModel: viewModel)

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
        .listStyle(.insetGrouped)
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

struct ConfigurationRequiredView: View {
    var body: some View {
        ContentUnavailableView {
            Label("Configuration Required", systemImage: "gear")
        } description: {
            Text("Please configure your API URL and API key in Settings to get started.")
        } actions: {
            Text("Go to Settings tab")
                .foregroundStyle(.secondary)
        }
    }
}

struct EmptyDashboardView: View {
    @Binding var showCreateTest: Bool

    var body: some View {
        ContentUnavailableView {
            Label("No Test Runs", systemImage: "testtube.2")
        } description: {
            Text("Create your first test to get started.")
        } actions: {
            Button("Create Test") {
                showCreateTest = true
            }
            .buttonStyle(.borderedProminent)
        }
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
