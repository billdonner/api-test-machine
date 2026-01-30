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
            Group {
                if !settingsManager.isConfigured {
                    ConfigurationRequiredView()
                } else if viewModel.isLoading && viewModel.schedules.isEmpty {
                    ProgressView("Loading schedules...")
                } else if viewModel.schedules.isEmpty {
                    emptyState
                } else {
                    schedulesList
                }
            }
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

    private var emptyState: some View {
        ContentUnavailableView {
            Label("No Schedules", systemImage: "calendar.badge.clock")
        } description: {
            Text("Create a schedule to run tests automatically.")
        } actions: {
            Button("Create Schedule") {
                showingCreateSchedule = true
            }
            .buttonStyle(.borderedProminent)
        }
    }

    private var schedulesList: some View {
        List {
            if let error = viewModel.error {
                Section {
                    ErrorBannerView(error: error) {
                        Task { await viewModel.refresh() }
                    }
                }
            }

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
        .listStyle(.insetGrouped)
    }
}

#Preview {
    SchedulesView()
        .environment(SettingsManager())
}
