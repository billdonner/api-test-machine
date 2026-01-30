//
//  RunDetailView.swift
//  APITestMachine
//
//  Run details screen with metrics and requests
//

import SwiftUI

struct RunDetailView: View {
    let runId: UUID

    @State private var viewModel: RunDetailViewModel
    @State private var selectedRequestNumber: Int?
    @State private var showingRequestDetail = false

    init(runId: UUID) {
        self.runId = runId
        self._viewModel = State(initialValue: RunDetailViewModel(runId: runId))
    }

    var body: some View {
        Group {
            if viewModel.isLoading && viewModel.runDetail == nil {
                ProgressView("Loading...")
            } else if let runDetail = viewModel.runDetail {
                runDetailContent(runDetail)
            } else if let error = viewModel.error {
                ContentUnavailableView {
                    Label("Error", systemImage: "exclamationmark.triangle")
                } description: {
                    Text(error.localizedDescription)
                } actions: {
                    Button("Retry") {
                        Task { await viewModel.load() }
                    }
                    .buttonStyle(.borderedProminent)
                }
            }
        }
        .navigationTitle(viewModel.runDetail?.spec.name ?? "Run Details")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if viewModel.isActive {
                ToolbarItem(placement: .primaryAction) {
                    Button("Cancel") {
                        Task { await viewModel.cancelRun() }
                    }
                    .foregroundStyle(.red)
                }
            }
        }
        .task {
            await viewModel.load()
            viewModel.startPolling()
        }
        .onDisappear {
            viewModel.stopPolling()
        }
        .sheet(isPresented: $showingRequestDetail) {
            if let requestNumber = selectedRequestNumber {
                RequestDetailSheet(
                    viewModel: viewModel,
                    requestNumber: requestNumber
                )
            }
        }
    }

    private func runDetailContent(_ runDetail: RunDetail) -> some View {
        List {
            // Status and Progress Section
            Section {
                statusRow(runDetail)

                if runDetail.status.isActive {
                    progressRow(runDetail)
                }

                if let errorMessage = runDetail.errorMessage {
                    HStack {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundStyle(.red)
                        Text(errorMessage)
                            .foregroundStyle(.red)
                    }
                }

                if !runDetail.failureReasons.isEmpty {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Failure Reasons")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        ForEach(runDetail.failureReasons, id: \.self) { reason in
                            Text("• \(reason)")
                                .font(.caption)
                                .foregroundStyle(.red)
                        }
                    }
                }
            } header: {
                Text("Status")
            }

            // Metrics Section
            Section {
                MetricsView(metrics: runDetail.metrics)
            } header: {
                Text("Metrics")
            }

            // Charts Section
            if runDetail.metrics.totalRequests > 0 {
                Section {
                    LatencyChart(metrics: runDetail.metrics)
                        .frame(height: 200)
                } header: {
                    Text("Latency Distribution")
                }

                if !runDetail.metrics.statusCodeCounts.isEmpty {
                    Section {
                        StatusCodeChart(statusCodes: runDetail.metrics.statusCodeCounts)
                            .frame(height: 200)
                    } header: {
                        Text("Status Codes")
                    }
                }
            }

            // Sampled Requests Section
            if !runDetail.sampledRequests.isEmpty {
                Section {
                    RequestListView(
                        requests: runDetail.sampledRequests,
                        onSelect: { request in
                            selectedRequestNumber = request.requestNumber
                            showingRequestDetail = true
                        }
                    )
                } header: {
                    Text("Sampled Requests (\(runDetail.sampledRequests.count))")
                }
            }

            // Test Spec Section
            Section {
                specInfoRow("URL", value: runDetail.spec.url)
                specInfoRow("Method", value: runDetail.spec.method.rawValue)
                specInfoRow("Total Requests", value: "\(runDetail.spec.totalRequests)")
                specInfoRow("Concurrency", value: "\(runDetail.spec.concurrency)")
                specInfoRow("Timeout", value: "\(runDetail.spec.timeoutSeconds)s")
            } header: {
                Text("Test Configuration")
            }
        }
        .listStyle(.insetGrouped)
        .refreshable {
            await viewModel.refresh()
        }
    }

    private func statusRow(_ runDetail: RunDetail) -> some View {
        HStack {
            Text("Status")
            Spacer()
            HStack(spacing: 6) {
                Circle()
                    .fill(statusColor(runDetail))
                    .frame(width: 8, height: 8)
                Text(runDetail.status.displayName)
                    .foregroundStyle(statusColor(runDetail))
            }
        }
    }

    private func progressRow(_ runDetail: RunDetail) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Progress")
                Spacer()
                Text("\(runDetail.requestsCompleted)/\(runDetail.spec.totalRequests)")
                    .foregroundStyle(.secondary)
            }
            ProgressView(value: runDetail.progress)
        }
    }

    private func specInfoRow(_ title: String, value: String) -> some View {
        HStack {
            Text(title)
                .foregroundStyle(.secondary)
            Spacer()
            Text(value)
                .lineLimit(1)
        }
    }

    private func statusColor(_ runDetail: RunDetail) -> Color {
        switch runDetail.status {
        case .pending: return .gray
        case .running: return .blue
        case .completed:
            if let passed = runDetail.passed {
                return passed ? .green : .red
            }
            return .gray
        case .cancelled: return .orange
        case .failed: return .red
        }
    }
}

