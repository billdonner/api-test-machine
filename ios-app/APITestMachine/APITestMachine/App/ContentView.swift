//
//  ContentView.swift
//  APITestMachine
//
//  Main tab-based navigation view
//

import SwiftUI

struct ContentView: View {
    @Environment(SettingsManager.self) private var settingsManager
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            DashboardView()
                .tabItem {
                    Label("Dashboard", systemImage: "chart.bar.fill")
                }
                .tag(0)

            SchedulesView()
                .tabItem {
                    Label("Schedules", systemImage: "calendar.badge.clock")
                }
                .tag(1)

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
                .tag(2)
        }
    }
}

#Preview {
    ContentView()
        .environment(SettingsManager())
}
