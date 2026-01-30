//
//  CreateTestViewModel.swift
//  APITestMachine
//
//  Test creation form state management
//

import Foundation

@MainActor
@Observable
class CreateTestViewModel {
    // Basic info
    var name: String = ""
    var description: String = ""

    // Single endpoint (legacy mode)
    var url: String = ""
    var method: HttpMethod = .GET
    var headers: [(key: String, value: String)] = []
    var body: String = ""

    // Multi-endpoint mode
    var useMultiEndpoint: Bool = false
    var endpoints: [EndpointSpec] = []
    var distributionStrategy: DistributionStrategy = .round_robin

    // Load configuration
    var totalRequests: Int = 100
    var concurrency: Int = 10
    var requestsPerSecond: Double?
    var timeoutSeconds: Double = 30.0

    // Thresholds
    var maxLatencyP50Ms: Double?
    var maxLatencyP95Ms: Double?
    var maxLatencyP99Ms: Double?
    var maxErrorRate: Double?
    var minThroughputRps: Double?

    // Expected status codes
    var expectedStatusCodes: [Int] = [200, 201, 204]

    // Variables
    var variables: [(key: String, value: String)] = []

    // State
    var isSubmitting = false
    var error: APIError?
    var createdRunId: UUID?

    var isValid: Bool {
        !name.isEmpty && (useMultiEndpoint ? !endpoints.isEmpty : !url.isEmpty)
    }

    func addHeader() {
        headers.append((key: "", value: ""))
    }

    func removeHeader(at index: Int) {
        headers.remove(at: index)
    }

    func addVariable() {
        variables.append((key: "", value: ""))
    }

    func removeVariable(at index: Int) {
        variables.remove(at: index)
    }

    func addEndpoint() {
        endpoints.append(EndpointSpec(name: "endpoint-\(endpoints.count + 1)", url: ""))
    }

    func removeEndpoint(at index: Int) {
        endpoints.remove(at: index)
    }

    func buildSpec() -> TestSpec {
        let headersDict = Dictionary(uniqueKeysWithValues: headers.filter { !$0.key.isEmpty })
        let variablesDict = Dictionary(uniqueKeysWithValues: variables.filter { !$0.key.isEmpty })

        let thresholds = Thresholds(
            maxLatencyP50Ms: maxLatencyP50Ms,
            maxLatencyP95Ms: maxLatencyP95Ms,
            maxLatencyP99Ms: maxLatencyP99Ms,
            maxErrorRate: maxErrorRate,
            minThroughputRps: minThroughputRps
        )

        var bodyValue: AnyCodable? = nil
        if !body.isEmpty {
            // Try to parse as JSON
            if let jsonValue = JSONValue.from(jsonString: body) {
                bodyValue = AnyCodable(jsonValue)
            } else {
                bodyValue = AnyCodable(body)
            }
        }

        return TestSpec(
            name: name,
            description: description.isEmpty ? nil : description,
            url: useMultiEndpoint ? "" : url,
            method: method,
            headers: headersDict,
            body: bodyValue,
            endpoints: useMultiEndpoint ? endpoints : nil,
            distributionStrategy: distributionStrategy,
            totalRequests: totalRequests,
            concurrency: concurrency,
            requestsPerSecond: requestsPerSecond,
            timeoutSeconds: timeoutSeconds,
            thresholds: thresholds,
            expectedStatusCodes: expectedStatusCodes,
            variables: variablesDict
        )
    }

    func submit() async {
        guard isValid else { return }

        isSubmitting = true
        defer { isSubmitting = false }

        do {
            let spec = buildSpec()
            let response = try await APIClient.shared.createRun(spec: spec)
            createdRunId = response.id
            error = nil
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .networkError(error)
        }
    }

    func reset() {
        name = ""
        description = ""
        url = ""
        method = .GET
        headers = []
        body = ""
        useMultiEndpoint = false
        endpoints = []
        distributionStrategy = .round_robin
        totalRequests = 100
        concurrency = 10
        requestsPerSecond = nil
        timeoutSeconds = 30.0
        maxLatencyP50Ms = nil
        maxLatencyP95Ms = nil
        maxLatencyP99Ms = nil
        maxErrorRate = nil
        minThroughputRps = nil
        expectedStatusCodes = [200, 201, 204]
        variables = []
        error = nil
        createdRunId = nil
    }

    func loadFromSpec(_ spec: TestSpec) {
        name = spec.name
        description = spec.description ?? ""
        url = spec.url
        method = spec.method
        headers = spec.headers.map { ($0.key, $0.value) }

        if let bodyValue = spec.body {
            body = bodyValue.toJSONString() ?? bodyValue.stringValue ?? ""
        }

        useMultiEndpoint = spec.isMultiEndpoint
        endpoints = spec.endpoints ?? []
        distributionStrategy = spec.distributionStrategy
        totalRequests = spec.totalRequests
        concurrency = spec.concurrency
        requestsPerSecond = spec.requestsPerSecond
        timeoutSeconds = spec.timeoutSeconds
        maxLatencyP50Ms = spec.thresholds.maxLatencyP50Ms
        maxLatencyP95Ms = spec.thresholds.maxLatencyP95Ms
        maxLatencyP99Ms = spec.thresholds.maxLatencyP99Ms
        maxErrorRate = spec.thresholds.maxErrorRate
        minThroughputRps = spec.thresholds.minThroughputRps
        expectedStatusCodes = spec.expectedStatusCodes
        variables = spec.variables.map { ($0.key, $0.value) }
    }
}
