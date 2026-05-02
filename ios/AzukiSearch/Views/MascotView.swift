import SwiftUI

// mockup の TVキャラ風マスコット (青いTV + 顔 + アンテナ)
struct MascotView: View {
    var size: CGFloat = 52

    var body: some View {
        ZStack {
            // 背景の角丸タイル(柔らかい青グラデ)
            RoundedRectangle(cornerRadius: size * 0.27, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [Color(red: 0.62, green: 0.86, blue: 0.96), Color(red: 0.45, green: 0.78, blue: 0.92)],
                        startPoint: .topLeading, endPoint: .bottomTrailing
                    )
                )

            // 内側のスクリーン部分 (オフホワイト)
            RoundedRectangle(cornerRadius: size * 0.16, style: .continuous)
                .fill(Color(red: 1.00, green: 0.97, blue: 0.91))
                .padding(size * 0.13)

            // アンテナ + 飾りドット (TVっぽさ)
            ZStack {
                // 左アンテナ
                Path { p in
                    p.move(to: CGPoint(x: size * 0.30, y: size * 0.21))
                    p.addLine(to: CGPoint(x: size * 0.20, y: size * 0.06))
                }
                .stroke(Color(red: 0.45, green: 0.78, blue: 0.92), style: StrokeStyle(lineWidth: size * 0.05, lineCap: .round))
                Circle()
                    .fill(Color(red: 1.00, green: 0.65, blue: 0.40))
                    .frame(width: size * 0.10, height: size * 0.10)
                    .position(x: size * 0.20, y: size * 0.06)

                // 右アンテナ
                Path { p in
                    p.move(to: CGPoint(x: size * 0.70, y: size * 0.21))
                    p.addLine(to: CGPoint(x: size * 0.80, y: size * 0.06))
                }
                .stroke(Color(red: 0.45, green: 0.78, blue: 0.92), style: StrokeStyle(lineWidth: size * 0.05, lineCap: .round))
                Circle()
                    .fill(Color(red: 1.00, green: 0.65, blue: 0.40))
                    .frame(width: size * 0.10, height: size * 0.10)
                    .position(x: size * 0.80, y: size * 0.06)
            }
            .frame(width: size, height: size, alignment: .topLeading)

            // 顔
            VStack(spacing: size * 0.10) {
                HStack(spacing: size * 0.18) {
                    Circle().fill(Color(red: 0.18, green: 0.15, blue: 0.13))
                        .frame(width: size * 0.08, height: size * 0.08)
                    Circle().fill(Color(red: 0.18, green: 0.15, blue: 0.13))
                        .frame(width: size * 0.08, height: size * 0.08)
                }
                // にっこり口
                Path { p in
                    p.move(to: CGPoint(x: 0, y: 0))
                    p.addQuadCurve(to: CGPoint(x: size * 0.20, y: 0), control: CGPoint(x: size * 0.10, y: size * 0.07))
                }
                .stroke(Color(red: 0.18, green: 0.15, blue: 0.13), style: StrokeStyle(lineWidth: size * 0.025, lineCap: .round))
                .frame(width: size * 0.20, height: size * 0.07)
            }
            .offset(y: size * 0.06)

            // ほっぺ
            HStack(spacing: size * 0.42) {
                Circle().fill(Color(red: 1.00, green: 0.70, blue: 0.78).opacity(0.7))
                    .frame(width: size * 0.07, height: size * 0.07)
                Circle().fill(Color(red: 1.00, green: 0.70, blue: 0.78).opacity(0.7))
                    .frame(width: size * 0.07, height: size * 0.07)
            }
            .offset(y: size * 0.10)
        }
        .frame(width: size, height: size)
    }
}

#Preview {
    HStack {
        MascotView(size: 52)
        MascotView(size: 80)
    }
    .padding()
    .background(Color(red: 1.00, green: 0.97, blue: 0.91))
}
