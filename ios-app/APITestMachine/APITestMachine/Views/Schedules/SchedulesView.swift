//
//  SchedulesView.swift
//  APITestMachine
//
//  Schedule list view
//

import SwiftUI

struct SchedulesView: View {
    @Environment(SettingsManager.self) private var settingsManager
    @State private var viewModel = SchedulesViewModel()
    @State private var showingCreateSchedule = false

    var body: some View {
        NavigationStack {
            mainContent
            .navigationTitle("Schedules")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        showingCreateSchedule = true
                    } label: {
                        Image(systemName: "plus")
                    }
                    .disabled(!settingsManager.isConfigured)
                }
            }
            .sheet(isPresented: $showingCreateSchedule) {
                CreateScheduleView(viewModel: viewModel)
            }
            .refreshable {
                await viewModel.refresh()
            }
            .task {
                if settingsManager.isConfigured {
                    await viewModel.load()
                    viewModel.startPolling()
                }
            }
            .onDisappear {
                viewModel.stopPolling()
            }
        }
    }

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
                        Task { await viewModel.refresh() }
                    }
                }
            }

            // Schedules list or empty state
            if viewModel.schedules.isEmpty {
                Section {
                    EmptySchedulesRow(showCreateSchedule: $showingCreateSchedule)
                }
            } else {
                ForEach(viewModel.schedules) { schedule in
                    ScheduleRowView(schedule: schedule)
                        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                            Button("Delete", role: .destructive) {
                                if let uuid = schedule.uuid {
                                    Task { await viewModel.deleteSchedule(id: uuid) }
                                }
                            }

                            if schedule.paused {
                                Button("Resume") {
                                    if let uuid = schedule.uuid {
                                        Task { await viewModel.resumeSchedule(id: uuid) }
                                    }
                                }
                                .tint(.green)
                            } else {
                                Button("Pause") {
                                    if let uuid = schedule.uuid {
                                        Task { await viewModel.pauseSchedule(id: uuid) }
                                    }
                                }
                                .tint(.orange)
                            }
                        }
                }
            }
        }
        .listStyle(.insetGrouped)
    }

}

struct EmptySchedulesRow: View {
    @Binding var showCreateSchedule: Bool

    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: "calendar.badge.clock")
                .font(.largeTitle)
                .foregroundStyle(.secondary)

            Text("No schedules yet")
                .font(.headline)

            Text("Create a schedule to run tests automatically")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            Button("Create Schedule") {
                showCreateSchedule = true
            }
            .buttonStyle(.borderedProminent)
            .padding(.top, 8)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 24)
    }
}

#Preview {
    SchedulesView()
        .environment(SettingsManager())
}
