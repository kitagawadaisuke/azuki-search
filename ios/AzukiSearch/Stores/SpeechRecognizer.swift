import Foundation
import Speech
import AVFoundation

/// 音声検索 (Speech-to-Text) を担う。 ja-JP の SFSpeechRecognizer を使用。
@MainActor
final class SpeechRecognizer: ObservableObject {
    @Published var transcript: String = ""
    @Published var isRecording: Bool = false
    @Published var errorMessage: String? = nil

    private let recognizer: SFSpeechRecognizer?
    private var recognitionTask: SFSpeechRecognitionTask?
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private let audioEngine = AVAudioEngine()

    init() {
        self.recognizer = SFSpeechRecognizer(locale: Locale(identifier: "ja-JP"))
    }

    /// 録音中なら停止、停止中なら開始。
    func toggle() {
        if isRecording {
            stop()
        } else {
            Task { await start() }
        }
    }

    func start() async {
        errorMessage = nil

        guard let recognizer, recognizer.isAvailable else {
            errorMessage = "音声認識が利用できません"
            return
        }

        // 権限確認
        let speechAuth = await SFSpeechRecognizer.requestAuthorizationAsync()
        guard speechAuth == .authorized else {
            errorMessage = "音声認識の許可が必要です(設定アプリから有効化)"
            return
        }
        let micGranted = await AVAudioApplication.requestRecordPermissionAsync()
        guard micGranted else {
            errorMessage = "マイクの許可が必要です(設定アプリから有効化)"
            return
        }

        // 既存タスクがあれば停止
        stop()

        // AVAudioSession 設定
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(.record, mode: .measurement, options: [.duckOthers])
            try session.setActive(true, options: [.notifyOthersOnDeactivation])
        } catch {
            errorMessage = "オーディオセッション設定失敗: \(error.localizedDescription)"
            return
        }

        // 認識リクエスト準備
        let request = SFSpeechAudioBufferRecognitionRequest()
        request.shouldReportPartialResults = true
        recognitionRequest = request

        // input tap
        let inputNode = audioEngine.inputNode
        let recordingFormat = inputNode.outputFormat(forBus: 0)
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { buffer, _ in
            request.append(buffer)
        }

        audioEngine.prepare()
        do {
            try audioEngine.start()
        } catch {
            errorMessage = "録音開始失敗: \(error.localizedDescription)"
            return
        }

        isRecording = true
        transcript = ""

        recognitionTask = recognizer.recognitionTask(with: request) { [weak self] result, error in
            guard let self else { return }
            Task { @MainActor in
                if let result {
                    self.transcript = result.bestTranscription.formattedString
                    if result.isFinal {
                        self.stop()
                    }
                }
                if error != nil {
                    self.stop()
                }
            }
        }
    }

    func stop() {
        if audioEngine.isRunning {
            audioEngine.stop()
            audioEngine.inputNode.removeTap(onBus: 0)
        }
        recognitionRequest?.endAudio()
        recognitionTask?.cancel()
        recognitionRequest = nil
        recognitionTask = nil
        isRecording = false
    }
}

// MARK: - permission async helpers
extension SFSpeechRecognizer {
    static func requestAuthorizationAsync() async -> SFSpeechRecognizerAuthorizationStatus {
        await withCheckedContinuation { c in
            SFSpeechRecognizer.requestAuthorization { status in
                c.resume(returning: status)
            }
        }
    }
}

extension AVAudioApplication {
    static func requestRecordPermissionAsync() async -> Bool {
        await withCheckedContinuation { c in
            AVAudioApplication.requestRecordPermission { granted in
                c.resume(returning: granted)
            }
        }
    }
}
