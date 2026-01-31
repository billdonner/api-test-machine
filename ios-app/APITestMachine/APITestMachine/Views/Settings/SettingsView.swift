//
//  SettingsView.swift
//  APITestMachine
//
//  Settings screen for API URL and API key configuration
//

import SwiftUI

struct SettingsView: View {
    @Environment(SettingsManager.self) private var settingsManager
    @State private var isTestingConnection = false
    @State private var connectionStatus: ConnectionStatus?
    @State private var showingClearConfirmation = false

    enum ConnectionStatus {
        case success(String)
        case failure(String)
    }

    var body: some View {
        @Bindable var settings = settingsManager

        NavigationStack {
            Form {
                Section {
                    TextField("API Base URL", text: $settings.apiBaseURL)
                        .keyboardType(.URL)
                        .textContentType(.URL)
                        .autocapitalization(.none)
                        .autocorrectionDisabled()

                    SecureField("API Key", text: $settings.apiKey)
                        .textContentType(.password)
                        .autocapitalization(.none)
                        .autocorrectionDisabled()
                } header: {
                    Text("API Configuration")
                } footer: {
                    Text("Enter the URL of your API Test Machine server and your API key.")
                }

                Section {
                    Button {
                        Task { await testConnection() }
                    } label: {
                        HStack {
                            Text("Test Connection")
                            Spacer()
                            if isTestingConnection {
                                ProgressView()
                            }
                        }
                    }
                    .disabled(!settingsManager.isConfigured || isTestingConnection)

                    if let status = connectionStatus {
                        HStack {
                            switch status {
                            case .success(let message):
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundStyle(.green)
                                Text(message)
                                    .foregroundStyle(.green)
                            case .failure(let message):
                                Image(systemName: "xmark.circle.fill")
                                    .foregroundStyle(.red)
                                Text(message)
                                    .foregroundStyle(.red)
                            }
                        }
                        .font(.caption)
                    }
                }

                Section {
                    Toggle("Auto-refresh Dashboard", isOn: $settings.autoRefresh)

                    if settings.autoRefresh {
                        HStack {
                            Text("Refresh Interval")
                            Spacer()
                            Picker("", selection: $settings.pollingInterval) {
                                Text("1s").tag(1.0)
                                Text("2s").tag(2.0)
                                Text("3s").tag(3.0)
                                Text("5s").tag(5.0)
                                Text("10s").tag(10.0)
                            }
                            .pickerStyle(.segmented)
                            .frame(maxWidth: 200)
                        }
                    }

                    Toggle("Show Connection Status", isOn: $settings.showConnectionStatus)

                    Toggle("Compact Run List", isOn: $settings.compactRunList)
                } header: {
                    Text("Dashboard")
                } footer: {
                    Text("Connection status shows server online/offline indicator. Compact list shows more runs on screen.")
                }

                Section {
                    Button(role: .destructive) {
                        showingClearConfirmation = true
                    } label: {
                        Text("Clear API Key")
                    }
                    .disabled(settingsManager.apiKey.isEmpty)

                    Button {
                        settingsManager.resetToDefaults()
                    } label: {
                        Text("Reset to Defaults")
                    }
                } header: {
                    Text("Security")
                } footer: {
                    Text("Your API key is stored securely in the iOS Keychain. Reset to Defaults restores all settings except the API key.")
                }

                Section {
                    LabeledContent("Version", value: "1.0.0")
                    LabeledContent("Build", value: Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "1")
                } header: {
                    Text("About")
                }
            }
            .navigationTitle("Settings")
            .alert("Clear API Key?", isPresented: $showingClearConfirmation) {
                Button("Cancel", role: .cancel) {}
                Button("Clear", role: .destructive) {
                    settingsManager.clearAPIKey()
                }
            } message: {
                Text("This will remove your API key from the device. You'll need to enter it again to use the app.")
            }
        }
    }

    private func testConnection() async {
        isTestingConnection = true
        connectionStatus = nil

        do {
            let health = try await APIClient.shared.checkHealth()
            connectionStatus = .success("Connected! Server v\(health.version)")
        } catch let error as APIError {
            connectionStatus = .failure(error.localizedDescription)
        } catch {
            connectionStatus = .failure(error.localizedDescription)
        }

        isTestingConnection = false
    }
}

#Preview {
    SettingsView()
        .environment(SettingsManager())
}
