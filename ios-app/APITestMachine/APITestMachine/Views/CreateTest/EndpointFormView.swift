//
//  EndpointFormView.swift
//  APITestMachine
//
//  Endpoint configuration form for multi-endpoint tests
//

import SwiftUI

struct EndpointFormView: View {
    @Binding var endpoint: EndpointSpec
    let onDelete: () -> Void

    @State private var headers: [(key: String, value: String)] = []
    @State private var bodyText: String = ""

    var body: some View {
        Group {
            HStack {
                TextField("Endpoint Name", text: $endpoint.name)
                Button(role: .destructive) {
                    onDelete()
                } label: {
                    Image(systemName: "trash")
                }
                .buttonStyle(.plain)
                .foregroundStyle(.red)
            }

            TextField("URL", text: $endpoint.url)
                .keyboardType(.URL)
                .textContentType(.URL)
                .autocapitalization(.none)

            Picker("Method", selection: $endpoint.method) {
                ForEach(HttpMethod.allCases, id: \.self) { method in
                    Text(method.rawValue).tag(method)
                }
            }

            Stepper("Weight: \(endpoint.weight)", value: $endpoint.weight, in: 1...100)

            DisclosureGroup("Headers (\(endpoint.headers.count))") {
                ForEach(Array(headers.enumerated()), id: \.offset) { index, _ in
                    HStack {
                        TextField("Key", text: Binding(
                            get: { headers[index].key },
                            set: {
                                headers[index].key = $0
                                updateEndpointHeaders()
                            }
                        ))
                        .frame(maxWidth: 100)

                        Text(":")
                            .foregroundStyle(.secondary)

                        TextField("Value", text: Binding(
                            get: { headers[index].value },
                            set: {
                                headers[index].value = $0
                                updateEndpointHeaders()
                            }
                        ))

                        Button {
                            headers.remove(at: index)
                            updateEndpointHeaders()
                        } label: {
                            Image(systemName: "minus.circle.fill")
                                .foregroundStyle(.red)
                        }
                        .buttonStyle(.plain)
                    }
                }

                Button {
                    headers.append((key: "", value: ""))
                } label: {
                    Label("Add Header", systemImage: "plus.circle")
                }
            }

            if endpoint.method != .GET && endpoint.method != .HEAD {
                DisclosureGroup("Body") {
                    TextEditor(text: $bodyText)
                        .frame(minHeight: 80)
                        .font(.system(.caption, design: .monospaced))
                        .onChange(of: bodyText) { _, newValue in
                            updateEndpointBody(newValue)
                        }
                }
            }
        }
        .onAppear {
            headers = endpoint.headers.map { ($0.key, $0.value) }
            if let bodyValue = endpoint.body {
                bodyText = bodyValue.toJSONString() ?? bodyValue.stringValue ?? ""
            }
        }
    }

    private func updateEndpointHeaders() {
        endpoint.headers = Dictionary(uniqueKeysWithValues: headers.filter { !$0.key.isEmpty })
    }

    private func updateEndpointBody(_ text: String) {
        if text.isEmpty {
            endpoint.body = nil
        } else if let jsonValue = JSONValue.from(jsonString: text) {
            endpoint.body = AnyCodable(jsonValue)
        } else {
            endpoint.body = AnyCodable(text)
        }
    }
}

#Preview {
    Form {
        EndpointFormView(
            endpoint: .constant(EndpointSpec(
                name: "get-users",
                url: "https://api.example.com/users",
                method: .GET,
                headers: ["Authorization": "Bearer token"],
                weight: 2
            )),
            onDelete: {}
        )
    }
}
