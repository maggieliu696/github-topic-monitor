import Foundation
import Security

let arguments = CommandLine.arguments
guard arguments.count == 3 else {
    fputs("usage: feishu_keychain_helper get|set SERVICE\n", stderr)
    exit(2)
}

let operation = arguments[1]
let service = arguments[2]
let account = NSUserName()
let base: [String: Any] = [
    kSecClass as String: kSecClassGenericPassword,
    kSecAttrService as String: service,
    kSecAttrAccount as String: account,
]

if operation == "get" {
    var query = base
    query[kSecReturnData as String] = true
    query[kSecMatchLimit as String] = kSecMatchLimitOne
    var result: CFTypeRef?
    let status = SecItemCopyMatching(query as CFDictionary, &result)
    guard status == errSecSuccess, let data = result as? Data else { exit(1) }
    FileHandle.standardOutput.write(data)
} else if operation == "set" {
    let data = FileHandle.standardInput.readDataToEndOfFile()
    guard !data.isEmpty else { exit(2) }
    SecItemDelete(base as CFDictionary)
    var item = base
    item[kSecValueData as String] = data
    let status = SecItemAdd(item as CFDictionary, nil)
    guard status == errSecSuccess else { exit(1) }
} else {
    exit(2)
}
