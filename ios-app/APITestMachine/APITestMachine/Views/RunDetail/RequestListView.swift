//
//  RequestListView.swift
//  APITestMachine
//
//  Sampled requests list
//

import SwiftUI

struct RequestListView: View {
    let requests: [RequestSummary]
    let onSelect: (RequestSummary) -> Void

    var body: some View {
        ForEach(requests) { request in
            RequestRow(request: request)
                .contentShape(Rectangle())
                .onTapGesture {
                    onSelect(request)
                }
        }
    }
}

struct RequestRow: View {
    let request: RequestSummary

    var body: some View {
        HStack(spacing: 12) {
            // Status indicator
            Circle()
                .fill(request.isSuccess ? Color.green : Color.red)
                .frame(width: 8, height: 8)

            // Request number
            Text("#\(request.requestNumber)")
                .font(.caption)
                .foregroundStyle(.secondary)
                .frame(width: 40, alignment: .leading)

            // Status code
            if let statusCode = request.statusCode {
                Text("\(statusCode)")
                    .font(.caption.monospaced())
                    .foregroundStyle(statusCode < 400 ? .green : .red)
                    .frame(width: 35, alignment: .leading)
            } else {
                Text("ERR")
                    .font(.caption.monospaced())
                    .foregroundStyle(.red)
                    .frame(width: 35, alignment: .leading)
            }

            // Latency
            Text(String(format: "%.0fms", request.latencyMs))
                .font(.caption.monospaced())
                .foregroundStyle(.secondary)

            Spacer()

            // Endpoint name if multi-endpoint
            if let endpoint = request.endpointName {
                Text(endpoint)
                    .font(.caption2)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Color.blue.opacity(0.1))
                    .clipShape(Capsule())
            }

            // Error indicator
            if request.error != nil {
                Image(systemName: "exclamationmark.circle.fill")
                    .foregroundStyle(.red)
                    .font(.caption)
            }

            Image(systemName: "chevron.right")
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
        .padding(.vertical, 4)
    }
}

#Preview {
    List {
        RequestListView(
            requests: [
                RequestSummary(
                    requestNumber: 1,
                    statusCode: 200,
                    latencyMs: 45.2,
                    error: nil,
                    timestamp: Date(),
                    responseSizeBytes: 1234,
                    endpointName: nil
                ),
                RequestSummary(
                    requestNumber: 2,
                    statusCode: 201,
                    latencyMs: 123.5,
                    error: nil,
                    timestamp: Date(),
                    responseSizeBytes: 567,
                    endpointName: "create-user"
                ),
                RequestSummary(
                    requestNumber: 3,
                    statusCode: nil,
                    latencyMs: 30000,
                    error: "Connection timeout",
                    timestamp: Date(),
                    responseSizeBytes: nil,
                    endpointName: nil
                ),
                RequestSummary(
                    requestNumber: 4,
                    statusCode: 500,
                    latencyMs: 234.1,
                    error: "Internal server error",
                    timestamp: Date(),
                    responseSizeBytes: 89,
                    endpointName: "get-data"
                )
            ],
            onSelect: { _ in }
        )
    }
}
