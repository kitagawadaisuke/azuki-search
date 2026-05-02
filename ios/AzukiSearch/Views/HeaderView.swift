import SwiftUI

struct HeaderView: View {
    let title: String
    let subtitle: String
    @Binding var query: String
    var searchPlaceholder: String = "番組名・歌名・コーナー名で検索"
    var onSubmit: (() -> Void)? = nil

    @StateObject private var speech = SpeechRecognizer()
    @State private var showSpeechAlert: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .center, spacing: 12) {
                MascotView(size: 52)
                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.system(size: 22, weight: .bold))
                        .foregroundColor(AppColor.text)
                    Text(subtitle)
                        .font(.system(size: 11))
                        .foregroundColor(AppColor.textDim)
                        .lineLimit(2)
                }
                Spacer(minLength: 0)
            }

            // search bar
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 15))
                    .foregroundColor(AppColor.textVeryDim)
                TextField(searchPlaceholder, text: $query)
                    .font(.system(size: 14))
                    .foregroundColor(AppColor.text)
                    .submitLabel(.search)
                    .onSubmit { onSubmit?() }
                if !query.isEmpty {
                    Button {
                        query = ""
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(AppColor.textVeryDim)
                    }
                    .buttonStyle(.plain)
                }
                Button {
                    speech.toggle()
                } label: {
                    ZStack {
                        if speech.isRecording {
                            Circle()
                                .fill(AppColor.primaryPink.opacity(0.18))
                                .frame(width: 30, height: 30)
                                .overlay(
                                    Circle().stroke(AppColor.primaryPink, lineWidth: 1.5)
                                )
                        }
                        Image(systemName: speech.isRecording ? "stop.fill" : "mic")
                            .font(.system(size: 15, weight: speech.isRecording ? .bold : .regular))
                            .foregroundColor(speech.isRecording ? AppColor.primaryPink : AppColor.textVeryDim)
                    }
                    .frame(width: 30, height: 30)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 11)
            .background(
                Capsule().fill(AppColor.surface)
            )
            .overlay(
                Capsule().stroke(speech.isRecording ? AppColor.primaryPink : AppColor.border, lineWidth: speech.isRecording ? 1.5 : 1)
            )

            if speech.isRecording {
                HStack(spacing: 6) {
                    Circle()
                        .fill(AppColor.primaryPink)
                        .frame(width: 6, height: 6)
                    Text("聞いてるよ…")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundColor(AppColor.primaryPink)
                    Spacer()
                }
                .padding(.horizontal, 8)
            }
        }
        .padding(.horizontal, 16)
        .padding(.top, 18)
        .padding(.bottom, 4)
        // 音声認識結果を query にバインド
        .onChange(of: speech.transcript) { _, newValue in
            if !newValue.isEmpty {
                query = newValue
            }
        }
        .onChange(of: speech.errorMessage) { _, msg in
            if msg != nil { showSpeechAlert = true }
        }
        .alert("音声検索", isPresented: $showSpeechAlert, presenting: speech.errorMessage) { _ in
            Button("OK") { speech.errorMessage = nil }
        } message: { msg in
            Text(msg)
        }
    }
}

#Preview {
    @Previewable @State var q = ""
    return HeaderView(
        title: "今日の放送内容",
        subtitle: "子ども番組の放送内容を検索・記録・アーカイブ",
        query: $q
    )
    .background(AppColor.bgGradient)
}
