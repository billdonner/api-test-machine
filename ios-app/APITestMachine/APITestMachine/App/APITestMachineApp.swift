//
//  APITestMachineApp.swift
//  APITestMachine
//
//  Main entry point for the API Test Machine iOS app
//

import SwiftUI

@main
struct APITestMachineApp: App {
    @State private var settingsManager = SettingsManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(settingsManager)
        }
    }
}