struct RequestDetailSheet: View {
    let viewModel: RunDetailViewModel
    let requestNumber: Int

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Group {
                if let request = viewModel.selectedRequest {
                    requestDetailContent(request)
                } else {
                    ProgressView("Loading...")
                }
            }
            .navigationTitle("Request #\(requestNumber)")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") { dismiss() }
                }
            }
            .task {
                await viewModel.loadRequestDetail(requestNumber: requestNumber)
            }
        }
    }

    private func requestDetailContent(_ request: RequestDetail) -> some View {
        List {
            Section("Overview") {
                LabeledContent("Status Code") {
                    if let code = request.statusCode {
                        Text("\(code)")
                            .foregroundStyle(code < 400 ? .green : .red)
                    } else {
                        Text("N/A")
                    }
                }

                LabeledContent("Latency") {
                    Text(String(format: "%.2fms", request.latencyMs))
                }

                if let size = request.responseSizeBytes {
                    LabeledContent("Response Size") {
                        Text(ByteCountFormatter.string(fromByteCount: Int64(size), countStyle: .file))
                    }
                }

                if let error = request.error {
                    LabeledContent("Error") {
                        Text(error)
                            .foregroundStyle(.red)
                    }
                }
            }

            if let url = request.requestUrl {
                Section("Request") {
                    LabeledContent("URL") {
                        Text(url)
                            .lineLimit(2)
                            .font(.caption)
                    }

                    if let method = request.requestMethod {
                        LabeledContent("Method") {
                            Text(method)
                        }
                    }
                }
            }

            if let headers = request.requestHeaders, !headers.isEmpty {
                Section("Request Headers") {
                    ForEach(headers.sorted(by: { $0.key < $1.key }), id: \.key) { key, value in
                        VStack(alignment: .leading) {
                            Text(key)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Text(value)
                                .font(.caption)
                        }
                    }
                }
            }

            if let body = request.requestBody, !body.isEmpty {
                Section("Request Body") {
                    Text(body)
                        .font(.caption.monospaced())
                }
            }

            if let headers = request.responseHeaders, !headers.isEmpty {
                Section("Response Headers") {
                    ForEach(headers.sorted(by: { $0.key < $1.key }), id: \.key) { key, value in
                        VStack(alignment: .leading) {
                            Text(key)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Text(value)
                                .font(.caption)
                        }
                    }
                }
            }

            if let body = request.responseBody, !body.isEmpty {
                Section("Response Body") {
                    Text(body)
                        .font(.caption.monospaced())
                        .lineLimit(50)
                }
            }
        }
        .listStyle(.insetGrouped)
    }
}

#Preview {
    NavigationStack {
        RunDetailView(runId: UUID())
    }
    .environment(SettingsManager())
}
