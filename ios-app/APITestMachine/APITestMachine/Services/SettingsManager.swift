//
//  SettingsManager.swift
//  APITestMachine
//
//  UserDefaults wrapper for app settings with Keychain for API key
//

import Foundation
import Security

@MainActor
@Observable
class SettingsManager {
    private let defaults = UserDefaults.standard

    private enum Keys {
        static let apiBaseURL = "apiBaseURL"
        static let pollingInterval = "pollingInterval"
        static let autoRefresh = "autoRefresh"
        static let showConnectionStatus = "showConnectionStatus"
        static let compactRunList = "compactRunList"
        static let apiKeyService = "com.apitestmachine.apikey"
    }

    // Default values (includes /api/v1 prefix)
    static let defaultAPIBaseURL = "http://localhost:8000/api/v1"
    static let defaultPollingInterval = 3.0

    var apiBaseURL: String {
        didSet {
            defaults.set(apiBaseURL, forKey: Keys.apiBaseURL)
            updateAPIClient()
        }
    }

    var apiKey: String {
        didSet {
            saveAPIKeyToKeychain(apiKey)
            updateAPIClient()
        }
    }

    var pollingInterval: Double {
        didSet {
            defaults.set(pollingInterval, forKey: Keys.pollingInterval)
        }
    }

    var autoRefresh: Bool {
        didSet {
            defaults.set(autoRefresh, forKey: Keys.autoRefresh)
        }
    }

    var showConnectionStatus: Bool {
        didSet {
            defaults.set(showConnectionStatus, forKey: Keys.showConnectionStatus)
        }
    }

    var compactRunList: Bool {
        didSet {
            defaults.set(compactRunList, forKey: Keys.compactRunList)
        }
    }

    var isConfigured: Bool {
        !apiBaseURL.isEmpty
    }

    var hasAPIKey: Bool {
        !apiKey.isEmpty
    }

    var baseURL: URL? {
        URL(string: apiBaseURL)
    }

    init() {
        // Initialize all stored properties first with sensible defaults
        self.apiBaseURL = defaults.string(forKey: Keys.apiBaseURL) ?? Self.defaultAPIBaseURL
        self.apiKey = Self.loadAPIKeyFromKeychain() ?? ""

        let savedInterval = defaults.double(forKey: Keys.pollingInterval)
        self.pollingInterval = savedInterval > 0 ? savedInterval : Self.defaultPollingInterval

        self.autoRefresh = defaults.object(forKey: Keys.autoRefresh) as? Bool ?? true
        self.showConnectionStatus = defaults.object(forKey: Keys.showConnectionStatus) as? Bool ?? true
        self.compactRunList = defaults.object(forKey: Keys.compactRunList) as? Bool ?? false

        // Now safe to call methods that use self
        updateAPIClient()
    }

    func resetToDefaults() {
        apiBaseURL = Self.defaultAPIBaseURL
        pollingInterval = Self.defaultPollingInterval
        autoRefresh = true
        showConnectionStatus = true
        compactRunList = false
    }

    private func updateAPIClient() {
        if let url = baseURL {
            Task {
                await APIClient.shared.configure(baseURL: url, apiKey: apiKey)
            }
        }
    }

    // MARK: - Keychain

    private func saveAPIKeyToKeychain(_ key: String) {
        let data = key.data(using: .utf8)!

        // Delete existing
        let deleteQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: Keys.apiKeyService
        ]
        SecItemDelete(deleteQuery as CFDictionary)

        // Add new
        let addQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: Keys.apiKeyService,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlocked
        ]
        SecItemAdd(addQuery as CFDictionary, nil)
    }

    private nonisolated static func loadAPIKeyFromKeychain() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: Keys.apiKeyService,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        if status == errSecSuccess, let data = result as? Data {
            return String(data: data, encoding: .utf8)
        }
        return nil
    }

    func clearAPIKey() {
        let deleteQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: Keys.apiKeyService
        ]
        SecItemDelete(deleteQuery as CFDictionary)
        apiKey = ""
    }
}
