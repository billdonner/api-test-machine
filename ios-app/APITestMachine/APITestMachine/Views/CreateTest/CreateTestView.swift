//
//  CreateTestView.swift
//  APITestMachine
//
//  Test creation form
//

import SwiftUI

struct CreateTestView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var viewModel = CreateTestViewModel()

    var body: some View {
        NavigationStack {
            Form {
                // Basic Info
                Section("Test Info") {
                    TextField("Test Name", text: $viewModel.name)
                    TextField("Description (optional)", text: $viewModel.description)
                }

                // Endpoint Configuration
                Section {
                    Toggle("Multi-Endpoint Test", isOn: $viewModel.useMultiEndpoint)
                } header: {
                    Text("Endpoint Mode")
                } footer: {
                    Text(viewModel.useMultiEndpoint
                         ? "Configure multiple endpoints with distribution strategy"
                         : "Configure a single endpoint")
                }

                if viewModel.useMultiEndpoint {
                    multiEndpointSection
                } else {
                    singleEndpointSection
                }

                // Load Configuration
                Section("Load Configuration") {
                    Stepper("Total Requests: \(viewModel.totalRequests)",
                            value: $viewModel.totalRequests,
                            in: 1...100000,
                            step: viewModel.totalRequests < 100 ? 10 : 100)

                    Stepper("Concurrency: \(viewModel.concurrency)",
                            value: $viewModel.concurrency,
                            in: 1...1000)

                    HStack {
                        Text("Timeout")
                        Spacer()
                        TextField("30", value: $viewModel.timeoutSeconds, format: .number)
                            .keyboardType(.decimalPad)
                            .frame(width: 60)
                            .multilineTextAlignment(.trailing)
                        Text("seconds")
                            .foregroundStyle(.secondary)
                    }
                }

                // Thresholds
                ThresholdsView(viewModel: viewModel)

                // Variables
                Section {
                    ForEach(Array(viewModel.variables.enumerated()), id: \.offset) { index, _ in
                        HStack {
                            TextField("Key", text: Binding(
                                get: { viewModel.variables[index].key },
                                set: { viewModel.variables[index].key = $0 }
                            ))
                            .frame(maxWidth: 100)

                            Text("=")
                                .foregroundStyle(.secondary)

                            TextField("Value", text: Binding(
                                get: { viewModel.variables[index].value },
                                set: { viewModel.variables[index].value = $0 }
                            ))

                            Button {
                                viewModel.removeVariable(at: index)
                            } label: {
                                Image(systemName: "minus.circle.fill")
                                    .foregroundStyle(.red)
                            }
                            .buttonStyle(.plain)
                        }
                    }

                    Button {
                        viewModel.addVariable()
                    } label: {
                        Label("Add Variable", systemImage: "plus.circle")
                    }
                } header: {
                    Text("Variables")
                } footer: {
                    Text("Use {{variable_name}} in URLs or body")
                }
            }
            .navigationTitle("Create Test")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }

                ToolbarItem(placement: .confirmationAction) {
                    Button("Run") {
                        Task {
                            await viewModel.submit()
                            if viewModel.createdRunId != nil {
                                dismiss()
                            }
                        }
                    }
                    .disabled(!viewModel.isValid || viewModel.isSubmitting)
                }
            }
            .alert("Error", isPresented: .constant(viewModel.error != nil)) {
                Button("OK") {
                    viewModel.error = nil
                }
            } message: {
                if let error = viewModel.error {
                    Text(error.localizedDescription)
                }
            }
        }
    }

    private var singleEndpointSection: some View {
        Group {
            Section("Endpoint") {
                TextField("URL", text: $viewModel.url)
                    .keyboardType(.URL)
                    .textContentType(.URL)
                    .autocapitalization(.none)

                Picker("Method", selection: $viewModel.method) {
                    ForEach(HttpMethod.allCases, id: \.self) { method in
                        Text(method.rawValue).tag(method)
                    }
                }
            }

            Section {
                ForEach(Array(viewModel.headers.enumerated()), id: \.offset) { index, _ in
                    HStack {
                        TextField("Header", text: Binding(
                            get: { viewModel.headers[index].key },
                            set: { viewModel.headers[index].key = $0 }
                        ))
                        .frame(maxWidth: 120)

                        Text(":")
                            .foregroundStyle(.secondary)

                        TextField("Value", text: Binding(
                            get: { viewModel.headers[index].value },
                            set: { viewModel.headers[index].value = $0 }
                        ))

                        Button {
                            viewModel.removeHeader(at: index)
                        } label: {
                            Image(systemName: "minus.circle.fill")
                                .foregroundStyle(.red)
                        }
                        .buttonStyle(.plain)
                    }
                }

                Button {
                    viewModel.addHeader()
                } label: {
                    Label("Add Header", systemImage: "plus.circle")
                }
            } header: {
                Text("Headers")
            }

            if viewModel.method != .GET && viewModel.method != .HEAD {
                Section("Request Body") {
                    TextEditor(text: $viewModel.body)
                        .frame(minHeight: 100)
                        .font(.system(.body, design: .monospaced))
                }
            }
        }
    }

    private var multiEndpointSection: some View {
        Group {
            Section {
                Picker("Distribution", selection: $viewModel.distributionStrategy) {
                    ForEach(DistributionStrategy.allCases, id: \.self) { strategy in
                        Text(strategy.displayName).tag(strategy)
                    }
                }
            } header: {
                Text("Distribution Strategy")
            }

            ForEach(Array(viewModel.endpoints.enumerated()), id: \.offset) { index, endpoint in
                Section {
                    EndpointFormView(
                        endpoint: Binding(
                            get: { viewModel.endpoints[index] },
                            set: { viewModel.endpoints[index] = $0 }
                        ),
                        onDelete: {
                            viewModel.removeEndpoint(at: index)
                        }
                    )
                } header: {
                    Text("Endpoint \(index + 1): \(endpoint.name)")
                }
            }

            Section {
                Button {
                    viewModel.addEndpoint()
                } label: {
                    Label("Add Endpoint", systemImage: "plus.circle")
                }
            }
        }
    }
}

#Preview {
    CreateTestView()
}
