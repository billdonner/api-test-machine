//
//  TestSpec.swift
//  APITestMachine
//
//  Test configuration models matching the API
//

import Foundation

enum HttpMethod: String, Codable, CaseIterable, Sendable {
    case GET
    case POST
    case PUT
    case PATCH
    case DELETE
    case HEAD
    case OPTIONS
}

enum DistributionStrategy: String, Codable, CaseIterable, Sendable {
    case round_robin
    case weighted
    case sequential

    var displayName: String {
        switch self {
        case .round_robin: return "Round Robin"
        case .weighted: return "Weighted"
        case .sequential: return "Sequential"
        }
    }
}

struct Thresholds: Codable, Equatable, Sendable {
    var maxLatencyP50Ms: Double?
    var maxLatencyP95Ms: Double?
    var maxLatencyP99Ms: Double?
    var maxErrorRate: Double?
    var minThroughputRps: Double?

    enum CodingKeys: String, CodingKey {
        case maxLatencyP50Ms = "max_latency_p50_ms"
        case maxLatencyP95Ms = "max_latency_p95_ms"
        case maxLatencyP99Ms = "max_latency_p99_ms"
        case maxErrorRate = "max_error_rate"
        case minThroughputRps = "min_throughput_rps"
    }
}

struct EndpointSpec: Codable, Equatable, Identifiable, Sendable {
    var id: String { name }
    var name: String
    var url: String
    var method: HttpMethod = .GET
    var headers: [String: String] = [:]
    var body: AnyCodable?
    var weight: Int = 1
    var expectedStatusCodes: [Int] = [200, 201, 204]

    enum CodingKeys: String, CodingKey {
        case name, url, method, headers, body, weight
        case expectedStatusCodes = "expected_status_codes"
    }
}

struct TestSpec: Codable, Equatable, Sendable {
    var name: String
    var description: String?
    var url: String = ""
    var method: HttpMethod = .GET
    var headers: [String: String] = [:]
    var body: AnyCodable?
    var endpoints: [EndpointSpec]?
    var distributionStrategy: DistributionStrategy = .round_robin
    var totalRequests: Int = 100
    var concurrency: Int = 10
    var requestsPerSecond: Double?
    var timeoutSeconds: Double = 30.0
    var thresholds: Thresholds = Thresholds()
    var expectedStatusCodes: [Int] = [200, 201, 204]
    var variables: [String: String] = [:]

    enum CodingKeys: String, CodingKey {
        case name, description, url, method, headers, body, endpoints
        case distributionStrategy = "distribution_strategy"
        case totalRequests = "total_requests"
        case concurrency
        case requestsPerSecond = "requests_per_second"
        case timeoutSeconds = "timeout_seconds"
        case thresholds
        case expectedStatusCodes = "expected_status_codes"
        case variables
    }

    var isMultiEndpoint: Bool {
        endpoints != nil && !endpoints!.isEmpty
    }
}

// Helper for encoding/decoding arbitrary JSON - Sendable wrapper
enum JSONValue: Codable, Equatable, Sendable {
    case null
    case bool(Bool)
    case int(Int)
    case double(Double)
    case string(String)
    case array([JSONValue])
    case object([String: JSONValue])

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()

        if container.decodeNil() {
            self = .null
        } else if let bool = try? container.decode(Bool.self) {
            self = .bool(bool)
        } else if let int = try? container.decode(Int.self) {
            self = .int(int)
        } else if let double = try? container.decode(Double.self) {
            self = .double(double)
        } else if let string = try? container.decode(String.self) {
            self = .string(string)
        } else if let array = try? container.decode([JSONValue].self) {
            self = .array(array)
        } else if let object = try? container.decode([String: JSONValue].self) {
            self = .object(object)
        } else {
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Unable to decode JSON value")
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .null:
            try container.encodeNil()
        case .bool(let value):
            try container.encode(value)
        case .int(let value):
            try container.encode(value)
        case .double(let value):
            try container.encode(value)
        case .string(let value):
            try container.encode(value)
        case .array(let value):
            try container.encode(value)
        case .object(let value):
            try container.encode(value)
        }
    }

    var stringValue: String? {
        if case .string(let s) = self { return s }
        return nil
    }

    var intValue: Int? {
        if case .int(let i) = self { return i }
        return nil
    }

    var doubleValue: Double? {
        if case .double(let d) = self { return d }
        if case .int(let i) = self { return Double(i) }
        return nil
    }

    var boolValue: Bool? {
        if case .bool(let b) = self { return b }
        return nil
    }

    var objectValue: [String: JSONValue]? {
        if case .object(let o) = self { return o }
        return nil
    }

    var arrayValue: [JSONValue]? {
        if case .array(let a) = self { return a }
        return nil
    }

    // Convert to a string representation for display
    func toJSONString() -> String? {
        let encoder = JSONEncoder()
        encoder.outputFormatting = .prettyPrinted
        guard let data = try? encoder.encode(self),
              let string = String(data: data, encoding: .utf8) else {
            return nil
        }
        return string
    }

    // Create from a JSON string
    static func from(jsonString: String) -> JSONValue? {
        guard let data = jsonString.data(using: .utf8) else { return nil }
        return try? JSONDecoder().decode(JSONValue.self, from: data)
    }
}

// AnyCodable using JSONValue for Sendable compliance
struct AnyCodable: Codable, Equatable, Sendable {
    let value: JSONValue

    init(_ jsonValue: JSONValue) {
        self.value = jsonValue
    }

    init(_ string: String) {
        self.value = .string(string)
    }

    init(_ int: Int) {
        self.value = .int(int)
    }

    init(_ double: Double) {
        self.value = .double(double)
    }

    init(_ bool: Bool) {
        self.value = .bool(bool)
    }

    init(_ array: [AnyCodable]) {
        self.value = .array(array.map { $0.value })
    }

    init(_ dict: [String: AnyCodable]) {
        self.value = .object(dict.mapValues { $0.value })
    }

    init(from decoder: Decoder) throws {
        self.value = try JSONValue(from: decoder)
    }

    func encode(to encoder: Encoder) throws {
        try value.encode(to: encoder)
    }

    // Convenience accessors
    var stringValue: String? { value.stringValue }
    var intValue: Int? { value.intValue }
    var doubleValue: Double? { value.doubleValue }
    var boolValue: Bool? { value.boolValue }

    func toJSONString() -> String? {
        value.toJSONString()
    }
}
