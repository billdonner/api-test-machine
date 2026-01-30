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
        static let apiKeyService = "com.apitestmachine.apikey"
    }

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

    var isConfigured: Bool {
        !apiBaseURL.isEmpty && !apiKey.isEmpty
    }

    var baseURL: URL? {
        URL(string: apiBaseURL)
    }

    init() {
        // Initialize all stored properties first
        self.apiBaseURL = defaults.string(forKey: Keys.apiBaseURL) ?? ""
        self.apiKey = Self.loadAPIKeyFromKeychain() ?? ""

        let savedInterval = defaults.double(forKey: Keys.pollingInterval)
        self.pollingInterval = savedInterval > 0 ? savedInterval : 3.0

        self.autoRefresh = defaults.object(forKey: Keys.autoRefresh) as? Bool ?? true

        // Now safe to call methods that use self
        updateAPIClient()
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
